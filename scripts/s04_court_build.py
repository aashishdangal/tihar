# Build the Scene 4 Newari courtyard (chowk) from scratch and save it.
#   blender -b --factory-startup --python scripts/s04_court_build.py -- <out.blend>
# Coordinates: metres, Z up, courtyard floor top z=0, courtyard x -6..6, y -6.6..6.0.
# North side (y>6) = portico (dalan) building facing south into the courtyard.
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Euler, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s04_court_lib as L
from s04_court_lib import MB, wall, coll, mat_pbr, mat_flat
import s04_court_mat as CM

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else L.ROOT + "/blender/scenes/s04_courtyard_v001.blend"
random.seed(4)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"

C_COURT = coll("S04_Courtyard")
C_PORT = coll("S04_Portico")
C_DRESS = coll("S04_Dressing")
C_LIGHT = coll("S04_Lights")
C_CAMS = coll("S04_TestCams")
C_SRC = coll("S04_AssetSrc")  # instance sources, excluded from the view layer

# ------------------------------------------------------------------ materials
M = {}
M["brick"] = CM.mat_newari_brick("S04_Brick", 0, eave_z=7.9, limewash=0.22, bright=1.15)
M["brick_b"] = CM.mat_newari_brick("S04_Brick_B", 1, eave_z=7.5, limewash=0.18, bright=1.05)
M["wood"] = mat_pbr("S04_Wood_Dark", "dark_wood", 1.2, value=0.45, sat=0.55, rough_add=0.15, bump=0.4)
M["post"] = mat_pbr("S04_Wood_Post", "dark_wood", 1.0, value=0.32, sat=0.7, rough_add=0.15, bump=0.5, rot=(0, math.pi / 2, 0))
M["beam"] = mat_pbr("S04_Wood_Beam", "rough_wood", 0.9, value=0.7, sat=0.6, rough_add=0.1, bump=0.6)
M["plank"] = mat_pbr("S04_Wood_Plank", "weathered_brown_planks", 1.8, value=1.0, sat=0.7, bump=0.6)
M["carve"] = mat_pbr("S04_Wood_Carved", "wood_table_worn", 0.6, value=0.55, sat=0.6, rough_add=0.1, bump=0.5)
M["roof"] = mat_pbr("S04_Roof_Tiles", "clay_roof_tiles_02", 2.0, value=0.7, sat=0.8, grime=0.35, bump=1.0)
M["tile"] = mat_pbr("S04_Portico_Tiles", "terracotta_floor_tiles", 1.6, value=0.85, sat=0.8, grime=0.2, bump=0.8)
M["slab"] = mat_pbr("S04_Stone_Slab", "rock_boulder_dry", 1.8, coords="UV", value=0.62, sat=0.25,
                    var_attr="slabvar", var_amt=0.35, bump=1.0)
M["stone"] = mat_pbr("S04_Stone", "concrete_floor_worn_001", 1.4, value=0.6, sat=0.25, grime=0.35, bump=1.0)
M["dark"] = mat_flat("S04_Interior_Dark", (0.012, 0.010, 0.009), rough=1.0)
M["brass"] = mat_flat("S04_Brass", (0.80, 0.55, 0.22), rough=0.32, metal=1.0)
M["cloth"] = mat_flat("S04_Cloth_Red", (0.30, 0.02, 0.015), rough=0.9)
M["clay"] = mat_flat("S04_Clay_Diyo", (0.42, 0.16, 0.07), rough=0.85)
M["oil"] = mat_flat("S04_Diyo_Oil", (0.10, 0.06, 0.01), rough=0.08)
M["flame"] = mat_flat("S04_Diyo_Flame", (1, 0.6, 0.2), emit=(1.0, 0.52, 0.14), emit_strength=25)


