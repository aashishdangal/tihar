"""Generate all s01/s08 night light points (houses, street lamps, vehicles, airport) for Kathmandu Valley.

Output: blender/assets/lights/s01_light_points.npy, rows = lat, lon, abs_height_m, r, g, b, strength, kind
kind: 0 street lamp, 1 vehicle, 2 airport, 3 house/building light.
Inputs (all local, git-ignored): Copernicus GLO-30 DEM tiles (.npy), Sentinel-2 2016 z13 mosaic,
OSM roads/forest/river mask and river buffer (blender/assets/osm).
Run from the repo root:  python -I scripts/s01_gen_lights.py
"""
import json
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "assets")
rng = np.random.default_rng(23)
M = 111320.0
KX = M * math.cos(math.radians(27.70))


def P(*a):
    return os.path.join(ROOT, *a)


D = P("dem", "Copernicus_DSM_COG_10_")
top = np.concatenate([np.load(D + "N28_00_E084_00_DEM.npy"), np.load(D + "N28_00_E085_00_DEM.npy")], axis=1)
bot = np.concatenate([np.load(D + "N27_00_E084_00_DEM.npy"), np.load(D + "N27_00_E085_00_DEM.npy")], axis=1)
dem = np.concatenate([top, bot], axis=0)  # rows 29N -> 27N, cols 84E -> 86E
del top, bot


def hgt(lat, lon):
    r = (29 - lat) * 3600 - 0.5
    c = (lon - 84) * 3600 - 0.5
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    fr = r - r0
    fc = c - c0
    return (dem[r0, c0] * (1 - fc) + dem[r0, c0 + 1] * fc) * (1 - fr) + (dem[r0 + 1, c0] * (1 - fc) + dem[r0 + 1, c0 + 1] * fc) * fr


mj = json.load(open(P("dem", "s01_hills_s2_mosaic.json")))
n = 2 ** mj["z"]
sat = np.asarray(Image.open(P("dem", "s01_hills_s2cloudless2016_z13.png")).convert("RGB"), dtype=np.float32) / 255.0
sat = np.where(sat <= 0.04045, sat / 12.92, ((sat + 0.055) / 1.055) ** 2.4)  # sRGB -> linear, as the shader sees it
osm = np.asarray(Image.open(P("osm", "s01_osm_roads_forest_mask.png")).convert("RGB"), dtype=np.float32) / 255.0
buf = np.array(Image.open(P("osm", "s01_river_buffer80m.png"))) > 127
XM = np.load(P("osm", "s01_osm_extra_masks.npz"))  # from scripts/s01_osm_masks.py
BDENS, OPEN, AERO, ROADCLR = XM["bdens"], XM["open"], XM["aero"], XM["roadclr"]


