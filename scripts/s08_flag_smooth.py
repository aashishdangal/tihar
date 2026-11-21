"""s08 flag: cloth sim with the lumps smoothed away (owner 2026-11-21: "we have to do something in
between the current one [scripts/s08_flag_wave.py] and the paper like one but without that scrambled look").

Takes the try-2 bake (s08_flag_v003.blend, scripts/s08_flag_soften.py: steady wind, no wrap), and per
frame runs a Taubin smooth over the cloth surface: grid-sized lumps (3-6 cm) go, the big folds and
the irregular, real cloth motion stay. Hoist row stays pinned. Then the same seamless-loop search
and Hermite correction as scripts/s08_flag_loop_geo.py, written to blender/assets/s08/flag_smooth.pc2
and played by S08_FlagLoop.

Headless: blender.exe -b blender/scenes/s08_flag_v003.blend --python scripts/s08_flag_smooth.py
  env S08_SMOOTH = Taubin passes (default 25); S08_TEST=1 renders every 4th frame at 50 %
  to renders/s08_finale/test/flag_smooth/.
"""
import os
import struct

import bpy
import numpy as np

ROOT = r"E:/Projects/tihar"
ITER = int(os.environ.get("S08_SMOOTH", "25"))
TAG = os.environ.get("S08_TAG", "")             # "" = the approved v005 run; e.g. "_s70" for a stronger pass
BLEND = os.environ.get("S08_BLEND", "s08_flag_v005.blend")
sc = bpy.context.scene
fl = bpy.data.objects["S08_Flag"]; lo = bpy.data.objects["S08_FlagLoop"]
END = 560

me0 = fl.data
nv = len(me0.vertices)
ed = np.array([e.vertices[:] for e in me0.edges])
deg = np.bincount(ed.ravel(), minlength=nv).astype(np.float32)[:, None]
pin = np.array([v.co.x > -0.012 for v in me0.vertices])


def lap(P):
    acc = np.zeros_like(P)
    np.add.at(acc, ed[:, 0], P[ed[:, 1]]); np.add.at(acc, ed[:, 1], P[ed[:, 0]])
    return acc / deg - P


def taubin(P):
    P = P.copy()
    for _ in range(ITER):
        for k in (0.5, -0.53):
            d = lap(P) * k; d[pin] = 0; P += d
    return P


mods = [m for m in fl.modifiers if m.type != "CLOTH"]; vis = [m.show_viewport for m in mods]
for m in mods:
    m.show_viewport = False
fl.hide_viewport = False
P = []
for f in range(1, END + 1):
    sc.frame_set(f); me = fl.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    a = np.zeros(nv * 3, np.float32); me.vertices.foreach_get("co", a)
    P.append(taubin(a.reshape(-1, 3)).ravel())
for m, v in zip(mods, vis):
    m.show_viewport = v
P = np.array(P); V = np.diff(P, axis=0)
print("[smooth] sampled + smoothed", len(P), "frames,", ITER, "passes")

best = min(((np.sqrt(((P[a] - P[a + L]) ** 2).mean()) + 3 * np.sqrt(((V[a] - V[a + L]) ** 2).mean()), a, L)
            for a in range(60, END - 241) for L in range(240, 361) if a + L < END - 1))
_, a, L = best
D = P[a] - P[a + L]; E = (P[a + 1] - P[a]) - (P[a + L + 1] - P[a + L])
t = np.arange(L + 1) / L; h = 3 * t ** 2 - 2 * t ** 3; k = (t ** 3 - t ** 2) * L
seq = [P[a + i] + D * h[i] + E * k[i] for i in range(L)] + [P[a]]
path = ROOT + "/blender/assets/s08/flag_smooth%s.pc2" % TAG
# lumpiness per loop frame: mean |Laplacian| on inner vertices (mm); boundary verts excluded
inner = deg[:, 0] >= 4
lump = np.array([np.linalg.norm(lap(np.asarray(s).reshape(-1, 3))[inner], axis=1).mean() * 1000 for s in seq[:-1]])
order = np.argsort(-lump)
print("[smooth] lumpiness mm: mean %.3f max %.3f; worst frames %s" % (lump.mean(), lump.max(), [int(i) + 1 for i in order[:8]]))
with open(path, "wb") as fh:
    fh.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, nv, 1.0, 1.0, len(seq)))
    for s in seq:
        fh.write(np.asarray(s, np.float32).tobytes())
print("[smooth] loop: source frame", a + 1, "length", L)

lo.location = fl.location; lo.rotation_euler = fl.rotation_euler; lo.scale = fl.scale
mc = next(m for m in lo.modifiers if m.type == "MESH_CACHE"); mc.filepath = path; mc.frame_start = 1.0
sub = next(m for m in lo.modifiers if m.type == "SUBSURF"); sub.levels = 1; sub.render_levels = 2
lo.hide_render = False; lo.hide_viewport = False; fl.hide_render = True; fl.hide_viewport = True
sc.frame_start, sc.frame_end = 1, L
sc["s08_flag_loop"] = {"method": "smoothed sim", "source_start": a + 1, "length": L, "taubin": ITER}
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/" + BLEND)
print("[smooth] saved", bpy.data.filepath)

if os.environ.get("S08_TEST"):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "HIP"; prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == "HIP" and "9070" in dv.name
    sc.cycles.device = "GPU"; sc.cycles.samples = 24
    sc.render.resolution_percentage = 50
    out = ROOT + "/renders/s08_finale/test/flag_smooth" + TAG
    os.makedirs(out, exist_ok=True)
    if os.environ.get("S08_TESTALL"):                  # every frame, small, for a motion preview video
        sc.render.resolution_percentage = 35; sc.cycles.samples = 16
    for f in (range(1, L + 1) if os.environ.get("S08_TESTALL") else sorted(int(i) + 1 for i in order[:6])):
        sc.frame_set(f); sc.render.filepath = out + "/f_%04d.png" % f
        bpy.ops.render.render(write_still=True)
    print("[smooth] rendered test frames")
print("[smooth] done")
