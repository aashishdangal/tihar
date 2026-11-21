"""Web assets for the hybrid finale (owner 2026-11-21: "go ahead with browser side").

In : renders/s08_finale/still3/clean/f_0036.png   clean still (no tree, grass, kite, flag)
     renders/s08_finale/still4/full/f_0036.png    full still (tree, grass, kite; no flag)
     renders/s08_finale/masks/{tree,kite,grass}.png   coverage of each layer (alpha)
     renders/s08_finale/flag3/graded/f_0001..0072.png + ../calib/region.json   flag loop, haze-graded
Out: web/public/frames/s08_finale/hybrid/clean.webp, tree.webp, kite.webp, grass.webp,
     flag/0001..0072.webp, hybrid.json (flag rect, kite pivot, loop length)

Layer colour is UN-MIXED from the full still: full = a*layer + (1-a)*clean, so layer = (full-(1-a)*clean)/a.
That keeps soft leaf edges free of the city behind them, so nothing haloes when the layer sways.

  python -I scripts/s08_hybrid_assets.py
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
R = os.path.join(ROOT, "renders", "s08_finale")
OUT = os.path.join(ROOT, "web", "public", "frames", "s08_finale", "hybrid")
os.makedirs(os.path.join(OUT, "flag"), exist_ok=True)

clean = np.asarray(Image.open(os.path.join(R, "still3", "clean", "f_0036.png")).convert("RGB"), np.float32)
full = np.asarray(Image.open(os.path.join(R, "still4", "full", "f_0036.png")).convert("RGB"), np.float32)


def city_d(c):
    """Owner 2026-11-21 chose option D for the city ("just visible, not full detail"): in the valley
    only the bright Tihar light points stay (house walls sink into the night), and the far city
    melts into the dusk haze with a little more softness the further it is. Sky and peaks untouched.
    Applied to the BACK still only; the layers above are cut from the original render."""
    from PIL import ImageFilter
    H = c.shape[0]
    y = np.arange(H, dtype=np.float32)[:, None, None]
    valley = np.clip((y - 380) / 90.0, 0, 1); valley = valley * valley * (3 - 2 * valley)
    far = np.clip((700 - y) / 280.0, 0, 1)                 # 1 at the horizon (~420 px), 0 from ~700 px down
    haze = c[380:420].reshape(-1, 3).mean(0)                # dusk colour just above the valley horizon
    lum = (0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2])[..., None]
    keep = np.clip((lum - 95) / 70, 0, 1) ** 1.5            # 1 on the lights, 0 on walls and ground
    lit = c * (0.30 + 0.70 * keep)
    soft = np.asarray(Image.fromarray(np.clip(lit, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), np.float32)
    city = lit * (1 - far * 0.6) + soft * far * 0.6
    city = city * (1 - far * 0.5) + haze * far * 0.5
    return np.clip(c * (1 - valley) + city * valley, 0, 255)


Image.fromarray(city_d(clean).astype(np.uint8)).save(os.path.join(OUT, "clean.webp"), quality=92, method=6)

meta = {"size": [clean.shape[1], clean.shape[0]], "loop_frames": 72, "fps": 24}
for name in ("tree", "kite", "grass"):
    a = np.asarray(Image.open(os.path.join(R, "masks", name + ".png")).convert("RGBA"), np.float32)[..., 3] / 255.0
    a3 = a[..., None]
    lay = np.where(a3 > 0.04, (full - (1 - a3) * clean) / np.maximum(a3, 0.04), full)
    lay = np.clip(lay, 0, 255)
    rgba = np.concatenate([lay, (a3 * 255)], axis=2).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, name + ".webp"), quality=90, alpha_quality=100, method=6)
    ys, xs = np.nonzero(a > 0.5)
    meta[name] = {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}
    if name == "kite":                                   # pivot = the kite's top corner (where it hangs)
        top = ys.min(); meta["kite"]["pivot"] = [float(xs[ys == top].mean()), float(top)]
    print(name, "bbox", meta[name]["bbox"])

# hill + front ridge (+ its grass) as a front layer, so the browser can draw the fireworks behind it
# (owner 2026-11-21). Static: colour straight from the clean still, alpha from masks/hill.png.
ha = np.asarray(Image.open(os.path.join(R, "masks", "hill.png")).convert("RGBA"), np.float32)[..., 3:]
Image.fromarray(np.concatenate([clean, ha], axis=2).astype(np.uint8), "RGBA").save(
    os.path.join(OUT, "hill.webp"), quality=90, alpha_quality=100, method=6)
ys, xs = np.nonzero(ha[..., 0] > 128)
meta["hill"] = {"bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}

reg = json.load(open(os.path.join(R, "flag3", "calib", "region.json")))
meta["flag"] = {"rect": [reg["x0"], reg["y0"], reg["x1"] - reg["x0"], reg["y1"] - reg["y0"]]}
for f in range(1, 73):
    im = Image.open(os.path.join(R, "flag3", "graded", "f_%04d.png" % f)).convert("RGBA")
    im.save(os.path.join(OUT, "flag", "%04d.webp" % f), quality=90, alpha_quality=100, method=6)
json.dump(meta, open(os.path.join(OUT, "hybrid.json"), "w"), indent=1)
tot = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
print("meta", json.dumps(meta)); print("total %.2f MB" % (tot / 1e6))
