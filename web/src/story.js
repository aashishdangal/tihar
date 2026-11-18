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
import { layout } from "./scroll_map.js";
import { initCaption, initPlaceMode } from "./caption.js";
import { setPlace } from "./audio.js";

gsap.registerPlugin(ScrollTrigger);

const SMOOTH_S = 0.14; // scrub ease time constant (s), once the scroll has come to rest
const SMOOTH_MOVING_S = 0.05; // while the gesture is live: the picture stays with the finger
const SETTLE_MS = 140; // quiet time after a gesture before the full-quality frame is drawn
const DECODE_BUDGET = 2; // WEB.md: never decode more than 2 frames per animation frame
const DRIFT_PERIOD_S = 9; // idle drift inside a hold
const IDLE_KEEP = 3; // decoded frames kept by a scene that is out of view
const SNAP_REACH = 30; // vh: a gesture ending this close to a snap frame settles onto it

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export function initStory({ stage, scenes, pickSet, reduceMotion }) {
  const story = document.getElementById("story");
  const caption = document.getElementById("caption");
  const captionLight = initCaption(caption, { reduceMotion });
  // ?place in the URL: drag each caption where it belongs, then read the values back out
  if (new URLSearchParams(location.search).has("place")) initPlaceMode(caption, captionLight);
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
    // Snap (scenes.json "snap", in frames): the scroll stays yours — frames follow the gesture
    // 1:1 — but when the gesture ends near a composed moment (the valley settling, the end of a
    // caption hold, the scene's last frame) it eases onto it instead of resting mid-pan.
    // Only near: beyond SNAP_REACH the scroll is left exactly where it was put, so a long sweep
    // is never yanked out of the viewer's hands.
    const snapAt = (scene.snap ?? []).map((f) => map.progressAt(f));
    const snapTo = (value) => {
      // a caption that has just arrested the scroll owns the reader's position until it has been
      // read; snapping back to the previous resting frame would yank the text off the screen
      if (performance.now() < snapHeldUntil) return value;
      const reach = SNAP_REACH / Math.max(1, map.totalVh); // vh -> progress
      let best = value;
      for (const s of snapAt) if (Math.abs(s - value) < Math.abs(best - value) || best === value) {
        if (Math.abs(s - value) <= reach) best = s;
      }
      return best;
    };

    p.st = ScrollTrigger.create({
      trigger: section,
      start: "top top",
      end: () => `+=${(map.totalVh * window.innerHeight) / 100}`,
      invalidateOnRefresh: true,
      ...(snapAt.length && !reduceMotion()
        ? { snap: { snapTo, duration: { min: 0.15, max: 0.5 }, delay: 0.08, ease: "power2.out" } }
        : {}),
      onUpdate(self) {
        p.progress = self.progress;
        lastScrollT = performance.now();
        if (window.scrollY > 8) cue.classList.remove("is-shown");
      },
    });
    return p;
  });

  // load scene by scene, in story order
  // The light set comes down first, for every scene: it is a third of the bytes and the scrub
  // can run on it from the start. The full set follows and is what you see once you stop.
  async function loadAll() {
    for (const p of players) await p.lo.load();
    for (const p of players) await p.seq.load();
  }
  function useSet(next) {
    if (next === set) return;
    set = next;
    for (const p of players) {
      p.seq?.close();
      p.seq = new FrameSequence({ id: p.scene.id, count: p.scene.frames, set, maxDecoded: 28 });
      // the light set is kept alongside it and is what a moving scrub draws (see pick())
      if (!p.lo) p.lo = new FrameSequence({ id: p.scene.id, count: p.scene.frames, set: "l", maxDecoded: 40, quiet: true });
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

  // Decode around the frame the scroll is ASKING for, not the one on screen: the drawn frame
  // lags behind the gesture, so centring here on p.cur kept decoding frames already passed.
  // The light set goes first (it is what a moving scrub draws); the full frame of a scroll that
  // has come to rest is decoded last, and only then does the picture sharpen.
  function decodeAround(p, i, settled) {
    let budget = DECODE_BUDGET;
    const order = [0, 1, 2, -1, 3, 4, 5, 6, -2, 7, 8, 9, 10];
    const seqs = settled ? [p.seq, p.lo] : [p.lo, p.seq];
    for (const k of order) {
      if (budget <= 0) break;
      const j = i - 1 + k * p.dir; // 0-based
      if (j < 0 || j >= p.scene.frames) continue;
      for (const seq of seqs) {
        if (budget <= 0) break;
        if (seq.decode(j)) budget--;
        if (!settled && k !== 0) break; // ahead of the gesture, only the light set is worth it
      }
    }
    return budget;
  }

  /** The best picture available for frame k right now: the full frame once the scroll has
   *  settled, the light one while it is moving, and the nearest of either rather than nothing. */
  function pick(p, k, settled) {
    const hi = p.seq.bitmaps.get(k);
    if (settled && hi) return hi;
    const lo = p.lo?.bitmaps.get(k);
    if (lo) return lo;
    return hi ?? p.lo?.nearest(k) ?? p.seq.nearest(k);
  }

  // Crossfade cut (scene "xfadeIn", in frames): over its first frames the scene fades in over
  // the previous scene's last frame, held still underneath (s02 crow -> s04 dog).
  const smooth = (t) => t * t * (3 - 2 * t);
  function xfadeAlpha(scene, f) {
    if (!scene.xfadeIn) return 1;
    return smooth(clamp((f - 1) / scene.xfadeIn, 0, 1));
  }

  // one exact frame, never a blend of two (a blend shows as a soft double image)
  function drawFrame(p, f, settled = true) {
    const bmp = pick(p, Math.round(f) - 1, settled);
    if (!bmp) return false;
    const a = xfadeAlpha(p.scene, f);
    if (a < 1) {
      const prevP = players[players.indexOf(p) - 1];
      const under = prevP && pick(prevP, prevP.scene.frames - 1, true);
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

  // A caption must survive momentum. On a Mac trackpad one flick keeps the page moving for a
  // second or more and covers thousands of pixels, so a caption hold of a few tens of vh used to
  // flash past unread and the scroll carried on into the next scene. Two rules fix that:
  //
  //  1. ARREST. The first time a flick reaches a caption, the scroll is pinned at the caption's
  //     own frame, which stops the momentum dead. It happens once per caption per approach, so
  //     the next gesture carries straight on through: the reader is stopped, never trapped.
  //  2. DWELL. Once shown, a caption stays for CAPTION_MIN_MS whatever the scroll does, and only
  //     a deliberate scroll after that takes it away.
  const CAPTION_MIN_MS = 1500; // a caption stays at least this long once it is up
  const FLICK_PX = 45; // scroll in one frame that counts as momentum rather than a careful move
  const PIN_MS = 380; // momentum keeps arriving after the first correction: hold the line
  let snapHeldUntil = 0; // while a caption is being read, snapping stays out of the way

  let lastY = 0;
  let pinY = null;
  let pinUntil = 0;
  const arrested = new Map(); // beat -> true while this approach has already been stopped

  /** page scroll position (px) of a frame inside scene p */
  const scrollOf = (p, f) => p.st.start + p.map.progressAt(f) * (p.st.end - p.st.start);

  /** Stop momentum at the first caption it runs into. Returns true if the scroll was pinned. */
  function arrestAtCaption(p, now) {
    const y = window.scrollY;
    const vy = y - lastY;
    lastY = y;
    // a correction already made: keep the scroll there until the momentum has spent itself
    if (pinY !== null) {
      if (now < pinUntil) {
        if (Math.abs(y - pinY) > 1) {
          window.scrollTo(0, pinY);
          lastY = pinY;
        }
        lastScrollT = now;
        return true;
      }
      pinY = null;
    }
    if (Math.abs(vy) < FLICK_PX) return false; // a careful scroll is never interfered with
    // Every caption on the page is a candidate, not just the scene in view: a hard flick can
    // clear a whole scene in two frames, and the first caption it flew past is the one to stop at.
    const prev = y - vy;
    let hit = null;
    for (const q of players) {
      for (const b of q.scene.beats) {
        if (!b.caption || arrested.get(b)) continue;
        // half a frame inside the range: stopping exactly on its first frame can land a hair
        // short of it, and the caption the arrest exists to show would not appear at all
        const gate = scrollOf(q, vy > 0 ? b.caption.from + 0.5 : b.caption.to - 0.5);
        const crossed = vy > 0 ? prev <= gate && y >= gate : prev >= gate && y <= gate;
        if (!crossed) continue;
        if (!hit || (vy > 0 ? gate < hit.gate : gate > hit.gate)) hit = { b, gate };
      }
    }
    if (hit) {
      arrested.set(hit.b, true);
      snapHeldUntil = now + CAPTION_MIN_MS + 250;
      pinY = Math.round(hit.gate);
      pinUntil = now + PIN_MS;
      window.scrollTo(0, pinY);
      lastY = pinY;
      lastScrollT = now;
      return true;
    }
    // re-arm a caption once the reader has left its hold well behind
    for (const q of players) {
      for (const b of q.scene.beats) {
        if (!b.caption || !arrested.get(b)) continue;
        const lo = scrollOf(q, b.hold[0]) - window.innerHeight;
        const hi = scrollOf(q, b.hold[1]) + window.innerHeight;
        if (y < lo || y > hi) arrested.delete(b);
      }
    }
    return false;
  }

  // Caption: up whenever the scroll is inside its frame range, and for CAPTION_MIN_MS after it
  // leaves — so momentum carrying the page past cannot snatch the text away half-read. It is the
  // frame range that rules, not the gesture: resting on a caption's frame always shows its text.
  let capBeat = null;
  let capT = 0;
  function updateCaption(p, scrollF, now) {
    const b = p.scene.beats.find((x) => x.caption && scrollF >= x.caption.from && scrollF <= x.caption.to);
    if (b && b !== capBeat) {
      capBeat = b;
      capT = now;
      // placement: the caption's own "at", else the scene's "captionAt", else bottom centre
      captionLight.set(b.caption.label, b.caption.text, {
        at: b.caption.at ?? p.scene.captionAt,
        lights: !!b.caption.lights,
        align: b.caption.align ?? p.scene.captionAlign,
        set,
        key: `${p.scene.id}:${b.caption.label}`,
      });
    }
    const dwelling = capBeat && now - capT < CAPTION_MIN_MS;
    if (!b && !dwelling) capBeat = null;
    const show = !!(b || dwelling);
    caption.classList.toggle("is-shown", show);
    // the lit layer belongs to the caption: it goes when the caption goes, not when the next
    // caption happens to replace it
    captionLight.shown(show);
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
    const prevTickT = lastT;
    lastT = now;
    activate(inView());
    const p = active;
    const { scene, map } = p;
    const scrollF = map.frameAt(p.progress);
    const settled = now - lastScrollT > SETTLE_MS && Math.abs(scrollF - p.cur) < 0.75;
    let budget = DECODE_BUDGET;

    if (reduceMotion()) {
      // WEB.md: no scrubbing; the nearest beat's frame crossfades in (s01: out to black at the end)
      const fadeOut = scene.fadeOut && p.progress >= map.progressAt(scene.frames - scene.fadeOut);
      reducedAlpha = clamp(reducedAlpha + Math.sign((fadeOut ? 0 : 1) - reducedAlpha) * dt * 2.5, 0, 1);
      const beat = scene.beats.reduce((a, b) => (Math.abs(b.stop - scrollF) < Math.abs(a.stop - scrollF) ? b : a));
      p.cur = beat.stop;
      budget = decodeAround(p, p.cur, true);
      stage.ctx.fillStyle = "#000";
      stage.ctx.fillRect(0, 0, stage.canvas.width, stage.canvas.height);
      const bmp = pick(p, p.cur - 1, true);
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
      p.cur += (target - p.cur) * (1 - Math.exp(-dt / (settled ? SMOOTH_S : SMOOTH_MOVING_S)));
      if (Math.abs(target - p.cur) < 0.002) p.cur = target;
      if (p.cur !== prev) p.dir = p.cur > prev ? 1 : -1;

      budget = decodeAround(p, Math.round(target), settled);
      if (!drawFrame(p, p.cur, settled)) {
        stage.ctx.fillStyle = "#000";
        stage.ctx.fillRect(0, 0, stage.canvas.width, stage.canvas.height);
      }
      // s01's out: fade to black over the last frames (no close-up cloud render)
      // (reaches full black one frame early: the scroll's end can stop a hair short of 1)
      if (scene.fadeOut) blackout(clamp((p.cur - (scene.frames - scene.fadeOut)) / (scene.fadeOut - 1), 0, 1));
    }
    p.seq.evict(Math.round(p.cur) - 1);
    p.lo?.evict(Math.round(p.cur) - 1);
    setPlace(scene.id, p.cur);

    // neighbours: the next scene's opening frames ready near the cut, the previous scene's last
    // frames ready for scrolling back; everything else out of view is freed
    const k = players.indexOf(p);
    const next = players[k + 1];
    const prevP = players[k - 1];
    for (const q of players) {
      if (q === p) continue;
      if (q === next && p.cur > scene.frames - 10) {
        for (let j = 0; j < IDLE_KEEP && budget > 0; j++) if (q.lo.decode(j) || q.seq.decode(j)) budget--;
        q.seq.evict(0, false, IDLE_KEEP);
        q.lo.evict(0, false, IDLE_KEEP);
      } else if (q === prevP && p.cur < 10) {
        const end = q.scene.frames - 1;
        for (let j = 0; j < IDLE_KEEP && budget > 0; j++) if (q.lo.decode(end - j) || q.seq.decode(end - j)) budget--;
        q.seq.evict(end, false, IDLE_KEEP);
        q.lo.evict(end, false, IDLE_KEEP);
      } else {
        q.seq.evict(q === next ? 0 : q.scene.frames - 1, false, 0);
        q.lo?.evict(q === next ? 0 : q.scene.frames - 1, false, 0);
      }
    }

    if (!reduceMotion()) arrestAtCaption(p, now);
    updateCaption(p, scrollF, now);

    // ?probe in the URL records the scrub loop so pacing problems can be measured, not guessed
    if (window.__probe) {
      window.__probe.push([
        Math.round(now),
        prevTickT ? Math.round(now - prevTickT) : 0, // ms since the last tick (frame budget)
        +p.cur.toFixed(2), // frame actually drawn
        +scrollF.toFixed(2), // frame the scroll is asking for
        p.seq.bitmaps.has(Math.round(p.cur) - 1) ? 1 : 0, // 1 = exact frame, 0 = a stand-in
        Math.round(window.scrollY),
      ]);
    }
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
