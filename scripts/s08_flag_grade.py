"""Put the haze back on the flag layer (owner 2026-11-21: flag rendered separately "but match the lighting").

scripts/s08_flag_layer.py renders the 72 loop frames WITHOUT the haze volume (a volume would fill the
layer's alpha) and one opaque calibration frame (frame 36) in the full scene WITH the haze. Haze adds
light in front of the flag and dims what is behind it: in linear light, per channel,
    with_haze = a * without + b
so a and b are fitted on the solid flag/pole pixels of frame 36 (loop alpha > 0.98) and applied to all
72 frames. Alpha is left untouched.

  python -I scripts/s08_flag_grade.py
In : renders/s08_finale/flag3/calib/f_0036.png, renders/s08_finale/flag3/loop/f_0001..0072.png
Out: renders/s08_finale/flag3/graded/f_0001..0072.png, grade.json, check.png (calib | graded 36 | diff x4)
"""
import json
import os

import numpy as np
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "renders", "s08_finale", "flag3")


def to_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055) * 255.0


cal = np.asarray(Image.open(os.path.join(R, "calib", "f_0036.png")).convert("RGB"), np.float64)
ref = np.asarray(Image.open(os.path.join(R, "loop", "f_0036.png")).convert("RGBA"), np.float64)
solid = ref[..., 3] > 250
print("solid flag/pole pixels:", int(solid.sum()))
A, B = [], []
for ch in range(3):
    x = to_lin(ref[..., ch][solid]); y = to_lin(cal[..., ch][solid])
    a, b = np.polyfit(x, y, 1)
    A.append(a); B.append(b)
    err = np.abs(to_srgb(a * x + b) - to_srgb(y)).mean()
    print("ch %d: with_haze = %.4f * without + %.5f  (mean error after fit %.2f / 255)" % (ch, a, b, err))
os.makedirs(os.path.join(R, "graded"), exist_ok=True)
json.dump({"a": A, "b": B}, open(os.path.join(R, "graded", "grade.json"), "w"), indent=1)
for f in range(1, 73):
    im = np.asarray(Image.open(os.path.join(R, "loop", "f_%04d.png" % f)).convert("RGBA"), np.float64)
    rgb = to_lin(im[..., :3]) * np.array(A) + np.array(B)
    o = np.concatenate([to_srgb(rgb), im[..., 3:]], axis=2)
    Image.fromarray(np.round(o).astype(np.uint8), "RGBA").save(os.path.join(R, "graded", "f_%04d.png" % f))
# check: calibration | graded frame 36 over the calibration background | difference x4
g = np.asarray(Image.open(os.path.join(R, "graded", "f_0036.png")).convert("RGBA"), np.float64)
al = g[..., 3:] / 255.0
comp = g[..., :3] * al + cal * (1 - al)
diff = np.clip(np.abs(comp - cal) * 4, 0, 255)
sheet = np.concatenate([cal, comp, diff], axis=1).astype(np.uint8)
Image.fromarray(sheet).save(os.path.join(R, "graded", "check.png"))
print("solid-pixel difference graded vs calibration: %.2f / 255" % np.abs(comp - cal)[solid].mean())
