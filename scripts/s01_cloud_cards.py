"""s01 v034 (v033 + rougher edges, brighter city glow): replace the black blob blockout with two procedural cloud cards (no volume).

Each card is a flat plane facing the hold-frame camera, 4.0 km (near) and 4.8 km (far) out, so its
lower edge stays well above the hills (checked with ray casts, printed below). Shader is
Transparent + Emission only, no lighting:
  - soft, noise-broken leading (right) edge and billowing top edge; bottom fades out
  - edges thin out (city lights show through dimmed), interior opaque
  - colour: dark blue-grey top, warm city-glow underside with a faint multicolour tint
  - 4D noise W driven by the frame, so the cloud slowly billows instead of sliding
Cards are visible to camera rays only (they don't shadow or light the city).
Both cards slide in from the left over the sweep (114 -> 162), in the camera's right direction.
The blockout (S01_DarkCloud_Blockout, made in this session) is removed; the old Lazy Cloud dive
slab is hidden from render (kept in the file).

Run: blender.exe -b s01_hero_v032.blend --python scripts/s01_cloud_cards.py -- <out.blend>
"""
import math, sys
import bpy
from mathutils import Matrix, Vector

out = sys.argv[sys.argv.index("--") + 1]
HOLD0, SWEEP0, SWEEP1 = 66, 114, 162

sc = bpy.context.scene
cam = bpy.data.objects["CAM_S01"]

for name in ("S01_DarkCloud_Blockout",):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob)
lc = bpy.data.objects.get("S01_DiveCloud_LC")
if lc:
    lc.hide_render = True
    lc.hide_viewport = True

sc.frame_set(HOLD0)
M = cam.matrix_world.copy()
R = M.to_3x3()
right = R @ Vector((1, 0, 0))
fx = cam.data.angle_x
fy = 2 * math.atan(math.tan(fx / 2) * sc.render.resolution_y / sc.render.resolution_x)
TX, TY = math.tan(fx / 2), math.tan(fy / 2)

# card extents in units of the frame half-width w / half-height h at the card's distance
X0, X1, Y0, Y1 = -2.4, 1.45, -1.6, 1.35


def u_of(x):
    return (x - X0) / (X1 - X0)


def v_of(y):
    return (y - Y0) / (Y1 - Y0)


CARDS = [
    # name, distance, leading-edge zone (x), top zone (y), noise seed, glow peak
    dict(name="S01_CloudCard_Far", D=4800, lead=(1.00, 1.35), top=(1.02, 1.30), seed=3.7, glow=0.05),
    dict(name="S01_CloudCard_Near", D=4000, lead=(1.10, 1.45), top=(0.30, 0.75), seed=11.2, glow=0.06),
]


def node(nt, t, loc, **props):
    n = nt.nodes.new(t)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def math_node(nt, op, a, b, loc, clamp=False, c=None):
    n = node(nt, "ShaderNodeMath", loc, operation=op, use_clamp=clamp)
    if c is not None:
        n.inputs[2].default_value = c
    for i, x in enumerate((a, b)):
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def map_range(nt, val, fmin, fmax, tmin, tmax, loc):
    n = node(nt, "ShaderNodeMapRange", loc, interpolation_type="SMOOTHSTEP", clamp=True)
    nt.links.new(val, n.inputs[0])
    for i, x in zip((1, 2, 3, 4), (fmin, fmax, tmin, tmax)):
        n.inputs[i].default_value = x
    return n.outputs[0]


def noise(nt, vec, scale, detail, rough, seed, loc):
    n = node(nt, "ShaderNodeTexNoise", loc, noise_dimensions="4D")
    nt.links.new(vec, n.inputs["Vector"])
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    fc = n.inputs["W"].driver_add("default_value")
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = f"frame/300+{seed}"  # simple expression: no Python auto-run needed
    return n.outputs["Fac"]


