# Fix teeth clipping through the tongue (frames ~84-90): while the dog is calm for the tika the
# mouth is nearly shut, so the tongue must be tucked in; it slides out only after the mouth reopens.
# blender.exe -b s04_kukur_v013.blend --python scripts/s04_fix_tongue.py -- <out.blend>
import bpy, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
rig = bpy.data.objects["Nubis"]
P = 'CTRLTongueHangingOut'
act = rig.animation_data.action
fcs = list(act.fcurves) if hasattr(act, "fcurves") else [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
fc = next(f for f in fcs if f.data_path == f'["{P}"]')
while True:
    ks = [k for k in fc.keyframe_points if 60 < k.co.x < 125]
    if not ks:
        break
    fc.keyframe_points.remove(ks[0])
for f, v in ((64, 0.44), (68, 0.0), (88, 0.0), (96, 0.48)):
    fc.keyframe_points.insert(f, v)
fc.update()
print("[fix] tongue keys", [(round(k.co.x), round(k.co.y, 2)) for k in fc.keyframe_points])
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[0]))
print("[fix] saved", argv[0])
