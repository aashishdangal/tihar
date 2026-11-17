"""s01 v042: built ON v039 (s01_hero_v039.blend; v040/v041 dropped by the user).
User on v039: 0162 is what they envisioned; but the cloud is too translucent (all frames), too warm
(wants a little blue), and the onset (0140) looks unrealistic.

Research on how valley fog really forms at night (radiation fog):
  - cold air drains downhill and pools in the lowest ground; fog condenses there first (river beds,
    wet fields: in Kathmandu the Bagmati / Khokana / Taudaha), as thin layers a little above the
    ground, growing in place, not sliding in as a sheet
  - lights under thin fog are not cut off: they lose contrast and bloom into halos, the fog glows
    from inside in the city's own colours, then they fade out
  - the inversion caps the top, so it ends as a flat-topped sea (= the v039 0162 look)

So, keeping v039's cloud sea geometry and camera:
  1. S01_Mist_0..2: three thin flat mist layers just above the lowest ground, rising slowly; wispy,
     streaked noise; present only where the ground is below the layer (lowest ground first, soft
     contact); lit from below by a small-radius RGB halo map of the real light points
  2. cloud sea: new material M_S01_CloudSea_v042. Coverage forms from the low ground outward
     (keyed level S01_FormLevel against the ground map, edges broken by noise), opaque once formed
     (v039 troughs were 45 % see-through), soft contact with the hills kept
  3. glow tint a little blue (v039 was warm 1/.93/.80), same luminance as v039

Run: blender.exe -b s01_hero_v039.blend --python scripts/s01_cloud_sea7.py -- <out.blend>
"""
import math, os, sys
import numpy as np
import bpy
from mathutils import Vector

out_path = sys.argv[sys.argv.index("--") + 1]
TAG = os.path.splitext(os.path.basename(out_path))[0].rsplit("_", 1)[-1]   # e.g. "v045": maps are per version so older files keep theirs
sc = bpy.context.scene
sea = bpy.data.objects["S01_CloudSea"]

# same extent as s01_cloud_sea3.py (v039)
LOC = Vector((1500, -16500, 5200))
X0, X1 = LOC.x - 30000, LOC.x + 30000
Y0, Y1 = LOC.y + 5000, LOC.y + 50000
W, H = X1 - X0, Y1 - Y0

glow_img = bpy.data.images["S01_CloudSea_Glow"]   # kept: it gave the 0162 look the user likes
LIGHTS = os.path.abspath(os.path.join(os.path.dirname(bpy.data.filepath), "..", "assets", "lights"))


def save_exr(arr, path, name):
    """Write float data exactly (Image.save() of a generated float image altered the values: the v039
    ground map came back as 12-31 m instead of ~1300 m, so v039's soft hill contact never worked).
    arr rows go from Y0 (bottom) up, like Blender's pixels; OIIO writes top-down, hence the flip."""
    import OpenImageIO as oiio
    a = np.ascontiguousarray(np.flipud(arr.astype(np.float32)))
    if a.ndim == 2:
        a = a[..., None].repeat(3, 2)
    out = oiio.ImageOutput.create(path)
    out.open(path, oiio.ImageSpec(a.shape[1], a.shape[0], a.shape[2], "float"))
    out.write_image(a)
    out.close()
    im = bpy.data.images.load(path, check_existing=False)
    im.name = name
    im.colorspace_settings.name = "Non-Color"
    return im


# --- ground height under the sea (max of the terrain meshes), recomputed and saved exactly
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
ground_img = save_exr(gnd, os.path.join(LIGHTS, f"s01_cloudsea_ground_{TAG}.exr"), "S01_CloudSea_Ground_v042")
chk = np.array(ground_img.pixels[:], np.float32).reshape(ggh, ggw, 4)[..., 0]
print(f"[v042] ground map {ggw}x{ggh}: p5/50/95 {np.percentile(gnd[gnd > -999], [5, 50, 95]).round()} m; "
      f"read back max error {np.abs(chk - gnd).max():.3f} m")

# --- halo map: light points blurred ~150 m, RGB (the mist glows in the lights' own colours)
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
rgb = np.zeros((gh, gw, 3), np.float64)
for c in range(3):
    np.add.at(rgb[..., c], (iy[ok], ix[ok]), st[ok] * col[ok, c])


def blur(a, sigma_px):
    r = int(sigma_px * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_px) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, a)


