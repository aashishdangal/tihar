"""s01 v029 camera retime: 0.5 s sky hold, tilt to the valley, valley hold, then (placeholder)
slow push while the dark cloud rolls in. Saves to a new numbered file; the input is untouched.

Run: blender.exe -b s01_hero_v028.blend --python scripts/s01_retime_v029.py -- <out.blend>

Timeline (24 fps, 162 frames):
  1-12    sky hold (fade in from black: exposure -14 -> -4 -> 0.8)
  12-66   tilt down to the valley (same 54-frame speed as v028)
  66-114  valley hold, slight drift (PAUSE at 90)
  114-162 cloud rolls in and fills the frame (camera keeps a slow push)
"""
import sys, bpy

out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene
cam = bpy.data.objects["CAM_S01"]


def fcurves(idb):
    act = idb.animation_data.action
    if getattr(act, "fcurves", None):
        return list(act.fcurves)
    res = []
    for layer in act.layers:
        for st in layer.strips:
            for cb in st.channelbags:
                res.extend(cb.fcurves)
    return res


def rekey(idb, path, index, keys):
    fc = next(f for f in fcurves(idb) if f.data_path == path and f.array_index == index)
    fc.keyframe_points.clear()
    for fr, v in keys:
        kp = fc.keyframe_points.insert(fr, v)
        kp.interpolation = "BEZIER"
        kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    fc.update()


# camera: (frame, loc x, loc y, loc z, rot x, rot z)
K = [
    (1, 1500, -16500, 5200, 1.955, -0.052),
    (12, 1500, -16500, 5200, 1.955, -0.052),
    (66, 1500, -16500, 5200, 1.440, -0.052),
    (114, 1500, -16300, 5150, 1.440, -0.052),
    (162, 1500, -15900, 5050, 1.420, -0.045),
]
for i, col in ((0, 1), (1, 2), (2, 3)):
    rekey(cam, "location", i, [(k[0], k[col]) for k in K])
rekey(cam, "rotation_euler", 0, [(k[0], k[4]) for k in K])
rekey(cam, "rotation_euler", 1, [(k[0], 0.0) for k in K])
rekey(cam, "rotation_euler", 2, [(k[0], k[5]) for k in K])

# fade in from black over the shortened sky hold
rekey(sc, "view_settings.exposure", 0, [(1, -14.0), (3, -4.0), (12, 0.8)])

sc.frame_start, sc.frame_end = 1, 162
for m in sc.timeline_markers:
    if m.name == "PAUSE":
        m.frame = 90

bpy.ops.wm.save_as_mainfile(filepath=out, copy=False)
print("[retime] saved", out)
