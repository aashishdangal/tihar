# s04 animation pass 1 (frames 1-100): camera arrives through the portico ceiling and glides out
# to the dog in the courtyard centre; the dog sits excited (panting, tongue, wagging tail, ears);
# beat 1 (40-66): two hands lower the marigold mala over its head onto the neck;
# beat 2 (66-86): the right hand presses the tika with its (reddish) ring finger, the stain fades in;
# 86-100: caption hold. The trot to the exit door (100-125) comes in a later pass.
# blender.exe -b blender/scenes/s04_kukur_v002.blend --python scripts/s04_animate.py -- <out.blend>
import bpy, sys, os, math
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "blender/scenes/s04_kukur_v003.blend")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 140
sc.render.fps = 24
D = bpy.data.objects

rig = D["Nubis"]
rig.rotation_euler = (0, 0, 0)   # DAZ dog faces -Y (south): camera south of it looks north at the portico house
mala = D["S04_Mala"]
tika = D["S04_Tika"]
RH, LH = D["S04_Hand_Rig"], D["S04_HandL_Rig"]

# hand pose helpers from the props script (without rebuilding its actions)
src = open(os.path.join(ROOT, "scripts", "s04_hand_poses.py"), encoding="utf-8").read()
src = src.split("if __name__ ==")[0]
g = {}
exec(src, g)
apply_pose = g["apply_pose"]
PALM_N = g["PALM_N"]

# ---- clean-up: no red dab; ring finger reddish instead -------------------------------------
dab = D.get("S04_TikaFinger")
if dab:
    bpy.data.objects.remove(dab)
hand = D["S04_Hand"]
handL = D["S04_HandL"]
if handL.data == hand.data:          # left hand gets its own mesh without the red finger
    handL.data = hand.data.copy()
    handL.data.name = "S04_HandL"
me = hand.data
gi = {vg.name: vg.index for vg in hand.vertex_groups}
want = {gi[n]: w for n, w in (("RING_UP_TOP_joint_014", 1.0), ("RING_TOP_joint_013", 0.9),
                               ("RING_MID_joint_012", 0.35)) if n in gi}
red = [0.0] * len(me.vertices)
for v in me.vertices:
    for ge in v.groups:
        if ge.group in want:
            red[v.index] = max(red[v.index], ge.weight * want[ge.group])
at = me.attributes.get("tika_red") or me.attributes.new("tika_red", "FLOAT", "POINT")
at.data.foreach_set("value", red)
if "tika_red" in handL.data.attributes:
    handL.data.attributes.remove(handL.data.attributes["tika_red"])
