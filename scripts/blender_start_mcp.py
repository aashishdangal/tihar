# Run at Blender launch: starts the Blender MCP server once the UI is ready.
# Usage: blender.exe <file.blend> --python scripts/blender_start_mcp.py
import bpy


def _start():
    try:
        win = bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=win):
            bpy.ops.blendermcp.start_server()
        print("[start_mcp] Blender MCP server started")
    except Exception as e:  # retry until the UI and addon are ready
        print("[start_mcp] not ready:", e)
        return 2.0
    return None


bpy.app.timers.register(_start, first_interval=3.0)
