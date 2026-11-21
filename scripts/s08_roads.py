"""Kathmandu Valley roads for s08 (owner, 2026-11-20: "add road details near the camera").

OSM ways (blender/assets/osm/roads.json: trunk, primary, secondary, tertiary and links,
© OpenStreetMap contributors, ODbL) -> polylines in the s01/s08 projection, draped on the
Copernicus GLO-30 DEM, resampled every ~25 m so they follow the ground.

Output: blender/assets/osm/s08_roads.npz with
  pts  (N, 3) float32  x, y, z
  way  (N,)   int32    polyline id (consecutive points with the same id are joined)
  width(W,)   float32  carriageway width per way (m)
Run (repo root): python -I scripts/s08_roads.py
"""
import json
import math
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
M = 111320.0
KX = M * math.cos(math.radians(27.70))
D = os.path.join(ROOT, "dem", "Copernicus_DSM_COG_10_")
top = np.concatenate([np.load(D + "N28_00_E084_00_DEM.npy"), np.load(D + "N28_00_E085_00_DEM.npy")], axis=1)
bot = np.concatenate([np.load(D + "N27_00_E084_00_DEM.npy"), np.load(D + "N27_00_E085_00_DEM.npy")], axis=1)
dem = np.concatenate([top, bot], axis=0)
del top, bot


def hgt(lat, lon):
    r = (29 - lat) * 3600 - 0.5
    c = (lon - 84) * 3600 - 0.5
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    fr, fc = r - r0, c - c0
    return (dem[r0, c0] * (1 - fc) + dem[r0, c0 + 1] * fc) * (1 - fr) + (dem[r0 + 1, c0] * (1 - fc) + dem[r0 + 1, c0 + 1] * fc) * fr


WIDTH = {"trunk": 14.0, "trunk_link": 8.0, "primary": 11.0, "primary_link": 7.0,
         "secondary": 8.0, "secondary_link": 6.0, "tertiary": 6.5, "tertiary_link": 5.0}
el = json.load(open(os.path.join(ROOT, "osm", "roads.json"), encoding="utf-8"))["elements"]
pts, way, width = [], [], []
for e in el:
    g = e.get("geometry")
    hw = e.get("tags", {}).get("highway", "")
    if not g or hw not in WIDTH:
        continue
    ll = np.array([(p["lat"], p["lon"]) for p in g])
    xy = np.stack([(ll[:, 1] - 85.32) * KX, (ll[:, 0] - 27.70) * M], 1)
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 30:
        continue
    t = np.linspace(0, s[-1], max(2, int(s[-1] / 25) + 1))
    x = np.interp(t, s, xy[:, 0]); y = np.interp(t, s, xy[:, 1])
    z = hgt(27.70 + y / M, 85.32 + x / KX) - 1.0      # the DSM is above the road surface
    wid = len(width)
    pts.append(np.stack([x, y, z], 1)); way.append(np.full(len(x), wid)); width.append(WIDTH[hw])
pts = np.concatenate(pts).astype(np.float32); way = np.concatenate(way).astype(np.int32)
np.savez(os.path.join(ROOT, "osm", "s08_roads.npz"), pts=pts, way=way, width=np.array(width, np.float32))
print(len(width), "roads,", len(pts), "points")
