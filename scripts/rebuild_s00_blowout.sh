#!/usr/bin/env bash
# Re-bake the blow-out smoke into a new version, then render + encode the blow-out.
# Usage: bash scripts/rebuild_s00_blowout.sh 067 068   (from v067 -> v068)
set -eu
FROM=$1; TO=$2
ROOT=/e/Projects/tihar
B="/c/Users/user/Downloads/blender-5.2.4-candidate+v52.4f5026e99892-windows.amd64-release/blender.exe"
cd "$ROOT"
"$B" -b blender/scenes/s00_enter_v${FROM}_realfire.blend --python scripts/s00_add_smoke.py -- "$ROOT/blender/scenes/s00_enter_v${TO}_realfire.blend" 128 2>&1 | grep -E "\[smoke\]|Error|Traceback"
bash scripts/render_s00_blowout.sh "$TO"
bash scripts/encode_frames.sh s00_blowout
node scripts/check_budget.js
