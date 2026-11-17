# Read-only: measure the posed Nubis neck cross-sections and forehead surface point.
# blender -b s04_kukur_v001.blend --python scripts/s04_hand_measure_dog.py   (never saves)
import bpy, math, json
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

dg = bpy.context.evaluated_depsgraph_get()
body = bpy.data.objects["Nubis Mesh"]
ev = body.evaluated_get(dg)
me = ev.to_mesh()
mw = body.matrix_world
verts = [mw @ v.co for v in me.vertices]
edges = [tuple(e.vertices) for e in me.edges]
rig = bpy.data.objects["Nubis"]
P = lambda b, t: rig.matrix_world @ (rig.pose.bones[b].tail if t else rig.pose.bones[b].head)

def hull_perim(pts2):
    pts = sorted(set((round(p[0], 5), round(p[1], 5)) for p in pts2))
    if len(pts) < 3: return 0, pts
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    per = sum(math.dist(h[i], h[(i+1) % len(h)]) for i in range(len(h)))
    return per, h

out = {}
a, b = P("NeckBase", 0), P("Neck", 1)
axis = (b - a).normalized()
for t in (0.0, 0.2, 0.4, 0.6, 0.8):
    c = a.lerp(b, t)
    pts = []
    for i, j in edges:
        p, q = verts[i], verts[j]
        dp, dq = (p - c).dot(axis), (q - c).dot(axis)
        if dp * dq < 0:
            x = p + (q - p) * (dp / (dp - dq))
            if (x - c).length < 0.35: pts.append(x)
    u = axis.orthogonal().normalized(); v = axis.cross(u)
    p2 = [((x - c).dot(u), (x - c).dot(v)) for x in pts]
    per, h = hull_perim(p2)
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    print("NECK t=%.1f centre %s perim %.3f  x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (t, tuple(round(k, 3) for k in c), per, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    out["neck_%.1f" % t] = dict(centre=list(c), perim=per)

bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
for z in (1.04, 1.05, 1.06, 1.07):
    hit = bvh.ray_cast(Vector((0, -0.6, z)), Vector((0, 1, 0)))
    if hit[0]: print("FOREHEAD z=%.2f hit %s normal %s" % (z, tuple(round(k, 4) for k in hit[0]), tuple(round(k, 3) for k in hit[1])))
# top of head
hit = bvh.ray_cast(Vector((0, -0.12, 1.5)), Vector((0, 0, -1)))
print("HEADTOP", hit[0])
# fur length near forehead
fur = bpy.data.objects["Nubis Fur"].evaluated_get(dg)
try:
    fd = fur.data
    pos = [fur.matrix_world @ Vector(p.position) for p in fd.points] if hasattr(fd, "points") else []
    f0 = Vector((0, -0.19, 1.05))
    near = [p for p in pos if (p - f0).length < 0.04]
    print("FUR points", len(pos), "near forehead", len(near))
    if near:
        hit = bvh.find_nearest(f0)
        d = [bvh.find_nearest(p)[3] for p in near]
        print("FUR max dist from skin near forehead %.4f mean %.4f" % (max(d), sum(d)/len(d)))
    n0 = P("NeckBase", 0)
    nearn = [p for p in pos if (p - n0).length < 0.15]
    d = [bvh.find_nearest(p)[3] for p in nearn[:20000]]
    if d: print("FUR neck max %.4f mean %.4f" % (max(d), sum(d)/len(d)))
except Exception as e:
    print("FUR err", e)
lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
for x in verts: lo = Vector(map(min, lo, x)); hi = Vector(map(max, hi, x))
print("BODY bounds", tuple(round(k,3) for k in lo), tuple(round(k,3) for k in hi))
