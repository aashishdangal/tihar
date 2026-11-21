// The five days, bottom-right: the moon of each night of Tihar (owner 2026-11-21: "everybody
// uses diyos for the five days"). Tihar runs on the lunar calendar across the new moon:
// त्रयोदशी and चतुर्दशी thin the waning crescent, औँसी (Laxmi Puja) is the dark moon the diyos
// light up for, then प्रतिपदा and द्वितीया bring the first sliver back for Bhai Tika.
// Each moon is a small realistic render (scripts/make_moons.py), with earthshine on its dark side.

// day → [lit fraction, side], as drawn by scripts/make_moons.py into sprites/moon_N.png.
// Waning moons are lit on the left, waxing on the right (as seen from Nepal). The crescents are
// a little fuller than the real ones so they read at HUD size; the order and sides are true.
const PHASES = [
  [0.26, "left"], // दिन १ त्रयोदशी: काग तिहार
  [0.12, "left"], // दिन २ चतुर्दशी: कुकुर तिहार
  [0, null], // दिन ३ औँसी: गाई तिहार, लक्ष्मी पूजा — only earthshine
  [0.05, "right"], // दिन ४ प्रतिपदा: गोवर्धन पूजा, देउसी
  [0.13, "right"], // दिन ५ द्वितीया: भाइटीका
];
const DIGITS = ["१", "२", "३", "४", "५"];

// Where each day begins: [scene, first frame]. Kaag Tihar lives inside s02 from the crow beat.
const DAY_START = [
  ["s02_legend", 128],
  ["s04_kukur", 1],
  ["s05_laxmi", 1],
  ["s06_govardhan", 1],
  ["s07_bhaitika", 1],
];
const ORDER = ["s00_enter", "s00_blowout", "s01_hero", "s02_legend", "s04_kukur", "s05_laxmi", "s06_govardhan", "s07_bhaitika", "s08_finale"];

/** 0 = before Tihar, 1–5 = that day, 6 = the finale (every moon has risen). */
function dayAt(id, frame) {
  if (id === "s08_finale") return 6;
  const at = ORDER.indexOf(id);
  let day = 0;
  DAY_START.forEach(([sid, f], i) => {
    const si = ORDER.indexOf(sid);
    if (at > si || (at === si && frame >= f)) day = i + 1;
  });
  return day;
}

export function initMoons(list) {
  if (!list) return () => {};
  const items = PHASES.map(([k], i) => {
    const li = document.createElement("li");
    li.className = "moon" + (k === 0 ? " moon--new" : "");
    li.setAttribute("aria-label", `दिन ${DIGITS[i]}`);
    const img = document.createElement("img");
    img.src = `${import.meta.env.BASE_URL}sprites/moon_${i + 1}.png`;
    img.alt = "";
    img.decoding = "async";
    li.append(img);
    list.append(li);
    return li;
  });

  let shown = -1;
  return function setDay(id, frame) {
    const day = dayAt(id, frame);
    if (day === shown) return;
    shown = day;
    items.forEach((li, i) => {
      li.classList.toggle("is-lit", i + 1 < day || day === 6);
      li.classList.toggle("is-active", i + 1 === day);
      if (i + 1 === day) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
    });
  };
}
