# s07: Jamuna fills the Bhai Tika thali, seen through her eyes (first-person view).
# Camera CAM_S07 = her eyes, kneeling at the plate (frames 1-12 top-down, 12-36 ease into FPP).
# Her hands (the s04/s05 tika hands: S04_Hand_Rig right, S04_HandL_Rig left = X-mirrored copy)
# come up from below the frame; each forearm points back to a shoulder just below/beside the
# camera and the sleeves are extended past it, so the cut end of an arm is never on screen.
# Two hands carry the tika-dani, both malas and the walnuts; one hand places each fruit.
# Each beat the camera (her head) turns part-way toward where the item goes, then back.
# The karuwa stands on the floor from frame 1.
# Run inside s07_bhaitika_vNNN.blend (MCP exec). Rebuilds all keys after frame 36; item final
# positions are kept in the custom property "s07_final".
import bpy, math
from mathutils import Vector, Matrix, Quaternion

exec(open(r"E:/Projects/tihar/scripts/s04_hand_poses.py", encoding="utf-8").read())   # apply_pose, PALM_N

SC = bpy.context.scene
CAM = bpy.data.objects["CAM_S07"]
RR = bpy.data.objects["S04_Hand_Rig"]
RL = bpy.data.objects["S04_HandL_Rig"]
VIEW = Vector((0.8, -0.6, 0)).normalized()        # from the plate toward Jamuna
RIGHT = Vector((-VIEW.y, VIEW.x, 0))              # her right / screen right
UP = Vector((0, 0, 1))
START, BEAT = 36, 24
ITEMS = [   # label, root objects, hands ("two" | "right"), grip ("sides" | "ends" | "top")
    ("tika-dani", ["S07_TikaDani"], "two", "sides"),
    ("sayapatri", ["S07_Sayapatri"], "two", "ends"),
    ("makhamali", ["S07_Makhamali"], "two", "ends"),
    ("okhar",     ["S07_Walnut", "S07_Walnut_2", "S07_Walnut_3"], "two", "sides"),
    ("banana",    ["S07_Banana_0", "S07_Banana_1", "S07_Banana_2"], "right", "top"),
    ("apple",     ["S07_Apple"], "right", "top"),
    ("orange",    ["S07_Orange"], "right", "top"),
]
MX = Matrix.Diagonal((-1, 1, 1))                  # the left rig's mirror


def tree(o): return [o] + list(o.children_recursive)


def clear_keys(o):
    if o.animation_data: o.animation_data_clear()


def world_bbox(objs):
    P = [m.matrix_world @ Vector(c) for r in objs for m in tree(r) if m.type in {"MESH", "CURVE"} for c in m.bound_box]
    return (Vector((min(p.x for p in P), min(p.y for p in P), min(p.z for p in P))),
            Vector((max(p.x for p in P), max(p.y for p in P), max(p.z for p in P))))


# ---------------------------------------------------------------- items back to their final place
SC.frame_set(1)
for _, names, _, _ in ITEMS:
    for n in names:
        o = bpy.data.objects[n]; clear_keys(o)
        if "s07_final" in o: o.location = Vector(o["s07_final"])
        else: o["s07_final"] = list(o.location)
        for m in tree(o): m.hide_render = False; m.hide_viewport = False
kar = bpy.data.objects["S07_Karuwa"]            # on the floor from the start
clear_keys(kar)
if "s07_final" in kar: kar.location = Vector(kar["s07_final"])
for m in tree(kar): m.hide_render = False; m.hide_viewport = False
bpy.context.view_layer.update()

# ---------------------------------------------------------------- her eyes, shoulders, lap
ad = CAM.animation_data
for fc in [fc for l in ad.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]:
    for kp in [k for k in fc.keyframe_points if k.co.x > START + 0.5][::-1]:
        fc.keyframe_points.remove(kp)
