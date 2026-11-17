# Red tika as STAINED FUR on Nubis' forehead.
# Adds node group "S04_TikaStain" (mask from the S04_Tika empty's local space, irregular edge, per-strand
# variation) and inserts it in front of the fur colour (NubisFurMat -> Principled Hair BSDF Color) and the
# base colour of the body material under the forehead, so gaps between hairs read red too.
# Needs an object "S04_Tika" (empty: X across, Y up the forehead, Z out of the skin; radii in its
# "stain_radii" property). Scale the empty 0 -> 1 to animate the stain appearing.
# Run inside a file that has Nubis + S04_Tika:  exec(open(r"E:/Projects/tihar/scripts/s04_hand_tika_stain.py").read())
import bpy
from mathutils import Vector

TIKA = bpy.data.objects["S04_Tika"]
RX, RY, RZ = TIKA.get("stain_radii", (0.012, 0.017, 0.008))

def lin(hexs):
    h = hexs.lstrip("#"); out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)

def build_group():
    ng = bpy.data.node_groups.get("S04_TikaStain") or bpy.data.node_groups.new("S04_TikaStain", "ShaderNodeTree")
    ng.nodes.clear(); ng.interface.clear()
    ng.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    s = ng.interface.new_socket("Strength", in_out="INPUT", socket_type="NodeSocketFloat"); s.default_value = 1.0
    ng.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    ng.interface.new_socket("Mask", in_out="OUTPUT", socket_type="NodeSocketFloat")
    N = ng.nodes.new; L = ng.links.new
    gi = N("NodeGroupInput"); gi.location = (-1400, 0)
    go = N("NodeGroupOutput"); go.location = (900, 0)
    tc = N("ShaderNodeTexCoord"); tc.object = TIKA; tc.location = (-1400, 300)
    mp = N("ShaderNodeMapping"); mp.location = (-1200, 300)
    mp.inputs["Scale"].default_value = (1 / RX, 1 / RY, 1 / RZ)
    L(tc.outputs["Object"], mp.inputs["Vector"])
    # ragged edge: distort the ellipsoid with low + mid frequency noise (in stain space)
    nz = N("ShaderNodeTexNoise"); nz.location = (-1000, 500); nz.inputs["Scale"].default_value = 2.4
    nz.inputs["Detail"].default_value = 4; nz.noise_dimensions = "3D"
    L(mp.outputs[0], nz.inputs["Vector"])
    sub = N("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.location = (-800, 500)
    L(nz.outputs["Color"], sub.inputs[0]); sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    sc = N("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.location = (-650, 500); sc.inputs["Scale"].default_value = 0.85
    L(sub.outputs[0], sc.inputs[0])
    ad = N("ShaderNodeVectorMath"); ad.operation = "ADD"; ad.location = (-500, 300)
    L(mp.outputs[0], ad.inputs[0]); L(sc.outputs[0], ad.inputs[1])
    ln = N("ShaderNodeVectorMath"); ln.operation = "LENGTH"; ln.location = (-350, 300)
    L(ad.outputs[0], ln.inputs[0])
    mr = N("ShaderNodeMapRange"); mr.location = (-200, 300); mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs[1].default_value = 1.0; mr.inputs[2].default_value = 0.7; mr.inputs[3].default_value = 0.0; mr.inputs[4].default_value = 1.0
    L(ln.outputs["Value"], mr.inputs[0])
    # per-strand variation (hair): some strands carry less powder; meshes get Random = 0 -> 0.8
    hi = N("ShaderNodeHairInfo"); hi.location = (-500, -50)
    vr = N("ShaderNodeMapRange"); vr.location = (-300, -50)
    vr.inputs[3].default_value = 0.8; vr.inputs[4].default_value = 1.0
    L(hi.outputs["Random"], vr.inputs[0])
    m1 = N("ShaderNodeMath"); m1.operation = "MULTIPLY"; m1.location = (0, 200); m1.use_clamp = True
    L(mr.outputs[0], m1.inputs[0]); L(vr.outputs[0], m1.inputs[1])
    m2 = N("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.location = (150, 200); m2.use_clamp = True
    L(m1.outputs[0], m2.inputs[0]); L(gi.outputs["Strength"], m2.inputs[1])
    # sindoor colour, mottled: clumps of deeper red and brighter orange-red
    nz2 = N("ShaderNodeTexNoise"); nz2.location = (-500, -300); nz2.inputs["Scale"].default_value = 6.0
    L(mp.outputs[0], nz2.inputs["Vector"])
    cr = N("ShaderNodeValToRGB"); cr.location = (-250, -300)
    cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[0].color = lin("#5E0507")
    cr.color_ramp.elements[1].position = 0.75; cr.color_ramp.elements[1].color = lin("#9E0A0C")
    L(nz2.outputs["Fac"], cr.inputs[0])
    # the fur's own light/dark shows through a little (stain multiplies over the coat value)
    hsv = N("ShaderNodeSeparateColor"); hsv.mode = "HSV"; hsv.location = (-250, -550)
    L(gi.outputs["Color"], hsv.inputs[0])
    vv = N("ShaderNodeMapRange"); vv.location = (0, -550); vv.inputs[1].default_value = 0.0; vv.inputs[2].default_value = 0.6
    vv.inputs[3].default_value = 0.65; vv.inputs[4].default_value = 1.0
    L(hsv.outputs[2], vv.inputs[0])
    mulc = N("ShaderNodeMix"); mulc.data_type = "RGBA"; mulc.blend_type = "MULTIPLY"; mulc.location = (250, -300)
    mulc.inputs[0].default_value = 1.0
    L(cr.outputs[0], mulc.inputs[6])
    cv = N("ShaderNodeCombineColor"); cv.location = (150, -550)
    L(vv.outputs[0], cv.inputs[0]); L(vv.outputs[0], cv.inputs[1]); L(vv.outputs[0], cv.inputs[2])
    L(cv.outputs[0], mulc.inputs[7])
    mix = N("ShaderNodeMix"); mix.data_type = "RGBA"; mix.location = (550, 0)
    L(m2.outputs[0], mix.inputs[0]); L(gi.outputs["Color"], mix.inputs[6]); L(mulc.outputs[2], mix.inputs[7])
    L(mix.outputs[2], go.inputs["Color"]); L(m2.outputs[0], go.inputs["Mask"])
    return ng

def insert(mat, to_node, to_socket_name):
    nt = mat.node_tree
    if any(n.type == "GROUP" and n.node_tree and n.node_tree.name == "S04_TikaStain" for n in nt.nodes):
        print("[stain] already in", mat.name); return
    sock = to_node.inputs[to_socket_name]
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = NG; g.name = "S04_TikaStain"
    g.location = (to_node.location.x - 250, to_node.location.y - 250)
    if sock.is_linked:
        src = sock.links[0].from_socket
        nt.links.new(src, g.inputs["Color"])
    else:
        g.inputs["Color"].default_value = sock.default_value
    nt.links.new(g.outputs["Color"], sock)
    print("[stain] inserted in", mat.name, "->", to_node.name, to_socket_name)

NG = build_group()
fur_mat = bpy.data.materials.get("NubisFurMat")
hair = next(n for n in fur_mat.node_tree.nodes if n.type == "BSDF_HAIR_PRINCIPLED")
insert(fur_mat, hair, "Color")
# the body material under the stain centre
body = bpy.data.objects["Nubis Mesh"]
dg = bpy.context.evaluated_depsgraph_get()
from mathutils.bvhtree import BVHTree
ev = body.evaluated_get(dg); me = ev.to_mesh()
bvh = BVHTree.FromPolygons([body.matrix_world @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
loc, nrm, idx, dist = bvh.find_nearest(TIKA.matrix_world.translation)
mi = me.polygons[idx].material_index
skin = body.material_slots[mi].material
ev.to_mesh_clear()
bs = next(n for n in skin.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
insert(skin, bs, "Base Color")
print("[stain] fur:", fur_mat.name, "skin:", skin.name, "dist to skin %.4f" % dist)
