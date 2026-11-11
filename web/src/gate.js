// Scene 0 enter gate: two choices (with / without sound), then the hidden cut into
// Scene 1: the flame "swells to warm white" (SCENES.md). Scene 1 must start on --cream.

import { setSound } from "./sound.js";

const SWELL_PX = 200; // element size; the solid cream core is the inner 35% of its radius
const CORE = 0.35;

export function initGate({ flamePoint, reduceMotion, onEntered }) {
  const gate = document.getElementById("gate");
  const swell = document.getElementById("swell");
  const story = document.getElementById("story");
  let leaving = false;

  async function enter(withSound) {
    if (leaving) return;
    leaving = true;
    setSound(withSound);
    gate.inert = true;
    gate.classList.add("is-leaving");

    if (reduceMotion()) {
      swell.classList.add("swell--fade");
      await swell.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 600, fill: "forwards" }).finished;
    } else {
      const [fx, fy] = flamePoint();
      const W = window.innerWidth;
      const H = window.innerHeight;
      const far = Math.max(Math.hypot(fx, fy), Math.hypot(W - fx, fy), Math.hypot(fx, H - fy), Math.hypot(W - fx, H - fy));
      const end = far / ((SWELL_PX / 2) * CORE);
      swell.style.left = `${fx - SWELL_PX / 2}px`;
      swell.style.top = `${fy - SWELL_PX / 2}px`;
      await swell.animate(
        [
          { transform: "scale(0.12)", opacity: 0 },
          { transform: "scale(0.5)", opacity: 1, offset: 0.2 },
          { transform: `scale(${end})`, opacity: 1 },
        ],
        { duration: 1900, easing: "cubic-bezier(.55,0,.8,.3)", fill: "forwards" }
      ).finished;
    }

    document.body.classList.add("is-entered");
    gate.hidden = true;
    onEntered?.();
    story.hidden = false;
    story.focus({ preventScroll: true });
  }

  gate.querySelector('[data-enter="sound"]').addEventListener("click", () => enter(true));
  gate.querySelector('[data-enter="silent"]').addEventListener("click", () => enter(false));
}
