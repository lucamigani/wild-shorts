import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

os.environ.update(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="42", IG_USER_ID="9", IG_ACCESS_TOKEN="x")
from bot import carousel, channels, content, footage, guide, main, story


class Content(unittest.TestCase):
    def test_seeds_are_valid_and_unique(self):
        for s in content.SEEDS:
            content.validate(dict(s))
        self.assertEqual(len({s["id"] for s in content.SEEDS}), len(content.SEEDS))

    def test_answers_are_not_always_in_one_position(self):
        self.assertEqual({s["correct"] for s in content.SEEDS}, {0, 1, 2})

    def test_banned_topic_rejected(self):
        s = dict(content.SEEDS[0], explanation="Eat these wild berries.")
        with self.assertRaises(ValueError):
            content.validate(s)

    def test_gemini_used_only_after_seeds(self):
        used = {s["id"] for s in content.SEEDS}
        with mock.patch.object(content, "from_gemini", return_value={"id": "new"}) as g:
            self.assertEqual(content.next_scenario(used)["id"], "new")
            g.assert_called_once()


class Stories(unittest.TestCase):
    def test_stories_are_complete(self):
        for s in story.STORIES:
            self.assertEqual(len(s["beats"]), 8)
            self.assertTrue(s["source"] and s["summary_it"])

    def test_stories_run_first(self):
        self.assertEqual(main.next_story(set())["id"], story.STORIES[0]["id"])
        self.assertIsNone(main.next_story({s["id"] for s in story.STORIES}))


class Guide(unittest.TestCase):
    def test_caption_chunks_keep_all_words(self):
        text = guide.GUIDES[0]["scenes"][1][0]
        self.assertEqual(" ".join(guide.chunks(text)), text)

    def test_timings_fill_the_scene(self):
        spans = guide.timings(["one two", "three"], 4.0)
        self.assertAlmostEqual(spans[-1][1], 4.0)
        self.assertEqual(spans[0][1], spans[1][0])


class Carousel(unittest.TestCase):
    def test_every_post_fits_instagram(self):
        for c in carousel.CAROUSELS:
            self.assertLessEqual(len(c["slides"]) + 2, 10)
            self.assertTrue(c["source"])

    def test_render_makes_all_slides(self):
        from PIL import Image
        def fake(photo_id, path):
            Image.new("RGB", (800, 1200), (70, 90, 80)).save(path); return path
        c = carousel.CAROUSELS[0]
        ids = list(range(len(c["slides"]) + 2))
        with tempfile.TemporaryDirectory() as d:
            carousel.render(c, ids, d, fake)
            made = sorted(p.name for p in pathlib.Path(d, c["id"]).glob("*.jpg"))
        self.assertEqual(len(made), len(c["slides"]) + 2)


class Footage(unittest.TestCase):
    def test_pick_smallest_sufficient_mp4(self):
        v = {"video_files": [{"file_type": "video/mp4", "height": 720}, {"file_type": "video/mp4", "height": 1920},
                             {"file_type": "video/mp4", "height": 1280}]}
        self.assertEqual(footage.pick_file(v)["height"], 1280)


    def test_pixabay_prefers_vertical_and_largest_file(self):
        wide = {"id": 1, "duration": 9, "user": "a", "videos": {"large": {"url": "w", "width": 1920, "height": 1080}}}
        tall = {"id": 2, "duration": 9, "user": "b", "videos": {"medium": {"url": "m", "width": 720, "height": 1280},
                                                              "large": {"url": "t", "width": 1080, "height": 1920}}}
        short = {"id": 3, "duration": 2, "user": "c", "videos": {"large": {"url": "s", "width": 1080, "height": 1920}}}
        response = mock.Mock(json=lambda: {"hits": [wide, tall, short]})
        with mock.patch.dict(os.environ, {"PIXABAY_API_KEY": "k"}), mock.patch.object(footage.requests, "get", return_value=response):
            found = footage.search("forest")
        self.assertEqual([x[1] for x in found], [2, 1])
        self.assertEqual(found[0][2], "t")


    def test_off_topic_tags_rejected(self):
        self.assertTrue(footage.relevant("sea waves", "ocean, sea, waves, blue"))
        self.assertFalse(footage.relevant("cougar", "lipstick, makeup, cougar"))
        self.assertFalse(footage.relevant("cougar", "forest, trees"))

    def test_mood_replaces_off_topic_beat(self):
        hits = {"cougar": [("p", 1, "u", "a", "lipstick, beauty")], "forest": [("p", 2, "v", "b", "forest, trees")]}
        with mock.patch.object(footage, "search", side_effect=lambda q: hits[q]), \
             mock.patch.object(footage, "download"), mock.patch.object(footage, "brightness", return_value=90), \
             mock.patch.dict(os.environ, {"PIXABAY_API_KEY": "k"}):
            clips, ids, _, log = footage.fetch_each(["cougar"], ["forest"], set(), tempfile.gettempdir())
        self.assertEqual(ids, [2])
        self.assertIn("cougar -> forest", log[0])


class Approval(unittest.TestCase):
    def state(self):
        return {"used_ids": [], "used_videos": [], "pending": {"a": {"tag": "reel-a", "url": "u", "caption": "c", "created": 0}}}

    def run_update(self, sender, data, ig=None):
        tg, state = mock.Mock(chat="42"), self.state()
        update = {"callback_query": {"id": "1", "from": {"id": sender}, "data": data}}
        with mock.patch.object(main, "save"), mock.patch.object(main, "gh"):
            main.handle(update, state, tg, lambda: ig)
        return tg, state

    def test_stranger_cannot_publish(self):
        ig = mock.Mock()
        _, state = self.run_update(7, "ok:a", ig)
        ig.publish.assert_not_called()
        self.assertIn("a", state["pending"])

    def test_owner_publishes(self):
        ig = mock.Mock(); ig.publish.return_value = "m"
        _, state = self.run_update(42, "ok:a", ig)
        ig.publish.assert_called_once_with("u", "c")
        self.assertEqual(state["pending"], {})

    def test_failed_publish_stays_pending(self):
        ig = mock.Mock(); ig.publish.side_effect = RuntimeError("boom")
        tg, state = self.run_update(42, "ok:a", ig)
        self.assertIn("a", state["pending"])
        tg.say.assert_called_once()


class Publish(unittest.TestCase):
    def test_reel_flow(self):
        ok = lambda p: mock.Mock(ok=True, json=lambda: p)
        with mock.patch.object(channels.requests, "post", side_effect=[ok({"id": "c"}), ok({"id": "m"})]) as post, \
             mock.patch.object(channels.requests, "get", side_effect=[ok({"status_code": "IN_PROGRESS"}), ok({"status_code": "FINISHED"})]):
            self.assertEqual(channels.Instagram(sleep=lambda s: None).publish("https://v", "t"), "m")
        self.assertEqual(post.call_args_list[0].kwargs["json"]["media_type"], "REELS")
        self.assertEqual(post.call_args_list[1].kwargs["json"]["creation_id"], "c")


if __name__ == "__main__":
    unittest.main()
