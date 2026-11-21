"""s08 flag as smooth travelling waves instead of a cloth sim (owner 2026-11-21: "still looks crumbled
fabric doesnot behave like that").

The cloth sim on a 3 cm grid kept producing grid-sized lumps (field noise, self-collision jitter,
weak bending). Here the motion is computed: waves travel from the hoist to the fly end, growing in
amplitude away from the pole, with a slow swell. Every frequency is a whole number of cycles per
loop, so frame L flows into frame 1 exactly. The fly is pulled in along the wave so the cloth does
not stretch. Written as a PC2 cache played by S08_FlagLoop (Mesh Cache -> Subdivision -> Solidify).

Headless, on blender/scenes/s08_flag.blend (writes s08_flag_v004.blend, blender/assets/s08/flag_wave.pc2):
  blender.exe -b blender/scenes/s08_flag.blend --python scripts/s08_flag_wave.py
Env S08_TEST=1 renders test frames to renders/s08_finale/test/flag_wave/ (every 4th frame, 50 %).
"""
import math
import os
import struct

import bpy
import numpy as np

ROOT = r"E:/Projects/tihar"
L = 72                                # 3 s at 24 fps (owner 2026-11-21: "the loop should be 3sec")
sc = bpy.context.scene
fl = bpy.data.objects["S08_Flag"]
lo = bpy.data.objects["S08_FlagLoop"]
rest = np.array([v.co[:] for v in fl.data.vertices])     # flat pennant, hoist at x=0, fly toward -x, z up
x0, z0 = rest[:, 0], rest[:, 2]
W = -x0.min(); H = z0.max() - z0.min(); zb = z0.min()

# waves: (amplitude m, wavelength m, cycles per loop, phase, tilt = how much the crest leans with height)
# owner 2026-11-21 on the first wave pass: "its too much waving" -> about half the height, slower
# (0.6 / 0.9 / 1.4 Hz) and longer waves, like a light evening breeze
# pass 2 (after the cloth sims kept curling their tips): between pass 1 and the calm set
# pass 3 (owner: "a bit more movement", loop shorter): ~25 % taller, 0.8 / 1.2 / 1.8 Hz in a 5 s loop
# pass 4 (owner: "more movement"): ~1.6x pass 3 -> 0.080 / 0.035 / 0.012
# pass 5 (owner: "more movement" again): main wave x1.6, ripples x1.15 (big rolls, not chop)
# pass 6 (owner: "small wind due to which flag must fold and wave"): 3 s loop, gentler waves
# (0.67 / 1.0 / 1.67 Hz) and the fly hangs down from the hoist (sag), more in the lulls
# pass 7 (owner reference photos refrences/New folder/nepal*-flag-blowing-by-the-wind*.jpg, images (5).jpg):
# the flag stands out almost flat, one big soft DIAGONAL fold (main wave leans strongly with height),
# little sag, and the two tips flutter fast while the body moves slowly
# pass 8 (owner: "very realistic, research in web"). From the flag-flutter literature:
#  - bending waves run hoist -> fly at ONE speed, a little below the wind (Alben & Shelley 2008;
#    arXiv 2106.14988), so every component shares the phase speed C (lambda = C / f) and the shape
#    travels as one piece instead of ripples sliding over each other;
#  - the amplitude envelope is roughly LINEAR in distance from the pole (Alben & Shelley 2008);
#  - Strouhal St = f L / U ~ 0.1-1, near constant (arXiv 2602.06237): L = 1.1 m in a light breeze
#    (~2-3 m/s) -> main flap ~1 Hz; wavelength ~ the flag length;
#  - gusts make it irregular (arXiv 2103.08246), gravity sags it in the lulls.
# 3 s loop (72 frames): 1 / 2 / 3 Hz = 3 / 6 / 9 cycles per loop.
C = 1.25                               # m/s, wave speed along the cloth
WAVES = [(0.100, C / 1.0, 3, 0.0, 0.60),
         (0.025, C / 2.0, 6, 1.7, 0.60),
         (0.009, C / 3.0, 9, 4.1, 0.60)]
