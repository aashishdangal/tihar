"""Test renders of the s08 foreground layer (blender/scenes/s08_fg.blend).

  blender.exe -b blender/scenes/s08_fg.blend --python scripts/s08_fg_test.py
Env S08_FRAMES="1,80,160" (default), S08_PCT=50, S08_SPP=32, S08_OUT=renders/s08_finale/test/fg2
"""
import os

import bpy

sc = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "HIP"; prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type == "HIP" and "9070" in dv.name
sc.cycles.device = "GPU"
sc.cycles.samples = int(os.environ.get("S08_SPP", "32"))
sc.render.resolution_percentage = int(os.environ.get("S08_PCT", "50"))
out = os.environ.get("S08_OUT", r"E:/Projects/tihar/renders/s08_finale/test/fg2")
os.makedirs(out, exist_ok=True)
fr = os.environ.get("S08_FRAMES", "1,80,160")
frames = range(1, sc.frame_end + 1) if fr == "all" else [int(f) for f in fr.split(",")]
for f in frames:
    sc.frame_set(f); sc.render.filepath = out + "/f_%04d.png" % f
    bpy.ops.render.render(write_still=True)
    print("[fgt] rendered", f)
print("[fgt] done")
