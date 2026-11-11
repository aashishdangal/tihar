#!/usr/bin/env bash
# Usage: bash scripts/encode_frames.sh s00_enter
set -e
python "$(dirname "$0")/encode_frames.py" "$1"
