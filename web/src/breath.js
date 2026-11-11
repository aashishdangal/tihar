// The सुरु "breath" control: press and hold and the boy's face breathes in (head back, then
// cheeks puffed; the ring fills), let go and he blows the diyo out. Each face change is a
// crossfade with a small spring (CSS) and a soft pulse of the ring.
// Holding is never required: a quick click/tap, Enter/Space, or a screen-reader "activate"
// plays a full breath automatically. Letting go before BLOW_MIN just lets the breath out.

const BREATHE_MS = 1200; // a full breath in
const AUTO_MS = 520; // the automatic breath for a tap / keyboard / assistive tech
const DRAIN_MS = 450; // breath let out without blowing
const TAP_MS = 220; // a press shorter than this is a tap
const BLOW_MIN = 0.6; // enough breath to blow the diyo out
const CHEEKS_AT = 0.8; // the boy switches from "arms wide" to "cheeks puffed"

const easeOut = (x) => 1 - (1 - x) * (1 - x);
const breathe = (x) => x * x * (3 - 2 * x); // slow start, faster middle, slow finish: ~0.7 s to BLOW_MIN

export function initBreath(button, { onBlow }) {
  let p = 0; // breath 0..1, drawn on the button as --p
  let raf = 0;
  let pressAt = 0;
  let pressing = false;
  let done = false;
  let lastInput = 0; // time of the last pointer/key press (to ignore the follow-up click)

  let pulseTimer = 0;
  /** the ring pulses softly whenever the face changes */
  const pulse = () => {
    button.classList.remove("is-change");
    void button.offsetWidth; // restart the animation
    button.classList.add("is-change");
    clearTimeout(pulseTimer);
    pulseTimer = setTimeout(() => button.classList.remove("is-change"), 450);
  };
  const toggle = (cls, on) => {
    if (button.classList.contains(cls) !== on) {
      button.classList.toggle(cls, on);
      if (cls === "is-cheeks") pulse();
    }
  };

  const set = (v) => {
    p = Math.max(0, Math.min(1, v));
    button.style.setProperty("--p", p.toFixed(3));
    toggle("is-full", p >= 1);
    toggle("is-cheeks", p >= CHEEKS_AT); // near the top of the breath: cheeks puffed
  };

  /** animate p to `to` over `ms`, then call `then` */
  function tween(to, ms, ease, then) {
    cancelAnimationFrame(raf);
    const from = p;
    const t0 = performance.now();
    const step = (now) => {
      const x = Math.min(1, (now - t0) / ms);
      set(from + (to - from) * ease(x));
      if (x < 1) raf = requestAnimationFrame(step);
      else then?.();
    };
    raf = requestAnimationFrame(step);
  }

  function blow() {
    if (done) return;
    done = true;
    cancelAnimationFrame(raf);
    button.classList.remove("is-holding");
    button.classList.add("is-blowing");
    pulse();
    onBlow(p);
  }

  function autoBreath() {
    if (done) return;
    button.classList.add("is-holding");
    tween(1, AUTO_MS * (1 - p), easeOut, blow);
  }

  function press() {
    if (done || pressing) return;
    pressing = true;
    pressAt = lastInput = performance.now();
    button.classList.add("is-holding");
    pulse();
    tween(1, BREATHE_MS * (1 - p), breathe);
  }

  function release() {
    if (!pressing || done) return;
    pressing = false;
    if (performance.now() - pressAt < TAP_MS) return autoBreath();
    if (p >= BLOW_MIN) return blow();
    button.classList.remove("is-holding");
    pulse();
    tween(0, DRAIN_MS * p, easeOut); // not enough breath: let it out
  }

  function cancel() {
    if (!pressing || done) return;
    pressing = false;
    button.classList.remove("is-holding");
    tween(0, DRAIN_MS * p, easeOut);
  }

  button.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    button.setPointerCapture?.(e.pointerId);
    press();
  });
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", cancel);
  button.addEventListener("contextmenu", (e) => e.preventDefault()); // long-press menu on touch

  button.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && !e.repeat) {
      e.preventDefault();
      press();
    }
  });
  button.addEventListener("keyup", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      release();
    }
  });

  // screen readers / switch access send a click with no pointer or key press before it
  button.addEventListener("click", (e) => {
    e.preventDefault();
    if (performance.now() - lastInput > 600) autoBreath();
  });

  set(0);
}