def make_material(c):
    m = bpy.data.materials.new("M_" + c["name"])
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, 200))
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]
    # object coords are metres on the card: big billows ~700 m, wisps ~170 m
    n1 = noise(nt, tc.outputs["Object"], 0.0014, 8, 0.6, c["seed"], (-1200, -100))
    n2 = noise(nt, tc.outputs["Object"], 0.006, 5, 0.65, c["seed"] + 5, (-1200, -400))

    # leading edge (right), pushed in and out by the billows
    wob = math_node(nt, "ADD", math_node(nt, "MULTIPLY", math_node(nt, "SUBTRACT", n1, 0.5, (-1000, -100)), 1.0, (-900, -100)),
                    math_node(nt, "MULTIPLY", math_node(nt, "SUBTRACT", n2, 0.5, (-1000, -180)), 0.35, (-900, -180)), (-850, -140))
    ue = math_node(nt, "ADD", u, math_node(nt, "MULTIPLY", wob, 0.30, (-820, 0)), (-800, 100))
    lead = map_range(nt, ue, u_of(c["lead"][0]), u_of(c["lead"][1]), 1, 0, (-600, 200))
    # top edge, more lumpy
    ve = math_node(nt, "ADD", v, math_node(nt, "MULTIPLY", wob, 0.32, (-820, -250)), (-800, -50))
    top = map_range(nt, ve, v_of(c["top"][0]), v_of(c["top"][1]), 1, 0, (-600, 0))
    bottom = map_range(nt, v, 0.0, 0.06, 0, 1, (-600, -200))
    mask = math_node(nt, "MULTIPLY", math_node(nt, "MULTIPLY", lead, top, (-400, 100)), bottom, (-250, 100))
    # opacity: wisps break the edges up, the inside stays solid
    dens = math_node(nt, "MULTIPLY", mask, math_node(nt, "MULTIPLY_ADD", n2, 0.8, (-400, -350), c=0.6), (-100, 0))
    alpha = map_range(nt, dens, 0.15, 0.75, 0, 1, (50, 0))

    # colour: warm city glow on the lower part, dark blue-grey above
    glow = map_range(nt, v, v_of(-1.2), v_of(0.9), 1, 0, (-400, -600))
    glow = math_node(nt, "POWER", glow, 1.5, (-250, -600))
    glow = math_node(nt, "MULTIPLY", glow, math_node(nt, "MULTIPLY_ADD", n1, 1.2, (-250, -800), c=0.4), (-100, -600), clamp=True)
    tint = node(nt, "ShaderNodeMix", (50, -800), data_type="RGBA")
    tint.inputs["A"].default_value = (1.0, 0.50, 0.22, 1)        # warm (diyos, sodium, warm LED)
    tint.inputs["B"].default_value = (0.70, 0.35, 0.95, 1)       # multicolour LED hint
    nt.links.new(math_node(nt, "MULTIPLY", n2, 0.35, (-100, -900)), tint.inputs["Factor"])
    warm = node(nt, "ShaderNodeMix", (200, -700), data_type="RGBA", blend_type="MULTIPLY")
    warm.inputs["Factor"].default_value = 1.0
    nt.links.new(tint.outputs["Result"], warm.inputs["A"])
    warm.inputs["B"].default_value = (c["glow"],) * 3 + (1,)
    col = node(nt, "ShaderNodeMix", (350, -500), data_type="RGBA")
    col.inputs["A"].default_value = (0.35 * 0.004, 0.42 * 0.004, 0.60 * 0.004, 1)
    nt.links.new(glow, col.inputs["Factor"])
    nt.links.new(warm.outputs["Result"], col.inputs["B"])

    # billow shading: brighter and darker lumps inside the cloud
    em = node(nt, "ShaderNodeEmission", (500, -300))
    shade = math_node(nt, "MULTIPLY_ADD", n1, 1.4, (350, -700), c=0.3)
    nt.links.new(math_node(nt, "MULTIPLY", shade, math_node(nt, "MULTIPLY_ADD", n2, 0.8, (350, -850), c=0.6), (450, -750)), em.inputs["Strength"])
    nt.links.new(col.outputs["Result"], em.inputs["Color"])
    tr = node(nt, "ShaderNodeBsdfTransparent", (500, -100))
    mix = node(nt, "ShaderNodeMixShader", (700, 0))
    nt.links.new(alpha, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    outn = node(nt, "ShaderNodeOutputMaterial", (900, 0))
    nt.links.new(mix.outputs[0], outn.inputs["Surface"])
    return m


dg = bpy.context.evaluated_depsgraph_get()
for c in CARDS:
    D = c["D"]
    w, h = D * TX, D * TY
    verts = [(X0 * w, Y0 * h, 0), (X1 * w, Y0 * h, 0), (X1 * w, Y1 * h, 0), (X0 * w, Y1 * h, 0)]
    me = bpy.data.meshes.new(c["name"])
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(c["name"], me)
    sc.collection.objects.link(ob)
    ob.matrix_world = M @ Matrix.Translation((0, 0, -D))
    me.materials.append(make_material(c))
    for attr in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
        setattr(ob, attr, False)

    # sweep: start with the leading edge off the left of the frame, end in place
    home = ob.location.copy()
    shift = (c["lead"][1] + 1.0 + 0.15) * w
    for f, loc in ((SWEEP0, home - right * shift), (SWEEP1, home)):
        ob.location = loc
        ob.keyframe_insert("location", frame=f)

    # clearance: cast down from points along the card's bottom edge, at both ends of the sweep
    clear = []
    for loc in (home - right * shift, home):
        base = Matrix.Translation(loc) @ M.to_3x3().to_4x4()
        for i in range(25):
            x = X0 + (X1 - X0) * i / 24
            p = base @ Vector((x * w, Y0 * h, 0))
            hit, hp, *_ = sc.ray_cast(dg, p, Vector((0, 0, -1)))
            if hit:
                clear.append(p.z - hp.z)
    ob.location = home
    print(f"[cards] {c['name']}: D={D} w={w:.0f} h={h:.0f} min clearance over terrain "
          f"{min(clear):.0f} m ({len(clear)} hits)" if clear else f"[cards] {c['name']}: no terrain hit below")

sc.cycles.transparent_max_bounces = max(sc.cycles.transparent_max_bounces, 8)
bpy.ops.wm.save_as_mainfile(filepath=out, copy=False)
print("[cards] saved", out)
