"""Cinematic mini-stories: real footage, fast cuts, word-by-word text, tense sound."""
import pathlib
import subprocess

from PIL import Image, ImageDraw

from .render import ENC, H, W, font, wrap

BEAT = 2.3
AMBER, WHITE, BLACK = (255, 190, 50, 255), (255, 255, 255, 255), (0, 0, 0, 255)

STORIES = [
 {"id": "rip-current", "source": "NOAA", "tag": "Don't fight it.", "mood": ["ocean waves", "sea", "ocean"],
  "summary_it": "Corrente di risacca: non lottare, galleggia, nuota parallelo alla riva, chiedi aiuto.",
  "beats": [("The water looks calm.", "calm sea"), ("Then the shore moves away.", "waves aerial"),
            ("You swim back. Hard.", "sea waves"), ("That's how you get worn out.", "rough sea"),
            ("Don't fight it.", "stormy sea"), ("Float. Save your energy.", "water surface"),
            ("Strong swimmer? Go parallel to shore.", "coast aerial"), ("Wave and yell for help.", "lifeguard")]},
 {"id": "mountain-lion", "source": "U.S. National Park Service", "tag": "Do not run.",
  "mood": ["dark forest", "forest fog", "forest"],
  "summary_it": "Puma: non correre, sembra più grande, indietreggia guardandolo, se attacca reagisci.",
  "beats": [("Something is watching you.", "dark forest"), ("A mountain lion.", "cougar"),
            ("Every instinct says run.", "forest fog"), ("Do not run.", "puma"),
            ("Get big. Wave your arms.", "mountain wilderness"), ("Shout. Throw rocks.", "rocks forest"),
            ("Back away. Keep watching it.", "forest path"), ("If it attacks, fight back.", "cougar")]},
 {"id": "lightning-ridge", "source": "U.S. National Weather Service", "tag": "That tree can kill you.",
  "mood": ["storm clouds", "dark clouds", "lightning"],
  "summary_it": "Temporale in cresta: scendi subito, mai sotto un albero isolato, cerca un edificio o un'auto chiusa.",
  "beats": [("You're on a ridge.", "mountain ridge"), ("Thunder.", "thunderstorm"),
            ("One tree. Right there.", "lone tree"), ("Stay away from it.", "lightning"),
            ("Get off the ridge. Now.", "mountain fog"), ("Don't lie flat.", "rain rocks"),
            ("Move away from water.", "lake storm"), ("Get to a building or a closed car.", "rain cabin")]},
 {"id": "moose-charge", "source": "U.S. Air Force, Joint Base Elmendorf-Richardson", "tag": "Forget the bear rules.",
  "mood": ["pine forest", "forest fog", "forest"],
  "summary_it": "Alce alla carica: corri, mettiti dietro qualcosa di solido; se cadi, raggomitolati e proteggi la testa.",
  "beats": [("It looks calm.", "moose"), ("Then its ears pin back.", "moose"), ("It charges.", "moose"),
            ("Forget the bear rules.", "pine forest"), ("Run if you can.", "forest path"),
            ("Get behind a solid tree.", "tree trunk"), ("Knocked down? Curl up.", "forest floor"),
            ("Protect your head. Stay still.", "forest fog")]},
 {"id": "stream-water", "source": "CDC", "tag": "Looks safe. May not be.",
  "mood": ["mountain stream", "river", "campfire"],
  "summary_it": "Acqua: filtra se torbida, bollore pieno 1 minuto, non rimuove carburante o sostanze chimiche.",
  "beats": [("Day two without water.", "dry mountain"), ("Then you find a stream.", "mountain stream"),
            ("It looks safe.", "clear stream"), ("Cloudy? Filter it through cloth.", "river"),
            ("Bring it to a rolling boil.", "boiling water"), ("One full minute.", "campfire"),
            ("High altitude? Three minutes.", "snowy mountain"), ("Boiling can't remove chemicals.", "campfire night")]},
 {"id": "hemlock", "source": "Penn State Extension", "tag": "Check the stem.",
  "mood": ["meadow", "wild flowers", "field"],
  "summary_it": "Cicuta: fusto liscio con macchie viola. Carota selvatica: fusto molto peloso. Se hai dubbi non toccare.",
  "beats": [("White flowers in a field.", "white wildflowers"), ("Looks like wild carrot.", "wild carrot"),
            ("Check the stem.", "plant stem"), ("Densely hairy: wild carrot.", "meadow"),
            ("Smooth, purple spots: poison hemlock.", "hemlock"), ("It's poisonous to people.", "dark meadow"),
            ("Not 100% sure?", "field dusk"), ("Don't touch it. Don't eat it.", "forest edge")]},
]


