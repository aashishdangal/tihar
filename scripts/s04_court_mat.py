# v008+: procedural old Newari (dachi appa) brick, weathering, dust/moss helpers for the s04 courtyard.
import bpy
from s04_court_lib import new_mat, bsdf_of, mix_rgb, img, ph_file


def _m(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _smooth(nt, v, lo, hi, to_lo=0.0, to_hi=1.0):
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = lo; mr.inputs["From Max"].default_value = hi
    mr.inputs["To Min"].default_value = to_lo; mr.inputs["To Max"].default_value = to_hi
    nt.links.new(v, mr.inputs["Value"])
    return mr.outputs[0]


def _noise(nt, vec, scale, detail=4.0, rough=0.55):
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def _vec(nt, x, y, z):
    c = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, v in enumerate((x, y, z)):
        if isinstance(v, (int, float)):
            c.inputs[i].default_value = v
        else:
            nt.links.new(v, c.inputs[i])
    return c.outputs[0]


def _grey(nt, v):
    return _vec(nt, v, v, v)


def weather(nt, col, pos, z, strength=1.0, ground=True, streaks=True, moss=True, eave_z=None, ground_z=0.0):
    """Darker near the ground, vertical rain streaks, soot under the eaves, moss at the base."""
    X = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(pos, X.inputs[0])
    zr = _m(nt, "SUBTRACT", z, ground_z)
    if ground:
        g = _smooth(nt, zr, 1.3, 0.0)
        g = _m(nt, "MULTIPLY", g, _smooth(nt, _noise(nt, pos, 2.5, 6), 0.3, 0.7, 0.55, 1.0))
        dark = _smooth(nt, g, 0, 1, 1.0, 1.0 - 0.45 * strength)
        col = mix_rgb(nt, "MULTIPLY", col, _grey(nt, dark), 1.0)
    if streaks:
        sv = _vec(nt, _m(nt, "MULTIPLY", X.outputs[0], 7.0), _m(nt, "MULTIPLY", X.outputs[1], 7.0),
                  _m(nt, "MULTIPLY", X.outputs[2], 0.35))
        s = _smooth(nt, _noise(nt, sv, 3.0, 3), 0.52, 0.72, 1.0, 1.0 - 0.32 * strength)
        col = mix_rgb(nt, "MULTIPLY", col, _grey(nt, s), 1.0)
    if eave_z is not None:
        e = _smooth(nt, z, eave_z - 1.6, eave_z, 1.0, 1.0 - 0.35 * strength)
        col = mix_rgb(nt, "MULTIPLY", col, _grey(nt, e), 1.0)
    if moss:
        mz = _m(nt, "MULTIPLY", _smooth(nt, zr, 0.45, 0.02), _smooth(nt, _noise(nt, pos, 6.0, 8), 0.45, 0.65))
        col = mix_rgb(nt, "MIX", col, (0.045, 0.07, 0.02), _m(nt, "MULTIPLY", mz, 0.85 * strength))
    return col


PALETTES = [
    [(0.0, (0.07, 0.035, 0.03)), (0.08, (0.13, 0.045, 0.03)), (0.3, (0.21, 0.075, 0.045)), (0.5, (0.28, 0.11, 0.06)),
     (0.7, (0.19, 0.08, 0.055)), (0.85, (0.38, 0.17, 0.09)), (0.93, (0.30, 0.15, 0.10)), (1.0, (0.11, 0.06, 0.055))],
    [(0.0, (0.17, 0.06, 0.035)), (0.3, (0.26, 0.10, 0.055)), (0.55, (0.32, 0.13, 0.07)),
     (0.8, (0.22, 0.09, 0.06)), (0.9, (0.10, 0.05, 0.04)), (1.0, (0.40, 0.19, 0.10))],
]


def mat_newari_brick(name, palette=0, eave_z=7.6, limewash=0.35, brick=(0.235, 0.062, 0.0055), bright=1.0):
    """Dachi-appa brick wall in world coordinates (walls facing +-X or +-Y): per-brick colour and
    roughness, thin dark recessed mortar of uneven width, photo grain, lime-wash, weathering."""
    m = new_mat(name)
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = bsdf_of(m)
    geo = N.new("ShaderNodeNewGeometry")
    pos = geo.outputs["Position"]
    P = N.new("ShaderNodeSeparateXYZ"); Lk.new(pos, P.inputs[0])
    Nn = N.new("ShaderNodeSeparateXYZ"); Lk.new(geo.outputs["Normal"], Nn.inputs[0])
    sel = _m(nt, "GREATER_THAN", _m(nt, "ABSOLUTE", Nn.outputs[0]), _m(nt, "ABSOLUTE", Nn.outputs[1]))
    # hand-laid wobble: low-frequency warp of the coursing (a few mm)
    wv = N.new("ShaderNodeTexNoise"); wv.inputs["Scale"].default_value = 1.3; wv.inputs["Detail"].default_value = 2
    Lk.new(pos, wv.inputs["Vector"])
    W = N.new("ShaderNodeSeparateColor"); Lk.new(wv.outputs["Color"], W.inputs[0])
    x = _m(nt, "ADD", P.outputs[0], _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", W.outputs[0], 0.5), 0.012))
    y = _m(nt, "ADD", P.outputs[1], _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", W.outputs[1], 0.5), 0.012))
    z = _m(nt, "ADD", P.outputs[2], _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", W.outputs[2], 0.5), 0.008))
    u = _m(nt, "ADD", x, _m(nt, "MULTIPLY", sel, _m(nt, "SUBTRACT", y, x)))
    bw, rh, mo = brick
    row = _m(nt, "FLOOR", _m(nt, "DIVIDE", z, rh))
    odd = _m(nt, "MULTIPLY", _m(nt, "FRACT", _m(nt, "MULTIPLY", row, 0.5)), 2.0)
    u2 = _m(nt, "ADD", u, _m(nt, "MULTIPLY", odd, bw * 0.5))
    col_i = _m(nt, "FLOOR", _m(nt, "DIVIDE", u2, bw))
    fu = _m(nt, "MULTIPLY", _m(nt, "FRACT", _m(nt, "DIVIDE", u2, bw)), bw)
    fz = _m(nt, "MULTIPLY", _m(nt, "FRACT", _m(nt, "DIVIDE", z, rh)), rh)
    d = _m(nt, "MINIMUM", _m(nt, "MINIMUM", fu, _m(nt, "SUBTRACT", bw, fu)),
           _m(nt, "MINIMUM", fz, _m(nt, "SUBTRACT", rh, fz)))
    jit = _smooth(nt, _noise(nt, pos, 14.0, 2), 0.3, 0.7, mo * 0.35, mo * 0.75)
    mortar = _smooth(nt, _m(nt, "SUBTRACT", d, jit), -0.0006, 0.0012, 1.0, 0.0)
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
    Lk.new(_vec(nt, col_i, row, _m(nt, "MULTIPLY", sel, 7.3)), wn.inputs["Vector"])
    rnd = wn.outputs["Value"]
    cr = N.new("ShaderNodeValToRGB"); Lk.new(rnd, cr.inputs[0]); cr.color_ramp.interpolation = "CONSTANT"
    pal = PALETTES[palette]
    el = cr.color_ramp.elements
    el[0].position, el[0].color = pal[0][0], (*[c * bright for c in pal[0][1]], 1)
    el[1].position, el[1].color = pal[-1][0], (*[c * bright for c in pal[-1][1]], 1)
    for p, c in pal[1:-1]:
        e = el.new(p); e.color = (*[v * bright for v in c], 1)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / 0.8,) * 3
    Lk.new(tc.outputs["Object"], mp.inputs[0])
    gt = N.new("ShaderNodeTexImage"); gt.image = img(ph_file("rock_boulder_dry", "diff"))
    gt.projection = "BOX"; gt.projection_blend = 0.3
    Lk.new(mp.outputs[0], gt.inputs[0])
    bwn = N.new("ShaderNodeRGBToBW"); Lk.new(gt.outputs[0], bwn.inputs[0])
    grain = _smooth(nt, bwn.outputs[0], 0.15, 0.85, 0.6, 1.3)
    fine = _smooth(nt, _noise(nt, pos, 60.0, 6), 0.3, 0.7, 0.85, 1.1)
    big = _smooth(nt, _noise(nt, pos, 0.35, 3), 0.3, 0.7, 0.8, 1.12)
    gmul = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", grain, fine), big)
    # worn, darker brick arrises and burnt/sooty spots inside bricks
    edge = _smooth(nt, d, 0.004, 0.016, 0.72, 1.0)
    edge = _m(nt, "ADD", edge, _m(nt, "MULTIPLY", _noise(nt, pos, 25.0, 3), 0.15), clamp=True)
    spots = _smooth(nt, _noise(nt, pos, 18.0, 5), 0.58, 0.72, 1.0, 0.55)
    gmul = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", gmul, edge), spots)
    bcol = mix_rgb(nt, "MULTIPLY", cr.outputs[0], _grey(nt, gmul), 1.0)
    mcol = mix_rgb(nt, "MULTIPLY", (0.055, 0.047, 0.04), _grey(nt, fine), 1.0)
    col = mix_rgb(nt, "MIX", bcol, mcol, mortar)
    if limewash > 0:
        lw = _m(nt, "MULTIPLY", _smooth(nt, _noise(nt, pos, 0.9, 5), 0.60, 0.66),
                _smooth(nt, _noise(nt, pos, 9.0, 4), 0.35, 0.6))
        col = mix_rgb(nt, "MIX", col, (0.42, 0.38, 0.32), _m(nt, "MULTIPLY", lw, limewash))
    col = weather(nt, col, pos, z, 1.0, eave_z=eave_z)
    Lk.new(col, b.inputs["Base Color"])
    rough = _m(nt, "ADD", _m(nt, "MULTIPLY", rnd, 0.14), 0.78)
    rough = _m(nt, "ADD", rough, _m(nt, "MULTIPLY", mortar, 0.12), clamp=True)
    Lk.new(rough, b.inputs["Roughness"])
    tilt = _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", rnd, 0.5), _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", fz, rh / 2), 0.15))
    h = _m(nt, "ADD", _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", 1.0, mortar), 0.006),
           _m(nt, "MULTIPLY", bwn.outputs[0], 0.0018))
    h = _m(nt, "SUBTRACT", h, _m(nt, "MULTIPLY", _smooth(nt, d, 0.0, 0.012, 1.0, 0.0), 0.0015))
    h = _m(nt, "ADD", h, tilt)
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 1.0
    Lk.new(h, bp.inputs["Height"]); Lk.new(bp.outputs[0], b.inputs["Normal"])
    return m


