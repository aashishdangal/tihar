// The story (Scene 1 onward): scroll scrubs the rendered frames (WEB.md "Architecture").
// Each scene is a tall section; their scroll ranges sit back to back, so the last frame of one
// scene meets the first frame of the next (the hidden cuts in SCENES.md). GSAP ScrollTrigger
// gives each section's scroll progress; the frame follows it with a short ease (scrub
// smoothing); each tick draws one exact rendered frame of the scene in view.
// A scene's "beats" are holds: extra scroll length so a caption can be read; while the viewer
// rests in a hold the frame can drift gently (s01: the lights keep twinkling).
// s01 starts on black (the s00 cut): its first frames play by themselves on entering, then
// scroll takes over; its last frames fade to black on the page and s02 rises out of black.

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { FrameSequence } from "./frames.js";
import { setPlace } from "./audio.js";

gsap.registerPlugin(ScrollTrigger);

const SMOOTH_S = 0.14; // scrub ease time constant (s)
const DECODE_BUDGET = 2; // WEB.md: never decode more than 2 frames per animation frame
const DRIFT_PERIOD_S = 9; // idle drift inside a hold
const IDLE_KEEP = 3; // decoded frames kept by a scene that is out of view

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** Scroll layout of one scene: piecewise-linear map between scroll and frame number.
 *  Frames intro[1]..frames at vhPerFrame; each beat's hold gets extraVh more. Lengths in vh. */
function layout(scene) {
  const v = scene.vhPerFrame;
  const segs = [];
  let f = scene.intro ? scene.intro[1] : 1;
  for (const b of scene.beats) {
    const [h0, h1] = b.hold;
    if (h0 > f) segs.push({ f0: f, f1: h0, len: (h0 - f) * v });
    segs.push({ f0: h0, f1: h1, len: (h1 - h0) * v + b.extraVh });
    f = h1;
  }
  if (scene.frames > f) segs.push({ f0: f, f1: scene.frames, len: (scene.frames - f) * v });
  const total = segs.reduce((a, s) => a + s.len, 0);
  return {
    totalVh: total,
    /** progress 0..1 -> frame (fractional) */
    frameAt(p) {
      let d = clamp(p, 0, 1) * total;
      for (const s of segs) {
        if (d <= s.len) return s.f0 + (s.f1 - s.f0) * (d / s.len);
        d -= s.len;
      }
      return scene.frames;
    },
    /** frame -> progress 0..1 */
    progressAt(f) {
      let d = 0;
      for (const s of segs) {
        if (f <= s.f1) return (d + s.len * ((f - s.f0) / (s.f1 - s.f0))) / total;
        d += s.len;
      }
      return 1;
    },
  };
}

