"""Full render of the approved s08 flag loop (smoothed sim, scripts/s08_flag_smooth.py).

  blender.exe -b blender/scenes/s08_flag_v005.blend --python scripts/s08_flag_render.py
Writes renders/s08_finale/flag/loop/f_0001.png ... (transparent film, 1080p, 128 samples, 9070 XT).
Skips frames that already exist, so a crashed run can be restarted.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_progress_hook as rp  # noqa: E402

sc = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "HIP"; prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type == "HIP" and "9070" in dv.name
print("[flagr] devices", [d.name for d in prefs.devices if d.use])
sc.cycles.device = "GPU"; sc.cycles.samples = 128; sc.cycles.use_denoising = True
sc.render.resolution_percentage = 100; sc.render.film_transparent = True
sc.render.use_persistent_data = True
out = r"E:/Projects/tihar/renders/s08_finale/flag/loop"
os.makedirs(out, exist_ok=True)
frames = [f for f in range(sc.frame_start, sc.frame_end + 1) if not os.path.exists(out + "/f_%04d.png" % f)]
prog = rp.Progress(out, frames, samples=sc.cycles.samples, res=(sc.render.resolution_x, sc.render.resolution_y))
for f in frames:
    prog.frame_begin(f)
    sc.frame_set(f)
    prog.stage("Rendering")
    sc.render.filepath = out + "/f_%04d.png" % f
    bpy.ops.render.render(write_still=True)
    prog.frame_end(f)
prog.finish()
print("[flagr] done", len(frames), "frames")
