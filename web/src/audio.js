// Sound engine (Web Audio). Each scene's mix lives in scenes.json "sound":
//   beds:   loops whose gain follows the frame on screen: { src, gain: [[frame, gain], ...] }
//           `onlyMoving: true` also ties it to the scroll: silent while the picture is still
//   cues:   one-shots fired when the frame passes `at` going forward: { src, at, gain, rate }
//   motion: gain of the wind that follows how fast the frames move (scroll = camera move)
// Sources are files in /audio/<src>.mp3 (built by scripts/build_audio.py, credits in
// CREDITS.md) or generated here: "peck", "mala" (the garland going on), "tail_thump".
// A source whose file is missing is skipped, not an error: s06's "deusi_loop" and
// "madal_loop" are wired in scenes.json and stay silent until those files are added.
// The page calls setPlace(sceneId, frame) on every animation frame. Audio can only start after
// a user gesture: the first pointer/key press anywhere (the gate's सुरु) unlocks it.

import scenes from "./scenes.json";
import { isSoundOn } from "./sound.js";

const BASE = `${import.meta.env.BASE_URL}audio/`;
// "crackle" is kept but unused: oil wicks do not crackle (owner, 2026-11-19), so every
// lamp in the site now uses the recorded "flame_loop" flutter instead. "blow", "breath_in"
// "wings" and "dog_breath" are owner-supplied recordings (2026-11-19); the generated
// versions they replaced have been removed.
const SYNTH = new Set(["crackle", "peck", "mala", "tail_thump"]);
const SCENE_FADE_S = 0.6; // crossfade between scenes
const MOTION_FULL = 40; // frames per second of scroll that give full motion wind
const MASTER = 0.9;

const mixes = Object.fromEntries(scenes.filter((s) => s.sound).map((s) => [s.id, s.sound]));

let ctx = null;
let master = null;
let motionGain = null;
const buffers = new Map(); // src -> AudioBuffer | Promise
const scenesOn = new Map(); // sceneId -> { gain, beds: Map(src -> {gain}), last }
let current = null;
let lastFrame = null;
let lastT = 0;
let motion = 0;
// 1 while the scroll is actually moving the frames, falling to 0 about half a second after it
// stops. Beds marked `onlyMoving` follow it: a dog panting or anything else that belongs to the
// action goes quiet when the picture is still, and only the background is left (owner,
// 2026-11-19). It rises fast and falls slowly, so a pause between flicks does not chop it.
let moving = 0;

/** piecewise-linear gain from [[frame, gain], ...] (holds the ends) */
function keyed(keys, f) {
  if (typeof keys === "number") return keys;
  if (f <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [f1, g1] = keys[i];
    if (f <= f1) {
      const [f0, g0] = keys[i - 1];
      return g0 + ((g1 - g0) * (f - f0)) / Math.max(1e-6, f1 - f0);
    }
  }
  return keys[keys.length - 1][1];
}

// ---- generated sources --------------------------------------------------------------------
function noise(n, seed = 1) {
  let s = seed;
  const a = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    s = (s * 16807) % 2147483647;
    a[i] = (s / 2147483647) * 2 - 1;
  }
  return a;
}

