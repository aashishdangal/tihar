"""Masks for the hybrid finale (owner 2026-11-21): which pixels of the full still
(renders/s08_finale/still4/full/f_0036.png) are tree, kite and grass, so the browser can cut them out
and sway them over the clean still (renders/s08_finale/still3/clean/f_0036.png).

One pass per layer, frame 36 like the stills: that layer visible with a flat white override, every other
visible object a HOLDOUT (so what stands in front of the layer still cuts it), haze off, transparent film.
The alpha channel is the anti-aliased coverage. Writes renders/s08_finale/masks/{tree,kite,grass}.png.

  blender.exe -b blender/scenes/s08_finale_v073.blend --python scripts/s08_mask_render.py
Live progress: python scripts/render_watch.py renders/s08_finale/masks
"""
import os
import sys

import bpy

ROOT = r"E:/Projects/tihar"
sys.path.insert(0, ROOT + "/scripts")
import render_progress_hook as rp  # noqa: E402

LAYERS = {
    "tree": ["S08_Tree"],
    "kite": ["S08_KitePaper", "S08_KiteSpine", "S08_KiteBow", "S08_KiteString"],
    "grass": ["S08_GrassFG"],
}
EMPTIES = ["S08_KiteFollow", "S08_KitePivot"]          # parents of the kite, must be on for its motion
# hill we stand on + front ridge (with its grass) + hill road: the browser draws the fireworks BEHIND
# them (owner 2026-11-21: "the firework should start behind the hill and our tree, nepali flag and kite")
HILL = ["S08_Hill", "S08_FrontRidge", "S08_HillRoad"]
if os.environ.get("S08_MASKS") == "hill":
    LAYERS = {"hill": HILL}

sc = bpy.context.scene
grass_src = set(o.name for o in bpy.data.collections["S08_GrassSrc"].objects)   # instanced by the grass
fg = set(n for v in LAYERS.values() for n in v)
for n in fg | set(EMPTIES):
    bpy.data.objects[n].hide_render = False
haze = bpy.data.objects.get("S08_HazeLayer")
if haze:
    haze.hide_render = True

wm = bpy.data.materials.new("M_MaskWhite"); wm.use_nodes = True
nt = wm.node_tree; nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs["Surface"])
bpy.context.view_layer.material_override = wm

prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "HIP"; prefs.get_devices()
for dv in prefs.devices:
    dv.use = dv.type == "HIP" and "9070" in dv.name
c = sc.cycles
c.device = "GPU"; c.samples = 48; c.use_adaptive_sampling = False; c.use_denoising = False
c.max_bounces = 0; c.transparent_max_bounces = 16
sc.render.film_transparent = True; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.frame_set(36)

outdir = ROOT + "/renders/s08_finale/masks"
os.makedirs(outdir, exist_ok=True)
order = list(LAYERS)
prog = rp.Progress(outdir, list(range(1, len(order) + 1)), samples=c.samples, res=(sc.render.resolution_x, sc.render.resolution_y))
# Only what can stand IN FRONT of a layer matters for its mask: the other layers and the ground.
# Everything else (city, valley, mountains: millions of instances) is switched off - with it in the
# scene as holdouts the first attempt ran out of memory.
OCCLUDERS = ["S08_Hill", "S08_FrontRidge", "S08_HillRoad"]
keep = fg | set(EMPTIES) | set(OCCLUDERS) | grass_src
for o in bpy.data.objects:
    if o.type == "CAMERA":
        continue
    if o.name not in keep:
        o.hide_render = True
for i, name in enumerate(order, 1):
    for o in bpy.data.objects:
        if o.name in grass_src or o.type in ("LIGHT", "CAMERA", "EMPTY"):
            continue
        o.is_holdout = o.name not in LAYERS[name]
    prog.frame_begin(i); prog.stage("Rendering mask " + name)
    sc.render.filepath = outdir + "/" + name + ".png"
    bpy.ops.render.render(write_still=True)
    prog.frame_end(i)
    print("[mask] rendered", name, flush=True)
prog.finish()
print("[mask] done")
