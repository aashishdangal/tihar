# s06 camera: from behind the Deusi group (their backs only), through the gap at x~0,
# then pitch down to a centred top-down view of the thali (frame 72 = s07's opening size).
import bpy, math
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 72
cam = bpy.data.objects["CAM_S06"]
cam.animation_data_clear()
cam.data.lens = 28
cam.data.clip_start = 0.02
cam.rotation_mode = "XYZ"
KEYS = [  # frame, location, pitch (deg, 90 = level, 0 = straight down), yaw (deg)
    (1,  (0.25, -5.0, 1.45), 82, 3),
    (40, (0.05, -2.3, 1.35), 76, 0),
    (52, (0.02, -1.3, 1.22), 58, 0),
    (62, (0.0, -0.45, 1.08), 26, 0),
    (72, (0.0, 0.0, 1.0), 0, 0),
]
for f, loc, pitch, yaw in KEYS:
    cam.location = loc
    cam.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)
sc.camera = cam
print("camera keyed", [k[0] for k in KEYS])
