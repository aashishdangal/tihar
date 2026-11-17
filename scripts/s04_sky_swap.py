# Swap the world sky image: blender -b <in.blend> --python scripts/s04_sky_swap.py -- <hdr file name> [out.blend]
import bpy, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env = next(n for n in bpy.context.scene.world.node_tree.nodes if n.type == "TEX_ENVIRONMENT")
env.image = bpy.data.images.load(os.path.join(root, "blender", "assets", "polyhaven", "hdris", argv[0]), check_existing=True)
print("[sky]", env.image.name)
if len(argv) > 1:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[1]))
