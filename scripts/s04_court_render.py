# Test-render one camera of the s04 courtyard on the discrete GPU.
#   blender -b <s04_courtyard_vNNN.blend> --python scripts/s04_court_render.py -- <cam> <out.png> [spp] [width height]
# Run it through scripts/s04_court_run.sh so the shared GPU lock is honoured.
import bpy, sys, os, time

argv = sys.argv[sys.argv.index("--") + 1:]
cam, out = argv[0], argv[1]
spp = int(argv[2]) if len(argv) > 2 else 48
w, h = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (1280, 720)
sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
print("[render] devices", [(d.name, d.use) for d in cp.devices])
sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = spp
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
sc.camera = bpy.data.objects[cam]
for k, v in os.environ.items():  # optional overrides, e.g. S04_EXPOSURE=-0.5
    if k == "S04_EXPOSURE":
        sc.view_settings.exposure = float(v)
sc.render.filepath = out
sc.render.image_settings.file_format = "PNG"
os.makedirs(os.path.dirname(out), exist_ok=True)
t0 = time.time()
bpy.ops.render.render(write_still=True)
print("[render] %s -> %s  %.1fs" % (cam, out, time.time() - t0))
