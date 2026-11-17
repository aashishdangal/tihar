# s07: Jamuna's empty engraved brass Bhai Tika thali on the chamber floor (s02 room copy).
# Engraving mask: blender/assets/s07/thali_engrave.png (scripts/s07_thali_engrave.py), mapped
# top-down from object x/y so the swastik sits at the plate centre.
# Run inside s07_bhaitika_vNNN.blend (MCP exec). Rebuilds collection S07_Thali each time.
import bpy, bmesh, math
from mathutils import Vector

FLOOR = 0.0                      # top of S02_Floor
LOC = (1.5, 1.2)                 # open floor between Jamuna and the shadow wall (x=3)
R = 0.24                         # plate radius (Ø 48 cm: room for tika-dani, malas, fruit, mithai box)
ENGRAVE = r"E:\Projects\tihar\blender\assets\s07\thali_engrave.png"
IMG_R = 0.30                     # plate radius the mask was drawn for (maps image edge to rim)

col = bpy.data.collections.get("S07_Thali")
if col:
    for o in list(col.objects):
        if o.name.startswith("S07_"):
            bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("S07_Thali")
    bpy.context.scene.collection.children.link(col)
root = bpy.data.objects.new("S07_Thali_Root", None)
root.location = (LOC[0], LOC[1], FLOOR)
col.objects.link(root)


def brass_mat():
    m = bpy.data.materials.get("S07_BrassEngraved") or bpy.data.materials.new("S07_BrassEngraved")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = N("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
    L(bsdf.outputs[0], out.inputs["Surface"])
    tc = N("ShaderNodeTexCoord"); tc.location = (-1000, 0)
    # object x/y (metres) -> image 0..1: u = x / (2R) + 0.5
    mp = N("ShaderNodeMapping"); mp.location = (-800, 0)
    mp.inputs["Scale"].default_value = (1 / (2 * R), 1 / (2 * R), 1)
    mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    L(tc.outputs["Object"], mp.inputs["Vector"])
    img = N("ShaderNodeTexImage"); img.location = (-600, 0)
    img.image = bpy.data.images.load(ENGRAVE, check_existing=True)
    img.image.colorspace_settings.name = "Non-Color"
    img.extension = "CLIP"; img.interpolation = "Cubic"
    L(mp.outputs[0], img.inputs["Vector"])
    groove = img.outputs["Color"]
    # worn polish: low-frequency noise drives roughness + slight colour variation
    nz = N("ShaderNodeTexNoise"); nz.location = (-600, -350)
    nz.inputs["Scale"].default_value = 18; nz.inputs["Detail"].default_value = 8
    L(tc.outputs["Object"], nz.inputs["Vector"])
    scratch = N("ShaderNodeTexWave"); scratch.location = (-600, -600)   # fine circular polish marks
    scratch.wave_type = "RINGS"; scratch.inputs["Scale"].default_value = 140
    scratch.inputs["Distortion"].default_value = 3
    L(tc.outputs["Object"], scratch.inputs["Vector"])
    base = N("ShaderNodeMix"); base.data_type = "RGBA"; base.location = (-300, 200)
    base.inputs["A"].default_value = (0.78, 0.55, 0.22, 1)     # bright worn brass
    base.inputs["B"].default_value = (0.55, 0.36, 0.13, 1)     # older, duller brass
    L(nz.outputs["Fac"], base.inputs["Factor"])
    grime = N("ShaderNodeMix"); grime.data_type = "RGBA"; grime.location = (0, 200)
    grime.inputs["B"].default_value = (0.09, 0.06, 0.03, 1)    # dark residue in the cuts
    L(base.outputs["Result"], grime.inputs["A"]); L(groove, grime.inputs["Factor"])
    L(grime.outputs["Result"], bsdf.inputs["Base Color"])
    rough = N("ShaderNodeMapRange"); rough.location = (-300, -350)
    rough.inputs["To Min"].default_value = 0.16; rough.inputs["To Max"].default_value = 0.34
    L(nz.outputs["Fac"], rough.inputs["Value"])
    rmix = N("ShaderNodeMix"); rmix.location = (0, -350)
    rmix.inputs["B"].default_value = 0.7
    L(rough.outputs["Result"], rmix.inputs["A"]); L(groove, rmix.inputs["Factor"])
    sc = N("ShaderNodeMath"); sc.operation = "MULTIPLY_ADD"; sc.location = (200, -500)
    sc.inputs[1].default_value = 0.06; L(scratch.outputs["Fac"], sc.inputs[0]); L(rmix.outputs["Result"], sc.inputs[2])
    L(sc.outputs[0], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 1.0
    # grooves cut in: invert the mask for height
    inv = N("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.location = (0, -800)
    inv.inputs[0].default_value = 1.0; L(groove, inv.inputs[1])
    bump = N("ShaderNodeBump"); bump.location = (300, -800)
    bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.0006
    L(inv.outputs[0], bump.inputs["Height"])
    sbump = N("ShaderNodeBump"); sbump.location = (450, -650)               # polish marks
    sbump.inputs["Strength"].default_value = 0.05; sbump.inputs["Distance"].default_value = 0.0001
    L(scratch.outputs["Fac"], sbump.inputs["Height"]); L(bump.outputs["Normal"], sbump.inputs["Normal"])
    L(sbump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def lathe(name, prof, seg=192, mat=None):
    """prof: [(r, z)] from centre outwards; revolved around Z."""
    bm = bmesh.new()
    rings = []
    for (r, z) in prof:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
                      for i in range(seg)])
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


BRASS = brass_mat()
k = R / 0.30   # s06 profile, scaled to this plate; floor ring at 0.24R/0.30 meets the rim slope
prof = [(0.001, 0.004), (0.24, 0.004), (0.272, 0.010), (0.292, 0.022), (0.300, 0.028),
        (0.304, 0.026), (0.300, 0.020), (0.282, 0.008), (0.25, 0.0), (0.001, 0.0)]
plate = lathe("S07_Thali_Plate", [(r * k, z) for r, z in prof], mat=BRASS)
bev = plate.modifiers.new("Bevel", "BEVEL"); bev.width = 0.0008; bev.segments = 2
rim = lathe("S07_Thali_Rim", [(r * k, z) for r, z in
            [(0.296, 0.030), (0.300, 0.033), (0.305, 0.030), (0.300, 0.026), (0.296, 0.030)]], mat=BRASS)
print("S07_Thali built at", LOC, "R", R)
