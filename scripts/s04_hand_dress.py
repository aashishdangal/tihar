# Dress the S04 right hand: South-Asian skin (model's own painted maps, re-toned) with subsurface,
# a forearm continuation inside a plain cotton sleeve, and a thin red cotton thread at the wrist.
# exec(open(r"E:/Projects/tihar/scripts/s04_hand_dress.py").read())
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

ARM = bpy.data.objects["S04_Hand_Rig"]
HAND = bpy.data.objects["S04_Hand"]

def lin(hexs):
    h = hexs.lstrip("#"); out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)

# ------------------------------------------------------------------ palm mask (rest pose, per vertex)
PALM_N = Vector((0.7, -0.7, 0.0)).normalized()
me = HAND.data
attr = me.attributes.get("palm") or me.attributes.new("palm", "FLOAT", "POINT")
vals = []
for v in me.vertices:
    d = v.normal.dot(PALM_N)
    vals.append(max(0.0, min(1.0, (d - 0.05) / 0.5)) if v.co.z > -0.035 else 0.0)
# a few smoothing passes over edges
nb = [[] for _ in me.vertices]
for e in me.edges:
    a, b = e.vertices; nb[a].append(b); nb[b].append(a)
for _ in range(3):
    vals = [0.5 * vals[i] + 0.5 * (sum(vals[j] for j in nb[i]) / len(nb[i]) if nb[i] else vals[i]) for i in range(len(vals))]
attr.data.foreach_set("value", vals)

# ------------------------------------------------------------------ skin material
def skin_material():
    img = lambda n: bpy.data.images.get(n)
    m = bpy.data.materials.get("S04_Hand_Skin") or bpy.data.materials.new("S04_Hand_Skin")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); out.location = (1100, 0)
    bs = N("ShaderNodeBsdfPrincipled"); bs.location = (750, 0)
    uv = N("ShaderNodeUVMap"); uv.location = (-1300, 0); uv.uv_map = HAND.data.uv_layers[0].name
    tb = N("ShaderNodeTexImage"); tb.image = img("aiStandardSurface1_baseColor.png"); tb.location = (-1050, 300)
    tr = N("ShaderNodeTexImage"); tr.image = img("aiStandardSurface1_metallicRoughness.png"); tr.location = (-1050, -50)
    tn = N("ShaderNodeTexImage"); tn.image = img("aiStandardSurface1_normal.png"); tn.location = (-1050, -400)
    for t in (tr, tn): t.image.colorspace_settings.name = "Non-Color"
    for t in (tb, tr, tn): L(uv.outputs[0], t.inputs[0])
    # re-tone: keep the painted detail (creases, nails) as a ratio to its mean, multiply by the target tone
    div = N("ShaderNodeMix"); div.data_type = "RGBA"; div.blend_type = "DIVIDE"; div.location = (-750, 300)
    div.inputs[0].default_value = 1.0; div.inputs[7].default_value = (0.62, 0.30, 0.23, 1)   # painted mean (linear)
    L(tb.outputs["Color"], div.inputs[6])
    soft = N("ShaderNodeMix"); soft.data_type = "RGBA"; soft.location = (-550, 300)
    soft.inputs[0].default_value = 0.35; soft.inputs[7].default_value = (1, 1, 1, 1)         # tame the painted contrast
    L(div.outputs[2], soft.inputs[6])
    dorsum = N("ShaderNodeMix"); dorsum.data_type = "RGBA"; dorsum.blend_type = "MULTIPLY"; dorsum.location = (-300, 400)
    dorsum.inputs[0].default_value = 1.0; dorsum.inputs[7].default_value = lin("#7B4B30")       # medium-brown back of hand
    L(soft.outputs[2], dorsum.inputs[6])
    palm = N("ShaderNodeMix"); palm.data_type = "RGBA"; palm.blend_type = "MULTIPLY"; palm.location = (-300, 150)
    palm.inputs[0].default_value = 1.0; palm.inputs[7].default_value = lin("#9A6A4E")         # lighter, pinker palm
    L(soft.outputs[2], palm.inputs[6])
    pa = N("ShaderNodeAttribute"); pa.attribute_name = "palm"; pa.location = (-300, -50)
    mixp = N("ShaderNodeMix"); mixp.data_type = "RGBA"; mixp.location = (0, 300)
    L(pa.outputs["Fac"], mixp.inputs[0]); L(dorsum.outputs[2], mixp.inputs[6]); L(palm.outputs[2], mixp.inputs[7])
    # subtle blotchy variation
    tc = N("ShaderNodeTexCoord"); tc.location = (-550, -650)
    nz = N("ShaderNodeTexNoise"); nz.location = (-300, -600); nz.inputs["Scale"].default_value = 60.0
    L(tc.outputs["Object"], nz.inputs["Vector"])
    hsv = N("ShaderNodeHueSaturation"); hsv.location = (250, 300)
    vr = N("ShaderNodeMapRange"); vr.location = (0, -450); vr.inputs[3].default_value = 0.9; vr.inputs[4].default_value = 1.08
    L(nz.outputs["Fac"], vr.inputs[0]); L(vr.outputs[0], hsv.inputs["Value"])
    L(mixp.outputs[2], hsv.inputs["Color"])
    L(hsv.outputs[0], bs.inputs["Base Color"])
    # roughness: painted map (G channel) remapped + noise variation
    sep = N("ShaderNodeSeparateColor"); sep.location = (-750, -50); L(tr.outputs["Color"], sep.inputs[0])
    rr = N("ShaderNodeMapRange"); rr.location = (-300, -250); rr.inputs[3].default_value = 0.38; rr.inputs[4].default_value = 0.58
    L(sep.outputs[1], rr.inputs[0])
    radd = N("ShaderNodeMath"); radd.operation = "MULTIPLY_ADD"; radd.location = (250, -250)
    L(nz.outputs["Fac"], radd.inputs[0]); radd.inputs[1].default_value = 0.12
    rsub = N("ShaderNodeMath"); rsub.operation = "SUBTRACT"; rsub.location = (50, -250); rsub.inputs[1].default_value = 0.06
    L(rr.outputs[0], rsub.inputs[0]); L(rsub.outputs[0], radd.inputs[2])
    L(radd.outputs[0], bs.inputs["Roughness"])
    nm = N("ShaderNodeNormalMap"); nm.location = (-700, -400); nm.inputs["Strength"].default_value = 0.8
    nm.uv_map = HAND.data.uv_layers[0].name
    L(tn.outputs["Color"], nm.inputs["Color"])
    bump = N("ShaderNodeBump"); bump.location = (400, -450); bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.0003
    nz2 = N("ShaderNodeTexNoise"); nz2.location = (100, -650); nz2.inputs["Scale"].default_value = 2500.0
    L(tc.outputs["Object"], nz2.inputs["Vector"])
    L(nz2.outputs["Fac"], bump.inputs["Height"]); L(nm.outputs[0], bump.inputs["Normal"])
    L(bump.outputs[0], bs.inputs["Normal"])
    bs.inputs["Subsurface Weight"].default_value = 1.0
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.38, 0.2)
    bs.inputs["Subsurface Scale"].default_value = 0.004
    bs.inputs["Specular IOR Level"].default_value = 0.45
    bs.inputs["Sheen Weight"].default_value = 0.05
    L(bs.outputs[0], out.inputs[0])
    m.diffuse_color = lin("#7B4B30")
    return m

