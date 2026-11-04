"""Photo carousels: real stock photos with short, sourced survival rules."""
import glob
import os
import pathlib

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from .footage import REJECT, relevant

W, H = 1080, 1350
PIXABAY = "https://pixabay.com/api/"
PAPER, AMBER, INK = (250, 246, 236), (246, 178, 44), (14, 18, 16)
TAGS = "#survival #bushcraft #wilderness #outdoors #hiking"

CAROUSELS = [
 {"id": "water", "source": "CDC", "mood": ["mountain river", "mountain stream", "forest"],
  "cover": ("Clear water can still make you sick.", "6 rules for drinking safely in the wild", "mountain stream"),
  "slides": [("Cloudy? Clear it first.", "Filter it through clean cloth, or let it settle.", "river water"),
             ("Boil it hard.", "A rolling boil for 1 full minute.", "campfire"),
             ("Up high? Go longer.", "Above 6,500 ft (2,000 m), boil for 3 minutes.", "snowy mountain"),
             ("No fire? Use the sun.", "Clear plastic bottle: 6 hours of sun, 2 days if cloudy.", "sunlight forest"),
             ("Keep it clean.", "Let it cool. Store it in a clean, covered container.", "lake"),
             ("Boiling can't fix everything.", "Fuel and toxic chemicals stay. Find another source.", "river rocks")]},
 {"id": "lightning", "source": "U.S. National Weather Service", "mood": ["storm clouds", "dark clouds", "mountain"],
  "cover": ("That tree could be the worst place to stand.", "7 rules when a storm catches you outside", "lone tree"),
  "slides": [("Hear thunder? Move.", "If you can hear it, lightning is close enough to reach you.", "thunderstorm"),
             ("Get off high ground.", "Leave ridges, hills and peaks immediately.", "mountain ridge"),
             ("Never use a lone tree.", "An isolated tree is not shelter.", "lone tree"),
             ("Don't lie flat.", "It doesn't make you safe.", "rain"),
             ("Skip the overhang.", "A cliff or rocky overhang is not shelter.", "cliff"),
             ("Move away from water.", "Leave ponds and lakes right away.", "lake storm"),
             ("Get fully inside.", "A building or hard-top car. Wait 30 minutes after the last thunder.", "cabin")]},
 {"id": "run-or-not", "source": "U.S. National Park Service; Joint Base Elmendorf-Richardson",
  "mood": ["forest", "mountain forest", "wilderness"],
  "cover": ("One of these you run from. The other, you never do.", "Mountain lion or moose: know the difference", "moose"),
  "slides": [("Mountain lion: don't run.", "Keep watching it and back away slowly.", "cougar"),
             ("Get big and loud.", "Raise your arms, wave, shout, throw rocks toward it.", "mountain trail"),
             ("If it attacks, fight back.", "Rocks, sticks, a jacket, your hands.", "rocks forest"),
             ("Moose: run if you can.", "Get behind something solid, like a tree.", "moose"),
             ("Know the warning signs.", "Ears back, raised neck hair, licking lips: back away.", "moose"),
             ("Knocked down?", "Curl up, cover your head, stay still until it leaves.", "forest floor")]},
]


def font(size):
    for pattern in ("/usr/share/fonts/**/LeagueSpartan*Bold*.?tf", "/usr/share/fonts/**/LeagueSpartan*.?tf",
                    "/usr/share/fonts/**/Oswald*Bold*.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        found = sorted(glob.glob(pattern, recursive=True))
        if found:
            return ImageFont.truetype(found[0], size)
    raise FileNotFoundError("No display font")


def wrap(d, text, f, width):
    rows, row = [], ""
    for word in text.split():
        probe = f"{row} {word}".strip()
        if d.textlength(probe, font=f) <= width:
            row = probe
        else:
            rows.append(row); row = word
    return rows + [row]


def search(query):
    r = requests.get(PIXABAY, timeout=30, params={"key": os.environ["PIXABAY_API_KEY"], "q": query, "image_type": "photo",
                     "orientation": "vertical", "safesearch": "true", "per_page": 30, "min_height": 1200})
    r.raise_for_status()
    return r.json().get("hits", [])


def photo(queries, used, path):
    for query in queries:
        for hit in search(query):
            tags = hit.get("tags", "").lower()
            if hit["id"] in used or not relevant(query, tags):
                continue
            data = requests.get(hit["largeImageURL"], timeout=60)
            data.raise_for_status()
            path.write_bytes(data.content)
            used.add(hit["id"])
            return f"{query}: {tags} ({hit.get('user')})"
    raise RuntimeError(f"No photo for {queries}")


def base(path):
    img = ImageOps.fit(Image.open(path).convert("RGB"), (W, H), Image.LANCZOS)
    img = ImageEnhance.Color(img).enhance(1.05)
    shade = Image.new("L", (1, H))
    for y in range(H):
        shade.putpixel((0, y), int(40 + 195 * max(0, (y - H * 0.25) / (H * 0.75)) ** 1.1))
    img.paste(Image.new("RGB", (W, H), INK), mask=shade.resize((W, H)))
    return img


def block(d, rows, f, size, y, fill):
    for row in rows:
        d.text((76, y), row, font=f, fill=fill)
        y += int(size * 1.12)
    return y


def slide(path, title, body, number, total, target, cover=False):
    img = base(path); d = ImageDraw.Draw(img)
    size = 104 if cover else 92
    big, small = font(size), font(46)
    rows, lines = wrap(d, title, big, 930), wrap(d, body, small, 900)
    height = len(rows) * size * 1.12 + 30 + len(lines) * 58
    y = H - 110 - height
    d.rectangle((76, y - 34, 196, y - 24), fill=AMBER)
    y = block(d, rows, big, size, y, PAPER) + 30
    block(d, lines, small, 46, y, AMBER if cover else PAPER)
    d.text((W - 76, H - 56), f"{number}/{total}", font=font(30), fill=PAPER, anchor="rs")
    img.save(target, quality=93)


def finish(c, path, total, target):
    img = base(path); d = ImageDraw.Draw(img)
    f = font(120)
    y = block(d, ["Save this.", "Share it."], f, 120, 700, PAPER) + 40
    src = font(36)
    block(d, wrap(d, f"Source: {c['source']}", src, 900), src, 36, y, AMBER)
    d.text((W - 76, H - 56), f"{total}/{total}", font=font(30), fill=PAPER, anchor="rs")
    img.save(target, quality=93)


def caption(c):
    return (f"{c['cover'][0]} {c['cover'][1]}. Save this for your next trip.\n\n"
            f"Source: {c['source']}. General safety information; follow local authorities.\nPhotos: Pixabay\n\n{TAGS}")


def render(c, out, fetch=photo):
    out = pathlib.Path(out) / c["id"]; out.mkdir(parents=True, exist_ok=True)
    used, log = set(), []
    total = len(c["slides"]) + 2
    pics = []
    for n, item in enumerate([c["cover"], *c["slides"]], 1):
        path = out / f"source{n}.jpg"
        log.append(fetch([item[2], *c["mood"]], used, path))
        slide(path, item[0], item[1], n, total, out / f"{n:02d}.jpg", cover=n == 1)
        pics.append(path)
    last = out / "source_end.jpg"
    log.append(fetch(c["mood"], used, last))
    finish(c, last, total, out / f"{total:02d}.jpg")
    for p in [*pics, last]:
        p.unlink()
    (out / "caption.txt").write_text(caption(c), encoding="utf-8")
    (out / "foto.txt").write_text("\n".join(log), encoding="utf-8")
