# Import Poly Haven glTF props side by side, print dims, Workbench contact render.
#   blender -b --factory-startup --python scripts/s04_court_proplook.py -- <out.png> <gltf> [<gltf> ...]
import bpy, sys, os
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
out, srcs = argv[0], argv[1:]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
x = 0.0
for s in srcs:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=s)
    new = [o for o in bpy.data.objects if o not in before]
    lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
    bpy.context.view_layer.update()
    for o in new:
        if o.type == "MESH":
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    d = hi - lo
    print("[prop] %-28s dims %.2f %.2f %.2f objs %d" % (os.path.basename(s), d.x, d.y, d.z, len(new)))
    for o in new:
        if o.parent is None: o.location.x += x - lo.x
    x += d.x + 0.3
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.color_type = "TEXTURE"; sc.display.shading.show_shadows = True
sc.render.resolution_x, sc.render.resolution_y = 1800, 500
cd = bpy.data.cameras.new("C"); cd.type = "ORTHO"; cd.ortho_scale = x
cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (x / 2, -20, 0.8); cam.rotation_euler = (1.5708, 0, 0)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
