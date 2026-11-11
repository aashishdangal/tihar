"""One-off: add the blow-out smoke wisp to s00 (v066 -> v067) and bake it.

Run: blender.exe -b s00_enter_v066_realfire.blend --python scripts/s00_add_smoke.py -- <out.blend> [resolution]

Mantaflow gas sim over the blow-out frames only (101-172): a 1.5 mm emitter at the wick tip
releases smoke when the flame dies (frame ~117) and fades by ~150; a wind field pushes it toward
screen-right (strong during the gust, then a drift). The ember barely lights anything, so a faint
cool backlight, light-linked to the smoke only, makes the wisp readable; it fades with the scene.
Cache: //cache/s00_smoke (git-ignored).
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
RES = int(argv[1]) if len(argv) > 1 else 128

s = bpy.context.scene
TIP = Vector((0.0475, 0.0, 0.0366))
F0, F1 = 101, 172          # blow-out range
F_OUT = 118                # first frame without flame (s00_render_headless.py: BLOW_START + OUT_K + 1)
coll = bpy.data.collections.get("FX") or s.collection

cam = s.camera
r = cam.matrix_world.col[0].xyz
r = Vector((r.x, r.y, 0)).normalized()          # screen-right in world (downwind)


def get_or_new_mesh_obj(name, make):
    o = bpy.data.objects.get(name)
    if o is None:
        o = make()
        o.name = name
        if o.name not in coll.objects:
            for c in o.users_collection:
                c.objects.unlink(o)
            coll.objects.link(o)
    return o


def new_cube():
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    return bpy.context.active_object


def new_sphere():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=16, ring_count=8)
    return bpy.context.active_object


# --- domain: box from the wick, up and downwind
dom = get_or_new_mesh_obj("S00_SmokeDomain", new_cube)
centre = TIP + r * 0.035 + Vector((0, 0, 0.075))
dom.location = centre
dom.rotation_euler = (0, 0, math.atan2(r.y, r.x))     # box's X along the wind
dom.scale = (0.14, 0.12, 0.17)
dom.display_type = "WIRE"
md = dom.modifiers.get("Fluid") or dom.modifiers.new("Fluid", "FLUID")
md.fluid_type = "DOMAIN"
d = md.domain_settings
d.domain_type = "GAS"
d.resolution_max = RES
d.cache_directory = "//cache/s00_smoke"
d.cache_type = "ALL"
d.cache_frame_start = F0
d.cache_frame_end = F1
d.use_adaptive_domain = False
d.alpha = 0.6              # smoke rises (density buoyancy)
d.beta = 1.2               # heat buoyancy
d.vorticity = 0.35         # small curls
d.use_dissolve_smoke = True
d.dissolve_speed = 45
d.use_dissolve_smoke_log = True
d.time_scale = 1.0

# volume material: thin grey-blue smoke
mat = bpy.data.materials.get("M_S00_Smoke") or bpy.data.materials.new("M_S00_Smoke")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
outn = nt.nodes.new("ShaderNodeOutputMaterial")
vol = nt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1.0)
vol.inputs["Density"].default_value = 10.0
vol.inputs["Anisotropy"].default_value = 0.45      # forward scattering: glows when backlit
nt.links.new(vol.outputs["Volume"], outn.inputs["Volume"])
dom.data.materials.clear()
dom.data.materials.append(mat)

# --- emitter at the wick tip, density keyed: nothing until the flame dies
em = get_or_new_mesh_obj("S00_SmokeEmitter", new_sphere)
em.location = TIP + Vector((0, 0, 0.001))
em.scale = (0.0015, 0.0015, 0.0015)
em.hide_render = True
mf = em.modifiers.get("Fluid") or em.modifiers.new("Fluid", "FLUID")
mf.fluid_type = "FLOW"
f = mf.flow_settings
f.flow_type = "SMOKE"
f.flow_behavior = "INFLOW"
f.flow_source = "MESH"
f.surface_distance = 1.5
f.subframes = 2
f.smoke_color = (0.7, 0.72, 0.75)
f.temperature = 1.2
f.use_initial_velocity = True
f.velocity_coord = (0.0, 0.0, 0.05)
if em.animation_data:
    em.animation_data_clear()
for frame, dens in ((F0, 0.0), (F_OUT - 1, 0.0), (F_OUT, 1.0), (F_OUT + 10, 0.8), (F_OUT + 22, 0.35), (F_OUT + 34, 0.0)):
    f.density = dens
    f.keyframe_insert("density", frame=frame)

# --- wind toward screen-right: strong in the gust, then a gentle drift
wind = bpy.data.objects.get("S00_Wind")
if wind is None:
    wind = bpy.data.objects.new("S00_Wind", None)
    coll.objects.link(wind)
wind.location = TIP - r * 0.08
wind.rotation_euler = Vector((0, 0, 1)).rotation_difference((r + Vector((0, 0, 0.15))).normalized()).to_euler()
if wind.field is None or wind.field.type != "WIND":
    with bpy.context.temp_override(object=wind, active_object=wind, selected_objects=[wind]):
        bpy.ops.object.forcefield_toggle()
    wind.field.type = "WIND"
wind.field.flow = 0.0
wind.field.noise = 0.4
if wind.animation_data:
    wind.animation_data_clear()
for frame, st in ((F0, 0.0), (F0 + 4, 1.6), (F_OUT, 1.2), (F_OUT + 12, 0.35), (F1, 0.2)):
    wind.field.strength = st
    wind.field.keyframe_insert("strength", frame=frame)

# --- faint cool backlight on the smoke only, fades with the scene
rim = bpy.data.objects.get("L_S00_SmokeRim")
if rim is None:
    ld = bpy.data.lights.new("L_S00_SmokeRim", "AREA")
    rim = bpy.data.objects.new("L_S00_SmokeRim", ld)
    coll.objects.link(rim)
view = (centre - cam.matrix_world.translation).normalized()
rim.location = centre + view * 0.25 + Vector((0, 0, 0.06))
rim.rotation_euler = (centre - rim.location).to_track_quat("-Z", "Y").to_euler()
rim.data.size = 0.12
rim.data.color = (0.75, 0.82, 1.0)
lc = bpy.data.collections.get("LL_S00_SmokeOnly") or bpy.data.collections.new("LL_S00_SmokeOnly")
if dom.name not in lc.objects:
    lc.objects.link(dom)
rim.light_linking.receiver_collection = lc
if rim.data.animation_data:
    rim.data.animation_data_clear()
for frame, e in ((F0, 0.0), (F_OUT - 1, 0.0), (F_OUT + 4, RIM_W := 0.8), (F_OUT + 30, RIM_W), (F1 - 8, 0.0)):
    rim.data.energy = e
    rim.data.keyframe_insert("energy", frame=frame)

# domain renders only in the blow-out
if dom.animation_data:
    dom.animation_data_clear()
dom.hide_render = True
dom.keyframe_insert("hide_render", frame=1)
dom.hide_render = False
dom.keyframe_insert("hide_render", frame=F0)
for o in (dom,):
    for fc in o.animation_data.action.layers[0].strips[0].channelbag(o.animation_data.action_slot).fcurves \
            if not hasattr(o.animation_data.action, "fcurves") else o.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"

print("[smoke] domain", tuple(round(v, 3) for v in dom.location), "res", RES, "wind dir", tuple(round(v, 2) for v in r))
bpy.ops.wm.save_as_mainfile(filepath=out)

# --- bake
s.frame_set(F0)
with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom], scene=s):
    res = bpy.ops.fluid.bake_all()
print("[smoke] bake", res)
bpy.ops.wm.save_mainfile()
print("[smoke] saved", out)
