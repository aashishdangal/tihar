"""Final Cycles render of s02 frames in a background Blender. Never saves the .blend.
RX 9070 XT only (the Ryzen iGPU is also a HIP device), HIP RT off (as in the s02 tests),
persistent data on, 1920x1080, OpenImageDenoise. Frames go to <out_dir>/NNNN.png.

Run: blender.exe -b s02_legend_vNNN.blend --python scripts/s02_render_frames.py -- <out_dir> <f1,f2,...> [res_x res_y]
or through scripts/render_resume.py (restarts after crashes, renders only missing frames).
S02_SAMPLES overrides the sample count (default 192, same as the s01 final).
"""
import os, sys, time
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir = os.path.abspath(argv[0])
frames = [int(x) for x in argv[1].split(",")]
rx = int(argv[2]) if len(argv) > 2 else 1920
ry = int(argv[3]) if len(argv) > 3 else 1080
spp = int(os.environ.get("S02_SAMPLES", "192"))

sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
cp.use_hiprt = False
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
sc.cycles.device = "GPU"
print("[s02r] devices:", [d.name for d in cp.devices if d.use], flush=True)

sc.cycles.samples = spp
sc.cycles.use_adaptive_sampling = True
sc.cycles.use_denoising = True
try:
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
except TypeError:
    pass
r = sc.render
r.use_persistent_data = True
r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.image_settings.color_depth = "8"
os.makedirs(out_dir, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_progress_hook as rp
prog = rp.Progress(out_dir, frames, samples=spp, res=(rx, ry))

log = open(os.path.join(out_dir, "render_log.txt"), "a")
try:
    for f in frames:
        prog.frame_begin(f)
        t = time.time()
        sc.frame_set(f)
        r.filepath = os.path.join(out_dir, f"{f:04d}.png")
        prog.stage("Sending scene to the GPU")
        bpy.ops.render.render(write_still=True)
        prog.frame_end(f)
        msg = f"frame {f}: {time.time() - t:.1f} s at {rx}x{ry}, {spp} spp"
        print("[s02r]", msg, flush=True)
        log.write(msg + "\n")
        log.flush()
except Exception as e:
    prog.finish(error=repr(e))
    raise
prog.finish()
