import "./styles.css";
import scenes from "./scenes.json";
import { FrameSequence } from "./frames.js";
import { Stage } from "./stage.js";
import { initGate } from "./gate.js";
import { initSoundToggle } from "./sound.js";
import { initAudio, setPlace } from "./audio.js";
import { initStory } from "./story.js";

const s0 = scenes.find((s) => s.id === "s00_enter");
const sb = scenes.find((s) => s.id === "s00_blowout");
const storyScenes = scenes.filter((s) => s.beats); // s01_hero, s02_legend, … in story order
const stage = new Stage(document.getElementById("stage"));
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
const pickSet = () => (window.innerWidth / window.innerHeight <= 1 ? "m" : "d"); // portrait -> mobile frames

const CROSSFADE_MS = 150; // loop frame -> blow-out frame 1 (both open on the same flame pose)
const DECODE_BUDGET = 2; // WEB.md: never decode more than 2 frames per animation frame
const BLOW_WAIT_MS = 2000; // if the blow-out isn't loaded by then, fall back to a fade
const DEBUG = new URLSearchParams(location.search).has("debug"); // ?debug: log blow-out ticks
if (DEBUG) window.__blowLog = [];

let set = null;
let loop = null; // FrameSequence, s00_enter (96-frame loop)
let blow = null; // FrameSequence, s00_blowout (72 frames, the hidden cut into Scene 1)
let phase = "loop"; // loop -> blow -> done
let lastLoopBmp = null;
let blowT0 = 0;
let blowDone = null; // resolves when the blow-out has played
let blowAsked = 0;
let onBlowFrame = null; // page-side wind (gate.js), driven by the blow-out clock
const t0 = performance.now();

function useSet(next) {
  if (next === set) return;
  loop?.close();
  blow?.close();
  set = next;
  loop = new FrameSequence({ id: s0.id, count: s0.frames, set });
  blow = new FrameSequence({ id: sb.id, count: sb.frames, set, maxDecoded: 16 });
  // the loop first; then the blow-out (mostly dark frames, small); then the story scenes
  loop.load().then(() => blow.load()).then(() => story.preload());
}

function markReady() {
  document.body.classList.add("is-ready");
}

function decodeAhead(sequence, from, n, loopIt, budget) {
  for (let k = 0; k < n && budget > 0; k++) {
    const i = loopIt ? (from + k) % sequence.count : from + k;
    if (i < sequence.count && sequence.decode(i)) budget--;
  }
  return budget;
}

function tick(now) {
  if (phase === "done") return;

  if (phase === "loop") {
    // Scene 0 loops at its own frame rate; reduced motion holds the first frame
    const i = reduce.matches ? 0 : Math.floor(((now - t0) / 1000) * s0.fps) % s0.frames;
    let budget = decodeAhead(loop, i, 6, true, DECODE_BUDGET);
    decodeAhead(blow, 0, 4, false, budget); // keep the first blow-out frames ready for the click
    const bmp = loop.nearest(i, true);
    if (bmp) {
      stage.draw(bmp, s0.focus[set]);
      lastLoopBmp = bmp;
      markReady();
    }
    loop.evict(i, true);
    setPlace(s0.id, i + 1);
  } else {
    // blow-out: starts once its first frame is decoded, then plays in real time
    if (!blowT0) {
      blow.decode(0);
      if (blow.bitmaps.has(0)) blowT0 = now;
      else if (now - blowAsked > BLOW_WAIT_MS) {
        // frames not here in time (slow network): fade the last loop frame to black instead
        const a = Math.max(0, 1 - (now - blowAsked - BLOW_WAIT_MS) / 600);
        stage.ctx.fillStyle = "#000";
        stage.ctx.fillRect(0, 0, stage.canvas.width, stage.canvas.height);
        if (lastLoopBmp && a > 0) stage.draw(lastLoopBmp, s0.focus[set], a);
        if (a === 0) {
          phase = "done";
          loop.close();
          blow.close();
          blowDone(false);
          return;
        }
      } else if (lastLoopBmp) stage.draw(lastLoopBmp, s0.focus[set]);
    }
    if (blowT0) {
      const t = now - blowT0;
      const j = Math.min(sb.frames - 1, Math.floor((t / 1000) * sb.fps));
      decodeAhead(blow, j, 8, false, DECODE_BUDGET);
      const bmp = blow.nearest(j);
      const xf = Math.min(1, t / CROSSFADE_MS);
      if (xf < 1 && lastLoopBmp) stage.draw(lastLoopBmp, s0.focus[set]);
      if (bmp) stage.draw(bmp, sb.focus[set], xf);
      onBlowFrame?.((t / 1000) * sb.fps);
      setPlace(sb.id, (t / 1000) * sb.fps + 1);
      if (DEBUG) window.__blowLog.push([Math.round(now - blowAsked), +((t / 1000) * sb.fps).toFixed(2), j, !!bmp]);
      blow.evict(j);
      if (t > (sb.frames / sb.fps) * 1000 + 120) {
        phase = "done";
        loop.close();
        blow.close();
        blowDone(true);
        return;
      }
    }
  }
  requestAnimationFrame(tick);
}

/** Play the blow-out from wherever the loop is. onFrame(k) gets the current (fractional)
 *  blow-out frame every tick, so page animations share its clock. Resolves true on the last
 *  (black) frame, or false if the frames were late and it fell back to a fade. */
function playBlowout(onFrame) {
  if (phase !== "loop") return Promise.resolve(false);
  phase = "blow";
  onBlowFrame = onFrame;
  blowAsked = performance.now();
  return new Promise((resolve) => (blowDone = resolve));
}

const story = initStory({ stage, scenes: storyScenes, pickSet, reduceMotion: () => reduce.matches });
useSet(pickSet());
requestAnimationFrame(tick);
setTimeout(markReady, 1500); // show the gate text even if frames are slow

window.addEventListener("resize", () => {
  stage.resize();
  if (phase === "loop") useSet(pickSet());
});

initSoundToggle();
initAudio();

initGate({
  reduceMotion: () => reduce.matches,
  playBlowout,
  onEntered: () => {
    if (phase !== "done") {
      phase = "done";
      loop.close();
      blow.close();
    }
    story.start();
  },
});
