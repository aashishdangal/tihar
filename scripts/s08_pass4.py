"""s08 pass 4 (owner 2026-11-20): the flag now lives in its own file (s08_flag.blend) and is
composited as a transparent looping layer, so the finale plate must not render its own flag/pole;
and the dusk sky glow sits at the real November sunset azimuth (~245 deg, WSW) - it had been at
170 deg (S), lighting everything from behind-right.

Run headless: blender.exe -b s08_finale_v069.blend --python scripts/s08_pass4.py -- s08_finale_v070.blend
"""
import math
import os
import sys

import bpy

w = bpy.context.scene.world
w.node_tree.nodes["S08_HDRI_Rot"].inputs["Rotation"].default_value[2] = math.radians(12.4)   # glow -> 245 deg
for n in ("S08_Flag", "S08_FlagPole"):
    o = bpy.data.objects[n]
    o.hide_render = True; o.hide_viewport = True
out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(bpy.data.filepath), out))
print("[s08p4] saved", bpy.data.filepath)
