# Finger poses for the S04 right hand (rig "S04_Hand_Rig", from Sketchfab "hands animation" by hugocolauto).
# Builds three pose actions, each with a fake user and marked as a pose asset:
#   HandRest       relaxed, fingers softly bent
#   HandHoldMala   loose curl, thumb to index/middle, as if holding a garland strand from above
#   HandTika       ring finger extended (the tika finger), others loosely curled, thumb relaxed
# exec(open(r"E:/Projects/tihar/scripts/s04_hand_poses.py").read())     then  apply_pose("HandTika")
import bpy, math
from mathutils import Vector, Quaternion

ARM = bpy.data.objects["S04_Hand_Rig"]
B = ARM.data.bones
FINGERS = {
    "index": ["INDEX_BASE_joint_03", "INDEX_MID_joint_04", "INDEX_TOP_joint_05"],
    "middle": ["MIDDLE_F_BASE_joint_07", "MIDDLE_F_MID_joint_08", "MIDDLE_F_TOP_joint_09"],
    "ring": ["RING_BASE_joint_011", "RING_MID_joint_012", "RING_TOP_joint_013"],
    "pinky": ["PINK_BASE_joint_015", "PINK_MID_joint_016", "PINK_TOP_joint_017"],
    "thumb": ["THUMB_BASE_joint_019", "THUMB_MID_joint_020", "THUMB_TOP_joint_021"],
}
# palm normal from the nail positions (nails face the back of the hand): rest pose, armature space
PALM_N = Vector((0.7, -0.7, 0.0)).normalized()
SIDE = (B["THUMB_BASE_joint_019"].head_local - B["PINK_BASE_joint_015"].head_local).normalized()  # towards the thumb

def curl_quat(bone_name, flex_deg, spread_deg=0.0, twist_deg=0.0):
    """rotation in the bone's rest frame: flex towards the palm, spread towards the thumb side"""
    b = B[bone_name]
    # FBX bone tails are arbitrary: use the direction to the next joint along the finger
    nxt = b.children[0] if b.children else None
    d = ((nxt.head_local if nxt else b.tail_local) - b.head_local).normalized()
    k_flex = d.cross(PALM_N).normalized()           # rotating d about k moves it towards the palm
    k_spread = d.cross(SIDE).normalized()
    inv = b.matrix_local.to_3x3().inverted()
    q = Quaternion(inv @ k_flex, math.radians(flex_deg))
    if spread_deg:
        q = Quaternion(inv @ k_spread, math.radians(spread_deg)) @ q
    if twist_deg:
        q = Quaternion(inv @ d, math.radians(twist_deg)) @ q
    return q

# degrees per joint: (MCP, PIP, DIP); thumb: (CMC, MCP, IP); optional spread on the first joint
# thumb aim: (target bone whose posed head the thumb tip should approach, fraction 0..1)
THUMB_AIM = {"HandRest": ("INDEX_MID_joint_04", 0.25), "HandHoldMala": ("INDEX_MID_joint_04", 0.9),
             "HandTika": ("INDEX_MID_joint_04", 0.55)}
POSES = {
    "HandRest": dict(
        index=((12, 18, 10), 2), middle=((15, 22, 12), 0), ring=((18, 26, 14), -2), pinky=((22, 30, 15), -5),
        thumb=((12, 10, 12), 6)),
    "HandHoldMala": dict(
        index=((40, 50, 30), 4), middle=((48, 58, 32), 0), ring=((55, 62, 35), -3), pinky=((60, 66, 35), -6),
        thumb=((30, 18, 25), 22)),
    "HandTika": dict(
        index=((48, 70, 40), 3), middle=((55, 78, 45), 0), ring=((2, 4, 2), -2), pinky=((62, 82, 45), -4),
        thumb=((18, 15, 15), 12)),
}

def apply_pose(name, key=False, frame=1, arm=None):
    """arm: the rig to pose (default the right hand; works for the mirrored left rig too)"""
    ARM = arm or bpy.data.objects["S04_Hand_Rig"]
    for pb in ARM.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    for finger, (angles, spread) in POSES[name].items():
        for i, (bn, a) in enumerate(zip(FINGERS[finger], angles)):
            pb = ARM.pose.bones[bn]
            pb.rotation_quaternion = curl_quat(bn, a, spread if i == 0 else 0.0)
    aim = THUMB_AIM.get(name)
    if aim:
        bpy.context.view_layer.update()
        P = ARM.pose.bones
        base = P["THUMB_BASE_joint_019"]
        tip = P["THUMB_UP_TOP_joint_022"].head
        tgt = P[aim[0]].head + SIDE * 0.012          # stop beside the index finger, not inside it
        cur = (tip - base.head).normalized(); want = (tgt - base.head).normalized()
        q_arm = Quaternion().slerp(cur.rotation_difference(want), aim[1])
        R = base.bone.matrix_local.to_quaternion()
        base.rotation_quaternion = R.inverted() @ q_arm @ R @ base.rotation_quaternion
    if key:
        for chain in FINGERS.values():
            for bn in chain:
                ARM.pose.bones[bn].keyframe_insert("rotation_quaternion", frame=frame, group=bn)

def build_pose_actions():
    ad = ARM.animation_data or ARM.animation_data_create()
    for name in POSES:
        old = bpy.data.actions.get(name)
        if old: bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        ad.action = act
        apply_pose(name, key=True)
        act.use_fake_user = True
        try:
            act.asset_mark(); act.asset_generate_preview()
        except Exception as e:
            print("[poses] asset mark failed", e)
        ad.action = None
    apply_pose("HandRest")
    print("[poses] built", list(POSES))

if __name__ == "__main__" or True:
    build_pose_actions()
