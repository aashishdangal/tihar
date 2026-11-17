"""s01 v039: cloud sea v3, after the render-critic report on v038 (0162_v038_vs_ref.md) and user notes.

Based on s01_cloud_sea2.py. Changes:
  - shape: round-capped Voronoi domes (1500 / 450 m) joined with Smooth Maximum instead of added;
    130 m puffs only on the heads; half the noise; 450 m tall (no more rocky ridges)
  - city glow: map blurred ~800 m and raised to power 1.8 so Kathmandu / Patan / Bhaktapur are
    separate pools; warm grey (no mauve); thin troughs glow brighter over the city
  - blue night tone on the heap tops (user: "blue instead of yellow")
  - translucent: troughs ~45% see-through, tops nearly opaque, so city lights show dimmed
  - soft contact with the hills: a ground-height map fades the cloud out where it meets terrain
  - edge darkening halved and widened (it drew a dark outline on every ridge)
  - slower fill: first patches ~130, city mostly dark ~155, full at 162
  - no volumetric hero heap: the zoom lands on the sea itself
Writes new maps (s01_cloudsea_glow_v039.exr, s01_cloudsea_ground_v039.exr) so v036-v038 keep theirs.

Run: blender.exe -b s01_hero_v032.blend --python scripts/s01_cloud_sea3.py -- <out.blend>
"""
import math, sys
import numpy as np
import bpy
from mathutils import Matrix, Vector

out_path = sys.argv[sys.argv.index("--") + 1]
HOLD0, FILL0, FILL1, END = 66, 114, 162, 198
Z_START, Z_END = 700.0, 1600.0   # layer base height (m); heaps add up to ~AMP on top
AMP = 450.0
GRID = 25.0                       # m between grid vertices
NAME = "S01_CloudSea"

sc = bpy.context.scene
cam = bpy.data.objects["CAM_S01"]

# --- clean up the earlier blockout (made in this session); keep the old dive slab but hide it
for n in ("S01_DarkCloud_Blockout",):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob)
lc = bpy.data.objects.get("S01_DiveCloud_LC")
if lc:
    lc.hide_render = lc.hide_viewport = True


# --- camera
def fcurves(idb):
    act = idb.animation_data.action
    if getattr(act, "fcurves", None):
        return list(act.fcurves)
    return [fc for l in act.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]


def rekey(idb, path, index, keys):
    fcs = [f for f in fcurves(idb) if f.data_path == path and f.array_index == index] if idb.animation_data and idb.animation_data.action else []
    if not fcs:
        for fr, v in keys:
            prop = path.rsplit(".", 1)[-1]
            setattr(idb, prop, v)
            idb.keyframe_insert(path, frame=fr)
        fcs = [f for f in fcurves(idb) if f.data_path == path and f.array_index == index]
    fc = fcs[0]
    fc.keyframe_points.clear()
    for fr, v in keys:
        kp = fc.keyframe_points.insert(fr, v)
        kp.interpolation = "BEZIER"
        kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    fc.update()


LOC = Vector((1500, -16500, 5200))
RX_SKY, RX_VAL, RX_ZOOM, RZ = 1.955, 1.440, 1.405, -0.052
fwd = Matrix.Rotation(RZ, 3, "Z") @ Matrix.Rotation(RX_VAL, 3, "X") @ Vector((0, 0, -1))
LOC_END = LOC + fwd * 400
K = [(1, LOC, RX_SKY), (12, LOC, RX_SKY), (HOLD0, LOC, RX_VAL), (FILL1, LOC, RX_VAL), (END, LOC_END, RX_ZOOM)]
for i in range(3):
    rekey(cam, "location", i, [(f, l[i]) for f, l, _ in K])
rekey(cam, "rotation_euler", 0, [(f, r) for f, _, r in K])
rekey(cam, "rotation_euler", 1, [(f, 0.0) for f, _, _ in K])
rekey(cam, "rotation_euler", 2, [(f, RZ) for f, _, _ in K])
L0 = cam.data.lens
cam.data.lens = L0
cam.data.keyframe_insert("lens", frame=FILL1)
cam.data.lens = L0 * 2.3
cam.data.keyframe_insert("lens", frame=END)
cam.data.lens = L0
sc.frame_start, sc.frame_end = 1, END
print(f"[sea] lens {L0:.1f} -> {L0 * 2.3:.1f} mm")

