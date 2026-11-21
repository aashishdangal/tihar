// Scene 8's caption lines, written in firework sparks (owner 2026-11-21 chose "firework sparks"
// for the finale captions; every other scene's caption is made of something from its scene).
//
// When a line is shown (story.js toggles .is-shown) gold sparks rush in from around the screen and
// settle into the letters; the crisp text then fades up under a faint glitter. When it goes, the
// text lets go and the letters fall away as sparks under gravity, like the fireworks behind them.
// The words' shapes come from the line itself: each word is drawn into an offscreen canvas in the
// line's own font and sampled, so the sparks land on the real Devanagari (no letter-spacing, no
// hand-made outlines). One shared canvas over the finale; it only animates while sparks are alive.
// Reduced motion: no sparks, the text simply fades.

const HUES = ["#ffd27a", "#fff2c8", "#ffb347", "#ffc861", "#ff9a2e", "#ffe2a0"];
// owner 2026-11-21: "tone down the firework effect, it's too much" -> about a third of the sparks,
// smaller, softer, from closer by, and the glitter dies away instead of staying on
const STEP = 4; // px between sampled points
const MAX_SPARKS = 700; // per line (was 2200)
const IN_S = [0.7, 1.1]; // flight time into the letters
const INK_AT = 0.75; // the crisp text starts fading up once most sparks have landed
const INK_S = 0.55;
const GRAVITY = 200; // px/s^2 when the letters fall away
const FALL_S = [0.7, 1.2];