mat = hand.material_slots[0].material
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
if not nt.nodes.get("TikaRedMix"):
    base_link = bsdf.inputs["Base Color"].links[0] if bsdf.inputs["Base Color"].links else None
    a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = "tika_red"; a.name = "TikaRedAttr"
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 180.0
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    mul2 = nt.nodes.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"; mul2.inputs[1].default_value = 1.0
    nt.links.new(a.outputs["Fac"], mul.inputs[0]); nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    # noise ~0.5 mean: lift so the tint is patchy but present
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"
    nt.links.new(nz.outputs["Fac"], add.inputs[0]); add.inputs[1].default_value = 0.6; add.inputs[2].default_value = 0.7
    nt.links.new(a.outputs["Fac"], mul.inputs[0]); nt.links.new(add.outputs[0], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.name = "TikaRedMix"
    mix.inputs["B"].default_value = (0.50, 0.015, 0.012, 1.0)   # sindoor powder stain
    if base_link:
        nt.links.new(base_link.from_socket, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    nt.links.new(mul2.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
print("[anim] ring finger tint verts", sum(1 for r in red if r > 0.05))

# ---- the portico ceiling hatch opens for the camera -----------------------------------------
hatch = D.get("S04_Portico_CeilingHatch")
if hatch:
    hatch.hide_render = True
    hatch.hide_viewport = True


def key_hide(ob, frames_vis):
    """frames_vis: list of (frame, visible) — constant interpolation"""
    for f, vis in frames_vis:
        ob.hide_render = not vis
        ob.hide_viewport = not vis
        ob.keyframe_insert("hide_render", frame=f)
        ob.keyframe_insert("hide_viewport", frame=f)


def constant(ob):
    ad = ob.animation_data
    if ad and ad.action:
        for fc in getattr(ad.action, "fcurves", []):
            if fc.data_path in ("hide_render", "hide_viewport"):
                for k in fc.keyframe_points:
                    k.interpolation = "CONSTANT"


def all_fcurves(idb):
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []   # Blender 5 layered actions
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out


# ---- dog: excited sit via the DAZ control morphs ---------------------------------------------
def kp(prop, f, v):
    rig[prop] = v
    rig.keyframe_insert(f'["{prop}"]', frame=f)


for f in range(1, 141):
    t = f / 24.0
    calm = 0.0
    if 66 <= f <= 86:          # still for the tika
        calm = min(1.0, (f - 64) / 4.0, (88 - f) / 4.0)
    wag = math.sin(2 * math.pi * 3.2 * t) * (0.85 - 0.55 * calm)
    if f % 1 == 0:
        kp("CTRLTailCurlSide-Side", f, wag)
    if f % 2 == 1:
        pant = 0.5 + 0.5 * math.sin(2 * math.pi * 2.6 * t)
        kp("CTRLMouthOpenWide", f, (0.10 + 0.22 * pant) * (1 - 0.7 * calm))
for f, v in ((1, 0.55), (60, 0.55), (64, 0.55), (68, 0.0), (88, 0.0), (96, 0.6), (125, 0.6)):   # tongue in while the mouth is shut (no teeth clipping)
    kp("CTRLPanting", f, 0.0)   # the panting morph half-closes the eyes; mouth/tongue morphs carry it
    kp("CTRLTongueHangingOut", f, v * 0.8)
for f, v in ((1, 0.0), (125, 0.0)):   # Happy squints the eyes shut
    kp("CTRLHappy", f, v)
    kp("CTRLTailDown-Up", f, 0.6)
# head: eager tilts, looks up at the mala, lowers a touch for it, raises for the tika
for f, side, lr in ((1, 0.0, 0.1), (16, 0.35, 0.15), (28, -0.25, 0.1), (38, 0.2, 0.3), (46, 0.0, 0.45),
                    (56, 0.0, -0.25), (64, 0.1, 0.0), (70, 0.0, 0.25), (84, 0.0, 0.2), (92, -0.3, 0.1),
                    (100, 0.25, 0.1), (125, 0.0, 0.1)):
    kp("CTRLHeadSide-Side", f, side)
    kp("CTRLHeadLower-Raise", f, lr)
for f, v in ((1, 0.6), (44, 0.6), (52, -0.4), (62, 0.5), (125, 0.5)):   # ears flatten as the mala passes
    kp("CTRLEarsFront-Back", f, v)
for f, v in ((1, 0), (71, 0), (74, 0.85), (79, 0.85), (82, 0), (125, 0)):   # eyes close for the tika press
    kp("CTRLEyesClosed", f, v)

# ---- tika stain: grows when the finger presses -----------------------------------------------
for f, s in ((1, 0.01), (74, 0.01), (77, 1.0), (125, 1.0)):
    tika.scale = (s, s, s)
    tika.keyframe_insert("scale", frame=f)

# ---- mala: hidden until the hands bring it, then held -> over the head -> worn -------------
sk = mala.data.shape_keys.key_blocks
worn_loc = Vector(mala["worn_location"])
over_loc = Vector(mala["overhead_location"])
hp = list(mala["hold_points_two_hands"])
key_hide(mala, [(1, False), (40, True)])


def set_mala(f, held, over, loc_local, world_offset=Vector()):
    sk["HeldTwoHands"].value = held
    sk["OverHead"].value = over
    sk["HeldTwoHands"].keyframe_insert("value", frame=f)
    sk["OverHead"].keyframe_insert("value", frame=f)
    sc.frame_set(f)
    mala.location = loc_local
    bpy.context.view_layer.update()
    if world_offset.length:
        mw = mala.matrix_world.copy()
        mw.translation += world_offset
        mala.matrix_world = mw
    mala.keyframe_insert("location", frame=f)


MALA_KEYS = [  # frame, held, over, local loc, world offset (up and towards the camera)
    (40, 1.0, 0.0, over_loc, Vector((0, -0.12, 0.72))),
    (47, 1.0, 0.0, over_loc, Vector((0, -0.08, 0.48))),
    (53, 0.5, 0.5, over_loc, Vector((0, -0.03, 0.22))),
    (57, 0.0, 1.0, over_loc, Vector()),
    (62, 0.0, 0.0, worn_loc, Vector()),
    (125, 0.0, 0.0, worn_loc, Vector()),
]
for k in MALA_KEYS:
    set_mala(*k)


def mala_point_world(i):
    """world position of control point i with the current shape-key mix"""
    basis = mala.data.shape_keys.key_blocks[0].data[i].co
    co = Vector(basis)
    for kb in mala.data.shape_keys.key_blocks[1:]:
        co += (Vector(kb.data[i].co) - Vector(basis)) * kb.value
    return mala.matrix_world @ co


# ---- hands -----------------------------------------------------------------------------------
def frame_rot(F, U, Lb):
    """rotation taking local finger axis +Z to F and local back-of-hand Lb to U"""
    F = F.normalized()
    U = (U - F * U.dot(F)).normalized()
    Lz = Vector((0, 0, 1))
    Lb = (Lb - Lz * Lb.dot(Lz)).normalized()
    W = Matrix((F, U, F.cross(U))).transposed()
    L = Matrix((Lz, Lb, Lz.cross(Lb))).transposed()
    return W @ L.transposed()


def place_hand(arm, f, R, grip_world, grip_local):
    """put the rig so that its armature-space point grip_local lands on grip_world"""
    S = Matrix.Diagonal(arm.scale.to_3d())
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = R.to_euler("XYZ")
    arm.location = grip_world - R @ (S @ grip_local)
    arm.keyframe_insert("location", frame=f)
    arm.keyframe_insert("rotation_euler", frame=f)


def posed_point(arm, bone, frac_to_child=0.0):
    pb = arm.pose.bones[bone]
    p = pb.head.copy()
    if frac_to_child and pb.children:
        p = p.lerp(pb.children[0].head, frac_to_child)
    return p


BACK = -PALM_N               # nails side, armature space (right hand)
BACK_L = Vector((-BACK.x, BACK.y, BACK.z))  # the left rig is mirrored on X

for arm in (RH, LH):
    arm.animation_data_create()
# grip point for the mala: between the thumb tip and the index middle joint
apply_pose("HandHoldMala", key=True, frame=38, arm=RH)
apply_pose("HandHoldMala", key=True, frame=38, arm=LH)
bpy.context.view_layer.update()
grip_R = (posed_point(RH, "THUMB_UP_TOP_joint_022") + posed_point(RH, "INDEX_MID_joint_04")) / 2
grip_L = (posed_point(LH, "THUMB_UP_TOP_joint_022") + posed_point(LH, "INDEX_MID_joint_04")) / 2
apply_pose("HandHoldMala", key=True, frame=64, arm=RH)

key_hide(RH, [(1, False), (39, True), (90, False)])
key_hide(LH, [(1, False), (39, True), (70, False)])
for ob in RH.children_recursive:
    key_hide(ob, [(1, False), (39, True), (90, False)])
for ob in LH.children_recursive:
    key_hide(ob, [(1, False), (39, True), (70, False)])

centre_world = None
for f in range(36, 70):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    ctr = sum((mala_point_world(i) for i in range(0, len(mala.data.splines[0].points), 4)), Vector()) / \
        len(range(0, len(mala.data.splines[0].points), 4))
    pts = sorted((mala_point_world(int(i)) for i in hp), key=lambda v: v.x)   # [left, right] on screen
    for arm, p, grip, back, side in ((RH, pts[1], grip_R, BACK, 1.0), (LH, pts[0], grip_L, BACK_L, -1.0)):
        # hands come in horizontally from the frame edges (right hand from the right, left from the left)
        enter = Vector((side * 0.45, -0.05, -0.04))
        if f < 40:
            p = p + enter * (40 - f) / 4
        if f > 62:
            p = p + enter * (f - 62) / 6
        F = Vector((-side, 0.35, -0.06))          # fingers point across the frame, a touch forward
        U = Vector((0, -0.5, 0.85))               # back of the hand to the camera and up
        place_hand(arm, f, frame_rot(F, U, back), p, grip)

# tika: right hand, ring finger pad pressed on the forehead
apply_pose("HandTika", key=True, frame=70, arm=RH)
bpy.context.view_layer.update()
tip = posed_point(RH, "RING_UP_TOP_joint_014")
tip = tip + (tip - posed_point(RH, "RING_TOP_joint_013")).normalized() * 0.008
for f in range(70, 90):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    tw = tika.matrix_world.translation.copy()
    nrm = Vector((0, -0.75, 0.66)).normalized()     # forehead faces the camera side (-Y) and up
    approach = 0.0
    if f < 74:
        approach = (74 - f) / 4.0
    elif f > 78:
        approach = (f - 78) / 6.0
    p = tw + Vector((0, -0.012, 0)) + Vector((0.32, -0.08, 0.22)) * approach   # in from the upper right
    F = Vector((-0.7, 0.3, -0.65))              # down-left onto the forehead from the upper right
    U = Vector((-0.5, -0.3, 0.8))               # back of the hand up and to the camera
    place_hand(RH, f, frame_rot(F, U, BACK), p, tip)

for ob in (RH, LH, mala, tika) + tuple(RH.children_recursive) + tuple(LH.children_recursive):
    for fc in all_fcurves(ob):
        if fc.data_path in ("hide_render", "hide_viewport"):
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"
for fc in all_fcurves(RH):   # finger poses switch instantly between beats
    if "pose.bones" in fc.data_path:
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"

# ---- materials: more real skin, livelier marigold ------------------------------------------
skin = bpy.data.materials["S04_Hand_Skin"]
for n in skin.node_tree.nodes:
    if n.type == "BUMP":
        n.inputs["Strength"].default_value = 0.28          # pores read at close range
    if n.type == "BSDF_PRINCIPLED":
        n.inputs["Specular IOR Level"].default_value = 0.32
        n.inputs["Subsurface Scale"].default_value = 0.006
        n.inputs["Sheen Weight"].default_value = 0.12
        if not n.inputs["Roughness"].is_linked:
            n.inputs["Roughness"].default_value = 0.55
mg = bpy.data.materials["S04_Marigold"]
for n in mg.node_tree.nodes:
    if n.type == "BSDF_PRINCIPLED":
        n.inputs["Sheen Weight"].default_value = 0.08
        n.inputs["Roughness"].default_value = 0.42
        n.inputs["Subsurface Weight"].default_value = 0.35
    if n.type == "HUE_SAT":
        n.inputs["Saturation"].default_value = 1.2
        n.inputs["Value"].default_value = 1.12
    if n.type == "MIX_SHADER" and not n.inputs["Fac"].is_linked:
        n.inputs["Fac"].default_value = max(n.inputs["Fac"].default_value, 0.25)

fur = bpy.data.materials.get("NubisFurMat")
if fur:
    for n in fur.node_tree.nodes:
        if n.type == "HUE_SAT":
            n.inputs["Saturation"].default_value = 1.18
            n.inputs["Value"].default_value = 1.0
        if n.type == "BSDF_HAIR_PRINCIPLED":
            n.inputs["Coat"].default_value = 0.08

# ---- sky: blue with clouds (Poly Haven CC0) ---------------------------------------------------
w = sc.world
envn = next((n for n in w.node_tree.nodes if n.type == "TEX_ENVIRONMENT"), None)
if envn:
    envn.image = bpy.data.images.load(os.path.join(ROOT, "blender", "assets", "polyhaven", "hdris",
                                                   "kloofendal_38d_partly_cloudy_puresky_4k.hdr"), check_existing=True)
    print("[anim] sky ->", envn.image.name)

# ---- camera ----------------------------------------------------------------------------------
cd = bpy.data.cameras.get("CAM_S04") or bpy.data.cameras.new("CAM_S04")
cam = D.get("CAM_S04") or bpy.data.objects.new("CAM_S04", cd)
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
tgt = D.get("CAM_S04_Aim") or bpy.data.objects.new("CAM_S04_Aim", None)
if tgt.name not in sc.collection.objects:
    sc.collection.objects.link(tgt)
cam.constraints.clear()
c = cam.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
cd.dof.use_dof = True
cd.dof.focus_object = tgt
cd.sensor_width = 36
dog = rig.matrix_world.translation
sc.frame_set(1); bpy.context.view_layer.update()
head = tika.matrix_world.translation.copy() - Vector((0, 0.02, 0.03))
print("[anim] dog", tuple(dog), "head", tuple(head))
FRONT = dog + Vector((0.22, -1.5, 0.75))
CAM = [  # frame, camera position, aim point, lens, f-stop  (front view only)
    # wide lens from the south side: both side wings of the courtyard in view while it tilts down
    (1, dog + Vector((0.0, -4.6, 1.5)), Vector((0, 7.0, 11.5)), 16, 11.0),     # cloudy sky + roofs, no dog
    (12, dog + Vector((0.0, -4.5, 1.45)), Vector((0, 7.0, 4.2)), 18, 11.0),    # tilting down over the house
    (16, dog + Vector((0.05, -3.4, 1.15)), Vector((0, 3.0, 1.9)), 28, 8.0),    # fast zoom: dog still below frame
    (20, FRONT + Vector((0, -0.2, 0.05)), head + Vector((0, 0, 0.04)), 38, 2.8), # dog arrives already close
    (32, FRONT, head, 38, 2.8),
    # beat 1: the camera pushes in with the hands as the mala goes on
    (40, FRONT + Vector((0, 0.1, 0.06)), head + Vector((0, 0, 0.16)), 40, 2.8),
    (58, FRONT + Vector((0, 0.5, 0.02)), head + Vector((0, 0, 0.06)), 46, 2.8),
    (64, FRONT + Vector((0, 0.45, -0.02)), head + Vector((0, 0, 0.02)), 46, 2.8),
    # beat 2: pushes in again, close on the forehead for the tika
    (72, FRONT + Vector((0, 0.65, -0.04)), head + Vector((0, 0, 0.05)), 52, 2.8),
    (80, FRONT + Vector((0, 0.7, -0.04)), head + Vector((0, 0, 0.05)), 54, 2.8),
    # hands gone: ease back out to the front view for the caption
    (90, FRONT + Vector((0, 0.3, -0.06)), head, 45, 2.8),
    (100, FRONT + Vector((0, 0.25, -0.06)), head, 45, 2.8),
    (125, FRONT + Vector((0, 0.3, -0.06)), head, 45, 2.8),
    (126, FRONT + Vector((0, 0.3, -0.06)), head, 45, 2.8),       # hold key: frames <=125 unchanged
    # exit: tilt up off the dog into the cloudy sky (fill for the cut into s05)
    (140, FRONT + Vector((0, 0.1, 0.05)), Vector((0, 6.0, 16.0)), 20, 8.0),
]
for f, p, a, lens, fs in CAM:
    cam.location = p; cam.keyframe_insert("location", frame=f)
    tgt.location = a; tgt.keyframe_insert("location", frame=f)
    cd.lens = lens; cd.keyframe_insert("lens", frame=f)
    cd.dof.aperture_fstop = fs; cd.dof.keyframe_insert("aperture_fstop", frame=f)
sc.camera = cam
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[anim] saved", OUT)
