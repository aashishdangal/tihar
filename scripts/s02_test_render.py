"""Quick Cycles test render of chosen s02 frames in a background Blender (keeps the live
session safe from GPU crashes). HIP RT off. Never saves the .blend.

Run: [S02_CPU=1] blender.exe -b s02_legend_vNNN.blend --python scripts/s02_test_render.py -- <out_prefix> <f1,f2,...> [percent] [samples]
"""
import os, sys, time
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out, frames = argv[0], [int(x) for x in argv[1].split(",")]
pct = int(argv[2]) if len(argv) > 2 else 50
spp = int(argv[3]) if len(argv) > 3 else 64

sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
cp.use_hiprt = False
cp.refresh_devices()
# discrete card only: the Ryzen iGPU ("AMD Radeon(TM) Graphics") is also a HIP device and
# drags every frame down when Cycles splits work across both
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
print("[s02t] devices:", [d.name for d in cp.devices if d.use], flush=True)
sc.cycles.device = "CPU" if os.environ.get("S02_CPU") == "1" else "GPU"   # S02_CPU=1 when the HIP driver is stuck
sc.cycles.samples = spp
sc.cycles.use_denoising = True
sc.render.use_persistent_data = os.environ.get("S02_NO_PERSIST") != "1"   # keep BVH/textures between frames: only frame 1 pays the long prep
sc.render.resolution_percentage = pct
# S02_EXPOSURE=2.5: brighten review stills of dark corners (judging only, never for final frames)
sc.view_settings.exposure += float(os.environ.get("S02_EXPOSURE", "0"))
# live progress for scripts/render_watch.py (writes <dir of out_prefix>/progress.json)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_progress_hook as rp
r = sc.render
prog = rp.Progress(os.path.dirname(out), frames, samples=spp,
                   res=(r.resolution_x * pct // 100, r.resolution_y * pct // 100))
try:
    for f in frames:
        t = time.time()
        prog.frame_begin(f)
        sc.frame_set(f)
        sc.render.filepath = f"{out}_{f:04d}.png"
        prog.stage("Sending scene to the GPU" if sc.cycles.device == "GPU" else "Syncing scene")
        bpy.ops.render.render(write_still=True)
        prog.frame_end(f)
        print(f"[s02t] frame {f}: {time.time() - t:.1f} s", flush=True)
except Exception as e:
    prog.finish(error=repr(e))
    raise
prog.finish()

# S02_REVIEW="REV_Wide,REV_Bed:frame,...": extra stills from review cameras (default frame 100)
for spec in filter(None, os.environ.get("S02_REVIEW", "").split(",")):
    name, _, fr = spec.partition(":")
    sc.camera = bpy.data.objects[name]
    sc.frame_set(int(fr) if fr else 100)
    sc.render.filepath = f"{out}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"[s02t] {name} done", flush=True)