def pix(lat, lon):
    tx = (lon + 180) / 360 * n
    ty = (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n
    return (np.clip(((ty - mj["y0"]) * 256).astype(int), 0, mj["H"] - 1),
            np.clip(((tx - mj["x0"]) * 256).astype(int), 0, mj["W"] - 1))


def smooth_noise(x, y, cell, seed):
    r = np.random.default_rng(seed)
    x0, y0 = x.min() - cell, y.min() - cell
    gx = int((x.max() - x0) / cell) + 3
    gy = int((y.max() - y0) / cell) + 3
    g = r.random((gy, gx))
    fx = (x - x0) / cell
    fy = (y - y0) / cell
    ix = np.floor(fx).astype(int)
    iy = np.floor(fy).astype(int)
    tx = fx - ix
    ty = fy - iy
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    return (g[iy, ix] * (1 - tx) + g[iy, ix + 1] * tx) * (1 - ty) + (g[iy + 1, ix] * (1 - tx) + g[iy + 1, ix + 1] * tx) * ty


def mr(v, a, b, c=0.0, d=1.0):
    t = np.clip((v - a) / (b - a), 0, 1)
    return c + (d - c) * t


# Airport frame (TIA runway 02/20 thresholds)
A = (27.683814, 85.353417)
B = (27.709353, 85.364783)
ax, ay = (A[1] - 85.32) * KX, (A[0] - 27.70) * M
bx, by = (B[1] - 85.32) * KX, (B[0] - 27.70) * M
RL = math.hypot(bx - ax, by - ay)
ux, uy = (bx - ax) / RL, (by - ay) / RL
nx, ny = -uy, ux
cxr, cyr = (ax + bx) / 2, (ay + by) / 2

# colour shares (owner refs): cool white 42 %, warm 10 %, blue 18 %, violet 3 %, magenta 3 %, green 2 %,
# red 4 %, cyan 6 %, marigold (diyos/candles) 12 %
POS = [0.00, 0.42, 0.52, 0.70, 0.73, 0.76, 0.78, 0.82, 0.88]
PAL = np.array([(0.80, 0.90, 1.00), (1.00, 0.80, 0.55), (0.08, 0.25, 1.00), (0.42, 0.12, 1.00), (1.00, 0.10, 0.55),
                (0.10, 1.00, 0.22), (1.00, 0.07, 0.04), (0.08, 0.80, 1.00), (0.887, 0.366, 0.042)])


def house_points(lat0, lat1, lon0, lon1, step, village_only=False):
    xs = np.arange((lon0 - 85.32) * KX, (lon1 - 85.32) * KX, step)
    ys = np.arange((lat0 - 27.70) * M, (lat1 - 27.70) * M, step)
    X, Y = np.meshgrid(xs, ys)
    X = X.ravel() + rng.uniform(-step / 2, step / 2, X.size)
    Y = Y.ravel() + rng.uniform(-step / 2, step / 2, Y.size)
    lat = 27.70 + Y / M
    lon = 85.32 + X / KX
    h = hgt(lat, lon)
    r, c = pix(lat, lon)
    R, G, Bc = sat[r, c, 0], sat[r, c, 1], sat[r, c, 2]
    V = np.maximum(np.maximum(R, G), Bc)
    S = np.where(V > 0, (V - np.minimum(np.minimum(R, G), Bc)) / np.maximum(V, 1e-6), 0)
    cm = mr(V, 0.38, 0.52) * mr(S, 0.25, 0.12)
    u2 = mr(R - G, -0.10, -0.025) * mr(V, 0.09, 0.17) * (1 - cm)
    band = mr(h, 1235, 1275) * mr(h, 1460, 1390)  # 1 on the valley floor, 0 above ~1460 m
    rad = mr(np.hypot(X, Y), 9000, 17000, 1.0, 0.25)
    # Density varies gently by neighbourhood (multi-scale noise, no holes): the real dark gaps
    # (parks, forests, rivers, airport) come from the OSM masks below, not from noise.
    fr = 0.55 * smooth_noise(X, Y, 900, 1) + 0.30 * smooth_noise(X, Y, 300, 11) + 0.15 * smooth_noise(X, Y, 100, 12)
    dist = mr(fr, 0.30, 0.55, 0.45, 1.0)
    core = u2 * band * rad * dist * 0.85
    sb = mr(h, 1400, 1480) * mr(h, 2400, 2050)  # village belt on the slopes, 1400-2400 m
    # sparse hillside villages; density scaled so a 14 m grid gives the same lights per km2 as a 60 m grid
    vil = sb * mr(smooth_noise(X, Y, 450, 2), 0.60, 0.75) * 0.10 * (step / 60.0) ** 2
    mask = vil if village_only else np.maximum(core, vil)
    is_village = vil >= core
    forest, river = osm[r, c, 1], osm[r, c, 2]
    pu = (X - cxr) * ux + (Y - cyr) * uy
    pv = (X - cxr) * nx + (Y - cyr) * ny
    # real structure from OSM: building density, open land (farmland/parks/...), airport, main-road corridors
    bd = np.clip(BDENS[r, c], 0.15, 1.0)
    mask = mask * bd * (1 - OPEN[r, c]) * (1 - AERO[r, c]) * (1 - ROADCLR[r, c])
    mask = mask * (1 - 0.97 * forest) * (1 - mr(river, 0.2, 0.5))
    clus = mr(smooth_noise(X, Y, 200, 3), 0.2, 0.8, 0.3, 1.6)
    keep = rng.random(X.size) < np.clip(mask * 0.5 * clus, 0, 1)  # fewer lamps ...
    X, Y, lat, lon, h, is_village = X[keep], Y[keep], lat[keep], lon[keep], h[keep], is_village[keep]
    cid = np.floor(X / 70).astype(np.int64) * 1000003 + np.floor(Y / 70).astype(np.int64)
    cr = (np.sin(cid * 12.9898) * 43758.5453) % 1.0
    col = PAL[np.searchsorted(POS, cr, side="right") - 1]
    b = rng.random(X.size) ** 3 * 3.92 + 0.08
    b = np.where(rng.random(X.size) < 0.05, b * 3, b)
    b = np.where(is_village, b * 0.5, b)  # village houses: fewer, dimmer lights than the city
    b = b * 1.6 * rng.lognormal(-0.55, 1.05, X.size)  # ... a few bright lamps over a dim floor
    b = np.where((cr >= 0.52) & (cr < 0.73), b * 2.0, b)  # blue/violet strings are dim to the eye: boost so they register
    return np.column_stack([lat, lon, h + rng.uniform(3, 14, X.size), col, b, np.full(X.size, 3)])


houses = np.concatenate([
    house_points(27.60, 27.80, 85.20, 85.52, 14.0),
    house_points(27.80, 28.06, 84.95, 85.72, 60.0, village_only=True),
    house_points(27.60, 27.80, 84.95, 85.20, 60.0, village_only=True),
    house_points(27.60, 27.80, 85.52, 85.72, 60.0, village_only=True),
])

# Street lamps and vehicles. Survival rates from reporting on Kathmandu street lights.
roads = json.load(open(P("osm", "roads.json"), encoding="utf-8"))["elements"]
LED = (0.86, 0.92, 1.0)
SOD = (1.0, 0.50, 0.16)
HEAD = (1.0, 0.95, 0.85)
TAIL = (1.0, 0.06, 0.03)
SPEC = {"trunk": (32, 2, 14, 0.66), "trunk_link": (32, 1, 6, 0.5), "primary": (35, 2, 10, 0.60),
        "primary_link": (35, 1, 6, 0.5), "secondary": (40, 1, 7, 0.30), "tertiary": (50, 1, 5, 0.10)}
RING_NP = "चक्रपथ"        # Nepali name of the Ring Road
CORR_NP = "करिडोर"        # "corridor" in Nepali
pts = []
for e in roads:
    hw = e["tags"].get("highway")
    if hw not in SPEC or "geometry" not in e:
        continue
    sp, sides, off, pw = SPEC[hw]
    stren = 0.5
    name_np = e["tags"].get("name", "")
    nm = (e["tags"].get("name:en", "") + " " + name_np).lower()
    ring = ("ring" in nm) or (RING_NP in name_np)
    corridor = ("corridor" in nm) or (CORR_NP in name_np)
    if hw in ("trunk", "primary") or ring:
        stren = 0.8  # main roads read as warm beads against the city
    if ring:
        sp, sides, off, pw = 30, 2, 16, 0.50
    if corridor:
        pw, stren = 0.15, 0.25
    g = np.array([(p["lat"], p["lon"]) for p in e["geometry"]])
    if len(g) < 2:
        continue
    xy = np.stack([(g[:, 1] - 85.32) * KX, (g[:, 0] - 27.70) * M], 1)
    seg = np.diff(xy, axis=0)
    sl = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0], np.cumsum(sl)])
    if cum[-1] < sp:
        continue
    s = np.arange(rng.uniform(0, sp), cum[-1], sp)
    s = np.clip(s + rng.uniform(-8, 8, s.size), 0, cum[-1])  # poles are not perfectly evenly spaced
    i = np.clip(np.searchsorted(cum, s) - 1, 0, len(sl) - 1)
    t = (s - cum[i]) / np.maximum(sl[i], 1e-6)
    p = xy[i] + seg[i] * t[:, None]
    tng = seg[i] / np.maximum(sl[i], 1e-6)[:, None]
    nrm = np.stack([-tng[:, 1], tng[:, 0]], 1)
    la0 = 27.70 + p[:, 1] / M
    lo0 = 85.32 + p[:, 0] / KX
    elev = hgt(la0, lo0)
    valley = (elev < 1460) & (np.hypot(p[:, 0], p[:, 1] - 1500) < 16000)
    rr_, cc_ = pix(la0, lo0)
    pk = np.where(valley, pw, pw * 0.15) * np.where(buf[rr_, cc_], 0.4, 1.0) * 0.85  # 15 % more lamps out
    for sd in ([1, -1] if sides == 2 else [rng.choice([1, -1])]):
        keep = rng.random(len(p)) < pk
        q = p + nrm * sd * off
        for a, b_ in zip(27.70 + q[keep, 1] / M, 85.32 + q[keep, 0] / KX):
            pts.append((a, b_, 8.0, *(SOD if rng.random() < 0.50 else LED), stren * rng.uniform(0.7, 1.1), 0))
    if hw in ("trunk", "primary", "secondary") or ring:
        dens = 1 / 90 if (ring or hw == "trunk") else (1 / 160 if hw == "primary" else 1 / 300)
        nveh = rng.poisson(cum[-1] * dens)
        sv = rng.uniform(0, cum[-1], nveh)
        iv = np.clip(np.searchsorted(cum, sv) - 1, 0, len(sl) - 1)
        tv = (sv - cum[iv]) / np.maximum(sl[iv], 1e-6)
        pv = xy[iv] + seg[iv] * tv[:, None]
        nv_ = np.stack([-seg[iv][:, 1], seg[iv][:, 0]], 1) / np.maximum(sl[iv], 1e-6)[:, None]
        pv = pv + nv_ * rng.choice([1, -1], nveh)[:, None] * 3.0
        la = 27.70 + pv[:, 1] / M
        lo = 85.32 + pv[:, 0] / KX
        ev = hgt(la, lo)
        for a, b_, e_ in zip(la, lo, ev):
            if e_ > 1460 and rng.random() > 0.25:
                continue
            u_ = rng.random()
            vcol = TAIL if u_ < 0.45 else ((1.0, 0.82, 0.55) if u_ < 0.85 else HEAD)  # tail / warm head / white head
            pts.append((a, b_, 1.0, *vcol, 0.7 * rng.uniform(0.8, 1.2), 1))


