"""s08 pass 5 (owner 2026-11-21), on top of the one-pass finale (s08_finale_v071.blend):
  1. "move the mountains blocked by the tree to middle": S01_Himalaya_GLO30 turned -15 deg about
     the camera (owner chose: rotate the whole range), so the snowy peaks behind the tree sit mid-frame.
  2. "far buildings should be low poly and transition ... little smooth": the detailed City Generator
     zone shrinks from 3.5 km to a dithered band 1.5-2.5 km. Inside 1.5 km every footprint stays
     detailed; across the band a footprint stays detailed with a chance falling 1 -> 0, and the far
     low-poly boxes fill in with the opposite chance; past 2.5 km only boxes. Also much faster.
  3. "render is fast": 64 samples + adaptive threshold, fewer transparent bounces (grass cut-outs).

  blender.exe -b blender/scenes/s08_finale_v071.blend --python scripts/s08_pass5.py   -> s08_finale_v072.blend
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = r"E:/Projects/tihar"
A = r"E:\Projects\tihar\blender\assets\osm"
CX, CY = 2000.0, -11000.0
NEAR_ANG = 27.0
R1, R2 = 1500.0, 2500.0
sc = bpy.context.scene

# ---- 1. mountains
him = bpy.data.objects["S01_Himalaya_GLO30"]
cam = bpy.data.objects["CAM_S08"].matrix_world.translation
piv = Vector((cam.x, cam.y, 0.0))
him.matrix_world = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-15), 4, "Z") @ Matrix.Translation(-piv) @ him.matrix_world
print("[p5] Himalaya turned -15 deg about the camera")

# ---- 2a. near city: dithered band
d = np.load(A + r"\s08_near.npz")
bv, bf = d["bv"], d["bf"]
off = np.concatenate([[0], np.cumsum(bf)])
cent = np.add.reduceat(bv[:, :2], off[:-1]) / bf[:, None]
dd = np.hypot(cent[:, 0] - CX, cent[:, 1] - CY)
ang = np.degrees(np.arctan2(cent[:, 0] - CX, cent[:, 1] - CY))
keep_p = np.clip((R2 - dd) / (R2 - R1), 0.0, 1.0)
rng = np.random.default_rng(55)
sel = np.where((np.abs(ang) < NEAR_ANG) & (dd > 150) & (rng.random(len(dd)) < keep_p))[0]
verts, faces = [], []
for i in sel:
    p = bv[off[i]:off[i + 1]]; s = len(verts)
    verts += p.tolist(); faces.append(list(range(s, s + len(p))))
for name in ("S08_NearCity", "S08_NearLights"):
    ob = bpy.data.objects[name]
    old = ob.data
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    for m in old.materials:
        me.materials.append(m)
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
print("[p5] near footprints", len(sel), "(was every one inside 3.5 km)")

# ---- 2b. far boxes: fill the band with the opposite chance; same cone
ng = bpy.data.node_groups["GN_S08_Buildings"]
N, Lk = ng.nodes, ng.links
dl = N["S08_Delete"]
cull_max = dl.inputs["Selection"].links[0].from_node       # MAXIMUM(MAXIMUM(near, thin), cone cull) - s08_pass3
mx = cull_max.inputs[0].links[0].from_node                  # MAXIMUM(near, far/altitude thin) - s08_upgrade
pos = N.new("GeometryNodeInputPosition")
sp = N.new("ShaderNodeSeparateXYZ"); Lk.new(pos.outputs[0], sp.inputs[0])


def m(op, a, b=None):
    n = N.new("ShaderNodeMath"); n.operation = op
    for i, v in ((0, a), (1, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            Lk.new(v, n.inputs[i])
    return n.outputs[0]


dx = m("SUBTRACT", sp.outputs[0], CX); dy = m("SUBTRACT", sp.outputs[1], CY)
dist = m("SQRT", m("ADD", m("MULTIPLY", dx, dx), m("MULTIPLY", dy, dy)))
cone = m("LESS_THAN", m("ABSOLUTE", dx), m("MULTIPLY", dy, math.tan(math.radians(NEAR_ANG))))
pdet = N.new("ShaderNodeMapRange"); pdet.inputs["From Min"].default_value = R1; pdet.inputs["From Max"].default_value = R2
pdet.inputs["To Min"].default_value = 1.0; pdet.inputs["To Max"].default_value = 0.0; Lk.new(dist, pdet.inputs["Value"])
rnd = N.new("FunctionNodeRandomValue"); rnd.data_type = "FLOAT"; rnd.inputs["Seed"].default_value = 77
rv = next(o for o in rnd.outputs if o.enabled and o.type == "VALUE")      # Blender 5: one output per type
near_del = m("MULTIPLY", cone, m("LESS_THAN", rv, pdet.outputs[0]))   # box removed where a detailed house stands
Lk.new(near_del, mx.inputs[0])                              # only the near term changes; thinning + cull stay
print("[p5] far boxes: dithered handover", R1, "-", R2, "m")

# ---- 3. faster render
c = sc.cycles
c.samples = 64; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.03
c.transparent_max_bounces = 6
c.use_denoising = True
print("[p5] samples", c.samples, "transparent bounces", c.transparent_max_bounces, "max bounces", c.max_bounces)

bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_finale_v072.blend")
print("[p5] saved", bpy.data.filepath)
