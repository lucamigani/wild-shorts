"""Stock footage lookup. Uses Pixabay when its key is set, otherwise Pexels."""
import os
import pathlib
import subprocess

import requests

PEXELS = "https://api.pexels.com/v1/videos/search"
PIXABAY = "https://pixabay.com/api/videos/"
REJECT = {"woman", "man", "girl", "boy", "people", "person", "model", "fashion", "makeup", "lipstick", "cosmetic",
          "beauty", "business", "office", "city", "car", "helicopter", "wind turbine", "horse", "jogging", "runner"}
MIN_BRIGHTNESS = 28


def pick_file(video):
    files = [f for f in video.get("video_files", [])
             if f.get("file_type") == "video/mp4" and (f.get("height") or 0) >= 1280]
    return min(files, key=lambda f: f["height"], default=None)


def pick_pixabay(hit):
    files = [f for f in hit.get("videos", {}).values() if f.get("url") and (f.get("height") or 0) >= 720]
    return max(files, key=lambda f: f["height"], default=None)


def search_pixabay(query):
    r = requests.get(PIXABAY, timeout=30, params={"key": os.environ["PIXABAY_API_KEY"], "q": query[:100],
                     "video_type": "film", "safesearch": "true", "per_page": 30})
    r.raise_for_status()
    hits = [h for h in r.json().get("hits", []) if h.get("duration", 0) >= 4]
    # Vertical clips need no heavy crop, so they come first.
    hits.sort(key=lambda h: (pick_pixabay(h) or {}).get("width", 1) > (pick_pixabay(h) or {}).get("height", 1))
    return [("pixabay", h["id"], pick_pixabay(h)["url"], h.get("user", "Pixabay"), h.get("tags", "").lower())
            for h in hits if pick_pixabay(h)]


def search_pexels(query):
    r = requests.get(PEXELS, headers={"Authorization": os.environ["PEXELS_API_KEY"]}, timeout=30, params={
        "query": query, "orientation": "portrait", "per_page": 15, "min_duration": 4})
    r.raise_for_status()
    found = [(v, pick_file(v)) for v in r.json().get("videos", [])]
    return [("pexels", v["id"], f["link"], v["user"]["name"], "") for v, f in found if f]


def search(query):
    return search_pixabay(query) if os.environ.get("PIXABAY_API_KEY") else search_pexels(query)


def credit(names):
    site = "Pixabay" if os.environ.get("PIXABAY_API_KEY") else "Pexels"
    return "Video: " + ", ".join(dict.fromkeys(names)) + f" on {site}"


def download(url, path):
    with requests.get(url, stream=True, timeout=120) as d:
        d.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in d.iter_content(1 << 20):
                fh.write(chunk)


def relevant(query, tags):
    """Tags must contain every query word and none of the off-topic words."""
    words = [w.rstrip("s") for w in query.lower().split()]
    return all(w in tags for w in words) and not any(r in tags for r in REJECT)


def brightness(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "0.7", "-i", str(path), "-frames:v", "1",
                          "-vf", "scale=32:32,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return sum(raw) / len(raw) if raw else 0


def choose(query, used, path, strict=True):
    tried = 0
    for _, video_id, url, user, tags in search(query):
        if video_id in used or (strict and not relevant(query, tags)):
            continue
        tried += 1
        download(url, path)
        if brightness(path) >= MIN_BRIGHTNESS:
            return video_id, user, tags
        used.add(video_id)
        if tried == 5:
            break
    return None


def fetch_each(queries, moods, used, out, strict=True):
    """One distinct, on-topic clip per query. Mood queries replace off-topic results."""
    used = set(used)
    clips, ids, names, log = [], [], [], []
    for n, query in enumerate(queries):
        path = pathlib.Path(out) / f"source{n}.mp4"
        for attempt in [query, *moods]:
            pick = choose(attempt, used, path, strict)
            if pick:
                used.add(pick[0]); clips.append(path); ids.append(pick[0]); names.append(pick[1])
                log.append(f"{query} -> {attempt}: {pick[2]}")
                break
        else:
            if clips:
                clips.append(clips[-1]); log.append(f"{query} -> clip precedente")
    if len(clips) != len(queries):
        raise RuntimeError(f"Not enough footage for {queries}")
    return clips, ids, credit(names), log


def fetch(terms, used, out, count=3):
    """Quiz videos: up to `count` clips across the given terms."""
    queries = (list(terms) * count)[:count]
    return fetch_each(queries, [], used, out, strict=False)[:3]
