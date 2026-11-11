#!/usr/bin/env bash
# Full s00 render (RealFire mode): 96 frames, then a 3x loop preview.
# Usage: bash scripts/render_s00_full.sh 063   -> blender/scenes/s00_enter_v063_realfire.blend
set -u
V=${1:?version, e.g. 063}
ROOT=/e/Projects/tihar
B="/c/Users/user/Downloads/blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release/blender.exe"
FF="/c/Users/user/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"
OUT=renders/s00_enter_v$V
PREV=$ROOT/renders/s00_enter/preview
LOG=$PREV/render_v${V}_log.txt
cd "$ROOT"
mkdir -p "$OUT"
echo "start $(date)" > "$LOG"
"$B" -b blender/scenes/s00_enter_v${V}_realfire.blend --python scripts/s00_render_headless.py -- realfire "$OUT" 1-96 2>&1 | grep -E "\[s00\]|Error|Traceback" >> "$LOG"
echo "renders done $(date) frames=$(ls $OUT/*.png | wc -l)" >> "$LOG"
"$FF" -y -hide_banner -loglevel error -stream_loop 2 -framerate 24 -i "$OUT/%04d.png" -frames:v 288 -c:v libx264 -crf 18 -pix_fmt yuv420p "$PREV/s00_v${V}_loop.mp4" && echo "video ok" >> "$LOG"
echo "all done $(date)" >> "$LOG"
