"""The five moons of Tihar for the HUD (web/public/sprites/moon_1..5.png).

Drawn from scratch (no downloaded texture): a sphere seen face-on, lit by the sun at each night's
phase angle with Lommel-Seeliger shading (the real moon has almost no limb darkening), an albedo
map with the near-side maria at roughly their true places so the "face" reads, scattered craters,
Tycho and its rays, and faint earthshine on the dark side so the whole disc is always there.

    python scripts/make_moons.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image

N = 160  # sprite size (shown at ~28 CSS px; 160 keeps it crisp on 4x screens)
SS = 3   # supersampling for a clean limb
OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "sprites"

# lit fraction, side ("l" = waning, lit on the left as seen from Nepal; "r" = waxing)
PHASES = [(0.26, "l"), (0.12, "l"), (0.0, None), (0.05, "r"), (0.13, "r")]

rng = np.random.default_rng(7)
S = N * SS
y, x = np.mgrid[0:S, 0:S]
x = (x + 0.5) / S * 2 - 1
y = 1 - (y + 0.5) / S * 2
r2 = x * x + y * y
inside = r2 <= 1
z = np.sqrt(np.clip(1 - r2, 0, 1))


def noise(octaves, base, seed):
    """Value noise on the disc: sum of upsampled random grids."""
    g = np.random.default_rng(seed)
    acc = np.zeros((S, S))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        grid = Image.fromarray((g.random((n, n)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)
        acc += amp * (np.asarray(grid, float) / 255 - 0.5)
        tot += amp
        amp *= 0.55
    return acc / tot


# --- albedo ------------------------------------------------------------------------------------
alb = np.full((S, S), 0.62)
alb += noise(6, 4, 1) * 0.12  # highland mottling

# maria: (cx, cy, rx, ry, depth)
MARIA = [
    (-0.58, 0.12, 0.30, 0.42, 0.26),  # Oceanus Procellarum
    (-0.25, 0.44, 0.26, 0.22, 0.30),  # Imbrium
    (0.22, 0.42, 0.15, 0.14, 0.30),   # Serenitatis
    (0.40, 0.14, 0.19, 0.15, 0.28),   # Tranquillitatis
    (0.74, 0.34, 0.10, 0.09, 0.30),   # Crisium
    (0.60, -0.14, 0.11, 0.16, 0.24),  # Fecunditatis
    (0.42, -0.32, 0.08, 0.08, 0.22),  # Nectaris
    (-0.18, -0.34, 0.16, 0.12, 0.22), # Nubium
    (-0.55, -0.36, 0.09, 0.09, 0.24), # Humorum
    (0.02, 0.74, 0.42, 0.06, 0.18),   # Frigoris
    (0.06, 0.12, 0.10, 0.08, 0.18),   # Vaporum / Sinus Medii
]
edge = noise(6, 3, 2) * 1.1
for cx, cy, rx, ry, d in MARIA:
    q = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + edge
    alb -= d * np.clip(1.1 - q, 0, 1) ** 0.45
alb += noise(4, 16, 3) * 0.05 * (alb < 0.45)  # texture inside the seas

# craters: mostly relief (a height map, so they show along the terminator like the real moon),
# with only a faint albedo trace; on a full moon real craters almost vanish
h = np.zeros((S, S))
for _ in range(240):
    cx, cy = rng.uniform(-1, 1, 2)
    if cx * cx + cy * cy > 0.98:
        continue
    rad = 0.006 + 0.05 * rng.random() ** 5
    d = np.hypot(x - cx, y - cy) / rad
    h += rad * (-0.9 * np.clip(1 - d * d, 0, 1) + 0.45 * np.exp(-((d - 1.0) / 0.25) ** 2))
    alb += 0.025 * np.exp(-((d - 1.0) / 0.2) ** 2) - 0.012 * np.clip(1 - d, 0, 1)
h += noise(6, 8, 4) * 0.012  # small-scale roughness
# Tycho, Copernicus, Kepler: bright young craters; Tycho's rays reach across the south
for cx, cy, rad, rays in [(-0.14, -0.70, 0.035, 1.0), (-0.32, 0.17, 0.03, 0.45), (-0.62, 0.15, 0.018, 0.35)]:
    d = np.hypot(x - cx, y - cy)
    alb += 0.22 * np.exp(-(d / rad) ** 2)
    ang = np.arctan2(y - cy, x - cx)
    streak = np.zeros_like(x)
    for a in rng.uniform(-math.pi, math.pi, 18):
        streak += np.exp(-(((ang - a + math.pi) % (2 * math.pi) - math.pi) / 0.025) ** 2)
    alb += rays * 0.07 * streak * np.exp(-d / 0.55) * (d > rad)

alb = np.clip(alb, 0.08, 1)


def render(k, side):
    # phase angle a: lit fraction k = (1 + cos a) / 2; sun direction in view space
    if k > 0:
        a = math.acos(2 * k - 1)
        sx = -1 if side == "l" else 1
        sun = np.array([sx * math.sin(a), 0.0, math.cos(a)])
        gy, gx = np.gradient(h, 2 / S)
        gy = -gy  # image rows run downward
        BUMP = 0.5
        nx, ny, nz = x - BUMP * gx * z, y - BUMP * gy * z, z
        nl = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-9
        mu0 = np.clip((nx * sun[0] + ny * sun[1] + nz * sun[2]) / nl, 0, None)
        # the bumps may only shade what the sphere itself lights: no crater rim glows on the night side
        mu_s = x * sun[0] + y * sun[1] + z * sun[2]
        mu0 = mu0 * np.clip(mu_s * 12 + 0.15, 0, 1)
        lit = mu0 / (mu0 + z + 1e-6) * 2.0  # Lommel-Seeliger
        lit = np.clip(lit, 0, 1.0) ** 0.85
    else:
        lit = np.zeros_like(x)
    earth = 0.075 + 0.03 * z  # ashen light: the dark side, faintly blue-grey
    rgb_sun = np.array([1.0, 0.96, 0.88])
    rgb_earth = np.array([0.60, 0.68, 0.80])
    img = alb[..., None] * (lit[..., None] * rgb_sun * 1.05 + earth[..., None] * rgb_earth)
    img = np.clip(img, 0, 1) ** (1 / 1.1)
    # soft anti-aliased limb
    rr = np.sqrt(r2)
    alpha = np.clip((1 - rr) * S / 2.2, 0, 1)
    rgba = np.dstack([img, alpha])
    im = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")
    return im.resize((N, N), Image.LANCZOS)


OUT.mkdir(parents=True, exist_ok=True)
for i, (k, side) in enumerate(PHASES, 1):
    render(k, side).save(OUT / f"moon_{i}.png", optimize=True)
    print("moon", i, k, side)


