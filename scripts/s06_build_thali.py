# s06: the Deusi offering thali at the courtyard centre (where the s05 rangoli was).
# Reference: refrences/Two-View Copper Puja Offering Plate.png — hammered copper plate, a fan of
# banknotes round the rim, orange + yellow marigolds, a copper bowl of rice with a lit diyo,
# bananas, an apple and an orange.
# Run inside the s06 .blend (MCP exec). Rebuilds collection S06_Thali each time.
import bpy, bmesh, math, random
from mathutils import Vector, Euler

random.seed(606)
FLOOR = 0.011          # top of S04_Floor_Slabs
R = 0.30               # plate radius (Ø 60 cm)
NOTE_TEX = r"E:\Projects\tihar\blender\assets\s06\note_1000_photo.jpg"   # owner photo of a real NPR 1000 (back)

# --- collection ----------------------------------------------------------------------------
col = bpy.data.collections.get("S06_Thali")
if col:
    for o in list(col.objects):
        if o.name.startswith("S06_"):
            bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("S06_Thali")
    bpy.context.scene.collection.children.link(col)
root = bpy.data.objects.new("S06_Thali_Root", None)
root.location = (0, 0, FLOOR)
col.objects.link(root)


def link(o, parent=root):
    for c in o.users_collection:
        c.objects.unlink(o)
    col.objects.link(o)
    if parent:
        mw = o.matrix_basis.copy()   # unparented here; matrix_world isn't updated until a depsgraph eval
        o.parent = parent
        o.matrix_world = mw
    return o


