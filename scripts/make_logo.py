"""Render the Bounty Bench logo (diff hunk + bounty coin) as a 512x512 PNG."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
S = 4  # supersample
W = 512 * S
img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(img)


def px(v):
    return int(v * S)


d.rounded_rectangle([0, 0, W - 1, W - 1], radius=px(112), fill=(15, 18, 24, 255))
# diff hunk lines
bars = [
    (96, 128, 300, (70, 78, 92), None),
    (96, 196, 250, (239, 123, 116), "-"),
    (96, 264, 330, (95, 211, 141), "+"),
    (96, 332, 220, (70, 78, 92), None),
]
for x, y, length, color, mark in bars:
    if mark:
        d.rounded_rectangle([px(x - 24), px(y - 8), px(x + length + 8), px(y + 40)], radius=px(10), fill=(color[0], color[1], color[2], 46))
        cx, cy = px(x - 8), px(y + 16)
        d.rectangle([cx - px(10), cy - px(2.5), cx + px(10), cy + px(2.5)], fill=color)
        if mark == "+":
            d.rectangle([cx - px(2.5), cy - px(10), cx + px(2.5), cy + px(10)], fill=color)
    d.rounded_rectangle([px(x + 24), px(y + 8), px(x + 24 + length - 60), px(y + 24)], radius=px(8), fill=color)
# bounty coin
cx, cy, r = px(386), px(352), px(78)
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(232, 163, 61, 255))
d.ellipse([cx - r + px(14), cy - r + px(14), cx + r - px(14), cy + r - px(14)], outline=(15, 18, 24, 255), width=px(7))
# check mark
d.line([(cx - px(28), cy + px(2)), (cx - px(8), cy + px(24)), (cx + px(30), cy - px(22))], fill=(15, 18, 24, 255), width=px(14), joint="curve")
img = img.resize((512, 512), Image.LANCZOS)
(ROOT / "public").mkdir(exist_ok=True)
img.save(ROOT / "public/logo.png")
img.resize((256, 256), Image.LANCZOS).save(ROOT / "app/icon.png")
print("logo written")
