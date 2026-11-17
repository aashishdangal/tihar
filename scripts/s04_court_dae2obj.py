# Convert a SketchUp COLLADA export (model.dae + model/ textures) to OBJ + MTL in metres, Z-up.
# Blender 5.x has no COLLADA importer; OBJ is imported natively (up Z, forward Y).
#   python -I scripts/s04_court_dae2obj.py <model.dae> <out.obj> [--max-top N]
# One OBJ object per top-level scene node (SketchUp group/component) so parts can be moved.
import sys, os, re
import numpy as np
import collada
from collada import scene as cscene, material as cmat

src, out = sys.argv[1], sys.argv[2]
d = collada.Collada(src, ignore=[collada.common.DaeUnsupportedError, collada.common.DaeBrokenRefError])
unit = d.assetInfo.unitmeter or 0.0254
print("unit", unit, "up", d.assetInfo.upaxis)

def mat_info(m):
    """(name, rgb or None, texture path or None, alpha)"""
    name = re.sub(r"[^A-Za-z0-9_]+", "_", m.name or m.id or "mat")
    eff = m.effect
    rgb, tex, alpha = None, None, 1.0
    dif = eff.diffuse
    if isinstance(dif, cmat.Map):
        try:
            tex = dif.sampler.surface.image.path
        except Exception:
            tex = None
    elif isinstance(dif, tuple):
        rgb = dif[:3]
    if isinstance(eff.transparency, float) and eff.transparent is not None:
        try:
            t = eff.transparent
            if isinstance(t, tuple):
                alpha = 1.0 - (1 - t[3]) * eff.transparency if eff.opaque_mode == "A_ONE" else 1.0
        except Exception:
            pass
    return name, rgb, tex, alpha

mats = {}
lines = ["mtllib " + os.path.basename(out)[:-4] + ".mtl"]
vo = to = no = 0  # running offsets (OBJ is 1-based)
ntri = 0

def emit(objname, bound_geoms):
    global vo, to, no, ntri
    chunks = {}
    for bg in bound_geoms:
        for prim in bg.primitives():
            if not isinstance(prim, (collada.triangleset.BoundTriangleSet, collada.polylist.BoundPolylist, collada.polygons.BoundPolygons)):
                continue
            if not isinstance(prim, collada.triangleset.BoundTriangleSet):
                prim = prim.triangleset()
            if prim.vertex is None or len(prim.vertex_index) == 0:
                continue
            m = prim.material
            if m is not None and not isinstance(m, cmat.Material):
                m = None
            key = "default" if m is None else (m.id or m.name)
            if m is not None and key not in mats:
                mats[key] = mat_info(m)
            chunks.setdefault(key, []).append(prim)
    if not chunks:
        return
    lines.append("o " + objname)
    for key, prims in chunks.items():
        lines.append("usemtl " + (mats[key][0] if key in mats else "default"))
        for p in prims:
            v = p.vertex * unit
            vi = p.vertex_index
            has_t = p.texcoordset and len(p.texcoordset) > 0
            has_n = p.normal is not None and p.normal_index is not None
            lines.extend("v %.5f %.5f %.5f" % tuple(r) for r in v)
            if has_t:
                t = p.texcoordset[0]; ti = p.texcoord_indexset[0]
                lines.extend("vt %.5f %.5f" % (r[0], r[1]) for r in t)
            if has_n:
                n = p.normal; ni = p.normal_index
                lines.extend("vn %.4f %.4f %.4f" % tuple(r) for r in n)
            for k in range(len(vi)):
                a = vi[k] + vo + 1
                if has_t and has_n:
                    b = ti[k] + to + 1; c = ni[k] + no + 1
                    lines.append("f %d/%d/%d %d/%d/%d %d/%d/%d" % (a[0], b[0], c[0], a[1], b[1], c[1], a[2], b[2], c[2]))
                elif has_t:
                    b = ti[k] + to + 1
                    lines.append("f %d/%d %d/%d %d/%d" % (a[0], b[0], a[1], b[1], a[2], b[2]))
                elif has_n:
                    c = ni[k] + no + 1
                    lines.append("f %d//%d %d//%d %d//%d" % (a[0], c[0], a[1], c[1], a[2], c[2]))
                else:
                    lines.append("f %d %d %d" % tuple(a))
            ntri += len(vi)
            vo += len(v)
            if has_t: to += len(p.texcoordset[0])
            if has_n: no += len(p.normal)

sc = d.scene
# split into parts: expand the node tree level by level (parent matrices carried) until ~40 parts
level = [(n, np.identity(4)) for n in sc.nodes]
while len(level) < 40:
    nxt = []
    for n, m in level:
        if isinstance(n, cscene.Node) and n.children:
            mm = m @ n.matrix
            nxt.extend((c, mm) for c in n.children)
        else:
            nxt.append((n, m))
    if len(nxt) == len(level) or len(nxt) > 400:
        break
    level = nxt
for j, (top, m) in enumerate(level):
    if isinstance(top, (cscene.Node, cscene.GeometryNode)):
        nm = re.sub(r"[^A-Za-z0-9_]+", "_", getattr(top, "id", None) or getattr(top, "name", None) or "part")
        geoms = list(top.objects("geometry", m))
        emit("%s_%03d" % (nm, j), geoms)

with open(out, "w") as f:
    f.write("\n".join(lines) + "\n")
srcdir = os.path.dirname(os.path.abspath(src))
with open(out[:-4] + ".mtl", "w") as f:
    f.write("newmtl default\nKd 0.6 0.6 0.6\n\n")
    for key, (name, rgb, tex, alpha) in mats.items():
        f.write("newmtl %s\n" % name)
        f.write("Kd %.4f %.4f %.4f\n" % (rgb or (1, 1, 1)))
        if alpha < 1: f.write("d %.3f\n" % alpha)
        if tex:
            p = tex.replace("%20", " ")
            f.write("map_Kd %s\n" % p)
        f.write("\n")
print("triangles", ntri, "materials", len(mats), "->", out)