function synth(src) {
  const sr = ctx.sampleRate;
  if (src === "crackle") {
    // UNUSED since 2026-11-19 (see SYNTH above): a wood fire, not an oil wick
    // a small oil flame: soft low hiss + sparse pops, 6 s loop
    const n = sr * 6;
    const buf = ctx.createBuffer(1, n, sr);
    const d = buf.getChannelData(0);
    const w = noise(n, 7);
    let lp = 0;
    for (let i = 0; i < n; i++) {
      lp += (w[i] - lp) * 0.02;
      d[i] = lp * 0.25;
    }
    const r = noise(400, 11);
    for (let k = 0; k < 400; k++) {
      if (r[k] < 0.55) continue; // ~90 pops
      const at = Math.floor(((r[(k * 7) % 400] + 1) / 2) * (n - 800));
      const amp = 0.25 + 0.5 * Math.abs(r[(k * 13) % 400]);
      const len = 40 + Math.floor(Math.abs(r[(k * 3) % 400]) * 300);
      const z = noise(len, k + 3);
      for (let j = 0; j < len; j++) d[at + j] += z[j] * amp * Math.exp(-j / (len / 4));
    }
    return buf;
  }
  if (src === "peck") {
    // beak on fried dough and leaf: a dry tick with a soft body
    const n = Math.floor(sr * 0.18);
    const buf = ctx.createBuffer(1, n, sr);
    const d = buf.getChannelData(0);
    const z = noise(n, 9);
    for (let i = 0; i < n; i++) {
      const tick = z[i] * Math.exp(-i / (sr * 0.003));
      const body = Math.sin((2 * Math.PI * 180 * i) / sr) * Math.exp(-i / (sr * 0.02)) * 0.4;
      const crumb = i > sr * 0.02 ? z[(i * 3) % n] * 0.12 * Math.exp(-(i - sr * 0.02) / (sr * 0.04)) : 0;
      d[i] = tick + body + crumb;
    }
    return buf;
  }
  if (src === "mala") {
    // The marigold mala going over the dog's head (owner, 2026-11-19). A garland on fur is not
    // an impact: it is a handful of dry flower heads brushing past each other, the thread
    // settling, and then the weight of it arriving — a soft low push, no click anywhere.
    const n = Math.floor(sr * 0.5);
    const buf = ctx.createBuffer(1, n, sr);
    const d = buf.getChannelData(0);
    const z = noise(n, 41);
    // a scatter of small dry rustles: the flower heads, not all landing together
    const heads = [0.0, 0.028, 0.049, 0.081, 0.104, 0.142, 0.171, 0.216, 0.262];
    for (const t0 of heads) {
      const at = Math.floor(t0 * sr);
      const len = Math.floor(sr * (0.05 + 0.05 * ((t0 * 37) % 1)));
      const lp = [0, 0];
      for (let j = 0; at + j < n && j < len; j++) {
        let v = z[(at + j * 2) % n];
        for (let q = 0; q < 2; q++) {
          lp[q] += (v - lp[q]) * 0.11; // dry and mid: petals, never a tick
          v = lp[q];
        }
        d[at + j] += v * 2.4 * Math.sin((Math.PI * j) / len) ** 2;
      }
    }
    // the weight settling on the neck, under everything
    for (let i = 0; i < n; i++) {
      const t = i / sr;
      d[i] += Math.sin(2 * Math.PI * 96 * t) * Math.exp(-t / 0.05) * 0.1 * (t > 0.06 ? 1 : t / 0.06);
    }
    return buf;
  }
  if (src === "tail_thump") {
    // A tail hitting packed earth: a low body at 68 Hz with almost no attack, and dust filtered
    // down to nothing bright. Centroid ~190 Hz — a thud, never a click.
    const n = Math.floor(sr * 0.4);
    const buf = ctx.createBuffer(1, n, sr);
    const d = buf.getChannelData(0);
    const z = noise(n, 37);
    const lp = [0, 0, 0];
    for (let i = 0; i < n; i++) {
      const t = i / sr;
      const body = Math.sin(2 * Math.PI * 68 * t) * Math.exp(-t / 0.045) * 0.6;
      let v = z[i];
      for (let q = 0; q < 3; q++) {
        lp[q] += (v - lp[q]) * 0.03;
        v = lp[q];
      }
      d[i] = body + v * Math.exp(-t / 0.07) * 2.2;
    }
    return buf;
  }
  return null;
}

function buffer(src) {
  if (buffers.has(src)) return buffers.get(src);
  if (SYNTH.has(src)) {
    const b = synth(src);
    buffers.set(src, b);
    return b;
  }
  const p = fetch(`${BASE}${src}.mp3`)
    .then((r) => r.arrayBuffer())
    .then((a) => ctx.decodeAudioData(a))
    .then((b) => {
      buffers.set(src, b);
      return b;
    })
    .catch(() => {
      buffers.set(src, null);
      return null;
    });
  buffers.set(src, p);
  return p;
}

function play(src, { gain = 1, rate = 1, loop = false, dest = master } = {}) {
  const b = buffers.get(src);
  if (!(b instanceof AudioBuffer)) {
    // not loaded yet: load, and start a loop when it arrives (a late one-shot is skipped)
    if (loop) Promise.resolve(buffer(src)).then((bb) => bb && play(src, { gain, rate, loop, dest }));
    else buffer(src);
    return null;
  }
  const s = ctx.createBufferSource();
  s.buffer = b;
  s.loop = loop;
  s.playbackRate.value = rate;
  const g = ctx.createGain();
  g.gain.value = gain;
  s.connect(g).connect(dest);
  // loops start at a random point so repeated beds don't phase
  s.start(0, loop ? Math.random() * b.duration : 0);
  return { s, g };
}

// ---- scene mixes --------------------------------------------------------------------------
function sceneState(id) {
  if (scenesOn.has(id)) return scenesOn.get(id);
  const mix = mixes[id];
  const gain = ctx.createGain();
  gain.gain.value = 0;
  gain.connect(master);
  const st = { gain, beds: new Map(), last: null, mix };
  for (const bed of mix?.beds ?? []) {
    const bg = ctx.createGain();
    bg.gain.value = 0;
    bg.connect(gain);
    st.beds.set(bed, bg);
    Promise.resolve(buffer(bed.src)).then(() => play(bed.src, { loop: true, rate: bed.rate ?? 1, dest: bg }));
  }
  for (const cue of mix?.cues ?? []) buffer(cue.src); // preload
  scenesOn.set(id, st);
  return st;
}

