# Short dog fur for Nubis as geometry-nodes hair that follows the rig.
# Roots are scattered on the body's REST geometry (rest_position attribute, so they never swim),
# aimed along the coat flow (head -> tail, then down), then moved onto the posed body with
# Deform Curves on Surface. Colour comes from the body texture at each root's UV.
# blender.exe -b <in.blend> --python scripts/s04_nubis_fur.py -- <out.blend> [density_per_m2]
import bpy, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0] if argv else "blender/assets/s04_dog/nubis_v003.blend")
DENSITY = float(argv[1]) if len(argv) > 1 else 160000.0   # roots per m2 (model units)
UV = "Default UVs"

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = bpy.data.objects["Nubis Mesh"]
body.add_rest_position_attribute = True
tex_img = next(i for i in bpy.data.images if i.filepath and os.path.basename(i.filepath).lower() == "nubis.jpg")

# coat flow in rest space: from the head towards the tail root
bones = rig.data.bones
head_b = next(b for b in bones if b.name.lower() == "head")
tail_b = next(b for b in bones if b.name.lower().startswith("tail"))
flow = (tail_b.head_local - head_b.head_local)
flow.z = 0
flow = flow.normalized()
print("[fur] head", head_b.head_local, "tail", tail_b.name, tail_b.head_local, "flow", flow)

# ---- the curves object ---------------------------------------------------------------------
old = bpy.data.objects.get("Nubis Fur")
if old:
    bpy.data.objects.remove(old)
cd = bpy.data.hair_curves.new("Nubis Fur")
fur = bpy.data.objects.new("Nubis Fur", cd)
for c in body.users_collection:
    c.objects.link(fur)
fur.parent = body.parent
fur.matrix_parent_inverse = body.matrix_parent_inverse.copy()
fur.matrix_basis = body.matrix_basis.copy()
cd.surface = body
cd.surface_uv_map = UV

