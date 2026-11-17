# Cow-only look renders (s05): a few fixed views of the garlanded cow in the courtyard daylight.
# Never saves the .blend.
#   blender.exe -b s05_laxmi_vNNN.blend --python scripts/s05_cow_renders.py -- <out_dir> [frame] [spp]
import bpy, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0]); os.makedirs(out, exist_ok=True)
frame = int(argv[1]) if len(argv) > 1 else 40
spp = int(argv[2]) if len(argv) > 2 else 64

sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"; cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"
sc.cycles.samples = spp; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 100
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = "PNG"
sc.frame_set(frame)

rig = bpy.data.objects["Cattle_Rig_grp"]; W = rig.matrix_world
head = W @ rig.pose.bones["DEF_Head"].head
neck = W @ rig.pose.bones["DEF_neck_c"].head
body = W @ rig.pose.bones["DEF_neck_a"].head
fwd = head - body; fwd.z = 0; fwd.normalize()
side = Vector((fwd.y, -fwd.x, 0))
mid = body + fwd * -0.35 + Vector((0, 0, -0.15))     # middle of the body

VIEWS = {   # name: (camera position, aim point, lens)
    "01_front34": (head + fwd * 2.4 + side * 1.3 + Vector((0, 0, -0.15)), neck + Vector((0, 0, 0.05)), 50),
    "02_side":    (mid + side * 3.6 + Vector((0, 0, 0.05)), mid + Vector((0, 0, 0.05)), 40),
    "03_udder":   (mid - fwd * 1.6 + side * 1.5 + Vector((0, 0, -0.45)), mid - fwd * 0.35 + Vector((0, 0, -0.35)), 35),
    "04_head":    (head + fwd * 1.0 + side * 0.35 + Vector((0, 0, 0.05)), head + Vector((0, 0, -0.05)), 70),
}
cd = bpy.data.cameras.new("CowLook"); cam = bpy.data.objects.new("CowLook", cd); sc.collection.objects.link(cam)
cd.dof.use_dof = True; cd.dof.aperture_fstop = 4.0
sc.camera = cam
for name, (p, a, lens) in VIEWS.items():
    cam.location = p
    cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (a - p).to_track_quat("-Z", "Y")
    cd.lens = lens; cd.dof.focus_distance = (a - p).length
    sc.render.filepath = os.path.join(out, f"cow_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("[cow]", name, flush=True)
