"""One-off: v060 -> v061 (render-critic fixes 1 and 2, scene part).

Run: blender.exe -b s00_enter_v060_realfire.blend --python scripts/s00_fix_v061.py -- <out.blend>
Fix 1: fill light lights only the diyo/oil/wick (not the ground); faint cool world light;
       darker, textured ground (procedural, no downloaded asset).
Flame: v064 keeps the v060 flame (volume width, core curves); the v061-v063 flame changes were
       undone at the user's request. Emission/size/exposure live in s00_render_headless.py.
"""
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
O = bpy.data.objects

# --- fix 1a: light-link the fill to the diyo only
coll = bpy.data.collections.get("LL_S00_FillDiyo") or bpy.data.collections.new("LL_S00_FillDiyo")
for n in ("S00_DiyoScan_Mesh", "S00_Oil", "S00_Wick", "S00_WickTip"):
    if O[n].name not in coll.objects:
        coll.objects.link(O[n])
O["L_S00_Fill"].light_linking.receiver_collection = coll
print("[fix] fill receivers:", [o.name for o in coll.objects])

# --- fix 1b: faint cool world light (ground is all the camera sees, so it only lights)
w = bpy.context.scene.world
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.6, 0.7, 1.0, 1.0)
bg.inputs["Strength"].default_value = 0.004
print("[fix] world cool 0.004")

# --- fix 1c: dark textured ground (packed earth / stone), albedo ~0.05-0.14
m = O["S00_Ground"].active_material
nt = m.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
if "S00_GroundNoise" not in nt.nodes:
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.name = "S00_GroundNoise"
    noise.inputs["Scale"].default_value = 60.0     # ground plane is 6 m: ~1.7 cm blotches
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.6
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.name = "S00_GroundRamp"
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.045, 0.032, 0.024, 1.0)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.13, 0.09, 0.065, 1.0)
    fine = nt.nodes.new("ShaderNodeTexNoise"); fine.name = "S00_GroundGrit"
    fine.inputs["Scale"].default_value = 900.0     # ~1 mm grit
    fine.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.001
    L = nt.links.new
    L(tc.outputs["Object"], noise.inputs["Vector"])
    L(tc.outputs["Object"], fine.inputs["Vector"])
    L(noise.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    L(fine.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], bsdf.inputs["Normal"])
ramp = nt.nodes["S00_GroundRamp"].color_ramp   # absolute, so re-running is safe
ramp.elements[0].color = (0.026, 0.019, 0.015, 1.0)   # first pass 0.045/0.032/0.024: title area too bright
ramp.elements[1].color = (0.075, 0.053, 0.04, 1.0)    # first pass 0.13/0.09/0.065
bsdf.inputs["Roughness"].default_value = 0.8
print("[fix] ground textured")

# --- fix 2: narrower RealFire envelope, scaled about the flame axis (pivot origin)
K = 1.0   # v064: v060 width again (user preferred the v060 flame; v061 0.75, v062-063 0.6)
for n in ("S00_FireVol", "S00_FireVol_B"):
    o = O[n]
    f = K / o.get("s00_xy_narrowed", 1.0)   # relative step, so re-running is safe
    o.scale.x *= f; o.scale.y *= f
    o.location.x *= f; o.location.y *= f
    o["s00_xy_narrowed"] = K
print("[fix] fire volumes XY x", K)

# flame core curves: v064 back to the v060 values (the v062-063 "visible blue base" edit is undone)
def set_curve(node, pts):
    mp = node.mapping
    c = mp.curves[0]
    while len(c.points) > len(pts):
        c.points.remove(c.points[-1])
    while len(c.points) < len(pts):
        c.points.new(0.5, 0.5)
    for p, (x, y) in zip(c.points, pts):
        p.location = (x, y)
    mp.update()
cnt0 = bpy.data.materials["M_S00_FlameCore"].node_tree
set_curve(cnt0.nodes["S00_CoreAlphaH"], [(0.0, 0.15), (0.2, 0.9), (0.7, 0.9), (1.0, 0.0)])   # v064 = v060; v062-063 base 0.6
set_curve(cnt0.nodes["S00_CoreStrength"], [(0.0, 0.05), (0.15, 0.25), (0.3, 1.0), (0.6, 0.85), (0.85, 0.45), (1.0, 0.15)])   # v064 = v060

# report the flame-core curves (blue base check)
cnt = bpy.data.materials["M_S00_FlameCore"].node_tree
for nn in ("S00_CoreStrength", "S00_CoreAlphaH"):
    c = cnt.nodes[nn].mapping.curves[0]
    print("[fix]", nn, [(round(p.location.x, 3), round(p.location.y, 3)) for p in c.points])
print("[fix] CoreGain", [round(i.default_value, 3) for i in cnt.nodes["S00_CoreGain"].inputs if not i.is_linked], cnt.nodes["S00_CoreGain"].operation)

bpy.ops.wm.save_as_mainfile(filepath=out)
print("[fix] saved", out)
