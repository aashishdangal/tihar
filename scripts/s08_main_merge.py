"""One-pass finale (owner 2026-11-21: "yes do single render"): bring the swaying tree, near grass, kite
(scripts/s08_fg_file.py in S08_INPLACE mode) and the approved flag loop (s08_flag_v013.blend,
computed waves, 120 frames) into the finale file, so the final view renders in one pass with the
finale's own lighting and haze. The separate layers had a lighting mismatch.

  blender.exe -b blender/scenes/s08_finale_v070.blend --python scripts/s08_main_merge.py
writes blender/scenes/s08_finale_v071.blend (frames 1-120, 5 s loop).
Env S08_FRAMES="17,58,103" also renders those frames at full quality to renders/s08_finale/test/v071/.
"""
import os
import sys

import bpy

ROOT = r"E:/Projects/tihar"
sc = bpy.context.scene

anim = [o.name for o in bpy.data.objects if o.animation_data and (o.animation_data.action or o.animation_data.drivers)]
print("[merge] animated objects before:", anim)

# 1. tree sway + near grass + kite, in place, kite pinned to the approved spot
os.environ["S08_INPLACE"] = "1"
os.environ["S08_KITE_AT"] = "1996.32,-10983.18,2003.01"
os.environ.pop("S08_TEST", None)
exec(open(ROOT + "/scripts/s08_fg_file.py", encoding="utf-8").read())

# 2. the approved flag loop from the flag file (pole, finial, loop mesh with its PC2 cache)
src = ROOT + "/blender/scenes/" + os.environ.get("S08_FLAG_FILE", "s08_flag_v014.blend")   # 3 s gentle loop (pass 6)
want = ["S08_FlagLoop", "S08_FlagPole", "S08_FlagFinial"]
for n in ("S08_Flag", "S08_FlagPole", "S08_FlagFinial"):            # the finale's own old flag stays hidden
    o = bpy.data.objects.get(n)
    if o:
        o.hide_render = True; o.hide_viewport = True
with bpy.data.libraries.load(src, link=False) as (df, dt):
    dt.objects = [n for n in df.objects if n in want]
coll = bpy.data.collections.get("S08_Foreground") or sc.collection
for o in dt.objects:
    if o is None:
        continue
    coll.objects.link(o)
    o.hide_render = False; o.hide_viewport = False
    print("[merge] flag object", o.name, tuple(round(c, 2) for c in o.location))
loop = next(o for o in dt.objects if o and o.name.startswith("S08_FlagLoop"))
mc = next(m for m in loop.modifiers if m.type == "MESH_CACHE")
print("[merge] flag cache", mc.filepath, os.path.exists(bpy.path.abspath(mc.filepath)))

sc.frame_start, sc.frame_end = 1, L                                   # L from s08_fg_file.py (72 = 3 s)
sc.render.film_transparent = False
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_finale_v071.blend")
print("[merge] saved", bpy.data.filepath)

fr = os.environ.get("S08_FRAMES")
if fr:
    sys.path.insert(0, ROOT + "/scripts")
    import render_progress_hook as rp
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "HIP"; prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == "HIP" and "9070" in dv.name
    sc.cycles.device = "GPU"; sc.cycles.samples = 128; sc.render.resolution_percentage = 100
    out = ROOT + "/renders/s08_finale/test/v071"
    os.makedirs(out, exist_ok=True)
    frames = [int(f) for f in fr.split(",")]
    prog = rp.Progress(out, frames, samples=128, res=(sc.render.resolution_x, sc.render.resolution_y))
    for f in frames:
        prog.frame_begin(f); sc.frame_set(f); prog.stage("Rendering")
        sc.render.filepath = out + "/f_%04d.png" % f
        bpy.ops.render.render(write_still=True)
        prog.frame_end(f)
        print("[merge] rendered", f)
    prog.finish()
print("[merge] done")
