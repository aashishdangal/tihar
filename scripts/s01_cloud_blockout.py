"""s01: black solid blockout of the dark cloud that rolls up and hides the valley (frames 114-162).
Lumpy icosphere top edge over a solid slab, built in front of the frame-162 camera, rising from
below. Clay/timing check only; the real cloud will be a volume. Saves to a new numbered file.

Run: blender.exe -b s01_hero_v029.blend --python scripts/s01_cloud_blockout.py -- <out.blend> [start end]
"""
import math, random, sys
import bpy, bmesh
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
f0 = int(argv[1]) if len(argv) > 1 else 114
f1 = int(argv[2]) if len(argv) > 2 else 162
NAME = "S01_DarkCloud_Blockout"

sc = bpy.context.scene
cam = bpy.data.objects["CAM_S01"]
sc.frame_set(f1)
M = cam.matrix_world.copy()

fx = cam.data.angle_x
fy = 2 * math.atan(math.tan(fx / 2) * sc.render.resolution_y / sc.render.resolution_x)
tx, ty = math.tan(fx / 2), math.tan(fy / 2)
print(f"[cloud] fov x={math.degrees(fx):.1f} y={math.degrees(fy):.1f}")

rng = random.Random(7)
bm = bmesh.new()


def blob(d, x, y, r):
    """sphere of radius r at camera-local (x, y) at distance d (camera looks down -Z)."""
    p = M @ Vector((x, y, -d))
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r, matrix=Matrix.Translation(p))


# solid slab behind everything: guarantees the final frame is fully covered
D_BACK = 1100
hb, wb = D_BACK * ty, D_BACK * tx
slab = bmesh.ops.create_cube(bm, size=1.0)["verts"]
S = Matrix.Diagonal((wb * 3.2, hb * 5.2, 200, 1))
T = Matrix.Translation((0, -1.4 * hb, -D_BACK))
bmesh.ops.transform(bm, matrix=M @ T @ S, verts=slab)

# lumpy billows: a top edge row plus scattered front lumps
for _ in range(140):
    d = rng.uniform(650, 1050)
    h, w = d * ty, d * tx
    x = rng.uniform(-1.6 * w, 1.6 * w)
    y = rng.uniform(0.9 * h, 1.25 * h)
    blob(d, x, y, rng.uniform(0.22, 0.45) * h)
for _ in range(120):
    d = rng.uniform(600, 1050)
    h, w = d * ty, d * tx
    blob(d, rng.uniform(-1.6 * w, 1.6 * w), rng.uniform(-3.5 * h, 0.9 * h), rng.uniform(0.3, 0.6) * h)

old = bpy.data.objects.get(NAME)
if old:
    bpy.data.objects.remove(old)
me = bpy.data.meshes.new(NAME)
bm.to_mesh(me)
bm.free()
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new(NAME, me)
sc.collection.objects.link(ob)
ob.color = (0.0, 0.0, 0.0, 1.0)

tex = bpy.data.textures.new(NAME + "_tex", "CLOUDS")
tex.noise_scale = 60
dm = ob.modifiers.new("Lumps", "DISPLACE")
dm.texture = tex
dm.strength = 40
dm.mid_level = 0.5

# rise from below: start low enough that even the top billows sit under the frame at f0
rise = 4.2 * hb
ob.location = (0, 0, -rise)
ob.keyframe_insert("location", index=2, frame=f0)
ob.location = (0, 0, 0)
ob.keyframe_insert("location", index=2, frame=f1)

bpy.ops.wm.save_as_mainfile(filepath=out, copy=False)
print("[cloud] saved", out, "rise", round(rise))
