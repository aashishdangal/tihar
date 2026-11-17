"""s05 test renders with Cycles texture size capped at 2048 (VRAM fit on the 16 GB RX 9070 XT).
Run: blender.exe -b <file>.blend --python scripts/s05_test_render_capped.py -- <out_prefix> <frames> [percent] [samples]
"""
import bpy, runpy, os, sys
bpy.context.scene.cycles.texture_limit_render = '2048'
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 's02_test_render.py'), run_name='__main__')
