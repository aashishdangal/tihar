"""s01 v032: 2 s valley hold, dark cloud sweeps in from the left over the valley and mountains,
short push toward it. The fade to black is done on the website over the last ~12 frames.
The cloud is a black solid blockout for timing (the real one will be a distant volume).
Saves to a new numbered file; the input is untouched.

Run: blender.exe -b s01_hero_v029.blend --python scripts/s01_cloud_sweep.py -- <out.blend>

Timeline (24 fps, 186 frames):
  1-12    sky hold (fade in from black)
  12-66   tilt down to the valley
  66-114  valley hold, camera locked (PAUSE at 90; can loop on the web)
  114-162 cloud sweeps in from the left, camera locked
  162-186 short push toward the cloud; web fades to black over ~174-186
"""
import math, random, sys
import bpy, bmesh
from mathutils import Matrix, Vector

out = sys.argv[sys.argv.index("--") + 1]
HOLD0, SWEEP0, PUSH0, END = 66, 114, 162, 186
NAME = "S01_DarkCloud_Blockout"

sc = bpy.context.scene
cam = bpy.data.objects["CAM_S01"]


def fcurves(idb):
    act = idb.animation_data.action
    if getattr(act, "fcurves", None):
        return list(act.fcurves)
    return [fc for l in act.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]


def rekey(idb, path, index, keys):
    fc = next(f for f in fcurves(idb) if f.data_path == path and f.array_index == index)
    fc.keyframe_points.clear()
    for fr, v in keys:
        kp = fc.keyframe_points.insert(fr, v)
        kp.interpolation = "BEZIER"
        kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    fc.update()


# --- camera: locked from the end of the tilt until the push
LOC = Vector((1500, -16500, 5200))
RX_SKY, RX_VAL, RZ = 1.955, 1.440, -0.052
sc.frame_set(HOLD0)
fwd = Matrix.Rotation(RZ, 3, "Z") @ Matrix.Rotation(RX_VAL, 3, "X") @ Vector((0, 0, -1))
LOC_END = LOC + fwd * 600
K = [(1, LOC, RX_SKY), (12, LOC, RX_SKY), (HOLD0, LOC, RX_VAL), (PUSH0, LOC, RX_VAL), (END, LOC_END, RX_VAL)]
for i in range(3):
    rekey(cam, "location", i, [(f, l[i]) for f, l, _ in K])
rekey(cam, "rotation_euler", 0, [(f, r) for f, _, r in K])
rekey(cam, "rotation_euler", 1, [(f, 0.0) for f, _, _ in K])
rekey(cam, "rotation_euler", 2, [(f, RZ) for f, _, _ in K])
rekey(sc, "view_settings.exposure", 0, [(1, -14.0), (3, -4.0), (12, 0.8)])
sc.frame_start, sc.frame_end = 1, END
for m in sc.timeline_markers:
    if m.name == "PAUSE":
        m.frame = 90

# --- cloud blockout, built in front of the hold-frame camera
sc.frame_set(HOLD0)
M = cam.matrix_world.copy()
fx = cam.data.angle_x
fy = 2 * math.atan(math.tan(fx / 2) * sc.render.resolution_y / sc.render.resolution_x)
tx, ty = math.tan(fx / 2), math.tan(fy / 2)
D = 8500  # metres from the camera: in front of the city and the mountains
w, h = D * tx, D * ty
rng = random.Random(11)
bm = bmesh.new()

# solid core: covers the frame from the bottom up to 0.70 h once in place
core = bmesh.ops.create_cube(bm, size=1.0)["verts"]
x0, x1, y0, y1 = -3.0 * w, 1.15 * w, -1.6 * h, 0.70 * h
bmesh.ops.transform(bm, verts=core, matrix=M @ Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, -D))
                    @ Matrix.Diagonal((x1 - x0, y1 - y0, 900, 1)))


def blob(x, y, r, dz=0.0):
    p = M @ Vector((x, y, -(D + dz)))
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r, matrix=Matrix.Translation(p))


for _ in range(70):   # billowing leading edge (right side), which is what the eye follows
    blob(rng.uniform(1.0, 1.35) * w, rng.uniform(-1.4, 0.8) * h, rng.uniform(0.12, 0.28) * h, rng.uniform(-400, 400))
for _ in range(110):  # lumpy top edge over the mountains
    blob(rng.uniform(-3.0, 1.3) * w, rng.uniform(0.62, 0.85) * h, rng.uniform(0.08, 0.2) * h, rng.uniform(-400, 400))

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
tex.noise_scale = 500
dm = ob.modifiers.new("Lumps", "DISPLACE")
dm.texture = tex
dm.strength = 250

# sweep: start fully off the left edge, end in place
right = M.to_3x3() @ Vector((1, 0, 0))
off = -right * (x1 + 1.4 * w + 0.3 * h)
for f, v in ((SWEEP0, off), (PUSH0, Vector())):
    ob.location = v
    ob.keyframe_insert("location", frame=f)

bpy.ops.wm.save_as_mainfile(filepath=out, copy=False)
print(f"[sweep] saved {out}  cloud at {D} m, w={w:.0f} h={h:.0f}")
