"""More hillside in front of the camera (owner 2026-11-21: "raise the hill we are sitting on little bit"
-> chose "more ground in front": keep the camera, lift the slope in front/below it).

A separate fine mesh S08_FrontRidge (the hill's own faces are 100s of m, too coarse to shape here), in
front of CAM_S08 from 28 m (past the near grass) to 120 m, +-32 deg. It only rises where the hill is
lower. Its far edge is the new skyline of the hillside, set ~15 deg below the camera (the bottom tenth of
the frame), wavering +-1.3 deg across the view so it does not read as a ruled line; behind the edge it
falls away steeper than any view ray, so the ridge itself shows as one dark slope. Hill material.

  blender.exe -b blender/scenes/s08_finale_v073.blend --python scripts/s08_front_ridge.py   (saves in place)
"""
import math

import bpy
import numpy as np
from mathutils import Vector

sc = bpy.context.scene
cam = bpy.data.objects["CAM_S08"]; cp = cam.matrix_world.translation
hill = bpy.data.objects["S08_Hill"]; hinv = hill.matrix_world.inverted()
fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1)); yaw0 = math.atan2(fwd.x, fwd.y)

D0, D1, DR = 28.0, 120.0, 62.0                 # near edge, far edge of the mesh, rim distance
NA, ND = 129, 47
TH = math.radians(15.0)


def hill_z(x, y):
    o = hinv @ Vector((x, y, cp.z + 800)); d = (hinv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, loc, _, _ = hill.ray_cast(o, d)
    return (hill.matrix_world @ loc).z if ok else None


verts, faces, lift, rimw = [], [], [], []
for j in range(ND):
    dd = D0 + (D1 - D0) * j / (ND - 1)
    for i in range(NA):
        a = yaw0 + math.radians(-32 + 64 * i / (NA - 1))
        x, y = cp.x + dd * math.sin(a), cp.y + dd * math.cos(a)
        g = hill_z(x, y)
        g = g if g is not None else cp.z - 200
        u = i / (NA - 1)
        th = TH + math.radians(1.3) * (0.6 * math.sin(2 * math.pi * (1.7 * u + 0.2)) + 0.4 * math.sin(2 * math.pi * (4.3 * u + 0.7)))
        rim = cp.z - DR * math.tan(th)                         # rim height that sits at angle th
        if dd <= DR:
            z = rim + (DR - dd) * 0.04                         # near side: almost level, a gentle rise toward us
            near_w = min(1.0, (dd - D0) / 10.0)                # first 10 m: blend down into the real hill
            z = g + (max(z, g) - g) * near_w
        else:
            z = rim - (dd - DR) * math.tan(math.radians(32))   # behind the rim: falls away, hidden
        z = max(z, g)                                          # never below the real hill
        verts.append((x, y, z))
        lift.append(z - g)                                     # > 0 where the ridge stands proud of the hill
        rimw.append(math.exp(-((dd - DR) / 7.0) ** 2))          # 1 on the skyline edge
for j in range(ND - 1):
    for i in range(NA - 1):
        a = j * NA + i
        faces.append((a, a + 1, a + NA + 1, a + NA))

old = bpy.data.objects.get("S08_FrontRidge")
if old:
    me_old = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(me_old)
me = bpy.data.meshes.new("S08_FrontRidge"); me.from_pydata(verts, [], faces); me.update()
for p in me.polygons:
    p.use_smooth = True
for name, vals in (("lift", lift), ("rimw", rimw)):
    at = me.attributes.new(name, "FLOAT", "POINT"); at.data.foreach_set("value", vals)

# first render: the hill material without UVs read as a smooth grey dune -> own dark earth/scrub shader
mat = bpy.data.materials.get("M_S08_Ridge") or bpy.data.materials.new("M_S08_Ridge")
mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
nt.links.new(bs.outputs[0], out.inputs["Surface"])
geo = nt.nodes.new("ShaderNodeNewGeometry")
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 8.0
n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 4.0; n2.inputs["Detail"].default_value = 6.0
for n in (n1, n2):
    nt.links.new(geo.outputs["Position"], n.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.018, 0.017, 0.014, 1)       # dark earth
ramp.color_ramp.elements[1].color = (0.030, 0.034, 0.020, 1)       # dry scrub
nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
bs.inputs["Roughness"].default_value = 0.95
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.3
nt.links.new(n2.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], bs.inputs["Normal"])
me.materials.append(mat)
ob = bpy.data.objects.new("S08_FrontRidge", me)
hill.users_collection[0].objects.link(ob)

