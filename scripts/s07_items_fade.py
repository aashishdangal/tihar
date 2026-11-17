# s07: the Bhai Tika items fade in slowly on the empty thali, one per scroll beat
# (owner 2026-11-17: no hands, no pop - a slow fade). Each item's objects carry a custom property
# "s07_hide" (1 = invisible, 0 = solid) that is keyframed; every material they render with is
# wrapped once as  mix(Transparent, original, 1 - max(object.s07_hide, instancer.s07_hide)),
# so GN instances (mala heads, powder grains) fade with their instancer. Objects without the
# property read 0 -> fully visible, so shared materials are safe elsewhere.
# The camera (Jamuna's eyes) turns a little toward each item and back. Karuwa, tapari + diyo are
# there from frame 1. The hands (collection S07_Hand) stay excluded.
# Run inside s07_bhaitika_vNNN.blend (MCP exec). Rebuilds all item keys and camera keys > 36.
import bpy
from mathutils import Vector

SC = bpy.context.scene
CAM = bpy.data.objects["CAM_S07"]
START, BEAT, FADE = 36, 24, 18
LOOK = 0.35
ITEMS = [
    ("tika-dani", ["S07_TikaDani"]),
    ("sayapatri", ["S07_Sayapatri"]),
    ("makhamali", ["S07_Makhamali"]),
    ("okhar",     ["S07_Walnut", "S07_Walnut_2", "S07_Walnut_3"]),
    ("banana",    ["S07_Banana_0", "S07_Banana_1", "S07_Banana_2"]),
    ("apple",     ["S07_Apple"]),
    ("orange",    ["S07_Orange"]),
]
PROP = "s07_hide"


def tree(o): return [o] + list(o.children_recursive)


def fcurves(o):
    a = o.animation_data
    if not a or not a.action: return []
    return [fc for l in a.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def find_lc(name, lc=None):
    lc = lc or bpy.context.view_layer.layer_collection
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find_lc(name, ch)
        if r: return r


lc = find_lc("S07_Hand")
if lc: lc.exclude = True

# --- items back to their final, untouched state ------------------------------------------------
SC.frame_set(1)
all_objs = []
for _, names in ITEMS:
    for n in names:
        r = bpy.data.objects[n]
        for o in tree(r):
            if o.animation_data: o.animation_data_clear()
            o.hide_render = False; o.hide_viewport = False
            if PROP in o: del o[PROP]
            all_objs.append(o)
        if "s07_final" in r: r.location = Vector(r["s07_final"])
        if "s07_scale" in r: r.scale = Vector(r["s07_scale"])
kar = bpy.data.objects["S07_Karuwa"]
if kar.animation_data: kar.animation_data_clear()
for m in tree(kar): m.hide_render = False; m.hide_viewport = False
bpy.context.view_layer.update()

# --- every material the items render with (own slots + GN instances) ---------------------------
mats = set()
names_set = {o.name for o in all_objs}
for o in all_objs:
    for s in getattr(o, "material_slots", []):
        if s.material: mats.add(s.material)
dg = bpy.context.evaluated_depsgraph_get()
for inst in dg.object_instances:
    if inst.is_instance and inst.parent and inst.parent.original.name in names_set:
        for s in inst.object.original.material_slots:
            if s.material: mats.add(s.material)
for o in all_objs:                               # materials set inside GN (Set Material inputs)
    for md in o.modifiers:
        if md.type == "NODES" and md.node_group:
            for nd in md.node_group.nodes:
                if nd.bl_idname == "GeometryNodeSetMaterial" and nd.inputs["Material"].default_value:
                    mats.add(nd.inputs["Material"].default_value)


def wrap(m):
    if m.get("s07_fadewrap") or not m.use_nodes: return
    nt = m.node_tree
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) \
        or next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if not out or not out.inputs["Surface"].is_linked: return
    src = out.inputs["Surface"].links[0].from_socket
    a1 = nt.nodes.new("ShaderNodeAttribute"); a1.attribute_type = "OBJECT"; a1.attribute_name = PROP
    a2 = nt.nodes.new("ShaderNodeAttribute"); a2.attribute_type = "INSTANCER"; a2.attribute_name = PROP
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(a1.outputs["Fac"], mx.inputs[0]); nt.links.new(a2.outputs["Fac"], mx.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mx.outputs[0], mix.inputs["Fac"])           # Fac 0 -> original, 1 -> transparent
    nt.links.new(src, mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    for i, n in enumerate((a1, a2, mx, tr, mix)):
        n.location = (out.location.x - 200, out.location.y - 180 - 120 * i)
    m["s07_fadewrap"] = 1


for m in mats: wrap(m)
print("materials wrapped:", len(mats))

# --- camera head turns ---------------------------------------------------------------------------
for fc in fcurves(CAM):
    for kp in [k for k in fc.keyframe_points if k.co.x > START + 0.5][::-1]:
        fc.keyframe_points.remove(kp)
SC.frame_set(START)
EYE = CAM.matrix_world.translation.copy()
BASE_ROT = CAM.rotation_euler.copy()
BASE_DIR = (CAM.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()


def cam_key(frame, d):
    CAM.rotation_euler = d.to_track_quat("-Z", "Y").to_euler("XYZ", BASE_ROT)
    CAM.keyframe_insert("rotation_euler", frame=frame)


def centre_of(objs):
    P = [m.matrix_world @ Vector(c) for r in objs for m in tree(r) if m.type in {"MESH", "CURVE"} for c in m.bound_box]
    return sum(P, Vector()) / len(P)


# --- fade keys ---------------------------------------------------------------------------------
for k, (label, names) in enumerate(ITEMS):
    f0 = START + k * BEAT
    roots = [bpy.data.objects[n] for n in names]
    for r in roots:
        for o in tree(r):
            def key(frame, v, hidden=None):
                o[PROP] = v; o.keyframe_insert('["%s"]' % PROP, frame=frame)
                if hidden is not None:
                    o.hide_render = hidden; o.hide_viewport = hidden
                    o.keyframe_insert("hide_render", frame=frame); o.keyframe_insert("hide_viewport", frame=frame)
            key(1, 1.0, hidden=True)
            key(f0, 1.0, hidden=False)
            key(f0 + FADE, 0.0)
            o.update_tag()
    c = centre_of(roots)
    mid = (BASE_DIR * (1 - LOOK) + (c - EYE).normalized() * LOOK).normalized()
    cam_key(f0, BASE_DIR); cam_key(f0 + 10, mid); cam_key(f0 + 17, mid); cam_key(f0 + 23, BASE_DIR)
    print("%-10s fades in %d-%d" % (label, f0, f0 + FADE))

END = START + len(ITEMS) * BEAT
SC.frame_end = END + 24
for o in [CAM] + all_objs:
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            if fc.data_path.startswith("hide"): kp.interpolation = "CONSTANT"
            else: kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
SC.frame_set(1)
print("all items in by", END, "- scene end", SC.frame_end)