SC.frame_set(START)
EYE = CAM.matrix_world.translation.copy()
BASE_ROT = CAM.rotation_euler.copy()
BASE_DIR = (CAM.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
SHOULDER = {"R": EYE + RIGHT * 0.17 - UP * 0.24, "L": EYE - RIGHT * 0.17 - UP * 0.24}
FWD = -VIEW
PULL = 0.05          # rest = 18 % of the way from the shoulder to the target: below the frame, and the
                     # forearm still points back past the camera (a hand under the lens would point its
                     # sleeve up into view)
PLATE_C = Vector(bpy.data.objects["S07_Thali_Root"].location)
def rest(side, target): return SHOULDER[side] + (target - SHOULDER[side]) * PULL
LAP = {"R": rest("R", PLATE_C + RIGHT * 0.1), "L": rest("L", PLATE_C - RIGHT * 0.1)}
MID_SH = (SHOULDER["R"] + SHOULDER["L"]) / 2


def look_dir(d):
    return d.to_track_quat("-Z", "Y").to_euler("XYZ", BASE_ROT)


def cam_key(frame, d):
    CAM.rotation_euler = look_dir(d); CAM.keyframe_insert("rotation_euler", frame=frame)


# ---------------------------------------------------------------- hands
for r in (RR, RL):
    clear_keys(r); r.rotation_mode = "QUATERNION"; r.location = (0, 0, 0); r.rotation_quaternion = (1, 0, 0, 0)
apply_pose("HandHoldMala", arm=RR); apply_pose("HandHoldMala", arm=RL)
bpy.context.view_layer.update()
GRIP = {}
for side, r in (("R", RR), ("L", RL)):
    pb = r.pose.bones
    GRIP[side] = (pb["THUMB_UP_TOP_joint_022"].head + pb["INDEX_UP_TOP_joint_00"].head) / 2   # armature space
PALM_L = PALM_N.normalized()


def hand_rot(side, F, P):
    """rotation so local fingers (+Z) -> F and the palm -> P (left rig: through its X mirror)"""
    a = Vector((0, 0, 1)); b = PALM_L if side == "R" else (MX @ PALM_L)
    b = (b - a * b.dot(a)).normalized()
    P = (P - F * P.dot(F)).normalized()
    Lb = Matrix((a, b, a.cross(b))).transposed()
    Wb = Matrix((F, P, F.cross(P))).transposed()
    return (Wb @ Lb.inverted()).to_quaternion()


def hand_key(side, frame, grip_w, palm_dir, pose=None):
    r = RR if side == "R" else RL
    F = (grip_w - SHOULDER[side]).normalized()                 # forearm points back to the shoulder
    q = hand_rot(side, F, palm_dir)
    local = GRIP[side] if side == "R" else MX @ GRIP[side]
    r.rotation_quaternion = q
    r.location = grip_w - (q.to_matrix() @ local)
    r.keyframe_insert("location", frame=frame); r.keyframe_insert("rotation_quaternion", frame=frame)
    if pose: apply_pose(pose, key=True, frame=frame, arm=r)


DOWN = -UP
for side in ("R", "L"):
    hand_key(side, 1, LAP[side], DOWN, "HandRest")
    hand_key(side, START, LAP[side], DOWN, "HandRest")


def vis_key(objs, frame, hidden):
    for r in objs:
        for m in tree(r):
            m.hide_render = hidden; m.hide_viewport = hidden
            m.keyframe_insert("hide_render", frame=frame); m.keyframe_insert("hide_viewport", frame=frame)


def mala_ends(curve_ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = curve_ob.evaluated_get(dg).to_mesh()
    pts = [curve_ob.matrix_world @ v.co for v in me.vertices]
    curve_ob.evaluated_get(dg).to_mesh_clear()
    best = max(((p, q) for i, p in enumerate(pts[::3]) for q in pts[i * 3::3]), key=lambda t: (t[0] - t[1]).length)
    return best


for k, (label, names, hands, grip) in enumerate(ITEMS):
    f0 = START + k * BEAT
    objs = [bpy.data.objects[n] for n in names]
    finals = {o: o.location.copy() for o in objs}
    mn, mx = world_bbox(objs); c_final = (mn + mx) / 2
    # grip points relative to the item's centre
    if grip == "sides":
        half = max(0.03, (mx - mn).dot(RIGHT.normalized()) / 2 + 0.008)
        g_rel = {"R": RIGHT * half + UP * 0.004, "L": -RIGHT * half + UP * 0.004}
    elif grip == "ends":
        p, q = mala_ends(objs[0])
        pr, pl = (p, q) if (p - q).dot(RIGHT) > 0 else (q, p)
        g_rel = {"R": pr - c_final + UP * 0.01, "L": pl - c_final + UP * 0.01}
    else:
        g_rel = {"R": Vector((0, 0, mx.z - c_final.z - 0.004))}
    palm = {"R": (DOWN * 0.6 - RIGHT * 0.4) if hands == "two" else DOWN, "L": DOWN * 0.6 + RIGHT * 0.4}
    path = [  # (frame, item centre, hand pose)
        (f0,      MID_SH + (c_final - MID_SH) * PULL, "HandHoldMala"),
        (f0 + 10, c_final + UP * 0.06,             "HandHoldMala"),
        (f0 + 14, c_final,                         "HandHoldMala"),
    ]
    vis_key(objs, 1, True); vis_key(objs, f0, False)
    for frame, centre, pose in path:
        for o in objs:
            o.location = finals[o] + (centre - c_final); o.keyframe_insert("location", frame=frame)
        for side in g_rel:
            hand_key(side, frame, centre + g_rel[side], palm[side], pose)
    for side in g_rel:                                     # release, lift, back to the lap
        g = c_final + g_rel[side]
        hand_key(side, f0 + 17, g + UP * 0.01, palm[side], "HandRest")
        hand_key(side, f0 + 19, g + UP * 0.05 + VIEW * 0.03, palm[side])
        hand_key(side, f0 + 23, LAP[side], DOWN, "HandRest")
    for o in objs: o.location = finals[o]
    # her head follows the hands part-way and comes back
    to_item = (c_final - EYE).normalized()
    mid = (BASE_DIR * 0.5 + to_item * 0.5).normalized()
    cam_key(f0, BASE_DIR); cam_key(f0 + 9, mid); cam_key(f0 + 16, mid); cam_key(f0 + 23, BASE_DIR)
    print("%-10s %s-hand  frames %d-%d" % (label, hands, f0, f0 + 23))

END = START + len(ITEMS) * BEAT
SC.frame_end = END + 24
for o in [RR, RL, CAM] + [bpy.data.objects[n] for _, ns, _, _ in ITEMS for n in ns]:
    a = o.animation_data
    if not a or not a.action: continue
    for l in a.action.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT" if fc.data_path.startswith("hide") else "BEZIER"
SC.frame_set(1)
print("placing ends at", END)
