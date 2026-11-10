# WEB.md — The scroll site

## Architecture

- Vite + vanilla JS. No framework.
- One full-screen `<canvas>` draws the current frame of the current scene.
- GSAP ScrollTrigger maps scroll position → (scene, frame). Each scene gets a
  scroll length proportional to its frame count, plus extra length at each
  `PAUSE` marker so the caption can be read.
- `web/src/scenes.json` lists each scene: id, frame count, pause frames,
  caption keys, which progress diyo lights, sound file.
- `<html lang="ne">`.

## Loading

- Scene 0 (enter gate) loads first; the loading % covers Scene 1 and the first
  half of Scene 2.
- After that, preload one scene ahead of the viewer. Release frames two scenes
  behind from memory.
- Use `createImageBitmap` for decoding. Pick `d/` or `m/` frames by viewport
  aspect ratio (portrait → mobile set).
- If a frame isn't loaded yet, keep showing the nearest loaded frame.

## Live layer (DOM over the canvas)

| Element | Position | Notes |
| --- | --- | --- |
| Wordmark तिहार | top-left | Mukta 800, 24px |
| अध्यायहरू button | top-right | opens chapter menu |
| आवाज बन्द / आवाज खुला toggle | bottom-left | muted by default |
| Diyo progress bar | bottom-right | 5 SVG diyos: unlit / active / lit |
| Caption block | bottom-centre, max 600px | gold label 15px/800 + text 23px/600; fade in 400 ms, out 300 ms |
| Cursor sparks | canvas overlay | small marigold particles following the pointer; off on touch |
| Particle titles | Scenes 1 and 8 | "तिहार" and "शुभ तिहार" built from glyph outlines (SVG paths) |

Chapter menu items: कथा · दिन १ · काग तिहार · दिन २ · कुकुर तिहार ·
दिन ३ · गाई तिहार र लक्ष्मी पूजा · दिन ४ · गोवर्धन पूजा र देउसी · दिन ५ · भाइटीका.
Current chapter marked अहिले.

## Style tokens

```css
:root {
  --night: #0E1430;
  --marigold: #F2A33A;   /* the only accent */
  --cream: #FFF4E0;
  --muted: #CBBFA8;
  --vermilion: #B3202A;
  --makhamali: #7B2D6E;
  --caption-bg: rgba(8, 10, 24, 0.62);
  --font: "Mukta", system-ui, sans-serif;
}
```

- Never set `letter-spacing` on Devanagari text.
- Nepali digits in all UI text.
- Touch targets ≥ 44px. Visible focus rings on all controls.
- Respect `prefers-reduced-motion`: replace scrubbing with a crossfade between
  each scene's pause frames, and disable sparks.

## Accessibility

- Captions are real text (not baked into frames), so screen readers can read them.
- Each scene section has an `aria-label` with its chapter name.
- Canvas gets `role="img"` with a short Nepali description per scene.
- Keyboard: arrow keys / Page Down move between pause points.

## Performance targets

- First paint of the enter gate < 1.5 s on a mid-range phone.
- Scroll scrubbing at 60 fps on desktop; never decode more than 2 frames per
  animation frame.
