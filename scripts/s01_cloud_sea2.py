"""s01 v038: cloud sea v2 (Spring cloud recipe for the heaps) + one volumetric hero heap where the zoom lands.

Based on s01_cloud_sea.py (v037). Changes:
  - heaps: 3 stacked Voronoi domes (1500 / 450 / 130 m) + noise, after the Blender Studio "Spring"
    procedural cloud recipe, 700 m tall with deep troughs; as the layer rises the heap tops break
    through the valley floor first, so the city goes dark patch by patch
  - shading: heap tops get a faint sky tone (by normal), sides/troughs the warm city glow
  - zoom ends looking at the brightest part of the city, where a volumetric hero heap
    (Spring clouds.blend cubes + density recipe, absorption + emission only, no scattering) rises
    out of the sea
fades to black. Replaces the sweep-in cloud. References: user's night sea-of-cloud photos; the
light comes only from the city below (new-moon night, no moon).

  - Cloud tops are real geometry (geometry nodes): a 20 m grid lifted into cumulus heaps
    (Voronoi domes + noise), churning fast like a time-lapse (4D noise W follows the frame) and
    drifting with the wind. A named attribute "lump" (0 trough .. 1 heap top) goes to the shader.
  - The layer rises from below the valley floor (frame 114) to ~2200 m (frame 162): it floods the
    lowest ground first, swallows the city and leaves the rim hills and Himalaya standing out.
  - Shader is emission only: a blurred map of the real light points (city glow seen through
    the cloud) x thinner-in-the-troughs, plus a faint dark-blue sky tone on the heap tops.
    Camera-visible only (does not shadow or light anything else).
  - Camera: still through the fill, then 162-198 a lens zoom (x2.3) with a slight tilt and push
    toward the glowing city. Web fades to black over ~186-198.

Run: blender.exe -b s01_hero_v032.blend --python scripts/s01_cloud_sea2.py -- <out.blend>
"""
import math, sys
import numpy as np
import bpy
from mathutils import Matrix, Vector

out_path = sys.argv[sys.argv.index("--") + 1]
HOLD0, FILL0, FILL1, END = 66, 114, 162, 198
Z_START, Z_END = 550.0, 1700.0   # layer base height (m); heaps add up to ~AMP on top
AMP = 700.0
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


glow = blur(grid, 350.0 / PX)                     # light spreads ~350 m inside the cloud
glow /= np.percentile(glow[glow > 0], 99.5)
glow = np.clip(glow, 0, 1.5) ** 0.8
gcol = (col[ok] * st[ok, None]).sum(0) / st[ok].sum()
gcol = gcol / gcol.max()
print(f"[sea] glow map {gw}x{gh}, {ok.sum()} lights inside, mean light colour {np.round(gcol, 3)}")

# saved as an EXR next to the light data (a generated image is not kept in the .blend)
import os
gpath = os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath), "..", "assets", "lights", "s01_cloudsea_glow.exr"))
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


def dome(v, w):
    return m("MULTIPLY", m("POWER", m("SUBTRACT", 1.0, m("MULTIPLY", v.outputs["Distance"], 1.2), clamp=True), 0.7), w)


lump = m("ADD", m("ADD", dome(v1, 0.55), dome(v2, 0.30)), m("ADD", dome(v3, 0.12),
         m("MULTIPLY", m("SUBTRACT", nz.outputs["Fac"], 0.5), 0.25)), clamp=True)
zoff = m("ADD", m("MULTIPLY", m("POWER", lump, 1.4), AMP), m("MULTIPLY", m("SUBTRACT", big.outputs["Fac"], 0.5), 300.0))
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
it = SN.new("ShaderNodeTexImage")
it.image = img
it.extension = "EXTEND"
it.interpolation = "Cubic"
SL.new(uv.outputs[0], it.inputs["Vector"])
at = SN.new("ShaderNodeAttribute")
at.attribute_name = "lump"
lw = SN.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.5
shade = sm("SUBTRACT", 1.0, sm("MULTIPLY", lw.outputs["Facing"], 0.55))
thin = sm("SUBTRACT", 1.25, sm("MULTIPLY", at.outputs["Fac"], 1.0))
gfac = sm("MULTIPLY", sm("MULTIPLY", sm("MULTIPLY", it.outputs["Color"], thin), shade), 1.0)
GAIN = 0.11
glowc = SN.new("ShaderNodeMix")
glowc.data_type = "RGBA"
glowc.blend_type = "MULTIPLY"
glowc.inputs["Factor"].default_value = 1.0
glowc.inputs["A"].default_value = (*(float(c) * GAIN for c in (0.55 * gcol + 0.45 * np.array([1.0, 0.62, 0.35]))), 1)
glowc.inputs["B"].default_value = (1, 1, 1, 1)
mulg = SN.new("ShaderNodeVectorMath")
mulg.operation = "SCALE"
SL.new(glowc.outputs["Result"], mulg.inputs[0])
SL.new(gfac, mulg.inputs["Scale"])
geo = SN.new("ShaderNodeNewGeometry")
nsep = SN.new("ShaderNodeSeparateXYZ")
SL.new(geo.outputs["Normal"], nsep.inputs[0])
up = sm("POWER", sm("MAXIMUM", nsep.outputs[2], 0.0), 2.0)
skyf = sm("MULTIPLY", sm("MULTIPLY", sm("ADD", 0.3, sm("MULTIPLY", at.outputs["Fac"], 0.7)), shade), sm("ADD", 0.25, sm("MULTIPLY", up, 0.75)))
sky = SN.new("ShaderNodeVectorMath")
sky.operation = "SCALE"
sky.inputs[0].default_value = (0.0025, 0.0030, 0.0045)
SL.new(skyf, sky.inputs["Scale"])
add = SN.new("ShaderNodeVectorMath")
add.operation = "ADD"
SL.new(mulg.outputs[0], add.inputs[0])
SL.new(sky.outputs[0], add.inputs[1])
em = SN.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 1.0
SL.new(add.outputs[0], em.inputs["Color"])
mo = SN.new("ShaderNodeOutputMaterial")
SL.new(em.outputs[0], mo.inputs["Surface"])
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
for f, z in ((FILL0, Z_START), (FILL1, Z_END)):
    ob.location.z = z
    ob.keyframe_insert("location", index=2, frame=f)