ng = bpy.data.node_groups.new("NubisFurGN", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
N = ng.nodes
L = ng.links
X = 0


def node(t, **kw):
    global X
    n = N.new(t)
    n.location = (X, 0)
    X += 220
    for k, v in kw.items():
        setattr(n, k, v)
    return n


gin = node("NodeGroupInput")
obi = node("GeometryNodeObjectInfo")
obi.inputs["Object"].default_value = body
obi.transform_space = "ORIGINAL"
# rest geometry: positions from rest_position
rest_attr = node("GeometryNodeInputNamedAttribute", data_type="FLOAT_VECTOR")
rest_attr.inputs["Name"].default_value = "rest_position"
setp = node("GeometryNodeSetPosition")
L.new(obi.outputs["Geometry"], setp.inputs["Geometry"])
L.new(rest_attr.outputs["Attribute"], setp.inputs["Position"])
# only the coat (material slot 0, "Pads-1": body + legs + head skin)
msel = node("GeometryNodeMaterialSelection")
msel.inputs["Material"].default_value = body.data.materials[0]
sep = node("GeometryNodeSeparateGeometry", domain="FACE")
L.new(setp.outputs["Geometry"], sep.inputs["Geometry"])
L.new(msel.outputs["Selection"], sep.inputs["Selection"])
# uv as a named attribute so it is carried to the points
uv_attr = node("GeometryNodeInputNamedAttribute", data_type="FLOAT_VECTOR")
uv_attr.inputs["Name"].default_value = UV
dist = node("GeometryNodeDistributePointsOnFaces", distribute_method="RANDOM")
dist.inputs["Density"].default_value = DENSITY
dist.inputs["Seed"].default_value = 7
L.new(sep.outputs["Selection"], dist.inputs["Mesh"])
cap = node("GeometryNodeCaptureAttribute", domain="FACE")
# Blender 5: capture items
cap.capture_items.new("VECTOR", "uv")
L.new(sep.outputs["Selection"], cap.inputs["Geometry"])
L.new(uv_attr.outputs["Attribute"], cap.inputs["uv"])
# distribute from the captured mesh instead
L.new(cap.outputs["Geometry"], dist.inputs["Mesh"])

# per-point direction: normal lifted 0.35, plus the flow projected on the surface, plus gravity
nrm = dist.outputs["Normal"]
flow_v = node("FunctionNodeInputVector"); flow_v.vector = (flow.x, flow.y, -0.55)
dotn = node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
L.new(flow_v.outputs[0], dotn.inputs[0]); L.new(nrm, dotn.inputs[1])
scl = node("ShaderNodeVectorMath", operation="SCALE")
L.new(nrm, scl.inputs[0]); L.new(dotn.outputs["Value"], scl.inputs["Scale"])
tang = node("ShaderNodeVectorMath", operation="SUBTRACT")
L.new(flow_v.outputs[0], tang.inputs[0]); L.new(scl.outputs[0], tang.inputs[1])
tangn = node("ShaderNodeVectorMath", operation="NORMALIZE")
L.new(tang.outputs[0], tangn.inputs[0])
lift = node("ShaderNodeVectorMath", operation="SCALE"); lift.inputs["Scale"].default_value = 0.38
L.new(nrm, lift.inputs[0])
dirv = node("ShaderNodeVectorMath", operation="ADD")
L.new(tangn.outputs[0], dirv.inputs[0]); L.new(lift.outputs[0], dirv.inputs[1])
# a little random spread so the coat doesn't look combed
rnd = node("FunctionNodeRandomValue", data_type="FLOAT_VECTOR")
[i for i in rnd.inputs if i.name == "Min" and i.type == "VECTOR"][0].default_value = (-0.25, -0.25, -0.25)
[i for i in rnd.inputs if i.name == "Max" and i.type == "VECTOR"][0].default_value = (0.25, 0.25, 0.25)
rnd.inputs["Seed"].default_value = 3
dir2 = node("ShaderNodeVectorMath", operation="ADD")
L.new(dirv.outputs[0], dir2.inputs[0]); L.new([o for o in rnd.outputs if o.type == "VECTOR"][0], dir2.inputs[1])
rot = node("FunctionNodeAlignRotationToVector", axis="Z")
L.new(dir2.outputs[0], rot.inputs["Vector"])

# length: 2.6 cm on the body, shorter low on the legs and on the head (model units)
pos = node("GeometryNodeInputPosition")
sepz = node("ShaderNodeSeparateXYZ"); L.new(pos.outputs[0], sepz.inputs[0])
legs = node("ShaderNodeMapRange"); legs.inputs["From Min"].default_value = 0.22; legs.inputs["From Max"].default_value = 0.55
legs.inputs["To Min"].default_value = 0.012; legs.inputs["To Max"].default_value = 0.026
L.new(sepz.outputs["Z"], legs.inputs["Value"])
# head region: distance to the head bone
hd = node("ShaderNodeVectorMath", operation="DISTANCE")
hpos = node("FunctionNodeInputVector"); hpos.vector = tuple(head_b.head_local)
L.new(pos.outputs[0], hd.inputs[0]); L.new(hpos.outputs[0], hd.inputs[1])
headf = node("ShaderNodeMapRange"); headf.inputs["From Min"].default_value = 0.12; headf.inputs["From Max"].default_value = 0.3
headf.inputs["To Min"].default_value = 0.42; headf.inputs["To Max"].default_value = 1.0
L.new(hd.outputs["Value"], headf.inputs["Value"])
rlen = node("FunctionNodeRandomValue", data_type="FLOAT")
fmin = [i for i in rlen.inputs if i.name == "Min" and i.type == "VALUE"][0]
fmax = [i for i in rlen.inputs if i.name == "Max" and i.type == "VALUE"][0]
fmin.default_value = 0.7; fmax.default_value = 1.15; rlen.inputs["Seed"].default_value = 11
rlen_out = [o for o in rlen.outputs if o.type == "VALUE"][0]
m1 = node("ShaderNodeMath", operation="MULTIPLY"); L.new(legs.outputs[0], m1.inputs[0]); L.new(headf.outputs[0], m1.inputs[1])
m2 = node("ShaderNodeMath", operation="MULTIPLY"); L.new(m1.outputs[0], m2.inputs[0]); L.new(rlen_out, m2.inputs[1])

line = node("GeometryNodeCurvePrimitiveLine")
line.inputs["Start"].default_value = (0, 0, 0); line.inputs["End"].default_value = (0, 0, 1)
res = node("GeometryNodeResampleCurve"); res.inputs["Count"].default_value = 4
L.new(line.outputs[0], res.inputs["Curve"])
iop = node("GeometryNodeInstanceOnPoints")
L.new(dist.outputs["Points"], iop.inputs["Points"])
L.new(res.outputs[0], iop.inputs["Instance"])
L.new(rot.outputs[0], iop.inputs["Rotation"])
L.new(m2.outputs[0], iop.inputs["Scale"])
# carry the root uv to the instances (instance domain), then realize
st_uv_i = node("GeometryNodeStoreNamedAttribute", data_type="FLOAT2", domain="INSTANCE")
st_uv_i.inputs["Name"].default_value = "surface_uv_coordinate"
L.new(iop.outputs[0], st_uv_i.inputs["Geometry"])
L.new(cap.outputs["uv"], st_uv_i.inputs["Value"])
real = node("GeometryNodeRealizeInstances")
L.new(st_uv_i.outputs[0], real.inputs["Geometry"])
# fur_uv for the shader (curve domain copy)
uvread = node("GeometryNodeInputNamedAttribute", data_type="FLOAT_VECTOR")
uvread.inputs["Name"].default_value = "surface_uv_coordinate"
st_fuv = node("GeometryNodeStoreNamedAttribute", data_type="FLOAT_VECTOR", domain="CURVE")
st_fuv.inputs["Name"].default_value = "fur_uv"
L.new(real.outputs[0], st_fuv.inputs["Geometry"])
L.new(uvread.outputs["Attribute"], st_fuv.inputs["Value"])
# droop: tips sag a little under gravity
spar = node("GeometryNodeSplineParameter")
sq = node("ShaderNodeMath", operation="POWER"); sq.inputs[1].default_value = 2.0
L.new(spar.outputs["Factor"], sq.inputs[0])
sag = node("ShaderNodeVectorMath", operation="SCALE")
sag_v = node("FunctionNodeInputVector"); sag_v.vector = (0, 0, -0.006)
L.new(sag_v.outputs[0], sag.inputs[0]); L.new(sq.outputs[0], sag.inputs["Scale"])
setp2 = node("GeometryNodeSetPosition")
L.new(st_fuv.outputs[0], setp2.inputs["Geometry"])
L.new(sag.outputs[0], setp2.inputs["Offset"])
# onto the posed body
deform = node("GeometryNodeDeformCurvesOnSurface")
L.new(setp2.outputs[0], deform.inputs["Curves"])
# taper radius root -> tip
rad = node("ShaderNodeMapRange"); rad.inputs["To Min"].default_value = 0.00022; rad.inputs["To Max"].default_value = 0.00004
L.new(spar.outputs["Factor"], rad.inputs["Value"])
srad = node("GeometryNodeSetCurveRadius")
L.new(deform.outputs[0], srad.inputs["Curve"])
L.new(rad.outputs[0], srad.inputs["Radius"])
# material
fm = bpy.data.materials.get("NubisFurMat") or bpy.data.materials.new("NubisFurMat")
fm.use_nodes = True
nt = fm.node_tree
nt.nodes.clear()
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); o_.location = (600, 0)
hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled"); hb.location = (300, 0)
try:
    hb.parametrization = "COLOR"
