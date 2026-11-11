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


# ---------------------------------------------------------------------------------------------
# Blow-out (the hidden cut into Scene 1): frames 101-172, after the loop (1-96), same camera.
# A gust (direction WIND_SIGN) leans the flame over, it tears and goes out (~frame 117), the
# wick tip glows as an ember, and everything fades to pure black by frame 166.
# Frame 101 = loop frame 1, so the web can crossfade from any loop frame into it.
BLOW_START = 101
# +1: the gust goes toward screen-right (v067, the shipped frames; the सुरु figure faces right).
# v068 tried -1 (toward screen-left) and was dropped.
WIND_SIGN = 1
BLOW_LEN = 72
VDB_OFFSET_LOOP = 64                      # loop frame f shows cache frame f + 64
VDB_OFFSET_BLOW = VDB_OFFSET_LOOP - (BLOW_START - 1)   # blow-out frame 101 shows the same cache frame as loop frame 1
OUT_K = 16                                # last frame (offset from BLOW_START) with any flame
# k: (lean deg, width mult, height mult, light mult, drift m downwind)
GUST = [(0, 1.0, 1.0, 1.0, 0.0), (3, 18, 0.92, 1.18, 1.25, 0.0), (6, 34, 0.80, 1.32, 1.10, 0.0005),
        (8, 28, 0.85, 1.15, 0.95, 0.0008), (10, 40, 0.70, 1.05, 0.70, 0.0012), (12, 52, 0.55, 0.75, 0.45, 0.002),
        (14, 60, 0.35, 0.45, 0.22, 0.003), (15, 64, 0.22, 0.28, 0.12, 0.004), (16, 68, 0.10, 0.12, 0.05, 0.005)]
GUST[0] = (0,) + GUST[0]                  # k=0: no lean, base size, base light
EMBER = [(17, 0.6), (24, 0.42), (36, 0.25), (50, 0.1), (60, 0.03), (65, 0.0)]  # wick tip glow gain (loop = 1)
EMBER_LIGHT = [(17, 0.03), (36, 0.012), (60, 0.0)]                           # x LIGHT_BASE
FADE_TO_BLACK_K = 65                      # world light gone; frames 166-172 are pure black
DUST_GUST = [(0, 0.0), (6, 0.02), (12, 0.07), (17, 0.15), (40, 0.6)]   # k: metres the dust cloud has moved downwind


