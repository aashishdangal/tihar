# Make the LEFT hand as a mirror of the right S04 hand (object scale -1 on X, shared mesh data).
# Objects: S04_HandL_Rig (armature, scale -1,1,1) with children S04_HandL, S04_HandL_Forearm,
# S04_HandL_Sleeve, S04_HandL_SleeveHem, S04_HandL_RedThread. Poses: apply_pose(name, arm=S04_HandL_Rig)
# or assign the same pose actions (bone names match; the mirror is in the object transform).
# exec(open(r"E:/Projects/tihar/scripts/s04_hand_make_left.py").read())
import bpy
R = bpy.data.objects["S04_Hand_Rig"]
old = bpy.data.objects.get("S04_HandL_Rig")
if old:
    for c in list(old.children): bpy.data.objects.remove(c)
    bpy.data.objects.remove(old)
L = R.copy(); L.data = R.data.copy(); L.data.name = "S04_HandL_Rig"; L.name = "S04_HandL_Rig"
L.animation_data_clear()
for c in R.users_collection: c.objects.link(L)
L.scale = (-1, 1, 1); L.location = (0.35, 0, 0)
for c in R.children:
    if c.name == "S04_TikaFinger": continue           # the tika is done with the right hand only
    n = c.copy()                                     # shares mesh / curve data with the right hand
    n.name = c.name.replace("S04_Hand", "S04_HandL")
    for col in c.users_collection: col.objects.link(n)
    n.parent = L
    for m in n.modifiers:
        if m.type == "ARMATURE": m.object = L
print("[left] made", L.name, [c.name for c in L.children])
