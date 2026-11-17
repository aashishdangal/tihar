# s07: saptarangi (seven-colour) tika powder heaped in the owner's tika-dani (S07_TikaDani),
# and the dish's silver material.
# Cup centres/bottoms are found by ray-casting the dish (stored on the object as "cups"/"rim_top"
# by the placement step). Each cup gets a fine, irregular heap (dense grid, multi-octave lumps)
# plus a GN dusting of tiny pigment grains. Centre cup = red. Yellow = damp paste (owner).
# Run inside s07_bhaitika_vNNN.blend (MCP exec). Rebuilds S07_Tika_* each time.
import bpy, bmesh, math, random
from mathutils import Vector, noise

random.seed(707)
dish = bpy.data.objects["S07_TikaDani"]
cups = [Vector(c) for c in dish["cups"]]
rim = dish["rim_top"]
col = bpy.data.collections["S07_Thali"]
centre = sum(cups, Vector()) / len(cups)
CUP_R = 0.0185          # cup radius at the rim (centres 45 mm apart)
PEAK = 0.0030           # heap peak above the rim (lower: less blob-like)

COLOURS = {             # linear RGB, pigment
    "Red":     (0.55, 0.012, 0.02),
    "Yellow":  (0.80, 0.52, 0.02),
    "Green":   (0.04, 0.30, 0.05),
    "Blue":    (0.015, 0.08, 0.50),
    "White":   (0.80, 0.80, 0.76),
    "Orange":  (0.85, 0.22, 0.01),
    "Magenta": (0.60, 0.015, 0.22),
}

for o in list(bpy.data.objects):
    if o.name.startswith("S07_Tika_"):
        bpy.data.objects.remove(o, do_unlink=True)