def add_blowout():
    from mathutils import Vector as V
    piv = bpy.data.objects["S00_FlamePivot"]
    L = bpy.data.objects["L_S00_Flame"]
    fill = bpy.data.objects["L_S00_Fill"]
    cam = s.camera
    r = cam.matrix_world.col[0].xyz          # camera right in world
    r = V((r.x, r.y, 0)).normalized() * WIND_SIGN   # downwind direction
    base_loc = V((TIP.x, TIP.y, TIP.z + FLAME_DZ))

    def key_pivot(f, lean, wm, hm, drift):
        th = math.radians(lean)
        # loop pose at frame 1, plus a lean toward screen-right (Rx tips +Z toward -Y, Ry toward +X)
        rx0 = math.radians(5.5 * loop_sin(1, 2, 0.3) + 2.5 * loop_sin(1, 5, 1.7) + 1.0 * loop_sin(1, 11, 0.6))
        ry0 = math.radians(6.0 * loop_sin(1, 3, 0.9) + 3.0 * loop_sin(1, 7, 2.4) + 1.0 * loop_sin(1, 12, 1.3))
        sz = flicker(1)
        sxy = 1.0 - 0.35 * (sz - 1.0)
        piv.rotation_euler = (rx0 - th * r.y, ry0 + th * r.x, 0.0)
        piv.scale = (FLAME_W * sxy * wm, FLAME_W * sxy * wm, FLAME_H * sz * hm)
        piv.location = base_loc + r * drift
        for p in ("rotation_euler", "scale", "location"):
            piv.keyframe_insert(p, frame=f)

    # pivot location gets keys only here; key the loop range with the base so it stays put
    piv.location = base_loc
    piv.keyframe_insert("location", frame=1)
    for k, lean, wm, hm, lm, drift in GUST:
        key_pivot(BLOW_START + k, lean, wm, hm, drift)
        L.data.energy = LIGHT_BASE * (1.0 + 1.3 * (flicker(1) - 1.0)) * lm
        L.data.keyframe_insert("energy", frame=BLOW_START + k)
        fill.data.energy = FILL_ENERGY * min(lm, 1.2)
        fill.data.keyframe_insert("energy", frame=BLOW_START + k)
    f_out = BLOW_START + OUT_K + 1
    key_pivot(f_out, 70, 0.001, 0.001, 0.005)
    fill.data.energy = 0.0
    fill.data.keyframe_insert("energy", frame=f_out)
    # flame objects vanish for good at f_out
    for n in ("S00_FlameCore", "S00_FireVol", "S00_FireVol_B"):
        o = bpy.data.objects[n]
        visible_before = n == "S00_FlameCore" or ENVELOPE_ON
        o.hide_render = not visible_before
        o.keyframe_insert("hide_render", frame=1)
        o.keyframe_insert("hide_render", frame=f_out - 1)
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=f_out)
    # ember: the point light becomes a faint deep-orange glow, then nothing
    for k, m in EMBER_LIGHT:
        L.data.energy = LIGHT_BASE * m
        L.data.keyframe_insert("energy", frame=BLOW_START + k)
    L.data.color = (1.0, 0.62, 0.30)
    L.data.keyframe_insert("color", frame=f_out - 1)
    L.data.color = (1.0, 0.35, 0.08)
    L.data.keyframe_insert("color", frame=f_out)
    # wick tip: visible to the camera once the flame is gone, glowing then cooling
    # (Emission Strength is driven by the S00_Ember gradient node, so a gain node goes after it)
    char = bpy.data.materials["M_S00_WickChar"].node_tree
    bsdf = next(n for n in char.nodes if n.type == "BSDF_PRINCIPLED")
    gain = char.nodes.get("S00_EmberGain")
    if gain is None:
        src = bsdf.inputs["Emission Strength"].links[0].from_socket
        gain = char.nodes.new("ShaderNodeMath")
        gain.name = "S00_EmberGain"
        gain.operation = "MULTIPLY"
        char.links.new(src, gain.inputs[0])
        char.links.new(gain.outputs[0], bsdf.inputs["Emission Strength"])
    es = gain.inputs[1]
    es.default_value = 1.0
    es.keyframe_insert("default_value", frame=1)
    es.keyframe_insert("default_value", frame=f_out - 1)
    for k, v in EMBER:
        es.default_value = v
        es.keyframe_insert("default_value", frame=BLOW_START + k)
    es.default_value = 1.0
    for mn in ("M_S00_Wick", "M_S00_WickChar"):
        mr = bpy.data.materials[mn].node_tree.nodes["S00_WickFadeRange"]
        for sock, loop_v, out_v in (("From Min", WICK_FADE_Z[0], 0.050), ("From Max", WICK_FADE_Z[1], 0.051)):
            i = mr.inputs[sock]
            i.default_value = loop_v
            i.keyframe_insert("default_value", frame=1)
            i.keyframe_insert("default_value", frame=f_out - 1)
            i.default_value = out_v
            i.keyframe_insert("default_value", frame=f_out)
    # OneClickDust motes (s00_add_airdust.py): absent in the approved loop, brought in by the gust
    # and carried toward screen-right, accelerating; they only show while the flame lights them
    dust = bpy.data.objects.get("S00_AirDust")
    if dust is not None:
        base = V(dust["s00_base_location"])
        dust.location = base
        dust.hide_render = True
        dust.keyframe_insert("hide_render", frame=1)
        dust.hide_render = False
        dust.keyframe_insert("hide_render", frame=BLOW_START)
        for k, d in DUST_GUST:
            dust.location = base + r * d
            dust.keyframe_insert("location", frame=BLOW_START + k)
        dust.location = base
    # night ambient fades out too: pure black at the end
    bg = next(n for n in s.world.node_tree.nodes if n.type == "BACKGROUND")
    st = bg.inputs["Strength"]
    st.keyframe_insert("default_value", frame=BLOW_START + 30)
    v0 = st.default_value
    st.default_value = 0.0
    st.keyframe_insert("default_value", frame=BLOW_START + FADE_TO_BLACK_K)
    st.default_value = v0
    # step changes (hide, wick fade, colour) must not interpolate
    for idb in (piv, L.data, fill.data, char, s.world.node_tree, bpy.data.materials["M_S00_Wick"].node_tree,
                bpy.data.objects["S00_FlameCore"], bpy.data.objects["S00_FireVol"], bpy.data.objects["S00_FireVol_B"],
                *([dust] if dust is not None else [])):
        ad = idb.animation_data
        if not (ad and ad.action):
            continue
        for fc in action_fcurves(ad):
            if fc.data_path.endswith(("hide_render", "color")) or "S00_WickFadeRange" in fc.data_path:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


def action_fcurves(ad):
    """F-curves of an ID's action (Blender 5 layered actions, or legacy .fcurves)."""
    act = ad.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            bag = strip.channelbag(ad.action_slot)
            if bag:
                out.extend(bag.fcurves)
    return out


def clear_blowout_keys():
    """Make add_blowout idempotent: drop keys it owns (loop keys are rebuilt by add_flame_motion)."""
    if bpy.data.objects.get("S00_AirDust"):
        bpy.data.objects["S00_AirDust"].animation_data_clear()
    for idb in (bpy.data.objects["L_S00_Fill"].data, bpy.data.materials["M_S00_WickChar"].node_tree,
                bpy.data.materials["M_S00_Wick"].node_tree, s.world.node_tree,
                bpy.data.objects["S00_FlameCore"], bpy.data.objects["S00_FireVol"], bpy.data.objects["S00_FireVol_B"]):
        idb.animation_data_clear()
    bpy.data.objects["L_S00_Fill"].data.energy = FILL_ENERGY
    next(n for n in s.world.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.004


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
    clear_blowout_keys()
    add_flame_motion()
    brighten_realfire()
    add_blowout()
    bpy.ops.wm.save_mainfile()
else:
    use_realfire(False)

s.render.use_border = False
s.render.use_compositing = True
s.cycles.use_denoising = True
s.cycles.samples = 32 if test else 128
s.render.resolution_percentage = 50 if test else 100
os.makedirs(out_dir, exist_ok=True)
vdb = bpy.data.objects["S00_FireVol"].data
for f in frames:
    # the fire cache plays the loop's stretch again for the blow-out (frame 101 = loop frame 1)
    vdb.frame_offset = VDB_OFFSET_BLOW if f >= BLOW_START else VDB_OFFSET_LOOP
    s.frame_set(f)
    s.render.filepath = os.path.join(out_dir, f"{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[s00] {mode} frame {f} done", flush=True)
print("[s00] finished", mode)
