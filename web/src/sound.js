// Sound on/off state + the HUD toggle (bottom-left). On by default: entering the site is the
// user gesture that allows audio to start. Audio files per scene come later (SCENES.md
// "Sound per scene"); listeners react to the "tihar:sound" event.

let on = true;

export const isSoundOn = () => on;

export function setSound(next) {
  on = Boolean(next);
  document.documentElement.dataset.sound = on ? "on" : "off";
  const btn = document.getElementById("sound");
  if (btn) btn.setAttribute("aria-pressed", String(on));
  window.dispatchEvent(new CustomEvent("tihar:sound", { detail: { on } }));
}

export function initSoundToggle() {
  const btn = document.getElementById("sound");
  setSound(on);
  btn.addEventListener("click", () => setSound(!on));
}
