"""Photo carousels: real stock photos with short, sourced survival rules."""
import glob
import io
import json
import os
import pathlib
import time

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

W, H = 1080, 1350
PIXABAY = "https://pixabay.com/api/"
PAPER, AMBER, INK = (250, 246, 236), (246, 178, 44), (14, 18, 16)
BLOCK = ("mushroom", "lipstick", "fashion", "model", "woman", "girl", "wedding", "toy", "cartoon", "illustration")
TAGS = "#survival #bushcraft #wilderness #outdoors #hiking"

CAROUSELS = [
 {"id": "run-or-not", "source": "U.S. National Park Service; Joint Base Elmendorf-Richardson", "end": "wilderness forest|mountain forest",
  "cover": ("One of these you run from. The other, you never do.", "Mountain lion or moose: know the difference", "moose|cougar"),
  "slides": [("Mountain lion: don't run.", "Keep watching it and back away slowly.", "cougar|mountain lion|puma"),
             ("Get big and loud.", "Raise your arms, wave, shout, throw rocks toward it.", "hiker arms raised|mountain trail hiker"),
             ("If it attacks, fight back.", "Rocks, sticks, a jacket, your hands.", "cougar|wooden sticks|rocks"),
             ("Moose: run if you can.", "Get behind something solid, like a tree.", "moose|big tree trunk"),
             ("Know the warning signs.", "Ears back, raised neck hair, licking lips: back away.", "moose close up|bull moose"),
             ("Knocked down?", "Curl up, cover your head, stay still until it leaves.", "moose forest|moose")]},
 {"id": "bears", "source": "U.S. National Park Service", "end": "bear forest|wilderness mountains",
  "cover": ("Never run from a bear.", "What to do instead, from the U.S. National Park Service", "grizzly bear|bear"),
  "slides": [("Talk calmly.", "So the bear knows you're human. Stay still.", "bear forest|bear looking"),
             ("Don't run.", "Bears can outrun you, and they chase what flees.", "brown bear running|brown bear"),
             ("Don't climb a tree.", "Grizzlies and black bears can both climb.", "bear climbing tree|black bear tree"),
             ("Back away sideways.", "Move slowly and leave the bear an escape route.", "bear walking|bear trail"),
             ("Grizzly attack: play dead.", "Flat on your stomach, hands behind your neck, pack on.", "grizzly|brown bear"),
             ("Black bear attack: fight back.", "Don't play dead. Get to safety, or aim for the face and muzzle.", "black bear")]},
 {"id": "lightning", "source": "U.S. National Weather Service", "end": "storm clouds mountains|dark clouds",
  "cover": ("That tree could be the worst place to stand.", "7 rules when a storm catches you outside", "lone tree storm|lightning tree|lone tree"),
  "slides": [("Hear thunder? Move.", "If you can hear it, lightning is close enough to reach you.", "lightning strike|lightning storm"),
             ("Get off high ground.", "Leave ridges, hills and peaks immediately.", "mountain ridge hiker|mountain ridge"),
             ("Never use a lone tree.", "An isolated tree is not shelter.", "lone tree field|lone tree"),
             ("Don't lie flat.", "It doesn't make you safe.", "muddy trail rain|rain ground"),
             ("Skip the overhang.", "A cliff or rocky overhang is not shelter.", "rock overhang|cave rock|cliff"),
             ("Move away from water.", "Leave ponds and lakes right away.", "lake storm clouds|dark lake"),
             ("Get fully inside.", "A building or hard-top car. Wait 30 minutes after the last thunder.", "cabin rain|mountain hut|car rain")]},
 {"id": "rip-current", "source": "NOAA", "end": "beach waves|ocean sunset",
  "cover": ("Swimming back to shore is the mistake.", "What to do in a rip current", "ocean waves beach|beach waves"),
  "slides": [("Stay calm.", "It pulls you out, not under.", "ocean water|sea surface"),
             ("Don't fight it.", "Swimming against it only wears you out.", "rough sea|big waves"),
             ("Float.", "Save your energy.", "floating in water|calm water"),
             ("Strong swimmer? Go sideways.", "Swim parallel to shore, then angle back.", "coastline aerial|beach aerial"),
             ("Wave and yell.", "Get the attention of lifeguards or people on shore.", "lifeguard tower|lifeguard"),
             ("See someone in trouble?", "Call for help and throw something that floats. Don't go in yourself.", "life ring|lifebuoy")]},
 {"id": "water", "source": "CDC", "end": "mountain lake|waterfall",
  "cover": ("Clear water can still make you sick.", "6 rules for drinking safely in the wild", "clear stream|clear water stones|mountain stream"),
  "slides": [("Cloudy? Clear it first.", "Filter it through clean cloth, or let it settle.", "muddy river|muddy water"),
             ("Boil it hard.", "A rolling boil for 1 full minute.", "boiling water|pot campfire|kettle campfire"),
             ("Up high? Go longer.", "Above 6,500 ft (2,000 m), boil for 3 minutes.", "camping mountain stove|snowy mountain camp"),
             ("No fire? Use the sun.", "Clear plastic bottle: 6 hours of sun, 2 days if cloudy.", "plastic bottle water|water bottle sun"),
             ("Keep it clean.", "Let it cool. Store it in a clean, covered container.", "canteen|water bottle camping|thermos"),
             ("Boiling can't fix everything.", "Fuel and toxic chemicals stay. Find another source.", "polluted water|oil water|polluted river")]},
 {"id": "cold", "source": "CDC / NIOSH", "end": "snow forest|winter mountains",
  "cover": ("Stopped shivering? That's a bad sign.", "How to spot hypothermia", "blizzard|snow storm hiker|snowstorm"),
  "slides": [("Early signs.", "Shivering, fatigue, poor coordination, confusion.", "winter hiker|hiker snow"),
             ("Late signs.", "Shivering stops, skin turns bluish, breathing slows.", "ice frozen|frozen forest"),
             ("Get medical help.", "Call for help right away.", "mountain rescue|rescue snow"),
             ("Get out of the cold.", "Move them to a warm indoor space or shelter.", "cabin snow|mountain hut snow"),
             ("Take off wet clothes.", "Then rewarm them, skin to skin if needed.", "wool blanket|blanket"),
             ("Warm drinks, no alcohol.", "Only if they're awake and alert.", "hot tea|thermos cup|hot drink")]},
 {"id": "lost", "source": "U.S. National Park Service", "end": "forest path|mountain valley",
  "cover": ("Lost? Moving can make you harder to find.", "What to do when you lose the trail", "foggy forest|lost forest"),
  "slides": [("Stop.", "Check your map, GPS or landmarks.", "map hiking|map compass"),
             ("Call for help if you can.", "Give your location, landmarks and clothing colors.", "phone mountain|smartphone hiking"),
             ("Stay put.", "Move only if your life is in immediate danger.", "hiker resting|hiker sitting"),
             ("Get shelter, add layers.", "Protect yourself from sun, rain or snow.", "tent forest|tarp camp|camping rain"),
             ("Whistle three times.", "Pause, then repeat. It saves more energy than yelling.", "whistle|mountain valley"),
             ("Be seen from above.", "Arrange rocks or your shelter so aircraft can spot it.", "rescue helicopter|helicopter mountains")]},
 {"id": "shelter", "source": "Wilderness Awareness School; Outdoor Life", "end": "forest morning|autumn forest",
  "cover": ("No tent? The forest floor can keep you warm.", "How to build a debris shelter", "bushcraft shelter|forest shelter|autumn forest floor"),
  "slides": [("Pick a dry spot.", "Near lots of leaves. Avoid low ground and standing dead trees.", "forest clearing|fallen leaves forest"),
             ("Add a long, strong pole.", "One end on a stump at hip height, one on the ground.", "fallen tree|log forest"),
             ("Lean sticks on both sides.", "Close together, with a door at the high end.", "branches pile|sticks forest|wooden sticks"),
             ("Pile on leaves.", "Two feet thick, more if rain is likely.", "pile of leaves|leaf pile"),
             ("Stuff the inside too.", "Packed dry debris insulates you from below.", "dry leaves|leaf litter"),
             ("Keep fire away.", "Leaf shelters burn easily. Stay well downwind.", "campfire night|campfire")]},
 {"id": "north", "source": "EarthSky; Birmingham Scouts", "end": "milky way|starry sky",
  "cover": ("No compass? The sky still knows the way.", "Find direction by day and by night", "milky way mountains|starry night"),
  "slides": [("By day: use a stick.", "Stand a straight stick upright in the sun.", "stick shadow|wooden stick ground"),
             ("Mark the shadow tip.", "Place a stone at the very end of the shadow.", "stone ground|pebbles"),
             ("Wait at least 15 minutes.", "Mark the new tip with a second stone.", "sun dial|sundial|shadow"),
             ("First is west, second is east.", "A line between the stones runs west to east.", "compass|old compass"),
             ("By night: find the Big Dipper.", "Look for it in the northern sky.", "big dipper|night sky stars"),
             ("Follow the Pointers.", "The bowl's two outer stars lead to Polaris, the North Star.", "north star|star trails")]},
 {"id": "signal", "source": "U.S. National Park Service; Popular Science", "end": "plane sky mountains|mountain valley",
  "cover": ("A mirror flash can reach 7 miles on a clear day.", "How to get spotted by rescuers", "small plane mountains|plane sky|sun reflection"),
  "slides": [("Three whistle blasts.", "Pause and repeat. It saves your voice.", "whistle|hiker mountain"),
             ("Flash a light.", "Three quick, three slow, three quick. Use it sparingly.", "flashlight night|headlamp|torch night"),
             ("Aim a mirror.", "Make a V with two fingers around the target.", "hand mirror|small mirror"),
             ("Flash it three times.", "Rock the mirror so the light hits the V.", "sun flare|sun reflection"),
             ("Make a ground signal.", "Arrange rocks or lay out your shelter in a clear shape.", "stones arranged|rocks mountain"),
             ("Then save your energy.", "Stay warm, stay put, and wait.", "campfire night|camp night")]},
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
    """One Pixabay search, paced to stay under the rate limit."""
    time.sleep(0.8)
    r = requests.get(PIXABAY, timeout=30, params={"key": os.environ["PIXABAY_API_KEY"], "q": query, "image_type": "photo",
                     "orientation": "vertical", "safesearch": "true", "per_page": 20, "min_height": 1200})
    r.raise_for_status()
    return r.json().get("hits", [])


def by_id(photo_id, path):
    time.sleep(0.8)
    r = requests.get(PIXABAY, timeout=30, params={"key": os.environ["PIXABAY_API_KEY"], "id": photo_id})
    r.raise_for_status()
    data = requests.get(r.json()["hits"][0]["largeImageURL"], timeout=60)
    data.raise_for_status()
    path.write_bytes(data.content)
    return path


def rows(c):
    return [(item[0], item[2]) for item in [c["cover"], *c["slides"]]] + [("End", c["end"])]


def sheet(c, out, per_row=6):
    """Contact sheet of candidates, so a person can pick the photo that fits each slide."""
    cell_w, cell_h, side = 230, 340, 150
    data = rows(c)
    img = Image.new("RGB", (side + cell_w * per_row, cell_h * len(data)), (20, 20, 20))
    d = ImageDraw.Draw(img); f = font(22); key = {}
    for r, (title, queries) in enumerate(data):
        for i, row in enumerate(wrap(d, title, f, side - 12)[:5]):
            d.text((6, cell_h * r + 8 + i * 26), row, font=f, fill=PAPER)
        hits, seen = [], set()
        parts = queries.split("|")
        found = [search(q) for q in parts]
        for i in range(per_row):
            for lst in found:
                if i < len(lst) and lst[i]["id"] not in seen and not any(b in lst[i].get("tags", "").lower() for b in BLOCK):
                    seen.add(lst[i]["id"]); hits.append(lst[i])
        for col, hit in enumerate(hits[:per_row]):
            pic = Image.open(io.BytesIO(requests.get(hit["webformatURL"], timeout=30).content)).convert("RGB")
            x, y = side + col * cell_w, cell_h * r
            img.paste(ImageOps.fit(pic, (cell_w - 6, cell_h - 6)), (x, y))
            label = f"{r}{'abcdef'[col]}"
            d.rectangle((x, y, x + 62, y + 34), fill=INK)
            d.text((x + 6, y + 4), label, font=f, fill=AMBER)
            key[label] = hit["id"]
    img.save(pathlib.Path(out) / f"{c['id']}.jpg", quality=80)
    return key


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


def render(c, ids, out, fetch=by_id):
    """ids: one chosen photo per row of the carousel, cover first and end last."""
    out = pathlib.Path(out) / c["id"]; out.mkdir(parents=True, exist_ok=True)
    items = [c["cover"], *c["slides"]]
    total = len(items) + 1
    assert len(ids) == total
    for n, (item, photo_id) in enumerate(zip(items, ids), 1):
        path = fetch(photo_id, out / f"source{n}.jpg")
        slide(path, item[0], item[1], n, total, out / f"{n:02d}.jpg", cover=n == 1)
        path.unlink()
    path = fetch(ids[-1], out / "source_end.jpg")
    finish(c, path, total, out / f"{total:02d}.jpg")
    path.unlink()
    (out / "caption.txt").write_text(caption(c), encoding="utf-8")
