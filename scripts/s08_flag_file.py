"""Light-weight flag file for s08 (owner 2026-11-20: "we are rendering flag without background and
placing it there in same lighting so its not that heavy").

Run headless on the current finale save; writes blender/scenes/s08_flag.blend:
  blender.exe -b s08_finale_v069.blend --python scripts/s08_flag_file.py

Keeps: flag, pole, finial, wind + gusts, CAM_S08, the world (same dusk sky) and a bare copy of
the hill (no grass) that the camera cannot see, so the flag still gets the hill's bounce light and
sky occlusion. Everything else (city, terrain, City Generator, trees) is deleted from this copy.
Film is transparent: the frames go straight over the finale plate in the same camera.
Then rebuilds the pennant cloth (scripts/s08_flag_rebuild.py) and bakes it.
"""
import time

import bpy

KEEP = {"S08_Flag", "S08_FlagPole", "S08_FlagFinial", "S08_Wind", "S08_Gusts", "CAM_S08", "S08_Hill"}
sc = bpy.context.scene

for o in list(bpy.data.objects):
    if o.name not in KEEP:
        bpy.data.objects.remove(o, do_unlink=True)
for lib in list(bpy.data.libraries):
    bpy.data.libraries.remove(lib)
hill = bpy.data.objects["S08_Hill"]
for m in list(hill.modifiers):
    hill.modifiers.remove(m)
hill.visible_camera = False
hill.name = "S08_Hill_Bounce"
for c in list(bpy.data.collections):
    if not c.objects and not c.children:
        bpy.data.collections.remove(c)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

sc.camera = bpy.data.objects["CAM_S08"]
sc.render.film_transparent = True
sc.cycles.samples = 128
sc.cycles.use_denoising = True
sc.render.use_persistent_data = True

exec(open(r"E:/Projects/tihar/scripts/s08_flag_rebuild.py", encoding="utf-8").read())
# wind (owner 2026-11-20 "add wind and animate"; "wind should be from back of the camera towards the
# mountain side"): a steady breeze toward +Y (north) with built-in noise,
# strength re-keyed every 0.75-1.7 s (900-1500) and direction wandering +-8 deg; small turbulence
# (0.45 m) drifting with the wind at ~3 m/s for the flutter. A wind blowing exactly along the
# cloth alone keeps it rigid and flat, then it collapses - the turbulence is what makes it flap.
import math, random
rnd = random.Random(11)
sc.frame_start, sc.frame_end = 1, 200
w = bpy.data.objects["S08_Wind"]; g = bpy.data.objects["S08_Gusts"]
w.animation_data_clear(); g.animation_data_clear()
# owner: "angled so that flag is viewable", then "fly more to the left" -> heading 60 deg WEST of north: the flag flies away and
# to the left into the frame, showing its back (moon and sun mirrored, as a real flag seen from that
# side); pole back at the v069 spot near the right edge, balancing the tree on the left
from mathutils import Vector
A = math.radians(-60)
pole = bpy.data.objects["S08_FlagPole"]; fl = bpy.data.objects["S08_Flag"]; fin = bpy.data.objects["S08_FlagFinial"]
hill = bpy.data.objects["S08_Hill_Bounce"]; mi = hill.matrix_world.inverted()
nx, ny = pole.location.x, pole.location.y        # the v069 spot near the right edge
hit = hill.ray_cast(mi @ Vector((nx, ny, 3000)), (mi.to_3x3() @ Vector((0, 0, -1))).normalized())
gz = (hill.matrix_world @ hit[1]).z; H = pole.dimensions.z
pole.location = (nx, ny, gz + H / 2); top = gz + H
fin.location = (nx, ny, top + 0.03)
d = Vector((math.sin(A), math.cos(A), 0))
fl.rotation_euler = (0, 0, math.atan2(-d.y, -d.x))      # local -X -> wind heading
fl.location = (nx + 0.03 * d.x, ny + 0.03 * d.y, top - 0.08 - 1.35)
w.location = (nx - 4 * d.x, ny - 4 * d.y, 1999.6); w.field.noise = 3.5
fr = 1
while fr <= 200:
    w.field.strength = rnd.uniform(900, 1500); w.field.keyframe_insert("strength", frame=fr)
    w.rotation_euler = (math.radians(-90), 0.0, -A + math.radians(rnd.uniform(-8, 8))); w.keyframe_insert("rotation_euler", frame=fr)
    fr += rnd.randint(18, 40)
g.field.size = 0.45; g.field.flow = 0.0
g.location = (nx - 5 * d.x, ny - 5 * d.y, 1999.6); g.keyframe_insert("location", frame=1)
g.location = (nx + 20 * d.x, ny + 20 * d.y, 1999.6); g.keyframe_insert("location", frame=200)
fr = 1
while fr <= 200:
    g.field.strength = rnd.uniform(400, 750); g.field.keyframe_insert("strength", frame=fr)
    fr += rnd.randint(10, 24)
f = bpy.data.objects["S08_Flag"]; cm = next(m for m in f.modifiers if m.type == "CLOTH")
cm.settings.mass = 0.05; cm.settings.air_damping = 1.0; cm.settings.quality = 10
cm.point_cache.frame_end = 200
sc.frame_set(1)
t = time.time()
with bpy.context.temp_override(point_cache=cm.point_cache, active_object=f, object=f):
    bpy.ops.ptcache.free_bake(); bpy.ops.ptcache.bake(bake=True)
print("[flagfile] baked", cm.point_cache.is_baked, round(time.time() - t), "s")
bpy.ops.wm.save_as_mainfile(filepath=r"E:\Projects\tihar\blender\scenes\s08_flag.blend")
print("[flagfile] saved", bpy.data.filepath, [o.name for o in bpy.data.objects])
