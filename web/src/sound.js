// Sound on/off state. Muted by default (WEB.md). Audio files per scene come later
// (SCENES.md "Sound per scene"); listeners react to the "tihar:sound" event.

let on = false;

export const isSoundOn = () => on;

export function setSound(next) {
  on = Boolean(next);
  document.documentElement.dataset.sound = on ? "on" : "off";
  window.dispatchEvent(new CustomEvent("tihar:sound", { detail: { on } }));
}
