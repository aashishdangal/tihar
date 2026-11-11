#!/usr/bin/env bash
# Full s00 render: A (RealFire, v055) then B (original flame, v053), then 3x-loop preview videos.
set -u
ROOT=/e/Projects/tihar
B="/c/Users/user/Downloads/blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release/blender.exe"
FF="/c/Users/user/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"
PREV=$ROOT/renders/s00_enter/preview
LOG=$PREV/render_AB_log.txt
cd "$ROOT"
echo "A start $(date)" > "$LOG"
"$B" -b blender/scenes/s00_enter_v055_realfire.blend --python scripts/s00_render_headless.py -- realfire renders/s00_enter_realfire 1-96 2>&1 | grep -E "\[s00\]|Error|Traceback" >> "$LOG"
echo "B start $(date)" >> "$LOG"
"$B" -b blender/scenes/s00_enter_v053.blend --python scripts/s00_render_headless.py -- origflame renders/s00_enter 1-96 2>&1 | grep -E "\[s00\]|Error|Traceback" >> "$LOG"
echo "renders done $(date)" >> "$LOG"
"$FF" -y -hide_banner -loglevel error -stream_loop 2 -framerate 24 -i renders/s00_enter_realfire/%04d.png -frames:v 288 -c:v libx264 -crf 18 -pix_fmt yuv420p "$PREV/s00_A_v055_loop.mp4" && echo "video A ok" >> "$LOG"
"$FF" -y -hide_banner -loglevel error -stream_loop 2 -framerate 24 -i renders/s00_enter/%04d.png -frames:v 288 -c:v libx264 -crf 18 -pix_fmt yuv420p "$PREV/s00_B_v053_loop.mp4" && echo "video B ok" >> "$LOG"
echo "all done $(date)" >> "$LOG"
