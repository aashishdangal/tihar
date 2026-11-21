"""Wind sweep for the s08 flag (owner 2026-11-21: "the flag still is wrinkled and looks unrealistic on some
frames"). The approved smoothed loop (v005) bunches up from ~frame 90: the try-2 sim slowly stops
flying (mean fly-out 0.43 m -> 0.28 m). Here several wind setups are baked on s08_flag_v003.blend and
measured: fly-out (how far the cloth stands off the pole) and lumpiness, over the whole bake.

  blender.exe -b blender/scenes/s08_flag_v003.blend --python scripts/s08_flag_sweep.py
Env S08_PICK=<name> bakes only that config and saves it as s08_flag_v007.blend (input to s08_flag_smooth.py).
"""
import math
import os
import random

import bpy
import numpy as np
from mathutils import Vector

ROOT = r"E:/Projects/tihar"
END = 560
sc = bpy.context.scene
fl = bpy.data.objects["S08_Flag"]; cm = next(m for m in fl.modifiers if m.type == "CLOTH")
w = bpy.data.objects["S08_Wind"]; g = bpy.data.objects["S08_Gusts"]
pole = bpy.data.objects["S08_FlagPole"].matrix_world.translation.copy()
sc.frame_set(1)
base_rot = w.rotation_euler.z
g_start = g.location.copy()
wd = Vector((-math.sin(base_rot), math.cos(base_rot), 0))
me0 = fl.data; nv = len(me0.vertices)
ed = np.array([e.vertices[:] for e in me0.edges])
deg = np.bincount(ed.ravel(), minlength=nv)[:, None].astype(np.float32)
inner = deg[:, 0] >= 4

# name: wind min/max, wobble deg, wind noise, gust min/max, gust size, gust drift m/s, wind yaw offset deg[, bending]
# round 2 (owner: "see how it curls under itself" - tips folding back in frames 100-250 of "strong")
CONFIGS = {
    "strong_b2":   (3800, 4600, 3, 1.0, 250, 380, 2.5, 0.0, 8, 2.0),
    "strong_b4":   (3800, 4600, 3, 1.0, 250, 380, 2.5, 0.0, 8, 4.0),
    "calm_b2":     (3800, 4600, 2, 0.5, 120, 200, 3.0, 0.0, 8, 2.0),
    "calm_b4":     (3800, 4600, 2, 0.5, 120, 200, 3.0, 0.0, 8, 4.0),
    "calm_b8":     (3800, 4600, 2, 0.5, 120, 200, 3.0, 0.0, 8, 8.0),
    "strong_ref":  (3800, 4600, 3, 1.0, 250, 380, 2.5, 0.0, 8, 0.9),     # = "strong", for the curl baseline
    "calm_b12":    (3800, 4600, 2, 0.5, 120, 200, 3.0, 0.0, 8, 12.0),
    "calm_b16":    (3800, 4600, 2, 0.5, 120, 200, 3.0, 0.0, 8, 16.0),
}
ROUND1 = {  # fly-out after f60: try2 0.32, steady_gust 0.31, oblique10 0.34, strong 0.41 (picked), strong_flut 0.39, oblique20 0.36
    "try2":      (2600, 3200, 3, 1.0, 120, 220, 2.5, 3.0, 0),
    "steady_gust": (2600, 3200, 3, 1.0, 300, 450, 2.5, 0.0, 0),
    "oblique10": (2600, 3200, 3, 1.0, 200, 320, 2.5, 0.0, 10),
    "strong":    (3800, 4600, 3, 1.0, 250, 380, 2.5, 0.0, 8),
    "strong_flut": (3600, 4400, 4, 2.0, 400, 550, 1.6, 0.0, 8),
    "oblique20": (3200, 3800, 3, 1.0, 250, 380, 2.5, 0.0, 20),
}


def setup(cfg):
    wmin, wmax, wob, noise, gmin, gmax, gsize, drift, yaw = cfg[:9]
    cm.settings.bending_stiffness = cfg[9] if len(cfg) > 9 else 0.9
    rnd = random.Random(21)
    w.animation_data_clear(); g.animation_data_clear()
    w.field.noise = noise
    fr = 1
    while fr <= END:
        w.field.strength = rnd.uniform(wmin, wmax); w.field.keyframe_insert("strength", frame=fr)
        w.rotation_euler = (math.radians(-90), 0.0, base_rot + math.radians(yaw + rnd.uniform(-wob, wob)))
        w.keyframe_insert("rotation_euler", frame=fr)
        fr += rnd.randint(24, 48)
    g.field.size = gsize; g.field.flow = 0.0
    g.location = g_start; g.keyframe_insert("location", frame=1)
    g.location = g_start + wd * (drift * END / 24.0); g.keyframe_insert("location", frame=END)
    fr = 1
    while fr <= END:
        g.field.strength = rnd.uniform(gmin, gmax); g.field.keyframe_insert("strength", frame=fr)
        fr += rnd.randint(16, 32)
    cm.point_cache.frame_start = 1; cm.point_cache.frame_end = END
    fl.hide_viewport = False
    sc.frame_set(1)
    with bpy.context.temp_override(point_cache=cm.point_cache, active_object=fl, object=fl):
        bpy.ops.ptcache.free_bake(); bpy.ops.ptcache.bake(bake=True)


def measure():
    mods = [m for m in fl.modifiers if m.type != "CLOTH"]; vis = [m.show_viewport for m in mods]
    for m in mods:
        m.show_viewport = False
    fo, lu, fold = [], [], []
    tris = np.array([p.vertices[:3] for p in me0.polygons])
    for f in range(1, END + 1, 10):
        sc.frame_set(f); me = fl.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        a = np.zeros(nv * 3, np.float32); me.vertices.foreach_get("co", a); a = a.reshape(-1, 3)
        wa = np.array([fl.matrix_world @ Vector(c) for c in a])
        fo.append(np.hypot(wa[:, 0] - pole.x, wa[:, 1] - pole.y).mean())
        acc = np.zeros_like(a); np.add.at(acc, ed[:, 0], a[ed[:, 1]]); np.add.at(acc, ed[:, 1], a[ed[:, 0]])
        lu.append(np.linalg.norm((acc / deg - a)[inner], axis=1).mean() * 1000)
        n = np.cross(a[tris[:, 1]] - a[tris[:, 0]], a[tris[:, 2]] - a[tris[:, 0]])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        mn = n.mean(0); mn /= np.linalg.norm(mn)
        fold.append((n @ mn < 0.0).mean() * 100)          # % of the cloth facing backwards (curled under)
    for m, v in zip(mods, vis):
        m.show_viewport = v
    fo, lu = np.array(fo), np.array(lu)
    late = fo[6:]                                     # after the first 60 frames
    global FOLD
    FOLD = np.array(fold[6:])
    return fo, lu, late


pick = os.environ.get("S08_PICK")
for name, cfg in CONFIGS.items():
    if pick and name != pick:
        continue
    setup(cfg)
    fo, lu, late = measure()
    print("[sweep] %-12s fly-out mean %.2f min %.2f | lump %.2f | curled-under %% mean %.1f max %.1f frames>3%%: %d/%d" % (
        name, late.mean(), late.min(), lu.mean(), FOLD.mean(), FOLD.max(), (FOLD > 3).sum(), len(FOLD)))
if pick and pick not in CONFIGS:
    raise SystemExit("unknown config " + pick)
if pick:
    sc["s08_flag_wind"] = {"config": pick, "values": list(CONFIGS[pick])}
    bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/" + os.environ.get("S08_BLEND", "s08_flag_v009.blend"))
    print("[sweep] saved", bpy.data.filepath)
