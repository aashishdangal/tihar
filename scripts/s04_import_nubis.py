# Import the Nubis dog (DAZ figure, Vyusur, free Renderhub giveaway) with the Diffeomorphic
# DAZ Importer and save it as blender/assets/s04_dog/nubis.blend.
# Run: blender.exe -b --factory-startup? (no: the extension must load) --python scripts/s04_import_nubis.py
import bpy, sys, os, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB = os.path.join(ROOT, "blender", "assets", "s04_dog", "daz_lib").replace("\\", "/")
DUF = os.environ.get("NUBIS_DUF", "Animals/Vyusur/Nubis/Characters/Nubis With Fur.duf")
OUT = os.path.join(ROOT, "blender", "assets", "s04_dog", "nubis.blend")

api = None
for name in ("bl_ext.user_default.import_daz", "import_daz"):
    try:
        api = __import__(name + ".api", fromlist=["api"])
        break
    except ImportError:
        pass
if api is None:
    sys.exit("[nubis] DAZ Importer not loaded")

api.set_global_setting("contentDirs", [LIB])
api.set_global_setting("mdlDirs", [])
api.set_global_setting("cloudDirs", [])
api.set_silent_mode(True)
api.set_global_setting("onlyDbz", False)

# empty scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)

t = time.time()
path = f"{LIB}/{DUF}"
res = bpy.ops.daz.easy_import_daz(filepath=path, files=[{"name": os.path.basename(path)}],
                                  directory=os.path.dirname(path) + "/", fitMeshes=os.environ.get("NUBIS_FIT", "MORPHED"))
print("[nubis] import", res, f"{time.time() - t:.1f}s", "error:", api.get_error_message())
for ob in bpy.data.objects:
    extra = ""
    if ob.type == "MESH":
        extra = f"verts {len(ob.data.vertices)} mats {[m.name for m in ob.data.materials if m]}"
        if ob.data.shape_keys:
            extra += f" keys {len(ob.data.shape_keys.key_blocks)}"
    if ob.type == "ARMATURE":
        extra = f"bones {len(ob.data.bones)}"
    if ob.type == "CURVES":
        extra = f"curves {len(ob.data.curves)}"
    print(f"[nubis] {ob.type:9} {ob.name:40} dims {tuple(round(d, 3) for d in ob.dimensions)} {extra}")
print("[nubis] missing images:", [i.filepath for i in bpy.data.images if i.source == "FILE" and not os.path.exists(bpy.path.abspath(i.filepath))])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[nubis] saved", OUT)
