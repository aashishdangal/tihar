"""PNG -> WebP for one scene (see PIPELINE.md section 3).

renders/<scene>/0001.png -> web/public/frames/<scene>/d/0001.webp  (1920x1080, q100 sharp_yuv)
                         -> web/public/frames/<scene>/m/0001.webp  (720x1280,  q100 sharp_yuv)

Mobile framing comes from scripts/mobile_framing.json (per scene); default is the spec's
centre crop to 9:16. Mode "fit" is for shots whose subject is off-centre (s00: diyo on the
left third): crop columns x0..x1 of the frame at full height, scale to 720 wide, place it at
center_y, and fill above/below with the frame's own edge colour (feathered).
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from webp_util import CWEBP, save_webp  # noqa: E402


scene = sys.argv[1]
root = pathlib.Path(__file__).resolve().parent.parent
src = root / "renders" / scene
out = root / "web" / "public" / "frames" / scene
framing = json.loads((root / "scripts" / "mobile_framing.json").read_text(encoding="utf-8"))
cfg = framing.get(scene, {"mode": "centre"})
MW, MH, FEATHER = 720, 1280, 48
# q72/q68 (old spec) left visible blocks in dark gradients. Lossy q100 + sharp_yuv is ~93 KB/frame
# and is the ceiling for lossy WebP; near-lossless and lossless are ~820-850 KB/frame (render grain).
# Optional per-scene override ("q_d" / "q_m" in mobile_framing.json, a number or "lossless").
# s01 is lossless: its dense coloured city lights looked smeared even at lossy q100 (owner: size
# budget doesn't matter for this scene, quality does).
Q_D, Q_M = cfg.get("q_d", 100), cfg.get("q_m", 100)


def mobile_centre(im):
    w, h = im.size
    cw = round(h * 9 / 16)
    x = (w - cw) // 2
    return im.crop((x, 0, x + cw, h)).resize((MW, MH), Image.LANCZOS)


def edge_colour(im, top):
    rows = im.crop((0, 0, im.width, 4)) if top else im.crop((0, im.height - 4, im.width, im.height))
    return rows.resize((1, 1), Image.BOX).getpixel((0, 0))


def mobile_fit(im):
    w, h = im.size
    part = im.crop((round(cfg["x0"] * w), 0, round(cfg["x1"] * w), h))
    ph = round(MW * part.height / part.width)
    part = part.resize((MW, ph), Image.LANCZOS)
    top = round(cfg["center_y"] * MH - ph / 2)
    canvas = Image.new("RGB", (MW, MH), edge_colour(part, True))
    canvas.paste(Image.new("RGB", (MW, MH - top - ph // 2), edge_colour(part, False)), (0, top + ph // 2))
    # alpha mask: opaque, fading to 0 over FEATHER px at the top and bottom edges
    mask = Image.new("L", (MW, ph), 255)
    for i in range(FEATHER):
        a = round(255 * i / FEATHER)
        mask.paste(a, (0, i, MW, i + 1))
        mask.paste(a, (0, ph - 1 - i, MW, ph - i))
    canvas.paste(part, (0, top), mask)
    return canvas


def mobile_point(px, py, w, h):
    """Where a point of the 1920x1080 frame lands in the mobile frame (0..1)."""
    if cfg["mode"] == "fit":
        x0, x1 = cfg["x0"], cfg["x1"]
        ph = MW * h / ((x1 - x0) * w)
        return (px - x0) / (x1 - x0), (cfg["center_y"] * MH - ph / 2 + py * ph) / MH
    return 0.5 + (px - 0.5) * 16 / 9 * 16 / 9, py


frames = sorted(src.glob("[0-9][0-9][0-9][0-9].png"))
if not frames:
    sys.exit(f"no frames in {src}")
(out / "d").mkdir(parents=True, exist_ok=True)
(out / "m").mkdir(parents=True, exist_ok=True)
mobile = mobile_fit if cfg["mode"] == "fit" else mobile_centre
dt = mt = 0
for p in frames:
    im = Image.open(p).convert("RGB")
    d = out / "d" / f"{p.stem}.webp"
    save_webp(p, d, Q_D)
    m = out / "m" / f"{p.stem}.webp"
    save_webp(mobile(im), m, Q_M)
    dt += d.stat().st_size
    mt += m.stat().st_size
n = len(frames)
print(f"encoder: {CWEBP or 'Pillow'}")
subprocess.run([sys.executable, str(root / "scripts" / "make_low_set.py"), scene], check=True)
print(f"{n} frames -> {out}  d {dt/1e6:.1f} MB ({dt/n/1e3:.0f} KB/frame)  m {mt/1e6:.1f} MB ({mt/n/1e3:.0f} KB/frame)")
for name, (px, py) in cfg.get("points", {}).items():
    mx, my = mobile_point(px, py, 1920, 1080)
    print(f"point {name}: d ({px:.3f}, {py:.3f})  m ({mx:.3f}, {my:.3f})")
