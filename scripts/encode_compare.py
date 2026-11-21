"""Side-by-side check of a frame encode: render PNG vs the current site WebP vs AVIF 4:4:4.

    python scripts/encode_compare.py s04_kukur 104 [--q 80]
-> renders/<scene>/test/encode_compare_<frame>.png

Top row: whole frames. Bottom row: the busiest 240x135 patch at 3x, nearest-neighbour, so
compression damage is visible. Sizes per frame are printed on each panel.
"""
import argparse
import io
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from webp_util import save_avif  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("scene")
ap.add_argument("frame", type=int)
ap.add_argument("--q", type=int, default=80)
a = ap.parse_args()

root = pathlib.Path(__file__).resolve().parent.parent
name = f"{a.frame:04d}"
png = root / "renders" / a.scene / f"{name}.png"
webp = root / "web" / "public" / "frames" / a.scene / "d" / f"{name}.webp"
if not webp.exists():
    webp = root / "renders" / a.scene / "webp_backup" / "d" / f"{name}.webp"

ref = Image.open(png).convert("RGB")
buf = io.BytesIO()
save_avif(ref, buf, a.q)
avif_kb = buf.tell() / 1024
buf.seek(0)
panels = [
    (f"render (PNG)", ref),
    (f"site now: WebP  {webp.stat().st_size / 1024:.0f} KB", Image.open(webp).convert("RGB")),
    (f"AVIF 4:4:4 q{a.q}  {avif_kb:.0f} KB", Image.open(buf).convert("RGB")),
]

# busiest patch: most local contrast
g = np.asarray(ref.convert("L"), float)
best = None
for y in range(0, 1080 - 135, 45):
    for x in range(0, 1920 - 240, 60):
        w = g[y:y + 135, x:x + 240]
        s = np.abs(np.diff(w, axis=1)).mean() + np.abs(np.diff(w, axis=0)).mean()
        if best is None or s > best[0]:
            best = (s, x, y)
_, x, y = best
box = (x, y, x + 240, y + 135)

W, H, L = 720, 405, 26
sheet = Image.new("RGB", (W * 3, (H + L) * 2), (18, 18, 18))
d = ImageDraw.Draw(sheet)
for i, (label, im) in enumerate(panels):
    full = im.resize((W, H), Image.LANCZOS)
    dr = ImageDraw.Draw(full)
    sx, sy = W / 1920, H / 1080
    dr.rectangle((box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy), outline=(242, 163, 58), width=2)
    sheet.paste(full, (i * W, L))
    sheet.paste(im.crop(box).resize((W, H), Image.NEAREST), (i * W, H + 2 * L))
    d.text((i * W + 8, 7), label, fill=(255, 255, 255))
    d.text((i * W + 8, H + L + 7), "3x close-up of the boxed patch", fill=(200, 200, 200))
out = root / "renders" / a.scene / "test" / f"encode_compare_{name}.png"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out)
print(f"{a.scene} {name}: webp {webp.stat().st_size / 1024:.0f} KB  avif {avif_kb:.0f} KB  -> {out}")