# --- extent: everything the camera can see of a layer at ~2 km, from 5 km ahead to 50 km out
X0, X1 = LOC.x - 30000, LOC.x + 30000
Y0, Y1 = LOC.y + 5000, LOC.y + 50000
W, H = X1 - X0, Y1 - Y0

# --- city glow map from the real light points
lp = bpy.data.objects["S01_LightPoints"]
me = lp.data
n = len(me.vertices)
co = np.empty(n * 3, np.float32)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3) @ np.array(lp.matrix_world.to_3x3()).T + np.array(lp.matrix_world.translation)
st = np.empty(n, np.float32)
me.attributes["lstr"].data.foreach_get("value", st)
col = np.empty(n * 4, np.float32)
me.attributes["lcol"].data.foreach_get("color", col)
col = col.reshape(-1, 4)[:, :3]
PX = 50.0
gw, gh = int(W / PX), int(H / PX)
ix = ((co[:, 0] - X0) / PX).astype(int)
iy = ((co[:, 1] - Y0) / PX).astype(int)
ok = (ix >= 0) & (ix < gw) & (iy >= 0) & (iy < gh)
grid = np.zeros((gh, gw), np.float64)
np.add.at(grid, (iy[ok], ix[ok]), st[ok])


def blur(a, sigma_px):
    r = int(sigma_px * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_px) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, a)


glow = blur(grid, 800.0 / PX)                     # light spreads ~800 m: city pools
glow /= np.percentile(glow[glow > 0], 99.5)
glow = np.clip(glow, 0, 1.3) ** 1.8               # separate pools, dark countryside
gcol = (col[ok] * st[ok, None]).sum(0) / st[ok].sum()
gcol = gcol / gcol.max()
print(f"[sea] glow map {gw}x{gh}, {ok.sum()} lights inside, mean light colour {np.round(gcol, 3)}")

# saved as an EXR next to the light data (a generated image is not kept in the .blend)
import os
gpath = os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath), "..", "assets", "lights", "s01_cloudsea_glow_v039.exr"))
os.makedirs(os.path.dirname(gpath), exist_ok=True)
tmp = bpy.data.images.new("tmp_glow", gw, gh, float_buffer=True, alpha=False)
px = np.ones((gh, gw, 4), np.float32)
px[..., 0] = px[..., 1] = px[..., 2] = glow
tmp.pixels.foreach_set(px.ravel())
tmp.filepath_raw = gpath
tmp.file_format = "OPEN_EXR"
tmp.save()
bpy.data.images.remove(tmp)
img = bpy.data.images.load(gpath)
img.name = "S01_CloudSea_Glow"
img.colorspace_settings.name = "Non-Color"
print("[sea] glow map saved", gpath)

# --- ground height under the cloud (max of the terrain meshes), for the soft contact fade
dgr = bpy.context.evaluated_depsgraph_get()
GPX = 200.0
ggw, ggh = int(W / GPX), int(H / GPX)
gnd = np.full((ggh, ggw), -1000.0, np.float32)
for tn in ("S01_Valley_PTerrain", "S01_Hills_GLO30", "S01_Himalaya_GLO30"):
    to = bpy.data.objects.get(tn)
    if not to:
        continue
    mi = to.matrix_world.inverted()
    dl = (mi.to_3x3() @ Vector((0, 0, -1))).normalized()
    for j in range(ggh):
        for i in range(ggw):
            hit, lo, *_ = to.ray_cast(mi @ Vector((X0 + (i + 0.5) * GPX, Y0 + (j + 0.5) * GPX, 12000.0)), dl, depsgraph=dgr)
            if hit:
                z = (to.matrix_world @ lo).z
                if z > gnd[j, i]:
                    gnd[j, i] = z