def split_words(d, text, f, width):
    return wrap(d, text, f, width)


def overlays(text, out, index):
    """One transparent PNG per word count, so words land one at a time."""
    words = text.split()
    size = 112 if len(text) < 26 else 92
    f = font(size)
    probe = ImageDraw.Draw(Image.new("RGBA", (W, H)))
    rows = split_words(probe, text, f, 930)
    paths = []
    for shown in range(1, len(words) + 1):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        y, seen = 760 - len(rows) * size * 0.62, 0
        for row in rows:
            parts = row.split()
            full = d.textlength(row, font=f)
            x = (W - full) / 2
            for word in parts:
                seen += 1
                if seen <= shown:
                    fill = AMBER if seen == len(words) else WHITE
                    d.text((x, y), word, font=f, fill=fill, stroke_width=9, stroke_fill=BLACK)
                x += d.textlength(word + " ", font=f)
            y += size * 1.24
        path = pathlib.Path(out) / f"t{index}_{shown}.png"
        img.save(path); paths.append(path)
    return paths


def beat_clip(clip, text, index, out):
    target = pathlib.Path(out) / f"beat{index}.mp4"
    tmp = target.with_suffix(".tmp.mp4")
    pics = overlays(text, out, index)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", "0.5", "-i", str(clip)]
    for p in pics:
        cmd += ["-i", str(p)]
    direction = "t" if index % 2 else f"{BEAT}-t"
    graph = [f"[0:v]scale=1210:2150:force_original_aspect_ratio=increase,crop=1210:2150,"
             f"crop={W}:{H}:x='(iw-ow)*({direction})/{BEAT}':y='(ih-oh)*({direction})/{BEAT}',"
             "eq=contrast=1.16:saturation=0.82:brightness=-0.05,vignette=PI/4.5,fps=30[v0]"]
    step = min(0.28, (BEAT - 1.1) / max(1, len(pics)))
    for i in range(len(pics)):
        graph.append(f"[v{i}][{i + 1}:v]overlay=0:0:enable='gte(t,{0.1 + i * step:.2f})'[v{i + 1}]")
    subprocess.run(cmd + ["-filter_complex", ";".join(graph), "-map", f"[v{len(pics)}]", "-t", str(BEAT),
                          "-an", *ENC, str(tmp)], check=True)
    tmp.rename(target)
    return target


def sound(total, turn):
    hits = "+".join(f"between(t,{i * BEAT},{i * BEAT + 0.3})*sin(2*PI*62*t)*exp(-14*(t-{i * BEAT}))*0.75"
                    for i in range(int(total / BEAT)))
    heart = f"if(lt(t,{turn}),sin(2*PI*52*t)*exp(-11*mod(t,0.72))*0.7,0)"
    return (f"anoisesrc=d={total}:c=brown:a=0.5:r=44100,lowpass=f=520,highpass=f=60,tremolo=f=0.3:d=0.6[w];"
            f"aevalsrc='{heart}+{hits}':d={total}:s=44100[p];[w][p]amix=inputs=2:normalize=0,"
            f"alimiter=limit=0.9,afade=t=out:st={total - 0.5}:d=0.5[a]")


def render(story, clips, out, target):
    out = pathlib.Path(out)
    parts = [beat_clip(c, beat[0], i, out) for i, (c, beat) in enumerate(zip(clips, story["beats"]))]
    listing = out / "beats.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    silent = out / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", str(silent)], check=True)
    total = BEAT * len(parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-filter_complex", sound(total, BEAT * 4),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", "-shortest", str(target)], check=True)
    return target


def caption(story, credit):
    return (f"{story['tag']} Save this and share it with whoever you hike with.\n\n"
            f"Source: {story['source']}. General safety information; follow local authorities.\n{credit}\n\n"
            "#survival #wilderness #outdoors #nature #hiking")
