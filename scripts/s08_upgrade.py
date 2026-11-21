"""s08 finale pass 2 (owner notes 2026-11-20), run inside the live Blender on s08_finale_v061:
    exec(open(r"E:/Projects/tihar/scripts/s08_upgrade.py", encoding="utf-8").read())

1. Stray lights: S01_LightPoints and the s01 night-ground emission (Voronoi city glow baked in
   the terrain shader) are switched off; every light now hangs on a building, a lamp post or a car.
2. Near city: real OSM footprints within 3.5 km of CAM_S08 (scripts/s08_near_city.py) dressed by
   The City Generator add-on (linked, not appended: its .blend packs 1.4 GB of textures). The
   instanced boxes are cut out of that zone.
3. Tihar lights on the near houses: rope light on each roof parapet + curtain strands from the
   parapet down the walls that face the camera (Kathmandu: "fronts dressed top to bottom").
4. Far boxes: new facade shader (window grid, floor lines, lit windows, grime, roof concrete,
   black/blue tanks, per-house paint) + the same curtain lights; density thinned with distance
   and up the far hill feet.
5. Roads read at dusk through their lights: lamp posts every ~35 m and car lights on the big roads.
6. Water: OSM rivers + ponds (scripts/s08_water.py) as sky-reflecting water.
7. Terrain regrade; alpenglow pinker/brighter; flag lower, further, real fabric; tree smaller.
"""
import math

import bpy
import numpy as np

A = r"E:\Projects\tihar\blender\assets\osm"
CG = r"C:\Users\user\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\user_default\CityGenerator\City_Generator.blend"
CX, CY = 2000.0, -11000.0
NEAR_R, NEAR_ANG = 3500.0, 27.0
COL = bpy.data.objects["S08_Buildings"].users_collection[0]
TERRAIN = bpy.data.objects["S01_Valley_PTerrain"]


