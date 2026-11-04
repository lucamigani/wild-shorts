"""Telegram review and Instagram Reels publishing."""
import os
import time

import requests


class Telegram:
    def __init__(self):
        self.base = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
        self.chat = str(os.environ["TELEGRAM_CHAT_ID"])

    def call(self, method, files=None, timeout=60, **data):
        r = requests.post(f"{self.base}/{method}", data=data, files=files, timeout=timeout)
        r.raise_for_status()
        return r.json()["result"]

    def say(self, message, **extra):
        return self.call("sendMessage", chat_id=self.chat, text=message[:4000], **extra)

    def review(self, item, video, keyboard):
        with open(video, "rb") as fh:
            self.call("sendVideo", files={"video": fh}, timeout=180, chat_id=self.chat,
                      caption=item["review"][:1000], reply_markup=keyboard)

    def updates(self):
        return self.call("getUpdates", timeout=30, allowed_updates='["callback_query"]')

    def confirm(self, last_update_id):
        self.call("getUpdates", offset=last_update_id + 1, limit=1)

    def answer(self, callback_id, message):
        self.call("answerCallbackQuery", callback_query_id=callback_id, text=message)


class Instagram:
    def __init__(self, sleep=time.sleep):
        version = os.environ.get("IG_API_VERSION", "v25.0")
        self.base = f"https://graph.instagram.com/{version}"
        self.user = os.environ["IG_USER_ID"]
        self.auth = {"Authorization": f"Bearer {os.environ['IG_ACCESS_TOKEN']}"}
        self.sleep = sleep

    def _json(self, r):
        if not r.ok:
            raise RuntimeError(f"Instagram {r.status_code}: {r.text[:300]}")
        return r.json()

    def publish(self, video_url, text):
        container = self._json(requests.post(f"{self.base}/{self.user}/media", headers=self.auth, timeout=60, json={
            "media_type": "REELS", "video_url": video_url, "caption": text, "share_to_feed": True}))["id"]
        for _ in range(5):  # Meta recommends once per minute, for at most 5 minutes.
            self.sleep(60)
            status = self._json(requests.get(f"{self.base}/{container}", headers=self.auth, timeout=30,
                                             params={"fields": "status_code"}))["status_code"]
            if status == "FINISHED":
                return self._json(requests.post(f"{self.base}/{self.user}/media_publish", headers=self.auth,
                                                timeout=60, json={"creation_id": container}))["id"]
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram container status {status}")
        raise RuntimeError("Instagram processing timed out")
