# Load a DAZ pose and the Nubis face/tail control morphs onto the imported dog.
# blender.exe -b blender/assets/s04_dog/nubis.blend --python scripts/s04_nubis_pose.py -- <pose name> <out.blend>
import bpy, sys, os, glob

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
pose = argv[0] if argv else "Nubis Sitting 01"
out = os.path.abspath(argv[1] if len(argv) > 1 else "blender/assets/s04_dog/nubis_v002.blend")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB = os.path.join(ROOT, "blender", "assets", "s04_dog", "daz_lib").replace("\\", "/")

api = __import__("bl_ext.user_default.import_daz.api", fromlist=["api"])
api.set_global_setting("contentDirs", [LIB])
api.set_global_setting("onlyDbz", False)
api.set_silent_mode(True)

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.name == "Nubis Mesh")
for o in bpy.context.view_layer.objects:
    o.select_set(False)


def activate(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


# control morphs (face expressions, ears, tail) -- the non-alias .dsf files
mdir = f"{LIB}/data/Vyusur/Nubis/Nubis/Morphs/Vyusur/Base/"
mfiles = sorted(os.path.basename(f) for f in glob.glob(mdir + "*.dsf") if not os.path.basename(f).startswith("alias_"))
activate(rig)
try:
    r = bpy.ops.daz.import_custom_morphs(directory=mdir, files=[{"name": f} for f in mfiles])
    print("[pose] morphs", r, len(mfiles), api.get_error_message())
except Exception as e:
    print("[pose] morphs failed:", e)

pfile = f"{LIB}/Animals/Vyusur/Nubis/Poses/{pose}.duf"
activate(rig)
r = bpy.ops.daz.import_pose(filepath=pfile, directory=os.path.dirname(pfile) + "/", files=[{"name": os.path.basename(pfile)}])
print("[pose] pose", pose, r, api.get_error_message())

props = [k for k in rig.keys() if not k.startswith("_")]
print("[pose] rig props", len(props), [p for p in props if "CTRL" in p or "Pant" in p or "Happy" in p][:40])
if body.data.shape_keys:
    print("[pose] shape keys", len(body.data.shape_keys.key_blocks), [k.name for k in body.data.shape_keys.key_blocks][:30])
bpy.ops.wm.save_as_mainfile(filepath=out)
print("[pose] saved", out)
