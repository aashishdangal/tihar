"""s08 pass 3 (owner, 2026-11-20: "fix the sky, foothills peaks and flag and make the light for
overall viewable city same as near building lights also for performance ..."), following the
render-critic report renders/s08_finale/test/v065/compare/g_0080_vs_ref.md.

Run headless on the previous save, it writes the next one:
  blender.exe -b s08_finale_v065.blend --python scripts/s08_pass3.py -- s08_finale_v066.blend
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "s08_upgrade.py"), encoding="utf-8").read().rsplit("\nrun()", 1)[0]
exec(src)                                            # helpers + mat_far_building etc.


def sky():
    """North at dusk: blue-grey overhead, a low peach band at the horizon (refs 1-3), not flat lilac."""
    w = bpy.context.scene.world; t = NT(w.node_tree)
    if any(n.label == "S08_SkyGrad" for n in t.N):
        return
    pink = t.N["S08_PinkTint"]; pink.inputs[7].default_value = (1.0, 0.95, 0.97, 1.0)
    bg = t.N["Background"]
    tc = t.N["Texture Coordinate.001"]
    z = t.sep(t.vmath("NORMALIZE", tc.outputs["Generated"]))[2]
    f = t.node("ShaderNodeMapRange", label="S08_SkyGrad", in_0=z, in_1=0.01, in_2=0.1, in_3=0.0, in_4=1.0).outputs[0]
    grad = t.mix(f, (1.0, 0.8, 0.7, 1.0), (0.5, 0.64, 0.95, 1.0))
    out = t.mix(1.0, pink.outputs[2], grad, "MULTIPLY")
    t.L.new(out, bg.inputs["Color"])


def foothills():
    """Dark forest green-blue silhouettes; the sun has set for everything below the snow."""
    sun = bpy.data.objects["S08_L_Sun"]
    sun.hide_render = True; sun.hide_viewport = True
    m = bpy.data.materials["M_S01_Hills"]; t = NT(m.node_tree)
    if not any(n.label == "S08_Forest" for n in t.N):
        bs = next(n for n in t.N if n.type == "BSDF_PRINCIPLED" and n.name == "Principled BSDF")
        mixn = t.N["Mix.001"]
        out = t.mix(1.0, mixn.outputs[2], (0.42, 0.6, 0.5, 1.0), "MULTIPLY")
        out.node.label = "S08_Forest"
        t.L.new(out, bs.inputs["Base Color"])
    t.N["Hue/Saturation/Value"].inputs["Saturation"].default_value = 0.6
    t.N["Hue/Saturation/Value"].inputs["Value"].default_value = 0.6


def peaks():
    """Pink from the light (sunlit faces) with cooler shade faces: less glow, stronger low sun."""
    L = bpy.data.objects["S08_L_Alpenglow"]
    L.data.color = (1.0, 0.45, 0.35); L.data.energy = 260.0
    m = bpy.data.materials["M_S01_Himalaya"]; t = m.node_tree
    mr = next(n for n in t.nodes if n.label == "S08_Alpenglow")
    k = next(l.to_node for l in t.links if l.from_node == mr and l.to_node.type == "MATH")
    em = next(l.to_node for l in t.links if l.from_node == k and l.to_node.type == "MATH")
    em.inputs[1].default_value = 0.35
    mx = next(l.to_node for l in t.links if l.from_node == mr and l.to_node.type == "MIX")
    mx.inputs[7].default_value = (1.0, 0.55, 0.42, 1.0)   # gentler tint, the light does the rest


def flag():
    m = bpy.data.materials["M_S08_Flag"]; t = m.node_tree
    hsv = next(n for n in t.nodes if n.type == "HUE_SAT")
    hsv.inputs["Saturation"].default_value = 0.75; hsv.inputs["Value"].default_value = 0.55
    bs = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Transmission Weight"].default_value = 0.12          # backlit cotton
    pm = bpy.data.materials["M_S08_Pole"]
    pb = next(n for n in pm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    pb.inputs["Base Color"].default_value = (0.05, 0.05, 0.055, 1.0)
    pb.inputs["Metallic"].default_value = 0.6; pb.inputs["Roughness"].default_value = 0.5
    # more wind + gusts -> moving folds instead of a flat sheet
    bpy.data.objects["S08_Wind"].field.strength = 600.0
    bpy.data.objects["S08_Gusts"].field.strength = 220.0
    f = bpy.data.objects["S08_Flag"]
    cm = next(x for x in f.modifiers if x.type == "CLOTH")
    cm.settings.bending_stiffness = 0.02
    with bpy.context.temp_override(point_cache=cm.point_cache, active_object=f, object=f):
        bpy.ops.ptcache.free_bake()
        bpy.ops.ptcache.bake(bake=True)


def performance():
    """Cheap wins that change nothing on screen."""
    sc = bpy.context.scene
    sc.cycles.texture_limit_render = "1024"      # City Generator packs 1.4 GB of 2-4k textures
    sc.render.use_persistent_data = True
    # Full HD ran out of GPU memory in one piece; 512 px tiles render it in ~144 s at 128 spp
    sc.cycles.use_auto_tile = True; sc.cycles.tile_size = 512
    sc.cycles.adaptive_threshold = 0.02
    # cull far boxes outside a 34 deg half-cone (frame half-width is 21.8 deg) - camera is static
    ng = bpy.data.node_groups["GN_S08_Buildings"]; g = NT(ng)
    dl = g.N["S08_Delete"]
    if not any(n.label == "S08_Cull" for n in g.N):
        old = next(l for l in g.L if l.to_socket == dl.inputs["Selection"]).from_socket
        pos = g.node("GeometryNodeInputPosition"); s = g.sep(pos.outputs[0])
        dx = g.math("SUBTRACT", s[0], CX); dy = g.math("SUBTRACT", s[1], CY)
        out = g.math("GREATER_THAN", g.math("ABSOLUTE", dx), g.math("MULTIPLY", dy, math.tan(math.radians(34))))
        out.node.label = "S08_Cull"
        g.set(dl.inputs["Selection"], g.math("MAXIMUM", old, out))


sky(); foothills(); peaks(); mat_far_building(); flag(); performance()
out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(bpy.data.filepath), out))
print("[s08p3] saved", bpy.data.filepath)
