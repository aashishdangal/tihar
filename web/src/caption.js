// The caption layer (scenes 1-7).
//
// The site's argument is light over darkness, so the caption is lit rather than merely drawn:
// the pointer is a flame the reader carries across the words. A word near it is lit — cream,
// with a marigold rim, standing proud of the surface; a word further off sinks toward the dark
// and throws its shadow AWAY from the light. The depth is the lighting, not an arbitrary tilt.
//
// Devanagari rules the implementation (CLAUDE.md 2): the shirorekha runs across a whole word,
// so a word is the smallest thing that may be moved. Nothing here splits characters, and nothing
// anywhere sets letter-spacing. Words are separated by real spaces in the DOM, so the caption
// still reads as one sentence to a screen reader.

import { createCaption3D } from "./caption3d.js";

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const smooth = (t) => t * t * (3 - 2 * t);

const BASE_LIGHT = 0.58; // a word out of the light must still read easily: the difference
                         // between lit and unlit is carried by the glow, not by darkness
const REACH = 0.42; // falloff radius as a share of the caption's width: the pool of light must
                    // be smaller than the line, or every word is lit at once and nothing moves
const LIFT_PX = 14; // how far a fully lit word stands off the surface
const TILT_DEG = 5; // how far the block turns toward the light

// Jhilimili: the string of Tihar lights, for a caption that asks for it ("lights" in
// scenes.json). The wire is drawn across the caption and the bulbs alternate in front of and
// behind the glyphs in the same 3D space, so the string reads as wound through the words rather
// than pasted over them. A bulb lights when the pointer comes near it, the same flame that lights
// the words. The colours are the valley's own lights in scene 1 — blue, green and rose among the
// marigold — not a second accent for the site (CLAUDE.md 7 keeps each scene its own palette).

export function initCaption(el, { reduceMotion }) {
  const label = el.querySelector("[data-label]");
  const text = el.querySelector("[data-text]");
  let words = [];
  let lit = false; // this caption is drawn by the WebGL layer
  let treatment = {};
  let strand = null;
  let spots = []; // cached word centres (the caption is position:fixed, so scroll cannot move them)
  let px = null;
  let py = null;
  let queued = false;

  /** Split on spaces only. A Devanagari danda or comma stays attached to its word. */
  function fill(node, string) {
    node.textContent = "";
    const parts = String(string).split(/\s+/).filter(Boolean);
    parts.forEach((part, i) => {
      const span = document.createElement("span");
      span.className = "caption__word";
      span.textContent = part;
      node.append(span);
      if (i < parts.length - 1) node.append(document.createTextNode(" "));
    });
    return [...node.querySelectorAll(".caption__word")];
  }

  function measure() {
    spots = words.map((w) => {
      const r = w.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    });
    if (strand && lit) strand.build(words, treatment);
  }

  // The lit caption (scenes.json "lights") is drawn in WebGL instead of CSS: see caption3d.js.
  // The DOM words stay exactly where they are — they own layout, wrapping and accessibility —
  // but go transparent, so what the reader sees is the lit, three-dimensional version of them.
  function ensureStrand() {
    if (strand) return strand;
    strand = createCaption3D({ reduceMotion });
    strand.mount(document.body);
    if (new URLSearchParams(location.search).has("probe")) window.__capLayer = strand;
    return strand;
  }

  function paint() {
    queued = false;
    if (!spots.length) return;
    const box = el.getBoundingClientRect();
    const reach = Math.min(Math.max(box.width * REACH, 240), 460);
    // with no pointer (touch, or the cursor away from the page) the light rests on the caption
    const lx = px ?? box.left + box.width / 2;
    const ly = py ?? box.top + box.height / 2;

    for (let i = 0; i < words.length; i++) {
      const s = spots[i];
      const dx = s.x - lx;
      const dy = s.y - ly;
      const near = smooth(clamp(1 - Math.hypot(dx, dy) / reach, 0, 1));
      const lit = BASE_LIGHT + (1 - BASE_LIGHT) * near;
      const len = Math.hypot(dx, dy) || 1;
      const w = words[i];
      w.style.setProperty("--lit", lit.toFixed(3));
      w.style.setProperty("--dz", `${(near * LIFT_PX).toFixed(2)}px`);
      // the shadow falls along the line from the light through the word
      w.style.setProperty("--sx", `${((dx / len) * (1 + near * 5)).toFixed(2)}px`);
      w.style.setProperty("--sy", `${((dy / len) * (1 + near * 5) + 2).toFixed(2)}px`);
    }

    if (strand && lit) {
      strand.pointer(px, py);
      strand.render();
    }

    const tx = px === null ? 0 : clamp((lx - (box.left + box.width / 2)) / box.width, -1, 1);
    const ty = py === null ? 0 : clamp((ly - (box.top + box.height / 2)) / Math.max(box.height, 1), -1.5, 1.5);
    el.style.setProperty("--turn-y", `${(tx * TILT_DEG).toFixed(2)}deg`);
    el.style.setProperty("--turn-x", `${(-ty * TILT_DEG * 0.6).toFixed(2)}deg`);
  }

  function request() {
    if (queued || reduceMotion()) return;
    queued = true;
    requestAnimationFrame(paint);
  }

  window.addEventListener(
    "pointermove",
    (e) => {
      if (e.pointerType !== "mouse") return; // a finger is not a light source
      px = e.clientX;
      py = e.clientY;
      request();
    },
    { passive: true }
  );
  window.addEventListener("pointerleave", () => {
    px = py = null;
    request();
  });
  window.addEventListener("resize", () => {
    measure();
    request();
  });

  // ---- placement ---------------------------------------------------------------------------
  // Each caption says where it sits: "at": [x, y] in 0..1 of the viewport, per frame set
  // ("at" may be {d:[..], m:[..]} to place it differently on a phone). Default: bottom centre.
  const DEFAULT_AT = [0.5, 0.86];
  let placedKey = null; // which caption is currently placed, so ?place knows what it is editing

  function placeAt(at, align) {
    const [x, y] = at;
    el.style.setProperty("--cap-x", clamp(x, 0, 1).toFixed(4));
    el.style.setProperty("--cap-y", clamp(y, 0.06, 0.94).toFixed(4));
    el.style.setProperty("--cap-align", align ?? (x < 0.34 ? "left" : x > 0.66 ? "right" : "center"));
    measure();
  }

  return {
    /** Put a caption up. Rebuilds the words, so call it only when the text actually changes. */
    set(labelText, bodyText, opts = {}) {
      // a caption may carry no label at all (s01 speaks without one)
      label.hidden = !labelText;
      if (labelText) fill(label, labelText);
      else label.textContent = "";
      words = fill(text, bodyText);
      // a caption may be lit (scene 1's hanging lights), carved, taken by smoke, or any mix
      treatment = {
        lights: !!opts.lights,
        wood: !!opts.wood,
        smoke: !!opts.smoke,
        lay: !!opts.lay,
        feather: !!opts.feather,
        peck: !!opts.peck,
        powder: !!opts.powder,
        mala: !!opts.mala,
        diyo: !!opts.diyo,
        gilt: !!opts.gilt,
        door: !!opts.door,
        grain: !!opts.grain,
      };
      lit = Object.values(treatment).some(Boolean);
      el.classList.toggle("is-3d", lit);
      if (lit) ensureStrand();
      else strand?.setVisible(false);
      const at = opts.at && !Array.isArray(opts.at) ? opts.at[opts.set] ?? opts.at.d : opts.at;
      placedKey = opts.key ?? null;
      placeAt(overrides.get(placedKey) ?? at ?? DEFAULT_AT, opts.align);
      if (lit) strand?.restart(); // this caption makes its own entrance, even mid-sequence
      if (reduceMotion()) {
        for (const w of words) w.style.setProperty("--lit", "1");
      } else {
        paint();
      }
    },
    /** Follow the caption's own visibility: up with it, and away with it. */
    shown(on) {
      if (!strand) return;
      strand.setVisible(!!(on && lit));
    },

    /** ?place: nudge the caption on screen and read the value back out */
    moveBy(dx, dy) {
      const x = parseFloat(el.style.getPropertyValue("--cap-x") || DEFAULT_AT[0]) + dx;
      const y = parseFloat(el.style.getPropertyValue("--cap-y") || DEFAULT_AT[1]) + dy;
      placeAt([x, y]);
      if (placedKey) {
        overrides.set(placedKey, [+clamp(x, 0, 1).toFixed(3), +clamp(y, 0.06, 0.94).toFixed(3)]);
        saveOverrides();
      }
      return { key: placedKey, at: overrides.get(placedKey) };
    },
    get placedKey() {
      return placedKey;
    },
  };
}