except Exception:
    pass
hb.inputs["Roughness"].default_value = 0.38
hb.inputs["Radial Roughness"].default_value = 0.5
hb.inputs["Coat"].default_value = 0.25
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "fur_uv"; at.location = (-500, 0)
im = nt.nodes.new("ShaderNodeTexImage"); im.image = tex_img; im.location = (-280, 0)
nt.links.new(at.outputs["Vector"], im.inputs["Vector"])
# tips a touch lighter
ramp = nt.nodes.new("ShaderNodeHueSaturation"); ramp.location = (60, 0)
ramp.inputs["Value"].default_value = 1.15
nt.links.new(im.outputs["Color"], ramp.inputs["Color"])
nt.links.new(ramp.outputs["Color"], hb.inputs["Color"])
nt.links.new(hb.outputs[0], o_.inputs["Surface"])
smat = node("GeometryNodeSetMaterial")
smat.inputs["Material"].default_value = fm
L.new(srad.outputs[0], smat.inputs["Geometry"])
gout = node("NodeGroupOutput")
L.new(smat.outputs[0], gout.inputs[0])
cd.materials.append(fm)

mod = fur.modifiers.new("Fur", "NODES")
mod.node_group = ng

dg = bpy.context.evaluated_depsgraph_get()
ev = fur.evaluated_get(dg)
print("[fur] curves", len(ev.data.curves), "points", len(ev.data.points))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("[fur] saved", out)
