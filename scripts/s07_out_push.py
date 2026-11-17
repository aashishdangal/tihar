# s07 out (owner 2026-11-17, option A): hold on the full thali for the two captions, then a slow
# push into the diyo flame; focus slips past the flame so it blooms out of focus, the lens closes in
# and the exposure lifts until the frame is a warm gold fill. s08 opens from gold bokeh of the
# valley lights (crossfade in the encoder).
# Run inside s07_bhaitika_vNNN.blend after s07_items_fade.py (MCP exec).
import bpy
from mathutils import Vector

SC = bpy.context.scene
CAM = bpy.data.objects["CAM_S07"]
HOLD0, HOLD1, END = 204, 232, 272
FLAME = bpy.data.objects["S07_Diyo_FlameCore"]


def fcurves(id_):
    a = id_.animation_data
    if not a or not a.action: return []
    return [fc for l in a.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


for id_ in (CAM, CAM.data, SC):
    for fc in fcurves(id_):
        for kp in [k for k in fc.keyframe_points if k.co.x > HOLD0 + 0.5][::-1]:
            fc.keyframe_points.remove(kp)

SC.frame_set(HOLD0)
eye = CAM.location.copy(); rot0 = CAM.rotation_euler.copy()
lens0 = CAM.data.lens; f0 = CAM.data.dof.focus_distance; fstop0 = CAM.data.dof.aperture_fstop
flame = FLAME.matrix_world.translation.copy() + Vector((0, 0, 0.008))


def cam_key(frame, loc, aim, lens, focus, fstop):
    CAM.location = loc
    CAM.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler("XYZ", rot0)
    CAM.data.lens = lens; CAM.data.dof.focus_distance = focus; CAM.data.dof.aperture_fstop = fstop
    CAM.keyframe_insert("location", frame=frame); CAM.keyframe_insert("rotation_euler", frame=frame)
    CAM.data.keyframe_insert("lens", frame=frame)
    CAM.data.dof.keyframe_insert("focus_distance", frame=frame)
    CAM.data.dof.keyframe_insert("aperture_fstop", frame=frame)


def expo_key(frame, ev):
    SC.view_settings.exposure = ev; SC.view_settings.keyframe_insert("exposure", frame=frame)


CAM.data.dof.use_dof = True
aim0 = eye + (CAM.matrix_world.to_3x3() @ Vector((0, 0, -1))) * f0
cam_key(HOLD0, eye, aim0, lens0, f0, fstop0)                 # hold: two caption pauses
cam_key(HOLD1, eye, aim0, lens0, f0, fstop0)
expo_key(1, 0.0); expo_key(HOLD1, 0.0)
# final approach drops to flame height so the flame is seen against the dark room, not the white
# rice (looking down, the out-of-focus rice filled the frame with beige)
h = Vector((eye.x - flame.x, eye.y - flame.y, 0)).normalized()
flame = flame + Vector((0, 0, 0.004))
p1 = flame + h * 0.35 + Vector((0, 0, 0.16))
cam_key(HOLD1 + 16, p1, flame, 38, (p1 - flame).length, 2.0)
p2 = flame + h * 0.06 + Vector((0, 0, 0.006))                 # 6 cm from the flame, at its height
cam_key(END, p2, flame, 55, 0.8, 1.2)                         # focus slips far behind -> one big bloom
# warm the bloom toward gold: white balance + a small exposure lift (more exposure washes it to cream)
vs = SC.view_settings; vs.use_white_balance = True
def wb_key(frame, temp):
    vs.white_balance_temperature = temp; vs.keyframe_insert("white_balance_temperature", frame=frame)
wb_key(1, 6500); wb_key(END - 22, 6500); wb_key(END, 20000)
expo_key(END - 22, 0.0); expo_key(END, 0.3)
SC.frame_end = END
for id_ in (CAM, CAM.data, SC):
    for fc in fcurves(id_):
        for kp in fc.keyframe_points:
            if kp.co.x >= HOLD0 - 0.5:
                kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
SC.frame_set(1)
print("hold %d-%d, push %d-%d, scene end %d" % (HOLD0, HOLD1, HOLD1, END, SC.frame_end))
