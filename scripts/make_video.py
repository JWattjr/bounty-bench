"""Compose docs/demo/*.png screenshots and captions into docs/demo/bounty-bench-demo.mp4 (no audio)."""

import json
import sys
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs/demo"
W, H, FPS = 1280, 720, 24
BG = (15, 18, 24)
AMBER = (232, 163, 61)
FONT_DIR = Path("C:/Windows/Fonts")


def font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arial.ttf"):
        try:
            return ImageFont.truetype(str(FONT_DIR / name), size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def title_card(title, subtitle, logo=True):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    y = 150
    if logo and (ROOT / "public/logo.png").exists():
        mark = Image.open(ROOT / "public/logo.png").convert("RGBA").resize((150, 150))
        img.paste(mark, ((W - 150) // 2, 110), mark)
        y = 300
    for line in wrap(d, title, font(58, True), W - 200):
        d.text(((W - d.textlength(line, font=font(58, True))) // 2, y), line, font=font(58, True), fill=(240, 242, 246))
        y += 72
    y += 14
    for line in wrap(d, subtitle, font(30), W - 260):
        d.text(((W - d.textlength(line, font=font(30))) // 2, y), line, font=font(30), fill=AMBER)
        y += 42
    return img


def shot_card(image_path, caption):
    img = Image.new("RGB", (W, H), BG)
    shot = Image.open(image_path).convert("RGB")
    box_h = H - 120
    scale = min((W - 80) / shot.width, box_h / shot.height)
    shot = shot.resize((int(shot.width * scale), int(shot.height * scale)), Image.LANCZOS)
    img.paste(shot, ((W - shot.width) // 2, 24))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 96, W, H], fill=(22, 26, 34))
    d.rectangle([0, H - 96, 8, H], fill=AMBER)
    lines = wrap(d, caption, font(28), W - 100)[:2]
    y = H - 84 + (2 - len(lines)) * 16
    for line in lines:
        d.text((40, y), line, font=font(28), fill=(240, 242, 246))
        y += 38
    return img


def render(plan):
    out = DEMO / "bounty-bench-demo.mp4"
    writer = imageio.get_writer(str(out), fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    previous = None
    for card, seconds in plan:
        frames = int(seconds * FPS)
        fade = min(10, frames // 3)
        for i in range(frames):
            frame = card
            if previous is not None and i < fade:
                frame = Image.blend(previous, card, (i + 1) / fade)
            writer.append_data(__import__("numpy").asarray(frame))
        previous = card
    writer.close()
    return out


def main():
    spec = json.loads((DEMO / "storyboard.json").read_text(encoding="utf-8"))
    plan = []
    for scene in spec:
        if scene["type"] == "title":
            plan.append((title_card(scene["title"], scene["subtitle"], scene.get("logo", True)), scene["seconds"]))
        else:
            plan.append((shot_card(DEMO / scene["image"], scene["caption"]), scene["seconds"]))
    print("video", render(plan), "seconds", sum(s for _, s in plan))


if __name__ == "__main__":
    sys.exit(main())