gpath2 = gpath.replace("glow_v039", "ground_v039")
tmp = bpy.data.images.new("tmp_ground", ggw, ggh, float_buffer=True, alpha=False)
px = np.ones((ggh, ggw, 4), np.float32)
px[..., 0] = px[..., 1] = px[..., 2] = gnd
tmp.pixels.foreach_set(px.ravel())
tmp.filepath_raw = gpath2
tmp.file_format = "OPEN_EXR"
tmp.save()
bpy.data.images.remove(tmp)
gimg = bpy.data.images.load(gpath2)
gimg.name = "S01_CloudSea_Ground"
gimg.colorspace_settings.name = "Non-Color"
print(f"[sea] ground map {ggw}x{ggh}: {np.percentile(gnd[gnd > -999], [5, 50, 95]).round()} m")

# --- zoom target: the brightest part of the city (glow blurred over ~1.5 km)
gb = blur(grid, 1500.0 / PX)
iy_, ix_ = np.unravel_index(np.argmax(gb), gb.shape)
TGT = Vector((X0 + (ix_ + 0.5) * PX, Y0 + (iy_ + 0.5) * PX, Z_END + 450))
d = TGT - LOC_END
RX_END, RZ_END = math.atan2(math.hypot(d.x, d.y), -d.z), math.atan2(-d.x, d.y)
rekey(cam, "rotation_euler", 0, [(1, RX_SKY), (12, RX_SKY), (HOLD0, RX_VAL), (FILL1, RX_VAL), (END, RX_END)])
rekey(cam, "rotation_euler", 2, [(1, RZ), (12, RZ), (HOLD0, RZ), (FILL1, RZ), (END, RZ_END)])
print(f"[sea] zoom target {tuple(round(c) for c in TGT)}  end rot x={math.degrees(RX_END):.1f} z={math.degrees(RZ_END):.1f}")

# --- geometry nodes: grid lifted into heaps
ng = bpy.data.node_groups.new("GN_" + NAME, "GeometryNodeTree")
ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
N = ng.nodes
L = ng.links
gin, gout = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
g = N.new("GeometryNodeMeshGrid")
g.inputs["Size X"].default_value = W
g.inputs["Size Y"].default_value = H
g.inputs["Vertices X"].default_value = int(W / GRID)
g.inputs["Vertices Y"].default_value = int(H / GRID)
tr = N.new("GeometryNodeTransform")
tr.inputs["Translation"].default_value = ((X0 + X1) / 2, (Y0 + Y1) / 2, 0)
L.new(g.outputs["Mesh"], tr.inputs["Geometry"])

pos = N.new("GeometryNodeInputPosition")
t = N.new("GeometryNodeInputSceneTime")
wind = N.new("ShaderNodeVectorMath")
wind.operation = "MULTIPLY_ADD"          # position + frame * wind
L.new(t.outputs["Frame"], wind.inputs[0])  # float -> vector (f,f,f)
wind.inputs[1].default_value = (9.0, 2.0, 0.0)
L.new(pos.outputs["Position"], wind.inputs[2])
wv = N.new("ShaderNodeMath")
wv.operation = "DIVIDE"
L.new(t.outputs["Frame"], wv.inputs[0])
wv.inputs[1].default_value = 48.0        # time-lapse churn


def tex(kind, scale, **kw):
    n_ = N.new(kind)
    for k, v in kw.items():
        setattr(n_, k, v)
    L.new(wind.outputs[0], n_.inputs["Vector"])
    L.new(wv.outputs[0], n_.inputs["W"])
    n_.inputs["Scale"].default_value = scale
    return n_


v1 = tex("ShaderNodeTexVoronoi", 1 / 1500.0, voronoi_dimensions="4D", feature="SMOOTH_F1")
v2 = tex("ShaderNodeTexVoronoi", 1 / 450.0, voronoi_dimensions="4D", feature="SMOOTH_F1")
v3 = tex("ShaderNodeTexVoronoi", 1 / 130.0, voronoi_dimensions="4D", feature="SMOOTH_F1")
nz = tex("ShaderNodeTexNoise", 1 / 700.0, noise_dimensions="4D")
nz.inputs["Detail"].default_value = 4
big = tex("ShaderNodeTexNoise", 1 / 6000.0, noise_dimensions="4D")


