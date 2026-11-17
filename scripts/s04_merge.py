# Merge the s04 parts into one scene file:
#   courtyard (s04_courtyard_v013) + dog with fur, mala, tika (s04_kukur_propsfit_v001)
#   + hands (hand_props_v001). The dog sits in the centre of the courtyard facing the portico.
# blender.exe -b blender/scenes/s04_courtyard_v013.blend --python scripts/s04_merge.py -- <out.blend>
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "blender/scenes/s04_kukur_v002.blend")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOG = os.path.join(ROOT, "blender", "scenes", "s04_kukur_propsfit_v001.blend")
HAND = os.path.join(ROOT, "blender", "assets", "s04_hand", "hand_props_v001.blend")
DOG_POS = Vector((0.0, -0.3, 0.0))   # courtyard centre (court spans x -6..6, y -6.6..6.0)

sc = bpy.context.scene


def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in (parent or sc.collection).children:
        (parent or sc.collection).children.link(c)
    return c


def append(path, names, cols=()):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
        dst.collections = [c for c in cols if c in src.collections]
    return dst.objects, dst.collections


# ---- dog + mala + tika ----------------------------------------------------------------------
dog_c = coll("S04_Dog")
objs, cols = append(DOG, ["Nubis", "Nubis Mesh", "Nubis Fur", "Fibers Mesh", "Whiskers Long Mesh",
                          "S04_Mala", "S04_Tika"], ["S04_Mala_Heads"])
for o in objs:
    dog_c.objects.link(o)
for c in cols:   # marigold head sources: in the file, excluded from the view layer
    sc.collection.children.link(c)
    bpy.context.view_layer.layer_collection.children[c.name].exclude = True
rig = bpy.data.objects["Nubis"]
rig.location = DOG_POS
rig.rotation_euler = (0, 0, math.pi)   # DAZ dog faces -Y; turn it to face the portico (+Y)
print("[merge] dog", [o.name for o in objs], "scale", tuple(rig.scale))

# ---- hands (parked out of view until animated) -----------------------------------------------
hand_c = coll("S04_Hands")
hand_names = ["S04_Hand_Rig", "S04_Hand", "S04_Hand_Forearm", "S04_Hand_RedThread", "S04_Hand_Sleeve",
              "S04_Hand_SleeveHem", "S04_HandL_Rig", "S04_HandL", "S04_HandL_Forearm", "S04_HandL_RedThread",
              "S04_HandL_Sleeve", "S04_HandL_SleeveHem", "S04_TikaFinger"]
objs, _ = append(HAND, hand_names)
for o in objs:
    hand_c.objects.link(o)
for r, x in (("S04_Hand_Rig", 0.25), ("S04_HandL_Rig", -0.25)):
    ob = bpy.data.objects[r]
    ob.location = DOG_POS + Vector((x, 1.2, 0.9))
print("[merge] hands", len(objs))

# pose actions for the hands come along with the objects only if used; append them explicitly
with bpy.data.libraries.load(HAND, link=False) as (src, dst):
    dst.actions = [a for a in src.actions if a in ("HandRest", "HandHoldMala", "HandTika")]
for a in dst.actions:
    a.use_fake_user = True
print("[merge] actions", [a.name for a in dst.actions])

# ---- test cameras ----------------------------------------------------------------------------
cams = coll("S04_TestCams")
head = DOG_POS + Vector((0, 0.15, 0.62))


def cam(name, loc, target, lens):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if ob.name not in cams.objects:
        cams.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cd.dof.use_dof = True
    cd.dof.focus_distance = (Vector(target) - Vector(loc)).length
    cd.dof.aperture_fstop = 2.8
    return ob


cam("CAM_S04_DogClose", DOG_POS + Vector((0.35, 1.25, 0.5)), head, 50)
cam("CAM_S04_DogWide", DOG_POS + Vector((0.8, 4.6, 1.1)), DOG_POS + Vector((0, 0, 0.45)), 35)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[merge] saved", OUT)
