"""Short seamless flag loop, made in the cloth itself (owner 2026-11-20: "still looks fake make such
that the first frame becomes last frame make this video short ... such that we can loop it", then "make it 10-15 s long ... but loopable").

The image crossfade (scripts/s08_flag_loop.py) blended two different flag shapes for a moment and
read as ghostly. Instead:
  1. sample the baked cloth (S08_Flag, cloth modifier only) for frames 1..320,
  2. pick the 240-360 frame (10-15 s) stretch whose end best matches its start in shape AND motion
     -> start 88, 350 frames (14.6 s at 24 fps),
  3. add a cubic Hermite correction D*h(t) + E*k(t) (D = shape gap, E = per-frame velocity gap):
     zero at the start, and at the end the shape AND velocity equal the first frame's, so the wrap
     has no jump and no jerk (< 0.3 mm per frame of correction),
  4. write it as a PC2 cache (blender/assets/s08/flag_loop.pc2) played by S08_FlagLoop
     (Mesh Cache -> Subdivision -> Solidify); the cloth flag is hidden.
Render frames 1-350; played on repeat, frame 350 flows into frame 1 with no blend.

Run inside the live Blender on blender/scenes/s08_flag.blend:
  exec(open(r"E:/Projects/tihar/scripts/s08_flag_loop48.py", encoding="utf-8").read())
"""
import struct

import bpy
import numpy as np

sc = bpy.context.scene
fl = bpy.data.objects["S08_Flag"]
END = 560                     # bake (wind keys) must cover the 240-360 frame search
mods = [m for m in fl.modifiers if m.type != "CLOTH"]; vis = [m.show_viewport for m in mods]
for m in mods:
    m.show_viewport = False
fl.hide_viewport = False
P = []
for f in range(1, END + 1):
    sc.frame_set(f); me = fl.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    a = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", a); P.append(a)
for m, v in zip(mods, vis):
    m.show_viewport = v
P = np.array(P); V = np.diff(P, axis=0)
best = min(((np.sqrt(((P[a] - P[a + L]) ** 2).mean()) + 3 * np.sqrt(((V[a] - V[a + L]) ** 2).mean()), a, L)
            for a in range(40, END - 241) for L in range(240, 361) if a + L < END - 1))
_, a, L = best
D = P[a] - P[a + L]; E = (P[a + 1] - P[a]) - (P[a + L + 1] - P[a + L])
t = np.arange(L + 1) / L; h = 3 * t ** 2 - 2 * t ** 3; k = (t ** 3 - t ** 2) * L
seq = [P[a + i] + D * h[i] + E * k[i] for i in range(L)] + [P[a]]
nv = P.shape[1] // 3
path = r"E:/Projects/tihar/blender/assets/s08/flag_loop.pc2"
with open(path, "wb") as f:
    f.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, nv, 1.0, 1.0, len(seq)))
    for s in seq:
        f.write(np.asarray(s, np.float32).tobytes())
lo = bpy.data.objects.get("S08_FlagLoop")
if lo is None:
    lo = bpy.data.objects.new("S08_FlagLoop", fl.data.copy()); fl.users_collection[0].objects.link(lo)
lo.matrix_world = fl.matrix_world.copy()
for m in list(lo.modifiers):
    lo.modifiers.remove(m)
mc = lo.modifiers.new("LoopCache", "MESH_CACHE"); mc.cache_format = "PC2"; mc.filepath = path
mc.frame_start = 1.0; mc.play_mode = "SCENE"; mc.time_mode = "FRAME"
s = lo.modifiers.new("S08_FlagSubsurf", "SUBSURF"); s.levels = s.render_levels = 1
so = lo.modifiers.new("S08_FlagSolidify", "SOLIDIFY"); so.thickness = 0.002; so.offset = 0.0
fl.hide_render = True; fl.hide_viewport = True
sc.frame_start, sc.frame_end = 1, L
sc["s08_flag_loop"] = {"source_start": a + 1, "length": L}
sc.frame_set(1)
bpy.ops.wm.save_mainfile()
print("loop: source frame", a + 1, "length", L)
