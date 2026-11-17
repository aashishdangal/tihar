# Build the S04 marigold (sayapatri) mala: procedural ruffled marigold heads + a NURBS loop curve
# with shape keys (Basis = Worn on the dog's neck, OverHead, Held), flowers instanced by Geometry Nodes.
# Run inside Blender (live via exec or background):  exec(open(r"E:/Projects/tihar/scripts/s04_hand_build_mala.py").read())
# Reads blender/assets/s04_hand/s04_mala_fit.json written by scripts/s04_hand_fit_dog.py.
import bpy, bmesh, math, random, json
from mathutils import Vector, Matrix, Quaternion

FIT = r"E:\Projects\tihar\blender\assets\s04_hand\s04_mala_fit.json"
fit = json.load(open(FIT))
HEAD_R = 0.018        # marigold base radius (m): heads come out ~4.2 cm across
N_VARIANTS = 4
COUNT = 48            # heads on the mala

def coll(name, parent=None, hide=False):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [ch.name for ch in p.children]:
        p.children.link(c)
    c.hide_render = hide; c.hide_viewport = hide
    return c

def lin(hexs):
    h = hexs.lstrip("#"); out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)

# ------------------------------------------------------------------ materials
def mat_marigold():
    m = bpy.data.materials.get("S04_Marigold") or bpy.data.materials.new("S04_Marigold")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bs = N("ShaderNodeBsdfPrincipled"); bs.location = (400, 100)
    tr = N("ShaderNodeBsdfTranslucent"); tr.location = (400, -250)
    mix = N("ShaderNodeMixShader"); mix.location = (700, 0); mix.inputs[0].default_value = 0.3
    # per-head colour from the GN instance attribute
    ah = N("ShaderNodeAttribute"); ah.attribute_type = "INSTANCER"; ah.attribute_name = "mg_rand"; ah.location = (-900, 200)
    ramp = N("ShaderNodeValToRGB"); ramp.location = (-650, 200)
    cr = ramp.color_ramp; cr.elements[0].position = 0.0; cr.elements[0].color = lin("#F0A400")
    cr.elements[1].position = 0.30; cr.elements[1].color = lin("#EC8C0E")
    e = cr.elements.new(0.80); e.color = lin("#E27A0A")
    e = cr.elements.new(0.93); e.color = lin("#C9580A")
    # darker, redder petal bases deep in the ball
    av = N("ShaderNodeAttribute"); av.attribute_type = "GEOMETRY"; av.attribute_name = "petal_v"; av.location = (-900, -100)
    inv = N("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; inv.location = (-650, -100)
    L(av.outputs["Fac"], inv.inputs[1])
    base = N("ShaderNodeMix"); base.data_type = "RGBA"; base.blend_type = "MULTIPLY"; base.location = (-350, 100)
    base.inputs[7].default_value = lin("#8A3A06")
    pw = N("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.0; pw.location = (-500, -100)
    L(inv.outputs[0], pw.inputs[0]); L(pw.outputs[0], base.inputs[0])
    L(ah.outputs["Fac"], ramp.inputs[0]); L(ramp.outputs[0], base.inputs[6])
    # per-petal brightness jitter
    ar = N("ShaderNodeAttribute"); ar.attribute_type = "GEOMETRY"; ar.attribute_name = "petal_rand"; ar.location = (-650, -300)
    jr = N("ShaderNodeMapRange"); jr.location = (-400, -300)
    jr.inputs[3].default_value = 0.8; jr.inputs[4].default_value = 1.1
    L(ar.outputs["Fac"], jr.inputs[0])
    hsv = N("ShaderNodeHueSaturation"); hsv.location = (-100, 100)
    L(base.outputs[2], hsv.inputs["Color"]); L(jr.outputs[0], hsv.inputs["Value"])
    L(hsv.outputs[0], bs.inputs["Base Color"]); L(hsv.outputs[0], tr.inputs["Color"])
    bs.inputs["Roughness"].default_value = 0.55
    bs.inputs["Sheen Weight"].default_value = 0.35
    bs.inputs["Sheen Tint"].default_value = lin("#FFC060")
    L(bs.outputs[0], mix.inputs[1]); L(tr.outputs[0], mix.inputs[2]); L(mix.outputs[0], out.inputs[0])
    m.diffuse_color = lin("#E8820C")
    return m

def mat_simple(name, hexs, rough=0.6, sss=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = lin(hexs); bs.inputs["Roughness"].default_value = rough
    if sss: bs.inputs["Subsurface Weight"].default_value = sss
    m.diffuse_color = lin(hexs)
    return m

M_FLOWER = mat_marigold()
M_CALYX = mat_simple("S04_Marigold_Calyx", "#4A5A1E", 0.6)
M_THREAD = mat_simple("S04_Mala_Thread", "#E8E0CC", 0.9)

# ------------------------------------------------------------------ marigold head
def petal(bm, M, w, l, rnd, lay_v, lay_r, curl):
    """one ligule: broad, blunt, crimped tip with a soft ruffle; local Y = length, Z = outward normal"""
    nu, nv = 7, 7
    freq = rnd.uniform(1.5, 2.6); amp = rnd.uniform(0.07, 0.14) * w
    cup = rnd.uniform(0.05, 0.18) * w; ph = rnd.uniform(0, 6.28)
    pr = rnd.random()
    grid = []
    for j in range(nv):
        v = j / (nv - 1)
        row = []
        for i in range(nu):
            s = i / (nu - 1) * 2 - 1
            wid = w * (0.3 + 0.7 * math.sqrt(v))
            if v > 0.7:
                wid *= max(0.45, math.sqrt(max(0.0, 1 - ((v - 0.7) / 0.3) ** 2)))
            x = s * wid / 2
            y = v * l * (1 + 0.05 * v ** 4 * math.cos(5 * math.pi * s + ph))       # notched, crimped end
            z = cup * s * s + curl * l * v * v + amp * v ** 2 * math.sin(freq * math.pi * s + ph + 2.5 * v)
            row.append(bm.verts.new(M @ Vector((x, y, z))))
        grid.append(row)
    for j in range(nv - 1):
        for i in range(nu - 1):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            f.material_index = 0
    for j in range(nv):
        for i in range(nu):
            lay_v[grid[j][i]] = j / (nv - 1)
            lay_r[grid[j][i]] = pr

def marigold(name, seed):
    rnd = random.Random(seed)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    lv = bm.verts.layers.float.new("petal_v"); lr = bm.verts.layers.float.new("petal_rand")
    vmap_v, vmap_r = {}, {}
    n = 260; ga = math.pi * (3 - math.sqrt(5))
    tmax = math.radians(rnd.uniform(115, 125))
    R = HEAD_R
    for i in range(n):
        f = (i + 0.5) / n
        th = math.acos(1 - f * (1 - math.cos(tmax)))          # area-uniform over the cap
        ph = i * ga + rnd.uniform(-0.15, 0.15)
        d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        t = Vector((math.cos(th) * math.cos(ph), math.cos(th) * math.sin(ph), -math.sin(th)))   # away from the face centre
        k = min(1.0, th / 1.5)
        beta = math.radians(25 + 40 * k + rnd.uniform(-12, 12))     # inner petals upright, outer ones lie back
        y = (d * math.cos(beta) + t * math.sin(beta)).normalized()
        z = (d - y * d.dot(y)).normalized()
        x = y.cross(z)
        rot = Matrix((x, y, z)).transposed()
        rot = rot @ Matrix.Rotation(rnd.uniform(-0.45, 0.45), 3, "Y")
        l = R * (0.55 + 0.25 * k) * rnd.uniform(0.85, 1.12)
        w = l * rnd.uniform(0.75, 0.95)
        base = d * R * (0.42 - 0.08 * k)
        M = Matrix.Translation(base) @ rot.to_4x4()
        petal(bm, M, w, l, rnd, vmap_v, vmap_r, curl=-0.25 + 0.45 * k + rnd.uniform(-0.1, 0.1))
    for v, val in vmap_v.items(): v[lv] = val
    for v, val in vmap_r.items(): v[lr] = val
    # green calyx cup at the back (thread side)
    ret = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=R * 0.42)
    for v in ret["verts"]:
        v.co.z = v.co.z * 0.8 - R * 0.62
        v[lv] = 0.0; v[lr] = 0.5
    for f in {f for v in ret["verts"] for f in v.link_faces}:
        f.material_index = 1
    bm.to_mesh(me); bm.free()
    me.materials.append(M_FLOWER); me.materials.append(M_CALYX)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, me)
    old = ob.data
    ob.data = me
    if old is not me and old.users == 0:
        bpy.data.meshes.remove(old)
    for m in [m for m in bpy.data.meshes if m.name.startswith(name) and m.users == 0]:
        bpy.data.meshes.remove(m)
    me.name = name
    return ob

parts = coll("S04_Mala_Parts")
heads = coll("S04_Mala_Heads", parts)
# keep the source heads out of view by excluding them from the view layer (a hidden collection
# would stop Collection Info from instancing them)
def exclude(name):
    def walk(lc):
        if lc.collection.name == name: return lc
        for ch in lc.children:
            r = walk(ch)
            if r: return r
    lc = walk(bpy.context.view_layer.layer_collection)
    if lc: lc.exclude = True
for i in range(N_VARIANTS):
    nm = "S04_Marigold_%02d" % (i + 1)
    old = bpy.data.objects.get(nm)
    ob = marigold(nm, 11 + 7 * i)
    if ob.name not in heads.objects: heads.objects.link(ob)
    ob.location = (0.06 * i, 0, 0)        # spread out for inspection; GN resets children

# ------------------------------------------------------------------ the loop curve
HAND_GAP = 0.28   # distance between the two holding hands (m)

def catenary(D, S, m):
    """m+1 points of a hanging chain of length S between (-D/2,0) and (D/2,0), evenly spaced by length"""
    lo, hi = 1e-4, 100.0
    for _ in range(80):
        a = (lo + hi) / 2
        if 2 * a * math.sinh(D / (2 * a)) > S: lo = a
        else: hi = a
    a = (lo + hi) / 2
    xs = [-D / 2 + D * i / 2000 for i in range(2001)]
    pts = [(x, a * math.cosh(x / a) - a * math.cosh(D / (2 * a))) for x in xs]
    acc = [0.0]
    for i in range(1, len(pts)): acc.append(acc[-1] + math.dist(pts[i], pts[i - 1]))
    out = []; j = 0
    for k in range(m + 1):
        t = acc[-1] * k / m
        while j < len(acc) - 2 and acc[j + 1] < t: j += 1
        f = (t - acc[j]) / max(acc[j + 1] - acc[j], 1e-9)
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f))
    return out

