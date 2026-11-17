# s07: the Bhai Tika items appear on the empty thali one per scroll beat by slowly popping up in
# place (owner 2026-11-17: no hands). Each item grows from its own base (bbox bottom centre) with a
# soft overshoot and settle; the camera (Jamuna's eyes) turns a little toward it and back.
# Frames 1-12 top-down, 12-36 ease into the first-person view (keys from earlier, kept).
# The karuwa and the tapari + diyo are there from frame 1. The hands (collection S07_Hand) are
# excluded from the view layer, not deleted.
# Run inside s07_bhaitika_vNNN.blend (MCP exec). Rebuilds all item keys and the camera keys > 36.
import bpy
from mathutils import Vector

SC = bpy.context.scene
CAM = bpy.data.objects["CAM_S07"]
START, BEAT = 36, 24
GROW, SETTLE = 14, 6          # frames to grow (with overshoot), then settle to 1.0
OVER = 1.06
LOOK = 0.35                   # how far the head turns toward each item (0 = not at all)
ITEMS = [
    ("tika-dani", ["S07_TikaDani"]),
    ("sayapatri", ["S07_Sayapatri"]),
    ("makhamali", ["S07_Makhamali"]),
    ("okhar",     ["S07_Walnut", "S07_Walnut_2", "S07_Walnut_3"]),
    ("banana",    ["S07_Banana_0", "S07_Banana_1", "S07_Banana_2"]),
    ("apple",     ["S07_Apple"]),
    ("orange",    ["S07_Orange"]),
]


def tree(o): return [o] + list(o.children_recursive)


def find_lc(name, lc=None):
    lc = lc or bpy.context.view_layer.layer_collection
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find_lc(name, ch)
        if r: return r


def fcurves(o):
    a = o.animation_data
    if not a or not a.action: return []
    return [fc for l in a.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


# hands out of the scene (kept in the file)
for r in ("S04_Hand_Rig", "S04_HandL_Rig"):
    o = bpy.data.objects.get(r)
    if o and o.animation_data: o.animation_data_clear()
lc = find_lc("S07_Hand")
if lc: lc.exclude = True

# items back to their final state, no keys
SC.frame_set(1)
for _, names in ITEMS:
    for n in names:
        o = bpy.data.objects[n]
        if o.animation_data: o.animation_data_clear()
        if "s07_final" in o: o.location = Vector(o["s07_final"])
        else: o["s07_final"] = list(o.location)
        if "s07_scale" in o: o.scale = Vector(o["s07_scale"])
        else: o["s07_scale"] = list(o.scale)
        for m in tree(o):
            m.hide_render = False; m.hide_viewport = False
            if m is not o and m.animation_data and m.name.startswith("S07_"):
                pass
kar = bpy.data.objects["S07_Karuwa"]
if kar.animation_data: kar.animation_data_clear()
if "s07_final" in kar: kar.location = Vector(kar["s07_final"])
for m in tree(kar): m.hide_render = False; m.hide_viewport = False
bpy.context.view_layer.update()

# camera: keep keys up to START, rebuild the head turns after it
for fc in fcurves(CAM):
    for kp in [k for k in fc.keyframe_points if k.co.x > START + 0.5][::-1]:
        fc.keyframe_points.remove(kp)
SC.frame_set(START)
EYE = CAM.matrix_world.translation.copy()
BASE_ROT = CAM.rotation_euler.copy()
BASE_DIR = (CAM.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()


def cam_key(frame, d):
    CAM.rotation_euler = d.to_track_quat("-Z", "Y").to_euler("XYZ", BASE_ROT)
    CAM.keyframe_insert("rotation_euler", frame=frame)


def base_point(objs):
    P = [m.matrix_world @ Vector(c) for r in objs for m in tree(r) if m.type in {"MESH", "CURVE"} for c in m.bound_box]
    mn = Vector((min(p.x for p in P), min(p.y for p in P), min(p.z for p in P)))
    mx = Vector((max(p.x for p in P), max(p.y for p in P), max(p.z for p in P)))
    return Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z)), (mn + mx) / 2


for k, (label, names) in enumerate(ITEMS):
    f0 = START + k * BEAT
    objs = [bpy.data.objects[n] for n in names]
    pivot, centre = base_point(objs)
    for o in objs:
        L1, S1 = Vector(o["s07_final"]), Vector(o["s07_scale"])

        def key(frame, s, hidden=None):
            o.scale = S1 * s
            o.location = pivot + (L1 - pivot) * s          # scale about the item's own base
            o.keyframe_insert("scale", frame=frame); o.keyframe_insert("location", frame=frame)
            if hidden is not None:
                for m in tree(o):
                    m.hide_render = hidden; m.hide_viewport = hidden
                    m.keyframe_insert("hide_render", frame=frame); m.keyframe_insert("hide_viewport", frame=frame)

        key(1, 0.0, hidden=True)
        key(f0, 0.0, hidden=False)
        key(f0 + GROW, OVER)
        key(f0 + GROW + SETTLE, 1.0)
        o.scale = S1; o.location = L1
    # head turns a little toward the new item and back
    mid = (BASE_DIR * (1 - LOOK) + (centre - EYE).normalized() * LOOK).normalized()
    cam_key(f0, BASE_DIR); cam_key(f0 + 10, mid); cam_key(f0 + 17, mid); cam_key(f0 + 23, BASE_DIR)
    print("%-10s pops %d-%d" % (label, f0, f0 + GROW + SETTLE))

END = START + len(ITEMS) * BEAT
SC.frame_end = END + 24
for o in [CAM] + [bpy.data.objects[n] for _, ns in ITEMS for n in ns]:
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            if fc.data_path.startswith("hide"):
                kp.interpolation = "CONSTANT"
            else:
                kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
SC.frame_set(1)
print("all items in by", END, "- scene end", SC.frame_end)
