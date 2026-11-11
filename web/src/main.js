import "./styles.css";
import scenes from "./scenes.json";
import { FrameSequence } from "./frames.js";
import { Stage } from "./stage.js";
import { initGate } from "./gate.js";

const s0 = scenes.find((s) => s.id === "s00_enter");
const stage = new Stage(document.getElementById("stage"));
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
const pickSet = () => (window.innerWidth / window.innerHeight <= 1 ? "m" : "d"); // portrait -> mobile frames

let seq = null;
let set = null;
let running = true;
const t0 = performance.now();

function useSet(next) {
  if (next === set) return;
  seq?.close();
  set = next;
  seq = new FrameSequence({ id: s0.id, count: s0.frames, set });
  seq.load();
}

function markReady() {
  document.body.classList.add("is-ready");
}

// Scene 0 loops at its own frame rate; reduced motion holds the first frame.
function tick(now) {
  if (!running) return;
  const i = reduce.matches ? 0 : Math.floor(((now - t0) / 1000) * s0.fps) % s0.frames;
  let budget = 2; // WEB.md: never decode more than 2 frames per animation frame
  for (let k = 0; k < 6 && budget > 0; k++) if (seq.decode((i + k) % s0.frames)) budget--;
  const bmp = seq.nearest(i, true);
  if (bmp) {
    stage.draw(bmp, s0.focus[set]);
    markReady();
  }
  seq.evict(i, true);
  requestAnimationFrame(tick);
}

useSet(pickSet());
requestAnimationFrame(tick);
setTimeout(markReady, 1500); // show the gate text even if frames are slow

window.addEventListener("resize", () => {
  stage.resize();
  useSet(pickSet());
});

initGate({
  flamePoint: () => stage.toScreen(s0.points.flame[set]),
  reduceMotion: () => reduce.matches,
  onEntered: () => {
    running = false;
    seq.close();
  },
});
