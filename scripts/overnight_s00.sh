#!/usr/bin/env bash
# One-off unattended job: wait for both s00 renders, make loop videos, then shut the PC down.
# A = RealFire flame -> renders/s00_enter_realfire/0001-0096.png
# B = original flame -> renders/s00_enter/0001-0096.png
set -u
ROOT=/e/Projects/tihar
PREV=$ROOT/renders/s00_enter/preview
MARK=$PREV/.overnight_start
LOG=$PREV/overnight_log.txt
FF="/c/Users/user/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"

count_new() { find "$1" -maxdepth 1 -name '[0-9][0-9][0-9][0-9].png' -newer "$MARK" | wc -l; }
echo "start $(date)" > "$LOG"

# wait up to 2 h for both sets (checks every 30 s); stop early if Blender dies
for i in $(seq 1 240); do
  a=$(count_new "$ROOT/renders/s00_enter_realfire"); b=$(count_new "$ROOT/renders/s00_enter")
  [ "$a" -ge 96 ] && [ "$b" -ge 96 ] && break
  if ! tasklist //FI "IMAGENAME eq blender.exe" | grep -q blender.exe; then echo "blender exited early: A=$a B=$b" >> "$LOG"; break; fi
  sleep 30
done
sleep 20   # let the last PNG finish writing
echo "frames A=$(count_new "$ROOT/renders/s00_enter_realfire") B=$(count_new "$ROOT/renders/s00_enter") $(date)" >> "$LOG"

make_video() {  # $1 frame dir, $2 output
  if [ "$(count_new "$1")" -ge 96 ]; then
    "$FF" -y -hide_banner -loglevel error -stream_loop 2 -framerate 24 -i "$1/%04d.png" \
      -frames:v 288 -c:v libx264 -crf 18 -pix_fmt yuv420p "$2" && echo "video ok: $2" >> "$LOG" \
      || echo "video FAILED: $2" >> "$LOG"
  else
    echo "skipped video (frames missing): $2" >> "$LOG"
  fi
}
make_video "$ROOT/renders/s00_enter_realfire" "$PREV/s00_A_realfire_loop.mp4"
make_video "$ROOT/renders/s00_enter"          "$PREV/s00_B_origflame_loop.mp4"

echo "shutdown requested $(date)" >> "$LOG"
shutdown.exe //s //t 120 //c "Tihar renders finished - shutting down in 2 minutes (run: shutdown /a to cancel)"
