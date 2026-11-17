# s06: the Deusi group (Procedural Crowds v2.1.2 individuals, official giveaway — see memory
# addon-licences). They stand in an arc south of the thali, facing north toward the house, so the
# camera (coming from the south) only ever sees their backs; a gap at x=0 lets it fly through.
# Rebuilds collection S06_Deusi each run.
import bpy, math, random
from pathlib import Path

random.seed(66)
PACK = Path(r"C:\Users\user\Downloads\Procedural Crowds v2.1.2\Procedural_Crowds_Assets_v2.0.0\Individuals\Casual Humans")
PEOPLE = [("Men", "Man 01"), ("Women", "Woman 01"), ("Men", "Man 02"), ("Women", "Woman 02"),
          ("Men", "Man 03"), ("Women", "Woman 04"), ("Men", "Man 10 Pose")]
ANIMS = ["Cheering 01", "Cheering 02", "Idle 01", "Cheering 03", "Idle 02", "Cheering 01", None]
FLOOR = 0.011
RAD = 1.35
# angles (deg, 270 = due south); the gap at 270 is the camera's way through
ANG = [222, 236, 250, 293, 306, 320, 208]

col = bpy.data.collections.get("S06_Deusi")
if col:
    for o in list(col.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("S06_Deusi")
    bpy.context.scene.collection.children.link(col)


def load_action(anim):
    if anim is None:
        return None
    f = next((PACK / "Animations" / anim).glob("*.blend"))
    name = "HQ_" + anim.replace(" ", "_")
    if name in bpy.data.actions:
        return bpy.data.actions[name]
    with bpy.data.libraries.load(str(f), link=False) as (src, dst):
        dst.actions = [a for a in src.actions if a == name]
    return dst.actions[0]


for k, ((sub, person), anim, ang) in enumerate(zip(PEOPLE, ANIMS, ANG)):
    f = next((PACK / "SubCategories" / sub / "High" / person).glob("*.blend"))
    mn = person.replace(" ", "_")
    want = [f"IND_{mn}", f"IND_{mn}_Armature"]
    with bpy.data.libraries.load(str(f), link=False) as (src, dst):
        dst.objects = [o for o in src.objects if o in want]
    arm = next(o for o in dst.objects if o.type == "ARMATURE")
    body = next(o for o in dst.objects if o.type != "ARMATURE")
    for o in dst.objects:
        col.objects.link(o)
    a = math.radians(ang + random.uniform(-2, 2))
    r = RAD + random.uniform(-0.12, 0.12)
    arm.location = (r * math.cos(a), r * math.sin(a), FLOOR)
    # face north (+Y) toward the house, turned a little toward the thali
    arm.rotation_euler = (0, 0, (a - math.radians(270)) * 0.35)
    arm.name = f"S06_Deusi_{k}_Rig"; body.name = f"S06_Deusi_{k}"
    act = load_action(anim)
    if act:
        arm.animation_data_create()
        arm.animation_data.action = act
        if hasattr(arm.animation_data, "action_slot") and act.slots:
            arm.animation_data.action_slot = act.slots[0]
        # desync: each one starts at a different point of its loop
        if arm.animation_data.action:
            tr = arm.animation_data.nla_tracks.new()
            st = tr.strips.new(act.name, int(1 - random.uniform(0, 40)), act)
            st.repeat = 4
            arm.animation_data.action = None
print("deusi:", [o.name for o in col.objects])
