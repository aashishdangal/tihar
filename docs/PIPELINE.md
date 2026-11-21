# PIPELINE.md — Blender → frames → web

## 1. Per-scene Blender file

- One file per scene in `blender/scenes/`, e.g. `s05_laxmi.blend`.
- Collections: `ASSETS`, `SET`, `CHARACTERS`, `LIGHTS`, `CAMERA`, `FX`.
- One camera per scene: `CAM_S05`. Animate it along a Bezier path or with keyframes.
- Frame 1 starts on the previous scene's fill; the last frame ends on this
  scene's fill (see the "Out" column in `SCENES.md`).
- Mark the pause frame with a timeline marker named `PAUSE` (and `PAUSE_2`,
  `PAUSE_3` for multi-beat scenes). The web layer reads these from
  `web/src/scenes.json`.

## 2. Render settings (Cycles)

| Setting | Test | Final |
| --- | --- | --- |
| Device | GPU (HIP) | GPU (HIP) |
| Resolution | 960×540 | 1920×1080 |
| Samples | 64 + denoise | 256–512 + OpenImageDenoise |
| Frames | 3–5 key frames | full range |
| Output | PNG 8-bit | PNG 16-bit or EXR, then encode |

- Use adaptive sampling, light tree on, persistent data on (faster repeated frames).
- Volumetrics (fog) are the slowest part: use a low step rate, or fake distant fog
  with a mist pass in the compositor.
- Small diyos: emissive mesh + noise shader, not VDB. VDB flames only for hero
  close-ups (Scene 0, Laxmi's eyes).
- Instance repeated objects (diyos, marigolds) with geometry nodes or collection
  instances.
- Record seconds per frame from the test render in the table below before
  committing to a full render.

| Scene | Frames | Sec/frame (test) | Est. hours | Done |
| --- | --- | --- | --- | --- |
| s00 | 48 loop | | | |
| s01 | 186 (v032) | 78 (v027 final look, 1920×1080, 192 spp; Lazy Cloud fog off — with it on: 708–912) | ~4.3 | |
| s02 | 200 (v083) | ~50 (1920×1080, 192 spp; kausi close-up) | 1.5 for 90–200 (rerun 2026-11-16) | ✓ v083 |
| s03 | merged into s02 (2026-11-16) | | | |
| s04 | 180 | | | |
| s05 | 260 | | | |
| s06 | 220 | | | |
| s07 | 240 | | | |
| s08 | 200 | | | |

## 3. Encoding frames for the web

`scripts/encode_frames.sh <scene>` produces two sets from `renders/<scene>/`:

- Desktop: 1920×1080 WebP, cwebp `-q 100 -sharp_yuv` → `web/public/frames/<scene>/d/0001.webp`
- Mobile: centre crop to 9:16, scaled to 720×1280, cwebp `-q 100 -sharp_yuv` →
  `web/public/frames/<scene>/m/0001.webp`
- Off-centre shots set their own mobile framing in `scripts/mobile_framing.json`
  (s00: mode `fit`, the left 60% of the frame placed mid-screen with the frame's edge
  colour above and below, so the diyo stays whole). The encoder prints where named
  points (e.g. the flame) land in the mobile frame, for `web/src/scenes.json`.

Budget: ≤300 KB per desktop frame, ≤150 KB per mobile frame (raised 2026-11-11: q72 showed
blocks in dark gradients). Lossy q100 is the WebP ceiling (~93 KB for s00); near-lossless and
lossless are ~820–850 KB/frame. To optimize later, lower -q per scene.
`scripts/check_budget.js` warns when a scene's folder exceeds its budget.

## 4. Hidden-cut checklist

Before encoding, place the last frame of scene N and the first frame of scene N+1
side by side. The fill (fog, wing, dark, gold, plate) must cover the whole frame
in both, with matching colour and brightness.

## 5. Blender MCP workflow

1. Save a numbered version.
2. Ask Claude for one step (import, bind, add Rigify, keyframe, set material…).
3. Claude takes a viewport screenshot; the user confirms.
4. Repeat. Test-render before any full sequence.
