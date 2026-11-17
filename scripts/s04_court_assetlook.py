# Import one converted OBJ, print bounds/parts, and render a quick Workbench look (textured) from 2 sides.
#   blender -b --factory-startup --python scripts/s04_court_assetlook.py -- <in.obj> <out_prefix>
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, prefix = argv[0], argv[1]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=src, up_axis="Z", forward_axis="Y")
sc = bpy.context.scene
keep = argv[2].split(",") if len(argv) > 2 else None
if keep:
    for o in list(sc.objects):
        if not any(o.name.startswith(k) for k in keep):
            bpy.data.objects.remove(o)
box = os.environ.get("LOOK_BOX")
if box:  # keep parts whose bbox centre lies in xmin,ymin,xmax,ymax
    x0, y0, x1, y1 = map(float, box.split(","))
    for o in list(sc.objects):
        c = sum((o.matrix_world @ Vector(b) for b in o.bound_box), Vector()) / 8
        if not (x0 <= c.x <= x1 and y0 <= c.y <= y1):
            bpy.data.objects.remove(o)
objs = [o for o in sc.objects if o.type == "MESH"]
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
print("[look] bounds", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi), "size", tuple(round(v, 2) for v in hi - lo))
for o in sorted(objs, key=lambda o: -len(o.data.polygons))[:40]:
    d = o.dimensions
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector(map(min, *bb))
    print("[part] %-40s tris %7d dims %5.2f %5.2f %5.2f min %6.2f %6.2f %6.2f mats %s" % (
        o.name, len(o.data.polygons), d.x, d.y, d.z, mn.x, mn.y, mn.z, ",".join(m.name for m in o.data.materials[:6] if m)))
ctr = (lo + hi) / 2; size = (hi - lo).length
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "TEXTURE"
sh.show_shadows = True; sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 1100, 760
cam_d = bpy.data.cameras.new("C"); cam_d.lens = 35; cam_d.clip_end = 1000
cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
yaws = [float(v) for v in argv[3].split(",")] if len(argv) > 3 else [30, 210]
for i, yaw in enumerate(yaws):
    y = math.radians(yaw)
    fwd = Vector((math.sin(y), -math.cos(y), float(os.environ.get("LOOK_UP", 0.45)))).normalized()
    cam.location = ctr + fwd * size * float(os.environ.get("LOOK_DIST", 1.0))
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = "%s_%d.png" % (prefix, i)
    bpy.ops.render.render(write_still=True)
    print("[look] wrote", sc.render.filepath)