# --- materials -------------------------------------------------------------------------------
def copper_mat():
    m = bpy.data.materials.get("S06_Copper") or bpy.data.materials.new("S06_Copper")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # tarnish: darker, rougher patches
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 18; n.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.55, 0.22, 0.10, 1)
    ramp.color_ramp.elements[1].position = 0.7; ramp.color_ramp.elements[1].color = (0.93, 0.52, 0.32, 1)
    nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.38; mr.inputs["To Max"].default_value = 0.22
    nt.links.new(n.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    # hammered dents
    v = nt.nodes.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 90
    v.feature = "SMOOTH_F1" if "SMOOTH_F1" in [i.identifier for i in v.bl_rna.properties["feature"].enum_items] else v.feature
    nt.links.new(tc.outputs["Object"], v.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(v.outputs["Distance"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m


def note_mat():
    m = bpy.data.materials.get("S06_Note") or bpy.data.materials.new("S06_Note")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.75
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(NOTE_TEX, check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    # paper lets a little light through
    for k in ("Subsurface Weight", "Transmission Weight"):
        if k in b.inputs:
            b.inputs[k].default_value = 0.0
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m


COPPER, NOTE = copper_mat(), note_mat()


# --- plate (lathe) -----------------------------------------------------------------------------
def lathe(name, prof, seg=160, mat=None):
    """prof: [(r, z)] from centre outwards; revolved around Z."""
    bm = bmesh.new()
    rings = []
    for (r, z) in prof:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    if mat: me.materials.append(mat)
    col.objects.link(o); o.parent = root
    return o


# top surface then lip then underside (closed-ish shell, 2 mm thick)
plate_prof = [(0.001, 0.004), (0.24, 0.004), (0.272, 0.010), (0.292, 0.022), (0.300, 0.028),
              (0.304, 0.026), (0.300, 0.020), (0.282, 0.008), (0.25, 0.0), (0.001, 0.0)]
plate = lathe("S06_Thali_Plate", plate_prof, mat=COPPER)
# beaded rim ring like the reference
rim = lathe("S06_Thali_Rim", [(0.296, 0.030), (0.300, 0.033), (0.305, 0.030), (0.300, 0.026), (0.296, 0.030)], mat=COPPER)

# --- banknotes: a fan round the rim, long side radial -------------------------------------------
NW, NH = 0.158, 0.064         # real size; the fan is pushed outward so it hangs a little over the rim (owner)
N_NOTES = 26
R_IN, R_LIP, Z_LIP = 0.177, 0.302, 0.034

def note_z(r):
    """Hanging note: straight from the floor up onto the rim lip, then a soft droop past it."""
    if r <= R_LIP:
        return 0.0050 + (Z_LIP - 0.0050) * (r - R_IN) / (R_LIP - R_IN)
    d = r - R_LIP
    return Z_LIP - 0.55 * d - 4.0 * d * d

PLATE_TOP = [(0.0, 0.004), (0.24, 0.004), (0.272, 0.010), (0.292, 0.022), (0.300, 0.028)]
def note_z_inside(r):
    """Inside note: flat on the plate floor, then lying on the sloped rim (1 mm above it)."""
    for (r0, z0), (r1, z1) in zip(PLATE_TOP, PLATE_TOP[1:]):
        if r <= r1:
            return z0 + (z1 - z0) * (r - r0) / (r1 - r0) + 0.0012
    return PLATE_TOP[-1][1] + 0.0012

for i in range(N_NOTES):
    a = 2 * math.pi * i / N_NOTES + random.uniform(-0.03, 0.03)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=2, size=1)
    o = bpy.context.active_object
    o.name = f"S06_Note_{i:02d}"
    hang = i % 2 == 0 or random.random() < 0.25          # most hang over the rim, some lie inside
    r_in = (R_IN if hang else 0.128) + random.uniform(-0.006, 0.006)
    zf = note_z if hang else note_z_inside
    for v in o.data.vertices:
        x = (v.co.x + 0.5) * NW                 # 0 .. NW along the radius
        v.co.x = r_in + x
        v.co.y = v.co.y * NH
        v.co.z = zf(r_in + x) + 0.00025 * i + (0.0004 if hang else 0) + 0.0012 * (v.co.y / NH) * math.sin(i)
    for p_ in o.data.polygons: p_.use_smooth = True
    o.location = (0, 0, FLOOR)
    o.rotation_euler = (0, 0, a + math.radians(random.uniform(-4, 4)))
    o.data.materials.append(NOTE)
    link(o)

# --- copper rice bowl + rice (Sketchfab models) -------------------------------------------------
# (place() is defined below; these use the same copy-and-bake helper)
# --- marigold ring between bowl and notes: orange + yellow alternating ---------------------------
def yellow_mat():
    src = bpy.data.materials["S05_Marigold"]
    m = bpy.data.materials.get("S06_Marigold_Yellow")
    if m: return m
    m = src.copy(); m.name = "S06_Marigold_Yellow"
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lk = b.inputs["Base Color"].links[0]; frm = lk.from_socket
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Hue"].default_value = 0.545; hs.inputs["Value"].default_value = 1.12
    nt.links.new(frm, hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    return m

def centred_flower(name, mat):
    from mathutils import Matrix
    me = bpy.data.meshes.get(name)
    if me: bpy.data.meshes.remove(me)
    me = bpy.data.meshes["model.005_lo_lo2"].copy(); me.name = name
    vs = [v.co for v in me.vertices]
    c = Vector([(min(v[i] for v in vs) + max(v[i] for v in vs)) / 2 for i in range(3)])
    c.z = min(v.z for v in vs)
    me.transform(Matrix.Translation(-c))
    me.materials.clear(); me.materials.append(mat)
    return me

def orange_mat():
    m = bpy.data.materials.get("S06_Marigold_Orange")
    if m: return m
    m = bpy.data.materials["S05_Marigold"].copy(); m.name = "S06_Marigold_Orange"
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    frm = b.inputs["Base Color"].links[0].from_socket
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = 1.45
    nt.links.new(frm, hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    return m

ORANGE_ME = centred_flower("S06_Marigold_Orange_me", orange_mat())
YEL_ME = centred_flower("S06_Marigold_Yellow_me", yellow_mat())
N_FL = 10
for i in range(N_FL):
    a = 2 * math.pi * (i + 0.5) / N_FL + random.uniform(-0.05, 0.05)
    me = ORANGE_ME if i % 2 == 0 else YEL_ME
    o = bpy.data.objects.new(f"S06_Thali_Marigold_{i:02d}", me)
    rr = 0.121 + random.uniform(-0.003, 0.003)
    s = random.uniform(0.042, 0.047) if me is ORANGE_ME else random.uniform(0.039, 0.044)
    o.location = (rr * math.cos(a), rr * math.sin(a), FLOOR + 0.004 - 0.15 * s)
    o.scale = (s, s, s)
    o.rotation_euler = (math.radians(random.uniform(-12, 12)), math.radians(random.uniform(-12, 12)), random.uniform(0, 6.28))
    col.objects.link(o); o.parent = root; o.matrix_parent_inverse = root.matrix_world.inverted()

# --- fruit: bananas, apple, orange in the upper-right sector --------------------------------------
fa = math.radians(52)
def place(name, newname, r, ang, z, rot=(0, 0, 0), scale=1.0, align=False, flip=False):
    """Copy a model with its import transform baked in, origin at its bottom centre."""
    from mathutils import Matrix
    src = bpy.data.objects[name]
    me = src.data.copy(); me.name = newname
    # world matrix rebuilt from the parent chain: the source models are hidden, and after a file
    # reload a hidden child's cached matrix_world can drop its parent's import scale (0.007 bowl)
    def world(o):
        m = o.matrix_basis.copy()
        while o.parent:
            m = o.parent.matrix_basis @ o.matrix_parent_inverse @ m
            o = o.parent
        return m
    me.transform(world(src))
    vs = [v.co for v in me.vertices]
    c = Vector(((min(v.x for v in vs) + max(v.x for v in vs)) / 2, (min(v.y for v in vs) + max(v.y for v in vs)) / 2, min(v.z for v in vs)))
    me.transform(Matrix.Translation(-c)); me.transform(Matrix.Scale(scale, 4))
    o = bpy.data.objects.new(newname, me)
    col.objects.link(o)
    if align:
        # long axis (PCA of the footprint) laid along the rim tangent; flip turns the curve
        n = len(me.vertices); mx = sum(v.co.x for v in me.vertices) / n; my = sum(v.co.y for v in me.vertices) / n
        sxx = sum((v.co.x - mx) ** 2 for v in me.vertices); syy = sum((v.co.y - my) ** 2 for v in me.vertices)
        sxy = sum((v.co.x - mx) * (v.co.y - my) for v in me.vertices)
        axis = 0.5 * math.atan2(2 * sxy, sxx - syy)
        rot = (rot[0], rot[1], ang + math.pi / 2 - axis + (math.pi if flip else 0) + rot[2])
    o.rotation_euler = rot
    o.location = (r * math.cos(ang), r * math.sin(ang), FLOOR + z)
    o.parent = root; o.matrix_parent_inverse = root.matrix_world.inverted()
    return o

BANANA_FLIP = False
for k, (nm, dr, dz) in enumerate([("bananas_a", 0.252, 0.010), ("bananas_b", 0.232, 0.016), ("bananas_c", 0.212, 0.010)]):
    place(nm, f"S06_Thali_Banana_{k}", dr, fa + 0.02 * k, dz, rot=(0, 0, math.radians(3 * k)), align=True, flip=BANANA_FLIP)
place("food_apple_01", "S06_Thali_Apple", 0.200, fa + 0.80, 0.010)
place("Orange_Orange_0", "S06_Thali_Orange", 0.205, fa - 0.78, 0.010, scale=1.25)
bowl = place("BowlA_01_fsdfs_0", "S06_Thali_Bowl", 0, 0, 0.004, scale=1.05)
bowl.data.materials.clear(); bowl.data.materials.append(COPPER)
rice = place("Object_3", "S06_Thali_Rice", 0, 0, 0.004 + 0.062 * 1.08 - 0.004, scale=1.08)
print("thali built:", len(col.objects), "objects")

# --- rice mound in the bowl (like the reference: a heaped dome of grains, diyo on top) ----------
def rice_mound():
    from mathutils import Matrix
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1)
    m = bpy.context.active_object; m.name = "S06_Thali_RiceMound"
    me = m.data
    for v in me.vertices:          # keep the top half, flatten into a low dome
        if v.co.z < 0: v.co.z = 0
    me.transform(Matrix.Diagonal((0.074, 0.074, 0.030, 1)))
    m.location = (0, 0, FLOOR + 0.004 + 0.066)
    link(m)
    mat = bpy.data.materials.get("S06_Rice") or bpy.data.materials.new("S06_Rice")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.93, 0.87, 0.73, 1)
    if "Subsurface Weight" in b.inputs:
        b.inputs["Subsurface Weight"].default_value = 0.35
        b.inputs["Subsurface Radius"].default_value = (0.002, 0.002, 0.0015)
    me.materials.append(mat)
    # one grain: a stretched ico sphere (7 x 2.2 mm)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
    g = bpy.context.active_object; g.name = "S06_RiceGrain"
    g.data.transform(Matrix.Diagonal((0.0036, 0.0011, 0.0011, 1)))
    g.data.materials.append(mat)
    link(g, parent=None); g.hide_render = True; g.hide_viewport = True
    # geometry nodes: scatter grains over the dome, random rotation, keep the dome under them
    ng = bpy.data.node_groups.new("S06_RiceScatter", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes; L = ng.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    dist = N.new("GeometryNodeDistributePointsOnFaces"); dist.inputs["Density"].default_value = 260000
    obj = N.new("GeometryNodeObjectInfo"); obj.inputs["Object"].default_value = g
    rr = N.new("FunctionNodeRandomValue"); rr.data_type = "FLOAT_VECTOR"
    rr.inputs["Max"].default_value = (6.3, 6.3, 6.3)
    inst = N.new("GeometryNodeInstanceOnPoints")
    join = N.new("GeometryNodeJoinGeometry")
    L.new(gi.outputs[0], dist.inputs["Mesh"])
    pos = N.new("GeometryNodeInputPosition"); sep = N.new("ShaderNodeSeparateXYZ")
    cmb = N.new("ShaderNodeCombineXYZ"); vl = N.new("ShaderNodeVectorMath"); vl.operation = "LENGTH"
    cmp = N.new("FunctionNodeCompare"); cmp.data_type = "FLOAT"; cmp.operation = "GREATER_THAN"
    cmp.inputs["B"].default_value = 0.042                 # keep a clear seat for the diyo (r < 4.2 cm)
    L.new(pos.outputs["Position"], sep.inputs[0]); L.new(sep.outputs["X"], cmb.inputs["X"]); L.new(sep.outputs["Y"], cmb.inputs["Y"])
    L.new(cmb.outputs[0], vl.inputs[0]); L.new(vl.outputs["Value"], cmp.inputs["A"])
    L.new(cmp.outputs["Result"], dist.inputs["Selection"])
    L.new(dist.outputs["Points"], inst.inputs["Points"])
    L.new(obj.outputs["Geometry"], inst.inputs["Instance"])
    L.new(rr.outputs["Value"], inst.inputs["Rotation"])
    L.new(gi.outputs[0], join.inputs[0]); L.new(inst.outputs["Instances"], join.inputs[0])
    L.new(join.outputs[0], go.inputs[0])
    mod = m.modifiers.new("rice", "NODES"); mod.node_group = ng
    return m

old = bpy.data.objects.get("S06_RiceGrain")
if old: bpy.data.objects.remove(old, do_unlink=True)
for n in list(bpy.data.node_groups):
    if n.name.startswith("S06_RiceScatter"): bpy.data.node_groups.remove(n)
rice_mound()
bpy.data.objects["S06_Thali_Rice"].hide_render = True     # the flat Sketchfab rice sits under the mound
bpy.data.objects["S06_Thali_Rice"].hide_viewport = True
# diyo smaller and sitting on the mound top, so rice shows all round it
print("rice mound added")


# --- centre diyo = the s00 diyo with its approved RealFire flame (v068), toned down a little -----
S00 = "E:/Projects/tihar/blender/scenes/s00_enter_v068_realfire.blend"
CD_LIGHT = 1.1            # s00's flame light is 0.72 W at its close-up; a little more here, far below the 9 W test
MOUND_TOP = FLOOR + 0.004 + 0.066 + 0.030

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
        # keep s00 animation: the flame pivot/core flicker is keyed (clearing it collapsed the flame)
        if o.parent is None or o.parent.name not in names:
            # keep the s00 world transform (the scan mesh's own parent "_0" carries its scale)
            m = o.matrix_basis.copy(); q = o
            while q.parent:
                m = q.parent.matrix_basis @ q.matrix_parent_inverse @ m
                q = q.parent
            o.parent = None
            o.matrix_basis = m
            o.parent = e                       # e is at the origin here, so no inverse needed
        o.name = f"{name}_" + o.name.replace("S00_", "")
    for o in dst.objects:
        if o.type == "LIGHT":
            o.data = o.data.copy(); o.data.energy = CD_LIGHT
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(rotz)); e.scale = (scale,) * 3
    e.parent = root; e.matrix_parent_inverse = root.matrix_world.inverted()
    return e

s00_diyo("S06_CentreDiyo", (0, 0, MOUND_TOP - 0.002), 0.7, 200)    # sits on the rice, oil showing
s00_diyo("S06_SideDiyo_L", (-0.43, 0.0, FLOOR + 2 * 0.056), 0.95, 4)            # floor, left; spout + flame face the thali
s00_diyo("S06_SideDiyo_R", (0.43, 0.0, FLOOR + 2 * 0.056), 0.95, 184)           # floor, right; spout + flame face the thali
print("s00 diyos: centre + left + right")

# --- clear mustard oil: glossy, see-through amber, so the diyo's clay floor shows through ---------
def oil_mat():
    """Clear mustard oil: a Transparent BSDF (lets the flame's light AND the view reach the clay
    floor; a refractive Principled blocks lamp light without caustics) mixed by Fresnel with a sharp
    gloss, so the surface still mirrors the flame."""
    m = bpy.data.materials.get("S06_Oil") or bpy.data.materials.new("S06_Oil")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (1.0, 0.86, 0.55, 1)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.02
    fr = nt.nodes.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.47
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 120; nz.inputs["Detail"].default_value = 2
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.04
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], gl.inputs["Normal"]); nt.links.new(bp.outputs["Normal"], fr.inputs["Normal"])
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs["Fac"], mx.inputs["Fac"]); nt.links.new(tr.outputs["BSDF"], mx.inputs[1]); nt.links.new(gl.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    return m

OIL = oil_mat()
for nm in ("S06_CentreDiyo", "S06_SideDiyo_L", "S06_SideDiyo_R"):
    for o in bpy.data.objects[nm].children_recursive:
        if "Oil" in o.name and o.type == "MESH":
            o.data.materials.clear(); o.data.materials.append(OIL)
print("oil: clear amber")

# --- two old bricks stacked under each side diyo (owner): raises them to ~11 cm ------------------
BRICK = (0.23, 0.11, 0.056)          # Nepali clay brick, l x w x h
for o in list(bpy.data.objects):
    if o.name.startswith("S06_Brick_") or o.name.endswith("_OilGlow"):
        bpy.data.objects.remove(o, do_unlink=True)

def clay_brick_mat():
    """Loose old Nepali brick: fired red-orange clay, mottled, chipped and dusty."""
    m = bpy.data.materials.get("S06_ClayBrick")
    if m: return m
    m = bpy.data.materials.new("S06_ClayBrick"); m.use_nodes = True
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].position = 0.3; rp.color_ramp.elements[0].color = (0.24, 0.075, 0.04, 1)
    rp.color_ramp.elements[1].position = 0.75; rp.color_ramp.elements[1].color = (0.52, 0.22, 0.12, 1)
    nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def brick(name, loc, rotz):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object; o.name = name
    o.scale = BRICK; bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new("bevel", "BEVEL"); bv.width = 0.004; bv.segments = 2
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rotz))
    o.data.materials.append(clay_brick_mat())
    link(o)
    return o

