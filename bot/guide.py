"""Narrated how-to videos: AI voice, AI cinematic stills with camera motion, word-timed captions."""
import base64
import math
import os
import pathlib
import subprocess
import time
import urllib.request
import wave

import requests
from PIL import Image, ImageDraw

from .render import ENC, H, W, font, wrap

SR = 24000
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FLUX = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/@cf/black-forest-labs/flux-1-schnell"
LOOK = ("Photorealistic cinematic film still, shot on 35mm, dramatic natural light, shallow depth of field, "
        "rich detail, vertical composition with the subject centered, no text, no watermark, no faces. ")
GAP = 0.12

GUIDES = [
 {"id": "debris-hut", "voice": "am_onyx", "source": "Wilderness Awareness School; Outdoor Life",
  "caption": "No tent, no problem: a shelter made from what's on the forest floor. Save this for your next trip.\n\n"
             "Always tell someone where you're going. Keep fires well away from leaf shelters. Images are AI-generated.\n\n"
             "#survival #bushcraft #outdoors #wilderness #shelter",
  "summary_it": "Rifugio di detriti: palo di colmo, costole ravvicinate, almeno 60 cm di foglie, interno riempito.",
  "scenes": [
   ("It's getting dark, it's freezing, and you have no tent. The forest floor is all you need.",
    "A lone hiker seen from behind in a dark autumn forest at dusk, cold mist, fallen leaves everywhere"),
   ("First, find a dry spot near plenty of leaves. Avoid low ground and standing dead trees.",
    "Thick dry autumn leaves covering a raised forest clearing, golden hour light through bare trees"),
   ("Grab a long, strong pole. Rest one end on a stump at hip height, and the other on the ground.",
    "Gloved hands placing a long thick wooden pole onto a tree stump in a forest, the other end on the ground"),
   ("Lean sticks along both sides, close together. Leave a door at the high end.",
    "A triangular frame of many sticks leaning against a long wooden ridgepole in a forest, like a skeleton tent"),
   ("Now pile on leaves. Two feet thick. It will look like too much. It isn't.",
    "A low dome-shaped shelter completely covered with a very thick layer of autumn leaves in a forest"),
   ("Here's what most people miss. Stuff the inside too. Leaves under you matter as much as leaves above you.",
    "View from inside a small dark leaf shelter, thick dry leaves packed all around, warm light at the entrance"),
   ("Crawl in feet first, and pull a pile of leaves in behind you to seal the door.",
    "Night in a frosty forest, a leaf-covered shelter with a small sealed entrance, moonlight and mist"),
   ("Save this. Next, how to start a fire when everything is wet.",
    "Close-up of a small flame catching in dry tinder in a rainy forest at night, sparks and raindrops"),
  ]},
]


def narrate(text, voice):
    """Return float samples at SR. The model files are downloaded once per run."""
    import numpy as np
    from kokoro_onnx import Kokoro
    folder = pathlib.Path("models"); folder.mkdir(exist_ok=True)
    for name in ("kokoro-v1.0.int8.onnx", "voices-v1.0.bin"):
        if not (folder / name).exists():
            urllib.request.urlretrieve(MODEL_URL + name, folder / name)
    engine = Kokoro(str(folder / "kokoro-v1.0.int8.onnx"), str(folder / "voices-v1.0.bin"))
    samples, rate = engine.create(text, voice=voice, speed=1.08, lang="en-us")
    assert rate == SR
    return np.asarray(samples)


def picture(prompt, seed, path):
    url = FLUX.format(os.environ["CLOUDFLARE_ACCOUNT_ID"])
    head = {"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}"}
    for attempt in range(3):
        r = requests.post(url, headers=head, timeout=120, json={"prompt": LOOK + prompt, "steps": 8})
        if r.ok:
            path.write_bytes(base64.b64decode(r.json()["result"]["image"]))
            return path
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Cloudflare image failed {r.status_code}: {r.text[:300]}")


def chunks(text, size=3):
    words = text.split()
    groups, group = [], []
    for w in words:
        group.append(w)
        if len(group) == size or w[-1] in ".?!,":
            groups.append(" ".join(group)); group = []
    return groups + ([" ".join(group)] if group else [])


def timings(groups, duration):
    total = sum(len(g) + 2 for g in groups)
    start, out = 0.0, []
    for g in groups:
        span = duration * (len(g) + 2) / total
        out.append((start, start + span)); start += span
    return out


def caption_png(text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    f = font(84)
    rows = wrap(d, text.upper(), f, 960)
    y = 1270
    for row in rows:
        d.text((W / 2, y), row, font=f, fill=(255, 225, 90, 255), anchor="ma", stroke_width=9, stroke_fill=(0, 0, 0, 255))
        y += 104
    img.save(path)
    return path


def scene(image, text, duration, index, out):
    out = pathlib.Path(out)
    target = out / f"scene{index}.mp4"; tmp = target.with_suffix(".tmp.mp4")
    groups = chunks(text)
    pngs = [caption_png(g, out / f"c{index}_{i}.png") for i, g in enumerate(groups)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(image)]
    for p in pngs:
        cmd += ["-i", str(p)]
    # Work at double size so the slow camera move stays smooth after scaling down.
    x, y = ("(iw-ow)*t/{D}", "(ih-oh)*t/{D}") if index % 2 else ("(iw-ow)*(1-t/{D})", "(ih-oh)/2")
    move = f"crop=2160:3840:x='{x.format(D=duration)}':y='{y.format(D=duration)}'"
    graph = [f"[0:v]scale=2500:4444:force_original_aspect_ratio=increase,crop=2500:4444,{move},scale={W}:{H},"
             "eq=contrast=1.08:saturation=1.08,vignette=PI/6,format=yuv420p,fps=30[v0]"]
    for i, (a, b) in enumerate(timings(groups, duration)):
        graph.append(f"[v{i}][{i + 1}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{i + 1}]")
    subprocess.run(cmd + ["-filter_complex", ";".join(graph), "-map", f"[v{len(pngs)}]", "-t", f"{duration:.3f}",
                          "-an", *ENC, str(tmp)], check=True)
    tmp.rename(target)
    return target


def render(g, out, target, speak=narrate, draw=picture):
    import numpy as np
    out = pathlib.Path(out)
    gap = np.zeros(int(SR * GAP))
    audio, parts = [], []
    for i, (text, prompt) in enumerate(g["scenes"]):
        voice = speak(text, g["voice"])
        image = draw(prompt, 1000 + i, out / f"image{i}.jpg")
        duration = len(voice) / SR + GAP
        parts.append(scene(image, text, duration, i, out))
        audio += [voice, gap]
    speech = out / "speech.wav"
    with wave.open(str(speech), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(np.concatenate(audio), -1, 1) * 32767).astype("<i2").tobytes())
    listing = out / "scenes.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    silent = out / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", str(silent)], check=True)
    total = sum(len(a) for a in audio) / SR
    mix = (f"anoisesrc=d={total}:c=brown:a=0.25:r=48000,lowpass=f=500,highpass=f=60,tremolo=f=0.2:d=0.5[wind];"
           "[1:a]aresample=48000,highpass=f=70,acompressor=threshold=0.2:ratio=3:makeup=1.5[voice];"
           f"[voice][wind]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,"
           f"afade=t=out:st={max(0, total - 0.4):.2f}:d=0.4[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(speech), "-filter_complex", mix,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", "-shortest", str(target)], check=True)
    return target
