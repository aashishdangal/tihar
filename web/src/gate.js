// Scene 0 enter gate. The viewer blows the diyo out: press and hold सुरु and the boy in the
// dhaka topi breathes in; let go and it blows (breath.js). The rendered blow-out (s00_blowout,
// gust toward screen-right, the way the figure faces) plays, and the same wind carries the page's
// letters off. The page side is driven by the blow-out's own clock (setGust gets the current
// blow-out frame), using the render's gust curve, so text and flame move together.
// The cut ends on black; Scene 1 rises out of it.

import { initBreath } from "./breath.js";
import boySvg from "./assets/boy-head.svg?raw";

// The render's gust (scripts/s00_render_headless.py GUST): blow-out frame k -> flame lean (deg)
// and light multiplier. The flame is gone from frame 17.
const GUST = [
  [0, 0, 1.0], [3, 18, 1.25], [6, 34, 1.1], [8, 28, 0.95], [10, 40, 0.7],
  [12, 52, 0.45], [14, 60, 0.22], [15, 64, 0.12], [16, 68, 0.05], [17, 70, 0.0],
];
const MAX_LEAN = 70;
const WIND_X = 1; // the gust blows toward screen-right, the way the सुरु figure faces
// The wind reaches the page a little after the diyo, left to right (ति, हा, र). Values are
// blow-out frames; the flame dies at 17 (0.71 s), the letters are gone by 18 / 19.5 / 21.
const DELAY_HINT = 2;
const DELAY_FIRST_CHAR = 1;
const DELAY_PER_CHAR = 1.5;

/** gust strength 0..1 and light 0..1 at (fractional) blow-out frame k */
function gustAt(k) {
  if (k <= 0) return [0, 1];
  const last = GUST[GUST.length - 1];
  if (k >= last[0]) return [1, 0];
  let i = 0;
  while (GUST[i + 1][0] < k) i++;
  const [k0, a0, l0] = GUST[i];
  const [k1, a1, l1] = GUST[i + 1];
  const u = (k - k0) / (k1 - k0);
  return [(a0 + (a1 - a0) * u) / MAX_LEAN, Math.min(1, l0 + (l1 - l0) * u)];
}

/** Move one element with the wind: drift downwind and up a little, skew, blur, fade with the light. */
function blow(el, k, distance) {
  const [g, light] = gustAt(k);
  const x = WIND_X * Math.pow(g, 1.6) * distance;
  el.style.transform = `translate(${x.toFixed(1)}px, ${(-g * 14).toFixed(1)}px) skewX(${(-WIND_X * g * 12).toFixed(1)}deg)`;
  el.style.filter = `blur(${(g * g * 8).toFixed(2)}px)`;
  el.style.opacity = light.toFixed(3);
}

/** Wrap each grapheme cluster (ति · हा · र) in a span so the wind can take them one by one.
 *  Devanagari clusters are shaped on their own, so splitting at cluster edges keeps the glyphs;
 *  no letter-spacing is added (CLAUDE.md rule 2). */
function splitTitle(el) {
  const text = el.textContent.trim();
  const seg = new Intl.Segmenter("ne", { granularity: "grapheme" });
  el.setAttribute("aria-label", text);
  el.textContent = "";
  for (const { segment } of seg.segment(text)) {
    const span = document.createElement("span");
    span.className = "gate__ch";
    span.setAttribute("aria-hidden", "true");
    span.textContent = segment;
    el.append(span);
  }
}

export function initGate({ reduceMotion, playBlowout, onEntered }) {
  const gate = document.getElementById("gate");
  const story = document.getElementById("story");
  const stageEl = document.getElementById("stage");
  const breathBtn = gate.querySelector("[data-enter]");
  const hint = gate.querySelector(".breath__hint");
  const title = gate.querySelector(".gate__title");

  breathBtn.querySelector("[data-boy]").innerHTML = boySvg;
  if (typeof Intl !== "undefined" && Intl.Segmenter) splitTitle(title);
  const chars = [...title.querySelectorAll(".gate__ch")];
  if (!chars.length) chars.push(title);

  /** called by the player on every blow-out tick with the current (fractional) frame */
  function setGust(k) {
    blow(breathBtn, k - 2, 18); // the figure stays and fades as the light dies
    blow(hint, k - DELAY_HINT, 90);
    chars.forEach((el, i) => blow(el, k - DELAY_FIRST_CHAR - i * DELAY_PER_CHAR, 170));
  }

  async function enter() {
    gate.inert = true;
    if (reduceMotion()) {
      gate.classList.add("is-leaving");
      await stageEl.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 600, fill: "forwards" }).finished;
    } else {
      gate.classList.add("is-blown");
      // the figure blows, the diyo goes out; the page follows the blow-out's clock
      const played = await playBlowout(setGust);
      if (!played) gate.classList.add("is-leaving"); // frames were late: plain fade instead
    }

    document.body.classList.add("is-entered");
    gate.hidden = true;
    onEntered?.();
    story.hidden = false;
    story.focus({ preventScroll: true });
  }

  initBreath(breathBtn, { onBlow: enter });
}