def powder_mat(name, rgb, wet=False):
    """Pigment powder: matte, dusty sheen, per-grain brightness speckle.
    wet=True: damp paste (darker, glossy, smoother)."""
    m = bpy.data.materials.get("S07_Powder_" + name) or bpy.data.materials.new("S07_Powder_" + name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial")
    b = N("ShaderNodeBsdfPrincipled")
    tc = N("ShaderNodeTexCoord")
    speck = N("ShaderNodeTexNoise"); speck.inputs["Scale"].default_value = 9000; speck.inputs["Detail"].default_value = 1
    blot = N("ShaderNodeTexNoise"); blot.inputs["Scale"].default_value = 450; blot.inputs["Detail"].default_value = 6
    L(tc.outputs["Object"], speck.inputs["Vector"]); L(tc.outputs["Object"], blot.inputs["Vector"])
    mx = N("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"
    L(speck.outputs["Fac"], mx.inputs[0]); mx.inputs[1].default_value = 0.5; L(blot.outputs["Fac"], mx.inputs[2])
    mr = N("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45; mr.inputs["From Max"].default_value = 1.05
    mr.inputs["To Min"].default_value = 0.8 if wet else 0.7; mr.inputs["To Max"].default_value = 1.2
    L(mx.outputs[0], mr.inputs["Value"])
    hsv = N("ShaderNodeHueSaturation")
    base = tuple(c * 0.75 for c in rgb) if wet else rgb
    hsv.inputs["Color"].default_value = (*base, 1)
    hsv.inputs["Saturation"].default_value = 1.15 if wet else 1.0
    L(mr.outputs["Result"], hsv.inputs["Value"]); L(hsv.outputs["Color"], b.inputs["Base Color"])
    bp = N("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.15 if wet else 0.5
    bp.inputs["Distance"].default_value = 0.0002
    L(speck.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    if wet:
        b.inputs["Roughness"].default_value = 0.22
        b.inputs["Coat Weight"].default_value = 0.35; b.inputs["Coat Roughness"].default_value = 0.15
        b.inputs["Subsurface Weight"].default_value = 0.25
        b.inputs["Subsurface Radius"].default_value = (0.002, 0.0015, 0.0005)
    else:
        b.inputs["Roughness"].default_value = 1.0
        b.inputs["Sheen Weight"].default_value = 0.5; b.inputs["Sheen Roughness"].default_value = 0.5
    L(b.outputs[0], out.inputs["Surface"])
    return m


def grains_group():
    """GN: scatter tiny pigment grains over the heap (and keep the heap)."""
    g = bpy.data.node_groups.get("S07_PowderGrains")
    if g: return g
    g = bpy.data.node_groups.new("S07_PowderGrains", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Density", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Material", in_out="INPUT", socket_type="NodeSocketMaterial")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = g.nodes.new, g.links.new
    gi = N("NodeGroupInput"); go = N("NodeGroupOutput")
    dist = N("GeometryNodeDistributePointsOnFaces")
    L(gi.outputs[0], dist.inputs["Mesh"]); L(gi.outputs[1], dist.inputs["Density"])
    ico = N("GeometryNodeMeshIcoSphere"); ico.inputs["Radius"].default_value = 0.00014
    ico.inputs["Subdivisions"].default_value = 2
    ss = N("GeometryNodeSetShadeSmooth"); L(ico.outputs["Mesh"], ss.inputs["Geometry"])   # flat grains read as dark specks
    sm = N("GeometryNodeSetMaterial"); L(ss.outputs[0], sm.inputs["Geometry"]); L(gi.outputs[2], sm.inputs["Material"])
    rnd = N("FunctionNodeRandomValue"); rnd.data_type = "FLOAT"
    rnd.inputs["Min"].default_value = 0.5; rnd.inputs["Max"].default_value = 1.8
    rot = N("FunctionNodeRandomValue"); rot.data_type = "FLOAT_VECTOR"
    rot.inputs["Max"].default_value = (6.3, 6.3, 6.3)
    inst = N("GeometryNodeInstanceOnPoints")
    L(dist.outputs["Points"], inst.inputs["Points"]); L(sm.outputs[0], inst.inputs["Instance"])
    L(rnd.outputs["Value"], inst.inputs["Scale"]); L(rot.outputs["Value"], inst.inputs["Rotation"])
    j = N("GeometryNodeJoinGeometry")
    L(gi.outputs[0], j.inputs[0]); L(inst.outputs[0], j.inputs[0])
    L(j.outputs[0], go.inputs[0])
    return g


def mound(name, c, mat, wet=False):
    """Fine heap: dense disc grid, irregular outline, off-centre peak, multi-octave lumps; the edge
    tucks under the rim inside the cup wall."""
    bm = bmesh.new()
    rings, seg = 40, 128
    seed = Vector((hash(name) % 97, hash(name) % 53, 3.0))
    peak = PEAK * (0.75 if wet else random.uniform(0.85, 1.15))
    off = Vector((random.uniform(-0.003, 0.003), random.uniform(-0.003, 0.003)))
    top = bm.verts.new((off.x, off.y, peak))
    ring_verts = []
    for k in range(1, rings + 1):
        t = k / rings
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            edge = CUP_R * (1 + 0.06 * noise.noise(seed + Vector((math.cos(a) * 2, math.sin(a) * 2, 0))))
            r = edge * t
            x = off.x * (1 - t) + r * math.cos(a)
            y = off.y * (1 - t) + r * math.sin(a)
            h = peak * (1 - t ** (2.4 if wet else 1.2)) - 0.0028 * t ** 6
            p = Vector((x, y, 0))
            if wet:   # a few big soft clumps, smooth surface
                h += 0.0010 * noise.noise(seed + p * 180) + 0.0002 * noise.noise(seed + p * 900)
            else:     # loose powder: fine ripples + crumbs
                h += (0.00055 * noise.noise(seed + p * 250) + 0.00040 * noise.noise(seed + p * 900)
                      + 0.00022 * noise.noise(seed + p * 2600) + 0.00010 * noise.noise(seed + p * 6000))
                h += 0.0006 * max(0.0, noise.noise(seed * 2 + p * 600) - 0.35)      # crumbs and lumps
            ring.append(bm.verts.new((x, y, h)))
        ring_verts.append(ring)
    for i in range(seg):
        bm.faces.new((top, ring_verts[0][i], ring_verts[0][(i + 1) % seg]))
    for k in range(rings - 1):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((ring_verts[k][i], ring_verts[k + 1][i], ring_verts[k + 1][j], ring_verts[k][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    col.objects.link(o)
    o.location = (c.x, c.y, rim)
    o.parent = dish; o.matrix_parent_inverse = dish.matrix_world.inverted()
    md = o.modifiers.new("Grains", "NODES"); md.node_group = grains_group()
    ids = [i.identifier for i in md.node_group.interface.items_tree
           if i.item_type == "SOCKET" and i.in_out == "INPUT"]
    getattr(md.properties.inputs, ids[1]).value = 5.0e4 if wet else 2.1e5
    getattr(md.properties.inputs, ids[2]).value = mat
    return o


def silver_dish():
    """Polished silver (owner: the first, grey/tarnished one looked fake): bright, low roughness
    with fine circular polish lines. Used with the Smooth modifier on the AI mesh and the
    light-linked S07_L_SilverSheen so it shows a bright/dark gradient."""
    m = bpy.data.materials.get("S07_Silver") or bpy.data.materials.new("S07_Silver")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.90, 0.89, 0.87, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Anisotropic"].default_value = 0.3
    tc = N("ShaderNodeTexCoord")
    w = N("ShaderNodeTexWave"); w.wave_type = "RINGS"; w.inputs["Scale"].default_value = 900
    w.inputs["Distortion"].default_value = 2
    nz = N("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40; nz.inputs["Detail"].default_value = 4
    L(tc.outputs["Object"], w.inputs["Vector"]); L(tc.outputs["Object"], nz.inputs["Vector"])
    r = N("ShaderNodeMapRange"); r.inputs["To Min"].default_value = 0.07; r.inputs["To Max"].default_value = 0.15
    L(nz.outputs["Fac"], r.inputs["Value"])
    ad = N("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.inputs[1].default_value = 0.03
    L(w.outputs["Fac"], ad.inputs[0]); L(r.outputs["Result"], ad.inputs[2]); L(ad.outputs[0], b.inputs["Roughness"])
    L(b.outputs[0], out.inputs["Surface"])
    dish.data.materials.clear(); dish.data.materials.append(m)


silver_dish()
ring_cups = sorted([c for c in cups if (c.xy - centre.xy).length > 0.01],
                   key=lambda c: math.atan2(c.y - centre.y, c.x - centre.x))
mid_cup = [c for c in cups if (c.xy - centre.xy).length <= 0.01]
order = ["Yellow", "Green", "Blue", "White", "Orange", "Magenta"]
for c, nm in zip(ring_cups, order):
    wet = nm == "Yellow"                       # owner: the yellow is a little wet
    mound("S07_Tika_" + nm, c, powder_mat(nm, COLOURS[nm], wet=wet), wet=wet)
for c in mid_cup:
    mound("S07_Tika_Red", c, powder_mat("Red", COLOURS["Red"]))
print("tika mounds:", len(ring_cups) + len(mid_cup))
