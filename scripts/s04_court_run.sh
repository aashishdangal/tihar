#!/usr/bin/env bash
# Run background Blender under the shared GPU lock (renders/.gpu_lock), then release it.
#   bash scripts/s04_court_run.sh <file.blend|-> <script.py> [-- args...]
# Use "-" as the blend to start from factory startup.
set -u
ROOT=/e/Projects/tihar
BL="/c/Users/user/Downloads/blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release/blender.exe"
LOCK=$ROOT/renders/.gpu_lock
blend=$1; shift; script=$1; shift
while [ -f "$LOCK" ]; do
  age=$(( $(date +%s) - $(stat -c %Y "$LOCK") ))
  [ $age -gt 1200 ] && break
  sleep 10
done
echo court-agent > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
t0=$(date +%s)
if [ "$blend" = "-" ]; then
  "$BL" -b --factory-startup --python "$script" "$@"
else
  "$BL" -b "$blend" --python "$script" "$@"
fi
echo "[run] elapsed $(( $(date +%s) - t0 ))s"
