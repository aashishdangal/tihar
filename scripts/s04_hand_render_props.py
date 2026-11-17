# Test-render the S04 props from hand_props_vNNN.blend (never saves the .blend).
# blender -b blender/assets/s04_hand/hand_props_v001.blend --python scripts/s04_hand_render_props.py -- <mode> <out.png>
#   mode: mala (the worn loop alone, 3/4 front) | marigold (close-up of a few heads) | held (Held shape key)
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
mode, out = argv[0], os.path.abspath(argv[1])
sc = bpy.context.scene

def gpu(sc, spp):
    cp = bpy.context.preferences.addons["cycles"].preferences
    cp.compute_device_type = "HIP"; cp.refresh_devices()
    for d in cp.devices:
        d.use = d.type == "HIP" and "Radeon(TM) Graphics" not in d.name
    sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"
    sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.resolution_percentage = int(os.environ.get("PCT", 75))
    sc.view_settings.view_transform = "AgX"
    sc.render.film_transparent = False

def studio(sc, ground_z, ctr, size):
    sun_d = bpy.data.lights.new("T_Sun", "SUN"); sun_d.energy = 2.2; sun_d.angle = math.radians(3)
    sun = bpy.data.objects.new("T_Sun", sun_d); sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(45), 0, math.radians(-35))
    w = bpy.data.worlds.new("T_World"); w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.62, 0.66, 0.74, 1); bg.inputs[1].default_value = 0.7
    sc.world = w
    bpy.ops.mesh.primitive_plane_add(size=size * 20, location=(ctr.x, ctr.y, ground_z))
    g = bpy.context.object
    gm = bpy.data.materials.new("T_Ground"); gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[0].default_value = (0.28, 0.22, 0.17, 1)
    g.data.materials.append(gm)

def camera(sc, target, direction, dist, lens=50):
    cd = bpy.data.cameras.new("T_Cam"); cd.lens = lens
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 5.6
    cam = bpy.data.objects.new("T_Cam", cd); sc.collection.objects.link(cam)
    cam.location = target + Vector(direction).normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cd.dof.focus_distance = dist
    sc.camera = cam

gpu(sc, int(os.environ.get("SPP", 48)))
mala = bpy.data.objects["S04_Mala"]
for o in bpy.data.objects:
    if o.name.startswith(("S04_Tika", "S04_Hand", "TMP_")) and not (mode == "held" and o.name.startswith("S04_Hand")):
        o.hide_render = True

def spline_bounds(ob):
    bpy.context.view_layer.update()
    e = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    kb = ob.data.shape_keys.key_blocks if ob.data.shape_keys else None
    act = [k for k in kb if k.value > 0.5][-1] if kb else None
    pts = [ob.matrix_world @ Vector(d.co) for d in act.data] if act and act != kb[0] else           [ob.matrix_world @ Vector(p.co[:3]) for p in ob.data.splines[0].points]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))) - Vector((0.025,) * 3)
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))) + Vector((0.025,) * 3)
    return lo, hi, pts

if mode in ("mala", "held"):
    if mode == "held":
        # both hands in HandHoldMala, the mala in HeldTwoHands, each pinch on its hold point
        from mathutils import Matrix
        ns = {}
        src = open(os.path.join(os.path.dirname(__file__), "s04_hand_poses.py")).read()
        src = src.replace('if __name__ == "__main__" or True:\n    build_pose_actions()', "")
        exec(compile(src, "poses", "exec"), ns)
        mala.location = (0, 0, 0.9)
        mala.data.shape_keys.key_blocks["HeldTwoHands"].value = 1.0
        bpy.context.view_layer.update()
        kb = mala.data.shape_keys.key_blocks["HeldTwoHands"].data
        iR, iL = mala["hold_points_two_hands"]
        # right hand: fingers down and a little inward/forward, palm facing the other hand
        f0 = Vector((0, 0, 1)); n0 = ns["PALM_N"]
        f1 = Vector((-0.25, 0.25, -0.93)).normalized(); n1 = Vector((-0.9, 0.0, -0.25))
        n1 = (n1 - f1 * n1.dot(f1)).normalized()
        A = Matrix((f0, n0, f0.cross(n0))).transposed(); Bm = Matrix((f1, n1, f1.cross(n1))).transposed()
        Rr = Bm @ A.inverted()
        M = Matrix.Diagonal((-1, 1, 1)); S = Matrix.Diagonal((-1, 1, 1))
        for rig_name, idx, R3 in (("S04_Hand_Rig", iR, Rr), ("S04_HandL_Rig", iL, M @ Rr @ S)):
            arm = bpy.data.objects[rig_name]
            ns["apply_pose"]("HandHoldMala", arm=arm)
            scl = arm.scale.copy()
            arm.matrix_world = Matrix.Translation((0, 0, 0)) @ R3.to_4x4() @ Matrix.Diagonal((*scl, 1))
            bpy.context.view_layer.update()
            P = arm.pose.bones
            pinch = arm.matrix_world @ ((P["THUMB_UP_TOP_joint_022"].head + P["INDEX_MID_joint_04"].head) / 2)
            target = mala.matrix_world @ Vector(kb[idx].co)
            arm.location = arm.location + (target - pinch)
            bpy.context.view_layer.update()
            print("[props-render]", rig_name, "pinch->point", idx)
    lo, hi, pts = spline_bounds(mala)
    if mode == "held":
        hi.z = max(hi.z, mala.location.z + 0.25)
    ctr = (lo + hi) / 2; size = (hi - lo).length
    studio(sc, lo.z - 0.15, ctr, size)
    view = (0.4, 0.9, 0.25) if mode == "held" else \
           (math.sin(math.radians(30)), -math.cos(math.radians(30)), 0.35)
    camera(sc, ctr, view, size * 1.6)
elif mode == "marigold":
    # a short loop section, close up: frame the front-bottom of the worn mala
    lo, hi, pts = spline_bounds(mala)
    tgt = min(pts, key=lambda p: p.z)
    studio(sc, tgt.z - 0.2, tgt, 0.3)
    camera(sc, tgt, (0.3, -1, 0.5), 0.17, lens=60)
    sc.camera.data.dof.aperture_fstop = 8

os.makedirs(os.path.dirname(out), exist_ok=True)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("[props-render] wrote", out)
