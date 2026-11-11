"""Side-by-side comparison of one of our renders against real-world reference photos.

Usage:
    python scripts/compare_render.py <render.png> <ref1> [<ref2> ...] --out <sheet.png>

Writes:
    <sheet.png>          render on the left, references to the right, same height, labelled
    <sheet>.stats.json   measured numbers for the render and each reference

The numbers give the critique something objective to point at:
    luma_mean    average brightness (0-1)
    luma_p05/p95 shadow and highlight levels (0-1)
    contrast     p95 - p05
    warmth       mean(R) / mean(B); above 1 is warm
    saturation   mean HSV saturation (0-1)
    black_clip   share of pixels below 2% brightness (crushed blacks)
    white_clip   share of pixels above 98% brightness (blown highlights)
"""
import argparse
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont, ImageStat

HEIGHT = 720
GAP = 16
LABEL_H = 40


def _percentile(hist: list, q: float) -> float:
    total, acc = sum(hist), 0
    for value, count in enumerate(hist):
        acc += count
        if acc >= q * total:
            return value / 255.0
    return 1.0


def stats(img: Image.Image) -> dict:
    rgb = img.convert("RGB")
    rgb.thumbnail((1024, 1024))  # speed; statistics barely change
    luma = rgb.convert("L")  # ITU-R 601 luma
    hist = luma.histogram()
    n = sum(hist)
    r, g, b = ImageStat.Stat(rgb).mean
    sat = ImageStat.Stat(rgb.convert("HSV")).mean[1]
    p05, p95 = _percentile(hist, 0.05), _percentile(hist, 0.95)
    return {
        "luma_mean": round(ImageStat.Stat(luma).mean[0] / 255.0, 3),
        "luma_p05": round(p05, 3),
        "luma_p95": round(p95, 3),
        "contrast": round(p95 - p05, 3),
        "warmth": round(r / max(b, 0.5), 2),
        "saturation": round(sat / 255.0, 3),
        "black_clip": round(sum(hist[:6]) / n, 3),
        "white_clip": round(sum(hist[250:]) / n, 3),
    }


def fit(img: Image.Image) -> Image.Image:
    w = round(img.width * HEIGHT / img.height)
    return img.convert("RGB").resize((w, HEIGHT), Image.LANCZOS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("refs", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    paths = [args.render] + args.refs
    imgs = [Image.open(p) for p in paths]
    panels = [fit(i) for i in imgs]
    labels = ["OURS: " + pathlib.Path(args.render).name] + [
        f"REF {n}: " + pathlib.Path(p).name for n, p in enumerate(args.refs, 1)
    ]

    total_w = sum(p.width for p in panels) + GAP * (len(panels) - 1)
    sheet = Image.new("RGB", (total_w, HEIGHT + LABEL_H), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    x = 0
    for panel, label in zip(panels, labels):
        sheet.paste(panel, (x, LABEL_H))
        draw.text((x + 8, 10), label[:60], fill=(242, 163, 58), font=font)
        x += panel.width + GAP

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    report = {label: stats(img) for label, img in zip(labels, imgs)}
    out.with_suffix(".stats.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(out)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