def joint_material():
    m = L.new_mat("S04_Stone_Joints")
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = L.bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.5,) * 3
    Lk.new(tc.outputs["Object"], mp.inputs[0])
    t = N.new("ShaderNodeTexImage"); t.image = L.img(L.ph_file("dirt", "diff")); t.projection = "BOX"
    Lk.new(mp.outputs[0], t.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
    Lk.new(tc.outputs["Object"], nz.inputs[0])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.45; cr.color_ramp.elements[1].position = 0.62
    Lk.new(nz.outputs["Fac"], cr.inputs[0])
    dirt = L.mix_rgb(nt, "MULTIPLY", t.outputs[0], (0.3, 0.27, 0.24))
    col = L.mix_rgb(nt, "MIX", dirt, (0.06, 0.11, 0.03), cr.outputs[0])
    Lk.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.6
    Lk.new(nz.outputs["Fac"], bm.inputs["Height"]); Lk.new(bm.outputs[0], b.inputs["Normal"])
    return m


M["joint"] = joint_material()
CM.add_dust_moss(M["wood"], dust=0.3, grime=0.3)
CM.add_dust_moss(M["post"], dust=0.2, grime=0.3, weathering=True)
CM.add_dust_moss(M["carve"], dust=0.3, grime=0.3)
CM.add_dust_moss(M["beam"], dust=0.25, grime=0.25)
CM.add_dust_moss(M["plank"], dust=0.15, grime=0.2)
CM.add_dust_moss(M["roof"], dust=0.0, moss=0.55, lichen=0.6, grime=0.35)
CM.add_dust_moss(M["stone"], dust=0.0, moss=0.35, grime=0.3, weathering=True)
CM.add_dust_moss(M["tile"], dust=0.25, grime=0.25)

# ------------------------------------------------------------------ layout constants
CX = 6.0          # courtyard half width (x)
YS = -6.6         # south facade plane
YPF = 6.0         # portico plinth front
PZ = 0.40         # portico floor height
YB = 9.0          # portico back wall front face
PIL_Y = 6.37
PIL_X = [-5.0, -3.0, -1.0, 1.0, 3.0, 5.0]
Z_POST_TOP, Z_BRK_TOP, Z_BEAM_TOP, Z_JOIST_TOP, Z_PLANK_TOP, Z_FLOOR1 = 2.30, 2.42, 2.62, 2.74, 2.77, 2.95
YW0, YW1 = 6.22, 6.67  # upper north wall
DOG = Vector((0.0, 7.0, PZ))
EXIT_X = -2.5
HATCH = (-0.2, 0.2, 6.62, 7.42)

# ------------------------------------------------------------------ courtyard floor: individual stone slabs
def build_floor():
    mb = MB()
    uv = mb.bm.loops.layers.uv.new("UVMap")
    y = YS
    rows = []
    while y < YPF - 0.05:
        h = random.choice([0.32, 0.38, 0.42, 0.46, 0.52, 0.58])
        h = min(h, YPF - y)
        rows.append((y, h)); y += h
    for (y0, h) in rows:
        x = -CX + random.uniform(-0.4, 0)
        while x < CX:
            w = random.uniform(0.45, 1.15)
            x0, x1 = max(x, -CX), min(x + w, CX)
            if x1 - x0 > 0.08:
                gap = random.uniform(0.010, 0.022)
                sx, sy = x1 - x0 - gap, h - gap
                zoff = random.uniform(-0.007, 0.007)
                tilt = Euler((math.radians(random.uniform(-0.5, 0.5)), math.radians(random.uniform(-0.5, 0.5)), 0)).to_matrix().to_4x4()
                mat = Matrix.Translation(((x0 + x1) / 2, y0 + h / 2, zoff - 0.03)) @ tilt
                faces = mb.box_m((sx, sy, 0.06), mat, M["slab"], {"slabvar": random.random()})
                ox, oy, rot = random.uniform(0, 20), random.uniform(0, 20), random.choice([0, 1])
                for f in faces:
                    for lp in f.loops:
                        co = lp.vert.co
                        u, v = (co.x, co.y) if rot == 0 else (co.y, -co.x)
                        lp[uv].uv = (u + ox, v + oy)
            x += w
    slabs = mb.obj("S04_Floor_Slabs", C_COURT, bevel=0.012, seg=2)
    mb = MB()
    mb.box((-CX - 0.5, YS - 0.5, -0.2), (CX + 0.5, YPF + 0.1, -0.028), M["joint"])
    mb.obj("S04_Floor_Joints", C_COURT)
    return slabs


# ------------------------------------------------------------------ windows (Newari Windows asset)
WIN = {}


def load_windows():
    objs = L.import_obj(L.ENV + "/newari_windows/newari_windows.obj")
    groups = {"A": [], "B": [], "C": []}
    for o in objs:
        if o.type != "MESH":
            continue
        cy = sum((v.co.y for v in o.data.vertices)) / max(1, len(o.data.vertices))
        groups["A" if cy < 1.7 else "B" if cy < 3.9 else "C"].append(o)
    for k, objs_k in groups.items():
        o = L.join(objs_k, "S04_Win_" + k)
        for i, m in enumerate(o.data.materials):
            o.data.materials[i] = M["carve"]
        vs = [v.co for v in o.data.vertices]
        lo = Vector(map(min, *vs)); hi = Vector(map(max, *vs))
        o.data.transform(Matrix.Translation(-Vector((lo.x, (lo.y + hi.y) / 2, lo.z))))
        c = coll("S04_Win_" + k, C_SRC)
        L.link_only(o, c)
        WIN[k] = (c, hi - lo)  # size: depth(x), width(y), height(z)
        print("[win]", k, tuple(round(v, 2) for v in hi - lo))


def put_window(kind, pos, facing, c, name):
    """facing: '-Y', '+Y', '-X', '+X' (direction the window front looks)."""
    rot = {"-Y": -90, "+Y": 90, "-X": 180, "+X": 0}[facing]
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"; e.instance_collection = WIN[kind][0]
    e.location = pos; e.rotation_euler = (0, 0, math.radians(rot))
    c.objects.link(e)
    return e


def win_opening(kind, along, sill, frac=0.62):
    d, w, h = WIN[kind][1]
    return (along - w * frac / 2, along + w * frac / 2, sill + h * (1 - frac) / 2, sill + h * (1 + frac) / 2)


# ------------------------------------------------------------------ doors
def door_frame(mb, axis, along, face, z0, w, h, depth_dir, leaves="closed"):
    """Newari door frame on a wall face. axis: wall direction ('x' or 'y'); face: wall front plane coord;
    depth_dir: +1/-1 = direction from wall front into the building."""
    fw, fd = 0.12, 0.16  # frame width / depth

    def bx(a0, a1, t0, t1, z_0, z_1, mat):
        t0, t1 = sorted((face + depth_dir * t0, face + depth_dir * t1))
        if axis == "x":
            mb.box((a0, t0, z_0), (a1, t1, z_1), mat)
        else:
            mb.box((t0, a0, z_0), (t1, a1, z_1), mat)
    a0, a1 = along - w / 2, along + w / 2
    bx(a0 - fw, a0, -0.05, fd, z0, z0 + h, M["carve"])            # jambs
    bx(a1, a1 + fw, -0.05, fd, z0, z0 + h, M["carve"])
    bx(a0 - fw - 0.28, a1 + fw + 0.28, -0.06, fd, z0 + h, z0 + h + 0.14, M["carve"])  # lintel with ears
    bx(a0 - fw - 0.18, a1 + fw + 0.18, -0.08, fd, z0 + h + 0.14, z0 + h + 0.20, M["carve"])
    bx(a0 - fw, a1 + fw, -0.04, fd, z0 - 0.06, z0 + 0.04, M["carve"])  # threshold
    if leaves == "closed":
        bx(a0, along - 0.004, 0.06, 0.10, z0 + 0.04, z0 + h, M["wood"])
        bx(along + 0.004, a1, 0.06, 0.10, z0 + 0.04, z0 + h, M["wood"])
        for zz in (z0 + 0.35, z0 + h * 0.5, z0 + h - 0.3):  # cross battens
            bx(a0 + 0.03, a1 - 0.03, 0.035, 0.06, zz, zz + 0.07, M["wood"])


# ------------------------------------------------------------------ roof
def roof(mb, axis, a0, a1, eave_t, eave_z, ridge_t, pitch_deg, out_dir):
    """Sloped roof strip. axis: direction of the eave line; eave_t: eave position across;
    rises toward ridge_t. out_dir: unused sign helper (+1 when ridge_t > eave_t)."""
    a = math.radians(pitch_deg)
    run = abs(ridge_t - eave_t)
    slope_len = run / math.cos(a) + 0.05
    s = 1 if ridge_t > eave_t else -1
    mid_t = eave_t + s * run / 2
    mid_z = eave_z + run * math.tan(a) / 2
    length = a1 - a0
    if axis == "x":
        R = Matrix.Rotation(s * a, 4, "X")
        base = Matrix.Translation(((a0 + a1) / 2, mid_t, mid_z)) @ R
        mb.box_m((length, slope_len, 0.07), base @ Matrix.Translation((0, 0, 0.05)), M["roof"])
        mb.box_m((length, slope_len, 0.04), base @ Matrix.Translation((0, 0, -0.005)), M["plank"])
        # fascia board along the eave
        mb.box((a0, eave_t - s * 0.02 - 0.03, eave_z - 0.12), (a1, eave_t - s * 0.02 + 0.03, eave_z + 0.06), M["wood"])
    else:
        R = Matrix.Rotation(-s * a, 4, "Y")
        base = Matrix.Translation((mid_t, (a0 + a1) / 2, mid_z)) @ R
        mb.box_m((slope_len, length, 0.07), base @ Matrix.Translation((0, 0, 0.05)), M["roof"])
        mb.box_m((slope_len, length, 0.04), base @ Matrix.Translation((0, 0, -0.005)), M["plank"])
        mb.box((eave_t - s * 0.02 - 0.03, a0, eave_z - 0.12), (eave_t - s * 0.02 + 0.03, a1, eave_z + 0.06), M["wood"])


def strut(mb, p0, p1, mat, w=0.11):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.to_track_quat("Y", "Z").to_matrix().to_4x4()
    mb.box_m((w, d.length, w * 1.2), Matrix.Translation((p0 + p1) / 2) @ q, mat)


# ------------------------------------------------------------------ north building with portico
def build_north():
    # plinth, coping, floor tiles
    mb = MB()
    mb.box((-CX - 0.45, YPF, -0.1), (CX + 0.45, 9.5, PZ - 0.03), M["brick"])
    pf = MB()
    x = -CX
    while x < CX:  # stone coping blocks along the front edge
        w = random.uniform(0.7, 1.1); x1 = min(CX, x + w)
        pf.box((x + 0.006, YPF - 0.04, PZ - 0.08), (x1 - 0.006, YPF + 0.30, PZ), M["stone"])
        x = x1
    pf.box((-CX, YPF + 0.30, PZ - 0.03), (CX, YB, PZ - 0.002), M["tile"])
    pf.obj("S04_Portico_Floor", C_PORT, bevel=0.01)
    mb.obj("S04_Portico_Plinth", C_PORT)

    # pillars
    pm = MB()
    for px in PIL_X:
        pm.box((px - 0.17, PIL_Y - 0.17, PZ), (px + 0.17, PIL_Y + 0.17, PZ + 0.12), M["stone"])
        # post: square base block, octagonal-looking shaft (two rotated boxes), carved collars
        pm.box((px - 0.12, PIL_Y - 0.12, PZ + 0.12), (px + 0.12, PIL_Y + 0.12, 0.78), M["carve"])
        shaft_h = 2.10 - 0.78
        for rz in (0.0, math.pi / 4):
            pm.box_m((0.19, 0.19, shaft_h), Matrix.Translation((px, PIL_Y, 0.78 + shaft_h / 2)) @ Matrix.Rotation(rz, 4, "Z"), M["post"])
        for z0, z1, r in ((0.52, 0.58, 0.14), (0.72, 0.78, 0.135), (0.78, 0.82, 0.125), (1.30, 1.34, 0.12),
                          (1.86, 1.90, 0.12), (1.96, 2.04, 0.13), (2.04, 2.10, 0.14)):
            pm.box((px - r, PIL_Y - r, z0), (px + r, PIL_Y + r, z1), M["carve"])
        pm.box((px - 0.13, PIL_Y - 0.13, 2.18), (px + 0.13, PIL_Y + 0.13, Z_POST_TOP), M["carve"])
        # saddle bracket (tapered ends)
        faces = pm.box((px - 0.48, PIL_Y - 0.11, Z_POST_TOP), (px + 0.48, PIL_Y + 0.11, Z_BRK_TOP), M["carve"])
        for v in {v for f in faces for v in f.verts}:
            if v.co.z < Z_POST_TOP + 0.01:
                v.co.x = px + (v.co.x - px) * 0.55
    pm.obj("S04_Portico_Pillars", C_PORT, bevel=0.008)

    # ceiling: dalin beam, joists, planks, mud floor, cornice
    cm = MB()
    cm.box((-CX - 0.45, YW0, Z_BRK_TOP), (CX + 0.45, YW0 + 0.32, Z_BEAM_TOP), M["beam"])  # dalin
    cm.box((-CX - 0.45, YB - 0.16, Z_BEAM_TOP - 0.12), (CX + 0.45, YB, Z_BEAM_TOP), M["beam"])  # wall plate
    jx = [0.2 + 0.4 * k for k in range(15)]
    for x in sorted([-v for v in jx] + jx):
        cm.box((x - 0.045, YW0 - 0.14, Z_BEAM_TOP), (x + 0.045, YB, Z_JOIST_TOP), M["beam"])
    hm = MB()
    y = YW0
    while y < YB - 1e-4:
        y1 = min(YB, y + 0.20)
        mid = (y + y1) / 2
        if HATCH[2] < mid < HATCH[3]:
            cm.box((-CX - 0.45, y + 0.003, Z_JOIST_TOP), (HATCH[0], y1 - 0.003, Z_PLANK_TOP), M["plank"])
            cm.box((HATCH[1], y + 0.003, Z_JOIST_TOP), (CX + 0.45, y1 - 0.003, Z_PLANK_TOP), M["plank"])
            hm.box((HATCH[0], y + 0.003, Z_JOIST_TOP), (HATCH[1], y1 - 0.003, Z_PLANK_TOP), M["plank"])
        else:
            cm.box((-CX - 0.45, y + 0.003, Z_JOIST_TOP), (CX + 0.45, y1 - 0.003, Z_PLANK_TOP), M["plank"])
        y = y1
    # mud floor above the planks, with the hatch hole
    h0, h1, h2, h3 = HATCH
    for lo, hi in (((-CX - 0.45, YW0, Z_PLANK_TOP), (CX + 0.45, h2, Z_FLOOR1)),
                   ((-CX - 0.45, h3, Z_PLANK_TOP), (CX + 0.45, YB + 0.45, Z_FLOOR1)),
                   ((-CX - 0.45, h2, Z_PLANK_TOP), (h0, h3, Z_FLOOR1)),
                   ((h1, h2, Z_PLANK_TOP), (CX + 0.45, h3, Z_FLOOR1))):
        cm.box(lo, hi, M["dark"])
    hm.box((h0, h2, Z_PLANK_TOP), (h1, h3, Z_FLOOR1), M["dark"])
    # cornice band on the facade (covers the floor edge)
    cm.box((-CX - 0.45, YW0 - 0.10, Z_JOIST_TOP), (CX + 0.45, YW0 + 0.05, Z_FLOOR1 + 0.04), M["carve"])
    cm.obj("S04_Portico_Ceiling", C_PORT, bevel=0.006)
    hatch = hm.obj("S04_Portico_CeilingHatch", C_PORT, bevel=0.004)

    # back wall with exit door, second door and a lattice window
    wm = MB()
    win_a = win_opening("A", 0.0, 1.05)
    openings = [(EXIT_X - 0.45, EXIT_X + 0.45, PZ, 2.15), (3.0 - 0.45, 3.0 + 0.45, PZ, 2.10), win_a]
    wall(wm, "x", -CX - 0.45, CX + 0.45, YB, YB + 0.45, PZ - 0.05, Z_BEAM_TOP - 0.12, openings, M["brick"])
    # portico end walls
    wm.box((-CX - 0.45, YPF + 0.3, PZ - 0.05), (-CX, YB, Z_PLANK_TOP), M["brick"])
    wm.box((CX, YPF + 0.3, PZ - 0.05), (CX + 0.45, YB, Z_PLANK_TOP), M["brick"])
    wm.obj("S04_Portico_BackWall", C_PORT)
    put_window("A", (0.0, YB - 0.03, 1.05), "-Y", C_PORT, "S04_Portico_Window")
    dm = MB()
    door_frame(dm, "x", 3.0, YB, PZ, 0.9, 1.70, +1, leaves="closed")
    dm.obj("S04_Portico_Door2", C_PORT, bevel=0.005)
    em = MB()
    door_frame(em, "x", EXIT_X, YB, PZ, 0.9, 1.75, +1, leaves=None)
    # open leaves swung inward (into the dark)
    for sgn in (-1, 1):
        hx = EXIT_X + sgn * 0.45
        ang = math.radians(100) * -sgn
        R = Matrix.Translation((hx, YB + 0.40, PZ + 0.04 + 0.85)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Translation((-sgn * 0.225, 0, 0))
        em.box_m((0.45, 0.04, 1.70), R, M["wood"])
    exitdoor = em.obj("S04_ExitDoor", C_PORT, bevel=0.005)
    p = Vector((EXIT_X, YB, PZ))
    exitdoor.data.transform(Matrix.Translation(-p)); exitdoor.location = p
    L.interior_shell("S04_Portico_InnerRoom", (-CX, YB + 0.45, PZ - 0.05), (CX, 12.5, Z_PLANK_TOP), M["dark"], C_PORT)

    # upper storeys
    um = MB()
    ops = []
    winpos = []
    for x in (-4.4, -1.6, 1.6, 4.4):
        ops.append(win_opening("A", x, 3.55)); winpos.append(("A", x, 3.55))
    ops.append(win_opening("C", 0.0, 5.55)); winpos.append(("C", 0.0, 5.55))
    for x in (-4.2, 4.2):
        ops.append(win_opening("B", x, 5.65)); winpos.append(("B", x, 5.65))
    wall(um, "x", -CX - 0.45, CX + 0.45, YW0, YW1, Z_FLOOR1, 7.55 + 1.2 * math.tan(math.radians(26)) + 0.02, ops, M["brick"])
    um.box((-CX - 0.45, YW0 - 0.07, 5.30), (CX + 0.45, YW0 + 0.02, 5.42), M["carve"])  # band
    um.box((-CX - 0.45, YW0 - 0.05, 7.38), (CX + 0.45, YW0 + 0.02, 7.55), M["beam"])  # wall plate
    roof(um, "x", -CX - 1.2, CX + 1.2, YW0 - 1.2, 7.55, 10.6, 26, 1)
    for x in [-5.85 + 1.3 * k for k in range(10)]:
        strut(um, (x, YW0 - 0.05, 6.55), (x, YW0 - 0.95, 7.62), M["carve"])
    um.obj("S04_North_Upper", C_COURT)
    for i, (k, x, z) in enumerate(winpos):
        put_window(k, (x, YW0 + 0.03, z), "-Y", C_COURT, "S04_North_Win_%02d" % i)
    L.interior_shell("S04_North_UpperRooms", (-CX - 0.4, YW1, Z_FLOOR1), (CX + 0.4, 12.5, 7.5), M["dark"], C_COURT)
    return hatch, exitdoor


# ------------------------------------------------------------------ east / west buildings
def side_building(side):
    s = 1 if side == "E" else -1
    face = s * CX                    # facade plane (x)
    face_dir = "-X" if s > 0 else "+X"
    t0, t1 = sorted((face, face + s * 0.45))
    y0, y1 = YS, YPF + 0.3
    mat = M["brick_b"] if s > 0 else M["brick"]
    mb = MB()
    ops, wins, doors = [], [], []
    if s > 0:
        doors = [(-1.2, 0.12, 0.95, 1.80)]
        g = [("A", -4.3, 0.95), ("A", 2.9, 0.95)]
        f1 = [("A", -4.2, 3.25), ("A", -1.2, 3.25), ("A", 1.8, 3.25), ("A", 4.6, 3.25)]
        f2 = [("B", -3.4, 5.35), ("C", 1.2, 5.25)]
    else:
        doors = [(1.6, 0.12, 0.95, 1.80), (-3.6, 0.12, 0.85, 1.70)]
        g = [("A", -1.0, 0.95), ("A", 4.4, 0.95)]
        f1 = [("B", -3.6, 3.05), ("A", 0.0, 3.25), ("B", 3.4, 3.05)]
        f2 = [("A", -4.4, 5.45), ("A", -1.8, 5.45), ("A", 1.2, 5.45), ("A", 4.2, 5.45)]
    for (yy, z0, w, h) in doors:
        ops.append((yy - w / 2, yy + w / 2, z0, z0 + h))
    for (k, yy, z) in g + f1 + f2:
        ops.append(win_opening(k, yy, z)); wins.append((k, yy, z))
    wall(mb, "y", y0, y1, t0, t1, -0.05, 7.2 + 1.1 * math.tan(math.radians(26)) + 0.02, ops, mat)
    # stone plinth band, floor bands, wall plate
    mb.box((min(face, face - s * 0.06), y0, -0.05), (max(face, face - s * 0.06), y1, 0.25), M["stone"])
    for zb in (2.55, 4.95):
        mb.box((min(face, face - s * 0.07), y0, zb), (max(face, face - s * 0.07), y1, zb + 0.13), M["carve"])
    roof(mb, "y", y0 - 1.0, y1, face - s * 1.1, 7.2, face + s * 3.6, 26, 1)
    for yy in [y0 + 0.5 + 1.25 * k for k in range(11)]:
        strut(mb, (face - s * 0.05, yy, 6.25), (face - s * 0.9, yy, 7.25), M["carve"])
    mb.obj("S04_%s_Building" % side, C_COURT, bevel=0.0)
    dm = MB()
    for (yy, z0, w, h) in doors:
        door_frame(dm, "y", yy, face, z0, w, h, s, leaves="closed" if (s > 0 or yy < 0) else None)
    dm.obj("S04_%s_Doors" % side, C_COURT, bevel=0.005)
    for i, (k, yy, z) in enumerate(wins):
        put_window(k, (face - s * 0.03, yy, z), face_dir, C_COURT, "S04_%s_Win_%02d" % (side, i))
    lo = (min(t1, t1 + s * 6), y0, -0.05); hi = (max(t1, t1 + s * 6), y1, 7.2)
    L.interior_shell("S04_%s_Rooms" % side, lo, hi, M["dark"], C_COURT)
    if s < 0:  # west: wooden balcony on the 2nd floor
        bm = MB()
        bx0, by0, by1, bz = face, -2.6, 2.6, 4.95
        bm.box((bx0, by0, bz), (bx0 + 0.75, by1, bz + 0.10), M["plank"])
        bm.box((bx0 + 0.68, by0, bz + 0.9), (bx0 + 0.78, by1, bz + 1.0), M["carve"])
        bm.box((bx0 + 0.70, by0, bz + 0.10), (bx0 + 0.76, by1, bz + 0.18), M["carve"])
        yy = by0
        while yy <= by1 + 1e-4:
            bm.box((bx0 + 0.71, yy - 0.02, bz + 0.18), (bx0 + 0.75, yy + 0.02, bz + 0.9), M["carve"])
            yy += 0.13
        for yy in (by0 + 0.05, 0.0, by1 - 0.05):
            strut(bm, (bx0 + 0.02, yy, bz - 0.6), (bx0 + 0.62, yy, bz - 0.02), M["carve"], w=0.09)
        bm.obj("S04_W_Balcony", C_COURT, bevel=0.004)


# ------------------------------------------------------------------ south: Jhwabaha house (3D Warehouse)
def build_south():
    objs = L.import_obj(L.ENV + "/jhwabaha/jhwabaha.obj")
    keep = [o for o in objs if o.name.startswith("ID12_010")]
    for o in objs:
        if o not in keep:
            bpy.data.objects.remove(o)
    o = L.join(keep, "S04_S_House")
    remap = {
        "material": M["wood"], "material_0": M["wood"], "__Charcoal_": M["carve"], "material_1": M["carve"],
        "Color_C04": M["dark"], "Color_C14": M["wood"], "Color_C13": M["wood"], "__Brick_antique_": M["brick"],
        "Roofing_Shingles_Variable": M["roof"], "Stone_Pavers_Flagstone_Gray": M["stone"],
        "Stone_Vein_Gray": M["stone"], "material_2": M["roof"], "_0020_Red": M["cloth"],
        "Wood_Cherry_Original": M["carve"], "__Wood_cherry_": M["carve"], "__Wood_Cherry_Original_1": M["carve"],
        "Wood_Cherry_Original_1": M["carve"], "__Goldenrod_": M["brass"], "__Metal_floor_": M["carve"],
        "__White_": M["brass"], "Metal_Aluminum_Anodized": M["brass"], "material_2_3": M["wood"],
    }
    me = o.data
    names = [m.name.split(".")[0] if m else "" for m in me.materials]
    # delete the modern railing (aluminium + gold tips below 1.6 m) and the sign plaque
    bm = bmesh.new(); bm.from_mesh(me)
    kill = []
    for f in bm.faces:
        n = names[f.material_index] if f.material_index < len(names) else ""
        c = f.calc_center_median()
        if n == "Metal_Aluminum_Anodized" or n == "material_2_3" or (n == "__Goldenrod_" and c.z < 1.6):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me); bm.free()
    for i, n in enumerate(names):
        me.materials[i] = remap.get(n, M["wood"])
    # rotate 180 so the facade (model -Y, brick plane y=12.9) faces +Y at y = YS
    cxm = 23.77
    T = Matrix.Translation((0, YS, 0)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation((-cxm, -12.9, 0))
    me.transform(T)
    L.link_only(o, C_COURT)
    print("[south] faces", len(me.polygons), "killed", len(kill))
    return o


# ------------------------------------------------------------------ background masses beyond the roofs
def build_background():
    mb = MB()
    random.seed(11)
    for (x0, x1, y0, y1) in ((-16, -9, -14, 14), (9, 16, -14, 14), (-9, 9, 12, 18), (-9, 9, -18, -12)):
        # a few blocks of different heights
        n = 3
        for i in range(n):
            if x1 - x0 > y1 - y0:
                a0 = x0 + (x1 - x0) * i / n; a1 = x0 + (x1 - x0) * (i + 1) / n
                lo, hi = (a0, y0, -0.1), (a1, y1, random.uniform(5.8, 6.4))
            else:
                a0 = y0 + (y1 - y0) * i / n; a1 = y0 + (y1 - y0) * (i + 1) / n
                lo, hi = (x0, a0, -0.1), (x1, a1, random.uniform(5.8, 6.4))
            mb.box(lo, hi, random.choice([M["brick"], M["brick_b"]]))
            # flat roof slab hint
            mb.box((lo[0] - 0.3, lo[1] - 0.3, hi[2]), (hi[0] + 0.3, hi[1] + 0.3, hi[2] + 0.12), M["roof"])
    mb.obj("S04_Background_Blocks", C_COURT)


# ------------------------------------------------------------------ dressing helpers
def marigold_template():
    """Ruffled marigold head (~5.5 cm): icosphere with petal-like radial spikes, flattened."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.027)
    rnd = random.Random(7)
    for v in bm.verts:
        n = v.co.normalized()
        ruff = 0.75 + 0.5 * rnd.random() ** 2
        v.co = n * 0.027 * ruff
        v.co.z *= 0.8
    verts = [v.co.copy() for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return verts, faces


def marigold_material():
    m = L.new_mat("S04_Marigold")
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = L.bsdf_of(m)
    at = N.new("ShaderNodeAttribute"); at.attribute_type = "GEOMETRY"; at.attribute_name = "mg"
    col = L.mix_rgb(nt, "MIX", (0.80, 0.20, 0.006), (0.92, 0.42, 0.01), at.outputs["Fac"])
    Lk.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    b.inputs["Subsurface Weight"].default_value = 0.25
    b.inputs["Subsurface Radius"].default_value = (0.01, 0.004, 0.002)
    nz = N.new("ShaderNodeTexVoronoi"); nz.inputs["Scale"].default_value = 420
    tc = N.new("ShaderNodeTexCoord"); Lk.new(tc.outputs["Object"], nz.inputs[0])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.7
    Lk.new(nz.outputs["Distance"], bp.inputs["Height"]); Lk.new(bp.outputs[0], b.inputs["Normal"])
    return m


MG_T = None


def garland(bm, layer, pts, spacing=0.034):
    """Place marigold heads every `spacing` along a polyline."""
    global MG_T
    tv, tf = MG_T
    acc = 0.0
    seq = []
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        t = 0.0
        while t < seg:
            seq.append(a.lerp(b, t / seg))
            t += spacing
    for p in seq:
        R = Euler((random.uniform(0, 6.28), random.uniform(0, 6.28), random.uniform(0, 6.28))).to_matrix()
        s = random.uniform(0.85, 1.12)
        vs = [bm.verts.new(p + (R @ v) * s) for v in tv]
        val = random.random() ** 1.5
        for f in tf:
            try:
                ff = bm.faces.new([vs[i] for i in f])
                ff[layer] = val
            except ValueError:
                pass
    return len(seq)


def swag(p0, p1, sag, n=24):
    p0, p1 = Vector(p0), Vector(p1)
    return [p0.lerp(p1, i / n) - Vector((0, 0, sag * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]


def build_marigolds():
    global MG_T
    MG_T = marigold_template()
    bm = bmesh.new()
    layer = bm.faces.layers.float.new("mg")
    n = 0
    yb = PIL_Y - 0.14
    for xa, xb in ((-3.0, -1.0), (-1.0, 1.0), (1.0, 3.0)):  # swags across three bays
        n += garland(bm, layer, swag((xa, yb, 2.36), (xb, yb, 2.36), 0.38))
        n += garland(bm, layer, swag((xa + 0.1, yb - 0.01, 2.36), (xb - 0.1, yb - 0.01, 2.36), 0.22))
    for px in (-1.0, 1.0):  # strands down two pillars
        n += garland(bm, layer, [Vector((px - 0.12, yb, 2.36)), Vector((px - 0.13, yb, 1.55))])
        n += garland(bm, layer, [Vector((px + 0.12, yb, 2.36)), Vector((px + 0.13, yb, 1.62))])
    # exit door lintel festoon
    yd = YB - 0.10
    n += garland(bm, layer, swag((EXIT_X - 0.55, yd, 2.28), (EXIT_X + 0.55, yd, 2.28), 0.2))
    for dx in (-0.55, 0.55):
        n += garland(bm, layer, [Vector((EXIT_X + dx, yd, 2.28)), Vector((EXIT_X + dx, yd, 1.75))])
    me = bpy.data.meshes.new("S04_Marigold_Strings")
    bm.to_mesh(me); bm.free()
    me.materials.append(marigold_material())
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new("S04_Marigold_Strings", me); C_DRESS.objects.link(o)
    # thread / tie at each swag end
    print("[marigold] heads", n)
    return o


def diyo_template():
    bm = bmesh.new()
    prof = [(0.0, 0.0), (0.03, 0.0), (0.044, 0.008), (0.05, 0.022), (0.046, 0.024), (0.040, 0.012), (0.0, 0.009)]
    vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((a, b)) for a, b in zip(vs, vs[1:])]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.radians(360), steps=28, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # pinch a spout at +x
    for v in bm.verts:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.035 and v.co.x > 0:
            ang = math.atan2(v.co.y, v.co.x)
            k = max(0.0, 1 - abs(ang) / 0.5)
            v.co.x += 0.012 * k; v.co.y *= 1 - 0.35 * k
    me = bpy.data.meshes.new("S04_Diyo")
    bm.to_mesh(me); bm.free()
    me.materials.append(M["clay"]); me.materials.append(M["oil"]); me.materials.append(M["flame"])
    for p in me.polygons:
        p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(me)
    g = bmesh.ops.create_circle(bm, cap_ends=True, radius=0.038, segments=24)
    bmesh.ops.translate(bm, vec=(0, 0, 0.017), verts=g["verts"])
    for f in {f for v in g["verts"] for f in v.link_faces}:
        f.material_index = 1
    g = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.006)
    bmesh.ops.scale(bm, vec=(1, 1, 2.4), verts=g["verts"])
    bmesh.ops.translate(bm, vec=(0.04, 0, 0.033), verts=g["verts"])
    for f in {f for v in g["verts"] for f in v.link_faces}:
        f.material_index = 2
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0025, radius2=0.0015, depth=0.016)
    bmesh.ops.translate(bm, vec=(0.038, 0, 0.022), verts=g["verts"])
    for f in {f for v in g["verts"] for f in v.link_faces}:
        f.material_index = 1
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("S04_Diyo_Src", me); C_SRC.objects.link(o)
    return o


def rangoli():
    m = L.new_mat("S04_Rangoli")
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = L.bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9; nz.inputs["Detail"].default_value = 10
    Lk.new(tc.outputs["Object"], nz.inputs[0])
    gr = N.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.6, 3.6, 1)
    Lk.new(tc.outputs["Object"], mp.inputs[0]); Lk.new(mp.outputs[0], gr.inputs[0])
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    Lk.new(nz.outputs["Fac"], mul.inputs[0]); Lk.new(gr.outputs["Fac"], mul.inputs[1])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.16; cr.color_ramp.elements[1].position = 0.32
    Lk.new(mul.outputs[0], cr.inputs[0])
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 4
    Lk.new(tc.outputs["Object"], nz2.inputs[0])
    col = L.mix_rgb(nt, "MIX", (0.55, 0.03, 0.02), (0.85, 0.25, 0.02), nz2.outputs["Fac"])
    Lk.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 1.0
    alpha = N.new("ShaderNodeMath"); alpha.operation = "MULTIPLY"; alpha.inputs[1].default_value = 0.9
    Lk.new(cr.outputs[0], alpha.inputs[0]); Lk.new(alpha.outputs[0], b.inputs["Alpha"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(EXIT_X + 0.05, YB - 0.62, PZ + 0.002))
    o = bpy.context.object; o.name = "S04_Rangoli"; o.scale = (1.0, 0.7, 1)
    o.data.materials.append(m)
    L.link_only(o, C_DRESS)


def leaf_material():
    m = L.new_mat("S04_Creeper_Leaf")
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = L.bsdf_of(m)
    t = N.new("ShaderNodeTexImage"); t.image = L.img(L.ph_file("jacaranda_tree_leaves", "diff"))
    a = N.new("ShaderNodeTexImage"); a.image = L.img(L.ph_file("jacaranda_tree_leaves", "alpha"), False)
    hsv = N.new("ShaderNodeHueSaturation"); hsv.inputs["Value"].default_value = 0.75; hsv.inputs["Hue"].default_value = 0.52
    Lk.new(t.outputs[0], hsv.inputs["Color"])
    Lk.new(hsv.outputs[0], b.inputs["Base Color"]); Lk.new(a.outputs[0], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Transmission Weight"].default_value = 0.0
    b.inputs["Subsurface Weight"].default_value = 0.15
    nrm = L.ph_file("jacaranda_tree_leaves", "nor")
    if nrm:
        n = N.new("ShaderNodeTexImage"); n.image = L.img(nrm, False)
        nm = N.new("ShaderNodeNormalMap"); Lk.new(n.outputs[0], nm.inputs["Color"]); Lk.new(nm.outputs[0], b.inputs["Normal"])
    return m


def creeper(name, wall_x, normal_sign, y0, y1, ztop, n_stems, density=55):
    """Leaf cards climbing a wall plane x=wall_x (normal along +/-x)."""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    cards = 0
    for s in range(n_stems):
        y = random.uniform(y0, y1); z = 0.05
        top = ztop * random.uniform(0.55, 1.0)
        while z < top:
            y += random.uniform(-0.12, 0.12); y = min(max(y, y0 - 0.3), y1 + 0.3)
            z += 0.06
            k = int(random.random() < density / 100 * (1.25 - 0.5 * z / ztop))
            for _ in range(k * random.randint(1, 3)):
                sz = random.uniform(0.14, 0.26)
                off = random.uniform(0.02, 0.22)
                c = Vector((wall_x + normal_sign * off, y + random.uniform(-0.15, 0.15), z + random.uniform(-0.1, 0.1)))
                R = (Matrix.Rotation(random.uniform(0, 6.28), 3, "X") @
                     Matrix.Rotation(random.uniform(-0.8, 0.8), 3, "Z") @ Matrix.Rotation(random.uniform(-0.5, 0.5), 3, "Y"))
                corners = [Vector((0, -0.5, -0.5)), Vector((0, 0.5, -0.5)), Vector((0, 0.5, 0.5)), Vector((0, -0.5, 0.5))]
                vs = [bm.verts.new(c + R @ (q * sz)) for q in corners]
                f = bm.faces.new(vs)
                for lp, uvv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    lp[uv].uv = uvv
                cards += 1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(LEAF)
    o = bpy.data.objects.new(name, me); C_DRESS.objects.link(o)
    print("[creeper]", name, cards)
    return o


def chaitya(pos):
    mb = MB()
    x, y = pos
    mb.box((x - 0.55, y - 0.55, 0), (x + 0.55, y + 0.55, 0.22), M["stone"])
    mb.box((x - 0.42, y - 0.42, 0.22), (x + 0.42, y + 0.42, 0.40), M["stone"])
    mb.box((x - 0.34, y - 0.34, 0.40), (x + 0.34, y + 0.34, 0.50), M["stone"])
    o = mb.obj("S04_Chaitya", C_DRESS, bevel=0.012)
    bm = bmesh.new()
    g = bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.30)
    for v in g["verts"]:
        if v.co.z < 0:
            v.co.z = 0
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.translate(bm, vec=(x, y, 0.50), verts=bm.verts)
    g = bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(0.22, 0.22, 0.18), verts=g["verts"]); bmesh.ops.translate(bm, vec=(x, y, 0.89), verts=g["verts"])
    for i in range(6):
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.10 - i * 0.013, radius2=0.09 - i * 0.013, depth=0.05)
        bmesh.ops.translate(bm, vec=(x, y, 1.005 + i * 0.055), verts=g["verts"])
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.05, radius2=0.0, depth=0.16)
    bmesh.ops.translate(bm, vec=(x, y, 1.40), verts=g["verts"])
    me = bpy.data.meshes.new("S04_Chaitya_Top"); bm.to_mesh(me); bm.free()
    me.materials.append(M["stone"])
    for p in me.polygons:
        p.use_smooth = True
    o2 = bpy.data.objects.new("S04_Chaitya_Top", me); C_DRESS.objects.link(o2)


def prop_src(mid, name, target_h=None, scale=None, pick=None):
    objs = L.import_gltf(L.PH + "/models/%s/%s_1k.gltf" % (mid, mid))
    meshes = [o for o in objs if o.type == "MESH"]
    if pick:
        meshes = pick(meshes)
        for o in objs:
            if o not in meshes:
                bpy.data.objects.remove(o)
        objs = meshes
    o = L.join(objs, name)
    size = L.origin_bottom(o)
    if target_h:
        f = target_h / size.z
        o.data.transform(Matrix.Scale(f, 4))
    elif scale:
        o.data.transform(Matrix.Scale(scale, 4))
    L.link_only(o, C_SRC)
    return o


def build_dressing():
    global LEAF
    LEAF = leaf_material()
    # v008: marigold strings removed (owner request)
    rangoli()
    chaitya((-3.9, -3.7))
    # clay diyos on the portico edge (coping) and at the chaitya
    d = diyo_template()
    for i, (x, y, z, r) in enumerate([(-0.75, YPF + 0.12, PZ, 200), (0.85, YPF + 0.10, PZ, 160), (2.2, YPF + 0.14, PZ, 185),
                                      (-3.9 + 0.2, -3.7 - 0.36, 0.40, 250), (-3.9 - 0.22, -3.7 - 0.34, 0.40, 290)]):
        L.place(d, "S04_Diyo_Inst_%02d" % i, (x, y, z), r, 1.0, C_DRESS)
    # panas (brass oil-lamp stands) flanking the exit door - owner's asset, decimated
    objs = L.import_obj(L.ROOT + "/blender/assets/s02/found/panas_lamp/source/Panas.obj", up="Y", forward="NEGATIVE_Z")
    pan = L.join(objs, "S04_Panas_Src")
    md = pan.modifiers.new("Dec", "DECIMATE"); md.ratio = 0.06
    with bpy.context.temp_override(object=pan, active_object=pan):
        bpy.ops.object.modifier_apply(modifier=md.name)
    size = L.origin_bottom(pan)
    pan.data.transform(Matrix.Scale(0.72 / size.z, 4))
    pan.data.materials.clear(); pan.data.materials.append(M["brass"])
    for p in pan.data.polygons:
        p.use_smooth = True
    L.link_only(pan, C_SRC)
    print("[panas] faces", len(pan.data.polygons), "orig height", round(size.z, 3))
    L.place(pan, "S04_Panas_01", (EXIT_X - 0.85, YB - 0.30, PZ), 0, 1.0, C_DRESS)
    L.place(pan, "S04_Panas_02", (EXIT_X + 0.85, YB - 0.30, PZ), 30, 1.0, C_DRESS)
    L.place(pan, "S04_Panas_03", (5.35, -5.2, 0.0), 10, 1.25, C_DRESS)
    L.place(pan, "S04_Panas_04", (5.45, -4.5, 0.0), 50, 1.1, C_DRESS)
    # pots and plants (Poly Haven)
    pp1 = prop_src("potted_plant_01", "S04_PottedPlant01_Src")
    pp2 = prop_src("potted_plant_02", "S04_PottedPlant02_Src")
    pot = prop_src("planter_pot_clay", "S04_ClayPot_Src")
    fern = prop_src("fern_02", "S04_Fern_Src", scale=0.45)
    peri = prop_src("periwinkle_plant", "S04_Periwinkle_Src")
    cpot = prop_src("ceramic_pot", "S04_CeramicPot_Src")
    brass = prop_src("brass_pot_01", "S04_BrassPot_Src")
    bucket = prop_src("wooden_bucket_01", "S04_Bucket_Src")
    basket = prop_src("wicker_basket_01", "S04_Basket_Src")
    rocks = L.import_gltf(L.PH + "/models/rock_moss_set_01/rock_moss_set_01_1k.gltf")
    rock_src = []
    bpy.context.view_layer.update()
    rmeshes = sorted([o for o in rocks if o.type == "MESH"], key=lambda o: -len(o.data.polygons))[:3]
    for o in rmeshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in rocks:
        if o not in rmeshes:
            bpy.data.objects.remove(o)
    for i, ro in enumerate(rmeshes):
        r = L.join([ro], "S04_Rock%d_Src" % i)
        sz = L.origin_bottom(r)
        r.data.transform(Matrix.Scale(0.42 / max(sz.x, sz.y), 4))
        L.link_only(r, C_SRC); rock_src.append(r)

    P = lambda s, n, loc, rz=0, k=1.0: L.place(s, n, loc, rz, k, C_DRESS)
    P(pp1, "S04_Plant_01", (-5.45, 5.45, 0), 20)
    P(pp1, "S04_Plant_02", (5.40, 5.35, 0), 140, 0.9)
    P(pp2, "S04_Plant_03", (-5.35, -5.6, 0), 60, 1.1)
    P(pp2, "S04_Plant_04", (-5.5, 1.0, 0), 200, 0.9)
    P(pot, "S04_BigPot_01", (4.85, -3.6, 0), 0, 2.6)
    P(fern, "S04_BigPot_01_Fern", (4.85, -3.6, 0.50), 30, 1.0)
    P(pot, "S04_BigPot_02", (-5.3, 3.4, 0), 70, 2.2)
    P(fern, "S04_BigPot_02_Fern", (-5.3, 3.4, 0.43), 100, 0.85)
    for i, x in enumerate((4.2, 4.65, 5.1, 5.55)):
        P(pot, "S04_EdgePot_%02d" % i, (x, YB - 0.3, PZ), i * 40, 1.15)
        P(peri, "S04_EdgePot_%02d_Plant" % i, (x, YB - 0.3, PZ + 0.22), i * 70, 0.3)
    P(cpot, "S04_WaterPot", (3.75, YB - 0.38, PZ), 15, 0.9)
    P(brass, "S04_BrassPot", (-4.6, YB - 0.30, PZ), 0, 1.0)
    P(basket, "S04_Basket", (-4.1, YB - 0.45, PZ), 25, 1.0)
    P(bucket, "S04_Bucket", (-5.35, 1.9, 0), 0, 0.85)
    for i, (x, y, rz, k) in enumerate([(4.35, -3.1, 10, 0.9), (4.4, -4.15, 80, 0.7), (5.3, -2.9, 140, 0.6),
                                       (-5.5, -4.8, 30, 0.8), (-4.7, -5.75, 200, 0.6), (-3.3, -3.0, 0, 0.45)]):
        P(rock_src[i % 3], "S04_Rock_%02d" % i, (x, y, -0.01), rz, k)
    # creepers: west facade (around the balcony) and the east end of the north portico
    creeper("S04_Creeper_West", -CX, 1, -2.0, 3.6, 5.2, 24, 38)
    creeper("S04_Creeper_East", CX, -1, 3.9, 6.0, 3.6, 10, 38)
    build_veg2(pot, peri, fern, d)



# ------------------------------------------------------------------ v008: more vegetation, stones, life
def prop_set(mid, prefix, scale=1.0):
    """Import a Poly Haven model set; every mesh becomes its own instance source (bottom-centre origin)."""
    objs = L.import_gltf(L.PH + "/models/%s/%s_1k.gltf" % (mid, mid))
    bpy.context.view_layer.update()
    meshes = [o for o in objs if o.type == "MESH"]
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in objs:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    out = []
    for i, o in enumerate(meshes):
        o.data = o.data.copy()
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
        L.origin_bottom(o)
        if scale != 1.0:
            o.data.transform(Matrix.Scale(scale, 4))
        o.name = "%s_%d_Src" % (prefix, i)
        L.link_only(o, C_SRC); out.append(o)
    return out


def mesh_size(o):
    vs = [v.co for v in o.data.vertices]
    return Vector(map(max, *vs)) - Vector(map(min, *vs))


def tulsi_math(pos, plant_srcs, diyo):
    x, y = pos
    mb = MB()
    mb.box((x - 0.36, y - 0.36, 0), (x + 0.36, y + 0.36, 0.10), M["stone"])
    mb.box((x - 0.27, y - 0.27, 0.10), (x + 0.27, y + 0.27, 0.72), M["brick"])
    mb.box((x - 0.33, y - 0.33, 0.72), (x + 0.33, y + 0.33, 0.80), M["brick"])
    mb.box((x - 0.12, y - 0.285, 0.30), (x + 0.12, y - 0.24, 0.52), M["dark"])  # small diyo niche
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):  # raised corner horns
        mb.box((x + sx * 0.33 - 0.06, y + sy * 0.33 - 0.06, 0.80), (x + sx * 0.33 + 0.06, y + sy * 0.33 + 0.06, 0.92), M["brick"])
    mb.obj("S04_TulsiMath", C_DRESS, bevel=0.006)
    soil = MB(); soil.box((x - 0.27, y - 0.27, 0.78), (x + 0.27, y + 0.27, 0.80), M["joint"]); soil.obj("S04_TulsiMath_Soil", C_DRESS)
    for i, (dx, dy, k) in enumerate(((0, 0, 1.6), (0.08, -0.06, 1.3), (-0.07, 0.05, 1.2))):
        L.place(plant_srcs[i % len(plant_srcs)], "S04_Tulsi_%d" % i, (x + dx, y + dy, 0.79), random.uniform(0, 360), k, C_DRESS)
    L.place(diyo, "S04_Diyo_Tulsi", (x, y - 0.27, 0.30), 270, 1.0, C_DRESS)


def build_veg2(pot, peri, fern, diyo):
    random.seed(21)
    grass = prop_set("grass_medium_01", "S04_Grass1") + prop_set("grass_medium_02", "S04_Grass2")
    berm = prop_set("grass_bermuda_01", "S04_Bermuda")
    weed = prop_set("weed_plant_02", "S04_Weed") + prop_set("dandelion_01", "S04_Dandelion")
    moss = prop_set("moss_01", "S04_Moss", 1.6)
    shrubs = prop_set("shrub_02", "S04_Shrub2")
    small = prop_set("shrub_03", "S04_Shrub3")
    stones = prop_set("stone_01", "S04_Stone1", 1.4) + prop_set("namaqualand_stones_01", "S04_NStone", 1.3)
    rocks2 = prop_set("rock_moss_set_02", "S04_RockB")
    broom = prop_set("wooden_broom", "S04_Broom")
    stool = prop_set("wooden_stool_01", "S04_Stool")
    for r in rocks2:
        sz = mesh_size(r)
        r.data.transform(Matrix.Scale(0.38 / max(sz.x, sz.y), 4))
    keep_out = [((-3.9, -3.7), 0.9), ((4.85, -3.6), 0.5), ((-5.3, 3.4), 0.45), ((4.4, 2.6), 0.5)]

    def free(x, y):
        return all((Vector((x, y)) - Vector(c)).length > r for c, r in keep_out)

    n = 0
    edges = [lambda: (random.uniform(-5.9, 5.9), random.uniform(-5.35, -5.0)),
             lambda: (random.uniform(-5.95, -5.6), random.uniform(-5.3, 5.8)),
             lambda: (random.uniform(5.6, 5.95), random.uniform(-5.3, 5.8)),
             lambda: (random.uniform(-5.9, 5.9), random.uniform(5.75, 5.97))]
    for i in range(170):  # grass and weeds along the wall bases
        x, y = random.choice(edges)()
        if not free(x, y):
            continue
        src = random.choice(grass + berm + weed + weed)
        L.place(src, "S04_Tuft_%03d" % n, (x, y, -0.02), random.uniform(0, 360), random.uniform(0.8, 1.5), C_DRESS); n += 1
    for i in range(70):  # sparse tufts in the open paving joints
        x, y = random.uniform(-5.5, 5.5), random.uniform(-5.0, 5.5)
        if not free(x, y):
            continue
        L.place(random.choice(berm + weed), "S04_Tuft_%03d" % n, (x, y, -0.02), random.uniform(0, 360), random.uniform(0.35, 0.7), C_DRESS); n += 1
    for i in range(140):  # moss cushions near the walls
        x, y = random.choice(edges)()
        L.place(random.choice(moss), "S04_MossPatch_%03d" % i, (x, y, -0.01), random.uniform(0, 360), random.uniform(0.8, 1.6), C_DRESS)
    sh = sorted(shrubs, key=lambda o: -mesh_size(o).z)
    L.place(sh[0], "S04_CornerShrub_01", (-5.1, -4.7, -0.02), 40, 0.8, C_DRESS)
    L.place(sh[min(1, len(sh) - 1)], "S04_CornerShrub_02", (-4.4, -5.0, -0.02), 160, 0.6, C_DRESS)
    tulsi_math((4.4, 2.6), small, diyo)
    pots = [((-5.6, 6.72, PZ), 1.3, peri, 0.3), ((-4.55, 6.75, PZ), 1.0, small[0], 0.9), ((-3.55, 6.72, PZ), 1.5, fern, 0.22),
            ((3.6, 6.72, PZ), 1.1, small[-1], 1.0), ((4.45, 6.75, PZ), 1.4, peri, 0.35),
            ((-5.65, -2.4, 0), 1.8, fern, 0.32), ((-5.6, -1.6, 0), 1.2, peri, 0.32), ((-5.65, 4.6, 0), 1.6, small[0], 1.4),
            ((5.65, 1.0, 0), 1.7, fern, 0.3), ((5.62, 1.8, 0), 1.1, small[-1], 1.1), ((5.65, -1.9, 0), 2.0, fern, 0.38)]
    for i, (loc, k, plant, pk) in enumerate(pots):
        L.place(pot, "S04_Pot2_%02d" % i, loc, random.uniform(0, 360), k, C_DRESS)
        L.place(plant, "S04_Pot2_%02d_Plant" % i, (loc[0], loc[1], loc[2] + 0.2 * k), random.uniform(0, 360), pk, C_DRESS)
    spots = [(4.55, -3.1), (5.15, -4.1), (-4.5, -3.3), (-3.3, -4.3), (-3.5, -3.1), (-4.8, -4.2), (-5.6, 3.0), (-4.9, 3.6),
             (5.3, 1.4), (4.0, 2.2), (-5.3, -2.0), (5.2, -2.3)]
    for i, (x, y) in enumerate(spots):
        src = random.choice(stones + rocks2)
        L.place(src, "S04_Stone2_%02d" % i, (x, y, -0.015), random.uniform(0, 360), random.uniform(0.7, 1.3), C_DRESS)
    b = L.place(broom[0], "S04_Broom", (5.80, -2.6, 0.0), 0, 1.0, C_DRESS)
    b.rotation_euler = (0, math.radians(12), math.radians(90))
    L.place(stool[0], "S04_Stool", (-4.9, 2.3, 0.0), 25, 0.8, C_DRESS)
    print("[veg2] tufts", n)

# ------------------------------------------------------------------ lights, world, markers, cameras
def sun_vec(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))


def build_lights(az=float(os.environ.get("S04_AZ", 160)), el=float(os.environ.get("S04_EL", 42))):
    sv = sun_vec(az, el)
    ld = bpy.data.lights.new("S04_Sun", "SUN"); ld.energy = 4.5; ld.angle = math.radians(0.6)
    ld.color = (1.0, 0.93, 0.84)
    sun = bpy.data.objects.new("S04_Sun", ld); C_LIGHT.objects.link(sun)
    sun.rotation_euler = sv.to_track_quat("Z", "Y").to_euler()
    w = bpy.data.worlds.new("S04_World"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; N = nt.nodes; Lk = nt.links
    bg = next(n for n in N if n.type == "BACKGROUND")
    env = N.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(L.PH + "/qwantani_morning_puresky_4k.hdr", check_existing=True)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    Lk.new(tc.outputs["Generated"], mp.inputs[0]); Lk.new(mp.outputs[0], env.inputs[0])
    # rotate the HDRI so its (clamped) sun side matches the sun lamp
    try:
        import numpy as np
        im = env.image; wdt, hgt = im.size
        px = np.empty(wdt * hgt * 4, dtype=np.float32); im.pixels.foreach_get(px)
        lum = px.reshape(hgt, wdt, 4)[..., :3].sum(-1)
        r, c = np.unravel_index(np.argmax(lum), lum.shape)
        u = (c + 0.5) / wdt
        a_img = 2 * math.pi - 2 * math.pi * u
        phi = math.atan2(sv.y, sv.x)
        mp.inputs["Rotation"].default_value = (0, 0, a_img - phi)
        print("[world] hdri sun u=%.3f v=%.3f peak=%.0f rot=%.1f deg" % (u, (r + 0.5) / hgt, lum[r, c], math.degrees(a_img - phi)))
    except Exception as e:
        print("[world] rotation skipped", e)
    # gentle bounce fill from the sunlit floor toward the shaded south house (not seen by camera)
    fd = bpy.data.lights.new("S04_Fill_Bounce", "AREA"); fd.shape = "RECTANGLE"; fd.size = 11.0; fd.size_y = 3.0
    fd.energy = float(os.environ.get("S04_FILL", 2500)); fd.color = (1.0, 0.9, 0.78)
    fo = bpy.data.objects.new("S04_Fill_Bounce", fd); C_LIGHT.objects.link(fo)
    fo.location = (0, 2.0, 3.0); fo.rotation_euler = (math.radians(-95), 0, 0)
    fo.visible_camera = False; fo.visible_glossy = False
    clamp = N.new("ShaderNodeVectorMath"); clamp.operation = "MINIMUM"; clamp.inputs[1].default_value = (3.0, 3.0, 3.0)
    Lk.new(env.outputs[0], clamp.inputs[0]); Lk.new(clamp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = float(os.environ.get("S04_SKY", 3.0))


def build_markers(hatch, exitdoor):
    def empty(name, loc, rotz=0.0, shape="ARROWS", size=0.3):
        e = bpy.data.objects.new(name, None); e.empty_display_type = shape; e.empty_display_size = size
        e.location = loc; e.rotation_euler = (0, 0, rotz); C_PORT.objects.link(e)
        return e
    empty("S04_DogMark", DOG, math.pi)  # local +Y points -Y: the dog faces the courtyard
    empty("S04_CamDescent", (0.0, 7.0, (Z_BEAM_TOP + Z_JOIST_TOP) / 2), 0, "PLAIN_AXES", 0.2)


def build_cams():
    def cam(name, loc, target, lens):
        cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.02; cd.clip_end = 300
        o = bpy.data.objects.new(name, cd); C_CAMS.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o
    cam("CAM_S04_Wide", (1.2, -5.1, 7.6), (-0.2, 5.5, 0.8), 20)
    cam("CAM_S04_DogEye", (0.45, 8.55, PZ + 0.45), (-0.35, 0.0, 0.75), 22)
    cam("CAM_S04_CeilingUp", (0.7, 8.3, 1.05), (0.0, 6.8, 2.75), 16)
    cam("CAM_S04_PorticoFront", (0.9, 1.2, 1.55), (-0.8, 8.6, 1.25), 24)
    cam("CAM_S04_South", (0.3, 7.6, 1.6), (0.0, -6.6, 3.2), 22)
    cam("CAM_S04_FloorClose", (2.0, -0.5, 1.5), (2.6, 3.0, 0.0), 30)
    cam("CAM_S04_ExitDoorView", (-1.3, 6.5, 1.25), (-2.6, 9.0, 0.95), 26)
    cam("CAM_S04_BrickClose", (-4.1, 5.35, 1.35), (-5.95, 7.2, 1.15), 30)
    sc.camera = bpy.data.objects["CAM_S04_Wide"]


# ------------------------------------------------------------------ render defaults
def render_defaults():
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.cycles.texture_limit_render = "2048"
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 8.0
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = float(os.environ.get("S04_EXP", 0.3))
    sc.render.film_transparent = False


# ------------------------------------------------------------------ run
load_windows()
build_floor()
hatch, exitdoor = build_north()
side_building("E")
side_building("W")
build_south()
build_background()
build_dressing()
build_lights()
build_markers(hatch, exitdoor)
build_cams()
render_defaults()
# exclude the instance-source collection from the view layer
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == "S04_AssetSrc":
        lc.exclude = True
bpy.context.view_layer.update()
for name in ("S04_DogMark", "S04_CamDescent", "S04_ExitDoor", "S04_Portico_CeilingHatch"):
    o = bpy.data.objects[name]
    print("[mark] %-26s %s" % (name, tuple(round(v, 3) for v in o.matrix_world.translation)))
tris = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print("[build] mesh faces total (sources counted once):", tris)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("[build] saved", OUT)
