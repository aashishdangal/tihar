# तिहार — उज्यालोको कथा (The Road of Lights)

A realistic, scroll-driven 3D story of why Tihar is celebrated in Nepal, told through
the folk tale of **बलि राजा** and his sister **जमुना**, and the five days of the festival.
Entry for the **KUCC Tihar-Chhath Web UI Design Competition**. School project, non-commercial.

**Live site: https://tihar-katha.pages.dev**

## How to view it

1. Open the link with **sound on**. On an iPhone, turn the silent switch off: Chrome on
   iPhone mutes the site in silent mode.
2. **Press and hold सुरु** until the ring fills, then let go. The boy blows the diyo out
   and the story begins.
3. **Scroll** (or swipe, or use the arrow / Page keys) to move through the story. The
   scroll stops briefly at each caption so it can be read.
4. At the end, **फेरि हेर्नुहोस्** starts again from the first scene.

Works on desktop, laptop and phone (portrait frames for phones, a lighter set for
low-end laptops).

## The story

| # | Scene | What you see |
| --- | --- | --- |
| 0 | प्रवेश | One clay diyo burning in the dark; the wind blows it out |
| 1 | उपत्यका | Kathmandu valley at night, lit with Tihar lights, under the stars |
| 2 | कथा · काग तिहार | A crow, a carved window, the dying king; out through the door onto a morning kausi where the crow eats |
| 4 | कुकुर तिहार | Down through the old floor to a courtyard; a dog gets its mala and tika |
| 5 | गाई तिहार · लक्ष्मी पूजा | The cow where the dog sat; night falls, diyos are lit, Laxmi's footsteps lead to the puja |
| 6 | गोवर्धन पूजा · देउसी | A Deusi group seen from behind, the offering plate at the centre |
| 7 | भाइटीका | The thali filled one item at a time; Jamuna's tika and Yamaraj, as shadows on the wall |
| 8 | शुभ तिहार | A golden burst into the evening valley from the hill, the flag and a kite, शुभ तिहार in sparks |

Day 1 (Kaag Tihar) is part of scene 2, so there is no separate scene 3. The full scene
spec is in [`SCENES.md`](SCENES.md).

## How it works

- Every scene is built and rendered in **Blender (Cycles)**. Scrolling plays the rendered
  frames forward and back on a `<canvas>`. No 3D model of a scene is loaded in the
  browser: the picture is always rendered frames.
- Scenes are joined by **hidden cuts**: each one ends on a full-frame fill (black, the
  crow's feathers, a doorway, gold light, a plate) and the next starts from it.
- A thin **live layer** sits on top: Nepali captions lit in 3D (Three.js), the five-moon
  progress bar, sparks, the finale firework and title, and a Web Audio sound mix that
  follows the frame on screen.
- All visible text is Nepali (Devanagari, Mukta font) with Nepali digits.

### Frames

About 1,200 rendered frames at 1920×1080, three sets per scene:

| Set | Used for | Format |
| --- | --- | --- |
| `d/` | Desktop, landscape | AVIF 4:4:4 (scenes 1–7), WebP (scene 0) |
| `m/` | Phones, portrait 720×1280 crop | AVIF (scenes 1–7), WebP (scene 0) |
| `l/` | Low-end laptops, 1280×720 | WebP |

Frames load scene by scene in story order, with the light set first so scrolling works
straight away.

## Tech

- Blender 4.x + Cycles (GPU, HIP), Blender MCP
- Vite + vanilla JS, GSAP ScrollTrigger, Three.js (captions and finale)
- Web Audio API for the sound mix
- ffmpeg, cwebp, Pillow (AVIF) for frame encoding
- Hosted on Cloudflare Pages

## Run it locally

```
cd web
npm install
npm run dev            # local site at http://localhost:5173
npm run build          # production build in web/dist
```

Add `?debug` to the address to show an on-screen audio readout (useful on phones).

## Deploy

```
cd web
npm run build
npx wrangler pages deploy dist --project-name tihar-katha --branch main
```

Needs a one-time `npx wrangler login`. Use `wrangler pages deploy` only: plain
`wrangler deploy` turns the project into a Worker and rewrites `package.json`.

## Encoding frames

```
python scripts/encode_frames.py s05_laxmi    # renders/<scene>/*.png -> web/public/frames/<scene>/{d,m,l}
node scripts/check_budget.js                 # warns if a scene goes over its per-frame size budget
python scripts/encode_compare.py s04_kukur 104   # render vs WebP vs AVIF, side by side
```

Per-scene options (mobile framing, quality, `"fmt": "avif"`) are in
`scripts/mobile_framing.json`.

## Repo layout

```
web/            the website (index.html, src/, public/frames, public/audio)
scripts/        Blender, render, encode and audio scripts
blender/        scene .blend files (Git LFS); downloaded assets are not committed
renders/        raw rendered frames (not committed)
*.md            specs: SCENES, ASSETS, PIPELINE, WEB, CREDITS
```

## Documentation

- Story, scenes, captions, camera: [`SCENES.md`](SCENES.md)
- Assets and licences: [`ASSETS.md`](ASSETS.md), [`CREDITS.md`](CREDITS.md)
- Render pipeline: [`PIPELINE.md`](PIPELINE.md)
- Website: [`WEB.md`](WEB.md)
- Project rules: [`CLAUDE.md`](CLAUDE.md)

## Credits

Only free assets are used (CC0, CC BY, or explicitly free licences). Every model, texture,
HDRI and sound is listed with its author and licence in [`CREDITS.md`](CREDITS.md).

The story follows one folk retelling of Bhai Tika; another account tells of Yamaraj
visiting his sister Yamuna.
