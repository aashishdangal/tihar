# s07: the two malas for Jamuna's thali.
#  - S07_Sayapatri: the s04 marigold mala (S04_Mala curve + S04_Mala_GN + S04_Mala_Heads, appended
#    from blender/assets/s04_hand/hand_props_v001.blend), its curve redrawn as a garland lying in a
#    crescent round the far side of the plate.
#  - S07_Makhamali: globe-amaranth (makhamali) heads built here (papery magenta bracts on an ovoid,
#    two green leafy bracts at the base), strung by a copy of the same GN, crescent on the near side.
# Run inside s07_bhaitika_vNNN.blend after the S07_Sayapatri append (MCP exec).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

PLATE = Vector((1.5, 1.2, 0.0))
FLOOR_Z = 0.004                       # plate floor top
VIEW = Vector((0.8, -0.6, 0)).normalized()     # camera side of the plate
SIDE = Vector((-VIEW.y, VIEW.x, 0))


def find_lc(name, lc=None):
    lc = lc or bpy.context.view_layer.layer_collection
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find_lc(name, ch)
        if r: return r


def source_collection(col):
    """Instance sources must be in the scene but excluded (a hidden one stops Collection Info)."""
    sc = bpy.context.scene.collection
    if col.name not in sc.children: sc.children.link(col)
    find_lc(col.name).exclude = True


def crescent(curve_ob, r_out, r_in, centre_dir, span_deg, z, n=64):
    """Closed loop: outer arc, round end, inner arc back, round end - a garland laid in a crescent."""
    a0 = math.atan2(centre_dir.y, centre_dir.x)
    half = math.radians(span_deg) / 2
    pts = []
    k = n // 2
    for i in range(k):                                    # outer arc
        a = a0 - half + 2 * half * i / (k - 1)
        pts.append(Vector((r_out * math.cos(a), r_out * math.sin(a), 0)))
    for i in range(k):                                    # inner arc, back
        a = a0 + half - 2 * half * i / (k - 1)
        pts.append(Vector((r_in * math.cos(a), r_in * math.sin(a), 0)))
    cu = curve_ob.data
    if cu.shape_keys:
        curve_ob.shape_key_clear()
    cu.splines.clear(); cu.dimensions = "3D"
    sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1)
    rnd = random.Random(5)
    for p, co in zip(sp.points, pts):
        j = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.004    # slack, not a perfect ring
        p.co = (*(co + j), 1.0)
    sp.use_cyclic_u = True; sp.order_u = 3; sp.resolution_u = 8
    curve_ob.parent = None
    curve_ob.matrix_world = Matrix.Translation((PLATE.x, PLATE.y, z))
    length = sum((pts[i] - pts[i - 1]).length for i in range(len(pts)))
    return length


# ---------------------------------------------------------------- sayapatri (s04 marigold mala)
say = bpy.data.objects["S07_Sayapatri"]
source_collection(bpy.data.collections["S04_Mala_Heads"])
L_say = crescent(say, 0.190, 0.148, -SIDE - VIEW * 0.15, 125, FLOOR_Z + 0.020)   # left rim
md = say.modifiers["S04_Mala_GN"]
heads_d = 0.036                                         # marigold heads ~4 cm, packed tight
md.properties.inputs.Socket_41.value = int(L_say / heads_d)
md.properties.inputs.Socket_43.value = 0.85
print("sayapatri length %.2f m, heads %d" % (L_say, int(L_say / heads_d)))


