"""Shared WebP writer for the frame encoders."""
import glob
import os
import shutil
import subprocess
import tempfile

from PIL import Image

# cwebp (libwebp, winget Google.Libwebp) gives -sharp_yuv: cleaner colour edges than Pillow at q100.
CWEBP = os.environ.get("CWEBP") or shutil.which("cwebp") or next(iter(glob.glob(os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Google.Libwebp_*\libwebp-*\bin\cwebp.exe"))), None)


def save_webp(im_or_path, dest, q):
    """Encode to WebP: cwebp -q <q> -sharp_yuv if available, else Pillow. q="lossless" keeps the
    render exactly (full-resolution colour; lossy WebP halves chroma, which smears small lights)."""
    lossless = q == "lossless"
    if CWEBP is None:
        im = im_or_path if isinstance(im_or_path, Image.Image) else Image.open(im_or_path).convert("RGB")
        im.save(dest, "WEBP", lossless=True, quality=100, method=6) if lossless else im.save(dest, "WEBP", quality=q, method=6)
        return
    tmp = None
    if isinstance(im_or_path, Image.Image):
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        im_or_path.save(tmp)
        im_or_path = tmp
    try:
        opts = ["-lossless", "-z", "6"] if lossless else ["-q", str(q), "-m", "6", "-sharp_yuv"]
        subprocess.run([CWEBP, "-quiet", *opts, str(im_or_path), "-o", str(dest)], check=True)
    finally:
        if tmp:
            os.remove(tmp)
