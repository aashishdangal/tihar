"""Final Cycles render of s05 frames in a background Blender. Same settings as s02_render_frames.py
(RX 9070 XT only, HIP RT off, persistent data, 1920x1080, 192 spp), plus the 2048 texture cap that
the s05 test renders used to fit VRAM. Never saves the .blend.

Run through scripts/render_resume.py (restarts after crashes, renders only missing frames):
  python scripts/render_resume.py <blender.exe> blender/scenes/s05_laxmi_v022.blend \
      scripts/s05_render_frames.py renders/s05_laxmi 1 180 1920 1080
"""
import os, runpy, sys
import bpy

bpy.context.scene.cycles.texture_limit_render = '2048'
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 's02_render_frames.py'),
               run_name='__main__')
