# Fit check: scale Nubis to 0.65, append the S04 mala + tika from hand_props_v001.blend, parent them to the
# rig, save as blender/scenes/s04_kukur_propsfit_v001.blend (a COPY; s04_kukur_v001.blend is not touched),
# then render the mala on the neck and the tika on the forehead.
# blender -b blender/scenes/s04_kukur_v001.blend --python scripts/s04_hand_propsfit.py -- <out_dir>
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir = os.path.abspath(argv[0])
PROPS = r"E:\Projects\tihar\blender\assets\s04_hand\hand_props_v001.blend"
SAVE = r"E:\Projects\tihar\blender\scenes\s04_kukur_propsfit_v001.blend"
sc = bpy.context.scene
rig = bpy.data.objects["Nubis"]
for o in bpy.data.objects:
    print("[fit] obj", o.name, o.type, "parent", o.parent.name if o.parent else None, "hide_render", o.hide_render, "visible", o.visible_get())
rig.scale = (0.65, 0.65, 0.65)
# "Nubis Strand Fur" is not parented to the rig, so it does not follow the 0.65 scale: hide it in this copy
if "Nubis Strand Fur" in bpy.data.objects:
    bpy.data.objects["Nubis Strand Fur"].hide_render = True; bpy.data.objects["Nubis Strand Fur"].hide_set(True)
bpy.context.view_layer.update()

with bpy.data.libraries.load(PROPS, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("S04_Mala", "S04_Tika")]
for o in dst.objects:
    sc.collection.objects.link(o)
bpy.context.view_layer.update()

def parent_keep(ob, bone):
    mw = ob.matrix_world.copy()
    ob.parent = rig; ob.parent_type = "BONE"; ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw
mala = bpy.data.objects["S04_Mala"]; tika = bpy.data.objects["S04_Tika"]
parent_keep(mala, "NeckBase"); parent_keep(tika, "Head")
bpy.context.view_layer.update()
# tika = red stain in the fur (driven by the S04_Tika empty)
exec(open(r"E:/Projects/tihar/scripts/s04_hand_tika_stain.py").read())
print("[fit] mala at", tuple(round(v, 3) for v in mala.matrix_world.translation), "tika at", tuple(round(v, 3) for v in tika.matrix_world.translation))

# camera + light for the checks (kept in the copy as T_ objects)
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"; cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"
sc.cycles.samples = int(os.environ.get("SPP", 64)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 75
sc.view_settings.view_transform = "AgX"
sun_d = bpy.data.lights.new("T_Sun", "SUN"); sun_d.energy = 2.5; sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("T_Sun", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
w = bpy.data.worlds.new("T_World"); w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.55, 0.62, 0.75, 1); bg.inputs[1].default_value = 0.6
sc.world = w
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
g = bpy.context.object; g.name = "T_Ground"
gm = bpy.data.materials.new("T_Ground"); gm.use_nodes = True
next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[0].default_value = (0.3, 0.27, 0.24, 1)
g.data.materials.append(gm)
cd = bpy.data.cameras.new("T_Cam"); cam = bpy.data.objects.new("T_Cam", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.dof.use_dof = True
bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
print("[fit] saved", SAVE)

def shoot(name, target, direction, dist, lens, fstop):
    cd.lens = lens; cd.dof.aperture_fstop = fstop; cd.dof.focus_distance = dist
    cam.location = target + Vector(direction).normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out_dir, name)
    bpy.ops.render.render(write_still=True)
    print("[fit] wrote", sc.render.filepath)

pts = [mala.matrix_world @ Vector(p.co[:3]) for p in mala.data.splines[0].points]
mc = sum(pts, Vector()) / len(pts)
head = rig.matrix_world @ rig.pose.bones["Head"].head
shoot("props_dog_mala.png", (mc + head) / 2 + Vector((0, 0, -0.02)), (math.sin(math.radians(35)), -math.cos(math.radians(35)), 0.25), 1.15, 50, 8)
shoot("props_dog_mala_side.png", (mc + head) / 2, (1, -0.15, 0.2), 1.15, 50, 8)
shoot("props_dog_mala_back.png", (mc + head) / 2, (-0.6, 1, 0.45), 1.15, 50, 8)
tc = tika.matrix_world.translation
n = tika.matrix_world.to_3x3() @ Vector((0, 0, 1))
shoot("props_dog_tika.png", tc, n + Vector((0.25, 0, 0.1)), 0.22, 60, 5.6)
shoot("props_dog_tika_mid.png", tc + Vector((0, 0, -0.03)), n + Vector((0.5, 0, -0.1)), 0.55, 50, 8)