SAG_MIN, SAG_LULL = 0.08, 0.20         # tip angle below horizontal (rad) in a gust / added in a lull
TIP = (0.015, C / 3.0, 9, 0.6)         # tip flick at the 3 Hz ripple, same wave speed
ENV_POW = 1.0                          # linear envelope (was 1.25)
SWELL = 1                              # slow gust swell, cycles per loop


def swell(t):
    """uneven gusts: two whole-cycle swells so it does not pulse like a metronome"""
    return 1.0 + 0.22 * math.sin(2 * math.pi * SWELL * t) + 0.14 * math.sin(2 * math.pi * 2 * t + 1.1)


def offset(s, zn, t):
    """normal displacement at distance s from the hoist (m), height 0..1, loop time 0..1"""
    u = s / W
    env = (u ** ENV_POW) * swell(t)
    y = 0.0
    for a, lam, n, ph, tilt in WAVES:
        y += a * np.sin(2 * math.pi * ((s + tilt * zn * H) / lam - n * t) + ph)
    a, lam, n, ph = TIP                                   # only the outer quarter, strongest at the very tips
    y += a * np.clip((u - 0.72) / 0.28, 0, 1) ** 2 * np.sin(2 * math.pi * (s / lam - n * t) + ph + 3.0 * zn)
    return env * y


NS = 48
CLAMP = [0]
seq = []
for f in range(L):
    t = f / L
    P = rest.copy()
    zn = (z0 - zb) / H
    # integrate along the cloth so arc length is kept: x shrinks where the wave tilts the surface
    sx = -x0
    ss = np.linspace(0, 1, NS + 1)[None, :] * sx[:, None]          # samples from hoist to vertex
    yy = offset(ss, zn[:, None], t)
    dy = np.diff(yy, axis=1); ds = np.diff(ss, axis=1)
    CLAMP[0] += int((dy ** 2 > ds ** 2).sum())        # surface steeper than 90 deg -> would fold
    c = np.sqrt(np.maximum(ds ** 2 - dy ** 2, 0))      # length left for the along-flag direction
    # sag: the cloth bends down from the hoist, angle growing toward the fly, deeper in the lulls;
    # integrated with the waves so no strip of cloth stretches
    phi_tip = SAG_MIN + SAG_LULL * (1.36 - swell(t)) / 0.72
    smid = 0.5 * (ss[:, 1:] + ss[:, :-1])
    phi = phi_tip * (smid / W) ** 1.5
    P[:, 0] = -(c * np.cos(phi)).sum(axis=1)
    P[:, 1] = yy[:, -1]
    P[:, 2] = z0 - (c * np.sin(phi)).sum(axis=1)
    seq.append(P.astype(np.float32))

path = ROOT + "/blender/assets/s08/flag_wave6.pc2"
with open(path, "wb") as fh:
    fh.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, len(rest), 1.0, 1.0, L + 1))
    for P in seq + [seq[0]]:
        fh.write(P.tobytes())
print("[wave] max offset %.3f m, folded samples %d" % (max(np.abs(P[:, 1]).max() for P in seq), CLAMP[0]))

# loc/rot/scale, not matrix_world: the hidden sim flag's matrix reads as identity in background mode
lo.location = fl.location; lo.rotation_euler = fl.rotation_euler; lo.scale = fl.scale
mc = next(m for m in lo.modifiers if m.type == "MESH_CACHE")
mc.filepath = path; mc.frame_start = 1.0
sub = next(m for m in lo.modifiers if m.type == "SUBSURF"); sub.levels = 1; sub.render_levels = 2
lo.hide_render = False; lo.hide_viewport = False
fl.hide_render = True
sc.frame_start, sc.frame_end = 1, L
sc["s08_flag_loop"] = {"method": "wave", "length": L}
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/scenes/s08_flag_v014.blend")
print("[wave] saved", bpy.data.filepath)

if os.environ.get("S08_TEST"):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "HIP"; prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == "HIP" and "9070" in dv.name
    sc.cycles.device = "GPU"; sc.cycles.samples = 16
    sc.render.resolution_percentage = 35
    out = ROOT + "/renders/s08_finale/test/flag_wave8"
    os.makedirs(out, exist_ok=True)
    for f in range(1, L + 1):
        sc.frame_set(f); sc.render.filepath = out + "/f_%04d.png" % f
        bpy.ops.render.render(write_still=True)
    print("[wave] rendered test frames")
print("[wave] done")