def cloth_material():
    m = bpy.data.materials.get("S04_Sleeve_Cotton") or bpy.data.materials.new("S04_Sleeve_Cotton")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); out.location = (800, 0)
    bs = N("ShaderNodeBsdfPrincipled"); bs.location = (500, 0)
    tc = N("ShaderNodeTexCoord"); tc.location = (-800, 0)
    wv = N("ShaderNodeTexWave"); wv.location = (-500, 100); wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 900; wv.inputs["Distortion"].default_value = 2.0
    wv2 = N("ShaderNodeTexWave"); wv2.location = (-500, -150); wv2.wave_type = "BANDS"; wv2.bands_direction = "Z"
    wv2.inputs["Scale"].default_value = 900; wv2.inputs["Distortion"].default_value = 2.0
    L(tc.outputs["Object"], wv.inputs["Vector"]); L(tc.outputs["Object"], wv2.inputs["Vector"])
    ad = N("ShaderNodeMath"); ad.operation = "ADD"; ad.location = (-250, 0)
    L(wv.outputs["Fac"], ad.inputs[0]); L(wv2.outputs["Fac"], ad.inputs[1])
    nz = N("ShaderNodeTexNoise"); nz.location = (-500, 350); nz.inputs["Scale"].default_value = 40
    L(tc.outputs["Object"], nz.inputs["Vector"])
    cr = N("ShaderNodeValToRGB"); cr.location = (-250, 350)
    cr.color_ramp.elements[0].color = lin("#3E1517"); cr.color_ramp.elements[1].color = lin("#562124")
    L(nz.outputs["Fac"], cr.inputs[0]); L(cr.outputs[0], bs.inputs["Base Color"])
    bump = N("ShaderNodeBump"); bump.location = (200, -200); bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.0004
    L(ad.outputs[0], bump.inputs["Height"]); L(bump.outputs[0], bs.inputs["Normal"])
    bs.inputs["Roughness"].default_value = 0.92
    bs.inputs["Sheen Weight"].default_value = 0.08; bs.inputs["Sheen Roughness"].default_value = 0.5
    bs.inputs["Sheen Tint"].default_value = lin("#8A4A4A")
    L(bs.outputs[0], out.inputs[0])
    m.diffuse_color = lin("#5E2326")
    return m

