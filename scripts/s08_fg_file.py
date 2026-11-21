"""s08 foreground layer: tree + kite + grass in their own light file (owner 2026-11-21: "lets work on the
animation of tree kite and the grass that appear below tree remove all that from main file").

Same idea as the flag (scripts/s08_flag_file.py): a transparent-film layer rendered in CAM_S08 and laid
over the finale plate. The finale itself hides tree + grass (scripts/s08_main_strip_fg.py).

  blender.exe -b blender/scenes/s08_finale_v070.blend --python scripts/s08_fg_file.py
writes blender/scenes/s08_fg.blend. Env S08_TEST=1 renders frames 1/80/160 at 50 % to
renders/s08_finale/test/fg/.

Keeps: S08_Tree, S08_Hill (now a HOLDOUT: hides what is behind it, still blocks light), S08_HillRoad
(holdout), grass sources, CAM_S08, world, lights. Everything else is deleted from this copy.

Motion, all seamless over L = 240 frames (10 s, same as the flag loop); every speed is a whole
number of cycles per loop:
  - tree: GN "S08_TreeSway" - slow gust sway (1 + 3 cycles) growing from trunk to crown, plus
    a faster leaf flutter on the leaf material only.
  - grass: each tuft leans on its base with drifting noise (GN_S08_Grass_FG).
  - kite: marigold Nepali changa (paper diamond, bamboo spine + bow, small tail) caught by its
    string in a branch. Follows the branch through a 3-vertex proxy that gets the same sway, swings
    on its top corner (drivers), and the paper ripples (GN).
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = r"E:/Projects/tihar"
# owner 2026-11-21: "the wind should match the wind of flag ... should shake not computed wave".
# Same loop as the flag (scripts/s08_flag_wave.py): 120 frames, same gust swell, same wind heading
# (60 deg west of north, scripts/s08_flag_file.py). Everything is scaled by the swell, so a gust that
# lifts the flag shakes the tree, grass and kite in the same frames.
L = 72                                                             # 3 s (owner 2026-11-21)
WIND_A = math.radians(-60)
WIND = Vector((math.sin(WIND_A), math.cos(WIND_A), 0.0))           # direction the wind blows TO
sc = bpy.context.scene

# ------------------------------------------------------------------ strip the copy
# no S08_L_Alpenglow: it is light-linked to the Himalaya only; with the peaks gone the link is empty
# and it lit the tree and grass gold (first test, 2026-11-21)
# S08_HazeLayer kept (owner: "i think there is lighting difference"): the camera sits inside this
# volume, and without it the tree came out ~25 % darker and warmer than in the finale plate
# (S08_HazeLayer was tried and dropped: a volume fills the alpha of the whole frame, so the layer would
#  lay a second haze over the plate; it changed the tree/grass colour very little anyway)
# S08_INPLACE=1 (owner 2026-11-21, "do single render"): build the same tree sway, grass and kite
# INSIDE the finale file (no stripping, hill stays a normal visible ground) so it all renders in one
# pass with the finale's own lighting and haze. Used by scripts/s08_main_merge.py.
INPLACE = bool(os.environ.get("S08_INPLACE"))
KEEP = {"S08_Tree", "S08_Hill", "S08_HillRoad", "CAM_S08", "S08_L_Sun"}
src_grass = set(o.name for o in bpy.data.collections["S08_GrassSrc"].objects)
for o in ([] if INPLACE else list(bpy.data.objects)):
    if o.name not in KEEP and o.name not in src_grass:
        bpy.data.objects.remove(o, do_unlink=True)
if not INPLACE:
    for lib in list(bpy.data.libraries):
        bpy.data.libraries.remove(lib)
    for c in list(bpy.data.collections):
        if not c.objects and not c.children:
            bpy.data.collections.remove(c)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    print("[fg] kept", sorted(o.name for o in bpy.data.objects if o.name not in src_grass))

sc.camera = bpy.data.objects["CAM_S08"]
if not INPLACE:
    sc.render.film_transparent = True
sc.cycles.samples = 128; sc.cycles.use_denoising = True
sc.render.use_persistent_data = True
sc.frame_start, sc.frame_end = 1, L
fg = bpy.data.collections.get("S08_Foreground") or sc.collection

# ------------------------------------------------------------------ shared loop helpers (GN)
def ng_new(name):
    g = bpy.data.node_groups.get(name)
    if g:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new(name, "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    return g


def node(g, kind, **inputs):
    n = g.nodes.new(kind)
    for k, v in inputs.items():
        if k.startswith("_"):
            setattr(n, k[1:], v)
        else:
            n.inputs[k].default_value = v
    return n


def math_n(g, op, a=None, b=None, **kw):
    n = node(g, "ShaderNodeMath", _operation=op)
    for i, v in ((0, a), (1, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            g.links.new(v, n.inputs[i])
    return n.outputs[0]


def vmath(g, op, a=None, b=None, scale=None):
    n = node(g, "ShaderNodeVectorMath", _operation=op)
    for i, v in ((0, a), (1, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, Vector)):
            n.inputs[i].default_value = v
        else:
            g.links.new(v, n.inputs[i])
    if scale is not None:
        if isinstance(scale, (int, float)):
            n.inputs["Scale"].default_value = scale
        else:
            g.links.new(scale, n.inputs["Scale"])
    return n.outputs["Value" if op in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else "Vector"]


def loop_noise(g, pos, scale, cycles, radius, detail=1.0):
    """3D noise sampled at pos*scale + a circle walked `cycles` times per loop -> centred (-0.5..0.5)"""
    t = node(g, "GeometryNodeInputSceneTime").outputs["Frame"]
    th = math_n(g, "MULTIPLY", t, 2 * math.pi * cycles / L)
    cx = math_n(g, "MULTIPLY", math_n(g, "COSINE", th), radius)
    cy = math_n(g, "MULTIPLY", math_n(g, "SINE", th), radius)
    cxyz = node(g, "ShaderNodeCombineXYZ")
    g.links.new(cx, cxyz.inputs[0]); g.links.new(cy, cxyz.inputs[1])
    p = vmath(g, "ADD", vmath(g, "SCALE", pos, scale=scale), cxyz.outputs[0])
    nz = node(g, "ShaderNodeTexNoise", Scale=1.0, Detail=detail, Roughness=0.5)
    nz.noise_dimensions = "3D"
    g.links.new(p, nz.inputs["Vector"])
    return vmath(g, "SUBTRACT", nz.outputs["Color"], (0.5, 0.5, 0.5))


def swell_node(g):
    """flag gust swell: 1 + 0.22 sin(2pi t) + 0.14 sin(4pi t + 1.1), t = (frame - 1) / L"""
    f = math_n(g, "SUBTRACT", node(g, "GeometryNodeInputSceneTime").outputs["Frame"], 1.0)
    a = math_n(g, "MULTIPLY", math_n(g, "SINE", math_n(g, "MULTIPLY", f, 2 * math.pi / L)), 0.22)
    b = math_n(g, "MULTIPLY", math_n(g, "SINE", math_n(g, "ADD", math_n(g, "MULTIPLY", f, 4 * math.pi / L), 1.1)), 0.14)
    return math_n(g, "ADD", math_n(g, "ADD", a, b), 1.0)


# the flag's own waves (scripts/s08_flag_wave.py pass 5): amplitude m, wavelength m, cycles per loop, phase.
# Phase is measured along the wind from the flag pole, so one wave field runs through flag, tree, grass, kite.
FLAG_WAVES = [(0.075, 1.30, 2, 0.0), (0.030, 0.75, 3, 1.7), (0.011, 0.45, 5, 4.1)]   # flag pass 6
FAST = FLAG_WAVES[-1][2]                                           # the flag's fastest ripple, cycles per loop
POLE = Vector((2005.0, -10984.0, 0.0))                             # S08_FlagPole (s08_flag_file.py)
A_SUM = sum(w_[0] for w_ in FLAG_WAVES)


def wind_wave(g, pos, u, c):
    """flag wave field at a point: sum a*sin(2pi((x/lam) - n t) + ph) / sum(a), x = dot(pos, u) + c =
    distance along the wind from the pole (pos in object space; u, c map it to world)"""
    x = math_n(g, "ADD", vmath(g, "DOT_PRODUCT", pos, tuple(u)), c)
    tt = math_n(g, "MULTIPLY", math_n(g, "SUBTRACT", node(g, "GeometryNodeInputSceneTime").outputs["Frame"], 1.0), 1.0 / L)
    tot = None
    for a, lam, n, ph in FLAG_WAVES:
        arg = math_n(g, "ADD", math_n(g, "MULTIPLY", math_n(g, "SUBTRACT", math_n(g, "DIVIDE", x, lam),
                                                              math_n(g, "MULTIPLY", tt, float(n))), 2 * math.pi), ph)
        term = math_n(g, "MULTIPLY", math_n(g, "SINE", arg), a / A_SUM)
        tot = term if tot is None else math_n(g, "ADD", tot, term)
    return tot


def wind_expr(xw):
    """same field as a driver expression, at a fixed world point (distance xw along the wind from the pole)"""
    return "(" + " + ".join("%.4f*sin(2*pi*(%.4f - %d*(frame-1)/%d) + %.2f)" % (a / A_SUM, xw / lam, n, L, ph)
                            for a, lam, n, ph in FLAG_WAVES) + ")"


def obj_uc(ob):
    """u, c so that dot(local_pos, u) + c = dot(world_pos - POLE, WIND)"""
    m3 = ob.matrix_world.to_3x3()
    return m3.transposed() @ WIND, (ob.matrix_world.translation - POLE).dot(WIND)


SWELL_EXPR = "(1 + 0.22*sin(2*pi*(frame-1)/%d) + 0.14*sin(4*pi*(frame-1)/%d + 1.1))" % (L, L)

# ------------------------------------------------------------------ tree sway
tree = bpy.data.objects["S08_Tree"]
co = [v.co for v in tree.data.vertices]
zmin = min(c.z for c in co); zmax = max(c.z for c in co)
base = [c for c in co if c.z < zmin + 0.02 * (zmax - zmin)]
ax, ay = sum(c.x for c in base) / len(base), sum(c.y for c in base) / len(base)
s = tree.scale.x
H = zmax - zmin
print("[fg] tree local height %.1f (world %.1f m), trunk axis %.2f %.2f" % (H, H * s, ax, ay))
leaf_idx = next(i for i, m in enumerate(tree.data.materials) if "leaves" in m.name)


def build_sway(name, ob, lean_m=0.02, wave_m=0.03, flutter_m=0.004):   # owner: "small wind"
    g = ng_new(name)
    gi = node(g, "NodeGroupInput"); go = node(g, "NodeGroupOutput")
    pos = node(g, "GeometryNodeInputPosition").outputs[0]
    # weight: 0 below 25 % of the height, rising to 1 at the top, plus a little more out on the branch ends
    sep = node(g, "ShaderNodeSeparateXYZ"); g.links.new(pos, sep.inputs[0])
    hz = node(g, "ShaderNodeMapRange", **{"From Min": zmin + 0.25 * H, "From Max": zmax, "To Min": 0.0, "To Max": 1.0})
    g.links.new(sep.outputs["Z"], hz.inputs["Value"])
    wz = math_n(g, "POWER", hz.outputs[0], 1.6)
    rad = vmath(g, "LENGTH", vmath(g, "MULTIPLY", vmath(g, "SUBTRACT", pos, (ax, ay, 0.0)), (1.0, 1.0, 0.0)))
    wr = math_n(g, "ADD", 1.0, math_n(g, "MULTIPLY", rad, 0.12 / (0.5 * H)))
    w = math_n(g, "MULTIPLY", wz, wr)
    sw_ = swell_node(g)
    ws = math_n(g, "MULTIPLY", w, sw_)                                # weight x gust strength
    # lean with the flag's wind (tree space), bigger in the gusts
    dl = (tree.matrix_world.inverted().to_3x3() @ WIND).normalized()
    off = vmath(g, "SCALE", tuple(dl), scale=math_n(g, "MULTIPLY", ws, lean_m / s))
    # the flag's waves passing through the crown, pushing along the wind
    u, c = obj_uc(ob)
    wv = wind_wave(g, pos, u, c)
    off = vmath(g, "ADD", off, vmath(g, "SCALE", tuple(dl), scale=math_n(g, "MULTIPLY", math_n(g, "MULTIPLY", ws, wv), wave_m / s)))
    # leaf flutter, leaves only, at the flag's fastest ripple (9 cycles = 1.8 Hz), small
    fl = loop_noise(g, pos, 6.0 / H, FAST, 1.0)
    flo = vmath(g, "SCALE", fl, scale=math_n(g, "MULTIPLY", ws, flutter_m / s * 2))
    msel = node(g, "GeometryNodeMaterialSelection")
    if leaf_idx < len(tree.data.materials):
        msel.inputs["Material"].default_value = tree.data.materials[leaf_idx]
    sw = node(g, "GeometryNodeSwitch", _input_type="VECTOR")
    g.links.new(msel.outputs[0], sw.inputs["Switch"]); sw.inputs["False"].default_value = (0, 0, 0)
    g.links.new(flo, sw.inputs["True"])
    tot = vmath(g, "ADD", off, sw.outputs[0])
    sp = node(g, "GeometryNodeSetPosition")
    g.links.new(gi.outputs[0], sp.inputs["Geometry"]); g.links.new(tot, sp.inputs["Offset"])
    g.links.new(sp.outputs[0], go.inputs[0])
    return g


sway = build_sway("GN_S08_TreeSway", tree)
for m in list(tree.modifiers):
    if m.name == "S08_TreeSway":
        tree.modifiers.remove(m)
tm = tree.modifiers.new("S08_TreeSway", "NODES"); tm.node_group = sway

# ------------------------------------------------------------------ grass: own object, sways; hill = holdout
hill = bpy.data.objects["S08_Hill"]
gsrc = hill.modifiers["S08_Grass"].node_group
gfg = gsrc.copy(); gfg.name = "GN_S08_Grass_FG"
# drop the hill surface from the output (only the grass), add the lean
# owner 2026-11-21 ("grass only near the camera"): scatter within 18 m (was 70 m), denser and taller,
# so it is a strip along the bottom edge and under the tree, not spread over the city view
R_NEAR = 18.0
gfg.nodes["Compare"].inputs["B"].default_value = R_NEAR
mr = gfg.nodes["Map Range"]
mr.inputs["From Min"].default_value = 2.0; mr.inputs["From Max"].default_value = R_NEAR
# owner 2026-11-21 "reduce grass density such that render is fast": 90/25 -> 35/12 per m2, scale 1.4-2.6 -> 1.0-2.0
mr.inputs["To Min"].default_value = 35.0; mr.inputs["To Max"].default_value = 12.0
rs = gfg.nodes["Random Value.002"]
rs.inputs["Min"].default_value = 1.0; rs.inputs["Max"].default_value = 2.0
# first test: the hill falls away right in front of the camera, so even 18 m of grass climbed into the
# middle of the frame over the city. Select by where a point lands in frame instead: at least 13 deg
# below the camera (bottom strip of the frame), or within 4 m of the tree trunk.
cam_l = bpy.data.objects["S08_Hill"].matrix_world.inverted() @ bpy.data.objects["CAM_S08"].matrix_world.translation
tree_o = bpy.data.objects["S08_Tree"]
trunk_l = bpy.data.objects["S08_Hill"].matrix_world.inverted() @ tree_o.matrix_world.translation
gp = node(gfg, "GeometryNodeInputPosition").outputs[0]
rel = vmath(gfg, "SUBTRACT", gp, tuple(cam_l))
rsep = node(gfg, "ShaderNodeSeparateXYZ"); gfg.links.new(rel, rsep.inputs[0])
hd = vmath(gfg, "LENGTH", vmath(gfg, "MULTIPLY", rel, (1.0, 1.0, 0.0)))
dep = math_n(gfg, "DIVIDE", math_n(gfg, "MULTIPLY", rsep.outputs["Z"], -1.0), math_n(gfg, "MAXIMUM", hd, 0.01))
low = math_n(gfg, "MINIMUM", math_n(gfg, "GREATER_THAN", dep, math.tan(math.radians(13))),
             math_n(gfg, "LESS_THAN", hd, 25.0))                 # and close: the slope far below is steep too
td = vmath(gfg, "LENGTH", vmath(gfg, "MULTIPLY", vmath(gfg, "SUBTRACT", gp, tuple(trunk_l)), (1.0, 1.0, 0.0)))
near_tree = math_n(gfg, "LESS_THAN", td, 4.0)
sel = math_n(gfg, "MAXIMUM", low, near_tree)
dist_node = gfg.nodes["Distribute Points on Faces"]
gfg.links.new(sel, dist_node.inputs["Selection"])
j = gfg.nodes["Join Geometry"]
for l in list(gfg.links):
    if l.to_node == j and l.from_node.bl_idname == "NodeGroupInput":
        gfg.links.remove(l)
iop = gfg.nodes["Instance on Points"]
out_link = next(l for l in gfg.links if l.from_node == iop)
to_sock = out_link.to_socket; gfg.links.remove(out_link)
ip = node(gfg, "GeometryNodeInputPosition").outputs[0]
# lean toward the flag's wind (bigger in gusts) + fast irregular shaking (2 and 4 Hz)
gsw = swell_node(gfg)
gu, gc = obj_uc(hill)
gw = wind_wave(gfg, ip, gu, gc)
k1 = loop_noise(gfg, ip, 1.5, FAST, 1.0)                                # small per-tuft jitter at the flag's 1.8 Hz
kx = node(gfg, "ShaderNodeSeparateXYZ"); gfg.links.new(k1, kx.inputs[0])
theta = math_n(gfg, "MULTIPLY", math_n(gfg, "ADD", 0.05, math_n(gfg, "ADD", math_n(gfg, "MULTIPLY", gw, 0.08),
                                                                 math_n(gfg, "MULTIPLY", kx.outputs["X"], 0.04))), gsw)
side = math_n(gfg, "MULTIPLY", kx.outputs["Y"], math_n(gfg, "MULTIPLY", gsw, 0.05))
# tilt toward +Y = -rot X, toward +X = +rot Y; wind (dx, dy), across = (-dy, dx)
rx = math_n(gfg, "SUBTRACT", math_n(gfg, "MULTIPLY", theta, -WIND.y), math_n(gfg, "MULTIPLY", side, WIND.x))
ry = math_n(gfg, "ADD", math_n(gfg, "MULTIPLY", theta, WIND.x), math_n(gfg, "MULTIPLY", side, -WIND.y))
lean = node(gfg, "ShaderNodeCombineXYZ"); gfg.links.new(rx, lean.inputs[0]); gfg.links.new(ry, lean.inputs[1])
# world-aligned tilt about each tuft's own base (Local Space OFF + pivot = instance position). The
# first tests pivoted on the hill origin and flung tufts 100s of m over the slope.
ri = node(gfg, "GeometryNodeRotateInstances"); ri.inputs["Local Space"].default_value = False
gfg.links.new(iop.outputs[0], ri.inputs["Instances"]); gfg.links.new(lean.outputs[0], ri.inputs["Rotation"])
gfg.links.new(node(gfg, "GeometryNodeInputPosition").outputs[0], ri.inputs["Pivot Point"])
gfg.links.new(ri.outputs[0], to_sock)
# The hill's faces are huge (100s of m), and the scatter selects per face, so one selected face
# spread grass far down the slope. Scatter on a fine patch (+-22 m around the camera, 0.4 m cells)
# laid onto the hill surface instead, in the hill's own space so the node maths stays the same.
hinv = hill.matrix_world.inverted()
cl = hinv @ bpy.data.objects["CAM_S08"].matrix_world.translation
R, STEPG = 22.0, 0.4
n = int(2 * R / STEPG) + 1
pv, pf = [], []
for iy in range(n):
    for ix in range(n):
        x, y = cl.x - R + ix * STEPG, cl.y - R + iy * STEPG
        ok, loc, _, _ = hill.ray_cast(Vector((x, y, cl.z + 500)), Vector((0, 0, -1)))
        pv.append((x, y, loc.z if ok else None))
# owner: "the grass only should be on the hill we are on" -> only cells on the hill top: every corner
# hit the hill and none lies more than 4 m below the ground under the camera (no drop-off faces)
okc, g0, _, _ = hill.ray_cast(Vector((cl.x, cl.y, cl.z + 500)), Vector((0, 0, -1)))
top_z = g0.z
for iy in range(n - 1):
    for ix in range(n - 1):
        a = iy * n + ix
        q = (a, a + 1, a + n + 1, a + n)
        if all(pv[k][2] is not None and pv[k][2] > top_z - 4.0 for k in q):
            pf.append(q)
pv = [(x, y, z if z is not None else top_z) for x, y, z in pv]
patch = bpy.data.meshes.new("S08_GrassPatch"); patch.from_pydata(pv, [], pf)
grass = bpy.data.objects.new("S08_GrassFG", patch)
fg.objects.link(grass); grass.matrix_world = hill.matrix_world.copy()
gm = grass.modifiers.new("S08_Grass", "NODES"); gm.node_group = gfg
hill.modifiers.remove(hill.modifiers["S08_Grass"])
# hill + road: invisible to the camera but still in the lighting. As holdouts they also killed the
# ground bounce and the grass came out ~30 % darker than in the finale plate.
for o in ([] if INPLACE else (hill, bpy.data.objects.get("S08_HillRoad"))):
    if o:
        o.is_holdout = False
        o.visible_camera = False
print("[fg] grass split from hill; hill + road hidden from camera, still lit")

# ------------------------------------------------------------------ kite: find a branch the camera sees against sky
cam = sc.camera
haze = bpy.data.objects.get("S08_HazeLayer")
if haze:
    haze.hide_viewport = True              # the camera sits inside it; it would catch every search ray
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
rx, ry = sc.render.resolution_x, sc.render.resolution_y


def cam_ray(px, py):
    """pixel (from top-left) -> world ray"""
    f = cam.data.lens; sw = cam.data.sensor_width
    x = (px / rx - 0.5) * sw; y = (0.5 - py / ry) * sw * ry / rx
    d = cam.matrix_world.to_3x3() @ Vector((x, y, -f))
    return cam.matrix_world.translation.copy(), d.normalized()


def hit(px, py):
    o, d = cam_ray(px, py)
    r = sc.ray_cast(dg, o, d)
    return r if r[0] and r[4] == tree else None


# owner 2026-11-21: "top edge, against sky", ~130 px tall. Search the upper crown for wood with open sky
# to the right and below (where the kite hangs), and sky above-right (so it reads against the sky).
def sky(px, py):
    o, d = cam_ray(px, py)
    return not sc.ray_cast(dg, o, d)[0]


best = None
for py in range(80, 300, 10):
    for px in range(200, 640, 10):
        r = hit(px, py)
        if not r or tree.data.polygons[r[3]].material_index == leaf_idx:   # want wood, not a leaf
            continue
        free = sum(1 for dy in range(15, 150, 15) for dx in (0, 40, 80) if sky(px + dx, py + dy))
        if free < 20:
            continue
        score = free - 0.02 * py                                    # prefer higher
        if best is None or score > best[0]:
            best = (score, px, py, r[1].copy())
if best:
    print("[fg] kite branch at px", best[1], best[2], "score %.1f" % best[0], "world", tuple(round(c, 2) for c in best[3]))
attach = best[3] if best else None
if os.environ.get("S08_KITE_AT"):                    # pin the owner-approved spot (in-place build sees more scene)
    attach = Vector(tuple(float(v) for v in os.environ["S08_KITE_AT"].split(",")))
    print("[fg] kite pinned at", tuple(attach))
if haze:
    haze.hide_viewport = False

# proxy: 3 verts in tree space, same sway -> the kite follows its branch
inv = tree.matrix_world.inverted()
pl = inv @ attach
pm = bpy.data.meshes.new("S08_KiteProxy")
pm.from_pydata([pl, pl + Vector((0.02 / s, 0, 0)), pl + Vector((0, 0, 0.02 / s))], [], [])
proxy = bpy.data.objects.new("S08_KiteProxy", pm); fg.objects.link(proxy)
proxy.matrix_world = tree.matrix_world.copy()
pmod = proxy.modifiers.new("S08_TreeSway", "NODES"); pmod.node_group = sway   # same matrix as the tree -> same field
proxy.hide_render = True

follow = bpy.data.objects.new("S08_KiteFollow", None); fg.objects.link(follow)
follow.parent = proxy; follow.parent_type = "VERTEX_3"; follow.parent_vertices = (0, 1, 2)
pivot = bpy.data.objects.new("S08_KitePivot", None); fg.objects.link(pivot)
pivot.parent = follow

# kite turned 40 deg away from the camera, rolled 22 deg, top corner 4 cm under the branch
to_cam = (cam.matrix_world.translation - attach); dist = to_cam.length; to_cam.z = 0; to_cam.normalize()
yaw = math.atan2(to_cam.y, to_cam.x) - math.pi / 2 + math.radians(55)
W_pivot = Matrix.Translation(attach + Vector((0, 0, -0.04))) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.radians(-22), 4, "Y")

# ---- paper: diamond sized to ~130 px tall in frame, grid so it can ripple; a ragged tear
D = 95 / sc.render.resolution_x * cam.data.sensor_width / cam.data.lens * dist   # owner: "make it little small" (was 130 px)
print("[fg] kite diagonal %.2f m at %.1f m" % (D, dist))
bm = bmesh.new(); N = 14
vs = {}
for i in range(N + 1):
    for j in range(N + 1):
        u, v = i / N - 0.5, j / N - 0.5                         # square in (u,v)
        x = (u - v) * D / 2.0
        z = -(u + v + 1.0) * D / 2.0                             # top corner at z=0
        bow = -0.05 * D * (1 - (2 * x / D) ** 2)                 # bowed back by the bamboo bow
        crease = -0.60 * abs(x) * (1 if x > 0 else 0.35)         # bent along the spine where it hit the branch
        vs[i, j] = bm.verts.new((x, bow + crease, z))
for i in range(N):
    for j in range(N):
        # ragged tear from the right corner inwards
        torn = (i >= N - 5 and j <= 3 and (i * 7 + j * 3) % 5 != 0) or (i >= N - 3 and j <= 5 and (i + j) % 3 == 0)
        if not torn:
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
# tail (pucchhar): small triangle under the bottom corner
t0 = bm.verts.new((0, 0, -D)); t1 = bm.verts.new((-0.09 * D, 0.0, -1.14 * D)); t2 = bm.verts.new((0.09 * D, 0.0, -1.14 * D))
bm.faces.new((t0, t2, t1))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
uvl = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for lp in f.loops:
        lp[uvl].uv = (lp.vert.co.x / D + 0.5, -lp.vert.co.z / D)
km = bpy.data.meshes.new("S08_KitePaper"); bm.to_mesh(km); bm.free()
for p in km.polygons:
    p.use_smooth = True
paper = bpy.data.objects.new("S08_KitePaper", km); fg.objects.link(paper); paper.parent = pivot

mk = bpy.data.materials.new("M_S08_KitePaper"); mk.use_nodes = True
nt = mk.node_tree; nt.nodes.clear()
outn = nt.nodes.new("ShaderNodeOutputMaterial")
pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
col = (0.72, 0.27, 0.035, 1)                                   # marigold, deeper so it sits in the dusk
pb.inputs["Roughness"].default_value = 0.7
# edging tape: a darker band ~6 % in from each edge of the diamond (UV: x 0..1, depth 0..1)
uvn = nt.nodes.new("ShaderNodeUVMap")
sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uvn.outputs[0], sep.inputs[0])
# distance to the diamond edge in UV space: 0.5 - (|u-0.5| + |v-0.5|)
def nm(op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op
    for i, v in ((0, a), (1, b)):
        if v is None:
            continue
        if isinstance(v, float):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]
du = nm("ABSOLUTE", nm("SUBTRACT", sep.outputs[0], 0.5)); dv = nm("ABSOLUTE", nm("SUBTRACT", sep.outputs[1], 0.5))
edge = nm("SUBTRACT", 0.5, nm("ADD", du, dv))
band = nm("LESS_THAN", edge, 0.035)
cr = nt.nodes.new("ShaderNodeMix"); cr.data_type = "RGBA"
nt.links.new(band, cr.inputs["Factor"])
cr.inputs["A"].default_value = col; cr.inputs["B"].default_value = (0.42, 0.10, 0.02, 1)   # darker tape
# a faint paper grain so it is not a flat sticker
grain = nt.nodes.new("ShaderNodeTexNoise"); grain.inputs["Scale"].default_value = 180.0; grain.inputs["Detail"].default_value = 4.0
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.06
nt.links.new(grain.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], pb.inputs["Normal"])
# bamboo spine (u = 0.5) and bow (v = 0.5, arched) seen as dark lines through the backlit tissue
spine = nm("LESS_THAN", nm("ABSOLUTE", nm("SUBTRACT", sep.outputs[0], 0.5)), 0.006)
arch = nm("ADD", 0.5, nm("MULTIPLY", nm("MULTIPLY", du, du), 0.25))
bowl = nm("LESS_THAN", nm("ABSOLUTE", nm("SUBTRACT", sep.outputs[1], arch)), 0.005)
sticks = nm("MAXIMUM", spine, bowl)
sh = nt.nodes.new("ShaderNodeMix"); sh.data_type = "RGBA"
nt.links.new(sticks, sh.inputs["Factor"]); nt.links.new(cr.outputs["Result"], sh.inputs["A"])
sh.inputs["B"].default_value = (0.12, 0.05, 0.02, 1)
nt.links.new(sh.outputs["Result"], pb.inputs["Base Color"])
tr = nt.nodes.new("ShaderNodeBsdfTranslucent"); nt.links.new(sh.outputs["Result"], tr.inputs["Color"])
mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 0.5    # thin tissue: dusk light comes through
nt.links.new(pb.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], outn.inputs["Surface"])
km.materials.append(mk)

# paper ripple: offset along the paper normal (local Y), stronger away from the spine and to the bottom
g = ng_new("GN_S08_KiteRipple")
gi = node(g, "NodeGroupInput"); go = node(g, "NodeGroupOutput")
pos = node(g, "GeometryNodeInputPosition").outputs[0]
sep = node(g, "ShaderNodeSeparateXYZ"); g.links.new(pos, sep.inputs[0])
wx = math_n(g, "MULTIPLY", math_n(g, "ABSOLUTE", sep.outputs["X"]), 1.0 / (D / 2))
wzz = math_n(g, "MULTIPLY", sep.outputs["Z"], -1.0 / D)
wk = math_n(g, "ADD", wx, math_n(g, "MULTIPLY", wzz, 0.6))
rn = loop_noise(g, vmath(g, "SCALE", pos, scale=1.0), 3.0, FAST, 1.0)      # paper ripples at the flag's 1.8 Hz
rsep = node(g, "ShaderNodeSeparateXYZ"); g.links.new(rn, rsep.inputs[0])
amp = math_n(g, "MULTIPLY", math_n(g, "MULTIPLY", math_n(g, "MULTIPLY", rsep.outputs["X"], wk), 0.05), swell_node(g))
cv = node(g, "ShaderNodeCombineXYZ"); g.links.new(amp, cv.inputs[1])
sp = node(g, "GeometryNodeSetPosition")
g.links.new(gi.outputs[0], sp.inputs["Geometry"]); g.links.new(cv.outputs[0], sp.inputs["Offset"]); g.links.new(sp.outputs[0], go.inputs[0])
paper.modifiers.new("S08_KiteRipple", "NODES").node_group = g
sol = paper.modifiers.new("S08_KiteSolid", "SOLIDIFY"); sol.thickness = 0.0008


# ---- bamboo spine + bow (curves), string
def curve_obj(name, pts, radius, mat, parent, world=False):
    cd = bpy.data.curves.new(name, "CURVE"); cd.dimensions = "3D"
    cd.bevel_depth = radius; cd.bevel_resolution = 2
    sp_ = cd.splines.new("POLY"); sp_.points.add(len(pts) - 1)
    for p, c in zip(sp_.points, pts):
        p.co = (c[0], c[1], c[2], 1)
    ob = bpy.data.objects.new(name, cd); fg.objects.link(ob); ob.parent = parent
    cd.materials.append(mat)
    return ob


mb = bpy.data.materials.new("M_S08_Bamboo"); mb.use_nodes = True
b = next(n for n in mb.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.45, 0.32, 0.15, 1); b.inputs["Roughness"].default_value = 0.5
curve_obj("S08_KiteSpine", [(0, -0.004, 0.01), (0, -0.004, -D - 0.005)], 0.0022, mb, pivot)
bow = [(D / 2 * (k / 10 - 0.5) * 2 * 1.02, -0.006 - 0.025 * (1 - (k / 5 - 1) ** 2), -D / 2) for k in range(11)]
curve_obj("S08_KiteBow", bow, 0.0016, mb, pivot)

ms = bpy.data.materials.new("M_S08_KiteString"); ms.use_nodes = True
b = next(n for n in ms.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.75, 0.72, 0.65, 1); b.inputs["Roughness"].default_value = 0.6
sc.frame_set(1); bpy.context.view_layer.update()

# parent inverses: world = parent @ inv @ basis -> make the empties sit exactly where wanted at frame 1
follow.matrix_parent_inverse = Matrix.Identity(4); follow.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
P0 = follow.matrix_world.copy()
follow.matrix_parent_inverse = P0.inverted() @ Matrix.Translation(attach)
bpy.context.view_layer.update()
pivot.matrix_parent_inverse = Matrix.Identity(4)
pivot.matrix_basis = follow.matrix_world.inverted() @ W_pivot
pivot["rest"] = list(pivot.rotation_euler)

# string in follow space: from the kite top round the branch twice, then hanging down in a lazy curve
wrap = []
for k in range(25):
    a = 2 * math.pi * 2.0 * k / 24
    wrap.append((0.022 * math.cos(a), 0.022 * math.sin(a), 0.03 - 0.0025 * k))
loc_top = follow.matrix_world.inverted() @ (W_pivot @ Vector((0, 0, 0)))
hang = [(0.03 + 0.05 * math.sin(k / 6), 0.01 * k, -0.02 - 0.11 * k) for k in range(12)]
curve_obj("S08_KiteString", [tuple(loc_top)] + wrap + hang, 0.0005, ms, follow)

# pivot swing: whole cycles over L so it loops; driven from the frame
rest = pivot.rotation_euler.copy()
# swing driven by the same flag wave field at the kite's spot: pushed out of its plane (X) as the
# waves pass, a little roll (Y) and yaw (Z) from the same field a quarter-wave later; x the flag swell
xk = (attach - POLE).dot(WIND)
for idx, (amp, dx) in enumerate([(0.11, 0.0), (0.035, 0.3), (0.05, 0.15)]):   # small wind
    fc = pivot.driver_add("rotation_euler", idx)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = "%.4f + %.3f*%s*%s" % (rest[idx], amp, SWELL_EXPR, wind_expr(xk + dx))
    if len(fc.driver.expression) > 250:
        print("[fg] long driver", idx, len(fc.driver.expression))
print("[fg] kite built, pivot", tuple(round(c, 2) for c in pivot.matrix_world.translation))

if not INPLACE:
    bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_fg.blend")
print("[fg] saved", bpy.data.filepath)

if os.environ.get("S08_TEST"):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "HIP"; prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == "HIP" and "9070" in dv.name
    sc.cycles.device = "GPU"; sc.cycles.samples = 32
    sc.render.resolution_percentage = 50
    out = ROOT + "/renders/s08_finale/test/fg"
    os.makedirs(out, exist_ok=True)
    for f in (1, 80, 160):
        sc.frame_set(f); sc.render.filepath = out + "/f_%04d.png" % f
        bpy.ops.render.render(write_still=True)
        print("[fg] rendered", f)
print("[fg] done")
