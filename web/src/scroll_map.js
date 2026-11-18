// Scroll <-> frame map for one scene.
//
// A scene is laid out as segments: "run" segments play at the scene's vhPerFrame, and each beat's
// hold is stretched by its extraVh so a caption can be read. Laid out literally, that is a
// piecewise-linear map, so the scroll speed changes in a STEP at every hold edge: in s02 the same
// wheel gesture moved 3x fewer frames the moment it crossed frame 182. That step is what reads as
// "some frames go too fast, some too slow".
//
// So the speed (vh per frame) is smoothed across each boundary with a symmetric smoothstep ramp.
// The ramp is symmetric, so the area under the speed curve is unchanged: every segment still
// occupies exactly the scroll length it was authored with, the total is identical, and holds and
// caption ranges stay where they were. Only the discontinuity goes.
//
// The smoothed speed has no closed-form inverse, so distance is integrated once onto a fine grid
// at build time and both directions are table lookups.

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const smoothstep = (t) => t * t * (3 - 2 * t);

export const RAMP_FRAMES = 6; // half-width of the speed ramp either side of a boundary
const STEP = 0.25; // integration grid, in frames

/** Segments of a scene, in frames, with the speed (vh/frame) each was authored at. */
function segments(scene) {
  const v = scene.vhPerFrame;
  const segs = [];
  let f = scene.intro ? scene.intro[1] : 1;
  for (const b of scene.beats) {
    const [h0, h1] = b.hold;
    if (h0 > f) segs.push({ f0: f, f1: h0, len: (h0 - f) * v });
    segs.push({ f0: h0, f1: h1, len: (h1 - h0) * v + b.extraVh, hold: true });
    f = h1;
  }
  if (scene.frames > f) segs.push({ f0: f, f1: scene.frames, len: (scene.frames - f) * v });
  for (const s of segs) s.speed = s.len / (s.f1 - s.f0);
  return segs;
}

/** Speed (vh/frame) at frame f: each segment's own speed, ramped across the boundaries. */
function speedFn(segs, ramp) {
  // a boundary may not eat more than half of either neighbour, or ramps would overlap
  const edges = [];
  for (let i = 1; i < segs.length; i++) {
    const a = segs[i - 1];
    const b = segs[i];
    const r = Math.min(ramp, (a.f1 - a.f0) / 2, (b.f1 - b.f0) / 2);
    if (r > 0) edges.push({ at: a.f1, r, from: a.speed, to: b.speed });
  }
  return (f) => {
    for (const e of edges) {
      if (f > e.at - e.r && f < e.at + e.r) {
        return e.from + (e.to - e.from) * smoothstep((f - (e.at - e.r)) / (2 * e.r));
      }
    }
    for (const s of segs) if (f <= s.f1) return s.speed;
    return segs[segs.length - 1].speed;
  };
}

/** Scroll layout of one scene: a smooth, monotonic map between scroll position and frame.
 *  `ramp` is the half-width in frames of the speed ramp at each boundary (0 = old step map). */
export function layout(scene, ramp = RAMP_FRAMES) {
  const segs = segments(scene);
  const f0 = segs[0].f0;
  const fN = scene.frames;
  const speed = speedFn(segs, ramp);

  // cumulative scroll distance at f0, f0+STEP, ... fN (trapezoid; the grid is far finer than the ramp)
  const n = Math.max(1, Math.ceil((fN - f0) / STEP));
  const dist = new Float64Array(n + 1);
  let prev = speed(f0);
  for (let i = 1; i <= n; i++) {
    const f = f0 + (i * (fN - f0)) / n;
    const s = speed(f);
    dist[i] = dist[i - 1] + ((prev + s) / 2) * ((fN - f0) / n);
    prev = s;
  }
  const total = dist[n];
  const frameOf = (i) => f0 + (i * (fN - f0)) / n;

  return {
    totalVh: total,
    segments: segs,
    speedAt: speed,
    /** progress 0..1 -> frame (fractional) */
    frameAt(p) {
      const d = clamp(p, 0, 1) * total;
      let lo = 0;
      let hi = n;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (dist[mid] < d) lo = mid + 1;
        else hi = mid;
      }
      if (lo === 0) return f0;
      const d0 = dist[lo - 1];
      const t = dist[lo] === d0 ? 0 : (d - d0) / (dist[lo] - d0);
      return frameOf(lo - 1) + t * (fN - f0) / n;
    },
    /** frame -> progress 0..1 */
    progressAt(f) {
      const x = clamp((f - f0) / ((fN - f0) / n), 0, n);
      const i = Math.floor(x);
      if (i >= n) return 1;
      return (dist[i] + (dist[i + 1] - dist[i]) * (x - i)) / total;
    },
  };
}
