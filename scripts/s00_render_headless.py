"""Headless s00 render helper (run with blender -b).

Usage:
  blender.exe -b <file.blend> --python scripts/s00_render_headless.py -- <mode> <out_dir> [frames]
    mode   : realfire | origflame
    out_dir: folder for 0001.png ... (created if missing)
    frames : optional comma list or range "1-96" (default 1-96)
  env S00_TEST=1 -> 50% resolution, 32 samples (quick look)

For mode=realfire it also adds flame movement (idempotent): the two RealFire volumes are
parented to a pivot empty at the wick tip, and the pivot gets a seamless 96-frame loop of
sway (lean left/right and forward/back) and height flicker. The flame light follows the flicker.
It also applies the option A look (brighter flame vs clay, flame size, glow, wick fade): see the
constants under "option A look".
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode, out_dir = argv[0], os.path.abspath(argv[1])
rng = argv[2] if len(argv) > 2 else "1-96"
if "-" in rng:
    a, b = map(int, rng.split("-"))
    frames = list(range(a, b + 1))
else:
    frames = [int(x) for x in rng.split(",")]
test = os.environ.get("S00_TEST") == "1"

s = bpy.context.scene
TIP = Vector((0.0475, 0.0, 0.036))
LOOP = 96


def loop_sin(f, cycles, phase=0.0):
    return math.sin(2 * math.pi * cycles * (f - 1) / LOOP + phase)


def add_flame_motion():
    piv = bpy.data.objects.get("S00_FlamePivot")
    if piv is None:
        piv = bpy.data.objects.new("S00_FlamePivot", None)
        piv.empty_display_size = 0.01
        bpy.data.objects["S00_FireVol"].users_collection[0].objects.link(piv)
        piv.location = TIP
        bpy.context.view_layer.update()
        for n in ("S00_FireVol", "S00_FireVol_B"):
            o = bpy.data.objects[n]
            mw = o.matrix_world.copy()
            o.parent = piv
            o.matrix_parent_inverse = piv.matrix_world.inverted()
            o.matrix_world = mw
    piv.location = (TIP.x, TIP.y, TIP.z + FLAME_DZ)  # volumes follow (parented)
    if piv.animation_data:
        piv.animation_data_clear()
    for f in range(1, LOOP + 2):
        # sway: up to ~9 degrees, mix of slow and quicker components; integer cycles => seamless
        rx = math.radians(5.5 * loop_sin(f, 2, 0.3) + 2.5 * loop_sin(f, 5, 1.7) + 1.0 * loop_sin(f, 11, 0.6))
        ry = math.radians(6.0 * loop_sin(f, 3, 0.9) + 3.0 * loop_sin(f, 7, 2.4) + 1.0 * loop_sin(f, 12, 1.3))
        sz = flicker(f)
        sxy = 1.0 - 0.35 * (sz - 1.0)  # taller flame gets slightly thinner
        piv.rotation_euler = (rx, ry, 0.0)
        piv.scale = (FLAME_W * sxy, FLAME_W * sxy, FLAME_H * sz)
        piv.keyframe_insert("rotation_euler", frame=f)
        piv.keyframe_insert("scale", frame=f)
    # the flame light follows the height flicker
    L = bpy.data.objects["L_S00_Flame"]
    if L.data.animation_data:
        L.data.animation_data_clear()
    for f in range(1, LOOP + 2):
        L.data.energy = LIGHT_BASE * (1.0 + 1.3 * (flicker(f) - 1.0))
        L.data.keyframe_insert("energy", frame=f)


def flicker(f):
    """Flame height multiplier, seamless over LOOP frames (about +-20%)."""
    return (1.0 + 0.10 * loop_sin(f, 4, 0.5) + 0.06 * loop_sin(f, 9, 1.1)
            + 0.04 * loop_sin(f, 13, 2.0) + 0.02 * loop_sin(f, 17, 0.8))


# option A look (absolute values, so re-running is safe). v056: flame much brighter than the
# clay; the lamps that light the clay go down and exposure goes up instead.
LIGHT_BASE = 0.6   # flame point light; v060 0.475, v055 0.95
FILL_ENERGY = 0.24  # L_S00_Fill; v055 0.6 (v061: light-linked to the diyo only)
EXPOSURE = 0.45     # AgX exposure; v060 0.8 (pink-white clay by the flame), v055 0
# v058: the RealFire volume is only the soft outer envelope now; the bright crisp core is the
# S00_FlameCore mesh (teardrop, emission, parented to the pivot; material M_S00_FlameCore).
# v064: back to the v060 flame (user preferred it over the v061-v063 slimmer flame)
FLAME_EMISSION = {"Main Emission Strength": 10.0,   # v061-063 4, v056 66
                  "Born Emission Strength": 5.0,    # v062-063 2, v056 45
                  "Death Emission Strength": 6.0}   # v061-063 3, v056 35
FLAME_COLORS = {"Main Flame Color": (1.0, 0.62, 0.20, 1.0),   # v056 (1,0.42,0.08): less pink in AgX
                "Born Flame Color": (1.0, 0.66, 0.28, 1.0),   # v060 value; v061-063 blue (0.25,0.4,1)
                "Death Flame Color": (1.0, 0.35, 0.06, 1.0)}  # v056 (1,0.2,0.02)
VOLUME_STEP_RATE = 0.3       # crisper volume edge; was 0.5
FLAME_W, FLAME_H = 1.3, 1.8  # flame size multipliers (v056 1.2, 1.6; v061-063 1.0, 2.1); core mesh scales with them
FLAME_DZ = -0.002            # flame base 2 mm lower, over the wick tip
GLARE = {"Threshold": 3.0, "Strength": 0.6, "Size": 0.8}  # glow on the flame only, not the clay
WICK_TIP_EMISSION = 15.0     # charred tip glows hot
WICK_FADE_Z = (0.034, 0.0365)  # wick fades out for camera rays between these world Z (m); v057 wick re-routed over the lip


def brighten_realfire():
    nt = bpy.data.materials["M_S00_RealFire"].node_tree
    grp = next(n for n in nt.nodes if n.type == "GROUP")
    for k, v in FLAME_EMISSION.items():
        grp.inputs[k].default_value = v
    for k, v in FLAME_COLORS.items():
        grp.inputs[k].default_value = v
    s.cycles.volume_step_rate = VOLUME_STEP_RATE
    bpy.data.objects["L_S00_Fill"].data.energy = FILL_ENERGY
    s.view_settings.exposure = EXPOSURE
    glare = s.compositing_node_group.nodes["S00_FlameGlow"]
    for k, v in GLARE.items():
        glare.inputs[k].default_value = v
    char = next(n for n in bpy.data.materials["M_S00_WickChar"].node_tree.nodes
                if n.type == "BSDF_PRINCIPLED")
    char.inputs["Emission Color"].default_value = (1.0, 0.55, 0.2, 1.0)
    char.inputs["Emission Strength"].default_value = WICK_TIP_EMISSION
    for mn in ("M_S00_Wick", "M_S00_WickChar"):
        wick_fade(bpy.data.materials[mn], *WICK_FADE_Z)


def wick_fade(mat, z0, z1):
    """Camera rays see the wick fade to transparent between z0 and z1 (shadows unchanged)."""
    nt = mat.node_tree
    mr = nt.nodes.get("S00_WickFadeRange")
    if mr is None:
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        src = out.inputs["Surface"].links[0].from_socket
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.name = "S00_WickFadeRange"
        lp = nt.nodes.new("ShaderNodeLightPath")
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], mul.inputs[0])
        nt.links.new(lp.outputs["Is Camera Ray"], mul.inputs[1])
        nt.links.new(mul.outputs[0], mix.inputs["Fac"])
        nt.links.new(src, mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    mr.inputs["From Min"].default_value = z0
    mr.inputs["From Max"].default_value = z1


# v063: the RealFire volume envelope is a straight column offset behind the core ("ghost
# column" in the render-critic report); the S00_FlameCore mesh + S00_FlameGlow glare look
# cleaner on their own. Set True to bring the envelope back.
ENVELOPE_ON = True   # v063 False; v064 back on with the v060 flame


def use_realfire(on):
    bpy.data.objects["S00_Flame"].hide_render = on
    for n in ("S00_FireVol", "S00_FireVol_B"):
        bpy.data.objects[n].hide_render = not (on and ENVELOPE_ON)


# GPU: RX 9070 XT via HIP
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP" and "9070" in d.name
s.cycles.device = "GPU"
print("[s00] devices:", [d.name for d in cp.devices if d.use])

if mode == "realfire":
    use_realfire(True)
    add_flame_motion()
    brighten_realfire()
    bpy.ops.wm.save_mainfile()
else:
    use_realfire(False)

s.render.use_border = False
s.render.use_compositing = True
s.cycles.use_denoising = True
s.cycles.samples = 32 if test else 128
s.render.resolution_percentage = 50 if test else 100
os.makedirs(out_dir, exist_ok=True)
for f in frames:
    s.frame_set(f)
    s.render.filepath = os.path.join(out_dir, f"{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[s00] {mode} frame {f} done", flush=True)
print("[s00] finished", mode)
