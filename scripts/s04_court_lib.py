# Shared helpers for the s04 courtyard build (materials, box mesh builder, walls, imports).
import bpy, bmesh, os, math, random, glob
from mathutils import Vector, Matrix, Euler

ROOT = "E:/Projects/tihar"
PH = ROOT + "/blender/assets/polyhaven"
ENV = ROOT + "/blender/assets/s04_env"


# ---------------------------------------------------------------- collections
def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link_only(obj, c):
    for uc in list(obj.users_collection):
        uc.objects.unlink(obj)
    c.objects.link(obj)


# ---------------------------------------------------------------- materials
def ph_file(tid, kind):
    pats = {
        "diff": ["%s_diff_*.jpg", "%s_Diffuse_*.jpg", "%s_diff_*.png"],
        "nor": ["%s_nor_gl_*.jpg", "%s_nor_gl_*.png"],
        "rough": ["%s_rough_*.jpg", "%s_Rough_*.jpg", "%s_rough_*.png"],
        "alpha": ["%s_alpha_*.png"],
    }[kind]
    for p in pats:
        hits = sorted(glob.glob(os.path.join(PH, p % tid)), reverse=True)  # prefer 4k over 2k
        if hits:
            return hits[0]
    return None


def img(path, color=True):
    im = bpy.data.images.load(path, check_existing=True)
    if not color:
        im.colorspace_settings.name = "Non-Color"
    return im


def new_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m


def bsdf_of(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def mix_rgb(nt, blend, a, b, fac=1.0):
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"; mx.blend_type = blend
    if isinstance(fac, float):
        mx.inputs[0].default_value = fac
    else:
        nt.links.new(fac, mx.inputs[0])
    for sock, val in ((mx.inputs[6], a), (mx.inputs[7], b)):
        if isinstance(val, tuple):
            sock.default_value = (*val[:3], 1)
        else:
            nt.links.new(val, sock)
    return mx.outputs[2]


def mat_pbr(name, tid, size_m, tint=None, rough_add=0.0, rough_mul=1.0, bump=1.0, coords="Object",
            blend=0.25, var_attr=None, var_amt=0.0, value=1.0, sat=1.0, hue=0.5, grime=0.0, rot=(0, 0, 0)):
    """Image-based PBR material. coords 'Object' -> box projection (vertices are in metres),
    'UV' -> flat UV. var_attr: per-face float attribute (0..1) that shifts brightness by +-var_amt."""
    m = new_mat(name)
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = bsdf_of(m)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / size_m,) * 3
    mp.inputs["Rotation"].default_value = rot
    L.new(tc.outputs["UV" if coords == "UV" else "Object"], mp.inputs["Vector"])

    def tex(path, color):
        t = N.new("ShaderNodeTexImage"); t.image = img(path, color)
        t.projection = "FLAT" if coords == "UV" else "BOX"; t.projection_blend = blend
        L.new(mp.outputs[0], t.inputs[0])
        return t

    col = tex(ph_file(tid, "diff"), True).outputs[0]
    if value != 1.0 or sat != 1.0 or hue != 0.5:
        hsv = N.new("ShaderNodeHueSaturation")
        hsv.inputs["Hue"].default_value = hue; hsv.inputs["Saturation"].default_value = sat
        hsv.inputs["Value"].default_value = value
        L.new(col, hsv.inputs["Color"]); col = hsv.outputs[0]
    if tint:
        col = mix_rgb(nt, "MULTIPLY", col, tint)
    if var_attr:
        at = N.new("ShaderNodeAttribute"); at.attribute_type = "GEOMETRY"; at.attribute_name = var_attr
        mr = N.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 1.0 - var_amt; mr.inputs["To Max"].default_value = 1.0 + var_amt
        L.new(at.outputs["Fac"], mr.inputs["Value"])
        cmb = N.new("ShaderNodeCombineColor")
        for i in range(3):
            L.new(mr.outputs[0], cmb.inputs[i])
        col = mix_rgb(nt, "MULTIPLY", col, cmb.outputs[0])
    if grime > 0:
        # large-scale dirt: darken with a world-space noise
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 6
        L.new(tc.outputs["Object"], nz.inputs["Vector"])
        cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.75
        cr.color_ramp.elements[0].color = (1 - grime, 1 - grime, 1 - grime * 1.1, 1)
        L.new(nz.outputs["Fac"], cr.inputs[0])
        col = mix_rgb(nt, "MULTIPLY", col, cr.outputs[0])
    L.new(col, b.inputs["Base Color"])
    rp = ph_file(tid, "rough")
    if rp:
        r = tex(rp, False)
        ma = N.new("ShaderNodeMath"); ma.operation = "MULTIPLY_ADD"; ma.use_clamp = True
        ma.inputs[1].default_value = rough_mul; ma.inputs[2].default_value = rough_add
        L.new(r.outputs[0], ma.inputs[0]); L.new(ma.outputs[0], b.inputs["Roughness"])
    npth = ph_file(tid, "nor")
    if npth and bump > 0:
        n = tex(npth, False)
        nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = bump
        L.new(n.outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], b.inputs["Normal"])
    return m