def m(op, a, b=None, clamp=False):
    n_ = N.new("ShaderNodeMath")
    n_.operation = op
    n_.use_clamp = clamp
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n_.inputs[i].default_value = x
        else:
            L.new(x, n_.inputs[i])
    return n_.outputs[0]


def cap(v, r):
    """round cap over each Voronoi cell: 1 at the centre, 0 at distance r"""
    mr = N.new("ShaderNodeMapRange")
    mr.clamp = True
    L.new(v.outputs["Distance"], mr.inputs[0])
    mr.inputs[1].default_value, mr.inputs[2].default_value = 0.0, r
    mr.inputs[3].default_value, mr.inputs[4].default_value = 1.0, 0.0
    return m("POWER", mr.outputs[0], 0.5)


c1, c2, c3 = cap(v1, 0.85), cap(v2, 0.8), cap(v3, 0.8)
smx = N.new("ShaderNodeMath")
smx.operation = "SMOOTH_MAX"
L.new(m("MULTIPLY", c1, 1.0), smx.inputs[0])
L.new(m("MULTIPLY", c2, 0.7), smx.inputs[1])
smx.inputs[2].default_value = 0.15
heads = smx.outputs[0]
lump = m("ADD", m("ADD", heads, m("MULTIPLY", m("MULTIPLY", c3, heads), 0.12)),
         m("MULTIPLY", m("SUBTRACT", nz.outputs["Fac"], 0.5), 0.12), clamp=True)
zoff = m("ADD", m("MULTIPLY", m("POWER", lump, 1.2), AMP), m("MULTIPLY", m("SUBTRACT", big.outputs["Fac"], 0.5), 250.0))
off = N.new("ShaderNodeCombineXYZ")
L.new(zoff, off.inputs["Z"])
sp = N.new("GeometryNodeSetPosition")
L.new(tr.outputs["Geometry"], sp.inputs["Geometry"])
L.new(off.outputs[0], sp.inputs["Offset"])
store = N.new("GeometryNodeStoreNamedAttribute")
store.data_type = "FLOAT"
store.domain = "POINT"
store.inputs["Name"].default_value = "lump"
L.new(sp.outputs["Geometry"], store.inputs["Geometry"])
L.new(lump, store.inputs["Value"])
smooth = N.new("GeometryNodeSetShadeSmooth")
L.new(store.outputs["Geometry"], smooth.inputs["Geometry"])
setm = N.new("GeometryNodeSetMaterial")
L.new(smooth.outputs["Geometry"], setm.inputs["Geometry"])
L.new(setm.outputs["Geometry"], gout.inputs[0])

# --- material: city glow through the cloud + faint sky tone on the heap tops
mat = bpy.data.materials.new("M_" + NAME)
mat.use_nodes = True
# the glow is for the camera only: don't turn 13M emissive triangles into sampled lights
for holder in (mat, getattr(mat, "cycles", None)):
    if holder is not None and hasattr(holder, "emission_sampling"):
        holder.emission_sampling = "NONE"
nt = mat.node_tree
nt.nodes.clear()
SN, SL = nt.nodes, nt.links


def sm(op, a, b=None, clamp=False):
    n_ = SN.new("ShaderNodeMath")
    n_.operation = op
    n_.use_clamp = clamp
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n_.inputs[i].default_value = x
        else:
            SL.new(x, n_.inputs[i])
    return n_.outputs[0]


tc = SN.new("ShaderNodeTexCoord")
sep = SN.new("ShaderNodeSeparateXYZ")
SL.new(tc.outputs["Object"], sep.inputs[0])
uv = SN.new("ShaderNodeCombineXYZ")
SL.new(sm("DIVIDE", sm("SUBTRACT", sep.outputs[0], X0), W), uv.inputs[0])
SL.new(sm("DIVIDE", sm("SUBTRACT", sep.outputs[1], Y0), H), uv.inputs[1])


def imgtex(im):
    n_ = SN.new("ShaderNodeTexImage")
    n_.image = im
    n_.extension = "EXTEND"
    n_.interpolation = "Cubic"
    SL.new(uv.outputs[0], n_.inputs["Vector"])
    return n_.outputs["Color"]


