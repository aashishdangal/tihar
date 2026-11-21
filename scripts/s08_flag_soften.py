"""Flag reads as crumpled paper (owner 2026-11-21: "it looks like paper scrambled").

Causes in the v1 bake (scripts/s08_flag_file.py):
  - bending_stiffness 0.05 + mass 0.05: the cloth creases sharply like tissue paper,
  - turbulence field only 0.45 m wide on a 1.35 m flag: many small crinkles instead of a few long waves,
  - wind/gust keys ended at frame 200 while the loop uses frames up to ~440.
Fix: fabric-like bending and weight, one long turbulence wave (2.5 m), wind keyed over the whole
560-frame bake, then rebake and rebuild the seamless loop (scripts/s08_flag_loop_geo.py).

Headless, on blender/scenes/s08_flag.blend (writes s08_flag_v003.blend; v001 = the old file, v002 = try 1):
  blender.exe -b blender/scenes/s08_flag.blend --python scripts/s08_flag_soften.py
Env S08_TEST=1 also renders 6 low-sample test frames to renders/s08_finale/test/flag_soft/.
"""
import math
import os
import random
import shutil
import time

import bpy
from mathutils import Vector

ROOT = r"E:/Projects/tihar"


def fcurves(ob):
    from bpy_extras import anim_utils
    ad = ob.animation_data
    return anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves

SRC = bpy.data.filepath
shutil.copy2(SRC, ROOT + "/blender/scenes/s08_flag_v001.blend")       # untouched old state
sc = bpy.context.scene
END = 560

fl = bpy.data.objects["S08_Flag"]
cm = next(m for m in fl.modifiers if m.type == "CLOTH")
cs = cm.settings
cs.mass = 0.12                       # polyester/cotton flag at 3 cm spacing
cs.bending_model = "ANGULAR"
cs.bending_stiffness = 0.9           # was 0.05: paper-like creases
cs.tension_stiffness = 20; cs.compression_stiffness = 20; cs.shear_stiffness = 8
cs.tension_damping = 5; cs.compression_damping = 5; cs.shear_damping = 5
cs.bending_damping = 0.5
cs.air_damping = 1.0
cs.quality = 10
cm.collision_settings.use_self_collision = True

# wind keyed over the whole bake, same heading/variation scheme as s08_flag_file.py
w = bpy.data.objects["S08_Wind"]; g = bpy.data.objects["S08_Gusts"]
sc.frame_set(1)
base_rot = w.rotation_euler.z            # heading as set in s08_flag_file.py (flag flies left)
w.animation_data_clear(); g.animation_data_clear()
rnd = random.Random(21)
w.field.noise = 1.0                  # was 3.5: per-vertex noise also adds crinkle
fr = 1
while fr <= END:
    w.field.strength = rnd.uniform(2600, 3200)   # try 2: 1600-2400 let the flag fall round the pole
    w.field.keyframe_insert("strength", frame=fr)
    w.rotation_euler = (math.radians(-90), 0.0, base_rot + math.radians(rnd.uniform(-3, 3)))
    w.keyframe_insert("rotation_euler", frame=fr)
    fr += rnd.randint(24, 48)
for fc in fcurves(w):
    for k in fc.keyframe_points:
        k.interpolation = "BEZIER"
g.field.size = 2.5                    # was 0.45: long rolling waves, not crinkles
g.field.flow = 0.0
start = g.location.copy()
g.keyframe_insert("location", frame=1)
# drift with the wind ~3 m/s over the full bake
wd = Vector((math.cos(base_rot + math.pi / 2), math.sin(base_rot + math.pi / 2), 0))
g.location = start + wd * (3.0 * END / 24.0); g.keyframe_insert("location", frame=END)
for fc in fcurves(g):
    for k in fc.keyframe_points:
        k.interpolation = "LINEAR"
fr = 1
while fr <= END:
    g.field.strength = rnd.uniform(120, 220); g.field.keyframe_insert("strength", frame=fr)
    fr += rnd.randint(16, 32)

cm.point_cache.frame_start = 1; cm.point_cache.frame_end = END
sc.frame_start, sc.frame_end = 1, END
fl.hide_viewport = False
sc.frame_set(1)
t = time.time()
with bpy.context.temp_override(point_cache=cm.point_cache, active_object=fl, object=fl):
    bpy.ops.ptcache.free_bake(); bpy.ops.ptcache.bake(bake=True)
print("[soften] baked", cm.point_cache.is_baked, round(time.time() - t), "s")

# how far the cloth flies out from the pole (flat flag ~0.55 m mean); low = hanging/wrapped
import numpy as np
pz = bpy.data.objects["S08_FlagPole"].matrix_world.translation
for f in range(1, END + 1, 20):
    sc.frame_set(f); me = fl.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    a = np.array([fl.matrix_world @ v.co for v in me.vertices])
    print('[soften] fly-out f%d mean %.2f m' % (f, np.hypot(a[:, 0] - pz.x, a[:, 1] - pz.y).mean()))

bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_flag_v003.blend")
exec(open(ROOT + "/scripts/s08_flag_loop_geo.py", encoding="utf-8").read())   # saves v003 again with the loop

if os.environ.get("S08_TEST"):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "HIP"; prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == "HIP" and "9070" in dv.name
    print("[soften] devices", [dv.name for dv in prefs.devices if dv.use])
    sc.cycles.device = "GPU"; sc.cycles.samples = 32
    out = ROOT + "/renders/s08_finale/test/flag_soft2"
    os.makedirs(out, exist_ok=True)
    L = sc.frame_end
    for f in [1, L // 6, L // 3, L // 2, 2 * L // 3, 5 * L // 6]:
        sc.frame_set(f); sc.render.filepath = out + "/f_%04d.png" % f
        bpy.ops.render.render(write_still=True)
        print("[soften] rendered", f)
print("[soften] done")
