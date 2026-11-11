"""One-off: add OneClickDust "Air Dust" motes to s00 (v065 -> v066).

Run: blender.exe -b s00_enter_v065_realfire.blend --python scripts/s00_add_airdust.py -- <out.blend> [amount] [particle_scale]

The add-on's Air Dust is a room-sized box (~6.3 x 9.1 x 5.0 m) of geometry-node motes whose motion
is scene time + noise (no simulation). Here it is scaled to a ~0.6 m pocket of air around the diyo,
between it and the camera, so the motes catch the flame light. The gust (blow-out, frames 101+)
is done by moving the whole cloud toward screen-right: keys live in s00_render_headless.py.
"""
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
amount = int(argv[1]) if len(argv) > 1 else 1500
pscale = float(argv[2]) if len(argv) > 2 else 0.5

ADDON_BLEND = bpy.utils.user_resource("SCRIPTS", path="addons/OneClickDust/Oneclickdust.blend")
TARGET_CENTER = Vector((-0.12, -0.04, 0.10))   # between camera and diyo, a bit above the table
TARGET_SPAN_Y = 0.6                              # metres along the box's long side

def _set_material_nodes(g):
    for n in g.nodes:
        if n.type == "SET_MATERIAL":
            yield n
        elif n.type == "GROUP" and n.node_tree:
            yield from _set_material_nodes(n.node_tree)


def _walk_set_material(g):
    for n in _set_material_nodes(g):
        m = n.inputs["Material"].default_value
        if m:
            yield m


o = bpy.data.objects.get("S00_AirDust")
if o is None:
    with bpy.data.libraries.load(ADDON_BLEND, link=False) as (src, dst):
        dst.objects = ["AirDust"]
    o = dst.objects[0]
    o.name = "S00_AirDust"
    coll = bpy.data.collections.get("FX") or bpy.context.scene.collection
    coll.objects.link(o)

# uniform scale so the long side is TARGET_SPAN_Y, then centre the box on TARGET_CENTER
o.rotation_euler = (0, 0, 0)
o.scale = (1, 1, 1)
bpy.context.view_layer.update()
mesh_dims = o.dimensions.copy()
k = TARGET_SPAN_Y / max(mesh_dims)
o.scale = (k, k, k)
bpy.context.view_layer.update()
corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
center = sum(corners, Vector()) / 8
o.location += TARGET_CENTER - center
bpy.context.view_layer.update()

ins = o.modifiers[0].properties.inputs
names = {it.name.strip(): it.identifier for it in o.modifiers[0].node_group.interface.items_tree
         if getattr(it, "in_out", None) == "INPUT"}
getattr(ins, names["Amount"]).value = amount
getattr(ins, names["Particle Scale"]).value = pscale
# the add-on's material glows (white emission 1.0), so every mote shows even in the dark;
# our copy has no emission: motes appear only where the flame light catches them
src_mat = next(n for n in _walk_set_material(o.modifiers[0].node_group))
mat = bpy.data.materials.get("M_S00_AirDust") or src_mat.copy()
mat.name = "M_S00_AirDust"
em = next(n for n in mat.node_tree.nodes if n.type == "EMISSION")
em.inputs["Strength"].default_value = 0.0
for n in _set_material_nodes(o.modifiers[0].node_group):
    n.inputs["Material"].default_value = mat
o["s00_base_location"] = list(o.location)
print("[dust] scale", round(k, 4), "dims", tuple(round(v, 3) for v in o.dimensions),
      "loc", tuple(round(v, 3) for v in o.location), "amount", amount, "pscale", pscale)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("[dust] saved", out)
