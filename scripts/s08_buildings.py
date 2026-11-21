"""Kathmandu Valley buildings for s08 (owner, 2026-11-20: "make buildings, very low poly ...
place them at the right place").

Every OpenStreetMap building centre (blender/assets/osm/buildings.json, 455k ways, © OSM
contributors, ODbL) becomes one box in Blender: same projection as s01 (x = (lon-85.32)*KX,
y = (lat-27.70)*M) and ground height from the Copernicus GLO-30 DEM, so they sit where the
real houses are.

What the boxes stand for (World Housing Encyclopedia reports 99 / 100103; Kathmandu census):
the valley is overwhelmingly 3-5 storey reinforced-concrete frame houses with flat roofs
(roof water tanks, painted render) mixed with older 3-5 storey brick Newari houses in the cores.
OSM `building:levels` is used where mapped; otherwise 3-5 storeys, ~3 m each. Footprints are
typical plot sizes (7-12 m). Colours: the painted-render palette of the valley.

Output: blender/assets/osm/s08_buildings.npy, float32 rows
  x, y, z_ground, sx, sy, height, rot_z, r, g, b, tank(0/1)
Run (repo root): python -I scripts/s08_buildings.py
"""
import json
import math
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
M = 111320.0
KX = M * math.cos(math.radians(27.70))
rng = np.random.default_rng(8)

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


el = json.load(open(os.path.join(ROOT, "osm", "buildings.json"), encoding="utf-8"))["elements"]
lat, lon, lev, kind = [], [], [], []
for e in el:
    c = e.get("center")
    if not c:
        continue
    t = e.get("tags", {})
    lv = t.get("building:levels", "")
    try:
        lv = float(str(lv).split(";")[0])
    except ValueError:
        lv = 0.0
    lat.append(c["lat"]); lon.append(c["lon"]); lev.append(lv)
    b = t.get("building", "yes")
    kind.append(1 if b in ("temple", "shrine") or t.get("amenity") == "place_of_worship" else 0)
lat, lon, lev = np.array(lat), np.array(lon), np.array(lev)
n = len(lat)

x = (lon - 85.32) * KX
y = (lat - 27.70) * M
z = hgt(lat, lon)

# DSM heights include the houses themselves; sink the box a little so it never floats
z = z - 2.5

levels = np.where((lev >= 1) & (lev <= 20), lev, rng.choice([2, 3, 3, 4, 4, 4, 5, 5, 6], n))
height = levels * 3.0 + rng.uniform(0.3, 1.2, n)          # parapet
sx = rng.uniform(7.0, 12.0, n)
sy = sx * rng.uniform(0.75, 1.35, n)
# streets in the valley run in a few local directions; snap rotations so blocks line up
rot = (np.round(rng.uniform(0, 4, n)) * (math.pi / 2) + rng.normal(0, 0.06, n)
       + 0.35 * np.sin(x / 2300.0) + 0.25 * np.cos(y / 1900.0))

PAL = np.array([
    (0.78, 0.76, 0.72), (0.80, 0.77, 0.70), (0.70, 0.69, 0.67), (0.62, 0.61, 0.60),   # render, concrete
    (0.85, 0.72, 0.62), (0.86, 0.66, 0.58), (0.82, 0.74, 0.55), (0.80, 0.80, 0.62),   # cream, salmon, ochre
    (0.66, 0.74, 0.80), (0.86, 0.63, 0.68), (0.55, 0.36, 0.28), (0.50, 0.32, 0.25),   # blue, pink, brick
], dtype=np.float32)
W = np.array([10, 9, 8, 6, 7, 5, 5, 4, 3, 3, 4, 3], dtype=np.float64)
col = PAL[rng.choice(len(PAL), n, p=W / W.sum())] * rng.uniform(0.9, 1.05, (n, 1))
tank = (rng.random(n) < 0.55).astype(np.float32)

out = np.stack([x, y, z, sx, sy, height, rot, col[:, 0], col[:, 1], col[:, 2], tank], 1).astype(np.float32)
np.save(os.path.join(ROOT, "osm", "s08_buildings.npy"), out)
print(n, "buildings;", "levels mapped:", int(((lev >= 1) & (lev <= 20)).sum()),
      "x", round(x.min()), round(x.max()), "y", round(y.min()), round(y.max()))
