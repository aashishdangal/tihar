# Build the S04 red tika: an irregular vermilion paste blob shaped to Nubis' forehead (dog scale 0.65),
# 8 akshata rice grains pressed into it, and a small dab for the hand's ring fingertip.
# exec(open(r"E:/Projects/tihar/scripts/s04_hand_build_tika.py").read())   (live or background)
import bpy, bmesh, math, random, json
from mathutils import Vector, Matrix, noise

FIT = r"E:\Projects\tihar\blender\assets\s04_hand\s04_mala_fit.json"
fit = json.load(open(FIT))["tika"]
rnd = random.Random(7)

def lin(hexs):
    h = hexs.lstrip("#"); out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)

# ------------------------------------------------------------------ materials
def mat_paste():
    m = bpy.data.materials.get("S04_Tika_Paste") or bpy.data.materials.new("S04_Tika_Paste")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); out.location = (700, 0)
    bs = N("ShaderNodeBsdfPrincipled"); bs.location = (350, 0)
    tc = N("ShaderNodeTexCoord"); tc.location = (-800, 0)
    nz = N("ShaderNodeTexNoise"); nz.location = (-550, 0); nz.inputs["Scale"].default_value = 900; nz.inputs["Detail"].default_value = 6
    L(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = N("ShaderNodeValToRGB"); ramp.location = (-300, 150)
    ramp.color_ramp.elements[0].color = lin("#8A1806"); ramp.color_ramp.elements[1].color = lin("#C62A0C")
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.7
    L(nz.outputs["Fac"], ramp.inputs[0]); L(ramp.outputs[0], bs.inputs["Base Color"])
    # wet: glossy where thick, a dry powdery rim at the edge (vertex attribute 'wet' 1 centre -> 0 rim)
    at = N("ShaderNodeAttribute"); at.attribute_name = "wet"; at.location = (-300, -150)
    rr = N("ShaderNodeMapRange"); rr.location = (0, -150); rr.inputs[3].default_value = 0.8; rr.inputs[4].default_value = 0.3
    L(at.outputs["Fac"], rr.inputs[0]); L(rr.outputs[0], bs.inputs["Roughness"])
    cw = N("ShaderNodeMapRange"); cw.location = (0, -350); cw.inputs[3].default_value = 0.0; cw.inputs[4].default_value = 0.35
    L(at.outputs["Fac"], cw.inputs[0]); L(cw.outputs[0], bs.inputs["Coat Weight"])
    bs.inputs["Coat Roughness"].default_value = 0.08
    bs.inputs["Subsurface Weight"].default_value = 0.05
    bs.inputs["Subsurface Radius"].default_value = (0.6, 0.08, 0.05)
    bs.inputs["Subsurface Scale"].default_value = 0.0015
    bump = N("ShaderNodeBump"); bump.location = (100, -550); bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.0002
    L(nz.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs[0], bs.inputs["Normal"])
    L(bs.outputs[0], out.inputs[0])
    m.diffuse_color = lin("#C8201A")
    return m

def mat_rice():
    m = bpy.data.materials.get("S04_Akshata_Rice") or bpy.data.materials.new("S04_Akshata_Rice")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); out.location = (700, 0)
    bs = N("ShaderNodeBsdfPrincipled"); bs.location = (350, 0)
    # dyed red-pink at the ends/edges (where the grain touched the paste), creamy white in the middle
    tc = N("ShaderNodeTexCoord"); tc.location = (-900, 0)
    sep = N("ShaderNodeSeparateXYZ"); sep.location = (-700, 0); L(tc.outputs["Generated"], sep.inputs[0])
    d = N("ShaderNodeMath"); d.operation = "SUBTRACT"; d.inputs[1].default_value = 0.5; d.location = (-500, 0)
    L(sep.outputs["X"], d.inputs[0])
    ab = N("ShaderNodeMath"); ab.operation = "ABSOLUTE"; ab.location = (-350, 0); L(d.outputs[0], ab.inputs[0])
    lw = N("ShaderNodeLayerWeight"); lw.location = (-500, -200); lw.inputs["Blend"].default_value = 0.35
    nz = N("ShaderNodeTexNoise"); nz.location = (-500, -400); nz.inputs["Scale"].default_value = 1500
    L(tc.outputs["Object"], nz.inputs["Vector"])
    mx = N("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.location = (-200, -100)
    m2 = N("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 1.6; m2.location = (-250, 50)
    L(ab.outputs[0], m2.inputs[0]); L(m2.outputs[0], mx.inputs[0]); L(lw.outputs["Facing"], mx.inputs[1])
    ad = N("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.location = (-50, -200)
    L(mx.outputs[0], ad.inputs[0]); L(nz.outputs["Fac"], ad.inputs[1]); ad.inputs[2].default_value = 0.35
    mix = N("ShaderNodeMix"); mix.data_type = "RGBA"; mix.location = (100, 100); mix.clamp_factor = True
    mix.inputs[6].default_value = lin("#E8C8BE"); mix.inputs[7].default_value = lin("#A8141C")
    L(ad.outputs[0], mix.inputs[0]); L(mix.outputs[2], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.42
    bs.inputs["Subsurface Weight"].default_value = 0.5
    bs.inputs["Subsurface Radius"].default_value = (1.0, 0.9, 0.7)
    bs.inputs["Subsurface Scale"].default_value = 0.0008
    L(bs.outputs[0], out.inputs[0])
    m.diffuse_color = lin("#F0E6E0")
    return m

M_PASTE = mat_paste()

def replace_obj(name, me):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    else:
        old = ob.data; ob.data = me
        if old.users == 0: bpy.data.meshes.remove(old)
    me.name = name
    return ob

# ------------------------------------------------------------------ forehead height field
G = len(fit["grid"]); HALF = fit["half"]; grid = fit["grid"]
def height(u, v):
    fu = (u + HALF) / (2 * HALF) * (G - 1); fv = (v + HALF) / (2 * HALF) * (G - 1)
    fu = min(max(fu, 0), G - 1.001); fv = min(max(fv, 0), G - 1.001)
    i, j = int(fu), int(fv); a, b = fu - i, fv - j
    return (grid[j][i] * (1 - a) * (1 - b) + grid[j][i + 1] * a * (1 - b) +
            grid[j + 1][i] * (1 - a) * b + grid[j + 1][i + 1] * a * b)

C = Vector(fit["centre"]); n = Vector(fit["normal"]); tx = Vector(fit["tx"]); ty = Vector(fit["ty"])
LIFT = 0.0012          # sits on the fur tips (fur ~1 mm at the forehead, final scale)
RX, RY = 0.0095, 0.0130  # half-size of the paste: ~1.4 x 1.9 cm, a ring-finger press drawn slightly upward
THICK = 0.0012

def rim(a):
    """irregular outline radius factor at angle a"""
    return 1 + 0.16 * noise.noise(Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, 0.3))) + \
           0.07 * noise.noise(Vector((math.cos(a) * 5.0, math.sin(a) * 5.0, 2.1)))

# The tika is red powder/paste STAINING THE FUR (user direction): S04_Tika is an empty whose local frame
# (X across, Y up the forehead, Z out of the skin) drives the S04_TikaStain shader mask that
# scripts/s04_hand_tika_stain.py adds to the dog's fur and skin materials. Scale the empty 0 -> 1 to animate
# the stain appearing as the finger presses.
STAIN_RX, STAIN_RY, STAIN_RZ = 0.012, 0.017, 0.008   # stain half-size (m) at empty scale 1

def build_tika_empty():
    ob = bpy.data.objects.get("S04_Tika")
    if ob is not None and ob.type != "EMPTY":
        kids = list(ob.children)
        me = ob.data
        bpy.data.objects.remove(ob)
        if me and me.users == 0: bpy.data.meshes.remove(me)
        for k in kids: k.parent = None
        ob = None
    if ob is None:
        ob = bpy.data.objects.new("S04_Tika", None); bpy.context.scene.collection.objects.link(ob)
    ob.empty_display_type = "SPHERE"; ob.empty_display_size = 1.0
    ob.matrix_world = Matrix.Translation(C) @ Matrix((tx, ty, n)).transposed().to_4x4()
    ob.scale = (1, 1, 1)
    ob["stain_radii"] = (STAIN_RX, STAIN_RY, STAIN_RZ)
    return ob

def grain(bm, M, rnd):
    L = rnd.uniform(0.0050, 0.0058); Wd = rnd.uniform(0.0020, 0.0024); H = Wd * rnd.uniform(0.75, 0.85)
    ret = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.5)
    vs = ret["verts"]
    broken = rnd.random() < 0.3
    for v in vs:
        x, y, z = v.co
        taper = 1 - 0.18 * max(0, x * 2) ** 2          # one end slightly pointed
        x2 = x * L * (0.8 if broken and x > 0 else 1)
        v.co = M @ Vector((x2, y * Wd * taper, z * H * taper))
    return vs

def build_rice(tika):
    bm = bmesh.new()
    pts = []; tries = 0
    while len(pts) < 5 and tries < 500:
        tries += 1
        a = rnd.uniform(0, 2 * math.pi); f = math.sqrt(rnd.uniform(0.0, 1.0)) * 0.75
        u = math.cos(a) * STAIN_RX * f; v = math.sin(a) * STAIN_RY * f
        if all((Vector((u, v)) - p).length > 0.006 for p in pts):
            pts.append(Vector((u, v)))
    for p in pts:
        z = height(p.x, p.y) + 0.0022                                     # caught in the fur tips
        M = Matrix.Translation((p.x, p.y, z)) @ Matrix.Rotation(rnd.uniform(0, math.pi), 4, "Z")             @ Matrix.Rotation(rnd.uniform(-0.35, 0.35), 4, "X")
        grain(bm, M, rnd)
    me = bpy.data.meshes.new("S04_Tika_Rice"); bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.use_smooth = True
    me.materials.append(M_RICE)
    ob = replace_obj("S04_Tika_Rice", me)
    ob.parent = tika; ob.matrix_parent_inverse.identity(); ob.matrix_basis.identity()
    return ob

def build_finger_dab():
    """small red smear for the ring fingertip, origin at the fingertip pad, Z = out of the pad"""
    bm = bmesh.new(); wet = bm.verts.layers.float.new("wet")
    ret = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    for v in ret["verts"]:
        x, y, z = v.co
        k = 1 + 0.15 * noise.noise(Vector((x * 2, y * 2, 0.7)))
        v.co = Vector((x * 0.0042 * k, y * 0.0055 * k, (z * 0.0008 if z > 0 else z * 0.0002)))
        v[wet] = max(0.0, z)
    me = bpy.data.meshes.new("S04_TikaFinger"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(M_PASTE)
    ob = replace_obj("S04_TikaFinger", me)
    ob["note"] = "Parent to the ring fingertip of the hand: origin = pad centre, +Z out of the pad, +Y along the finger."
    return ob

tika = build_tika_empty()
# no rice on the head (user direction): only the red stain. Remove any rice built earlier.
old_rice = bpy.data.objects.get("S04_Tika_Rice")
if old_rice:
    rm = old_rice.data; bpy.data.objects.remove(old_rice)
    if rm.users == 0: bpy.data.meshes.remove(rm)
rmat = bpy.data.materials.get("S04_Akshata_Rice")
if rmat and rmat.users == 0: bpy.data.materials.remove(rmat)
had_parent = bpy.data.objects.get("S04_TikaFinger") is not None and bpy.data.objects["S04_TikaFinger"].parent is not None
dab = build_finger_dab()
if not had_parent:
    dab.location = C + n * 0.03 + tx * 0.04    # parked beside the forehead until it is put on the fingertip
tika["note"] = ("Stain centre on Nubis' forehead between the eyes (dog scale 0.65, rig origin unchanged). Parent to "
                "bone 'Head' of rig 'Nubis' (keep transform), then run scripts/s04_hand_tika_stain.py to add the red "
                "fur/skin stain. Animate the empty's scale 0 -> 1 for the stain to appear.")
print("[tika] stain empty", tuple(round(v, 4) for v in tika.matrix_world.translation))