# render-critic on v044 0150 (fix 2): glow too even, no cores. Near halo (150 m) + wide spread
# (700 m): bright cores over the dense districts falling off over 1-2 km; also blends the hue
for c in range(3):
    rgb[..., c] = 0.55 * blur(rgb[..., c], 150.0 / PX) + 0.45 * blur(rgb[..., c], 700.0 / PX)
lum = rgb.sum(-1)
rgb /= np.percentile(lum[lum > 0], 99.5) / 3.0
lum = rgb.sum(-1) / 3.0
rgb *= (np.clip(lum, 0, 2.0) ** 1.35 / np.maximum(lum, 1e-9))[..., None]   # cores up, faint edges down (v045: **0.75 lifted them)
# user on v044: "a little too colorful". Keep 35 % of the lights' own colour, the rest goes to the
# cloud's blue tint, so the mist glows like the sea it turns into (fog mixes the colours anyway)
# v047 (user: "environment casts multiple colours but the mist only shows white - realistic?"): fog takes
# the colour of the light on it; from km up the city's lights blend into a warm-neutral glow with gentle
# district-to-district tints. The 700 m blur already removes v044's patchwork, so keep 60 % of the real
# colour and no blue pull (the blue belongs to the finished sea top, 0162).
HALO_SAT = 0.6
HALO_TINT = np.array((1.0, 1.0, 1.0))
lum3 = rgb.mean(-1, keepdims=True)
rgb = rgb * HALO_SAT + lum3 * HALO_TINT / HALO_TINT.mean() * (1.0 - HALO_SAT)
halo_img = save_exr(rgb, os.path.join(LIGHTS, f"s01_mist_halo_{TAG}.exr"), "S01_Mist_Halo")
print(f"[v042] halo map {gw}x{gh}, max {rgb.max():.2f}")

# --- valley floor heights under the city (ground map is 200 m, halo map 50 m)
gp = gnd
hl = lum[: ggh * 4, : ggw * 4].reshape(ggh, 4, ggw, 4).mean((1, 3))
city = (hl > 0.03) & (gp > -999)
F5, F25, F50, F75 = np.percentile(gp[city], [5, 25, 50, 75])
print(f"[v042] city floor m: p5 {F5:.0f}  p25 {F25:.0f}  p50 {F50:.0f}  p75 {F75:.0f}")


# --- shader helpers
class SB:
    def __init__(self, nt):
        self.N, self.L = nt.nodes, nt.links

    def m(self, op, a, b=None, clamp=False):
        n_ = self.N.new("ShaderNodeMath")
        n_.operation = op
        n_.use_clamp = clamp
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n_.inputs[i].default_value = x
            else:
                self.L.new(x, n_.inputs[i])
        return n_.outputs[0]

    def smap(self, val, a, b, c, d):
        n_ = self.N.new("ShaderNodeMapRange")
        n_.interpolation_type = "SMOOTHSTEP"
        n_.clamp = True
        self.L.new(val, n_.inputs[0])
        for i, x in zip((1, 2, 3, 4), (a, b, c, d)):
            if isinstance(x, (int, float)):
                n_.inputs[i].default_value = x
            else:
                self.L.new(x, n_.inputs[i])
        return n_.outputs[0]

    def vscale(self, rgb_, fac):
        n_ = self.N.new("ShaderNodeVectorMath")
        n_.operation = "SCALE"
        if isinstance(rgb_, tuple):
            n_.inputs[0].default_value = rgb_
        else:
            self.L.new(rgb_, n_.inputs[0])
        self.L.new(fac, n_.inputs["Scale"])
        return n_.outputs[0]

    def vadd(self, a, b):
        n_ = self.N.new("ShaderNodeVectorMath")
        n_.operation = "ADD"
        self.L.new(a, n_.inputs[0])
        self.L.new(b, n_.inputs[1])
        return n_.outputs[0]

    def value(self, name):
        n_ = self.N.new("ShaderNodeValue")
        n_.name = n_.label = name
        return n_

    def maps(self):
        """world position (separated) and the map UV"""
        geo = self.N.new("ShaderNodeNewGeometry")
        ps = self.N.new("ShaderNodeSeparateXYZ")
        self.L.new(geo.outputs["Position"], ps.inputs[0])
        uv = self.N.new("ShaderNodeCombineXYZ")
        self.L.new(self.m("DIVIDE", self.m("SUBTRACT", ps.outputs[0], X0), W), uv.inputs[0])
        self.L.new(self.m("DIVIDE", self.m("SUBTRACT", ps.outputs[1], Y0), H), uv.inputs[1])
        return geo, ps, uv

    def img(self, im, uv):
        n_ = self.N.new("ShaderNodeTexImage")
        n_.image = im
        n_.extension = "EXTEND"
        n_.interpolation = "Cubic"
        self.L.new(uv.outputs[0], n_.inputs["Vector"])
        return n_

    def noise(self, ps, sx, sy, w, detail=5, rough=0.6, zoff=0.0):
        """4D noise, stretched (sx, sy in metres), evolving with w"""
        v = self.N.new("ShaderNodeCombineXYZ")
        self.L.new(self.m("DIVIDE", ps.outputs[0], sx), v.inputs[0])
        self.L.new(self.m("DIVIDE", ps.outputs[1], sy), v.inputs[1])
        v.inputs[2].default_value = zoff
        n_ = self.N.new("ShaderNodeTexNoise")
        n_.noise_dimensions = "4D"
        n_.inputs["Scale"].default_value = 1.0
        n_.inputs["Detail"].default_value = detail
        n_.inputs["Roughness"].default_value = rough
        self.L.new(v.outputs[0], n_.inputs["Vector"])
        self.L.new(w, n_.inputs["W"])
        return n_.outputs["Fac"]


