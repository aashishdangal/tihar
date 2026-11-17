"""Clay (Workbench) preview of a scene's camera move. No textures, fog or Cycles.
Never saves the .blend.

Run: blender.exe -b <file.blend> --python scripts/s01_camcheck.py -- <probe|full> <out_dir> [res_x res_y] [hide_substrings,comma,sep] [color]
  probe: print the object list and render frames start / middle / end
  full:  render every frame to <out_dir>/####.png
  color: coloured clay, one flat colour per element (picked from the v027 full render, lifted so it
         reads in clay), and the city light points enlarged so they show as dots
"""
import sys, os, bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
colored = "color" in argv
argv = [a for a in argv if a != "color"]

# name substring -> RGB. First match wins.
PALETTE = [
    ("DarkCloud", (0.05, 0.05, 0.07)),   # dark cloud: near-black charcoal
    ("Himalaya", (0.88, 0.90, 0.95)),    # snow peaks on the horizon
    ("Hills", (0.16, 0.36, 0.14)),       # forested hills around the valley
    ("PTerrain", (0.36, 0.30, 0.22)),    # valley floor, fields and town
    ("LightPoints", (1.00, 0.85, 0.30)), # city lights (warm gold; multicolour in the real render)
    ("Pagoda", (0.55, 0.18, 0.10)),      # brick and timber
    ("House", (0.60, 0.30, 0.18)),
]
SKY = (0.06, 0.08, 0.16)  # night navy
mode = argv[0] if argv else "probe"
out_dir = os.path.abspath(argv[1] if len(argv) > 1 else "renders/s01_hero/camcheck")
rx = int(argv[2]) if len(argv) > 2 else 1280
ry = int(argv[3]) if len(argv) > 3 else 720
hide_subs = [s.lower() for s in argv[4].split(",") if s] if len(argv) > 4 else []

sc = bpy.context.scene
print(f"[camcheck] scene={sc.name} frames={sc.frame_start}-{sc.frame_end} camera={sc.camera.name if sc.camera else None}")


def volume_only(ob):
    """True if every material on the object only drives Volume (fog boxes)."""
    mats = [s.material for s in getattr(ob, "material_slots", []) if s.material and s.material.use_nodes]
    if not mats:
        return False
    for m in mats:
        out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None:
            return False
        surf = out.inputs[0].is_linked
        vol = out.inputs[1].is_linked
        if surf or not vol:
            return False
    return True


hidden = []
for ob in sc.objects:
    if ob.hide_render:
        continue
    reason = None
    if ob.type == "VOLUME":
        reason = "volume object"
    elif ob.type == "MESH" and volume_only(ob):
        reason = "volume-only material"
    elif any(s in ob.name.lower() for s in hide_subs):
        reason = "name match"
    if reason:
        ob.hide_render = True
        hidden.append((ob.name, reason))

if mode == "probe":
    for ob in sorted(sc.objects, key=lambda o: o.name):
        if ob.hide_render:
            continue
        dims = tuple(round(d, 1) for d in ob.dimensions)
        mods = ",".join(m.type for m in getattr(ob, "modifiers", []))
        print(f"[obj] {ob.name:40s} {ob.type:8s} dims={dims} mods={mods}")
for n, r in hidden:
    print(f"[hidden] {n} ({r})")

# Workbench clay look
try:
    sc.render.engine = "BLENDER_WORKBENCH"
except TypeError as e:
    print("[camcheck] engine error:", e)
    raise
sh = sc.display.shading
sh.light = "STUDIO"
# per-object colour: blockouts keep their own colour (the cloud is black), everything else is clay grey
sh.color_type = "OBJECT"
for ob in sc.objects:
    if colored:
        rgb = next((c for k, c in PALETTE if k in ob.name), (0.7, 0.7, 0.7))
        ob.color = (*rgb, 1.0)
    elif "Blockout" not in ob.name or tuple(ob.color) == (1.0, 1.0, 1.0, 1.0):
        ob.color = (0.8, 0.8, 0.78, 1.0)
if colored:
    # Light points are ~1 m point-cloud spheres: sub-pixel from 15 km, and Workbench draws point
    # clouds at this world scale as streaks. For the preview only, instance a low-poly mesh sphere on
    # every point (Workbench draws meshes correctly) and enlarge it.
    LIGHT_SCALE = 20
    ng = bpy.data.node_groups.get("GN_S01_LightPoints")
    if ng:
        nd = {n.bl_idname: n for n in ng.nodes}
        m2p, setm, isw = nd["GeometryNodeMeshToPoints"], nd["GeometryNodeSetMaterial"], nd["GeometryNodeIndexSwitch"]
        ico = ng.nodes.new("GeometryNodeMeshIcoSphere")
        ico.inputs["Radius"].default_value = 1.0
        ico.inputs["Subdivisions"].default_value = 1
        mul = ng.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = LIGHT_SCALE
        iop = ng.nodes.new("GeometryNodeInstanceOnPoints")
        ng.links.new(isw.outputs[0], mul.inputs[0])
        ng.links.new(m2p.outputs[0], iop.inputs["Points"])
        ng.links.new(ico.outputs["Mesh"], iop.inputs["Instance"])
        ng.links.new(mul.outputs[0], iop.inputs["Scale"])
        ng.links.new(iop.outputs["Instances"], setm.inputs["Geometry"])
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_shadows = False
sh.show_object_outline = False
sc.display.render_aa = "8"
# drop the fade-from-black (scene exposure keys) so every frame is readable
if sc.animation_data:
    sc.animation_data_clear()
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = 0.0
print(f"[camcheck] fps={sc.render.fps / sc.render.fps_base:.3f}")
if sc.world:
    sc.world.color = SKY if colored else (0.22, 0.27, 0.36)  # grey clay: light enough that a black cloud reads

r = sc.render
r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.use_compositing = False
r.use_sequencer = False
# burn the frame number into the corner
r.use_stamp = True
for attr in dir(r):
    if attr.startswith("use_stamp_") and attr not in ("use_stamp_labels",):
        try:
            setattr(r, attr, attr in ("use_stamp_frame", "use_stamp_camera"))
        except Exception:
            pass
r.stamp_font_size = 22

os.makedirs(out_dir, exist_ok=True)
if mode.startswith("frames="):  # e.g. frames=130,162
    for f in (int(x) for x in mode[7:].split(",")):
        sc.frame_set(f)
        r.filepath = os.path.join(out_dir, f"{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[camcheck] wrote {r.filepath}")
elif mode == "probe":
    mid = (sc.frame_start + sc.frame_end) // 2
    for f in (sc.frame_start, mid, sc.frame_end):
        sc.frame_set(f)
        r.filepath = os.path.join(out_dir, f"probe_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[camcheck] wrote {r.filepath}")
else:
    r.filepath = os.path.join(out_dir, "")
    bpy.ops.render.render(animation=True)
    print("[camcheck] done")