def thread_material():
    m = bpy.data.materials.get("S04_Red_Thread") or bpy.data.materials.new("S04_Red_Thread")
    m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = lin("#8A0C10"); bs.inputs["Roughness"].default_value = 0.85
    bs.inputs["Sheen Weight"].default_value = 0.1
    bs.inputs["Sheen Tint"].default_value = lin("#C03030")
    m.diffuse_color = lin("#B0141A")
    return m

M_SKIN = skin_material(); M_CLOTH = cloth_material(); M_THREAD = thread_material()
HAND.data.materials.clear(); HAND.data.materials.append(M_SKIN)

def replace_obj(name, me):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    else:
        old = ob.data; ob.data = me
        if old.users == 0: bpy.data.meshes.remove(old)
    me.name = name
    return ob

def parent_bone(ob, bone="Root_joint_01"):
    mw = ob.matrix_world.copy()
    ob.parent = ARM; ob.parent_type = "BONE"; ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw

# forearm axis in the rest pose (armature space == world: the rig sits at the origin unposed)
B = ARM.data.bones
AX = (B["HANDPALM_joint_02"].head_local - B["Root_joint_01"].head_local).normalized()   # towards the hand
def frame(z):
    """point on the forearm axis at height z below the wrist (z<0) and two side vectors"""
    c = Vector((0, 0, 0)) + AX * z
    sx = AX.cross(Vector((0, 1, 0))).normalized(); sy = AX.cross(sx).normalized()
    return c, sx, sy

# ------------------------------------------------------------------ forearm continuation (inside the sleeve)
def build_forearm():
    bm = bmesh.new(); SEG = 24; rows = []
    for k in range(9):
        z = -0.06 - k * 0.03
        c, sx, sy = frame(z)
        t = k / 8
        rx, ry = 0.0335 + 0.006 * t, 0.031 + 0.004 * t
        rows.append([bm.verts.new(c + sx * math.cos(a) * rx + sy * math.sin(a) * ry)
                     for a in [2 * math.pi * s / SEG for s in range(SEG)]])
    for r in range(len(rows) - 1):
        for s in range(SEG):
            bm.faces.new((rows[r][s], rows[r][(s + 1) % SEG], rows[r + 1][(s + 1) % SEG], rows[r + 1][s]))
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = bpy.data.meshes.new("S04_Hand_Forearm"); bm.to_mesh(m); bm.free()
    for p in m.polygons: p.use_smooth = True
    m.materials.append(M_SKIN)
    ob = replace_obj("S04_Hand_Forearm", m)
    ob.parent = None; ob.matrix_world = Matrix.Identity(4)
    parent_bone(ob)
    return ob