function unlock() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = isSoundOn() ? MASTER : 0;
    master.connect(ctx.destination);
    // Motion wind: the wind bed, its level set by the scroll speed. It whistled (owner,
    // 2026-11-19). 88 % of this recording's energy sits in 420-1800 Hz — that band *is* the
    // whistle — and the send used to pitch it up to 1.15, which moved it higher still. So it is
    // now pitched down to 0.8 and banded to 140-1500 Hz: the same wind, heard as a rush of air
    // rather than a note. (The old 420 Hz high-pass was not the cause: it removed 3 % of it.)
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 140;
    const lpf = ctx.createBiquadFilter();
    lpf.type = "lowpass";
    lpf.frequency.value = 1500;
    motionGain = ctx.createGain();
    motionGain.gain.value = 0;
    motionGain.connect(hp).connect(lpf).connect(master);
    Promise.resolve(buffer("wind_loop")).then(() => play("wind_loop", { loop: true, rate: 0.8, dest: motionGain }));
    buffer("breath_in"); // the gate control needs it the moment the first press lands
    if (current) sceneState(current);
    if (new URLSearchParams(location.search).has("debug")) window.__audio = { ctx, scenesOn, mixes, motion: () => motion };
  }
  if (ctx.state === "suspended" && isSoundOn()) ctx.resume();
}

/** Called every animation frame with the scene on screen and its (fractional) frame. */
export function setPlace(id, frame) {
  const now = performance.now();
  const dt = lastT ? Math.min(0.1, (now - lastT) / 1000) : 1 / 60;
  lastT = now;
  const moved = id === current && lastFrame != null ? frame - lastFrame : 0;
  if (id !== current) current = id;
  lastFrame = frame;
  if (!ctx || ctx.state !== "running") return;

  const t = ctx.currentTime;
  const st = sceneState(id);
  // scene crossfade: the one in view up, the others down (and dropped once silent)
  for (const [sid, s] of scenesOn) {
    const target = sid === id ? 1 : 0;
    s.gain.gain.setTargetAtTime(target, t, SCENE_FADE_S / 3);
  }
  for (const [bed, g] of st.beds) {
    const want = keyed(bed.gain, frame) * (bed.onlyMoving ? moving : 1);
    g.gain.setTargetAtTime(want, t, 0.08);
  }

  // one-shots: fire when the frame passes `at` moving forward (not on big jumps)
  if (st.last != null && frame > st.last && frame - st.last < 12) {
    for (const cue of st.mix?.cues ?? []) {
      if (st.last < cue.at && frame >= cue.at) play(cue.src, { gain: cue.gain ?? 1, rate: cue.rate ?? 1, dest: st.gain });
    }
  }
  st.last = frame;

  // is the picture moving at all? (a fractional frame still counts: the smoothing creeps)
  const stirred = Math.abs(moved) > 0.004 ? 1 : 0;
  moving += (stirred - moving) * Math.min(1, dt * (stirred ? 14 : 1.8));

  // motion wind follows the speed of the frames (smoothed), scaled per scene
  const speed = Math.abs(moved) / dt;
  motion += (Math.min(1, speed / MOTION_FULL) - motion) * Math.min(1, dt * 4);
  motionGain.gain.setTargetAtTime(motion * (st.mix?.motion ?? 0), t, 0.1);
}

// ---- the gate's breath (web/src/breath.js) -------------------------------------------------
// Press and hold सुरु and the boy breathes in; the blow cuts it off. This sits outside the scene
// mixes because it belongs to the control rather than to a frame, and it is the same gesture
// that unlocks audio — so it unlocks first and plays on whatever is ready.
let breathNode = null;

export function playBreath(gain = 0.55) {
  unlock();
  if (!ctx || ctx.state !== "running") return;
  stopBreath(0.02);
  breathNode = play("breath_in", { gain, dest: master });
}

/** Stop the breath: the blow cuts it short, or it is let back out. */
export function stopBreath(fadeS = 0.12) {
  const node = breathNode;
  breathNode = null;
  if (!node || !ctx) return;
  const t = ctx.currentTime;
  node.g.gain.cancelScheduledValues(t);
  node.g.gain.setTargetAtTime(0, t, Math.max(0.01, fadeS) / 3);
  try {
    node.s.stop(t + fadeS + 0.05);
  } catch {
    /* already stopped */
  }
}

export function initAudio() {
  const go = () => unlock();
  window.addEventListener("pointerdown", go, { passive: true });
  window.addEventListener("keydown", go);
  window.addEventListener("touchstart", go, { passive: true });
  window.addEventListener("tihar:sound", (e) => {
    if (!ctx) return;
    const on = e.detail.on;
    master.gain.setTargetAtTime(on ? MASTER : 0, ctx.currentTime, 0.15);
    if (on && ctx.state === "suspended") ctx.resume();
  });
}
