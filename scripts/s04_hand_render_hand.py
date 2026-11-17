# Test-render the S04 hand in each saved pose, side by side frames (never saves the .blend).
# blender -b blender/assets/s04_hand/hand_props_v001.blend --python scripts/s04_hand_render_hand.py -- <out_dir>
# Writes <out_dir>/props_hand_<Pose>.png for HandRest, HandHoldMala, HandTika.
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir = os.path.abspath(argv[0])
sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"; cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"
sc.cycles.samples = int(os.environ.get("SPP", 64)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 720, 900
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"
sc.view_settings.exposure = -0.8          # grey card ~ mid grey

for o in sc.objects:
    if o.name.startswith(("S04_Mala", "S04_Tika", "S04_Marigold", "S04_HandL")) and o.name != "S04_TikaFinger":
        o.hide_render = True

arm = bpy.data.objects["S04_Hand_Rig"]
# warm late-morning light: sun + soft sky + a dark earthy floor far below
sun_d = bpy.data.lights.new("T_Sun", "SUN"); sun_d.energy = 2.0; sun_d.angle = math.radians(4)
sun = bpy.data.objects.new("T_Sun", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(40), 0, math.radians(30))
w = bpy.data.worlds.new("T_World"); w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.58, 0.6, 0.66, 1); bg.inputs[1].default_value = 0.6
sc.world = w
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0.6, 0), rotation=(math.radians(90), 0, 0))
g = bpy.context.object
gm = bpy.data.materials.new("T_Back"); gm.use_nodes = True
next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[0].default_value = (0.16, 0.12, 0.09, 1)
g.data.materials.append(gm)

if os.environ.get("GREYCARD"):
    # 18% grey card beside the hand for exposure/albedo calibration
    bpy.ops.mesh.primitive_plane_add(size=0.05, location=(0.09, -0.02, 0.12))
    gc = bpy.context.object; gc.name = "T_GreyCard"
    gcm = bpy.data.materials.new("T_Grey18"); gcm.use_nodes = True
    next(n for n in gcm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[0].default_value = (0.18, 0.18, 0.18, 1)
    gc.data.materials.append(gcm)
cd = bpy.data.cameras.new("T_Cam"); cd.lens = 85
cam = bpy.data.objects.new("T_Cam", cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = Vector((0.01, 0, 0.05))
VIEWS = {"HandTika": (0.75, -0.6, 0.25)} if os.environ.get("GREYCARD") else {"HandRest": (-0.35, -0.9, 0.2), "HandHoldMala": (0.55, -0.8, 0.3), "HandTika": (0.75, -0.6, 0.25)}
ns = {}
exec(compile(open(os.path.join(os.path.dirname(__file__), "s04_hand_poses.py")).read().replace(
    "if __name__ == \"__main__\" or True:\n    build_pose_actions()", ""), "poses", "exec"), ns)
for pose, view in VIEWS.items():
    ns["apply_pose"](pose)
    bpy.context.view_layer.update()
    cam.location = tgt + Vector(view).normalized() * 0.75
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    if "T_GreyCard" in bpy.data.objects:
        gco = bpy.data.objects["T_GreyCard"]
        gco.rotation_euler = (cam.location - gco.location).to_track_quat("Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out_dir, ("calib_hand_%s.png" if os.environ.get("GREYCARD") else "props_hand_%s.png") % pose)
    bpy.ops.render.render(write_still=True)
    print("[hand-render] wrote", sc.render.filepath)
