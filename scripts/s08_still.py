"""Clean still for the hybrid finale (owner 2026-11-21: "first we will do clean still without the tree,
grass and kite ... city generator to fill upto airport area then mid poly then low poly also left side
mountain should be little higher such that it gets more light also add volumetric clouds as we are only
rendering a image").

  blender.exe -b blender/scenes/s08_finale_v072.blend --python scripts/s08_still.py   -> s08_finale_v073.blend

1. Tree, near grass and kite hidden (they come back as warped layers in the browser). Flag stays: its
   rendered loop covers that corner.
2. (dropped by the owner) city rings to the airport; the city stays as in v072.
3. Left-of-frame Himalaya raised (heights above 2 km scaled up to x1.3) so the tops reach the alpenglow.
4. Volumetric cloud deck, 7.5-9.5 km up, over the ranges; lit by the alpenglow too.
5. 256 samples, adaptive.
"""
import math

import bpy
import numpy as np
from mathutils import Vector

ROOT = r"E:/Projects/tihar"
A = r"E:\Projects\tihar\blender\assets\osm"
CX, CY = 2000.0, -11000.0
NEAR_ANG = 27.0
DET = (10000.0, 11500.0)          # detailed CG -> mid handover band (airport ~10.8 km)
MID = (14000.0, 16000.0)          # mid -> boxes handover band
BOX_X, BOX_Y = (-3450.0, 10350.0), (-11240.0, 3900.0)   # extent of s08_mid footprints (q_mid.txt)
sc = bpy.context.scene

# ---- 1. hide the moving foreground
for o in bpy.data.objects:
    # flag too (owner: "also remove the flag") - it comes back as its own rendered loop
    if o.name in ("S08_Tree", "S08_GrassFG") or o.name.startswith(("S08_Kite", "S08_Flag")):
        o.hide_render = True
print("[still] tree, grass, kite hidden")

# ---- 2. city rings - NOT USED (owner 2026-11-21: "let go with the current one leave this making detailed").
# The city stays as in v072 (detailed City Generator to 2.5 km, lit boxes beyond). Kept for reference:
# detailed to ~11 km would have been ~90k houses / ~30M instances, too much for the 16 GB GPU.
CITY_RINGS = False


