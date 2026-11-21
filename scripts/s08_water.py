"""Rivers and ponds for the s08 valley (owner, 2026-11-20: "water sources missing").

blender/assets/osm/rivers.json (Overpass q_rivers.txt; (c) OpenStreetMap contributors, ODbL):
waterway=river/stream/canal lines and natural=water polygons (Taudaha, Kamal Pokhari, Rani
Pokhari, the Bagmati riverbank areas ...). Same projection and DEM as s08_buildings.py.

Output: blender/assets/osm/s08_water.npz
  lv (N,3) river centreline points   ln (L,) points per line   lw (L,) width (m)
  pv (M,3) pond outline vertices     pn (P,) vertices per pond
Run (repo root): python -I scripts/s08_water.py
"""
import json
import math
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
M = 111320.0
KX = M * math.cos(math.radians(27.70))
D = os.path.join(ROOT, "dem", "Copernicus_DSM_COG_10_")
dem = np.load(D + "N27_00_E085_00_DEM.npy")


def hgt(lat, lon):
    r = (28 - lat) * 3600 - 0.5
    c = (lon - 85) * 3600 - 0.5
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    fr, fc = r - r0, c - c0
    return (dem[r0, c0] * (1 - fc) + dem[r0, c0 + 1] * fc) * (1 - fr) + (dem[r0 + 1, c0] * (1 - fc) + dem[r0 + 1, c0 + 1] * fc) * fr


# November is dry season: the big rivers run in a channel much narrower than their bed
WID = {"river": 22.0, "canal": 5.0, "stream": 5.0}
el = json.load(open(os.path.join(ROOT, "osm", "rivers.json"), encoding="utf-8"))["elements"]
lv, ln, lw, pv, pn = [], [], [], [], []


def xy(g):
    lat = np.array([p["lat"] for p in g]); lon = np.array([p["lon"] for p in g])
    return (lon - 85.32) * KX, (lat - 27.70) * M


for e in el:
    t = e.get("tags", {})
    if e["type"] == "way" and t.get("waterway") in WID and e.get("geometry"):
        x, y = xy(e["geometry"])
        seg = np.hypot(np.diff(x), np.diff(y)); s = np.concatenate([[0], np.cumsum(seg)])
        if s[-1] < 200 or (t["waterway"] == "stream" and s[-1] < 1500):
            continue
        tt = np.linspace(0, s[-1], max(2, int(s[-1] / 20) + 1))
        xi = np.interp(tt, s, x); yi = np.interp(tt, s, y)
        zi = hgt(27.70 + yi / M, 85.32 + xi / KX)
        # a river never runs uphill: carve the DSM (trees, bridges, banks) down the flow
        zi = np.minimum.accumulate(zi) - 2.0
        lv.append(np.stack([xi, yi, zi], 1)); ln.append(len(xi)); lw.append(WID[t["waterway"]])
    elif t.get("natural") == "water":
        rings = []
        if e["type"] == "way" and e.get("geometry"):
            rings = [e["geometry"]]
        elif e["type"] == "relation":
            rings = [m["geometry"] for m in e.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
        for g in rings:
            if len(g) < 4:
                continue
            x, y = xy(g)
            if g[0] == g[-1]:
                x, y = x[:-1], y[:-1]
            area = 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
            if abs(area) < 300:
                continue
            if area < 0:
                x, y = x[::-1], y[::-1]
            z = float(hgt(27.70 + y / M, 85.32 + x / KX).min()) - 0.5
            pv.append(np.stack([x, y, np.full(len(x), z)], 1)); pn.append(len(x))
np.savez(os.path.join(ROOT, "osm", "s08_water.npz"),
         lv=np.concatenate(lv).astype(np.float32), ln=np.array(ln, np.int32), lw=np.array(lw, np.float32),
         pv=np.concatenate(pv).astype(np.float32), pn=np.array(pn, np.int32))
print(len(ln), "river lines,", len(pn), "ponds")
