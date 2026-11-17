"""Cycles test render of chosen s01 frames with the file's own look. Never saves the .blend.
The cloud blockout gets a flat black material for now. The old Lazy Cloud dive slab is left out of
the render (replaced by the sweep-in cloud; its flat bottom made a straight line).

Run: blender.exe -b s01_hero_v032.blend --python scripts/s01_render_frames.py -- <out_dir> <f1,f2,...> [res_x res_y]
"""
import os, sys, time
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir = os.path.abspath(argv[0])
frames = [int(x) for x in argv[1].split(",")]
rx = int(argv[2]) if len(argv) > 2 else 1920
ry = int(argv[3]) if len(argv) > 3 else 1080

sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
if os.environ.get("S01_NO_HIPRT") == "1":   # set by render_resume.py after repeated HIP RT crashes
    cp.use_hiprt = False
    print("[s01r] HIP RT off")
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "9070" in d.name
sc.cycles.device = "GPU"
print("[s01r] devices:", [d.name for d in cp.devices if d.use])

old = bpy.data.objects.get("S01_DiveCloud_LC")
if old:
    old.hide_render = True

cloud = bpy.data.objects.get("S01_DarkCloud_Blockout")
if cloud:
    m = bpy.data.materials.new("M_S01_DarkCloud_Blockout")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.004, 0.004, 0.006, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    cloud.data.materials.clear()
    cloud.data.materials.append(m)

r = sc.render
r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
r.image_settings.file_format = "PNG"
os.makedirs(out_dir, exist_ok=True)

# live progress for scripts/render_watch.py (writes <out_dir>/progress.json)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_progress_hook as rp
prog = rp.Progress(out_dir, frames, samples=sc.cycles.samples, res=(rx, ry))

log = open(os.path.join(out_dir, "render_log.txt"), "a")
try:
    for f in frames:
        prog.frame_begin(f)
        t = time.time()
        sc.frame_set(f)                       # builds the cloud sea etc. on the CPU
        prep = time.time() - t
        r.filepath = os.path.join(out_dir, f"{f:04d}.png")
        prog.stage("Sending scene to the GPU")
        bpy.ops.render.render(write_still=True)
        prog.frame_end(f)
        msg = f"frame {f}: {time.time() - t:.1f} s ({prep:.1f} s geometry) at {rx}x{ry}, {sc.cycles.samples} spp"
        print("[s01r]", msg, flush=True)
        log.write(msg + "\n")
        log.flush()
except Exception as e:
    prog.finish(error=repr(e))
    raise
prog.finish()
