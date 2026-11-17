# Quick look render of a dog asset: 3/4 front camera on the mesh bounds, sun + sky, GPU.
# blender.exe -b blender/assets/s04_dog/nubis.blend --python scripts/s04_dog_look.py -- <out.png> [yaw_deg]
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "renders/s04_kukur/test/look.png")
yaw = math.radians(float(argv[1])) if len(argv) > 1 else math.radians(35)
sc = bpy.context.scene

cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = int(os.environ.get("LOOK_SPP", 64))
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 100
sc.view_settings.view_transform = "AgX"

meshes = [o for o in sc.objects if o.type == "MESH" and o.visible_get() and len(o.data.vertices)]
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
ctr = (lo + hi) / 2
size = (hi - lo).length
print("[look] bounds", tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi))

# the dog faces -Y in DAZ space: camera in front-left, slightly above
fwd = Vector((math.sin(yaw), -math.cos(yaw), 0.18)).normalized()
cam_d = bpy.data.cameras.new("LookCam"); cam_d.lens = 50
cam = bpy.data.objects.new("LookCam", cam_d); sc.collection.objects.link(cam)
ctr = ctr + Vector((0, float(os.environ.get("LOOK_DY", 0)), float(os.environ.get("LOOK_DZ", 0))))
cam.location = ctr + fwd * size * float(os.environ.get("LOOK_DIST", 1.6))
cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

sun_d = bpy.data.lights.new("LookSun", "SUN"); sun_d.energy = 4; sun_d.angle = math.radians(2)
sun = bpy.data.objects.new("LookSun", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
world = bpy.data.worlds.new("LookWorld"); world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 0.6
sc.world = world
# ground
bpy.ops.mesh.primitive_plane_add(size=size * 6, location=(ctr.x, ctr.y, lo.z))
g = bpy.context.object
gm = bpy.data.materials.new("LookGround"); gm.use_nodes = True
next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[0].default_value = (0.35, 0.33, 0.3, 1)
g.data.materials.append(gm)

os.makedirs(os.path.dirname(out), exist_ok=True)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("[look] wrote", out)