export function initStory({ stage, scenes, pickSet, reduceMotion }) {
  const story = document.getElementById("story");
  const caption = document.getElementById("caption");
  const capLabel = caption.querySelector("[data-label]");
  const capText = caption.querySelector("[data-text]");
  const cue = document.getElementById("scroll-cue");
  const stageEl = stage.canvas;

  let set = null;
  let loading = false; // downloads start with preload(), behind the enter gate (WEB.md "Loading")
  let running = false;
  let lastScrollT = 0;
  let lastT = 0;
  let active = null;
  let reducedAlpha = 0;

  const players = scenes.map((scene, k) => {
    const section = document.getElementById(scene.id);
    const map = layout(scene);
    const last = k === scenes.length - 1;
    // back to back: each section is exactly its scroll length; the last one also gets a screen
    // more, so the next block only starts rising after its final frame
    section.style.height = last ? `calc(${map.totalVh}vh + 100vh)` : `${map.totalVh}vh`;
    const p = { scene, section, map, seq: null, progress: 0, cur: 1, dir: 1, intro: null };
    p.st = ScrollTrigger.create({
      trigger: section,
      start: "top top",
      end: () => `+=${(map.totalVh * window.innerHeight) / 100}`,
      invalidateOnRefresh: true,
      onUpdate(self) {
        p.progress = self.progress;
        lastScrollT = performance.now();
        if (window.scrollY > 8) cue.classList.remove("is-shown");
      },
    });
    return p;
  });

  // load scene by scene, in story order
  async function loadAll() {
    for (const p of players) await p.seq.load();
  }
  function useSet(next) {
    if (next === set) return;
    set = next;
    for (const p of players) {
      p.seq?.close();
      p.seq = new FrameSequence({ id: p.scene.id, count: p.scene.frames, set, maxDecoded: 28 });
    }
    if (loading) loadAll();
  }
  useSet(pickSet());

  /** the scene in view: the last one whose scroll range has started */
  function inView() {
    const y = window.scrollY;
    let p = players[0];
    for (const q of players) if (y >= q.st.start - 1) p = q;
    return p;
  }

  function decodeAround(p, i) {
    let budget = DECODE_BUDGET;
    const order = [0, 1, 2, -1, 3, 4, 5, 6, -2, 7, 8, 9, 10];
    for (const k of order) {
      if (budget <= 0) break;
      const j = i - 1 + k * p.dir; // 0-based
      if (j >= 0 && j < p.scene.frames && p.seq.decode(j)) budget--;
    }
    return budget;
  }

  // Crossfade cut (scene "xfadeIn", in frames): over its first frames the scene fades in over
  // the previous scene's last frame, held still underneath (s02 crow -> s04 dog).
  const smooth = (t) => t * t * (3 - 2 * t);
  function xfadeAlpha(scene, f) {
    if (!scene.xfadeIn) return 1;
    return smooth(clamp((f - 1) / scene.xfadeIn, 0, 1));
  }

  // one exact frame, never a blend of two (a blend shows as a soft double image)
  function drawFrame(p, f) {
    const bmp = p.seq.nearest(Math.round(f) - 1);
    if (!bmp) return false;
    const a = xfadeAlpha(p.scene, f);
    if (a < 1) {
      const prevP = players[players.indexOf(p) - 1];
      const under = prevP?.seq.nearest(prevP.scene.frames - 1);
      if (under) stage.draw(under, prevP.scene.focus[set]);
      else {
        stage.ctx.fillStyle = "#000";
        stage.ctx.fillRect(0, 0, stage.canvas.width, stage.canvas.height);
      }
    }
    stage.draw(bmp, p.scene.focus[set], a);
    return true;
  }

  function blackout(alpha) {
    if (alpha <= 0) return;
    const { ctx, canvas } = stage;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalAlpha = 1;
  }

  const beatAt = (p, f) => p.scene.beats.find((b) => f >= b.hold[0] && f <= b.hold[1]);

  // Caption: appears when the scroll reaches a beat's caption range; the next scroll (one wheel
  // step) takes it away. Scroll during the first CAPTION_GRACE_MS doesn't count (the gesture that
  // arrived is still moving). It comes back only after leaving the range and returning.
  const CAPTION_GRACE_MS = 700;
  const CAPTION_DISMISS_PX = 40;
  let capBeat = null;
  let capState = "armed"; // armed -> shown -> dismissed
  let capT = 0;
  let capY = 0;
  function updateCaption(p, scrollF, now) {
    const b = p.scene.beats.find((x) => x.caption && scrollF >= x.caption.from && scrollF <= x.caption.to);
    if (b !== capBeat) {
      capBeat = b ?? null;
      capState = "armed";
    }
    if (!b) capState = "armed";
    else if (capState === "armed") {
      capState = "shown";
      capT = now;
      capY = window.scrollY;
      capLabel.textContent = b.caption.label;
      capText.textContent = b.caption.text;
    } else if (capState === "shown") {
      if (now - capT < CAPTION_GRACE_MS) capY = window.scrollY;
      else if (Math.abs(window.scrollY - capY) > CAPTION_DISMISS_PX) capState = "dismissed";
    }
    caption.classList.toggle("is-shown", capState === "shown");
  }

  function activate(p) {
    if (p === active) return;
    active = p;
    stageEl.setAttribute("aria-label", p.scene.alt);
    p.cur = clamp(p.map.frameAt(p.progress), 1, p.scene.frames); // no fast-forward on arrival
    reducedAlpha = 0;
  }

  function tick(now) {
    if (!running) return;
    const dt = lastT ? Math.min(0.1, (now - lastT) / 1000) : 1 / 60;
    lastT = now;
    activate(inView());
    const p = active;
    const { scene, map } = p;
    const scrollF = map.frameAt(p.progress);
    let budget = DECODE_BUDGET;

    if (reduceMotion()) {
      // WEB.md: no scrubbing; the nearest beat's frame crossfades in (s01: out to black at the end)
      const fadeOut = scene.fadeOut && p.progress >= map.progressAt(scene.frames - scene.fadeOut);
      reducedAlpha = clamp(reducedAlpha + Math.sign((fadeOut ? 0 : 1) - reducedAlpha) * dt * 2.5, 0, 1);
      const beat = scene.beats.reduce((a, b) => (Math.abs(b.stop - scrollF) < Math.abs(a.stop - scrollF) ? b : a));
      p.cur = beat.stop;
      budget = decodeAround(p, p.cur);
      stage.ctx.fillStyle = "#000";
      stage.ctx.fillRect(0, 0, stage.canvas.width, stage.canvas.height);
      const bmp = p.seq.nearest(p.cur - 1);
      if (bmp) stage.draw(bmp, scene.focus[set], reducedAlpha);
    } else {
      // target: the scroll's frame, plus a slow drift while resting in a hold
      const beat = beatAt(p, scrollF);
      let drift = 0;
      if (beat?.drift) {
        const [h0, h1] = beat.hold;
        const idle = clamp((now - lastScrollT - 400) / 1200, 0, 1);
        const edge = clamp(Math.min(scrollF - h0, h1 - scrollF) / beat.drift, 0, 1);
        drift = Math.sin((now / 1000 / DRIFT_PERIOD_S) * Math.PI * 2) * beat.drift * idle * edge;
      }
      let target = clamp(scrollF + drift, 1, scene.frames);
      if (p.intro) target = Math.min(target, p.intro.f);

      const prev = p.cur;
      p.cur += (target - p.cur) * (1 - Math.exp(-dt / SMOOTH_S));
      if (Math.abs(target - p.cur) < 0.002) p.cur = target;
      if (p.cur !== prev) p.dir = p.cur > prev ? 1 : -1;

      budget = decodeAround(p, Math.round(p.cur));
      if (!drawFrame(p, p.cur)) {
        stage.ctx.fillStyle = "#000";
        stage.ctx.fillRect(0, 0, stage.canvas.width, stage.canvas.height);
      }
      // s01's out: fade to black over the last frames (no close-up cloud render)
      // (reaches full black one frame early: the scroll's end can stop a hair short of 1)
      if (scene.fadeOut) blackout(clamp((p.cur - (scene.frames - scene.fadeOut)) / (scene.fadeOut - 1), 0, 1));
    }
    p.seq.evict(Math.round(p.cur) - 1);
    setPlace(scene.id, p.cur);

    // neighbours: the next scene's opening frames ready near the cut, the previous scene's last
    // frames ready for scrolling back; everything else out of view is freed
    const k = players.indexOf(p);
    const next = players[k + 1];
    const prevP = players[k - 1];
    for (const q of players) {
      if (q === p) continue;
      if (q === next && p.cur > scene.frames - 10) {
        for (let j = 0; j < IDLE_KEEP && budget > 0; j++) if (q.seq.decode(j)) budget--;
        q.seq.evict(0, false, IDLE_KEEP);
      } else if (q === prevP && p.cur < 10) {
        const end = q.scene.frames - 1;
        for (let j = 0; j < IDLE_KEEP && budget > 0; j++) if (q.seq.decode(end - j)) budget--;
        q.seq.evict(end, false, IDLE_KEEP);
      } else q.seq.evict(q === next ? 0 : q.scene.frames - 1, false, 0);
    }

    updateCaption(p, scrollF, now);
    requestAnimationFrame(tick);
  }

  // the next placeholder rises from below after the last scene
  gsap.fromTo(
    ".story__next .story__soon",
    { opacity: 0, y: 40 },
    {
      opacity: 1,
      y: 0,
      ease: "none",
      scrollTrigger: { trigger: ".story__next", start: "top 80%", end: "top 30%", scrub: true },
    }
  );

  // --- keyboard (WEB.md): arrows / Page keys move between pause points ---
  // every scene's start, its beats and its end, then the page end
  const stops = () => {
    const s = [];
    for (const p of players) {
      const { start, end } = p.st;
      s.push(start, ...p.scene.beats.map((b) => start + p.map.progressAt(b.stop) * (end - start)), end);
    }
    s.push(document.documentElement.scrollHeight - window.innerHeight);
    return [...new Set(s.map(Math.round))].sort((a, b) => a - b);
  };
  function onKey(e) {
    if (!running || e.altKey || e.ctrlKey || e.metaKey) return;
    const space = e.key === " ";
    const prev = e.key === "ArrowUp" || e.key === "PageUp" || (space && e.shiftKey);
    const next = e.key === "ArrowDown" || e.key === "PageDown" || (space && !e.shiftKey);
    if (!next && !prev) return;
    if (e.target.closest?.("button, input, textarea")) return;
    e.preventDefault();
    const y = window.scrollY;
    const s = stops();
    const to = prev
      ? ([...s].reverse().find((p) => p < y - 4) ?? 0)
      : (s.find((p) => p > y + 4) ?? s[s.length - 1]);
    window.scrollTo({ top: to, behavior: reduceMotion() ? "auto" : "smooth" });
  }

  window.addEventListener("resize", () => useSet(pickSet()));

  return {
    /** start downloading the frames (after the gate's own frames) */
    preload() {
      if (loading) return;
      loading = true;
      loadAll();
    },
    /** called once the enter gate has cut to black */
    start() {
      story.hidden = false; // measured before the first refresh
      history.scrollRestoration = "manual";
      window.scrollTo(0, 0);
      for (const p of players) p.progress = 0;
      const first = players[0];
      activate(first);
      first.cur = 1;
      running = true;
      lastScrollT = performance.now();
      requestAnimationFrame(tick);
      ScrollTrigger.refresh();
      window.addEventListener("keydown", onKey);
      // s01: stars first, then the valley: the opening frames rise out of black by themselves
      const s = first.scene;
      if (s.intro && !reduceMotion()) {
        first.intro = { f: s.intro[0] };
        gsap.to(first.intro, {
          f: s.intro[1],
          duration: ((s.intro[1] - s.intro[0]) / s.fps) * 2,
          ease: "power1.inOut",
          onComplete: () => (first.intro = null),
        });
      }
      setTimeout(() => {
        if (window.scrollY <= 8) cue.classList.add("is-shown");
      }, reduceMotion() ? 200 : 1600);
      story.classList.add("is-live");
    },
  };
}
