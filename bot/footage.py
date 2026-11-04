"""Stock footage lookup. Uses Pixabay when its key is set, otherwise Pexels."""
import os
import pathlib

import requests

PEXELS = "https://api.pexels.com/v1/videos/search"
PIXABAY = "https://pixabay.com/api/videos/"


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
    return [("pixabay", h["id"], pick_pixabay(h)["url"], h.get("user", "Pixabay")) for h in hits if pick_pixabay(h)]


def search_pexels(query):
    r = requests.get(PEXELS, headers={"Authorization": os.environ["PEXELS_API_KEY"]}, timeout=30, params={
        "query": query, "orientation": "portrait", "per_page": 15, "min_duration": 4})
    r.raise_for_status()
    found = [(v, pick_file(v)) for v in r.json().get("videos", [])]
    return [("pexels", v["id"], f["link"], v["user"]["name"]) for v, f in found if f]


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


def fetch_each(queries, used, out):
    """One distinct clip per query. A query with no result reuses the previous clip."""
    clips, ids, names = [], [], []
    for n, query in enumerate(queries):
        for _, video_id, url, user in search(query):
            if video_id in used or video_id in ids:
                continue
            path = pathlib.Path(out) / f"source{n}.mp4"
            download(url, path)
            clips.append(path); ids.append(video_id); names.append(user)
            break
        else:
            if clips:
                clips.append(clips[-1])
    if len(clips) != len(queries):
        raise RuntimeError(f"Not enough footage for {queries}")
    return clips, ids, credit(names)


def fetch(terms, used, out, count=3):
    """Quiz videos: up to `count` clips across the given terms."""
    queries = (list(terms) * count)[:count]
    return fetch_each(queries, used, out)
