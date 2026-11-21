"""Real OSM footprints from the s08 hill to past the airport (owner 2026-11-21: "city generator to fill
up to airport area then mid poly then low poly").

Input : blender/assets/osm/mid_tiles/t0-3.json (Overpass, q0-3.txt: way[building] in 4 latitude tiles of
        27.598,85.285,27.735,85.425, out geom; (c) OpenStreetMap contributors, ODbL)
Output: blender/assets/osm/s08_mid.npz   bv (N,3) footprint verts (x, y, z_base), bf (F,) verts per
        footprint, blev (F,) storeys, dist (F,) metres from CAM_S08, ang (F,) degrees off its view axis
Same projection, DEM and ground rule as scripts/s08_near_city.py.
Run (repo root): python -I scripts/s08_mid_city.py
"""
import json
import math
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
M = 111320.0
KX = M * math.cos(math.radians(27.70))
CX, CY = 2000.0, -11000.0
rng = np.random.default_rng(31)
D = os.path.join(ROOT, "dem", "Copernicus_DSM_COG_10_")
dem = np.load(D + "N27_00_E085_00_DEM.npy")


def hgt(lat, lon):
    r = (28 - lat) * 3600 - 0.5
    c = (lon - 85) * 3600 - 0.5
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    fr, fc = r - r0, c - c0
    return (dem[r0, c0] * (1 - fc) + dem[r0, c0 + 1] * fc) * (1 - fr) + (dem[r0 + 1, c0] * (1 - fc) + dem[r0 + 1, c0 + 1] * fc) * fr


# fetched as 4 latitude tiles in parallel (blender/assets/osm/mid_tiles/q0-3.txt); ways on a tile edge
# come twice, so keep each id once
el, seen = [], set()
for i in range(4):
    for e in json.load(open(os.path.join(ROOT, "osm", "mid_tiles", "t%d.json" % i), encoding="utf-8"))["elements"]:
        if e["id"] not in seen:
            seen.add(e["id"]); el.append(e)
bv, bf, blev, dist, ang = [], [], [], [], []
for e in el:
    g = e.get("geometry")
    t = e.get("tags", {})
    if not g or "building" not in t or len(g) < 4 or g[0] != g[-1]:
        continue
    lat = np.array([p["lat"] for p in g]); lon = np.array([p["lon"] for p in g])
    x = (lon - 85.32) * KX; y = (lat - 27.70) * M
    x, y = x[:-1], y[:-1]
    cx, cy = x.mean(), y.mean()
    a = math.degrees(math.atan2(cx - CX, cy - CY))
    if abs(a) > 30:                                    # outside the view cone (+-21.8 deg) with margin
        continue
    area = 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    if abs(area) < 15 or abs(area) > 4000:
        continue
    if area < 0:
        x, y = x[::-1], y[::-1]
    z = hgt(27.70 + y / M, 85.32 + x / KX)
    zb = float(z.min()) - 3.0
    try:
        lv = float(str(t.get("building:levels", "")).split(";")[0])
    except ValueError:
        lv = 0
    lv = lv if 1 <= lv <= 12 else float(rng.choice([2, 3, 3, 4, 4, 4, 5]))
    bv.append(np.stack([x, y, np.full(len(x), zb)], 1)); bf.append(len(x)); blev.append(lv)
    dist.append(math.hypot(cx - CX, cy - CY)); ang.append(a)
np.savez(os.path.join(ROOT, "osm", "s08_mid.npz"),
         bv=np.concatenate(bv).astype(np.float32), bf=np.array(bf, np.int32), blev=np.array(blev, np.float32),
         dist=np.array(dist, np.float32), ang=np.array(ang, np.float32))
d = np.array(dist)
print(len(bf), "footprints in the view cone; per 2 km:", np.histogram(d, bins=np.arange(0, 20001, 2000))[0].tolist())