# grass + scrub on the ridge, densest and biggest on its skyline so the edge against the city is ragged
g = bpy.data.node_groups.get("GN_S08_RidgeGrass")
if g:
    bpy.data.node_groups.remove(g)
g = bpy.data.node_groups.new("GN_S08_RidgeGrass", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
N, Lk = g.nodes, g.links
gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")


def named(name):
    n = N.new("GeometryNodeInputNamedAttribute"); n.data_type = "FLOAT"; n.inputs["Name"].default_value = name
    return n.outputs["Attribute"]


def mth(op, a, b):
    n = N.new("ShaderNodeMath"); n.operation = op
    for i, v in ((0, a), (1, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            Lk.new(v, n.inputs[i])
    return n.outputs[0]


raised = mth("GREATER_THAN", named("lift"), 0.3)
dens = mth("MULTIPLY", raised, mth("ADD", 5.0, mth("MULTIPLY", named("rimw"), 22.0)))   # 5 /m2, 27 /m2 on the rim
dist = N.new("GeometryNodeDistributePointsOnFaces"); dist.distribute_method = "RANDOM"
Lk.new(gi.outputs[0], dist.inputs["Mesh"]); Lk.new(dens, dist.inputs["Density"])
dist.inputs["Seed"].default_value = 9
ci = N.new("GeometryNodeCollectionInfo"); ci.inputs["Collection"].default_value = bpy.data.collections["S08_GrassSrc"]
ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
iop = N.new("GeometryNodeInstanceOnPoints"); iop.inputs["Pick Instance"].default_value = True
Lk.new(dist.outputs["Points"], iop.inputs["Points"]); Lk.new(ci.outputs[0], iop.inputs["Instance"])
ri = N.new("FunctionNodeRandomValue"); ri.data_type = "INT"; ri.inputs["Min"].default_value = 0; ri.inputs["Max"].default_value = 40
Lk.new(next(o for o in ri.outputs if o.enabled and o.type == "INT"), iop.inputs["Instance Index"])
rr = N.new("FunctionNodeRandomValue"); rr.data_type = "FLOAT_VECTOR"
rr.inputs["Min"].default_value = (0, 0, 0); rr.inputs["Max"].default_value = (0.15, 0.15, 6.283)
Lk.new(next(o for o in rr.outputs if o.enabled and o.type == "VECTOR"), iop.inputs["Rotation"])
rs = N.new("FunctionNodeRandomValue"); rs.data_type = "FLOAT"; rs.inputs["Min"].default_value = 1.8; rs.inputs["Max"].default_value = 3.4
sc_rim = mth("ADD", 1.0, mth("MULTIPLY", named("rimw"), 0.6))        # up to 60 % bigger on the skyline
Lk.new(mth("MULTIPLY", next(o for o in rs.outputs if o.enabled and o.type == "VALUE"), sc_rim), iop.inputs["Scale"])
j = N.new("GeometryNodeJoinGeometry")
Lk.new(gi.outputs[0], j.inputs[0]); Lk.new(iop.outputs[0], j.inputs[0]); Lk.new(j.outputs[0], go.inputs[0])
ob.modifiers.new("S08_RidgeGrass", "NODES").node_group = g
dg = bpy.context.evaluated_depsgraph_get()
n_inst = sum(1 for i in dg.object_instances if i.is_instance and i.parent and i.parent.original.name == "S08_FrontRidge")
print("[ridge] grass tufts on the ridge:", n_inst)
zs = np.array([v[2] for v in verts])
print("[ridge] verts", len(verts), "z %.1f..%.1f (camera %.1f)" % (zs.min(), zs.max(), cp.z))
bpy.ops.wm.save_mainfile()
print("[ridge] saved", bpy.data.filepath)