# ------------------------------------------------------------------ plain cotton sleeve with a hem
def build_sleeve():
    rnd = random.Random(5)
    bm = bmesh.new(); SEG = 40; RINGS = 26; rows = []
    z0, z1 = -0.042, -0.30
    folds = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(-0.25, -0.05), rnd.uniform(0.003, 0.006)) for _ in range(8)]
    for k in range(RINGS):
        t = k / (RINGS - 1); z = z0 + (z1 - z0) * t
        c, sx, sy = frame(z)
        row = []
        for s in range(SEG):
            a = 2 * math.pi * s / SEG
            r = 0.043 + 0.008 * t
            # soft folds: a few diagonal ridges + low noise; gathers a little at the cuff
            for (fa, fz, fh) in folds:
                d = math.atan2(math.sin(a - fa - (z - fz) * 9), math.cos(a - fa - (z - fz) * 9))
                r += fh * math.exp(-(d / 0.25) ** 2) * math.exp(-((z - fz) / 0.07) ** 2)
            r += 0.0035 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, z * 25))) + 0.0012 * noise.noise(Vector((math.cos(a) * 6, math.sin(a) * 6, z * 80)))
            # sag: cloth hangs down a little on the -sy (underside) when the arm is horizontal
            row.append(bm.verts.new(c + sx * math.cos(a) * r + sy * math.sin(a) * r * 0.93))
        rows.append(row)
    for r in range(RINGS - 1):
        for s in range(SEG):
            bm.faces.new((rows[r][s], rows[r][(s + 1) % SEG], rows[r + 1][(s + 1) % SEG], rows[r + 1][s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = bpy.data.meshes.new("S04_Hand_Sleeve"); bm.to_mesh(m); bm.free()
    for p in m.polygons: p.use_smooth = True
    m.materials.append(M_CLOTH)
    ob = replace_obj("S04_Hand_Sleeve", m)
    ob.parent = None; ob.matrix_world = Matrix.Identity(4)
    for mod in list(ob.modifiers): ob.modifiers.remove(mod)
    so = ob.modifiers.new("Thickness", "SOLIDIFY"); so.thickness = 0.0018; so.offset = 1.0
    sd = ob.modifiers.new("Subdivision", "SUBSURF"); sd.levels = 1; sd.render_levels = 2
    # rolled hem at the cuff
    c, sx, sy = frame(z0 + 0.002)
    hem = bpy.data.curves.get("S04_Hand_SleeveHem") or bpy.data.curves.new("S04_Hand_SleeveHem", "CURVE")
    hem.splines.clear(); hem.dimensions = "3D"; hem.bevel_depth = 0.0022; hem.bevel_resolution = 3
    sp = hem.splines.new("POLY"); sp.points.add(SEG - 1); sp.use_cyclic_u = True
    for s, p in enumerate(sp.points):
        a = 2 * math.pi * s / SEG
        r = 0.0445
        q = c + sx * math.cos(a) * r + sy * math.sin(a) * r * 0.93
        p.co = (*q, 1)
    ho = bpy.data.objects.get("S04_Hand_SleeveHem") or bpy.data.objects.new("S04_Hand_SleeveHem", hem)
    if ho.name not in bpy.context.scene.collection.objects: bpy.context.scene.collection.objects.link(ho)
    hem.materials.clear(); hem.materials.append(M_CLOTH)
    for o in (ob, ho):
        o.parent = None; o.matrix_world = Matrix.Identity(4); parent_bone(o)
    return ob

# ------------------------------------------------------------------ red cotton thread (doro) at the wrist
def build_thread():
    cu = bpy.data.curves.get("S04_Hand_RedThread") or bpy.data.curves.new("S04_Hand_RedThread", "CURVE")
    cu.splines.clear(); cu.dimensions = "3D"; cu.bevel_depth = 0.00045; cu.bevel_resolution = 2
    # three loose turns hugging the wrist, z -0.012 .. -0.02
    hm = HAND.evaluated_get(bpy.context.evaluated_depsgraph_get())
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(HAND, bpy.context.evaluated_depsgraph_get())
    sp = cu.splines.new("NURBS"); n = 3 * 36; sp.points.add(n - 1); sp.order_u = 4
    for i, p in enumerate(sp.points):
        a = 2 * math.pi * i / 36
        z = -0.012 - 0.006 * i / n + 0.0028 * math.sin(a + 1 + i / n * 2.4)
        c, sx, sy = frame(z)
        d = (sx * math.cos(a) + sy * math.sin(a))
        hit = bvh.ray_cast(c + d * 0.08, -d, 0.1)
        q = (hit[0] + d * 0.0007) if hit[0] else c + d * 0.034
        p.co = (*q, 1)
    ob = bpy.data.objects.get("S04_Hand_RedThread") or bpy.data.objects.new("S04_Hand_RedThread", cu)
    if ob.name not in bpy.context.scene.collection.objects: bpy.context.scene.collection.objects.link(ob)
    cu.materials.clear(); cu.materials.append(M_THREAD)
    ob.parent = None; ob.matrix_world = Matrix.Identity(4); parent_bone(ob)
    return ob

# build in the rest pose so everything lines up, then restore the pose
saved = {pb.name: pb.rotation_quaternion.copy() for pb in ARM.pose.bones}
ARM.data.pose_position = "REST"; bpy.context.view_layer.update()
fa = build_forearm(); sl = build_sleeve(); th = build_thread()
ARM.data.pose_position = "POSE"
for n, q in saved.items(): ARM.pose.bones[n].rotation_quaternion = q
bpy.context.view_layer.update()
print("[dress] skin, forearm, sleeve, hem, thread done")
