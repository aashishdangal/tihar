# Thumbnail each AI model in blender/assets/s05/ai/<id>/ (base_basic_pbr.glb or base.obj) so the
# owner's untitled AI downloads can be identified. Never saves a .blend.
#   blender.exe -b --factory-startup --python scripts/s05_ai_thumbs.py -- <out_dir>
import bpy, os, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0])
os.makedirs(out, exist_ok=True)
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "blender", "assets", "s05", "ai"))

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_WORKBENCH"
sc.render.resolution_x = sc.render.resolution_y = 512
w = bpy.data.worlds.new("W"); sc.world = w; w.color = (0.6, 0.6, 0.62)
for idn in sorted(os.listdir(root)):
    d = os.path.join(root, idn)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    f = next((os.path.join(d, n) for n in ("base_basic_pbr.glb", "base.glb", "base.obj") if os.path.exists(os.path.join(d, n))), None)
    if not f:
        continue
    if f.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=f)
    else:
        bpy.ops.import_scene.gltf(filepath=f)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr = (lo + hi) / 2; size = (hi - lo).length
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = ctr + Vector((0.9, -1.4, 0.8)).normalized() * size * 1.3
    cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (ctr - cam.location).to_track_quat("-Z", "Y")
    sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 4; sun.rotation_euler = (0.8, 0.2, 0.6)
    sc.render.filepath = os.path.join(out, idn + ".png")
    bpy.ops.render.render(write_still=True)
    print("[thumb]", idn, os.path.basename(f), "size", tuple(round(x, 2) for x in (hi - lo)), flush=True)