export function createSparkText(lines, { reduceMotion }) {
  const canvas = document.createElement("canvas");
  canvas.className = "finale__sparks";
  canvas.setAttribute("aria-hidden", "true");
  document.body.append(canvas);
  const ctx = canvas.getContext("2d");
  let dpr = 1;
  const resize = () => {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(window.innerWidth * dpr);
    canvas.height = Math.round(window.innerHeight * dpr);
  };
  resize();
  window.addEventListener("resize", resize);

  const states = new Map(); // line -> { sparks: [], ink, inkT, mode: "in" | "out" | "idle", t }
  let raf = 0;
  let last = 0;

  // wrap each word in a span once, so its box on screen can be measured
  for (const el of lines) {
    if (el.dataset.sparkWrapped) continue;
    const words = el.textContent.split(/(\s+)/);
    el.textContent = "";
    for (const w of words) {
      if (/^\s+$/.test(w)) el.append(document.createTextNode(w));
      else if (w) {
        const s = document.createElement("span");
        s.className = "finale__word";
        s.textContent = w;
        el.append(s);
      }
    }
    el.dataset.sparkWrapped = "1";
    el.classList.add("is-spark");
    el.style.setProperty("--ink", "0");
    states.set(el, { sparks: [], ink: 0, mode: "idle", t: 0 });
  }

  /** points on the line's letters, in CSS px on screen */
  function sample(el) {
    const r = el.getBoundingClientRect();
    const w = Math.ceil(r.width), h = Math.ceil(r.height);
    if (!w || !h) return [];
    const off = document.createElement("canvas");
    off.width = w; off.height = h;
    const o = off.getContext("2d");
    o.fillStyle = "#fff";
    o.textBaseline = "alphabetic";
    for (const s of el.querySelectorAll(".finale__word")) {
      const cs = getComputedStyle(s);
      o.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      const sr = s.getBoundingClientRect();
      const m = o.measureText(s.textContent);
      // baseline: centre the ink box in the span's box
      const asc = m.actualBoundingBoxAscent, desc = m.actualBoundingBoxDescent;
      const y = sr.top - r.top + (sr.height - (asc + desc)) / 2 + asc;
      o.fillText(s.textContent, sr.left - r.left + (sr.width - m.width) / 2, y);
    }
    const data = o.getImageData(0, 0, w, h).data;
    const pts = [];
    for (let y = 0; y < h; y += STEP) {
      for (let x = 0; x < w; x += STEP) {
        if (data[(y * w + x) * 4 + 3] > 120) pts.push([r.left + x + Math.random() * 1.5, r.top + y + Math.random() * 1.5]);
      }
    }
    // thin evenly if there are too many
    while (pts.length > MAX_SPARKS) pts.splice((Math.random() * pts.length) | 0, 1);
    return pts;
  }

  function show(el) {
    const st = states.get(el);
    if (reduceMotion()) {
      st.mode = "idle"; st.ink = 1; el.style.setProperty("--ink", "1");
      return;
    }
    const pts = sample(el);
    st.sparks = pts.map(([tx, ty]) => {
      const a = Math.random() * Math.PI * 2;
      const d = 50 + Math.random() * 140; // from close by (was 160-540 px)
      return {
        sx: tx + Math.cos(a) * d, sy: ty + Math.sin(a) * d * 0.7 - 30, tx, ty,
        dur: IN_S[0] + Math.random() * (IN_S[1] - IN_S[0]), delay: Math.random() * 0.25,
        hue: HUES[(Math.random() * HUES.length) | 0], size: 0.6 + Math.random() * 0.8,
        tw: Math.random() * 6.28, x: 0, y: 0, vx: 0, vy: 0, life: 0, max: 0,
      };
    });
    st.mode = "in"; st.t = 0;
    run();
  }

  function hide(el) {
    const st = states.get(el);
    if (reduceMotion() || st.mode === "idle" && !st.sparks.length) {
      st.ink = 0; el.style.setProperty("--ink", "0");
      st.mode = "idle"; st.sparks = [];
      return;
    }
    // every spark lets go of its letter and falls
    for (const s of st.sparks) {
      s.x = s.tx; s.y = s.ty;
      s.vx = (Math.random() - 0.5) * 50;
      s.vy = -10 - Math.random() * 40;
      s.life = 0; s.max = FALL_S[0] + Math.random() * (FALL_S[1] - FALL_S[0]);
    }
    st.mode = "out"; st.t = 0;
    run();
  }

  function run() {
    if (raf) return;
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }

  const ease = (x) => 1 - Math.pow(1 - x, 3);

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.globalCompositeOperation = "lighter";
    let alive = false;
    for (const [el, st] of states) {
      if (st.mode === "idle") continue;
      st.t += dt;
      if (st.mode === "in") {
        // the crisp text fades up under the landing sparks, then the sparks thin to a glitter
        const ink = Math.min(1, Math.max(0, (st.t - INK_AT) / INK_S));
        el.style.setProperty("--ink", ink.toFixed(3));
        const glitter = st.t > INK_AT ? Math.max(0, 1 - (st.t - INK_AT) / 0.9) : 1; // dies away fully
        for (const s of st.sparks) {
          const k = Math.min(1, Math.max(0, (st.t - s.delay) / s.dur));
          const e = ease(k);
          s.x = s.sx + (s.tx - s.sx) * e;
          s.y = s.sy + (s.ty - s.sy) * e;
          const tw = 0.55 + 0.45 * Math.sin(st.t * 9 + s.tw);
          const a = (k < 1 ? 0.2 + 0.5 * k : 0.7 * glitter * tw);
          dot(s.x, s.y, s.size * (k < 1 ? 1.2 : 0.9), s.hue, a);
        }
        if (st.t < INK_AT + 1.0) alive = true; // the glitter has died away after this
      } else {
        const ink = Math.max(0, 1 - st.t / 0.25);
        el.style.setProperty("--ink", ink.toFixed(3));
        let any = false;
        for (const s of st.sparks) {
          s.life += dt;
          if (s.life >= s.max) continue;
          any = true;
          s.vy += GRAVITY * dt;
          s.vx *= Math.exp(-1.2 * dt);
          s.x += s.vx * dt; s.y += s.vy * dt;
          const a = 1 - s.life / s.max;
          dot(s.x, s.y, s.size, s.hue, 0.7 * a * a);
        }
        if (!any) { st.mode = "idle"; st.sparks = []; }
        else alive = true;
      }
    }
    if (alive) raf = requestAnimationFrame(frame);
    else { raf = 0; ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, canvas.width, canvas.height); }
  }

  function dot(x, y, r, hue, a) {
    if (a <= 0.01) return;
    ctx.globalAlpha = Math.min(1, a);
    ctx.fillStyle = hue;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 6.283);
    ctx.fill();
  }

  // follow story.js's .is-shown on each line
  const mo = new MutationObserver((recs) => {
    for (const r of recs) {
      const el = r.target;
      if (!states.has(el)) continue;
      const on = el.classList.contains("is-shown");
      const st = states.get(el);
      if (on && st.mode !== "in") show(el);
      else if (!on && st.mode === "in") hide(el);
    }
  });
  for (const el of lines) mo.observe(el, { attributes: true, attributeFilter: ["class"] });

  return {
    dispose() {
      mo.disconnect();
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      canvas.remove();
    },
  };
}
