// Scene 8 — the finale. The hilltop view rendered in Blender, brought to life in the browser
// (finaleBackdrop.js: clean still, flag loop, swaying tree, kite and grass), and fireworks over it.
// The s01 still in index.html (s01 at its locked hold) is only the fallback until the backdrop's
// textures have loaded, or if they fail to.
//
// The fireworks are a single Points cloud with a fixed pool, simulated in screen space under an
// orthographic camera of one unit per pixel: "a third of the way up the sky" then means exactly
// that, whatever the window. One geometry, one draw call, no textures, and the pool is reused
// rather than reallocated.

import { createBackdrop } from "./finaleBackdrop.js";
import { createSparkText } from "./finaleSparkText.js";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  OrthographicCamera,
  Points,
  Scene,
  ShaderMaterial,
  WebGLRenderer,
} from "three";

const POOL = 2600; // particles alive at once, across every shell
const SHELL = 110; // sparks in one burst
const GRAVITY = 185; // px/s^2, gentle: a firework hangs longer than it falls
const DRAG_K = 0.8; // air resistance PER SECOND. Applied per frame, as it was at first, a
                    // spark lost 99.99% of its speed in a second and the burst never opened.
const LIFE = [1.5, 2.6];
// entry: a focus pull (owner 2026-11-21: "i dont like zoom transition" -> chose focus pull). The
// valley opens as soft bokeh and racks into sharp focus over the first part of the scroll.
const FOCUS_END = 0.4; // section progress at which the valley is sharp
const BLUR_MAX = 18; // px of blur at the start, at a 1920 px wide stage
// the way in from scene 7 (owner 2026-11-21): s07 ends on a full-frame gold glow; a firework rendered
// in Blender (scripts/s08_burst.py) starts on that same gold (its frame 3 is within ~8 levels of it),
// bursts into sparks over black, and the out-of-focus valley fades in under the falling sparks
const GLOW_END = 0.02; // s07's gold frame has crossfaded into the burst
const BURST_END = 0.13; // the burst has played its frames (scroll-driven, so it also runs back)
const BURST_FIRST = 3; // burst frame that matches s07's gold
const VALLEY_IN = [0.05, 0.16]; // the black under the burst lifts off the valley

// gold, as the owner asked: the range a real shell burns through, from white-hot at the centre
// to amber at the edge, with one warmer ember tone among them
const SPARK_HUES = [0xffd27a, 0xfff6d8, 0xffb347, 0xffc861, 0xff9a2e, 0xffe9a8];