# Airport, laid out like a real night airfield. u runs along the runway (south -> north),
# +v points WEST (n = (-uy, ux)); TIA's parallel taxiway, apron and terminal are on the west side.
def ap(u, v, hoff, col, s):
    x = cxr + ux * u + nx * v
    y = cyr + uy * u + ny * v
    pts.append((27.70 + y / M, 85.32 + x / KX, hoff, *col, s, 2))


WH = (1.0, 0.93, 0.78)
GRN = (0.1, 1.0, 0.25)
RED = (1.0, 0.08, 0.05)
BLU = (0.10, 0.25, 1.0)
AMB = (1.0, 0.62, 0.25)
RW_HALF = 30.0  # runway edge-light line, a little wider than the taxiways
TW_HALF = 10.0  # taxiway edge lights
for u in np.arange(-RL / 2, RL / 2 + 1, 60.0):  # runway edge lights, 60 m, either side
    for sd in (1, -1):
        ap(u, sd * RW_HALF, 0.5, WH, 0.45)
for w in np.linspace(-RW_HALF, RW_HALF, 12):  # threshold (green) and runway end (red) bars
    ap(-RL / 2, w, 0.5, GRN, 0.45)
    ap(RL / 2, w, 0.5, RED, 0.45)
for k in range(1, 31):  # approach lights RWY 02: 900 m centreline every 30 m, crossbar at 300 m
    ap(-RL / 2 - 30 * k, 0, 4.0, WH, 0.55)
    if k == 10:
        for w in np.linspace(-15, 15, 7):
            ap(-RL / 2 - 300, w, 4.0, WH, 0.55)
