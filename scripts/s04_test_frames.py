# Render chosen frames of the s04 animation (scene camera) to renders/s04_kukur/test/<tag>/NNNN.png
#   bash scripts/s04_court_run.sh <blend> scripts/s04_test_frames.py -- <tag> <spp> <pct> f1 f2 ...
import bpy, sys, os, time
argv = sys.argv[sys.argv.index("--") + 1:]
tag, spp, pct, frames = argv[0], int(argv[1]), int(argv[2]), [int(a) for a in argv[3:]]
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
out = os.path.join(root, "renders", os.environ.get("TEST_SCENE","s04_kukur"), "test", tag)
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"; cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"
sc.cycles.samples = spp; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, pct
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = "PNG"
for f in frames:
    t = time.time()
    sc.frame_set(f)
    sc.render.filepath = os.path.join(out, "%04d.png" % f)
    bpy.ops.render.render(write_still=True)
    print("[tf] frame %d %.1fs" % (f, time.time() - t), flush=True)