# ---------------------------------------------------------------- small node helpers
class NT:
    def __init__(self, tree):
        self.t, self.N, self.L = tree, tree.nodes, tree.links

    def node(self, kind, **kw):
        n = self.N.new(kind)
        for k, v in kw.items():
            if k.startswith("in_"):
                self.set(n.inputs[int(k[3:]) if k[3:].isdigit() else k[3:]], v)
            else:
                setattr(n, k, v)
        return n

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=None, c=None):
        n = self.N.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self.set(n.inputs[i], v)
        return n.outputs[0]

    def vmath(self, op, a, b=None):
        if op == "SCALE_FIX":                 # unit vector * 0.7 m
            n = self.N.new("ShaderNodeVectorMath"); n.operation = "NORMALIZE"; self.set(n.inputs[0], a)
            m = self.N.new("ShaderNodeVectorMath"); m.operation = "SCALE"; self.L.new(n.outputs[0], m.inputs[0])
            m.inputs["Scale"].default_value = 0.7
            return m.outputs[0]
        n = self.N.new("ShaderNodeVectorMath"); n.operation = op
        for i, v in enumerate((a, b)):
            if v is not None:
                self.set(n.inputs[i], v)
        return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.N.new("ShaderNodeMix"); n.data_type = "RGBA"; n.blend_type = blend
        self.set(n.inputs[0], fac); self.set(n.inputs[6], a); self.set(n.inputs[7], b)
        return n.outputs[2]

    def band(self, v, lo, hi):          # 1 inside [lo, hi]
        return self.math("MULTIPLY", self.math("GREATER_THAN", v, lo), self.math("LESS_THAN", v, hi))

    def sep(self, v):
        n = self.N.new("ShaderNodeSeparateXYZ"); self.set(n.inputs[0], v); return n.outputs

    def comb(self, x=0.0, y=0.0, z=0.0):
        n = self.N.new("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self.set(n.inputs[i], v)
        return n.outputs[0]


def ramp(nt, fac, stops, interp="CONSTANT"):
    r = nt.N.new("ShaderNodeValToRGB"); nt.set(r.inputs[0], fac)
    cr = r.color_ramp; cr.interpolation = interp
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for e, (p, c) in zip(cr.elements, stops):
        e.position = p; e.color = (*c, 1.0)
    return r.outputs[0]


# Tihar strings: warm white, marigold, red, blue, green, pink, cool white, multicolour handled per strand
LIGHT_PAL = [(0.0, (1.0, 0.78, 0.45)), (0.22, (1.0, 0.55, 0.12)), (0.36, (1.0, 0.12, 0.08)),
             (0.48, (0.15, 0.35, 1.0)), (0.58, (0.2, 1.0, 0.3)), (0.68, (1.0, 0.25, 0.65)),
             (0.78, (0.85, 0.9, 1.0)), (0.9, (1.0, 0.85, 0.2))]


# ---------------------------------------------------------------- 1. stray lights
def kill_stray_lights():
    lp = bpy.data.objects.get("S01_LightPoints")
    if lp:
        lp.hide_render = lp.hide_viewport = True
    for m in TERRAIN.data.materials:
        t = m.node_tree
        for l in list(t.links):
            if l.to_socket.name == "Emission Color" and l.from_node.type == "GROUP":
                t.links.remove(l)
        bsdf = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Emission Strength"].default_value = 0.0


# ---------------------------------------------------------------- 7a. terrain regrade
def regrade_terrain():
    """Satellite tiles read as grey-lilac plaster: give them back soil/field colour, pull the
    bright urban roofs down (the real houses are on top now) and lose the flat lilac cast."""
    for m in TERRAIN.data.materials:
        nt = NT(m.node_tree)
        hsv = next(n for n in nt.N if n.type == "HUE_SAT")
        hsv.inputs["Saturation"].default_value = 0.62
        hsv.inputs["Value"].default_value = 0.78
        mixn = next(n for n in nt.N if n.type == "MIX" and n.blend_type == "MULTIPLY")
        mixn.inputs[7].default_value = (0.95, 0.84, 0.66, 1.0)
        bsdf = next(n for n in nt.N if n.type == "BSDF_PRINCIPLED")
        if not any(n.label == "S08_Grade" for n in nt.N):
            g = nt.node("ShaderNodeGamma", label="S08_Grade"); g.inputs[1].default_value = 1.3
            nt.L.new(mixn.outputs[2], g.inputs[0]); nt.L.new(g.outputs[0], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.95


# ---------------------------------------------------------------- 2. near city
def near_city():
    d = np.load(A + r"\s08_near.npz")
    bv, bf = d["bv"], d["bf"]
    off = np.concatenate([[0], np.cumsum(bf)])
    cent = np.add.reduceat(bv[:, :2], off[:-1]) / bf[:, None]
    dd = np.hypot(cent[:, 0] - CX, cent[:, 1] - CY)
    ang = np.degrees(np.arctan2(cent[:, 0] - CX, cent[:, 1] - CY))
    sel = np.where((np.abs(ang) < NEAR_ANG) & (dd < NEAR_R) & (dd > 150))[0]
    verts, faces = [], []
    for i in sel:
        p = bv[off[i]:off[i + 1]]; s = len(verts)
        verts += p.tolist(); faces.append(list(range(s, s + len(p))))
    for name in ("S08_NearCity", "S08_NearLights"):
        if name in bpy.data.objects:
            o = bpy.data.objects[name]; me = o.data
            bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("S08_NearCity"); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new("S08_NearCity", me); COL.objects.link(ob)
    if "CityGenerator" not in bpy.data.node_groups:
        with bpy.data.libraries.load(CG, link=True) as (src, dst):
            dst.node_groups = ["CityGenerator"]
    mod = ob.modifiers.new("CityGenerator", "NODES"); mod.node_group = bpy.data.node_groups["CityGenerator"]
    I = mod.properties.inputs
    # Kathmandu: 2-5 storeys, footprint kept exactly as mapped, no fire escapes / scaffolding,
    # a few windows lit (Night Lights), shop ground floors kept
    for k, v in dict(Socket_113=True, Socket_11=2, Socket_12=3, Socket_19=0.0, Socket_25=0.0,
                     Socket_131=0.0, Socket_41=0.0, Socket_134=True, Socket_105=1.0).items():
        getattr(I, k).value = v
    # lights object shares the footprints
    me2 = me.copy(); me2.name = "S08_NearLights"
    lo = bpy.data.objects.new("S08_NearLights", me2); COL.objects.link(lo)
    m = lo.modifiers.new("GN", "NODES"); m.node_group = gn_near_lights(ob)
    return len(sel)


def gn_near_lights(city):
    """Rope light on the parapet + curtain strands down camera-facing walls. Roof height comes
    from a ray cast onto the City Generator's roof slabs (real mesh in its output)."""
    ng = bpy.data.node_groups.get("GN_S08_NearLights") or bpy.data.node_groups.new("GN_S08_NearLights", "GeometryNodeTree")
    ng.nodes.clear()
    if not ng.interface.items_tree:
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    g = NT(ng)
    gi = g.node("NodeGroupInput"); go = g.node("NodeGroupOutput")
    oi = g.node("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = city
    oi.transform_space = "RELATIVE"
    idx = g.node("GeometryNodeInputIndex")
    pos = g.node("GeometryNodeInputPosition")
    # per face: id and roof height
    st_id = g.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="FACE")
    st_id.inputs["Name"].default_value = "fid"
    g.L.new(gi.outputs[0], st_id.inputs[0]); g.L.new(idx.outputs[0], st_id.inputs["Value"])
    rc = g.node("GeometryNodeRaycast")
    g.L.new(oi.outputs["Geometry"], rc.inputs["Target Geometry"])
    g.set(rc.inputs["Source Position"], g.vmath("ADD", pos.outputs[0], (0, 0, 120.0)))
    rc.inputs["Ray Direction"].default_value = (0, 0, -1); rc.inputs["Ray Length"].default_value = 200
    hz = g.sep(rc.outputs["Hit Position"])[2]
    pz = g.sep(pos.outputs[0])[2]
    # miss -> assume 4 storeys
    top = g.math("ADD", g.math("MULTIPLY", rc.outputs["Is Hit"], g.math("SUBTRACT", hz, pz)),
                 g.math("MULTIPLY", g.math("SUBTRACT", 1.0, rc.outputs["Is Hit"]), 12.0))
    st_h = g.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="FACE")
    st_h.inputs["Name"].default_value = "bh"
    g.L.new(st_id.outputs[0], st_h.inputs[0]); g.set(st_h.inputs["Value"], top)
    st_c = g.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT_VECTOR", domain="FACE")
    st_c.inputs["Name"].default_value = "ctr"
    g.L.new(st_h.outputs[0], st_c.inputs[0]); g.L.new(pos.outputs[0], st_c.inputs["Value"])
    split = g.node("GeometryNodeSplitEdges"); g.L.new(st_c.outputs[0], split.inputs[0])
    m2c = g.node("GeometryNodeMeshToCurve"); g.L.new(split.outputs[0], m2c.inputs[0])
    bh = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT"); bh.inputs["Name"].default_value = "bh"
    fid = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT"); fid.inputs["Name"].default_value = "fid"
    # lit houses: 70 %
    rnd_b = g.node("FunctionNodeRandomValue", data_type="FLOAT")
    g.L.new(fid.outputs[0], rnd_b.inputs["ID"]); rnd_b.inputs["Seed"].default_value = 11
    dark = g.math("GREATER_THAN", rnd_b.outputs[0], 0.70)
    del_dark = g.node("GeometryNodeDeleteGeometry", domain="CURVE")
    g.L.new(m2c.outputs[0], del_dark.inputs[0]); g.L.new(dark, del_dark.inputs["Selection"])
    # rope on parapet
    rope_pos = g.node("GeometryNodeSetPosition"); g.L.new(del_dark.outputs[0], rope_pos.inputs[0])
    ctr0 = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT_VECTOR"); ctr0.inputs["Name"].default_value = "ctr"
    rw_ = g.sep(g.vmath("SUBTRACT", pos.outputs[0], ctr0.outputs[0]))
    rn = g.vmath("SCALE_FIX", g.comb(rw_[0], rw_[1], 0.0))
    g.set(rope_pos.inputs["Offset"], g.vmath("ADD", rn, g.comb(z=g.math("ADD", bh.outputs[0], 0.25))))
    rope_r = g.node("GeometryNodeSetCurveRadius"); g.L.new(rope_pos.outputs[0], rope_r.inputs[0])
    rope_r.inputs["Radius"].default_value = 0.05
    # curtain strands every 0.6 m on walls facing the camera
    c2p = g.node("GeometryNodeCurveToPoints"); c2p.mode = "LENGTH"; g.L.new(del_dark.outputs[0], c2p.inputs[0])
    c2p.inputs["Length"].default_value = 0.6
    ctr = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT_VECTOR"); ctr.inputs["Name"].default_value = "ctr"
    outward = g.vmath("SUBTRACT", pos.outputs[0], ctr.outputs[0])      # wall point minus house centre
    tocam = g.vmath("SUBTRACT", (CX, CY, 0.0), pos.outputs[0])
    facing = g.math("LESS_THAN", g.vmath("DOT_PRODUCT", outward, tocam), 0.0)
    rnd_p = g.node("FunctionNodeRandomValue", data_type="FLOAT"); rnd_p.inputs["Seed"].default_value = 5
    gap = g.math("GREATER_THAN", rnd_p.outputs[0], 0.85)               # a few missing strands
    del_back = g.node("GeometryNodeDeleteGeometry", domain="POINT")
    g.L.new(c2p.outputs["Points"], del_back.inputs[0]); g.set(del_back.inputs["Selection"], g.math("MAXIMUM", facing, gap))
    # City Generator trims and balconies stand ~0.5 m proud of the OSM footprint: hang the
    # strings just outside them, not inside the wall
    push = g.node("GeometryNodeSetPosition"); g.L.new(del_back.outputs[0], push.inputs[0])
    ow = g.sep(outward)
    g.set(push.inputs["Offset"], g.vmath("SCALE_FIX", g.comb(ow[0], ow[1], 0.0)))
    del_back = push
    line = g.node("GeometryNodeCurvePrimitiveLine")
    line.inputs["Start"].default_value = (0, 0, 0); line.inputs["End"].default_value = (0, 0, -1)
    res_l = g.node("GeometryNodeResampleCurve"); res_l.inputs["Count"].default_value = 2
    g.L.new(line.outputs[0], res_l.inputs[0])
    rnd_len = g.node("FunctionNodeRandomValue", data_type="FLOAT")
    g.L.new(fid.outputs[0], rnd_len.inputs["ID"]); rnd_len.inputs["Seed"].default_value = 3
    rnd_len.inputs["Min"].default_value = 0.5; rnd_len.inputs["Max"].default_value = 0.97
    length = g.math("MULTIPLY", bh.outputs[0], rnd_len.outputs[0])
    iop = g.node("GeometryNodeInstanceOnPoints")
    g.L.new(del_back.outputs[0], iop.inputs["Points"]); g.L.new(res_l.outputs[0], iop.inputs["Instance"])
    g.set(iop.inputs["Scale"], g.comb(1.0, 1.0, length))
    up = g.node("GeometryNodeTranslateInstances"); g.L.new(iop.outputs[0], up.inputs[0])
    g.set(up.inputs["Translation"], g.comb(z=g.math("ADD", bh.outputs[0], 0.2)))
    up.inputs["Local Space"].default_value = False
    real = g.node("GeometryNodeRealizeInstances"); g.L.new(up.outputs[0], real.inputs[0])
    str_r = g.node("GeometryNodeSetCurveRadius"); g.L.new(real.outputs[0], str_r.inputs[0])
    str_r.inputs["Radius"].default_value = 0.035
    join = g.node("GeometryNodeJoinGeometry")
    g.L.new(str_r.outputs[0], join.inputs[0]); g.L.new(rope_r.outputs[0], join.inputs[0])
    # bare GN curves on a mesh object don't reach Cycles here: make them thin 3-sided tubes
    prof = g.node("GeometryNodeCurvePrimitiveCircle"); prof.inputs["Resolution"].default_value = 3
    prof.inputs["Radius"].default_value = 1.0
    c2m = g.node("GeometryNodeCurveToMesh"); g.L.new(join.outputs[0], c2m.inputs["Curve"])
    g.L.new(prof.outputs[0], c2m.inputs["Profile Curve"])
    g.L.new(g.node("GeometryNodeInputRadius").outputs[0], c2m.inputs["Scale"])
    sm = g.node("GeometryNodeSetMaterial"); g.L.new(c2m.outputs[0], sm.inputs[0])
    sm.inputs["Material"].default_value = mat_tihar_lights()
    g.L.new(sm.outputs[0], go.inputs[0])
    return ng


def mat_tihar_lights():
    m = bpy.data.materials.get("M_S08_TiharLights") or bpy.data.materials.new("M_S08_TiharLights")
    m.use_nodes = True
    t = NT(m.node_tree); t.N.clear()
    out = t.node("ShaderNodeOutputMaterial")
    em = t.node("ShaderNodeEmission")
    fid = t.node("ShaderNodeAttribute", attribute_name="fid")
    wn = t.node("ShaderNodeTexWhiteNoise", noise_dimensions="1D"); t.L.new(fid.outputs["Fac"], wn.inputs["W"])
    house = ramp(t, wn.outputs["Value"], LIGHT_PAL)
    # one house in four: multicolour string, hue walks along the wire
    oc = t.node("ShaderNodeTexCoord")
    p = t.sep(oc.outputs["Object"])
    hue = t.math("FRACT", t.math("MULTIPLY", t.math("ADD", t.math("ADD", p[0], p[1]), p[2]), 2.3))
    hsv = t.node("ShaderNodeCombineColor", mode="HSV"); t.set(hsv.inputs[0], hue)
    hsv.inputs[1].default_value = 0.85; hsv.inputs[2].default_value = 1.0
    multi = t.math("GREATER_THAN", wn.outputs["Value"], 0.75)  # reuse noise, independent enough
    wn2 = t.node("ShaderNodeTexWhiteNoise", noise_dimensions="1D")
    t.L.new(t.math("ADD", fid.outputs["Fac"], 0.37), wn2.inputs["W"])
    col = t.mix(t.math("LESS_THAN", wn2.outputs["Value"], 0.25), house, hsv.outputs[0])
    # bulbs, not a neon tube: dots every ~25 cm along height
    dots = t.math("LESS_THAN", t.math("FRACT", t.math("MULTIPLY", p[2], 4.0)), 0.5)
    t.L.new(col, em.inputs["Color"])
    t.set(em.inputs["Strength"], t.math("MULTIPLY", t.math("ADD", dots, 0.15), 10.0))
    t.L.new(em.outputs[0], out.inputs["Surface"])
    m["s08_note"] = "multicolour Tihar strings (memory: tihar-lights-multicolour)"
    return m


# ---------------------------------------------------------------- 4. far boxes
def far_boxes():
    ng = bpy.data.node_groups["GN_S08_Buildings"]
    g = NT(ng)
    gi = g.N["Group Input"]
    for n in [n for n in g.N if n.name.startswith("S08_")]:
        g.N.remove(n)
    # rebuild: delete near-zone points + thin with distance / altitude
    first = [l for l in g.L if l.from_node == gi]
    for n in list(g.N):
        if n.type == "DELETE_GEOMETRY":
            for l in list(g.L):
                if l.from_node == n:
                    g.L.new(gi.outputs[0], l.to_socket)
            g.N.remove(n)
    pos = g.node("GeometryNodeInputPosition", name="S08_Pos")
    s = g.sep(pos.outputs[0])
    dx = g.math("SUBTRACT", s[0], CX); dy = g.math("SUBTRACT", s[1], CY)
    dist = g.math("SQRT", g.math("ADD", g.math("MULTIPLY", dx, dx), g.math("MULTIPLY", dy, dy)))
    near = g.math("MULTIPLY", g.math("LESS_THAN", dist, NEAR_R),
                  g.math("LESS_THAN", g.math("ABSOLUTE", dx), g.math("MULTIPLY", dy, math.tan(math.radians(NEAR_ANG)))))
    far_thin = g.math("MULTIPLY", g.node("ShaderNodeMapRange", in_0=dist, in_1=13000.0, in_2=26000.0, in_3=0.0, in_4=0.55).outputs[0], 1.0)
    hill_thin = g.node("ShaderNodeMapRange", in_0=s[2], in_1=1350.0, in_2=1480.0, in_3=0.0, in_4=0.6).outputs[0]
    pdel = g.math("MINIMUM", g.math("ADD", far_thin, hill_thin), 0.85)
    rnd = g.node("FunctionNodeRandomValue", data_type="FLOAT", name="S08_Rnd"); rnd.inputs["Seed"].default_value = 21
    sel = g.math("MAXIMUM", near, g.math("LESS_THAN", rnd.outputs[0], pdel))
    dl = g.node("GeometryNodeDeleteGeometry", name="S08_Delete", domain="POINT")
    g.L.new(gi.outputs[0], dl.inputs[0]); g.set(dl.inputs["Selection"], sel)
    for l in list(g.L):
        if l.from_node == gi and l.to_node != dl:
            to = l.to_socket; g.L.remove(l); g.L.new(dl.outputs[0], to)
    # mark tank instances for the shader
    tank_store = g.N["Store Named Attribute.001"]
    st = g.node("GeometryNodeStoreNamedAttribute", name="S08_TankFlag", data_type="FLOAT", domain="INSTANCE")
    st.inputs["Name"].default_value = "istank"; st.inputs["Value"].default_value = 1.0
    for l in list(g.L):
        if l.from_node == tank_store:
            to = l.to_socket; g.L.remove(l); g.L.new(st.outputs[0], to)
    g.L.new(tank_store.outputs[0], st.inputs[0])
    mat_far_building()


def mat_far_building():
    m = bpy.data.materials["M_S08_Building"]
    t = NT(m.node_tree); t.N.clear()
    out = t.node("ShaderNodeOutputMaterial")
    bs = t.node("ShaderNodeBsdfPrincipled")
    t.L.new(bs.outputs[0], out.inputs["Surface"])
    tc = t.node("ShaderNodeTexCoord"); p = t.sep(tc.outputs["Object"])
    oi = t.node("ShaderNodeObjectInfo")
    r1 = oi.outputs["Random"]
    sc = t.node("ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="bscale")
    S = t.sep(sc.outputs["Vector"])
    bcol = t.node("ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="bcol")
    tank = t.node("ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="istank")
    geo = t.node("ShaderNodeNewGeometry")
    nz = t.sep(geo.outputs["Normal"])[2]
    roof = t.math("GREATER_THAN", nz, 0.5)
    side = t.math("SUBTRACT", 1.0, roof)
    # metres along the wall / up the wall
    u = t.math("ADD", t.math("MULTIPLY", p[0], S[0]), t.math("MULTIPLY", p[1], S[1]))
    zw = t.math("MULTIPLY", p[2], S[2])
    fu = t.math("FRACT", t.math("DIVIDE", u, 2.7)); fz = t.math("FRACT", t.math("DIVIDE", zw, 3.0))
    win = t.math("MULTIPLY", t.math("MULTIPLY", t.band(fu, 0.24, 0.74), t.band(fz, 0.30, 0.80)),
                 t.math("MULTIPLY", side, t.math("GREATER_THAN", zw, 2.8)))
    slab = t.math("MULTIPLY", t.math("LESS_THAN", fz, 0.07), side)
    # per-cell random for lit windows
    cell = t.comb(t.math("FLOOR", t.math("DIVIDE", u, 2.7)), t.math("FLOOR", t.math("DIVIDE", zw, 3.0)),
                  t.math("MULTIPLY", r1, 977.0))
    wn = t.node("ShaderNodeTexWhiteNoise", noise_dimensions="3D"); t.L.new(cell, wn.inputs["Vector"])
    lit = t.math("MULTIPLY", win, t.math("LESS_THAN", wn.outputs["Value"], 0.22))
    # paint: owner palette per house, darker overall (no white plaster blocks), grime at the foot
    paint = t.mix(1.0, bcol.outputs["Color"], (0.78, 0.76, 0.74, 1.0), "MULTIPLY")
    var = t.node("ShaderNodeMapRange", in_0=r1, in_3=0.55, in_4=1.0).outputs[0]
    paint = t.mix(1.0, paint, t.comb(var, var, var), "MULTIPLY")
    grime = t.node("ShaderNodeMapRange", in_0=p[2], in_1=0.0, in_2=0.5, in_3=0.55, in_4=0.0).outputs[0]
    paint = t.mix(grime, paint, (0.18, 0.16, 0.14, 1.0))
    paint = t.mix(slab, paint, (0.35, 0.34, 0.33, 1.0))
    wall = t.mix(win, paint, (0.025, 0.03, 0.035, 1.0))
    nz_r = t.node("ShaderNodeTexNoise"); nz_r.inputs["Scale"].default_value = 3.0; t.L.new(tc.outputs["Object"], nz_r.inputs["Vector"])
    roofc = t.mix(nz_r.outputs["Fac"], (0.20, 0.19, 0.18, 1.0), (0.34, 0.33, 0.31, 1.0))
    col = t.mix(roof, wall, roofc)
    tankc = t.mix(t.math("GREATER_THAN", r1, 0.5), (0.02, 0.02, 0.025, 1.0), (0.04, 0.09, 0.22, 1.0))
    col = t.mix(tank.outputs["Fac"], col, tankc)
    t.L.new(col, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.85
    # --- Tihar lights, built like the near houses' real strings (owner 2026-11-20: "make the
    # light for overall viewable city same as near building lights"): 70 % of houses, rope
    # light round the roof edge, curtain strands every 0.6 m (12 % wide, = the near tubes)
    # down the walls that face the camera, 50 % bulb duty every 25 cm + 0.15 glow, strength 10
    wn_b = t.node("ShaderNodeTexWhiteNoise", noise_dimensions="1D")
    t.L.new(t.math("MULTIPLY", r1, 311.0), wn_b.inputs["W"])
    hl = t.math("LESS_THAN", wn_b.outputs["Value"], 0.70)
    tocam = t.vmath("NORMALIZE", t.vmath("SUBTRACT", (CX, CY, 2002.0), geo.outputs["Position"]))
    wface = t.math("GREATER_THAN", t.vmath("DOT_PRODUCT", geo.outputs["Normal"], tocam), 0.05)
    strand = t.math("LESS_THAN", t.math("FRACT", t.math("DIVIDE", u, 0.6)), 0.12)
    lenf = t.node("ShaderNodeMapRange", in_0=t.math("FRACT", t.math("MULTIPLY", r1, 53.0)), in_3=0.5, in_4=0.97).outputs[0]
    within = t.math("GREATER_THAN", p[2], t.math("SUBTRACT", 1.0, lenf))
    bulbs = t.math("ADD", t.math("LESS_THAN", t.math("FRACT", t.math("DIVIDE", zw, 0.25)), 0.5), 0.15)
    curtain = t.math("MULTIPLY", t.math("MULTIPLY", t.math("MULTIPLY", strand, within), bulbs),
                     t.math("MULTIPLY", t.math("MULTIPLY", hl, wface), side))
    # rope: last 0.12 m of the wall top + 0.08 m band round the roof edge (= the near rope tube)
    ex = t.math("MULTIPLY", t.math("SUBTRACT", 0.5, t.math("ABSOLUTE", p[0])), S[0])
    ey = t.math("MULTIPLY", t.math("SUBTRACT", 0.5, t.math("ABSOLUTE", p[1])), S[1])
    redge = t.math("MULTIPLY", roof, t.math("LESS_THAN", t.math("MINIMUM", ex, ey), 0.08))
    wtop = t.math("MULTIPLY", side, t.math("GREATER_THAN", zw, t.math("SUBTRACT", S[2], 0.12)))
    rope = t.math("MULTIPLY", t.math("MAXIMUM", redge, wtop), t.math("MULTIPLY", hl, 1.15))
    nott = t.math("SUBTRACT", 1.0, tank.outputs["Fac"])
    tihar = t.math("MULTIPLY", t.math("MAXIMUM", curtain, rope), nott)
    house = ramp(t, wn_b.outputs["Value"], LIGHT_PAL)
    hue = t.math("FRACT", t.math("MULTIPLY", t.math("ADD", t.math("ADD", u, zw), 0.0), 2.3 / 3.0))
    hsv = t.node("ShaderNodeCombineColor", mode="HSV"); t.set(hsv.inputs[0], hue)
    hsv.inputs[1].default_value = 0.85; hsv.inputs[2].default_value = 1.0
    lcol = t.mix(t.math("LESS_THAN", t.math("FRACT", t.math("MULTIPLY", r1, 17.0)), 0.25), house, hsv.outputs[0])
    wcol = (1.0, 0.68, 0.38, 1.0)
    ecol = t.mix(t.math("GREATER_THAN", tihar, 0.0), wcol, lcol)
    lit = t.math("MULTIPLY", lit, t.math("LESS_THAN", wn.outputs["Value"], 0.15 / 0.22))
    estr = t.math("ADD", t.math("MULTIPLY", tihar, 2.2), t.math("MULTIPLY", lit, 1.5))   # sub-pixel houses average brighter than the near tubes
    t.L.new(ecol, bs.inputs["Emission Color"])
    t.L.new(estr, bs.inputs["Emission Strength"])
    estr.node.label = "S08_LightStrength"


# ---------------------------------------------------------------- 5. road lights
def mat_emit(name, col, strength):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    t = NT(m.node_tree); t.N.clear()
    o = t.node("ShaderNodeOutputMaterial"); e = t.node("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*col, 1.0); e.inputs["Strength"].default_value = strength
    t.L.new(e.outputs[0], o.inputs["Surface"])
    return m


def road_lights():
    """Lamp posts every ~35 m (warm sodium on old roads, cool LED on the ring road) and car
    head/tail lights on trunk/primary roads. Points, so Cycles renders them as tiny spheres."""
    ng = bpy.data.node_groups.get("GN_S08_RoadLights") or bpy.data.node_groups.new("GN_S08_RoadLights", "GeometryNodeTree")
    ng.nodes.clear()
    if not ng.interface.items_tree:
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    g = NT(ng)
    gi = g.node("NodeGroupInput"); go = g.node("NodeGroupOutput")
    m2c = g.node("GeometryNodeMeshToCurve"); g.L.new(gi.outputs[0], m2c.inputs[0])
    rw = g.node("GeometryNodeInputNamedAttribute", data_type="FLOAT"); rw.inputs["Name"].default_value = "rw"
    join = g.node("GeometryNodeJoinGeometry")

    def pts(spacing, z, radius, mat, seed, keep, min_w=0.0, side=0.0):
        c2p = g.node("GeometryNodeCurveToPoints"); c2p.mode = "LENGTH"
        c2p.inputs["Length"].default_value = spacing; g.L.new(m2c.outputs[0], c2p.inputs[0])
        rnd = g.node("FunctionNodeRandomValue", data_type="FLOAT"); rnd.inputs["Seed"].default_value = seed
        drop = g.math("MAXIMUM", g.math("GREATER_THAN", rnd.outputs[0], keep), g.math("LESS_THAN", rw.outputs[0], min_w))
        dl = g.node("GeometryNodeDeleteGeometry", domain="POINT"); g.L.new(c2p.outputs["Points"], dl.inputs[0])
        g.set(dl.inputs["Selection"], drop)
        ts = g.sep(c2p.outputs["Tangent"])
        off = g.comb(g.math("MULTIPLY", ts[1], side), g.math("MULTIPLY", ts[0], -side), 0.0)
        sp = g.node("GeometryNodeSetPosition"); g.L.new(dl.outputs[0], sp.inputs[0])
        g.set(sp.inputs["Offset"], g.vmath("ADD", off, (0, 0, z)))
        r = g.node("GeometryNodeSetPointRadius"); g.L.new(sp.outputs[0], r.inputs[0]); r.inputs["Radius"].default_value = radius
        sm = g.node("GeometryNodeSetMaterial"); g.L.new(r.outputs[0], sm.inputs[0]); sm.inputs["Material"].default_value = mat
        g.L.new(sm.outputs[0], join.inputs[0])

    pts(40.0, 8.0, 0.25, mat_emit("M_S08_LampSodium", (1.0, 0.55, 0.2), 14.0), 1, 0.4)
    pts(40.0, 8.0, 0.25, mat_emit("M_S08_LampLED", (0.85, 0.9, 1.0), 10.0), 2, 0.15)
    pts(55.0, 0.8, 0.35, mat_emit("M_S08_CarHead", (1.0, 0.92, 0.75), 18.0), 3, 0.45, 9.5, -1.6)
    pts(55.0, 0.8, 0.35, mat_emit("M_S08_CarTail", (1.0, 0.05, 0.02), 14.0), 4, 0.45, 9.5, 1.6)
    g.L.new(join.outputs[0], go.inputs[0])
    for name in ("S08_Roads", "S08_NearStreets"):
        o = bpy.data.objects.get(name)
        if o and not any(m.name == "S08_RoadLights" for m in o.modifiers):
            # lights from the centreline mesh: put this modifier FIRST on a copy
            lo = bpy.data.objects.get(name + "Lights")
            if lo is None:
                lo = bpy.data.objects.new(name + "Lights", o.data); COL.objects.link(lo)
            for m in list(lo.modifiers):
                lo.modifiers.remove(m)
            mm = lo.modifiers.new("S08_RoadLights", "NODES"); mm.node_group = ng


def near_streets():
    d = np.load(A + r"\s08_near.npz")
    sv, sw, swid = d["sv"], d["sw"], d["swid"]
    off = np.concatenate([[0], np.cumsum(sw)])
    edges, rw = [], np.zeros(len(sv), np.float32)
    for i in range(len(sw)):
        a, b = off[i], off[i + 1]
        edges += [(j, j + 1) for j in range(a, b - 1)]
        rw[a:b] = swid[i]
    if "S08_NearStreets" in bpy.data.objects:
        o = bpy.data.objects["S08_NearStreets"]; me = o.data
        bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("S08_NearStreets"); me.from_pydata(sv.tolist(), edges, []); me.update()
    at = me.attributes.new("rw", "FLOAT", "POINT"); at.data.foreach_set("value", rw)
    o = bpy.data.objects.new("S08_NearStreets", me); COL.objects.link(o)
    m = o.modifiers.new("GN", "NODES"); m.node_group = bpy.data.node_groups["GN_S08_Roads"]


# ---------------------------------------------------------------- 6. water
def water():
    d = np.load(A + r"\s08_water.npz")
    lv, ln, lw, pv, pn = d["lv"], d["ln"], d["lw"], d["pv"], d["pn"]
    mw = bpy.data.materials.get("M_S08_Water") or bpy.data.materials.new("M_S08_Water")
    mw.use_nodes = True
    t = NT(mw.node_tree); t.N.clear()
    o = t.node("ShaderNodeOutputMaterial"); b = t.node("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.03, 0.035, 0.03, 1.0)
    b.inputs["Roughness"].default_value = 0.14; b.inputs["IOR"].default_value = 1.33
    b.inputs["Specular IOR Level"].default_value = 0.3
    nz = t.node("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 6
    bump = t.node("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
    t.L.new(nz.outputs["Fac"], bump.inputs["Height"]); t.L.new(bump.outputs[0], b.inputs["Normal"])
    t.L.new(b.outputs[0], o.inputs["Surface"])
    # river ribbons: reuse the road ribbon tree with the water material
    old = bpy.data.node_groups.get("GN_S08_Water")
    if old:
        bpy.data.node_groups.remove(old)
    rg = bpy.data.node_groups["GN_S08_Roads"].copy(); rg.name = "GN_S08_Water"
    next(n for n in rg.nodes if n.type == "SET_MATERIAL").inputs["Material"].default_value = mw
    # drape on the rendered terrain (the river DSM differs from PTerrain by a few metres)
    g = NT(rg)
    sp = next(n for n in rg.nodes if n.type == "SET_POSITION")
    oi = g.node("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = TERRAIN; oi.transform_space = "RELATIVE"
    pos = g.node("GeometryNodeInputPosition")
    rc = g.node("GeometryNodeRaycast"); g.L.new(oi.outputs["Geometry"], rc.inputs["Target Geometry"])
    s = g.sep(pos.outputs[0])
    g.set(rc.inputs["Source Position"], g.comb(s[0], s[1], 4000.0))
    rc.inputs["Ray Direction"].default_value = (0, 0, -1); rc.inputs["Ray Length"].default_value = 5000
    hz = g.sep(rc.outputs["Hit Position"])[2]
    sp2 = g.node("GeometryNodeSetPosition")
    g.set(sp2.inputs["Position"], g.comb(s[0], s[1], g.math("ADD", hz, 0.8)))
    g.set(sp2.inputs["Selection"], rc.outputs["Is Hit"])
    lk = next(l for l in rg.links if l.from_node == sp)
    to = lk.to_socket; rg.links.remove(lk)
    g.L.new(sp.outputs[0], sp2.inputs[0]); g.L.new(sp2.outputs[0], to)
    off = np.concatenate([[0], np.cumsum(ln)])
    edges, rw = [], np.zeros(len(lv), np.float32)
    for i in range(len(ln)):
        a, b2 = off[i], off[i + 1]
        edges += [(j, j + 1) for j in range(a, b2 - 1)]
        rw[a:b2] = lw[i] * 0.35          # Nov: the water is a thin thread in a wide bed
    poff = np.concatenate([[0], np.cumsum(pn)]) + len(lv)
    faces = [list(range(poff[i], poff[i + 1])) for i in range(len(pn))]
    verts = np.concatenate([lv, pv])
    for name in ("S08_Rivers", "S08_Ponds"):
        if name in bpy.data.objects:
            ob = bpy.data.objects[name]; me = ob.data
            bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("S08_Rivers"); me.from_pydata(lv.tolist(), edges, []); me.update()
    at = me.attributes.new("rw", "FLOAT", "POINT"); at.data.foreach_set("value", rw)
    ob = bpy.data.objects.new("S08_Rivers", me); COL.objects.link(ob)
    ob.modifiers.new("GN", "NODES").node_group = rg
    pv2 = pv.copy()
    pof = np.concatenate([[0], np.cumsum(pn)])
    me = bpy.data.meshes.new("S08_Ponds")
    me.from_pydata(pv2.tolist(), [], [list(range(pof[i], pof[i + 1])) for i in range(len(pn))]); me.update()
    me.materials.append(mw)
    ob = bpy.data.objects.new("S08_Ponds", me); COL.objects.link(ob)
    # ponds: lift each to the terrain with a tiny GN (raycast per vertex, +0.6 m)
    pg = bpy.data.node_groups.get("GN_S08_Drape") or bpy.data.node_groups.new("GN_S08_Drape", "GeometryNodeTree")
    pg.nodes.clear()
    if not pg.interface.items_tree:
        pg.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        pg.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    q = NT(pg)
    gi = q.node("NodeGroupInput"); go = q.node("NodeGroupOutput")
    oi = q.node("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = TERRAIN; oi.transform_space = "RELATIVE"
    pos = q.node("GeometryNodeInputPosition"); s = q.sep(pos.outputs[0])
    rc = q.node("GeometryNodeRaycast"); q.L.new(oi.outputs["Geometry"], rc.inputs["Target Geometry"])
    q.set(rc.inputs["Source Position"], q.comb(s[0], s[1], 4000.0))
    rc.inputs["Ray Direction"].default_value = (0, 0, -1); rc.inputs["Ray Length"].default_value = 5000
    sp = q.node("GeometryNodeSetPosition"); q.L.new(gi.outputs[0], sp.inputs[0])
    q.set(sp.inputs["Position"], q.comb(s[0], s[1], q.math("ADD", q.sep(rc.outputs["Hit Position"])[2], 0.6)))
    q.set(sp.inputs["Selection"], rc.outputs["Is Hit"])
    q.L.new(sp.outputs[0], go.inputs[0])
    ob.modifiers.new("GN", "NODES").node_group = pg


# ---------------------------------------------------------------- 7b. alpenglow
def alpenglow():
    """Owner photos: peaks glow salmon-pink, almost clipping, against a cool grey-blue sky."""
    L = bpy.data.objects["S08_L_Alpenglow"].data
    L.color = (1.0, 0.38, 0.28)
    L.energy = 160.0


# ---------------------------------------------------------------- 7c. flag + tree
def flag_and_tree():
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    from mathutils import Vector

    hill = bpy.data.objects["S08_Hill"]
    hmi = hill.matrix_world.inverted()

    def ground(x, y):        # the hill mesh only (grass, tree and flag would stop a scene ray)
        hit = hill.ray_cast(hmi @ Vector((x, y, 3000)), (hmi.to_3x3() @ Vector((0, 0, -1))).normalized())
        return (hill.matrix_world @ hit[1]).z
    pole = bpy.data.objects["S08_FlagPole"]; flag = bpy.data.objects["S08_Flag"]
    # 16 m out on the slope, right third; flag top ~28 % below the frame top
    px, py = CX + 5.0, CY + 16.0
    gz = ground(px, py)
    top = 2002.0 + 16.0 * math.tan(math.radians(0.75))
    d = Vector((px, py, 0)) - Vector((pole.location.x, pole.location.y, 0))
    hgt = top + 0.1 - gz
    pole_h0 = pole.dimensions.z
    # pole: bottom at the ground, scaled to height; flag keeps its offset to the pole top
    fl_off = flag.location - (pole.location + Vector((0, 0, pole_h0 / 2)))
    pole.scale.z *= hgt / pole_h0
    pole.location = (px, py, gz + hgt / 2)
    flag.location = Vector((px, py, gz + hgt)) + fl_off
    print("flag: ground", round(gz, 2), "pole", round(hgt, 2), "m")
    # tree: 0.8x, trunk at the left frame edge ~15 m out so the crown reads inside the frame
    tr = bpy.data.objects["S08_Tree"]
    tr.scale = tuple(v * 0.8 for v in tr.scale)
    tx, ty = CX - 5.6, CY + 15.0
    gzt = ground(tx, ty)
    bpy.context.view_layer.update()
    low = min((tr.matrix_world @ Vector(c)).z for c in tr.bound_box) - tr.location.z
    tr.location = (tx, ty, gzt - 0.3 - low)


def flag_material():
    m = bpy.data.materials["M_S08_Flag"]
    t = NT(m.node_tree)
    bs = next(n for n in t.N if n.type == "BSDF_PRINCIPLED")
    img = next(n for n in t.N if n.type == "TEX_IMAGE")
    if any(n.label == "S08_Fabric" for n in t.N):
        return
    # cotton bunting: weave bump, sheen, light through the cloth, slightly faded dye
    tc = t.node("ShaderNodeTexCoord")
    wave = t.node("ShaderNodeTexWave", label="S08_Fabric"); wave.inputs["Scale"].default_value = 260.0
    wave.inputs["Distortion"].default_value = 0.5; t.L.new(tc.outputs["UV"], wave.inputs["Vector"])
    wave2 = t.node("ShaderNodeTexWave"); wave2.bands_direction = "Y"; wave2.inputs["Scale"].default_value = 260.0
    t.L.new(tc.outputs["UV"], wave2.inputs["Vector"])
    h = t.math("MULTIPLY", wave.outputs["Fac"], wave2.outputs["Fac"])
    bump = t.node("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
    t.set(bump.inputs["Height"], h); t.L.new(bump.outputs[0], bs.inputs["Normal"])
    hsv = t.node("ShaderNodeHueSaturation"); hsv.inputs["Saturation"].default_value = 0.85
    hsv.inputs["Value"].default_value = 0.8
    lk = next(l for l in t.L if l.to_socket == bs.inputs["Base Color"])
    t.L.remove(lk); t.L.new(img.outputs["Color"], hsv.inputs["Color"]); t.L.new(hsv.outputs[0], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.9
    bs.inputs["Sheen Weight"].default_value = 0.6
    bs.inputs["Sheen Roughness"].default_value = 0.4
    bs.inputs["Transmission Weight"].default_value = 0.0
    bs.inputs["Subsurface Weight"].default_value = 0.15
    bs.inputs["Thin Wall"].default_value = True


def rebake_flag():
    flag = bpy.data.objects["S08_Flag"]
    cm = next(m for m in flag.modifiers if m.type == "CLOTH")
    # finer, heavier cotton so it ripples instead of floating like plastic
    cm.settings.quality = 12
    cm.settings.mass = 0.25
    cm.settings.air_damping = 1.5
    with bpy.context.temp_override(point_cache=cm.point_cache, active_object=flag, object=flag):
        bpy.ops.ptcache.free_bake()
        bpy.ops.ptcache.bake(bake=True)


def himalaya_pink():
    """Owner photos: summits salmon-pink and glowing, ridges below already in shade. The sky
    light alone keeps the snow cream-white, so the snow above ~4,700 m is tinted salmon by
    altitude and given a faint glow (summits only)."""
    m = bpy.data.materials["M_S01_Himalaya"]; t = m.node_tree; N = t.nodes; L = t.links
    if any(n.label == "S08_Alpenglow" for n in N):
        return
    bs = N["Principled BSDF"]; snow = N["Math.002"].outputs[0]; att = N["Attribute"].outputs["Fac"]
    for l in list(L):
        if l.to_socket == bs.inputs["Emission Color"]:
            L.remove(l)
    mr = N.new("ShaderNodeMapRange"); mr.label = "S08_Alpenglow"
    L.new(att, mr.inputs[0]); mr.inputs[1].default_value = 4300; mr.inputs[2].default_value = 6500
    mr.inputs[3].default_value = 0.5; mr.inputs[4].default_value = 1.0
    k = N.new("ShaderNodeMath"); k.operation = "MULTIPLY"; L.new(snow, k.inputs[0]); L.new(mr.outputs[0], k.inputs[1])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
    # rock above the line takes the light too (else the lower snow reads yellow-green)
    L.new(mr.outputs[0], mx.inputs[0]); L.new(N["Mix.005"].outputs[2], mx.inputs[6]); mx.inputs[7].default_value = (1.0, 0.42, 0.28, 1)
    L.new(mx.outputs[2], bs.inputs["Base Color"])
    bs.inputs["Emission Color"].default_value = (1.0, 0.38, 0.24, 1)
    e = N.new("ShaderNodeMath"); e.operation = "MULTIPLY"; L.new(k.outputs[0], e.inputs[0]); e.inputs[1].default_value = 0.9
    L.new(e.outputs[0], bs.inputs["Emission Strength"])
    N["Mix.002"].inputs[7].default_value = (0.95, 0.9, 0.88, 1)   # snow was blue-white
    # never let Cycles treat the glowing 30 m mesh as millions of lights (out of GPU memory)
    m.cycles.emission_sampling = "NONE"


def run():
    kill_stray_lights()
    regrade_terrain()
    n = near_city()
    near_streets()
    far_boxes()
    road_lights()
    water()
    alpenglow()
    himalaya_pink()
    flag_material()
    flag_and_tree()
    rebake_flag()
    print("[s08u] near footprints:", n)


run()