for i in range(4):  # PAPI on the west (left) side of the RWY 02 threshold
    ap(-RL / 2 + 300, 45 + 9 * i, 1.0, RED if i < 2 else WH, 0.6)
for u in np.arange(-500, 1300, 60.0):  # parallel taxiway on the west side, dotted blue edge lights
    for sd in (-1, 1):
        ap(u, 190 + sd * TW_HALF, 0.4, BLU, 0.15)
for u0 in (-350, 250, 900):  # link taxiways between runway and parallel taxiway
    for v in np.arange(RW_HALF + 10, 180, 40.0):
        for sd in (-1, 1):
            ap(u0 + sd * TW_HALF, v, 0.4, BLU, 0.15)
for u in np.linspace(-250, 1150, 8):  # apron high-mast floodlights: a grid over the apron area, not a line
    for v in (300, 340, 380):
        ap(u + rng.uniform(-20, 20), v, 25.0, AMB, 2.5)
# perimeter road around the aerodrome boundary (OSM aeroway=aerodrome), lamps every ~40 m, half working
_ol = np.load(P("osm", "s01_aerodrome_outline.npy"))
if len(_ol) > 2:
    oxy = np.stack([(_ol[:, 1] - 85.32) * KX, (_ol[:, 0] - 27.70) * M], 1)
    oseg = np.diff(oxy, axis=0)
    osl = np.hypot(oseg[:, 0], oseg[:, 1])
    for k_ in range(len(osl)):
        if osl[k_] > 400:  # skip joins between separate rings
            continue
        for t_ in np.arange(0, osl[k_], 40.0):
            if rng.random() < 0.5:
                q = oxy[k_] + oseg[k_] * (t_ / max(osl[k_], 1e-6))
                pts.append((27.70 + q[1] / M, 85.32 + q[0] / KX, 8.0, *(SOD if rng.random() < 0.5 else LED), 0.8, 0))
for u in np.arange(-150, 1050, 8.0):  # terminal / building windows, scattered west of the apron
    if rng.random() < 0.6:
        ap(u + rng.uniform(-4, 4), rng.uniform(400, 470), rng.uniform(4, 14), (1.0, 0.84, 0.6), 0.5)

Pt = np.array(pts)
Pt[:, 2] = hgt(Pt[:, 0], Pt[:, 1]) + Pt[:, 2]
ALL = np.concatenate([Pt, houses])
np.save(P("lights", "s01_light_points.npy"), ALL)
k = ALL[:, 7].astype(int)
print("lamps", (k == 0).sum(), "vehicles", (k == 1).sum(), "airport", (k == 2).sum(), "houses", (k == 3).sum(), "total", len(ALL))
