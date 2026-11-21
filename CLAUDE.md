# CLAUDE.md — Tihar Explainer ("The Road of Lights")

A realistic, scroll-driven 3D website explaining why Tihar is celebrated, for the
KUCC Tihar-Chhath Web UI Design Competition. School project, non-commercial.

## How it works (read first)

- Every scene is built and rendered in **Blender (Cycles)**. Scrolling plays the
  rendered frames forward and back. The browser loads no 3D model of a *scene* — the picture is
  always rendered frames. **Text is the exception** (owner, 2026-11-18): the caption layer may
  use real WebGL, so the words can be lit by real lights in a real 3D space.
- A thin **live web layer** sits on top: captions, diyo progress bar, cursor
  sparks, particle titles, sound.
- Scenes are separate Blender files joined by **hidden cuts**: each scene ends on
  a full-frame fill (fog, wing, dark doorway, gold light, a round plate) and the
  next starts from the same fill.

Detailed specs live in `docs/`. Read the relevant file before working on a part:

| Working on | Read |
| --- | --- |
| Story, scenes, captions, camera, transitions | `docs/SCENES.md` |
| Finding or importing models, textures, sound | `docs/ASSETS.md` |
| Blender scenes, rendering, frame export | `docs/PIPELINE.md` |
| The website itself | `docs/WEB.md` |
| Asset credits | `docs/CREDITS.md` (update every time an asset is added) |

## Non-negotiable rules

1. **Nepali only on screen.** All visible text is Nepali (Devanagari, Unicode).
   English exists only in code comments and docs.
2. **No letter-spacing on Devanagari.** It breaks the shirorekha (top line).
3. **Nepali digits** in UI text: १ २ ३ ४ ५, not 1 2 3 4 5.
4. **Free assets only.** CC0, CC BY, or explicitly free licences. Never pirated
   or cracked assets. Every CC BY asset gets a line in `docs/CREDITS.md`.
5. **Names:** यमराज (Yamaraj), बलि राजा (Bali Raja — he is a king), जमुना (Jamuna).
6. **Faces stay soft.** People are shown in silhouette, from behind, wide, or as
   hands in close-up with faces out of focus. Statues and animals may be sharp.
7. **One accent colour:** marigold `#F2A33A`. Each scene keeps its own muted palette.
8. **Captions:** max 2 short lines (~15 words). No label line — the marigold labels
   (`दिन १ · काग तिहार` and the rest) were dropped from every scene on 2026-11-18, so the day
   each scene belongs to is no longer named on screen. The diyo progress bar is now the only
   thing that can carry it.

## Blender MCP rules

- **Save before every MCP code call.** `execute_blender_code` cannot be undone.
  Use numbered saves: `s05_laxmi_v012.blend`.
- Work in **small steps**: one task, then take a viewport screenshot and check it.
- Telemetry must stay **off** (`DISABLE_TELEMETRY=true` in `.mcp.json`).
- Never delete objects, collections or files you did not create in this session
  without asking.
- Alignment, bone placement and weight painting are approximate from screenshots:
  ask the user to confirm before binding, applying modifiers or rendering a
  full sequence.
- Test-render 3–5 frames at low samples before any full scene render.

## Realism check (render-critic agent)

After every test render or full render of a scene, run the **`render-critic`** agent
(`.claude/agents/render-critic.md`) on a representative frame, e.g.
"render-critic: compare `renders/s00_enter/0048.png` — clay diyo burning at night, close-up".

It finds 2–3 real photographs of the same subject on the web, builds a side-by-side sheet
with `scripts/compare_render.py`, measures brightness/contrast/warmth/saturation/clipping, and
writes an element-by-element report with a Blender fix for each problem:

- `renders/<scene>/compare/<frame>_vs_ref.png`: side-by-side sheet (ours left, refs right)
- `renders/<scene>/compare/<frame>_vs_ref.md`: report + top 3 fixes
- `renders/<scene>/compare/refs/`: downloaded reference photos (comparison only, never assets)

Show the user the sheet and the top fixes; apply fixes only after the user agrees.
The agent never edits the .blend or runs Blender itself.

## Git / GitHub

- Repo: https://github.com/aashishdangal/tihar-katha (public since 2026-11-21; renamed from tihar).
- Live site: https://tihar-katha.pages.dev (Cloudflare Pages; deploy steps in README.md).
- **Claude must never appear as a contributor.** No `Co-Authored-By: Claude` lines,
  no "Generated with Claude Code" footers in commits, PRs or issues. Commits are
  authored by the user only.
- Only the latest `blender/scenes/<scene>.blend` is committed (Git LFS); numbered
  `_vNNN` saves and `refrences/` stay local.

## Tech stack

- Blender 4.x + Cycles (GPU: AMD RX 9070 XT, 16 GB VRAM, HIP backend)
- Blender MCP (`uvx blender-mcp`)
- Web: Vite + vanilla JS, GSAP ScrollTrigger, `<canvas>` image-sequence scrubbing
- Fonts: Mukta (Google Fonts, Unicode) for all text, titles included.
  AMS Gourav Bold was tried for the title and dropped (2026-11-11).
- ffmpeg + cwebp for frame encoding

## Repo layout

```
CLAUDE.md
README.md
.mcp.json
docs/            specs (SCENES, ASSETS, PIPELINE, WEB, CREDITS)
blender/
  scenes/        s00_enter.blend … s08_finale.blend
  assets/        downloaded models, textures, HDRIs   (git-ignored)
renders/         raw PNG/EXR frames per scene          (git-ignored)
web/
  index.html
  src/           main.js, scroll.js, captions.js, hud.js, sparks.js, styles.css
  public/frames/ encoded WebP sequences per scene
  public/audio/
scripts/         encode_frames.sh, check_budget.js
```

## Naming

- Scenes: `s00_enter`, `s01_hero`, `s02_legend`, `s03_kaag`, `s04_kukur`,
  `s05_laxmi`, `s06_govardhan`, `s07_bhaitika`, `s08_finale`
- Frames: `renders/s03_kaag/0001.png` → `web/public/frames/s03_kaag/0001.webp`
- Blender objects: `S05_Laxmi_Statue`, `S05_Diyo_Inst`, `CAM_S05`

## Commands

```
cd web && npm install && npm run dev      # local site
bash scripts/encode_frames.sh s05_laxmi   # PNG → WebP (desktop + mobile)
node scripts/check_budget.js              # warn if any scene exceeds its MB budget
python scripts/compare_render.py <render.png> <ref1> [ref2 ...] --out <sheet.png>   # side-by-side + stats
blender.exe <file.blend> --python scripts/blender_start_mcp.py   # open Blender and start the MCP server
```

## Open items

- Submission deadline: **2026-11-21, 23:59** (moved on 2026-11-19; was 2026-11-18, told
  2026-11-11). Plan scenes and renders around it.
- Captions need a native-speaker proofread before launch.
