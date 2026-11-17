# Material inventory of an imported OBJ part: area, face count, bbox per material.
#   blender -b --factory-startup --python scripts/s04_court_matinv.py -- <in.obj> [name_prefix,...]
import bpy, sys, bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=argv[0], up_axis="Z", forward_axis="Y")
keep = argv[1].split(",") if len(argv) > 1 and argv[1] else None
stats = {}
for o in bpy.context.scene.objects:
    if o.type != "MESH" or (keep and not any(o.name.startswith(k) for k in keep)):
        continue
    me = o.data
    for p in me.polygons:
        m = me.materials[p.material_index] if me.materials else None
        k = m.name if m else "-"
        s = stats.setdefault(k, [0.0, 0, Vector((1e9,) * 3), Vector((-1e9,) * 3), m])
        s[0] += p.area; s[1] += 1
        c = o.matrix_world @ p.center
        s[2] = Vector(map(min, s[2], c)); s[3] = Vector(map(max, s[3], c))
for k, (a, n, lo, hi, m) in sorted(stats.items(), key=lambda kv: -kv[1][0]):
    col = "-"; tex = "-"
    if m and m.use_nodes:
        b = next((x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED"), None)
        if b:
            col = tuple(round(v, 2) for v in b.inputs[0].default_value[:3])
            l = b.inputs[0].links
            if l and l[0].from_node.type == "TEX_IMAGE" and l[0].from_node.image:
                tex = l[0].from_node.image.name
    print("[mat] %-34s area %8.2f faces %6d  lo %6.1f %6.1f %5.1f  hi %6.1f %6.1f %5.1f  col %s tex %s" % (
        k, a, n, lo.x, lo.y, lo.z, hi.x, hi.y, hi.z, col, tex))
