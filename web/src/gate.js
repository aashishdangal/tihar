// Scene 0 enter gate. Clicking सुरु starts the hidden cut into Scene 1 (SCENES.md): a gust
// blows the diyo out (rendered frames, s00_blowout) and the same wind carries the page's own
// light away: the wick flame under सुरु is snuffed and the letters of तिहार drift right and
// dissolve. The cut ends on black; Scene 1 rises out of it.

const WIND_MS = 1300; // longest page-side wind animation (CSS); the blow-out itself is 3 s

/** Wrap each grapheme cluster (ति · हा · र) in a span so the wind can take them one by one.
 *  Devanagari clusters are shaped on their own, so splitting at cluster edges keeps the glyphs;
 *  no letter-spacing is added (CLAUDE.md rule 2). */
function splitTitle(el) {
  const text = el.textContent.trim();
  const seg = new Intl.Segmenter("ne", { granularity: "grapheme" });
  el.setAttribute("aria-label", text);
  el.textContent = "";
  [...seg.segment(text)].forEach(({ segment }, i) => {
    const span = document.createElement("span");
    span.className = "gate__ch";
    span.setAttribute("aria-hidden", "true");
    span.style.setProperty("--i", i);
    span.textContent = segment;
    el.append(span);
  });
}

export function initGate({ reduceMotion, playBlowout, onEntered }) {
  const gate = document.getElementById("gate");
  const story = document.getElementById("story");
  const stageEl = document.getElementById("stage");
  const enterBtn = gate.querySelector("[data-enter]");
  let leaving = false;

  if (typeof Intl !== "undefined" && Intl.Segmenter) splitTitle(gate.querySelector(".gate__title"));

  async function enter() {
    if (leaving) return;
    leaving = true;
    gate.inert = true;

    if (reduceMotion()) {
      gate.classList.add("is-leaving");
      await stageEl.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 600, fill: "forwards" }).finished;
    } else {
      gate.classList.add("is-blown"); // CSS: wick flame snuffed, letters carried off by the wind
      await Promise.all([playBlowout(), new Promise((r) => setTimeout(r, WIND_MS))]);
    }

    document.body.classList.add("is-entered");
    gate.hidden = true;
    onEntered?.();
    story.hidden = false;
    story.focus({ preventScroll: true });
  }

  enterBtn.addEventListener("click", enter);
}