def add_dust_moss(m, dust=0.35, moss=0.0, lichen=0.0, grime=0.25, weathering=False):
    """Insert grime, dust on up-facing faces, moss and lichen before the Base Color input."""
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = bsdf_of(m)
    col = b.inputs["Base Color"].links[0].from_socket
    geo = N.new("ShaderNodeNewGeometry")
    pos = geo.outputs["Position"]
    Nn = N.new("ShaderNodeSeparateXYZ"); Lk.new(geo.outputs["Normal"], Nn.inputs[0])
    P = N.new("ShaderNodeSeparateXYZ"); Lk.new(pos, P.inputs[0])
    up = _smooth(nt, Nn.outputs[2], 0.3, 0.9)
    if grime > 0:
        g = _smooth(nt, _noise(nt, pos, 1.2, 6), 0.35, 0.75, 1.0, 1.0 - grime)
        col = mix_rgb(nt, "MULTIPLY", col, _grey(nt, g), 1.0)
    if weathering:
        col = weather(nt, col, pos, P.outputs[2], 0.7, streaks=False)
    if dust > 0:
        dm = _m(nt, "MULTIPLY", up, _smooth(nt, _noise(nt, pos, 8.0, 6), 0.35, 0.7))
        col = mix_rgb(nt, "MIX", col, (0.30, 0.27, 0.23), _m(nt, "MULTIPLY", dm, dust))
    if moss > 0:
        mm = _m(nt, "MULTIPLY", _smooth(nt, Nn.outputs[2], 0.0, 0.7), _smooth(nt, _noise(nt, pos, 3.0, 8), 0.5, 0.68))
        col = mix_rgb(nt, "MIX", col, (0.05, 0.075, 0.025), _m(nt, "MULTIPLY", mm, moss))
    if lichen > 0:
        v = N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 9.0; Lk.new(pos, v.inputs["Vector"])
        lm = _m(nt, "MULTIPLY", _smooth(nt, v.outputs["Distance"], 0.12, 0.05),
                _smooth(nt, _noise(nt, pos, 1.5, 3), 0.45, 0.6))
        col = mix_rgb(nt, "MIX", col, (0.38, 0.37, 0.30), _m(nt, "MULTIPLY", lm, lichen))
    Lk.new(col, b.inputs["Base Color"])
    return m