# not in the render before the fill starts
ob.hide_render = True
ob.keyframe_insert("hide_render", frame=FILL0 - 1)
ob.hide_render = False
ob.keyframe_insert("hide_render", frame=FILL0)

# --- volumetric hero heap (Blender Studio "Spring" procedural clouds) at the zoom target
SPRING = r"C:\Users\user\Downloads\Procedural Volumetric Clouds\clouds.blend"
with bpy.data.libraries.load(SPRING, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("Cube")]
cubes = [o for o in dst.objects if o]
hc = bpy.data.collections.new("S01_HeroHeap")
sc.collection.children.link(hc)
heap = bpy.data.objects.new("S01_HeroHeap", None)
hc.objects.link(heap)
cen = sum((o.location for o in cubes), Vector()) / len(cubes)
ext = max(max(abs(o.location.x - cen.x), abs(o.location.y - cen.y)) + max(o.dimensions) / 2 for o in cubes)
S = 900.0 / ext                                   # heap ~1.8 km across
for o in cubes:
    hc.objects.link(o)
    o.location = o.location - cen
    o.parent = heap
    for a in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
        setattr(o, a, False)
heap.scale = (S, S, S)
HZ = 250.0                                        # heap centre above the layer base
for f, z in ((FILL0, Z_START), (FILL1, Z_END)):
    heap.location = (TGT.x, TGT.y, z + HZ)
    heap.keyframe_insert("location", frame=f)
for o in cubes + [heap]:
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=FILL0 - 1)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=FILL0)

# material: keep Spring's density recipe, replace the lit volume with absorption + emission
# (no scattering, so no light sampling inside the volume; the glow saturates at the city-glow colour)
hm = cubes[0].active_material
hm.name = "M_S01_HeroHeap"
hn, hl = hm.node_tree.nodes, hm.node_tree.links
pv = next(n for n in hn if n.type == "PRINCIPLED_VOLUME")
src_sock = pv.inputs["Density"].links[0].from_socket
mout = next(n for n in hn if n.type == "OUTPUT_MATERIAL")
k = hn.new("ShaderNodeMath"); k.operation = "MULTIPLY"; k.inputs[1].default_value = 1.6 / S
hl.new(src_sock, k.inputs[0])
ab = hn.new("ShaderNodeVolumeAbsorption"); ab.inputs["Color"].default_value = (0, 0, 0, 1)
hl.new(k.outputs[0], ab.inputs["Density"])
tch = hn.new("ShaderNodeTexCoord"); tch.object = heap
hs = hn.new("ShaderNodeSeparateXYZ"); hl.new(tch.outputs["Object"], hs.inputs[0])
hg = hn.new("ShaderNodeMapRange")
hg.inputs[1].default_value = -0.4 * ext; hg.inputs[2].default_value = 0.6 * ext
hg.inputs[3].default_value = 1.3; hg.inputs[4].default_value = 0.25
hl.new(hs.outputs[2], hg.inputs[0])
gat = float(glow[iy_, ix_])
ec = hn.new("ShaderNodeMath"); ec.operation = "MULTIPLY"
hl.new(k.outputs[0], ec.inputs[0]); hl.new(hg.outputs[0], ec.inputs[1])
emn = hn.new("ShaderNodeEmission")
emn.inputs["Color"].default_value = (*(float(c) * GAIN * min(gat, 1.2) for c in (0.55 * gcol + 0.45 * np.array([1.0, 0.62, 0.35]))), 1)
hl.new(ec.outputs[0], emn.inputs["Strength"])
addv = hn.new("ShaderNodeAddShader")
hl.new(ab.outputs[0], addv.inputs[0]); hl.new(emn.outputs[0], addv.inputs[1])
hl.new(addv.outputs[0], mout.inputs["Volume"])
for o in cubes:
    o.active_material = hm
print(f"[sea] hero heap: {len(cubes)} Spring cubes, scale {S:.0f}, ext {ext:.2f}, glow at target {gat:.2f}")

bpy.ops.wm.save_as_mainfile(filepath=out_path, copy=False)
print("[sea] saved", out_path)
