# s07: two lit clay diyos on the floor either side of Jamuna's thali (s00 scan + approved RealFire
# flame, appended from s00_enter_v068_realfire.blend, same method as s06_build_thali.py).
# Placed across the camera's view direction so both stay in frame beside the plate.
# Run inside s07_bhaitika_vNNN.blend after s07_build_thali.py (MCP exec).
import bpy, math
from mathutils import Vector

S00 = "E:/Projects/tihar/blender/scenes/s00_enter_v068_realfire.blend"
LIGHT_W = 1.4                       # flame light; morning sun does most of the work
VIEW = Vector((0.8, -0.6, 0)).normalized()        # camera sits plate + VIEW*0.62 (looks back along -VIEW)
SIDE = Vector((-VIEW.y, VIEW.x, 0))               # across the frame
GAP = 0.36                                         # plate centre -> diyo centre (plate R 0.24)

col = bpy.data.collections["S07_Thali"]
root = bpy.data.objects["S07_Thali_Root"]


def s00_diyo(name, loc, scale, rotz):
    old = bpy.data.objects.get(name)
    if old:
        for o in [old] + list(old.children_recursive):
            bpy.data.objects.remove(o, do_unlink=True)
    want = ["S00_DiyoScan_Mesh", "S00_Oil", "S00_Wick", "S00_WickTip", "S00_FlamePivot", "S00_FireVol",
            "S00_FireVol_B", "S00_FlameCore", "L_S00_Flame"]
    with bpy.data.libraries.load(S00, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in want]
    e = bpy.data.objects.new(name, None)
    col.objects.link(e)
    names = [x.name for x in dst.objects]
    for o in dst.objects:
        col.objects.link(o)
        # keep the s00 flame animation (clearing the pivot keys collapses the flame)
        if o.parent is None or o.parent.name not in names:
            m = o.matrix_basis.copy(); q = o
            while q.parent:                     # rebuild the world matrix from the parent chain
                m = q.parent.matrix_basis @ q.matrix_parent_inverse @ m
                q = q.parent
            o.parent = None
            o.matrix_basis = m
            o.parent = e
        o.name = f"{name}_" + o.name.replace("S00_", "")
    for o in dst.objects:
        if o.type == "LIGHT":
            o.data = o.data.copy(); o.data.energy = LIGHT_W
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(rotz)); e.scale = (scale,) * 3
    e.parent = root; e.matrix_parent_inverse = root.matrix_world.inverted()
    return e


def oil_mat():
    """Clear mustard oil (as s06): Transparent + Fresnel gloss so the flame light reaches the clay."""
    m = bpy.data.materials.get("S06_Oil") or bpy.data.materials.get("S07_Oil")
    if m: return m
    m = bpy.data.materials.new("S07_Oil"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (1.0, 0.86, 0.55, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.02
    fr = nt.nodes.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.47
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs["Fac"], mx.inputs["Fac"]); nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mx.inputs[2]); nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    return m


centre = root.matrix_world.translation.copy(); centre.z = 0.0
OIL = oil_mat()
for nm, sgn in (("S07_Diyo_A", 1), ("S07_Diyo_B", -1)):
    p = centre + SIDE * (GAP * sgn)
    to_plate = (centre - p).normalized()
    e = s00_diyo(nm, p, 0.95, math.degrees(math.atan2(to_plate.y, to_plate.x)))
    for o in e.children_recursive:
        if "Oil" in o.name and o.type == "MESH":
            o.data.materials.clear(); o.data.materials.append(OIL)
    print(nm, tuple(round(v, 2) for v in p))