for side, x in (("L", -0.43), ("R", 0.43)):
    brick(f"S06_Brick_{side}0", (x, 0.0, FLOOR + 0.028), 90 + random.uniform(-4, 4))
    brick(f"S06_Brick_{side}1", (x + random.uniform(-0.008, 0.008), random.uniform(-0.01, 0.01), FLOOR + 0.084), 90 + random.uniform(-7, 7))

# --- clay floor of each diyo visible through the clear oil from above (owner) --------------------
# a faint warm lamp just above the oil, hidden from the camera, lights the clay under the oil
bpy.context.view_layer.update()
for nm in ("S06_CentreDiyo", "S06_SideDiyo_L", "S06_SideDiyo_R"):
    e = bpy.data.objects[nm]
    oil = next(o for o in e.children_recursive if "Oil" in o.name and o.type == "MESH")
    L = bpy.data.lights.new(nm + "_OilGlow", "POINT"); L.energy = 0.08; L.shadow_soft_size = 0.004
    L.color = (1.0, 0.7, 0.35)
    lo = bpy.data.objects.new(nm + "_OilGlow", L); col.objects.link(lo)
    lo.location = oil.matrix_world.translation + Vector((0, 0, 0.006))
    lo.visible_camera = False
    lo.visible_glossy = False          # no white dot reflected in the oil
print("bricks + oil glow")

# (a separate "flame top" glow was tried and dropped: the approved look is the RealFire flame,
#  clear oil and lit clay; see v035 test dt3)
for nm in ("S06_CentreDiyo", "S06_SideDiyo_L", "S06_SideDiyo_R"):
    old = bpy.data.objects.get(nm + "_FlameTop")
    if old: bpy.data.objects.remove(old, do_unlink=True)

# the RealFire volume sits round the flame light; let that light out (it shadowed the diyo's inside)
for nm in ("S06_CentreDiyo", "S06_SideDiyo_L", "S06_SideDiyo_R"):
    for o in bpy.data.objects[nm].children_recursive:
        if o.type == "VOLUME":
            o.visible_shadow = False
