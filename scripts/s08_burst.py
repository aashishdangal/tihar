"""The gold that ends scene 7 becomes the first firework of scene 8 (owner 2026-11-21: "any idea we can do
after that golden by rendering" -> chose option 2: a rendered gold burst right in front of the lens that
breaks into sparks and reveals the out-of-focus valley).

Its own tiny scene (not the 860 MB finale), so it is cheap: black world, nothing but light. The browser
adds it over the valley (additive), so wherever it is dark the valley shows through.
  frames 1-4   a huge gold flash in front of the lens, filling the frame (scene 7's last-frame gold)
  frames 4-36  ~450 sparks on falling arcs with motion-blur trails, white-gold cooling to amber, fading;
               a few fly almost into the lens and go soft (depth of field)
Camera = CAM_S08's lens and frame (45 mm, 36 mm sensor, 1920x1080).

  blender.exe -b --factory-startup --python scripts/s08_burst.py
Env S08_PREVIEW=1: 35 %, 24 spp. Out: renders/s08_finale/burst[_preview]/f_0001..0036.png
Live progress: python scripts/render_watch.py <out>
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

ROOT = r"E:/Projects/tihar"
sys.path.insert(0, ROOT + "/scripts")
import render_progress_hook as rp  # noqa: E402

PREVIEW = bool(os.environ.get("S08_PREVIEW"))
N_FRAMES = 36                      # 1.5 s at 24 fps
N_SPARKS = 450
FPS = 24
GOLD = (1.0, 0.52, 0.17)           # preview 2 came out cream (238,229,217): AgX whitens bright light, so a deeper gold

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, N_FRAMES
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 35 if PREVIEW else 100
world = bpy.data.worlds.new("Black"); sc.world = world
world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0, 0, 0, 1)

# camera at the origin looking down +Y, 45 mm like CAM_S08; focused on the burst, f/2.8
cd = bpy.data.cameras.new("CAM_Burst"); cd.lens = 45; cd.sensor_width = 36
cd.dof.use_dof = True; cd.dof.focus_distance = 7.0; cd.dof.aperture_fstop = 2.8
cam = bpy.data.objects.new("CAM_Burst", cd); sc.collection.objects.link(cam)
cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam

C = Vector((0.0, 7.0, 0.55))       # burst centre: 7 m out, a little above the frame centre


def emit_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    # colour and strength come from the object: rgb = colour, alpha = strength / 100
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 100.0
    nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    nt.links.new(oi.outputs["Alpha"], mul.inputs[0]); nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


mat = emit_mat("M_Spark")


def soft_flash_mat():
    """the flash: brightest where it faces the lens, fading to nothing at its rim (preview 1 was a hard disc)"""
    m = emit_mat("M_Flash"); nt = m.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    mul = next(n for n in nt.nodes if n.type == "MATH")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 3.0
    nt.links.new(inv.outputs[0], pw.inputs[0])
    k = nt.nodes.new("ShaderNodeMath"); k.operation = "MULTIPLY"
    nt.links.new(mul.outputs[0], k.inputs[0]); nt.links.new(pw.outputs[0], k.inputs[1])
    nt.links.new(k.outputs[0], em.inputs["Strength"])
    # see-through, so the sparks inside show as the flash fades
    mix = nt.nodes.new("ShaderNodeMixShader"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    mix.inputs[0].default_value = 1.0
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m

# the flash: a big soft sphere right in front of the lens
fm = bpy.data.meshes.new("Flash")
import bmesh  # noqa: E402
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0); bm.to_mesh(fm); bm.free()
for p in fm.polygons:
    p.use_smooth = True
fm.materials.append(soft_flash_mat())
flash = bpy.data.objects.new("Flash", fm); sc.collection.objects.link(flash)
flash.location = C
# preview 1 clipped to white: strengths are object alpha x 100, so these are 6 / 5 / 3.5 ... not 400
for f, r, s in ((1, 5.5, 0.032), (2, 4.6, 0.027), (3, 3.4, 0.020), (4, 2.2, 0.010), (6, 1.0, 0.003), (8, 0.5, 0.0)):
    flash.scale = (r, r, r); flash.keyframe_insert("scale", frame=f)
    flash.color = (*GOLD, s); flash.keyframe_insert("color", frame=f)

# sparks: small spheres on ballistic arcs (gravity + drag), keyed every frame
sm = bpy.data.meshes.new("Spark")
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.018); bm.to_mesh(sm); bm.free()
sm.materials.append(mat)
rnd = random.Random(8)
G = Vector((0, 0, -3.2)); DRAG = 1.1
for i in range(N_SPARKS):
    d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
    if d.y < -0.6 and rnd.random() < 0.85:          # fewer straight at the lens, but keep a few
        d.y = -d.y
    v = d * rnd.uniform(5.5, 9.0)
    life = rnd.uniform(0.9, 1.45)                     # seconds
    t0 = rnd.uniform(0.0, 0.06)
    ob = bpy.data.objects.new("Spark%03d" % i, sm); sc.collection.objects.link(ob)
    p = C.copy(); vel = v.copy()
    for f in range(1, N_FRAMES + 1):
        t = (f - 1) / FPS
        if f > 1:
            dt = 1 / FPS
            vel = vel * math.exp(-DRAG * dt) + G * dt
            if t > t0:
                p = p + vel * dt
        age = max(0.0, t - t0) / life
        heat = max(0.0, 1.0 - age)                    # 1 -> 0
        col = (1.0, 0.42 + 0.30 * heat, 0.07 + 0.25 * heat * heat)   # gold -> deep amber
        strength = (0.0 if t < t0 else 0.07 * heat ** 1.4 * (1.0 + 1.5 * (rnd.random() < 0.08)))   # x100 = 7
        ob.location = p; ob.keyframe_insert("location", frame=f)
        ob.color = (*col, strength); ob.keyframe_insert("color", frame=f)

# motion-blur trails, GPU
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.9
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "HIP"; prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type == "HIP" and "9070" in dv.name
c = sc.cycles
c.device = "GPU"; c.samples = 24 if PREVIEW else 96; c.use_denoising = True
c.max_bounces = 2
sc.view_settings.view_transform = "AgX"
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
sc.render.use_persistent_data = True

out = ROOT + "/renders/s08_finale/" + ("burst_preview" if PREVIEW else "burst")
os.makedirs(out, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_burst.blend")
frames = list(range(1, N_FRAMES + 1))
prog = rp.Progress(out, frames, samples=c.samples, res=(sc.render.resolution_x * sc.render.resolution_percentage // 100,
                                                       sc.render.resolution_y * sc.render.resolution_percentage // 100))
for f in frames:
    prog.frame_begin(f); sc.frame_set(f); prog.stage("Rendering")
    sc.render.filepath = out + "/f_%04d.png" % f
    bpy.ops.render.render(write_still=True)
    prog.frame_end(f)
    print("[burst] rendered", f, flush=True)
prog.finish()
print("[burst] done")