// ---- ?place -------------------------------------------------------------------------------
// Drag a caption where it belongs instead of guessing numbers. Values are kept in localStorage
// under this key and read back out with captionPlacements() in the console.
const STORE = "tihar.caption.at";
const overrides = new Map(loadOverrides());

function loadOverrides() {
  try {
    return Object.entries(JSON.parse(localStorage.getItem(STORE) || "{}"));
  } catch {
    return [];
  }
}

function saveOverrides() {
  try {
    localStorage.setItem(STORE, JSON.stringify(Object.fromEntries(overrides)));
  } catch {
    /* private window: the session's placements simply do not persist */
  }
}

/** Turn on drag-to-place. Call from main.js when the URL carries ?place. */
export function initPlaceMode(el, caption) {
  let dragging = false;
  el.style.pointerEvents = "auto";
  el.style.cursor = "grab";
  el.title = "drag to place · arrow keys to nudge";

  el.addEventListener("pointerdown", (e) => {
    dragging = true;
    el.setPointerCapture(e.pointerId);
    el.style.cursor = "grabbing";
    e.preventDefault();
  });
  el.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const x = e.clientX / window.innerWidth;
    const y = e.clientY / window.innerHeight;
    const cur = { x: parseFloat(getComputedStyle(el).getPropertyValue("--cap-x")) || 0.5,
                  y: parseFloat(getComputedStyle(el).getPropertyValue("--cap-y")) || 0.86 };
    caption.moveBy(x - cur.x, y - cur.y);
  });
  el.addEventListener("pointerup", (e) => {
    dragging = false;
    el.releasePointerCapture(e.pointerId);
    el.style.cursor = "grab";
    const p = caption.moveBy(0, 0);
    if (p.key) console.log(`[place] ${p.key}  "at": [${p.at[0]}, ${p.at[1]}]`);
  });
  window.addEventListener("keydown", (e) => {
    const step = e.shiftKey ? 0.02 : 0.004;
    const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
    if (!d || !caption.placedKey) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const p = caption.moveBy(d[0], d[1]);
    console.log(`[place] ${p.key}  "at": [${p.at[0]}, ${p.at[1]}]`);
  }, true);

  window.captionPlacements = () => {
    const out = Object.fromEntries(overrides);
    console.log(JSON.stringify(out, null, 2));
    return out;
  };
  console.log('[place] drag the caption, or nudge with arrows (shift = coarse). Then run captionPlacements().');
}
