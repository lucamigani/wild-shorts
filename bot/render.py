"""Three-scene 1080x1920 quiz video: hook, question with countdown, reveal."""
import pathlib
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
HOOK, QUIZ, REVEAL = 3.0, 7.0, 5.0
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30"]
GREEN, CARD, WHITE = (46, 160, 90, 245), (12, 18, 16, 215), (255, 255, 255, 255)


def font(size):
    for f in FONTS:
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, size)
    raise FileNotFoundError("Install fonts-dejavu-core")


def wrap(d, text, f, width):
    lines, line = [], ""
    for word in text.split():
        probe = f"{line} {word}".strip()
        if d.textlength(probe, font=f) <= width:
            line = probe
        else:
            lines.append(line); line = word
    return lines + [line] if line else lines


def text(d, y, value, size, width=900):
    f = font(size)
    for line in wrap(d, value, f, width):
        d.text((W / 2, y), line, font=f, fill=WHITE, anchor="ma", stroke_width=max(4, size // 14),
               stroke_fill=(0, 0, 0, 255))
        y += int(size * 1.22)
    return y


def canvas():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def option(d, y, label, value, fill):
    f = font(46)
    lines = wrap(d, value, f, 730)
    h = max(130, 56 * len(lines) + 54)
    d.rounded_rectangle((70, y, W - 70, y + h), 30, fill=fill)
    d.text((132, y + h / 2), label, font=font(60), fill=WHITE, anchor="mm")
    ty = y + (h - 56 * len(lines)) / 2
    for line in lines:
        d.text((205, ty), line, font=f, fill=WHITE)
        ty += 56
    return y + h + 28


def overlays(s, out):
    out = pathlib.Path(out); paths = {}
    img, d = canvas(); text(d, 650, s["hook"], 86)
    paths["hook"] = out / "hook.png"; img.save(paths["hook"])
    img, d = canvas(); y = text(d, 330, s["question"], 72) + 40
    for label, value in zip("ABC", s["options"]):
        y = option(d, y, label, value, CARD)
    paths["quiz"] = out / "quiz.png"; img.save(paths["quiz"])
    for n in (3, 2, 1):
        img, d = canvas(); text(d, 1340, str(n), 170)
        paths[f"n{n}"] = out / f"n{n}.png"; img.save(paths[f"n{n}"])
    img, d = canvas()
    y = option(d, 400, "ABC"[s["correct"]], s["options"][s["correct"]], GREEN) + 30
    text(d, y, s["explanation"], 54)
    text(d, 1560, "General safety information. Follow local authorities.", 30)
    paths["reveal"] = out / "reveal.png"; img.save(paths["reveal"])
    return paths


def scene(clip, duration, images, target):
    """images: list of (png path, start, end), with None for always visible."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(clip)]
    for path, _, _ in images:
        cmd += ["-i", str(path)]
    graph = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
             "eq=brightness=-0.08:saturation=1.1,fps=30[v0]"]
    last = "v0"
    for i, (_, start, end) in enumerate(images, 1):
        enable = f":enable='between(t,{start},{end})'" if start is not None else ""
        graph.append(f"[{last}][{i}:v]overlay=0:0{enable}[v{i}]")
        last = f"v{i}"
    tmp = pathlib.Path(target).with_suffix(".tmp.mp4")
    subprocess.run(cmd + ["-filter_complex", ";".join(graph), "-map", f"[{last}]", "-t", str(duration),
                          "-an", *ENC, str(tmp)], check=True)
    tmp.rename(target)


def render(s, clips, out, target):
    out = pathlib.Path(out); o = overlays(s, out)
    scenes = [out / "s1.mp4", out / "s2.mp4", out / "s3.mp4"]
    scene(clips[0], HOOK, [(o["hook"], None, None)], scenes[0])
    scene(clips[1], QUIZ, [(o["quiz"], None, None), (o["n3"], 4, 5), (o["n2"], 5, 6), (o["n1"], 6, 7)], scenes[1])
    scene(clips[2], REVEAL, [(o["reveal"], None, None)], scenes[2])
    listing = out / "list.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in scenes))
    silent = out / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", str(silent)], check=True)
    total = HOOK + QUIZ + REVEAL
    # Original generated wind bed, so there is no music licensing to manage.
    audio = (f"anoisesrc=d={total}:c=brown:a=0.7:r=44100,lowpass=f=650,highpass=f=70,"
             f"tremolo=f=0.25:d=0.5,afade=t=in:d=0.5,afade=t=out:st={total-0.7}:d=0.7")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-f", "lavfi", "-i", audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", "-shortest", str(target)], check=True)
    return target