# ---------------------------------------------------------------- makhamali heads
def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mat_makhamali():
    m = bpy.data.materials.get("S07_Makhamali") or bpy.data.materials.new("S07_Makhamali")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled")
    at = N("ShaderNodeAttribute"); at.attribute_name = "bract_v"          # 0 base .. 1 tip of each bract
    ar = N("ShaderNodeAttribute"); ar.attribute_name = "bract_rand"
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (*lin("#6A0F55"), 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (*lin("#D8459E"), 1)
    e = ramp.color_ramp.elements.new(0.85); e.color = (*lin("#B72A86"), 1)
    L(at.outputs["Fac"], ramp.inputs["Fac"])
    hsv = N("ShaderNodeHueSaturation")
    mr = N("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.8; mr.inputs["To Max"].default_value = 1.15
    L(ar.outputs["Fac"], mr.inputs["Value"]); L(mr.outputs["Result"], hsv.inputs["Value"])
    L(ramp.outputs["Color"], hsv.inputs["Color"]); L(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45                             # papery, faint sheen
    b.inputs["Sheen Weight"].default_value = 0.4
    b.inputs["Subsurface Weight"].default_value = 0.3
    b.inputs["Subsurface Radius"].default_value = (0.003, 0.0008, 0.002)
    b.inputs["Transmission Weight"].default_value = 0.1                    # thin bracts let light through
    L(b.outputs[0], out.inputs["Surface"])
    return m


def mat_leaf():
    m = bpy.data.materials.get("S07_MakhamaliLeaf") or bpy.data.materials.new("S07_MakhamaliLeaf")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*lin("#3E5A1F"), 1); b.inputs["Roughness"].default_value = 0.55
    b.inputs["Subsurface Weight"].default_value = 0.15
    return m


M_MK, M_LEAF = mat_makhamali(), mat_leaf()
RX, RZ = 0.0085, 0.0105        # head: ~17 mm across, ~21 mm long (thread runs along Z)


def bract(bm, M, w, l, lay_v, lay_r, pr):
    """one papery bract: pointed, slightly cupped scale. local Y = length, Z = outward."""
    nu, nv = 4, 5
    grid = []
    for j in range(nv):
        v = j / (nv - 1)
        row = []
        for i in range(nu):
            s = i / (nu - 1) * 2 - 1
            wid = w * math.sin(math.pi * min(1.0, 0.15 + v * 0.95)) * (1 - v * 0.6)
            x = s * wid / 2
            y = v * l
            z = 0.25 * w * s * s + 0.15 * l * v * v
            row.append(bm.verts.new(M @ Vector((x, y, z))))
        grid.append(row)
    for j in range(nv - 1):
        for i in range(nu - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    for j in range(nv):
        for i in range(nu):
            lay_v[grid[j][i]] = j / (nv - 1); lay_r[grid[j][i]] = pr


def makhamali(name, seed):
    rnd = random.Random(seed)
    bm = bmesh.new()
    lv = bm.verts.layers.float.new("bract_v"); lr = bm.verts.layers.float.new("bract_rand")
    mv, mr = {}, {}
    n = 360; ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        f = (i + 0.5) / n
        th = math.acos(1 - 2 * f * 0.92)                         # leave the stalk end bare
        ph = i * ga + rnd.uniform(-0.2, 0.2)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        base = Vector((d.x * RX, d.y * RX, d.z * RZ)) * 0.9
        nrm = Vector((d.x / RX, d.y / RX, d.z / RZ)).normalized()
        up = Vector((0, 0, 1))
        y = (up - nrm * up.dot(nrm))                                # bracts point toward the tip (+Z)
        y = (y.normalized() if y.length > 1e-4 else Vector((1, 0, 0)))
        y = (y * 0.92 + nrm * 0.18).normalized()                    # lie close: tight papery ball
        z = (nrm - y * nrm.dot(y)).normalized(); x = y.cross(z)
        rot = Matrix((x, y, z)).transposed() @ Matrix.Rotation(rnd.uniform(-0.3, 0.3), 3, "Z")
        l = 0.0036 * rnd.uniform(0.85, 1.15); w = l * rnd.uniform(1.0, 1.25)
        bract(bm, Matrix.Translation(base) @ rot.to_4x4(), w, l, mv, mr, rnd.random())
    for v, val in mv.items(): v[lv] = val
    for v, val in mr.items(): v[lr] = val
    ret = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)   # core
    for v in ret["verts"]:
        v.co = Vector((v.co.x * RX * 0.85, v.co.y * RX * 0.85, v.co.z * RZ * 0.85))
        v[lv] = 0.0; v[lr] = 0.5
    core = {f for v in ret["verts"] for f in v.link_faces}
    nf_before = len(bm.faces)
    for k in range(2):                                              # two leafy bracts at the stalk end
        a = k * math.pi + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        y = (d * 0.8 + Vector((0, 0, -0.6))).normalized()
        z = d.cross(Vector((0, 0, 1))).cross(y).normalized(); x = y.cross(z)
        M = Matrix.Translation(Vector((0, 0, -RZ * 0.75))) @ Matrix((x, y, z)).transposed().to_4x4()
        bract(bm, M, 0.006, 0.011, mv, mr, 0.5)
    leaf_faces = list(bm.faces)[nf_before:]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(M_MK); me.materials.append(M_LEAF)
    for i, p in enumerate(me.polygons):
        p.use_smooth = True
        if i >= nf_before: p.material_index = 1
    ob = bpy.data.objects.get(name)
    if ob: ob.data = me
    else: ob = bpy.data.objects.new(name, me)
    return ob


mk_heads = bpy.data.collections.get("S07_Makhamali_Heads") or bpy.data.collections.new("S07_Makhamali_Heads")
for i in range(4):
    ob = makhamali("S07_MakhamaliHead_%02d" % (i + 1), 70 + 13 * i)
    if ob.name not in mk_heads.objects: mk_heads.objects.link(ob)
    ob.location = (0.03 * i, 0, 0)
source_collection(mk_heads)

# GN: a copy of the s04 mala GN pointing at the makhamali heads
gn = bpy.data.node_groups.get("S07_Makhamali_GN")
if not gn:
    gn = bpy.data.node_groups["S04_Mala_GN"].copy(); gn.name = "S07_Makhamali_GN"
for n in gn.nodes:
    if n.bl_idname == "GeometryNodeCollectionInfo":
        n.inputs[0].default_value = mk_heads

mk = bpy.data.objects.get("S07_Makhamali")
if not mk:
    mk = bpy.data.objects.new("S07_Makhamali", bpy.data.curves.new("S07_Makhamali", "CURVE"))
    bpy.data.collections["S07_Thali"].objects.link(mk)
L_mk = crescent(mk, 0.188, 0.160, SIDE - VIEW * 0.15, 125, FLOOR_Z + 0.009)      # right rim
m2 = mk.modifiers.get("Mala") or mk.modifiers.new("Mala", "NODES")
m2.node_group = gn
ids = [i.identifier for i in gn.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT"]
getattr(m2.properties.inputs, ids[1]).value = int(L_mk / 0.019)
getattr(m2.properties.inputs, ids[2]).value = 9
getattr(m2.properties.inputs, ids[3]).value = 1.0
print("makhamali length %.2f m, heads %d" % (L_mk, int(L_mk / 0.019)))
