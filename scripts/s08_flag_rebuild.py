"""Rebuild the s08 flag as a true double-pennant cloth (owner 2026-11-20: "rebuild the flag mesh
now ... flag pole make it little less height ... increase the size of flag according to pole").

Run inside the live Blender:  exec(open(r"E:/Projects/tihar/scripts/s08_flag_rebuild.py", encoding="utf-8").read())

- Outline from blender/assets/s08/nepal_flag_outline.json (scripts/s08_nepal_flag.py, Constitution
  Schedule 1, ratio 1.21901033). The mesh is the flag's real shape, not a rectangle with alpha,
  so no invisible corners pull on the folds.
- Even 3 cm grid clipped to the outline, edge vertices snapped onto it; UVs = the texture's box.
- Pole 6 m -> 4 m. Flag hoist 1.35 m (~1/3 of the pole, the usual proportion), fly 1.107 m.
- Hoist edge pinned; pole is a collider; self-collision on; Subdivision after the cloth for
  smooth folds; 2 mm Solidify so the hem catches light.
"""
import json
import math

import bmesh
import bpy
from mathutils import Vector

POLE_H = 4.0
FLAG_H = 1.35
STEP = 0.03

ol = json.load(open(r"E:/Projects/tihar/blender/assets/s08/nepal_flag_outline.json"))
poly = [tuple(p) for p in ol["outer"]]
s = FLAG_H / ol["height"]
W, Hh = ol["width"], ol["height"]


def inside(x, y):
    c = False; n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def snap(x, y):
    best = None
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        px, py = x1 + t * dx, y1 + t * dy
        d = (px - x) ** 2 + (py - y) ** 2
        if best is None or d < best[0]:
            best = (d, px, py)
    return best[1], best[2]


# ---- grid in flag units
st = STEP / s
nx, ny = int(math.ceil(W / st)) + 1, int(math.ceil(Hh / st)) + 1
bm = bmesh.new()
grid = {}
keep = []
for j in range(ny - 1):
    for i in range(nx - 1):
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        pts = [(min(a * st, W), min(b * st, Hh)) for a, b in corners]
        if any(inside(x, y) for x, y in pts):
            keep.append(corners)
for c in keep:
    for k in c:
        if k not in grid:
            grid[k] = None
for k in grid:
    x, y = min(k[0] * st, W), min(k[1] * st, Hh)
    if not inside(x, y):
        x, y = snap(x, y)
    grid[k] = bm.verts.new((-x * s, 0.0, y * s))          # flies toward -X (the wind's direction)
for c in keep:
    vs = [grid[k] for k in c]
    if len({id(v) for v in vs}) == 4:
        try:
            bm.faces.new(vs)
        except ValueError:
            pass
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=STEP * 0.25)
# drop slivers left by snapping
bad = [f for f in bm.faces if f.calc_area() < (STEP * STEP) * 0.08]
bmesh.ops.delete(bm, geom=bad, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for lp in f.loops:
        lp[uv].uv = (-lp.vert.co.x / s / W, lp.vert.co.z / s / Hh)
me = bpy.data.meshes.new("S08_Flag_Pennant")
bm.to_mesh(me); bm.free()

flag = bpy.data.objects["S08_Flag"]; pole = bpy.data.objects["S08_FlagPole"]
old = flag.data
mat = old.materials[0]
flag.data = me
me.materials.append(mat)
for p in me.polygons:
    p.use_smooth = True
if old.users == 0:
    bpy.data.meshes.remove(old)
vg = flag.vertex_groups.get("pin") or flag.vertex_groups.new(name="pin")
vg.add([v.index for v in me.vertices], 0.0, "REPLACE")
vg.add([v.index for v in me.vertices if v.co.x > -0.012], 1.0, "REPLACE")

# ---- pole: 4 m, same foot on the ground
ground = pole.location.z - pole.dimensions.z / 2
pole.scale.z *= POLE_H / pole.dimensions.z
pole.location.z = ground + POLE_H / 2
top = ground + POLE_H
flag.location = (pole.location.x - 0.03, pole.location.y, top - 0.08 - FLAG_H)
# small brass finial on top
fin = bpy.data.objects.get("S08_FlagFinial")
if fin is None:
    fm = bpy.data.meshes.new("S08_FlagFinial")
    b2 = bmesh.new(); bmesh.ops.create_uvsphere(b2, u_segments=16, v_segments=8, radius=0.045); b2.to_mesh(fm); b2.free()
    for p in fm.polygons:
        p.use_smooth = True
    fin = bpy.data.objects.new("S08_FlagFinial", fm); pole.users_collection[0].objects.link(fin)
    mb = bpy.data.materials.get("M_S08_Brass") or bpy.data.materials.new("M_S08_Brass")
    mb.use_nodes = True
    b = next(n for n in mb.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.75, 0.55, 0.25, 1); b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.35
    fm.materials.append(mb)
fin.location = (pole.location.x, pole.location.y, top + 0.03)
if not any(m.type == "COLLISION" for m in pole.modifiers):
    pole.modifiers.new("Collision", "COLLISION")
pole.collision.thickness_outer = 0.01

# ---- cloth: cotton, self collision, smooth + thickness after the sim
cm = next(m for m in flag.modifiers if m.type == "CLOTH")
cs = cm.settings
cs.vertex_group_mass = "pin"
cs.quality = 8
cs.mass = 0.15                     # kg per vertex-ish: light cotton at 3 cm spacing
cs.tension_stiffness = 15; cs.compression_stiffness = 15; cs.shear_stiffness = 5
cs.bending_stiffness = 0.05
cs.air_damping = 1.0
cc = cm.collision_settings
cc.use_self_collision = True; cc.self_distance_min = 0.004; cc.distance_min = 0.008
cm.point_cache.frame_start = 1; cm.point_cache.frame_end = 200
for name, kind in (("S08_FlagSubsurf", "SUBSURF"), ("S08_FlagSolidify", "SOLIDIFY")):
    if name not in flag.modifiers:
        m = flag.modifiers.new(name, kind)
sub = flag.modifiers["S08_FlagSubsurf"]; sub.levels = 1; sub.render_levels = 1
sol = flag.modifiers["S08_FlagSolidify"]; sol.thickness = 0.002; sol.offset = 0.0
print("flag verts", len(me.vertices), "faces", len(me.polygons), "size %.3f x %.3f m" % (W * s, FLAG_H),
      "pole top %.2f" % top)
