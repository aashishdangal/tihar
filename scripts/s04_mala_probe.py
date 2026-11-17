# Print the mala ring centre/radius and dog head/muzzle positions for frames 52-63 (diagnose snout clip).
import bpy
from mathutils import Vector
sc = bpy.context.scene
rig = bpy.data.objects["Nubis"]
mala = bpy.data.objects["S04_Mala"]
names = [b.name for b in rig.pose.bones if any(k in b.name.lower() for k in ("head", "nose", "muzzle", "jaw", "neck", "snout"))]
print("[p] bones", names)
dg = bpy.context.evaluated_depsgraph_get()
for f in range(52, 64):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mala.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    c = sum(pts, Vector()) / len(pts)
    r = sum((p - c).length for p in pts) / len(pts)
    bs = {n: tuple(round(x, 3) for x in (rig.matrix_world @ rig.pose.bones[n].head)) for n in names
          if any(k in n.lower() for k in ("nose", "head", "jaw"))}
    print(f"[p] f{f} c={tuple(round(x,3) for x in c)} r={r:.3f}", bs)
