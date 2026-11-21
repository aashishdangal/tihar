"""Real OSM footprints and streets for the slope right below the s08 hill (owner, 2026-11-20:
"use city generator ... take data required from openmap").

The far valley stays as instanced boxes (scripts/s08_buildings.py); only the ~3 km in front of
CAM_S08, where a house is big enough to show windows, gets true footprints for The City
Generator add-on to dress.

Input : blender/assets/osm/near.json (Overpass, scripts query q_near.txt: way[building] +
        way[highway] in 27.598,85.305,27.640,85.375; (c) OpenStreetMap contributors, ODbL)
Output: blender/assets/osm/s08_near.npz
  bv (N,3) footprint vertices (x, y, z_base)   bf (F,) vertex count per footprint
  blev (F,) storeys (OSM building:levels, else 2-5)
  sv (M,3) street points  sw (S,) points per street  swid (S,) width (m)
Run (repo root): python -I scripts/s08_near_city.py
"""
import json
import math
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
M = 111320.0
KX = M * math.cos(math.radians(27.70))
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


ST_W = {"primary": 10, "secondary": 8, "tertiary": 6.5, "unclassified": 5, "residential": 4.5,
        "living_street": 4, "service": 3.5, "track": 3}
el = json.load(open(os.path.join(ROOT, "osm", "near.json"), encoding="utf-8"))["elements"]
bv, bf, blev, sv, sw, swid = [], [], [], [], [], []
for e in el:
    g = e.get("geometry")
    t = e.get("tags", {})
    if not g:
        continue
    lat = np.array([p["lat"] for p in g]); lon = np.array([p["lon"] for p in g])
    x = (lon - 85.32) * KX; y = (lat - 27.70) * M
    if "building" in t:
        if len(g) < 4 or g[0] != g[-1]:
            continue
        x, y = x[:-1], y[:-1]
        area = 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
        if abs(area) < 15 or abs(area) > 4000:
            continue
        if area < 0:                                   # counter-clockwise -> normals up
            x, y = x[::-1], y[::-1]
        z = hgt(27.70 + y / M, 85.32 + x / KX)
        # DSM includes the roof; the ground is near the lowest corner minus the house
        zb = float(z.min()) - 3.0
        try:
            lv = float(str(t.get("building:levels", "")).split(";")[0])
        except ValueError:
            lv = 0
        lv = lv if 1 <= lv <= 12 else float(rng.choice([2, 3, 3, 4, 4, 4, 5]))
        bv.append(np.stack([x, y, np.full(len(x), zb)], 1)); bf.append(len(x)); blev.append(lv)
    elif t.get("highway") in ST_W:
        seg = np.hypot(np.diff(x), np.diff(y)); s = np.concatenate([[0], np.cumsum(seg)])
        if s[-1] < 15:
            continue
        tt = np.linspace(0, s[-1], max(2, int(s[-1] / 8) + 1))
        xi = np.interp(tt, s, x); yi = np.interp(tt, s, y)
        zi = hgt(27.70 + yi / M, 85.32 + xi / KX) - 1.5
        sv.append(np.stack([xi, yi, zi], 1)); sw.append(len(xi)); swid.append(ST_W[t["highway"]])
np.savez(os.path.join(ROOT, "osm", "s08_near.npz"),
         bv=np.concatenate(bv).astype(np.float32), bf=np.array(bf, np.int32), blev=np.array(blev, np.float32),
         sv=np.concatenate(sv).astype(np.float32), sw=np.array(sw, np.int32), swid=np.array(swid, np.float32))
print(len(bf), "footprints,", len(sw), "streets")
