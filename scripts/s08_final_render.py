"""Render the one-pass finale loop (blender/scenes/s08_finale_v071.blend, scripts/s08_main_merge.py).

  blender.exe -b blender/scenes/s08_finale_v071.blend --python scripts/s08_final_render.py
Env S08_FRAMES="17,58,103" (default: all 1-120), S08_OUT (default renders/s08_finale/final).
Fresh process on purpose: building v071 in the same process left a scene-wide ray-cast BVH in memory
and the render ran out of GPU + host memory. Skips frames that already exist (restartable).
Live progress: python scripts/render_watch.py <out>
"""
import os
import sys

import bpy

ROOT = r"E:/Projects/tihar"
sys.path.insert(0, ROOT + "/scripts")
import render_progress_hook as rp  # noqa: E402

sc = bpy.context.scene
# S08_SHOW / S08_HIDE: comma-separated EXACT object names to switch on/off for this render only
# (the hybrid finale renders the same v073 file as the clean still and as the full still).
# Exact names, not prefixes: "S08_Kite" once also matched the old hidden S08_KiteTree, which stands
# 5.5 m in front of the camera and blacked out a whole 27-minute render.
for key, hide in (("S08_SHOW", False), ("S08_HIDE", True)):
    want = [p for p in os.environ.get(key, "").split(",") if p]
    if want:
        missing = [n for n in want if n not in bpy.data.objects]
        if missing:
            raise SystemExit("[final] no such objects: %s" % missing)
        names = want
        for n in names:
            bpy.data.objects[n].hide_render = hide
        print("[final]", "hidden" if hide else "shown", names)
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "HIP"; prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type == "HIP" and "9070" in dv.name
print("[final] devices", [d.name for d in prefs.devices if d.use])
sc.cycles.device = "GPU"; sc.cycles.use_denoising = True     # samples come from the file (v072: 64 + adaptive)
sc.render.resolution_percentage = int(os.environ.get("S08_PCT", "100"))       # previews: S08_PCT=25
if os.environ.get("S08_SPP"):
    sc.cycles.samples = int(os.environ["S08_SPP"])
sc.cycles.use_auto_tile = True; sc.cycles.tile_size = 512; sc.cycles.texture_limit_render = "1024"
sc.render.use_persistent_data = True
out = os.environ.get("S08_OUT", ROOT + "/renders/s08_finale/final")
os.makedirs(out, exist_ok=True)
fr = os.environ.get("S08_FRAMES")
frames = [int(f) for f in fr.split(",")] if fr else list(range(sc.frame_start, sc.frame_end + 1))
frames = [f for f in frames if not os.path.exists(out + "/f_%04d.png" % f)]
prog = rp.Progress(out, frames, samples=sc.cycles.samples, res=(sc.render.resolution_x, sc.render.resolution_y))
for f in frames:
    prog.frame_begin(f)
    sc.frame_set(f)
    prog.stage("Rendering")
    sc.render.filepath = out + "/f_%04d.png" % f
    bpy.ops.render.render(write_still=True)
    prog.frame_end(f)
    print("[final] rendered", f, flush=True)
prog.finish()
print("[final] done", len(frames))
