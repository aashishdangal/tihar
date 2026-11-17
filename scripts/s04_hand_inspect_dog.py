# Read-only: print Nubis rig bones (head/neck) and body bounds. Never saves.
import bpy
from mathutils import Vector
rig = bpy.data.objects["Nubis"]
print("RIG scale", tuple(rig.scale), "loc", tuple(rig.location), "parent", rig.parent)
for b in rig.pose.bones:
    n = b.name.lower()
    if any(k in n for k in ("head", "neck", "chest", "nose", "eye", "ear", "jaw", "spine")):
        print("BONE", b.name, "head", tuple(round(v,3) for v in rig.matrix_world @ b.head), "tail", tuple(round(v,3) for v in rig.matrix_world @ b.tail))
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, o.parent.name if o.parent else None, [m.type for m in getattr(o, "modifiers", [])])
