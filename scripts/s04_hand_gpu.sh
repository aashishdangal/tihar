#!/usr/bin/env bash
# Run a background Blender render under the shared GPU lock (renders/.gpu_lock).
# usage: bash scripts/s04_hand_gpu.sh <blend> <script.py> [script args...]
B="/c/Users/user/Downloads/blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release/blender.exe"
LOCK=/e/Projects/tihar/renders/.gpu_lock
blend="$1"; py="$2"; shift 2
while [ -f "$LOCK" ]; do
  age=$(( $(date +%s) - $(stat -c %Y "$LOCK") ))
  [ "$age" -gt 1200 ] && { echo "stale lock ($age s), taking it"; break; }
  echo "waiting for GPU lock held by: $(cat "$LOCK" 2>/dev/null)"; sleep 15
done
echo "hand-agent" > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
"$B" -b "$blend" --python "$py" -- "$@" 2>&1 | grep -E "\[|Error|rror|Traceback|Saved" | grep -v "^Fra:" | tail -40
