"""Low-end laptop frames: web/public/frames/<scene>/d/*.webp|avif -> l/*.webp at 1280x720, lossy.

Made from the desktop WebP (not the PNG renders), so the 'l' set always matches what the site
shows. Picked by main.js on landscape screens under ~1600 physical px wide, or on devices with
<= 4 GB memory or <= 4 CPU cores: about a third of the download, decode time and memory.

Usage: python scripts/make_low_set.py s05_laxmi [s04_kukur ...]   (no args = every scene)
"""
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from webp_util import save_webp  # noqa: E402

W, H, Q = 1280, 720, 90
root = pathlib.Path(__file__).resolve().parent.parent / "web" / "public" / "frames"
scenes = sys.argv[1:] or sorted(p.name for p in root.iterdir() if (p / "d").is_dir())
for scene in scenes:
    src, out = root / scene / "d", root / scene / "l"
    out.mkdir(exist_ok=True)
    total = 0
    files = sorted(src.glob("*.avif")) or sorted(src.glob("*.webp"))  # d/ may be AVIF now
    for f in files:
        im = Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS)
        dest = out / (f.stem + ".webp")
        save_webp(im, dest, Q)
        total += dest.stat().st_size
    print(f"{scene}: {len(files)} frames -> l  {total/1e6:.1f} MB ({total/len(files)/1e3:.0f} KB/frame)")