def mat_flat(name, rgb, rough=0.6, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0):
    m = new_mat(name)
    b = bsdf_of(m)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


# ---------------------------------------------------------------- mesh builder
class MB:
    """Accumulates boxes (in world coordinates) into one mesh object."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []
        self.fattr = {}  # name -> list of (face, value)

    def mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def box_m(self, size, matrix, mat, attrs=None):
        g = bmesh.ops.create_cube(self.bm, size=1.0)
        vs = g["verts"]
        bmesh.ops.scale(self.bm, vec=Vector(size), verts=vs)
        bmesh.ops.transform(self.bm, matrix=matrix, verts=vs)
        faces = {f for v in vs for f in v.link_faces}
        idx = self.mi(mat)
        for f in faces:
            f.material_index = idx
        if attrs:
            for k, v in attrs.items():
                self.fattr.setdefault(k, []).extend((f, v) for f in faces)
        return faces

    def box(self, lo, hi, mat, attrs=None):
        lo, hi = Vector(lo), Vector(hi)
        return self.box_m(hi - lo, Matrix.Translation((lo + hi) / 2), mat, attrs)

    def obj(self, name, c, bevel=0.0, seg=1, smooth=False):
        me = bpy.data.meshes.new(name)
        # write float face attributes before to_mesh
        layers = {}
        for k in self.fattr:
            layers[k] = self.bm.faces.layers.float.new(k)
        for k, lst in self.fattr.items():
            for f, v in lst:
                if f.is_valid:
                    f[layers[k]] = v
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        c.objects.link(o)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        if bevel > 0:
            md = o.modifiers.new("Bevel", "BEVEL")
            md.width = bevel; md.segments = seg; md.limit_method = "ANGLE"
            md.angle_limit = math.radians(40)
        return o


def wall(mb, axis, a0, a1, t0, t1, z0, z1, openings, mat):
    """Box wall along `axis` ('x' or 'y') from a0..a1, thickness t0..t1, height z0..z1,
    with rectangular openings [(a_lo, a_hi, z_lo, z_hi), ...]."""
    cuts = sorted({a0, a1} | {o[0] for o in openings} | {o[1] for o in openings})
    cuts = [c for c in cuts if a0 <= c <= a1]
    for xa, xb in zip(cuts, cuts[1:]):
        if xb - xa < 1e-4:
            continue
        mid = (xa + xb) / 2
        cover = sorted((o[2], o[3]) for o in openings if o[0] < mid < o[1])
        z = z0
        spans = []
        for za, zb in cover:
            if za > z + 1e-4:
                spans.append((z, za))
            z = max(z, zb)
        if z < z1 - 1e-4:
            spans.append((z, z1))
        for za, zb in spans:
            if axis == "x":
                mb.box((xa, t0, za), (xb, t1, zb), mat)
            else:
                mb.box((t0, xa, za), (t1, xb, zb), mat)


def interior_shell(name, lo, hi, mat, c):
    """Inward-facing box (dark room seen through openings)."""
    mb = MB()
    mb.box(lo, hi, mat)
    bmesh.ops.reverse_faces(mb.bm, faces=list(mb.bm.faces))
    return mb.obj(name, c)


# ---------------------------------------------------------------- imports
def import_obj(path, up="Z", forward="Y"):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, up_axis=up, forward_axis=forward)
    return [o for o in bpy.data.objects if o not in before]


def import_gltf(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def join(objs, name):
    """Join mesh objects (transforms applied) into one; removes non-mesh leftovers."""
    meshes = [o for o in objs if o.type == "MESH"]
    bpy.context.view_layer.update()
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in objs:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    with bpy.context.temp_override(active_object=meshes[0], selected_editable_objects=meshes,
                                   selected_objects=meshes):
        if len(meshes) > 1:
            bpy.ops.object.join()
    o = meshes[0]
    o.name = name; o.data.name = name
    # apply transform
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    return o


def origin_bottom(o, mode="bottom"):
    """Move mesh so its bbox bottom-centre (or given point) sits at the object origin."""
    vs = [v.co for v in o.data.vertices]
    lo = Vector(map(min, *vs)); hi = Vector(map(max, *vs))
    p = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    o.data.transform(Matrix.Translation(-p))
    return hi - lo


def place(src, name, loc, rotz=0.0, scale=1.0, c=None):
    o = src.copy()  # linked duplicate (shares mesh -> instanced in Cycles)
    o.name = name
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rotz)); o.scale = (scale,) * 3
    (c or src.users_collection[0]).objects.link(o)
    return o
