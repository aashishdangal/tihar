"""Nepal flag drawn exactly from Schedule 1 of the Constitution (construction steps 1-24),
owner 2026-11-20: "your interpretation of nepali flag is wrong research about its exact dimensions".

Units: AB = 1, A at the origin, y up. Every point is named as in the Schedule.
Outputs (blender/assets/s08/):
  nepal_flag.png      texture, 4096 px tall, transparent outside the flag
  nepal_flag_outline.json  outer outline (blue border, mitred) in flag units + texture mapping
Checks: height / width of the whole flag must be 1.21901033... (Wikipedia, OEIS A230582).
Run (repo root): python -I scripts/s08_nepal_flag.py
"""
import json
import math
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets", "s08")
CRIMSON = (220, 20, 60)      # crimson #DC143C
BLUE = (0, 56, 147)          # deep blue #003893


def inter(p1, p2, p3, p4):
    """Intersection of line p1-p2 with line p3-p4."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


# (A) shape inside the border
A = (0.0, 0.0); B = (1.0, 0.0)
C = (0.0, 4.0 / 3.0)                                    # AC = AB + AB/3
D = (0.0, 1.0)                                          # AD = AB
s = 1 / math.sqrt(2)
E = (B[0] - s, B[1] + s)                                # on BD, BE = AB
F = (0.0, E[1]); G = (1.0, E[1])                        # FG through E, parallel to AB, FG = AB
# (B) moon
H = (0.25, 0.0)                                         # AH = AB/4, HI parallel to AC
J = (0.0, (C[1] + F[1]) / 2)                            # CF bisected
L = (H[0], J[1])                                        # JK x HI
M = inter(J, G, H, (H[0], 1.0))                         # JG x HI
dist_M_BD = abs(M[0] + M[1] - 1.0) / math.sqrt(2)       # BD: x + y = 1
N = (H[0], M[1] - dist_M_BD)
LN = L[1] - N[1]
half = math.sqrt(LN ** 2 - (L[1] - M[1]) ** 2)
P = (M[0] - half, M[1]); Q = (M[0] + half, M[1])        # circle (L, LN) x line OM
MQ = Q[0] - M[0]
NM = M[1] - N[1]
a = (LN ** 2 + LN ** 2 - NM ** 2) / (2 * LN)            # circle (N, NM) x circle (L, LN)
T = (H[0], L[1] - a)
TS = math.sqrt(LN ** 2 - a ** 2)
TM = M[1] - T[1]
# (C) sun
U = (0.0, F[1] / 2)
W = (H[0], U[1])                                        # UV x HI
# (D) border
TN = T[1] - N[1]

inner = [A, B, E, G, C]                                 # crimson field, counter-clockwise


def offset(poly, w):
    """Mitred outward offset (Schedule step 23: external angles equal the internal ones)."""
    n = len(poly); lines = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]; l = math.hypot(dx, dy)
        nx, ny = dy / l, -dx / l                         # outward for CCW
        lines.append(((p[0] + nx * w, p[1] + ny * w), (q[0] + nx * w, q[1] + ny * w)))
    return [inter(*lines[i - 1], *lines[i]) for i in range(n)]


outer = offset(inner, TN)
xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
ratio = (y1 - y0) / (x1 - x0)
print("TN %.5f  ratio %.8f (official 1.21901033)" % (TN, ratio))
assert abs(ratio - 1.21901033) < 1e-6, ratio

# ---- draw
HPX = 4096
k = HPX / (y1 - y0)
WPX = int(math.ceil((x1 - x0) * k))
SS = 2                                                  # supersample for clean edges


def px(p):
    return ((p[0] - x0) * k * SS, (y1 - p[1]) * k * SS)


img = Image.new("RGBA", (WPX * SS, HPX * SS), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.polygon([px(p) for p in outer], fill=BLUE)
d.polygon([px(p) for p in inner], fill=CRIMSON)
WHITE = (255, 255, 255)


def circle_pts(c, r, a0, a1, n=400):
    return [px((c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))) for i in range(n + 1)]


# moon crescent: lower half of circle (M, MQ) minus lower half of circle (L, LN), below line OM
d.polygon(circle_pts(M, MQ, 180, 360) + circle_pts(L, LN, 360 - math.degrees(math.asin((L[1] - M[1]) / LN)),
                                                    180 + math.degrees(math.asin((L[1] - M[1]) / LN))), fill=WHITE)
# moon body: a FULL disc (T, TM) whose lower half runs into the crescent, so the rays grow out of
# the crescent (owner 2026-11-20; matches Wikimedia's Flag_of_Nepal.svg, coded from the same
# Schedule). Rays: base on 0.98 TM spanning 22.5 deg, tip on TS, centred every 22.5 deg from
# +-11.25 to +-123.75 deg off vertical - the lower ones vanish into the crescent, 8 show above.
d.ellipse([px((T[0] - TM, T[1] + TM)), px((T[0] + TM, T[1] - TM))], fill=WHITE)
for i in range(12):
    side = 1 if i < 6 else -1
    ap = math.radians(90 - side * (11.25 + 22.5 * (i % 6)))
    b0 = ap - math.radians(11.25); b1 = ap + math.radians(11.25); rb = 0.980785 * TM
    d.polygon([px((T[0] + rb * math.cos(b0), T[1] + rb * math.sin(b0))),
               px((T[0] + TS * math.cos(ap), T[1] + TS * math.sin(ap))),
               px((T[0] + rb * math.cos(b1), T[1] + rb * math.sin(b1)))], fill=WHITE)
# sun: disc (W, MN) + 12 triangles out to circle (W, LN), two apexes on HI (90 and 270 deg)
MN = NM
d.ellipse([px((W[0] - MN, W[1] + MN)), px((W[0] + MN, W[1] - MN))], fill=WHITE)
for i in range(12):
    ap = math.radians(90 + 30 * i); b0 = ap - math.radians(15); b1 = ap + math.radians(15); rb = 0.965926 * MN
    d.polygon([px((W[0] + rb * math.cos(b0), W[1] + rb * math.sin(b0))),
               px((W[0] + LN * math.cos(ap), W[1] + LN * math.sin(ap))),
               px((W[0] + rb * math.cos(b1), W[1] + rb * math.sin(b1)))], fill=WHITE)
img = img.resize((WPX, HPX), Image.LANCZOS)
img.save(os.path.join(OUT, "nepal_flag.png"))
json.dump({"outer": [[(p[0] - x0), (p[1] - y0)] for p in outer], "width": x1 - x0, "height": y1 - y0,
           "ratio": ratio, "note": "flag units (AB=1), origin at bottom-left of the bounding box; "
                                   "texture covers the bounding box exactly"},
          open(os.path.join(OUT, "nepal_flag_outline.json"), "w"), indent=1)
print("saved", WPX, "x", HPX)
