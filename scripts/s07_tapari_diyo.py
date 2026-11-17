# s07: the single Bhai Tika diyo, sitting in the owner's leaf tapari heaped with rice, on the right
# of the thali (as seen from the angled camera). The diyo is the s00 scan with its RealFire flame.
# Run inside s07_bhaitika_vNNN.blend after s07_build_thali.py (MCP exec).
#
# Flame fix (2026-11-17): appending the s00 flame objects and re-parenting them by matrix_basis
# shrank the pivot's children ~1000x (flame invisible). Here every appended object is put back at
# its exact s00 world matrix (stored in the file), with parent inverses solved from those matrices.
import bpy, math
from mathutils import Vector, Matrix

S00 = "E:/Projects/tihar/blender/scenes/s00_enter_v068_realfire.blend"
LIGHT_W = 1.4
VIEW = Vector((0.8, -0.6, 0)).normalized()          # camera sits at plate + VIEW (looks along -VIEW)
RIGHT = Vector((-VIEW.y, VIEW.x, 0))                # screen right for that camera (forward x up)
OFFSET = 0.32                                        # plate centre -> tapari centre (plate R 0.24, tapari R ~0.10)
TAPARI_SCALE = 0.48                                  # owner: smaller again (Ø ~19 cm)
RICE_TOP = 0.042                                     # heap top above the floor (tapari ~5 cm deep here)

col = bpy.data.collections["S07_Thali"]
root = bpy.data.objects["S07_Thali_Root"]
centre = root.matrix_world.translation.copy(); centre.z = 0.0
base = centre + RIGHT * OFFSET + VIEW * 0.06          # beside the plate, a little toward the camera

for o in list(col.objects):
    if o.name.startswith(("S07_Tapari", "S07_TapariRice", "S07_Diyo")):
        bpy.data.objects.remove(o, do_unlink=True)

# --- tapari: a copy of the owner's leaf tapari from the s02 kausi -------------------------------
src = bpy.data.objects["model.002"]
tap = src.copy(); tap.name = "S07_Tapari"; tap.parent = None
col.objects.link(tap)
s = src.matrix_world.to_scale().x * TAPARI_SCALE
tap.matrix_world = Matrix.LocRotScale(Vector((0, 0, 0)), src.matrix_world.to_quaternion(), Vector((s, s, s)))
bpy.context.view_layer.update()
bb = [tap.matrix_world @ Vector(c) for c in tap.bound_box]
mid = sum(bb, Vector()) / 8
tap.location += Vector((base.x - mid.x, base.y - mid.y, -min(v.z for v in bb)))
bpy.context.view_layer.update()

# --- rice heap: a copy of the s03 rice mound (GN rice scatter), scaled into the tapari ----------
rs = bpy.data.objects["S03_RiceMound"]
rice = rs.copy(); rice.name = "S07_TapariRice"; rice.parent = None
rice.hide_render = False; rice.hide_viewport = False; rice.hide_set(False)
col.objects.link(rice)
# owner: the rice fills the tapari completely - heap as wide as the leaf bowl, its edge tucked
# under the leaf wall, the dome standing ~8 mm above the rim
k = 0.84 * tap.dimensions.x / max(rs.dimensions.x, 1e-6)
rice.scale = (k, k, k * 1.0)
RICE_TOP = max(v.z for v in bb) - min(v.z for v in bb) + 0.010
bpy.context.view_layer.update()
rb = [rice.matrix_world @ Vector(c) for c in rice.bound_box]
rmid = sum(rb, Vector()) / 8
rice.location += Vector((base.x - rmid.x, base.y - rmid.y, RICE_TOP - max(v.z for v in rb)))
bpy.context.view_layer.update()

# --- the diyo, appended with exact s00 world matrices -------------------------------------------
want = ["S00_DiyoScan_Mesh", "S00_Oil", "S00_Wick", "S00_WickTip", "S00_FlamePivot", "S00_FireVol",
        "S00_FireVol_B", "S00_FlameCore", "L_S00_Flame"]
with bpy.data.libraries.load(S00, link=False) as (lib, dst):
    dst.objects = [n for n in lib.objects if n in want]
objs = list(dst.objects)
def chain(o):          # s00 world matrix through the full parent chain (appended parents aren't evaluated)
    return chain(o.parent) @ o.matrix_parent_inverse @ o.matrix_basis if o.parent else o.matrix_basis.copy()
W = {o: chain(o) for o in objs}
e = bpy.data.objects.new("S07_Diyo", None)
col.objects.link(e)
inset = set(objs)
for o in objs:
    col.objects.link(o)
for o in objs:                                          # solve parent inverses: P @ inv @ basis = W
    p = o.parent if o.parent in inset else e
    o.parent = p
    PW = W[p] if p in inset else Matrix.Identity(4)
    o.matrix_parent_inverse = PW.inverted() @ W[o] @ o.matrix_basis.inverted()
for o in objs:
    o.name = "S07_Diyo_" + o.name.replace("S00_", "").split(".")[0]
    if o.type == "LIGHT":
        o.data = o.data.copy(); o.data.energy = LIGHT_W
bpy.context.view_layer.update()
dy = [o for o in objs if o.name.startswith("S07_Diyo_DiyoScan")][0]
db = [dy.matrix_world @ Vector(c) for c in dy.bound_box]
dmid = sum(db, Vector()) / 8
to_plate = (centre - base).normalized()
e.rotation_euler = (0, 0, math.atan2(to_plate.y, to_plate.x))   # spout (s00 local +x) toward the plate, flame in view
e.location = Vector((base.x, base.y, RICE_TOP - 0.006)) - Vector((dmid.x, dmid.y, min(v.z for v in db)))
bpy.context.view_layer.update()
print("tapari", tuple(round(v, 3) for v in tap.dimensions), "rice", tuple(round(v, 3) for v in rice.dimensions))
fv = [o for o in objs if o.name.startswith("S07_Diyo_FireVol")][0]
print("diyo dims", tuple(round(v, 3) for v in dy.dimensions), "flame world scale", tuple(round(v, 3) for v in fv.matrix_world.to_scale()))

# --- centre rice + diyo on the leaf bowl's vertex centroid (its bounding box is lopsided) ----------
vs = [tap.matrix_world @ v.co for v in tap.data.vertices]
cx = sum(v.x for v in vs) / len(vs); cy = sum(v.y for v in vs) / len(vs)
rb = [rice.matrix_world @ Vector(c) for c in rice.bound_box]; rm = sum(rb, Vector()) / 8
shift = Vector((cx - rm.x, cy - rm.y, 0))
rice.location += shift; e.location += shift