def two_hands(n, L):
    q = n // 4; tilt = math.radians(35)
    back = catenary(HAND_GAP, L / 2, 2 * q)      # from the left hand (-X) through point 0 to the right hand
    front = catenary(HAND_GAP, L / 2, 2 * q)
    pts = [None] * n
    for k, (x, y) in enumerate(back):           # indices 3q .. n-1, 0 .. q
        idx = (3 * q + k) % n
        pts[idx] = Vector((x, -y * math.sin(tilt), y * math.cos(tilt)))
    for k, (x, y) in enumerate(front):          # indices q .. 3q, x from +D/2 to -D/2
        idx = q + k
        pts[idx] = Vector((-x, y * math.sin(tilt), y * math.cos(tilt)))
    p0 = pts[0].copy()
    return [p - p0 for p in pts]

def build_curve():
    name = "S04_Mala"
    ob = bpy.data.objects.get(name)
    if ob is None:
        cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
        ob = bpy.data.objects.new(name, cu)
        bpy.context.scene.collection.objects.link(ob)
    cu = ob.data
    if ob.data.shape_keys:
        ob.shape_key_clear()
    cu.splines.clear()
    worn = [Vector(p) for p in fit["worn"]]
    sp = cu.splines.new("NURBS"); sp.points.add(len(worn) - 1)
    for p, co in zip(sp.points, worn): p.co = (*co, 1.0)
    sp.use_cyclic_u = True; sp.order_u = 3; sp.resolution_u = 6
    ob.location = Vector(fit["worn_origin"])
    ob.shape_key_add(name="Basis (Worn)")
    k = ob.shape_key_add(name="OverHead")
    for d, co in zip(k.data, fit["overhead"]): d.co = co
    # Held: teardrop hanging from the pinch point (point 0) in the X-Z plane, facing the dog
    L = fit["length_final"]; n = len(worn)
    def tear(b):
        pts = []
        for i in range(n * 4):
            t = 2 * math.pi * i / (n * 4)
            pts.append(Vector((0.032 * math.sin(t) * math.sqrt((1 - math.cos(t)) / 2), -0.01 * math.sin(t / 2) ** 2, -b * (1 - math.cos(t)) / 2)))
        return pts
    def plen(p): return sum((p[i] - p[i - 1]).length for i in range(len(p)))
    lo, hi = 0.05, 0.6
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if plen(tear(mid)) < L else (lo, mid)
    tp = tear((lo + hi) / 2)
    # resample to n points by arc length
    seg = [(tp[(i + 1) % len(tp)] - tp[i]).length for i in range(len(tp))]; Lt = sum(seg)
    out = []; j = 0; acc = 0.0
    for i in range(n):
        s = Lt * i / n
        while acc + seg[j] < s: acc += seg[j]; j += 1
        out.append(tp[j].lerp(tp[(j + 1) % len(tp)], (s - acc) / seg[j]))
    k = ob.shape_key_add(name="HeldOneHand")
    for d, co in zip(k.data, out): d.co = co
    # HeldTwoHands: right hand at point n/4 (+X), left hand at 3n/4; both halves hang as catenaries,
    # the nape half (through point 0) tilted away from the person, the chin half towards them.
    k = ob.shape_key_add(name="HeldTwoHands")
    for d, co in zip(k.data, two_hands(n, L)): d.co = co
    for kb in ob.data.shape_keys.key_blocks[1:]: kb.value = 0.0
    ob["worn_location"] = fit["worn_origin"]
    ob["overhead_location"] = fit["overhead_origin"]
    ob["hold_points_two_hands"] = [n // 4, 3 * n // 4]
    ob["note"] = ("Object origin = control point 0 (back of the neck when worn). Basis = worn on Nubis at scale 0.65 "
                  "(location worn_location). OverHead: loose ring round the head (location overhead_location). "
                  "HeldTwoHands: right hand at point n/4, left hand at 3n/4, hands %.2f m apart. "
                  "HeldOneHand: hanging from point 0." % HAND_GAP)
    return ob

mala = build_curve()

# ------------------------------------------------------------------ geometry nodes
def sock_id(node, ident):
    return next(i for i, s in enumerate(node.inputs) if s.identifier == ident)

def build_gn():
    ng = bpy.data.node_groups.get("S04_Mala_GN") or bpy.data.node_groups.new("S04_Mala_GN", "GeometryNodeTree")
    ng.nodes.clear(); ng.interface.clear()
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    s = ng.interface.new_socket("Count", in_out="INPUT", socket_type="NodeSocketInt"); s.default_value = COUNT; s.min_value = 4
    s = ng.interface.new_socket("Seed", in_out="INPUT", socket_type="NodeSocketInt"); s.default_value = 3
    s = ng.interface.new_socket("Head Scale", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = 1.0
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes.new; L = ng.links.new
    gi = N("NodeGroupInput"); gi.location = (-1200, 0)
    go = N("NodeGroupOutput"); go.location = (1000, 0)
    c2p = N("GeometryNodeCurveToPoints"); c2p.mode = "COUNT"; c2p.location = (-900, 200)
    L(gi.outputs["Geometry"], c2p.inputs["Curve"]); L(gi.outputs["Count"], c2p.inputs["Count"])
    # jitter along the curve a little
    jit = N("FunctionNodeRandomValue"); jit.data_type = "FLOAT_VECTOR"; jit.location = (-900, -100)
    jit.inputs["Min"].default_value = (-0.002, -0.002, -0.002); jit.inputs["Max"].default_value = (0.002, 0.002, 0.002)
    L(gi.outputs["Seed"], jit.inputs["Seed"])
    sp = N("GeometryNodeSetPosition"); sp.location = (-650, 200)
    L(c2p.outputs["Points"], sp.inputs["Geometry"]); L(jit.outputs["Value"], sp.inputs["Offset"])
    al = N("FunctionNodeAlignRotationToVector"); al.axis = "Z"; al.location = (-650, -50)
    L(c2p.outputs["Tangent"], al.inputs["Vector"])
    rr = N("FunctionNodeRandomValue"); rr.data_type = "FLOAT_VECTOR"; rr.location = (-650, -250)
    rr.inputs["Min"].default_value = (-0.35, -0.35, 0); rr.inputs["Max"].default_value = (0.35, 0.35, 6.283)
    sd2 = N("ShaderNodeMath"); sd2.operation = "ADD"; sd2.inputs[1].default_value = 17; sd2.location = (-850, -300)
    L(gi.outputs["Seed"], sd2.inputs[0]); L(sd2.outputs[0], rr.inputs["Seed"])
    e2r = N("FunctionNodeEulerToRotation"); e2r.location = (-450, -250)
    L(rr.outputs["Value"], e2r.inputs["Euler"])
    rot = N("FunctionNodeRotateRotation"); rot.rotation_space = "LOCAL"; rot.location = (-300, -50)
    L(al.outputs["Rotation"], rot.inputs["Rotation"]); L(e2r.outputs["Rotation"], rot.inputs["Rotate By"])
    ci = N("GeometryNodeCollectionInfo"); ci.location = (-450, 400)
    ci.inputs["Collection"].default_value = heads
    ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
    idx = N("FunctionNodeRandomValue"); idx.data_type = "INT"; idx.location = (-450, 150)
    idx.inputs["Min"].default_value = 0; idx.inputs["Max"].default_value = N_VARIANTS - 1
    sd3 = N("ShaderNodeMath"); sd3.operation = "ADD"; sd3.inputs[1].default_value = 31; sd3.location = (-650, 400)
    L(gi.outputs["Seed"], sd3.inputs[0]); L(sd3.outputs[0], idx.inputs["Seed"])
    sc = N("FunctionNodeRandomValue"); sc.data_type = "FLOAT"; sc.location = (-300, -300)
    sc.inputs["Min"].default_value = 0.86; sc.inputs["Max"].default_value = 1.12
    L(gi.outputs["Seed"], sc.inputs["Seed"])
    scm = N("ShaderNodeMath"); scm.operation = "MULTIPLY"; scm.location = (-100, -300)
    L(sc.outputs[0], scm.inputs[0]); L(gi.outputs["Head Scale"], scm.inputs[1])
    iop = N("GeometryNodeInstanceOnPoints"); iop.location = (0, 200)
    L(sp.outputs["Geometry"], iop.inputs["Points"]); L(ci.outputs[0], iop.inputs["Instance"])
    iop.inputs["Pick Instance"].default_value = True
    L(idx.outputs[0], iop.inputs["Instance Index"]); L(rot.outputs[0], iop.inputs["Rotation"])
    L(scm.outputs[0], iop.inputs["Scale"])
    col = N("FunctionNodeRandomValue"); col.data_type = "FLOAT"; col.location = (0, -200)
    sd4 = N("ShaderNodeMath"); sd4.operation = "ADD"; sd4.inputs[1].default_value = 53; sd4.location = (-150, -150)
    L(gi.outputs["Seed"], sd4.inputs[0]); L(sd4.outputs[0], col.inputs["Seed"])
    st = N("GeometryNodeStoreNamedAttribute"); st.data_type = "FLOAT"; st.domain = "INSTANCE"; st.location = (250, 200)
    st.inputs["Name"].default_value = "mg_rand"
    L(iop.outputs[0], st.inputs["Geometry"]); L(col.outputs[0], st.inputs["Value"])
    # the thread (mostly hidden inside the heads)
    prof = N("GeometryNodeCurvePrimitiveCircle"); prof.location = (0, 500); prof.inputs["Radius"].default_value = 0.0007
    prof.inputs["Resolution"].default_value = 6
    c2m = N("GeometryNodeCurveToMesh"); c2m.location = (250, 450)
    L(gi.outputs["Geometry"], c2m.inputs["Curve"]); L(prof.outputs[0], c2m.inputs["Profile Curve"])
    sm = N("GeometryNodeSetMaterial"); sm.location = (450, 450); sm.inputs["Material"].default_value = M_THREAD
    L(c2m.outputs[0], sm.inputs["Geometry"])
    j = N("GeometryNodeJoinGeometry"); j.location = (700, 200)
    L(st.outputs[0], j.inputs[0]); L(sm.outputs[0], j.inputs[0])
    L(j.outputs[0], go.inputs[0])
    return ng

ng = build_gn()
mod = mala.modifiers.get("S04_Mala_GN") or mala.modifiers.new("S04_Mala_GN", "NODES")
mod.node_group = ng
def set_input(mod, name, val):
    ident = next(i.identifier for i in mod.node_group.interface.items_tree
                 if getattr(i, "in_out", None) == "INPUT" and i.name == name)
    try:
        getattr(mod.properties.inputs, ident).value = val      # Blender 5.2+
    except AttributeError:
        mod[ident] = val                                         # older API
set_input(mod, "Count", COUNT); set_input(mod, "Seed", 3); set_input(mod, "Head Scale", 1.0)
mala.data.materials.clear(); mala.data.materials.append(M_FLOWER)
exclude("S04_Mala_Parts")
print("[mala] built", mala.name, "points", len(mala.data.splines[0].points), "length %.3f" % fit["length_final"])