def smap(val, a, b, c, d):
    n_ = SN.new("ShaderNodeMapRange")
    n_.interpolation_type = "SMOOTHSTEP"
    n_.clamp = True
    SL.new(val, n_.inputs[0])
    for i, x in zip((1, 2, 3, 4), (a, b, c, d)):
        n_.inputs[i].default_value = x
    return n_.outputs[0]


def vscale(rgb, fac):
    n_ = SN.new("ShaderNodeVectorMath")
    n_.operation = "SCALE"
    n_.inputs[0].default_value = rgb
    SL.new(fac, n_.inputs["Scale"])
    return n_.outputs[0]


city = imgtex(img)
ground = imgtex(gimg)
lumpv = SN.new("ShaderNodeAttribute")
lumpv.attribute_name = "lump"
lump_ = lumpv.outputs["Fac"]
geo = SN.new("ShaderNodeNewGeometry")
nsep = SN.new("ShaderNodeSeparateXYZ")
SL.new(geo.outputs["Normal"], nsep.inputs[0])
psep = SN.new("ShaderNodeSeparateXYZ")
SL.new(geo.outputs["Position"], psep.inputs[0])
up = sm("POWER", sm("MAXIMUM", nsep.outputs[2], 0.0), 2.0)
lw = SN.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.7
shade = sm("SUBTRACT", 1.0, sm("MULTIPLY", lw.outputs["Facing"], 0.27))

# warm-grey city glow, brightest in the thin troughs over the city
GAIN = 0.04
cityf = sm("MULTIPLY", sm("MULTIPLY", city, sm("ADD", 0.6, sm("SUBTRACT", 1.0, lump_))), shade)
glowv = vscale((1.0 * GAIN, 0.93 * GAIN, 0.80 * GAIN), cityf)
# blue night tone on the heap tops
SKY = 0.016
skyf = sm("MULTIPLY", sm("MULTIPLY", sm("ADD", 0.35, sm("MULTIPLY", up, 0.65)), sm("ADD", 0.5, sm("MULTIPLY", lump_, 0.5))), shade)
skyv = vscale((0.55 * SKY, 0.68 * SKY, 1.0 * SKY), skyf)
add = SN.new("ShaderNodeVectorMath")
add.operation = "ADD"
SL.new(glowv, add.inputs[0])
SL.new(skyv, add.inputs[1])
em = SN.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 1.0
SL.new(add.outputs[0], em.inputs["Color"])

# translucency: troughs see-through, heads nearly opaque; fade out where the cloud meets the hills
depth = sm("SUBTRACT", psep.outputs[2], ground)
contact = smap(depth, 0.0, 250.0, 0.0, 1.0)
alpha = sm("MULTIPLY", smap(lump_, 0.05, 0.6, 0.45, 0.97), contact)
trn = SN.new("ShaderNodeBsdfTransparent")
mix = SN.new("ShaderNodeMixShader")
SL.new(alpha, mix.inputs[0])
SL.new(trn.outputs[0], mix.inputs[1])
SL.new(em.outputs[0], mix.inputs[2])
mo = SN.new("ShaderNodeOutputMaterial")
SL.new(mix.outputs[0], mo.inputs["Surface"])
setm.inputs["Material"].default_value = mat

# --- object
me = bpy.data.meshes.new(NAME)
ob = bpy.data.objects.new(NAME, me)
sc.collection.objects.link(ob)
md = ob.modifiers.new("CloudSea", "NODES")
md.node_group = ng
for a in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
    setattr(ob, a, False)
# rise: slowly through the city's height (floor ~1300-1400 m) so the lights go out patch by
# patch, then faster to fill the bowl up to the rim hills
for f, z in ((FILL0, Z_START), (130, 950.0), (155, 1400.0), (FILL1, Z_END)):
    ob.location.z = z
    ob.keyframe_insert("location", index=2, frame=f)
# not in the render before the fill starts
ob.hide_render = True
ob.keyframe_insert("hide_render", frame=FILL0 - 1)
ob.hide_render = False
ob.keyframe_insert("hide_render", frame=FILL0)


bpy.ops.wm.save_as_mainfile(filepath=out_path, copy=False)
print("[sea] saved", out_path)
