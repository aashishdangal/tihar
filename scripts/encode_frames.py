"""PNG -> WebP for one scene. Desktop 1920w, mobile 960w.
renders/<scene>/0001.png -> web/public/frames/<scene>/0001.webp (+ mobile/0001.webp)"""
import sys, pathlib
from PIL import Image

scene = sys.argv[1]
root = pathlib.Path(__file__).resolve().parent.parent
src = root / "renders" / scene
out = root / "web" / "public" / "frames" / scene
(out / "mobile").mkdir(parents=True, exist_ok=True)
frames = sorted(p for p in src.glob("[0-9][0-9][0-9][0-9].png"))
if not frames:
    sys.exit(f"no frames in {src}")
total = 0
for p in frames:
    im = Image.open(p).convert("RGB")
    d = out / f"{p.stem}.webp"; im.save(d, "WEBP", quality=80, method=6)
    m = out / "mobile" / f"{p.stem}.webp"
    im.resize((960, round(960 * im.height / im.width)), Image.LANCZOS).save(m, "WEBP", quality=75, method=6)
    total += d.stat().st_size
print(f"{len(frames)} frames -> {out}  desktop {total/1e6:.1f} MB")