def key_value(node, keys, linear=False):
    for f, v in keys:
        node.outputs[0].default_value = v
        node.outputs[0].keyframe_insert("default_value", frame=f)
    if linear:
        nt = node.id_data
        for fc in fcurves_of(nt):
            if node.name in fc.data_path:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def fcurves_of(idb):
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if getattr(act, "fcurves", None):
        return list(act.fcurves)
    return [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def no_emission_sampling(mat):
    for holder in (mat, getattr(mat, "cycles", None)):
        if holder is not None and hasattr(holder, "emission_sampling"):
            holder.emission_sampling = "NONE"


# ============ 1. cloud sea: new material (v039's left in the file, unused)
mat = bpy.data.materials.new("M_S01_CloudSea_v042")
mat.use_nodes = True
no_emission_sampling(mat)
nt = mat.node_tree
nt.nodes.clear()
b = SB(nt)
geo, ps, uv = b.maps()
cityv = b.img(glow_img, uv).outputs["Color"]
ground = b.img(ground_img, uv).outputs["Color"]
lumpa = b.N.new("ShaderNodeAttribute")
lumpa.attribute_name = "lump"
lump_ = lumpa.outputs["Fac"]
nsep = b.N.new("ShaderNodeSeparateXYZ")
b.L.new(geo.outputs["Normal"], nsep.inputs[0])
up = b.m("POWER", b.m("MAXIMUM", nsep.outputs[2], 0.0), 2.0)
lw = b.N.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.7
shade = b.m("SUBTRACT", 1.0, b.m("MULTIPLY", lw.outputs["Facing"], 0.27))

# glow: v039's formula, tint moved from warm (1, .93, .80) to a little blue at the same luminance
TINT = (0.84, 0.91, 1.0)
lum_old = 0.2126 * 1.0 + 0.7152 * 0.93 + 0.0722 * 0.80
lum_new = 0.2126 * TINT[0] + 0.7152 * TINT[1] + 0.0722 * TINT[2]
GAIN = 0.04 * lum_old / lum_new
HALO_GAIN = 0.22                          # city halo on the mist (and on the forming sea); v042a 0.075: no visible halos
cityf = b.m("MULTIPLY", b.m("MULTIPLY", cityv, b.m("ADD", 0.6, b.m("SUBTRACT", 1.0, lump_))), shade)
glowv = b.vscale(tuple(c * GAIN for c in TINT), cityf)
SKY = 0.016
skyf = b.m("MULTIPLY", b.m("MULTIPLY", b.m("ADD", 0.35, b.m("MULTIPLY", up, 0.65)), b.m("ADD", 0.5, b.m("MULTIPLY", lump_, 0.5))), shade)
skyv = b.vscale((0.55 * SKY, 0.68 * SKY, 1.0 * SKY), skyf)
em = b.N.new("ShaderNodeEmission")
# while the sea forms over the glowing mist it must be lit from below just as brightly (v043: the
# new patches were darker than the mist and read as stains); handed back to the 0162 look by 158
seahalo = b.value("S01_SeaHalo")
halo_s = b.img(halo_img, uv).outputs["Color"]
hv = b.vscale(halo_s, b.m("MULTIPLY", b.m("MULTIPLY", seahalo.outputs[0], HALO_GAIN), shade))
b.L.new(b.vadd(b.vadd(glowv, skyv), hv), em.inputs["Color"])
key_value(seahalo, [(126, 1.0), (148, 1.0), (158, 0.0)])

# coverage: forms over the lowest ground first, spreads up the valley as S01_FormLevel rises;
# edges broken by streaky noise so there is no coastline
drift = b.value("S01_Drift")
form = b.value("S01_FormLevel")
edge = b.noise(ps, 900.0, 500.0, drift.outputs[0], detail=6, rough=0.62)
reach = b.m("ADD", b.m("SUBTRACT", form.outputs[0], ground), b.m("MULTIPLY", b.m("SUBTRACT", edge, 0.5), 200.0))   # critic fix 1: 420 -> 200, terrain sets the edge
cover = b.smap(reach, 0.0, 220.0, 0.0, 1.0)
# soft contact with the hills, broken by noise. Narrow (150 m): over the city the troughs of the
# full sea are only ~270 m above the floor and must stay opaque
cn = b.noise(ps, 900.0, 900.0, drift.outputs[0], detail=3, zoff=7.0)
depth = b.m("ADD", b.m("SUBTRACT", ps.outputs[2], ground), b.m("MULTIPLY", b.m("SUBTRACT", cn, 0.5), 200.0))
contact = b.smap(depth, 0.0, 150.0, 0.0, 1.0)
alpha = b.m("MULTIPLY", cover, contact)            # opaque once formed (v039: troughs 45 % see-through)
trn = b.N.new("ShaderNodeBsdfTransparent")
mix = b.N.new("ShaderNodeMixShader")
b.L.new(alpha, mix.inputs[0])
b.L.new(trn.outputs[0], mix.inputs[1])
b.L.new(em.outputs[0], mix.inputs[2])
mo = b.N.new("ShaderNodeOutputMaterial")
b.L.new(mix.outputs[0], mo.inputs["Surface"])

key_value(drift, [(100, 0.0), (198, 1.6)], linear=True)
key_value(form, [(126, F5 - 250), (140, F25), (150, F75 + 120), (157, F75 + 700), (162, 4500.0)])


# ============ critic fix 1 (v044 0150): while forming, the sea is a flat sheet in the low ground.
# Real forming fog has a flat top; the 450 m heads only belong to the mature sea (0162 unchanged).
gn = sea.modifiers["CloudSea"].node_group
amp = [nd for nd in gn.nodes if nd.type == "MATH" and nd.operation == "MULTIPLY" and abs(nd.inputs[1].default_value - 450.0) < 1e-3]
bign = [nd for nd in gn.nodes if nd.type == "MATH" and nd.operation == "MULTIPLY" and abs(nd.inputs[1].default_value - 250.0) < 1e-3]
assert len(amp) == 1 and len(bign) == 1, (len(amp), len(bign))
for nd, (lo, hi) in ((amp[0], (70.0, 450.0)), (bign[0], (40.0, 250.0))):
    for f, v in ((114, lo), (148, lo), (160, hi)):
        nd.inputs[1].default_value = v
        nd.inputs[1].keyframe_insert("default_value", frame=f)
# sea height: just under the river corridors at 140, at the city floor at 150, then v039's keys
zf = next(fc for fc in fcurves_of(sea) if fc.data_path == "location" and fc.array_index == 2)
zf.keyframe_points.clear()
for f, z in ((114, 700.0), (130, 950.0), (140, F25 - 60), (150, F50 - 10), (155, 1400.0), (162, 1600.0)):
    kp = zf.keyframe_points.insert(f, z)
    kp.interpolation = "BEZIER"
    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
zf.update()
print(f"[v042] forming sea flat until 148 (lumps 70 m, noise 40 m); z 140={F25 - 60:.0f} 150={F50 - 10:.0f}")

setm = next(nd for nd in sea.modifiers["CloudSea"].node_group.nodes if nd.type == "SET_MATERIAL")
setm.inputs["Material"].default_value = mat
print(f"[v042] sea material set; glow gain {GAIN:.4f} tint {TINT}")

# ============ 2. ground mist: three thin layers over the lowest ground
MIST_OFF = (12.0, 45.0, 95.0)              # m above the rising mist level
MIST_MAX = (0.85, 0.70, 0.55)              # critic fix 3: dense enough that points vanish in the cores (v045 0.62/0.50/0.40 let ~11 % through)
mcoll = bpy.data.collections.get("S01_Mist") or bpy.data.collections.new("S01_Mist")
if mcoll.name not in sc.collection.children:
    sc.collection.children.link(mcoll)
for i, (off, amax) in enumerate(zip(MIST_OFF, MIST_MAX)):
    name = f"S01_Mist_{i}"
    mm = bpy.data.meshes.new(name)
    mm.from_pydata([(X0, Y0, 0), (X1, Y0, 0), (X1, Y1, 0), (X0, Y1, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, mm)
    mcoll.objects.link(ob)
    for a in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
        setattr(ob, a, False)

    mat = bpy.data.materials.new("M_" + name)
    mat.use_nodes = True
    no_emission_sampling(mat)
    nt = mat.node_tree
    nt.nodes.clear()
    b = SB(nt)
    geo, ps, uv = b.maps()
    ground = b.img(ground_img, uv).outputs["Color"]
    halo = b.img(halo_img, uv).outputs["Color"]
    drift = b.value("S01_Drift")
    dens = b.value("S01_MistDensity")
    mglow = b.value("S01_MistGlow")   # v047: mist cores dim 145-154 so 150 -> 156 hands over to the sea without a drop
    # wisps: long streaks (fog lies in layers, drawn out along the valley), slowly evolving
    w1 = b.noise(ps, 1800.0, 450.0, drift.outputs[0], detail=3, rough=0.5, zoff=13.0 * i)   # critic fix 3: smooth from 5-10 km (was 650x210, detail 7)
    wisp = b.smap(w1, 0.30, 0.62, 0.30, 1.0)   # a continuous veil between the denser bands
    w2 = b.noise(ps, 2600.0, 1800.0, drift.outputs[0], detail=2, zoff=50.0 + 5 * i)
    patch = b.smap(w2, 0.32, 0.62, 0.25, 1.0)
    # only where the ground is below this layer: lowest ground first, soft contact
    above = b.m("SUBTRACT", ps.outputs[2], ground)
    contact = b.smap(above, 0.0, 60.0 + 40.0 * i, 0.0, 1.0)   # critic fix 3: thins over the higher terraces
    alpha = b.m("MULTIPLY", b.m("MULTIPLY", b.m("MULTIPLY", wisp, patch), contact), b.m("MULTIPLY", dens.outputs[0], amax))
    # lit from below by the lights: halo in their colours, a breath of night blue elsewhere
    hv = b.vscale(halo, b.m("MULTIPLY", b.m("MULTIPLY", b.m("ADD", 0.5, b.m("MULTIPLY", wisp, 0.5)), HALO_GAIN), mglow.outputs[0]))
    key_value(mglow, [(114, 1.0), (145, 1.0), (154, 0.55)])
    em = b.N.new("ShaderNodeEmission")
    base = b.N.new("ShaderNodeCombineColor")
    base.inputs[0].default_value, base.inputs[1].default_value, base.inputs[2].default_value = 0.0045, 0.0055, 0.0080   # critic fix 3: gaps dim grey-blue, not black stains
    b.L.new(b.vadd(hv, base.outputs[0]), em.inputs["Color"])
    trn = b.N.new("ShaderNodeBsdfTransparent")
    mix = b.N.new("ShaderNodeMixShader")
    b.L.new(alpha, mix.inputs[0])
    b.L.new(trn.outputs[0], mix.inputs[1])
    b.L.new(em.outputs[0], mix.inputs[2])
    mo = b.N.new("ShaderNodeOutputMaterial")
    b.L.new(mix.outputs[0], mo.inputs["Surface"])
    mm.materials.append(mat)

    key_value(drift, [(100, 0.0), (198, 1.6)], linear=True)
    # gone a little before the sea closes (v044: bright flecks of mist peeking through at 156)
    key_value(dens, [(114, 0.0), (122, 0.5), (132, 1.0), (150, 1.0), (157, 0.0)])
    # layer rises with the cold pool: from the lowest ground to well over the city floor
    for f, z in ((114, F5 - 10), (126, F25), (138, F50 + 40), (150, F75 + 110), (160, F75 + 200)):
        ob.location.z = z + off
        ob.keyframe_insert("location", index=2, frame=f)
    ob.hide_render = True
    ob.keyframe_insert("hide_render", frame=113)
    ob.keyframe_insert("hide_render", frame=165)
    ob.hide_render = False
    ob.keyframe_insert("hide_render", frame=114)
    ob.hide_render = True
print(f"[v042] mist layers at +{MIST_OFF} m, max opacity {MIST_MAX}")

bpy.ops.wm.save_as_mainfile(filepath=out_path, copy=False)
print("[v042] saved", out_path)
