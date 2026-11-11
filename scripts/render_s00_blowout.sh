#!/usr/bin/env bash
# Full render of the s00 blow-out (scene frames 101-172 = web scene "s00_blowout" 0001-0072),
# then a preview video (2 s of the loop + the blow-out).
# Usage: bash scripts/render_s00_blowout.sh 067   -> blender/scenes/s00_enter_v067_realfire.blend
set -u
V=${1:?version, e.g. 067}
ROOT=/e/Projects/tihar
B="/c/Users/user/Downloads/blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release/blender.exe"
FF="/c/Users/user/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"
RAW=renders/s00_blowout_raw_v$V
OUT=renders/s00_blowout
PREV=$ROOT/renders/s00_enter/preview
LOG=$PREV/render_blowout_v${V}_log.txt
cd "$ROOT"
mkdir -p "$RAW" "$OUT"
echo "start $(date)" > "$LOG"
"$B" -b blender/scenes/s00_enter_v${V}_realfire.blend --python scripts/s00_render_headless.py -- realfire "$RAW" 101-172 2>&1 | grep -E "\[s00\]|Error|Traceback" >> "$LOG"
echo "renders done $(date) frames=$(ls $RAW/*.png | wc -l)" >> "$LOG"
# renumber 0101-0172 -> 0001-0072 for the web sequence
rm -f "$OUT"/*.png
for f in $(seq 101 172); do cp "$RAW/$(printf %04d $f).png" "$OUT/$(printf %04d $((f - 100))).png"; done
"$FF" -y -hide_banner -loglevel error -framerate 24 -i renders/s00_enter/%04d.png -frames:v 48 -framerate 24 -i "$OUT/%04d.png" \
  -filter_complex "[0:v][1:v]concat=n=2:v=1[v]" -map "[v]" -c:v libx264 -crf 18 -pix_fmt yuv420p "$PREV/s00_blowout_v$V.mp4" && echo "video ok" >> "$LOG"
echo "all done $(date)" >> "$LOG"