def city_rings():
    d = np.load(A + r"\s08_mid.npz")
    bv, bf, dist, ang = d["bv"], d["bf"], d["dist"], d["ang"]
    off = np.concatenate([[0], np.cumsum(bf)])
    rng = np.random.default_rng(73)
    r = rng.random(len(bf))
    p_det = np.clip((DET[1] - dist) / (DET[1] - DET[0]), 0, 1)
    p_mid = np.clip((MID[1] - dist) / (MID[1] - MID[0]), 0, 1)
    cone = (np.abs(ang) < NEAR_ANG) & (dist > 150)
    det = np.where(cone & (r < p_det))[0]
    mid = np.where(cone & (r >= p_det) & (r < p_mid))[0]


    def mesh_from(idx, name):
        verts, faces = [], []
        for i in idx:
            p = bv[off[i]:off[i + 1]]; s = len(verts)
            verts += p.tolist(); faces.append(list(range(s, s + len(p))))
        me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
        return me


    def set_mesh(ob, me):
        old = ob.data
        for m in old.materials:
            me.materials.append(m)
        ob.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)


    near = bpy.data.objects["S08_NearCity"]; lights = bpy.data.objects["S08_NearLights"]
    set_mesh(near, mesh_from(det, "S08_NearCity"))
    set_mesh(lights, mesh_from(det, "S08_NearLights"))
    cg = near.modifiers["CityGenerator"]
    getattr(cg.properties.inputs, "Socket_137").value = True            # Cycles Light Optimization

    midob = bpy.data.objects.get("S08_MidCity")
    if midob is None:
        midob = bpy.data.objects.new("S08_MidCity", mesh_from(mid, "S08_MidCity"))
        near.users_collection[0].objects.link(midob)
        mm = midob.modifiers.new("CityGenerator", "NODES"); mm.node_group = cg.node_group
        # copy every City Generator setting from the near city, then switch to its low-poly mode
        for it in cg.node_group.interface.items_tree:
            if getattr(it, "in_out", None) == "INPUT" and it.socket_type != "NodeSocketGeometry":
                try:
                    getattr(mm.properties.inputs, it.identifier).value = getattr(cg.properties.inputs, it.identifier).value
                except (AttributeError, TypeError):
                    pass
        getattr(mm.properties.inputs, "Socket_135").value = True        # Low Poly Preview
        getattr(mm.properties.inputs, "Socket_137").value = True
    else:
        set_mesh(midob, mesh_from(mid, "S08_MidCity"))
    print("[still] footprints: detailed", len(det), " mid poly", len(mid))

    # far boxes: removed where a detailed/mid house stands (same dithered bands), only inside the footprint box
    ng = bpy.data.node_groups["GN_S08_Buildings"]; N, Lk = ng.nodes, ng.links
    mr = next(n for n in N if n.bl_idname == "ShaderNodeMapRange" and abs(n.inputs["From Min"].default_value - 1500.0) < 1)
    mr.inputs["From Min"].default_value = MID[0]; mr.inputs["From Max"].default_value = MID[1]
    near_del = next(l.to_node for l in mr.outputs[0].links)              # LESS_THAN(rand, p)
    mul = next(l.to_node for l in near_del.outputs[0].links)             # MULTIPLY(cone, ...)
    pos = N.new("GeometryNodeInputPosition"); sp = N.new("ShaderNodeSeparateXYZ"); Lk.new(pos.outputs[0], sp.inputs[0])


    def m(op, a, b=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        return n.outputs[0]


    inbox = m("MULTIPLY", m("MULTIPLY", m("GREATER_THAN", sp.outputs[0], BOX_X[0]), m("LESS_THAN", sp.outputs[0], BOX_X[1])),
              m("MULTIPLY", m("GREATER_THAN", sp.outputs[1], BOX_Y[0]), m("LESS_THAN", sp.outputs[1], BOX_Y[1])))
    gated = m("MULTIPLY", mul.outputs[0], inbox)
    for l in list(mul.outputs[0].links):
        if l.to_node != gated.node:
            to = l.to_socket; Lk.remove(l); Lk.new(gated, to)
    print("[still] boxes: handover", MID, "inside footprint box")



if CITY_RINGS:
    city_rings()
near = bpy.data.objects["S08_NearCity"]

# ---- 3. left mountains higher
him = bpy.data.objects["S01_Himalaya_GLO30"]; me = him.data
co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
Mw = np.array(him.matrix_world); w = co @ Mw[:3, :3].T + Mw[:3, 3]
az = np.degrees(np.arctan2(w[:, 0] - CX, w[:, 1] - CY))
wt = np.clip((-az - 5.0) / 7.0, 0, 1)                                  # 0 at -5 deg, 1 from -12 deg leftwards
k = 1.0 + 0.30 * wt * wt * (3 - 2 * wt)
co[:, 2] = 2000.0 + (co[:, 2] - 2000.0) * np.where(co[:, 2] > 2000.0, k, 1.0)
me.vertices.foreach_set("co", co.ravel()); me.update()
print("[still] left Himalaya raised, max x%.2f" % k.max())

# ---- 4. volumetric clouds - REMOVED by the owner ("remove the volumetric cloud", 2026-11-21) before
# any render; kept switched off for reference
ADD_CLOUDS = False


def add_clouds():
    cl = bpy.data.objects.get("S08_Clouds")
    if cl is None:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cl = bpy.context.active_object; cl.name = "S08_Clouds"
        for c in cl.users_collection:
            c.objects.unlink(cl)
        near.users_collection[0].objects.link(cl)
    cl.location = (CX + 4000.0, CY + 55000.0, 8500.0)
    cl.scale = (90000.0, 60000.0, 2000.0)
    mat = bpy.data.materials.get("M_S08_Clouds") or bpy.data.materials.new("M_S08_Clouds")
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (1.0, 0.97, 0.95, 1.0)
    pv.inputs["Anisotropy"].default_value = 0.55
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sc_v = nt.nodes.new("ShaderNodeVectorMath"); sc_v.operation = "SCALE"; sc_v.inputs["Scale"].default_value = 1 / 6000.0
    nt.links.new(geo.outputs["Position"], sc_v.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "3D"
    nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 8.0; nz.inputs["Roughness"].default_value = 0.58
    nt.links.new(sc_v.outputs[0], nz.inputs["Vector"])
    cov = nt.nodes.new("ShaderNodeMapRange")                              # coverage: only the top of the noise
    cov.inputs["From Min"].default_value = 0.56; cov.inputs["From Max"].default_value = 0.72
    nt.links.new(nz.outputs["Fac"], cov.inputs["Value"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    hprof = nt.nodes.new("ShaderNodeFloatCurve")                           # flat bases, rounded tops
    hz = nt.nodes.new("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 7500.0; hz.inputs["From Max"].default_value = 9500.0
    nt.links.new(sep.outputs["Z"], hz.inputs["Value"]); nt.links.new(hz.outputs[0], hprof.inputs["Value"])
    cv = hprof.mapping.curves[0]
    cv.points[0].location = (0.0, 0.0); cv.points[1].location = (1.0, 0.0)
    cv.points.new(0.08, 1.0); cv.points.new(0.45, 0.8)
    hprof.mapping.update()
    dens = nt.nodes.new("ShaderNodeMath"); dens.operation = "MULTIPLY"
    nt.links.new(cov.outputs[0], dens.inputs[0]); nt.links.new(hprof.outputs[0], dens.inputs[1])
    dk = nt.nodes.new("ShaderNodeMath"); dk.operation = "MULTIPLY"; dk.inputs[1].default_value = 0.0012   # per metre
    nt.links.new(dens.outputs[0], dk.inputs[0]); nt.links.new(dk.outputs[0], pv.inputs["Density"])
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    cl.data.materials.clear(); cl.data.materials.append(mat)
    recv = bpy.data.collections.get("S08_SunReceivers")
    if recv and cl.name not in recv.objects:
        recv.objects.link(cl)                                             # the pink alpenglow lights the clouds too
    print("[still] clouds:", tuple(round(v) for v in cl.location), tuple(round(v) for v in cl.scale))


if ADD_CLOUDS:
    add_clouds()

# ---- 5. still settings
c = sc.cycles
c.samples = 256; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.01
c.volume_max_steps = 512
sc.frame_set(36)
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_finale_v073.blend")
print("[still] saved", bpy.data.filepath)
