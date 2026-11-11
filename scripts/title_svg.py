"""Turn a title in AMS Gourav Bold into a single SVG path (big titles only, CLAUDE.md).

AMS Gourav Bold is a legacy, non-Unicode font: Devanagari is typed with ASCII keys, so the
browser can't use it for live text. We take its glyph outlines once and ship only the path.
The .ttf itself is NOT committed (licence: "All rights reserved", see CREDITS.md).

Usage:
  python scripts/title_svg.py <ams.gourav-bold.ttf> <legacy string> <out.svg>
  e.g. "ithar" = तिहार  (i = ि typed before त, t = त, h = ह, a = ा, r = र)
"""
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

font_path, text, out = sys.argv[1], sys.argv[2], sys.argv[3]
font = TTFont(font_path)
gs = font.getGlyphSet()
cmap = font.getBestCmap()
kern = {}
if "kern" in font:
    for sub in font["kern"].kernTables:
        kern.update(getattr(sub, "kernTable", {}))

svg_pen = SVGPathPen(gs)
bounds = BoundsPen(gs)
x = 0
prev = None
for ch in text:
    name = cmap[ord(ch)]
    if prev is not None:
        x += kern.get((prev, name), 0)
    # flip y (font units point up, SVG points down)
    gs[name].draw(TransformPen(svg_pen, (1, 0, 0, -1, x, 0)))
    gs[name].draw(TransformPen(bounds, (1, 0, 0, -1, x, 0)))
    x += font["hmtx"][name][0]
    prev = name

x0, y0, x1, y1 = bounds.bounds
pad = 10
vb = f"{x0 - pad:.0f} {y0 - pad:.0f} {x1 - x0 + 2 * pad:.0f} {y1 - y0 + 2 * pad:.0f}"
d = svg_pen.getCommands()
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">'
       f'<path fill="currentColor" d="{d}"/></svg>\n')
open(out, "w", encoding="utf-8").write(svg)
print(f"viewBox {vb}  ({len(d)} chars of path data) -> {out}")
