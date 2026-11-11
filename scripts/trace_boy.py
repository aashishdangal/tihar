"""Trace the four poses of the सुरु boy from the owner's reference mockup into one SVG.

Usage: python scripts/trace_boy.py "refrences/Tihar Diya and Playful Nepali Boys.png" web/src/assets/boy-head.svg --heads

The reference (local only, refrences/ is not committed) shows one cartoon boy in a dhaka topi in
four poses, left to right: sitting in namaste (idle), arms wide breathing in (inhale), bent
forward blowing (blow), cheeks puffed holding the breath (hold). Each pose is cut out, upscaled,
split into three layers (cream body, dark line work, orange accents), traced with potrace and
aligned on a shared ground point so the poses can swap in place. Output: one <svg> with a <g>
per pose (class boy__pose--idle / --inhale / --blow / --hold).
"""
import sys

import numpy as np
import potrace
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

src, out = sys.argv[1], sys.argv[2]
UP = 4                                   # trace at 4x for smooth curves
# (name, box in the reference: x0, y0, x1, y1) - found by scanning for the cream shapes
POSES = [("idle", (899, 437, 1063, 676)), ("inhale", (1067, 402, 1297, 676)),
         ("blow", (1297, 442, 1518, 676)), ("hold", (1536, 450, 1699, 676))]
W, H = 240, 290                          # shared viewBox (reference px); ground point at (120, 284)
GROUND = (120, 284)
HEADS = "--heads" in sys.argv
if HEADS:
    # --heads: topi to chin of each pose, with its own breath marks (inhale lines, cheek marks,
    # the puff), centred in a square viewBox and clipped to a circle for the round सुरु control
    POSES = [("idle", (918, 446, 1045, 551)), ("inhale", (1084, 414, 1240, 523)),
             ("blow", (1350, 452, 1496, 562)), ("hold", (1552, 450, 1706, 566))]
    W = H = 150
    CENTRE = (75, 79)                    # head centre in the circle
    CLIP_R = 69                          # just inside the ring

im = Image.open(src).convert("RGB")


def trace(mask, scale, dx, dy):
    """potrace a boolean mask -> SVG path data, mapped back to viewBox units."""
    bm = potrace.Bitmap(~mask)   # potracer traces the "dark" (False) pixels, so invert
    plist = bm.trace(turdsize=6, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                     alphamax=1.0, opticurve=True, opttolerance=0.25)
    f = lambda p: f"{p.x / scale + dx:.2f} {p.y / scale + dy:.2f}"
    parts = []
    for curve in plist:
        parts.append(f"M{f(curve.start_point)}")
        for seg in curve.segments:
            if seg.is_corner:
                parts.append(f"L{f(seg.c)}L{f(seg.end_point)}")
            else:
                parts.append(f"C{f(seg.c1)} {f(seg.c2)} {f(seg.end_point)}")
        parts.append("Z")
    return "".join(parts)


groups = []
for name, (x0, y0, x1, y1) in POSES:
    crop = im.crop((x0, y0, x1, y1))
    big = crop.resize((crop.width * UP, crop.height * UP), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(big).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = (a.max(2) - a.min(2)) / np.maximum(a.max(2), 1)
    cream = (lum > 150) & (sat < 0.35)
    accent = (r > 170) & (g > 90) & (g < 190) & (b < 110) & (sat > 0.45)
    # body silhouette = cream with its holes (the inner line work) filled; keep large parts only
    body = ndi.binary_fill_holes(ndi.binary_closing(cream, iterations=3))
    lab, n = ndi.label(body)
    if n:
        sizes = ndi.sum(body, lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 0.01 * sizes.max()])
        body &= keep
    lines = body & ~cream & ~accent
    lines = ndi.binary_opening(lines, iterations=1)
    ys, xs = np.nonzero(body)
    if HEADS:
        # align: centre of the head (topi + face) -> CENTRE
        dx = CENTRE[0] - (xs.min() + xs.max()) / 2 / UP
        dy = CENTRE[1] - (ys.min() + ys.max()) / 2 / UP
    else:
        # accents outside the body too (the puff), but not the ground strip at the very bottom
        accent[-int(10 * UP):, :] = False
        # align: feet bottom-centre of the body -> GROUND
        foot_y = ys.max() / UP
        cx = (xs.min() + xs.max()) / 2 / UP
        dx, dy = GROUND[0] - cx, GROUND[1] - foot_y
    layers = [("boy__body", trace(body, UP, dx, dy)),
              ("boy__lines", trace(lines, UP, dx, dy)),
              ("boy__accent", trace(accent, UP, dx, dy))]
    paths = "".join(f'<path class="{c}" d="{d}"/>' for c, d in layers if d)
    groups.append(f'<g class="boy__pose boy__pose--{name}">{paths}</g>')
    print(name, "body px", int(body.sum() / UP / UP), "lines", int(lines.sum() / UP / UP), "accent", int(accent.sum() / UP / UP))

inner = "".join(groups)
if HEADS:
    inner = (f'<defs><clipPath id="boy-clip"><circle cx="{W / 2}" cy="{H / 2}" r="{CLIP_R}"/></clipPath></defs>'
             f'<g clip-path="url(#boy-clip)">{inner}</g>')
svg = (f'<svg class="boy" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
       f'focusable="false">{inner}</svg>\n')
open(out, "w", encoding="utf-8").write(svg)
print("wrote", out, len(svg) // 1024, "KB")
