# s07: draws the engraving mask for Jamuna's brass Bhai Tika thali (top-down, planar).
# White = engraved groove, black = flat brass. The image spans the plate's full Ø 60 cm
# (x, y in -0.30..0.30 m), so Blender maps it from object x/y, no UVs needed.
# Motifs from real Nepali puja thalis: swastik in an 8-petal lotus, a 16-petal lotus ring,
# dotted bands, a scrolling vine band and a beaded rim.
#   python scripts/s07_thali_engrave.py  ->  blender/assets/s07/thali_engrave.png
import math, os
from PIL import Image, ImageDraw, ImageFilter

N = 4096
R_PLATE = 0.30
OUT = os.path.join(os.path.dirname(__file__), "..", "blender", "assets", "s07", "thali_engrave.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

img = Image.new("L", (N, N), 0)
d = ImageDraw.Draw(img)
C = N / 2
px = lambda m: m / R_PLATE * (N / 2)          # metres -> pixels
W = max(2, int(px(0.0012)))                    # groove width ~1.2 mm


def P(r, a):
    return (C + px(r) * math.cos(a), C - px(r) * math.sin(a))


def ring(r, w=W):
    d.ellipse([C - px(r), C - px(r), C + px(r), C + px(r)], outline=255, width=w)


def dots(r, n, size):
    for i in range(n):
        x, y = P(r, 2 * math.pi * i / n)
        s = px(size)
        d.ellipse([x - s, y - s, x + s, y + s], fill=255)


def petal(r0, r1, a, half_w, w=W, inner=True):
    """Pointed lotus petal from radius r0 to r1 at angle a, drawn as two arcs (outline)."""
    pts_l, pts_r = [], []
    for k in range(41):
        t = k / 40
        r = r0 + (r1 - r0) * t
        bulge = math.sin(math.pi * t) ** 0.8 * half_w * (1 - 0.35 * t)
        da = bulge / max(r, 1e-4)
        pts_l.append(P(r, a + da)); pts_r.append(P(r, a - da))
    d.line(pts_l + pts_r[::-1] + [pts_l[0]], fill=255, width=w, joint="curve")
    if inner:                                   # centre vein
        d.line([P(r0 + (r1 - r0) * 0.15, a), P(r0 + (r1 - r0) * 0.8, a)], fill=255, width=max(1, w // 2))


# --- centre: swastik inside a circle ------------------------------------------------------------
ring(0.030)
a = 0.018
arms = [((0, 0), (0, a), (a, a)), ((0, 0), (a, 0), (a, -a)), ((0, 0), (0, -a), (-a, -a)), ((0, 0), (-a, 0), (-a, a))]
for arm in arms:
    d.line([(C + px(x), C - px(y)) for x, y in arm], fill=255, width=int(W * 2.2), joint="curve")
for qx, qy in ((0.5, 0.5), (0.5, -0.5), (-0.5, -0.5), (-0.5, 0.5)):  # four dots between the arms
    x, y = C + px(qx * a), C - px(qy * a)
    s = px(0.0022); d.ellipse([x - s, y - s, x + s, y + s], fill=255)

# --- 8-petal lotus, then a 16-petal ring ---------------------------------------------------------
for i in range(8):
    petal(0.031, 0.072, 2 * math.pi * i / 8 + math.pi / 8, 0.016)
ring(0.075)
dots(0.080, 64, 0.0011)
ring(0.085)
for i in range(16):
    petal(0.086, 0.130, 2 * math.pi * i / 16, 0.012)
    petal(0.090, 0.118, 2 * math.pi * (i + 0.5) / 16, 0.006, inner=False)
ring(0.133)
ring(0.137)

# --- scrolling vine band (0.145 .. 0.200) --------------------------------------------------------
rm, amp, n = 0.172, 0.016, 24
wave = [P(rm + amp * math.sin(n * t), t) for t in [2 * math.pi * k / 1600 for k in range(1601)]]
d.line(wave, fill=255, width=W, joint="curve")
for i in range(n):                              # leaves in the hollows, a dot under every crest
    t_out = 2 * math.pi * (i + 0.25) / n        # outer crest
    t_in = 2 * math.pi * (i + 0.75) / n         # inner crest
    for t, side in ((t_out, -1), (t_in, 1)):    # leaf grows from the crest back toward the band centre
        r_crest = rm - side * amp
        petal(r_crest, r_crest + side * 0.022, t, 0.0055, w=max(2, W - 1))
        x, y = P(rm - side * amp * 0.15, t + math.pi / n)
        s = px(0.0016); d.ellipse([x - s, y - s, x + s, y + s], fill=255)
ring(0.205)
ring(0.209)
dots(0.218, 120, 0.0012)
ring(0.226)

# --- beaded rim (on the slope near the edge) ----------------------------------------------------
ring(0.278)
dots(0.288, 180, 0.0016)

img = img.filter(ImageFilter.GaussianBlur(1.2))   # soft groove walls for the bump
img.save(OUT)
print("wrote", os.path.abspath(OUT))