export function createFinale(section, { reduceMotion, onBurst = null }) {
  const stage = section.querySelector("[data-stage]") ?? section;
  const still = section.querySelector("[data-still]");

  // the hilltop view: clean still + flag loop + swaying tree, kite and grass (finaleBackdrop.js)
  const backdrop = createBackdrop(stage, still);
  // the closing शुभ तिहार is gilded and lit by the fireworks: each burst flares across the gold
  // where it opened (owner 2026-11-21 chose "gilded, firework-lit")
  const title = section.querySelector(".finale__title");
  let titleFlash = 0;
  let sparkText = null;

  // the hidden cut from scene 7 (owner 2026-11-21: "the 2nd last scene ends in golden ... make it
  // seamless"): s07 ends on a full-frame warm gold glow, so scene 8 opens on that exact frame, laid
  // over everything, and lets it fade as the out-of-focus valley appears behind it
  const glow = document.createElement("img");
  glow.className = "finale__glow";
  glow.alt = "";
  glow.setAttribute("aria-hidden", "true");
  glow.src = `/frames/s07_bhaitika/${window.innerWidth / window.innerHeight <= 1 ? "m" : "d"}/0272.webp`;
  const veil = document.createElement("div"); // the black between the gold and the valley
  veil.className = "finale__veil";
  veil.setAttribute("aria-hidden", "true");
  // the rendered burst, ADDED as light over the black and the valley (CSS plus-lighter)
  const burstEl = document.createElement("img");
  burstEl.className = "finale__burst";
  burstEl.alt = "";
  burstEl.setAttribute("aria-hidden", "true");
  const burstFrames = [];
  for (let i = 1; i <= 36; i++) {
    const im = new Image();
    im.src = `/frames/s08_finale/hybrid/burst/${String(i).padStart(4, "0")}.webp`;
    burstFrames.push(im);
  }
  let burstShown = -1;
  burstEl.src = burstFrames[BURST_FIRST - 1].src;

  const canvas = document.createElement("canvas");
  canvas.className = "finale__canvas";
  canvas.setAttribute("aria-hidden", "true");

  const renderer = new WebGLRenderer({ canvas, alpha: true, antialias: false });
  renderer.setClearAlpha(0);
  const scene = new Scene();
  const camera = new OrthographicCamera(0, 1, 1, 0, -10, 10);

  // --- the pool ------------------------------------------------------------------------------
  const pos = new Float32Array(POOL * 3);
  const col = new Float32Array(POOL * 3);
  const size = new Float32Array(POOL);
  const alpha = new Float32Array(POOL);
  const vel = new Float32Array(POOL * 2); // simulated on the CPU; the GPU only draws
  const life = new Float32Array(POOL);
  const age = new Float32Array(POOL);
  const hueOf = new Uint32Array(POOL); // a shell remembers its colour, to burst in it
  const kind = new Uint8Array(POOL); // 0 = dead, 1 = climbing shell, 2 = spark
  let cursor = 0;

  const geometry = new BufferGeometry();
  // BufferAttribute, NOT Float32BufferAttribute: the typed-array subclasses copy what they are
  // given, so the simulation would write into one array while the GPU read another, and every
  // particle would sit at the origin for ever.
  geometry.setAttribute("position", new BufferAttribute(pos, 3));
  geometry.setAttribute("aColor", new BufferAttribute(col, 3));
  geometry.setAttribute("aSize", new BufferAttribute(size, 1));
  geometry.setAttribute("aAlpha", new BufferAttribute(alpha, 1));

  const material = new ShaderMaterial({
    transparent: true,
    depthWrite: false,
    depthTest: false,
    blending: AdditiveBlending,
    vertexShader: `
      attribute float aSize;
      attribute float aAlpha;
      attribute vec3 aColor;
      varying vec3 vColor;
      varying float vAlpha;
      void main() {
        vColor = aColor;
        vAlpha = aAlpha;
        gl_PointSize = aSize;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      varying vec3 vColor;
      varying float vAlpha;
      void main() {
        float d = length(gl_PointCoord - vec2(0.5));
        if (d > 0.5 || vAlpha <= 0.0) discard;
        // a hot core inside a soft halo: that is how a spark reads against a night sky
        float core = pow(1.0 - d * 2.0, 2.4);
        float halo = pow(1.0 - d * 2.0, 1.0) * 0.55;
        float v = (core * 1.7 + halo) * vAlpha;
        gl_FragColor = vec4(vColor * v, min(v, 1.0));
      }
    `,
  });

  const points = new Points(geometry, material);
  points.frustumCulled = false;
  scene.add(points);

  let W = 1;
  let H = 1;
  let running = false;
  let raf = 0;
  let last = 0;
  let progress = 0;
  let nextShell = 0;
  const tint = new Color();

  function resize() {
    W = canvas.clientWidth || window.innerWidth;
    H = canvas.clientHeight || window.innerHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.setSize(W, H, false);
    camera.left = 0;
    camera.right = W;
    camera.top = H;
    camera.bottom = 0;
    camera.updateProjectionMatrix();
  }

  /** The pool is a ring: the oldest particle gives way, so a burst never fails to appear. */
  function take() {
    for (let n = 0; n < POOL; n++) {
      cursor = (cursor + 1) % POOL;
      if (kind[cursor] === 0) return cursor;
    }
    cursor = (cursor + 1) % POOL;
    return cursor;
  }

  function paint(i, hex) {
    tint.setHex(hex);
    col[i * 3] = tint.r;
    col[i * 3 + 1] = tint.g;
    col[i * 3 + 2] = tint.b;
    hueOf[i] = hex;
  }

  /** Send one shell up from somewhere over the city. */
  function launch() {
    const i = take();
    kind[i] = 1;
    pos[i * 3] = W * (0.12 + Math.random() * 0.76);
    pos[i * 3 + 1] = -20;
    pos[i * 3 + 2] = 0;
    vel[i * 2] = (Math.random() - 0.5) * 40;
    vel[i * 2 + 1] = H * (0.62 + Math.random() * 0.3); // enough climb to reach the upper sky
    paint(i, SPARK_HUES[(Math.random() * SPARK_HUES.length) | 0]);
    size[i] = 7;
    alpha[i] = 1;
    age[i] = 0;
    life[i] = 0.75 + Math.random() * 0.45;
  }

  /** Burst a shell into sparks, all of one colour, as a real shell is. */
  function burst(x, y, hex, count = SHELL, grand = 1) {
    const speed = (300 + Math.random() * 330) * grand;
    // the bang, on the same frame as the flash (audio.js fireworkBurst)
    onBurst?.({ pan: (x / W) * 2 - 1, size: grand });
    if (title) {
      titleFlash = Math.min(1, titleFlash + 0.55 * grand);
      title.style.setProperty("--fx", `${((x / W) * 100).toFixed(1)}%`);
    }
    for (let k = 0; k < count; k++) {
      const i = take();
      kind[i] = 2;
      pos[i * 3] = x;
      pos[i * 3 + 1] = y;
      pos[i * 3 + 2] = 0;
      // a sphere of sparks seen flat: denser at the ring's edge, which is what gives it shape
      const a = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random());
      vel[i * 2] = Math.cos(a) * speed * r;
      vel[i * 2 + 1] = Math.sin(a) * speed * r;
      paint(i, hex);
      size[i] = (7 + Math.random() * 7) * (grand > 1 ? 1.35 : 1);
      alpha[i] = 1;
      age[i] = 0;
      life[i] = (LIFE[0] + Math.random() * (LIFE[1] - LIFE[0])) * grand;
    }
  }

  function step(dt) {
    const decay = Math.exp(-DRAG_K * dt);
    for (let i = 0; i < POOL; i++) {
      if (kind[i] === 0) continue;
      age[i] += dt;
      const t = age[i] / life[i];
      if (t >= 1) {
        // a shell that has run out of climb is a shell at the top of its arc
        if (kind[i] === 1) burst(pos[i * 3], pos[i * 3 + 1], hueOf[i]);
        kind[i] = 0;
        alpha[i] = 0;
        continue;
      }
      if (kind[i] === 2) {
        vel[i * 2] *= decay;
        vel[i * 2 + 1] *= decay;
      }
      vel[i * 2 + 1] -= GRAVITY * dt;
      pos[i * 3] += vel[i * 2] * dt;
      pos[i * 3 + 1] += vel[i * 2 + 1] * dt;
      // sparks fade across their life; a climbing shell only flickers
      alpha[i] = kind[i] === 1 ? 0.8 + Math.random() * 0.2 : Math.pow(1 - t, 1.15);
    }
    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.aColor.needsUpdate = true;
    geometry.attributes.aSize.needsUpdate = true;
    geometry.attributes.aAlpha.needsUpdate = true;
  }

  function frame(now) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    backdrop.tick(dt);
    if (title && titleFlash > 0.002) {
      titleFlash *= Math.exp(-2.6 * dt);
      title.style.setProperty("--flash", titleFlash.toFixed(3));
    }
    // no other firework until the rendered opening burst has finished (owner 2026-11-21: "other
    // firework should only start after our main transition firework finishes")
    if (progress < BURST_END) nextShell = 0.35;
    else nextShell -= dt;
    if (nextShell <= 0) {
      launch();
      if (progress > 0.55 && Math.random() < 0.45) launch(); // the sky fills toward the end
      nextShell = 0.62 - Math.min(0.38, progress * 0.45) + Math.random() * 0.4;
    }
    step(dt);
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }

  return {
    canvas,
    mount() {
      stage.append(canvas);
      stage.append(backdrop.canvas); // hill, flag, kite, tree, grass: in FRONT of the fireworks
      stage.append(veil, burstEl, glow); // above the fireworks too: s07's last frame has none
      resize();
      window.addEventListener("resize", resize);
      backdrop.load();
      // the two lines over the valley are written in firework sparks (finaleSparkText.js)
      sparkText = createSparkText([...section.querySelectorAll(".finale__line")], { reduceMotion });
      renderer.render(scene, camera);
    },








    /** ?probe: the hilltop backdrop (loop phase, snapshots) */
    get backdrop() {
      return backdrop;
    },

    /** ?probe: what the sky is doing */
    get stats() {
      let alive = 0;
      for (let i = 0; i < POOL; i++) if (kind[i]) alive++;
      return { alive, running, bound: geometry.attributes.position.array === pos, W, H };
    },

    /** 0..1 through the section: the rate of fire, and the focus pull onto the valley */
    setProgress(p) {
      progress = Math.min(1, Math.max(0, p));
      // the scene opens out of focus (city lights as soft bokeh, a touch brighter) and racks
      // into focus; nothing moves or scales
      const f = Math.min(1, progress / FOCUS_END);
      const e = f * f * (3 - 2 * f);
      const blur = BLUR_MAX * (1 - e) * ((stage.clientWidth || window.innerWidth) / 1920);
      const look = blur > 0.05 ? `blur(${blur.toFixed(2)}px) brightness(${(1 + 0.15 * (1 - e)).toFixed(3)})` : "none";
      if (still) still.style.filter = look;
      backdrop.setFilter(look);
      // s07's gold -> the rendered burst (its matching gold frame first) -> sparks over black,
      // and the valley fades in from the black under them
      const ease = (x) => x * x * (3 - 2 * x);
      const ramp = (a, b) => ease(Math.min(1, Math.max(0, (progress - a) / (b - a))));
      const gk = ramp(0, GLOW_END);
      glow.style.opacity = (1 - gk).toFixed(3);
      glow.style.visibility = gk < 0.999 ? "inherit" : "hidden";
      const bf = Math.min(1, progress / BURST_END);
      const fi = Math.min(35, BURST_FIRST - 1 + Math.floor(bf * (36 - BURST_FIRST + 1)));
      if (fi !== burstShown && burstFrames[fi].complete) {
        burstEl.src = burstFrames[fi].src;
        burstShown = fi;
      }
      burstEl.style.visibility = progress < BURST_END ? "inherit" : "hidden";
      const vb = ramp(VALLEY_IN[0], VALLEY_IN[1]);
      veil.style.opacity = (1 - vb).toFixed(3);
      veil.style.visibility = vb < 0.999 ? "inherit" : "hidden";
    },
    play() {
      if (running || reduceMotion()) return;
      running = true;
      last = performance.now();
      nextShell = 0.35; // first shell shortly after the opening burst is done (see frame())
      raf = requestAnimationFrame(frame);
    },
    pause() {
      running = false;
      cancelAnimationFrame(raf);
    },
    dispose() {
      this.pause();
      window.removeEventListener("resize", resize);
      backdrop.dispose();
      sparkText?.dispose();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      canvas.remove();
      glow.remove();
      veil.remove();
      burstEl.remove();
    },
  };
}
