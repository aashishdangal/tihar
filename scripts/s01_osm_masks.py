"""Build extra OSM masks for s01 light generation, on the hills Sentinel-2 mosaic grid (~17 m/px).

Writes blender/assets/osm/s01_osm_extra_masks.npz with:
  bdens    building density (0..1), from building centroids per ~100 m, normalised at the 75th percentile
  open     farmland / parks / grass / cemetery / golf / military / pitches (0..1, 60 m soft edge)
  aero     airport (aeroway=aerodrome) polygon (0..1, 100 m soft edge)
  roadclr  main-road corridors (+-12 m around centrelines) where no house lights go
and blender/assets/osm/s01_aerodrome_outline.npy (lat, lon) for perimeter-road lamps.
Run from the repo root:  python -I scripts/s01_osm_masks.py
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
mj = json.load(open(os.path.join(ROOT, "dem", "s01_hills_s2_mosaic.json")))
n = 2 ** mj["z"]
W, H = mj["W"], mj["H"]
MPP = 40075016.7 * math.cos(math.radians(27.7)) / (n * 256)  # metres per mosaic pixel


def px(lat, lon):
    tx = (np.asarray(lon) + 180) / 360 * n
    ty = (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n
    return (tx - mj["x0"]) * 256, (ty - mj["y0"]) * 256


def load(name):
    return json.load(open(os.path.join(ROOT, "osm", name), encoding="utf-8"))["elements"]


# ---- building density
b = load("buildings.json")
lat = np.array([e["center"]["lat"] for e in b if "center" in e])
lon = np.array([e["center"]["lon"] for e in b if "center" in e])
x, y = px(lat, lon)
cell = max(1, int(round(100 / MPP)))
hist, _, _ = np.histogram2d(y, x, bins=[np.arange(0, H + cell, cell), np.arange(0, W + cell, cell)])
p75 = np.percentile(hist[hist > 0], 75)
dens = np.clip(hist / p75, 0, 1)
dimg = Image.fromarray((dens * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(cell * 0.6))
bdens = np.asarray(dimg, dtype=np.float32) / 255.0

# ---- open land and aerodrome polygons
lu = load("landuse.json")
OPEN = {"farmland", "grass", "meadow", "cemetery", "military", "orchard", "allotments", "recreation_ground",
        "park", "golf_course", "pitch", "stadium"}
oimg = Image.new("L", (W, H), 0)
od = ImageDraw.Draw(oimg)
aimg = Image.new("L", (W, H), 0)
ad = ImageDraw.Draw(aimg)
outline = []


def rings(members):
    segs = [[(g["lat"], g["lon"]) for g in m["geometry"]] for m in members
            if m.get("type") == "way" and m.get("role", "outer") == "outer" and "geometry" in m]
    out = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                    segs.pop(i)
                    changed = True
                    break
                if s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                    segs.pop(i)
                    changed = True
                    break
        out.append(ring)
    return out


for e in lu:
    t = e["tags"]
    kind = t.get("landuse") or t.get("leisure") or t.get("aeroway")
    polys = []
    if e["type"] == "way" and "geometry" in e:
        polys = [[(g["lat"], g["lon"]) for g in e["geometry"]]]
    elif e["type"] == "relation":
        polys = rings(e.get("members", []))
    for poly in polys:
        if len(poly) < 3:
            continue
        xs, ys = px(np.array([p[0] for p in poly]), np.array([p[1] for p in poly]))
        pts = list(zip(xs.tolist(), ys.tolist()))
        if kind == "aerodrome":
            ad.polygon(pts, fill=255)
            outline += poly
        elif kind in OPEN:
            od.polygon(pts, fill=255)
open_m = np.asarray(oimg.filter(ImageFilter.GaussianBlur(60 / MPP / 2)), dtype=np.float32) / 255.0
aero = np.asarray(aimg.filter(ImageFilter.GaussianBlur(100 / MPP / 2)), dtype=np.float32) / 255.0

# ---- main-road corridors (no house lights within +-12 m of the centreline)
rimg = Image.new("L", (W * 2, H * 2), 0)
rd = ImageDraw.Draw(rimg)
for e in load("roads.json"):
    if e["tags"].get("highway") not in ("trunk", "primary", "secondary", "trunk_link", "primary_link") or "geometry" not in e:
        continue
    xs, ys = px(np.array([g["lat"] for g in e["geometry"]]), np.array([g["lon"] for g in e["geometry"]]))
    rd.line(list(zip((xs * 2).tolist(), (ys * 2).tolist())), fill=255, width=max(1, int(round(24 / MPP * 2))))
roadclr = np.asarray(rimg.resize((W, H), Image.BILINEAR), dtype=np.float32) / 255.0

np.savez_compressed(os.path.join(ROOT, "osm", "s01_osm_extra_masks.npz"), bdens=bdens, open=open_m, aero=aero, roadclr=roadclr)
np.save(os.path.join(ROOT, "osm", "s01_aerodrome_outline.npy"), np.array(outline))
print("buildings", len(lat), "p75 per cell", p75, "open frac", round(float((open_m > 0.5).mean()), 3),
      "aerodrome pts", len(outline), "m/px", round(MPP, 1))
