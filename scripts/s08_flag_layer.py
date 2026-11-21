"""Flag layer for the hybrid finale (owner 2026-11-21: "render it separately just like before but match
the lighting").

Rendered INSIDE the finale file (s08_finale_v073.blend), not a stripped copy, so the flag gets the same
sky, alpenglow (light-linked), hill bounce and shadows as the stills. Every other object stays in the
lighting but is invisible to the camera; the hill / front ridge / hill road are HOLDOUTS so they still
cut the pole where they stand in front of it. Only the flag's corner of the frame is rendered.

Haze: a volume fills the alpha of a transparent layer, so the loop is rendered WITHOUT S08_HazeLayer,
and one calibration frame (frame 36, opaque, haze on, normal scene) gives the per-channel colour shift
the haze puts on the flag; scripts/s08_flag_grade.py applies it to every loop frame.

  blender.exe -b blender/scenes/s08_finale_v073.blend --python scripts/s08_flag_layer.py
Env S08_MODE = "calib" (one opaque frame with haze) or "loop" (frames 1-72, transparent, no haze).
Out: renders/s08_finale/flag3/{calib,loop}/f_####.png  (+ region.json with the crop box)
Live progress: python scripts/render_watch.py renders/s08_finale/flag3/<mode>
"""
import json
import os
import sys

import bpy

ROOT = r"E:/Projects/tihar"
sys.path.insert(0, ROOT + "/scripts")
import render_progress_hook as rp  # noqa: E402

MODE = os.environ.get("S08_MODE", "loop")
FLAG = ["S08_FlagLoop", "S08_FlagPole.001", "S08_FlagFinial"]
OCCLUDERS = ["S08_Hill", "S08_FrontRidge", "S08_HillRoad"]
OFF = ["S08_Tree", "S08_GrassFG", "S08_KitePaper", "S08_KiteSpine", "S08_KiteBow", "S08_KiteString",
       "S08_KiteTree", "S08_KiteProxy", "S08_Flag", "S08_FlagPole"]
# flag + pole region, px from the top-left of the 1920x1080 frame (flag flies left from the pole at x~1700)
X0, X1, Y0, Y1 = 1470, 1800, 500, 1080

sc = bpy.context.scene
for n in FLAG:
    bpy.data.objects[n].hide_render = False
for n in OFF:
    o = bpy.data.objects.get(n)
    if o:
        o.hide_render = True
haze = bpy.data.objects["S08_HazeLayer"]

if MODE == "loop":
    haze.hide_render = True
    for o in bpy.data.objects:
        if o.hide_render or o.type in ("LIGHT", "CAMERA", "EMPTY") or o.name in FLAG:
            continue
        if o.name in OCCLUDERS:
            o.is_holdout = True                  # still cuts the pole where the ground is in front
        else:
            o.visible_camera = False             # still lights, shadows and bounces; just not seen
    sc.render.film_transparent = True
    frames = list(range(1, 73))
else:
    sc.render.film_transparent = False           # normal scene, haze on: the reference look
    frames = [36]

prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "HIP"; prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type == "HIP" and "9070" in dv.name
c = sc.cycles
c.device = "GPU"; c.samples = 256; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.01; c.use_denoising = True
sc.render.resolution_percentage = 100
sc.render.use_persistent_data = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
rx, ry = sc.render.resolution_x, sc.render.resolution_y
sc.render.use_border = True; sc.render.use_crop_to_border = True
sc.render.border_min_x, sc.render.border_max_x = X0 / rx, X1 / rx
sc.render.border_min_y, sc.render.border_max_y = 1 - Y1 / ry, 1 - Y0 / ry   # Blender's border is bottom-up

out = ROOT + "/renders/s08_finale/flag3/" + MODE
os.makedirs(out, exist_ok=True)
json.dump({"x0": X0, "y0": Y0, "x1": X1, "y1": Y1, "frame": [rx, ry]}, open(out + "/region.json", "w"))
frames = [f for f in frames if not os.path.exists(out + "/f_%04d.png" % f)]
prog = rp.Progress(out, frames, samples=c.samples, res=(X1 - X0, Y1 - Y0))
for f in frames:
    prog.frame_begin(f); sc.frame_set(f); prog.stage("Rendering")
    sc.render.filepath = out + "/f_%04d.png" % f
    bpy.ops.render.render(write_still=True)
    prog.frame_end(f)
    print("[flagl]", MODE, "rendered", f, flush=True)
prog.finish()
print("[flagl] done", MODE, len(frames))
