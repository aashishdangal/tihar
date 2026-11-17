# Read-only fit of the S04 mala path and tika patch to the posed Nubis dog.
# blender -b blender/scenes/s04_kukur_v001.blend --python scripts/s04_hand_fit_dog.py -- <out.json>
# Never saves the .blend. All output coordinates are at FINAL dog scale S=0.65 about the
# rig origin (rig left at its current location), i.e. world-space for a dog scaled 0.65.
import bpy, math, json, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else r"E:\Projects\tihar\blender\assets\s04_hand\s04_mala_fit.json"
S = 0.65
N = 64                       # control points per mala shape
R_ROPE = 0.021               # flower-rope radius at final scale (head dia ~4.2 cm)
FUR = 0.013                  # max fur length at the neck (measured 1.3 cm full scale at the nape)
OFF = FUR + R_ROPE / S       # centreline clearance from skin (full scale)

dg = bpy.context.evaluated_depsgraph_get()
body = bpy.data.objects["Nubis Mesh"]
me = body.evaluated_get(dg).to_mesh()
mw = body.matrix_world
V = [mw @ v.co for v in me.vertices]
bvh = BVHTree.FromPolygons(V, [tuple(p.vertices) for p in me.polygons])
rig = bpy.data.objects["Nubis"]
O = rig.matrix_world.translation.copy()
P = lambda b, t: rig.matrix_world @ (rig.pose.bones[b].tail if t else rig.pose.bones[b].head)
W = lambda p: O + S * (p - O)          # full -> final world

def length(pts):
    return sum((pts[i] - pts[i - 1]).length for i in range(len(pts)))

def resample(pts, n):
    """closed polyline -> n points evenly spaced by arc length, starting at pts[0]"""
    seg = [(pts[(i + 1) % len(pts)] - pts[i]).length for i in range(len(pts))]
    L = sum(seg); out = []; i = 0; acc = 0.0
    for k in range(n):
        s = L * k / n
        while acc + seg[i] < s:
            acc += seg[i]; i += 1
        f = (s - acc) / seg[i] if seg[i] else 0
        out.append(pts[i].lerp(pts[(i + 1) % len(pts)], f))
    return out

def smooth(pts, it=4, w=0.5):
    for _ in range(it):
        pts = [p.lerp((pts[i - 1] + pts[(i + 1) % len(pts)]) / 2, w) for i, p in enumerate(pts)]
    return pts

def clear(pts, off, it=6):
    """push points out so each is at least `off` from the skin"""
    for _ in range(it):
        new = []
        for p in pts:
            q, n, _, d = bvh.find_nearest(p)
            inside = (p - q).dot(n) < 0
            if inside or d < off:
                p = q + n * off
            new.append(p)
        pts = smooth(new, 1, 0.3)
    return pts

def ring(centre_fn, dir_fn, off, M=240):
    pts = []
    for k in range(M):
        th = 2 * math.pi * k / M
        d = dir_fn(th); c = centre_fn(th)
        hit = bvh.ray_cast(c + d * 0.6, -d, 0.6)
        if hit[0] is None:
            pts.append(c + d * 0.15); continue
        n = (hit[1] + d).normalized()
        pts.append(hit[0] + n * off)
    return pts

# ---------------- worn: around the base of the neck, sagging onto the chest
a, b = P("NeckBase", 0), P("Neck", 1)
axis = (b - a).normalized()
back = (Vector((0, 1, 0)) - axis * axis.y).normalized()     # dog faces -Y: back of neck is +Y
side = back.cross(axis).normalized()                        # +X
c0 = a.lerp(b, 0.25)
neck_perim = 0.784                                          # measured at NeckBase head (full)
L_target = 1.3 * neck_perim + 2 * math.pi * OFF             # inner circumference = 1.3 x neck

def worn(sag):
    pts = ring(lambda th: c0 - axis * (sag * ((1 - math.cos(th)) / 2) ** 1.6),
               lambda th: back * math.cos(th) + side * math.sin(th), OFF)
    pts = smooth(pts, 6, 0.5)
    return clear(pts, OFF)

lo, hi = 0.0, 0.5
for _ in range(16):
    mid = (lo + hi) / 2
    if length(worn(mid)) < L_target: lo = mid
    else: hi = mid
sag = (lo + hi) / 2
worn_pts = resample(worn(sag), N)
print("[fit] worn sag %.3f length %.3f (target %.3f) -> final %.3f m" % (sag, length(worn_pts), L_target, length(worn_pts) * S))
zs = [p.z for p in worn_pts]; ys = [p.y for p in worn_pts]
print("[fit] worn z[%.3f,%.3f] y[%.3f,%.3f]" % (min(zs), max(zs), min(ys), max(ys)))

# ---------------- over-head: loose ring behind the ears and under the jaw
C = Vector((0, -0.07, 0.975))
u = Vector((0, 0.55, 0.835)).normalized()                 # up-back
X = Vector((1, 0, 0))
head = clear(smooth(ring(lambda th: C, lambda th: u * math.cos(th) + X * math.sin(th), OFF + 0.02), 6, 0.5), OFF + 0.015)
head = resample(head, N)
L0 = length(head); k = L_target / L0
p0 = head[0]
head = clear([p0 + (p - p0) * k for p in head], OFF + 0.01)  # scale about the held point to full length
head = resample(head, N)
print("[fit] overhead ring %.3f -> scaled x%.2f -> %.3f" % (L0, k, length(head)))

# ---------------- tika patch on the forehead between the eyes
hit = bvh.ray_cast(Vector((0, -0.6, 1.055)), Vector((0, 1, 0)))
F, nF = hit[0], hit[1].normalized()
tx = (X - nF * nF.dot(X)).normalized()
ty = nF.cross(tx).normalized()
G = 21; R = 0.025                                        # +-2.5 cm full = +-1.6 cm final
grid = []
for j in range(G):
    row = []
    for i in range(G):
        uu = -R + 2 * R * i / (G - 1); vv = -R + 2 * R * j / (G - 1)
        o = F + tx * uu + ty * vv + nF * 0.1
        h = bvh.ray_cast(o, -nF, 0.3)
        row.append((h[0] - (F + tx * uu + ty * vv)).dot(nF) * S if h[0] else 0.0)
    grid.append(row)
print("[fit] forehead", tuple(round(c, 4) for c in F), "normal", tuple(round(c, 3) for c in nF))

data = dict(
    scale=S, rig_origin=list(O), rope_radius=R_ROPE,
    worn_origin=list(W(worn_pts[0])), worn=[list((p - worn_pts[0]) * S) for p in worn_pts],
    overhead_origin=list(W(head[0])), overhead=[list((p - head[0]) * S) for p in head],
    length_final=length(worn_pts) * S, neck_perim_final=neck_perim * S,
    tika=dict(centre=list(W(F)), normal=list(nF), tx=list(tx), ty=list(ty), half=R * S, grid=grid),
    bones=dict(head=list(W(P("Head", 0))), neck=list(W(P("Neck", 0))), neckbase=list(W(P("NeckBase", 0)))),
)
with open(OUT, "w") as f:
    json.dump(data, f, indent=1)
print("[fit] wrote", OUT)
