"""Usage: python -m bot.main generate | process | preview [count]"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

from . import carousel, content, footage, guide, render, story
from .channels import Instagram, Telegram

STATE = pathlib.Path("state/state.json")
EXPIRY = 7 * 86400


def load():
    return json.loads(STATE.read_text())


def save(state):
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def gh(*args):
    subprocess.run(["gh", *args], check=True)


def keyboard(item_id):
    return json.dumps({"inline_keyboard": [[{"text": "Pubblica", "callback_data": f"ok:{item_id}"},
                                            {"text": "Scarta", "callback_data": f"no:{item_id}"}]]})


def next_story(used):
    return next((s for s in story.STORIES if s["id"] not in used), None)


def make_story(s, used_videos, tmp, target):
    clips, ids, credit, log = footage.fetch_each([b[1] for b in s["beats"]], s["mood"], used_videos, tmp)
    story.render(s, clips, tmp, target)
    return ids, credit, log


def build(tmp, state):
    """Return (id, video, caption, review text, footage ids). Stories come first."""
    video = pathlib.Path(tmp) / "video.mp4"
    s = next_story(set(state["used_ids"]))
    if s:
        ids, credit, _ = make_story(s, set(state["used_videos"]), tmp, video)
        return s["id"], video, story.caption(s, credit), f"{s['summary_it']}\nFonte: {s['source']}", ids
    s = content.next_scenario(set(state["used_ids"]))
    clips, ids, credit = footage.fetch(s["search_terms"], set(state["used_videos"]), tmp)
    render.render(s, clips, tmp, video)
    review = f"Verifica la risposta su una fonte ufficiale prima di pubblicare.\n\n{s['summary_it']}\n\nRisposta: {s['options'][s['correct']]}"
    return s["id"], video, content.caption(s, credit), review, ids


def generate():
    state = load()
    with tempfile.TemporaryDirectory() as tmp:
        item_id, video, text, review, ids = build(tmp, state)
        tag = f"reel-{item_id}"
        gh("release", "create", tag, str(video), "--title", tag, "--notes", "Video in attesa di approvazione", "--latest=false")
        item = {"tag": tag, "caption": text, "created": int(time.time()), "review": review,
                "url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases/download/{tag}/video.mp4"}
        try:
            Telegram().review(item, video, keyboard(item_id))
        except Exception:
            # Without this, the next run would stop on the leftover tag.
            gh("release", "delete", tag, "--cleanup-tag", "--yes")
            raise
    state["used_ids"].append(item_id); state["used_videos"] += ids
    state["pending"][item_id] = item
    save(state)


def handle(update, state, tg, ig_factory=Instagram):
    q = update.get("callback_query")
    if not q:
        return
    # Only the owner's chat may approve anything.
    if str(q.get("from", {}).get("id")) != tg.chat:
        return tg.answer(q["id"], "Non autorizzato")
    action, _, item_id = q.get("data", "").partition(":")
    item = state["pending"].get(item_id)
    if not item:
        return tg.answer(q["id"], "Già gestito")
    if action == "no":
        del state["pending"][item_id]
        save(state)
        gh("release", "delete", item["tag"], "--cleanup-tag", "--yes")
        tg.answer(q["id"], "Scartato")
    elif action == "ok":
        tg.answer(q["id"], "Pubblico...")
        try:
            media = ig_factory().publish(item["url"], item["caption"])
        except Exception as e:
            tg.say(f"Pubblicazione fallita: {e}", reply_markup=keyboard(item_id))
            return
        del state["pending"][item_id]
        save(state)
        tg.say(f"Reel pubblicato ({media}). Video nel messaggio sopra: caricalo a mano su YouTube e TikTok con questo testo:\n\n{item['caption']}")
        gh("release", "delete", item["tag"], "--cleanup-tag", "--yes")


def process():
    state, tg = load(), Telegram()
    updates = tg.updates()
    try:
        for update in updates:
            handle(update, state, tg)
    finally:
        if updates:
            tg.confirm(updates[-1]["update_id"])
    for item_id, item in list(state["pending"].items()):
        if time.time() - item["created"] > EXPIRY:
            del state["pending"][item_id]
            gh("release", "delete", item["tag"], "--cleanup-tag", "--yes")
    save(state)


def preview(count="3"):
    """Render sample videos into previews/ without touching state or publishing."""
    folder = pathlib.Path("previews"); folder.mkdir(exist_ok=True)
    used, credits = set(), []
    for s in story.STORIES[:int(count)]:
        with tempfile.TemporaryDirectory() as tmp:
            ids, credit, log = make_story(s, used, tmp, (folder / f"{s['id']}.mp4").resolve())
        used |= set(ids); credits += [f"{s['id']}: {credit}", *log, ""]
    (folder / "crediti.txt").write_text("\n".join(credits), encoding="utf-8")


def guide_preview(guide_id="debris-hut"):
    folder = pathlib.Path("previews"); folder.mkdir(exist_ok=True)
    g = next(x for x in guide.GUIDES if x["id"] == guide_id)
    with tempfile.TemporaryDirectory() as tmp:
        guide.render(g, tmp, (folder / f"{g['id']}.mp4").resolve())


def carousel_preview():
    chosen = json.loads(pathlib.Path("bot/photos.json").read_text())
    for c in carousel.CAROUSELS:
        if c["id"] in chosen:
            carousel.render(c, chosen[c["id"]], "previews")


def carousel_sheets():
    folder = pathlib.Path("previews"); folder.mkdir(exist_ok=True)
    keys = {c["id"]: carousel.sheet(c, folder) for c in carousel.CAROUSELS}
    (folder / "chiavi.json").write_text(json.dumps(keys, indent=1))


if __name__ == "__main__":
    commands = {"generate": generate, "process": process, "preview": preview, "guide-preview": guide_preview, "carousel-preview": carousel_preview, "carousel-sheets": carousel_sheets}
    commands[sys.argv[1]](*sys.argv[2:])
