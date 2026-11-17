"""Clay (grey material) renders of the whole s02 set in a background Blender. Never saves the .blend.

Every material is swapped for one neutral clay shader (leaf cut-outs keep their alpha so the
tree stays readable), the room haze is hidden, lights and the HDRI stay as they are.

Renders:
  <out>_overview_street.png  high view of the lane, house, tree and crow
  <out>_overview_room.png    the chamber from above with the ceiling removed
  <out>_####.png             chosen frames through the shot camera

Run: [S02_CPU=1] blender.exe -b s02_legend_vNNN.blend --python scripts/s02_clay_render.py -- <out_prefix> [f1,f2,...] [percent] [samples]
"""
import os, sys, time
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
frames = [int(x) for x in argv[1].split(",")] if len(argv) > 1 and argv[1] else []
pct = int(argv[2]) if len(argv) > 2 else 50
spp = int(argv[3]) if len(argv) > 3 else 32

sc = bpy.context.scene
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "HIP"
cp.use_hiprt = False
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "HIP"
sc.cycles.device = "CPU" if os.environ.get("S02_CPU") == "1" else "GPU"
sc.cycles.samples = spp
sc.cycles.use_denoising = True
sc.render.resolution_percentage = pct

# --- clay swap -------------------------------------------------------------------------------
for m in bpy.data.materials:
    if not m.use_nodes or not m.node_tree:
        continue
    nt = m.node_tree
    outn = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if outn is None:
        continue
    alpha_src = None
    old = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if old is not None and old.inputs["Alpha"].is_linked:
        alpha_src = old.inputs["Alpha"].links[0].from_socket
    clay = nt.nodes.new("ShaderNodeBsdfPrincipled")
    clay.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1.0)
    clay.inputs["Roughness"].default_value = 0.65
    if alpha_src is not None:
        nt.links.new(alpha_src, clay.inputs["Alpha"])
    for l in list(outn.inputs["Surface"].links):
        nt.links.remove(l)
    for l in list(outn.inputs["Volume"].links):
        nt.links.remove(l)
    nt.links.new(clay.outputs["BSDF"], outn.inputs["Surface"])

for name in ("S02_RoomHaze",):
    o = bpy.data.objects.get(name)
    if o:
        o.hide_render = True


def render(path):
    t = time.time()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[clay] {os.path.basename(path)}: {time.time() - t:.1f} s", flush=True)


def look_cam(name, loc, target, lens):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 200
    o = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


# --- overviews (frame 30: crow and tree present, window light on) ------------------------------
sc.frame_set(30)
sc.camera = look_cam("CLAY_Street", (5.0, 9.4, 11.5), (-0.3, 4.6, 1.0), 22)   # above the lane, under no roof
render(f"{out}_overview_street.png")

sc.frame_set(80)
ceil = [o for o in bpy.data.objects if o.name.startswith(("S02_Ceiling", "S02_Beam_"))]
for o in ceil:
    o.hide_render = True
sc.camera = look_cam("CLAY_Room", (2.6, 2.8, 6.2), (0.6, -0.9, 0.4), 16)
render(f"{out}_overview_room.png")
for o in ceil:
    o.hide_render = False

# --- shot frames -----------------------------------------------------------------------------
sc.camera = bpy.data.objects["CAM_S02"]
for f in frames:
    sc.frame_set(f)
    render(f"{out}_{f:04d}.png")
