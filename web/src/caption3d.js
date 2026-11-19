// The caption in real 3D (CLAUDE.md: text is the one thing the browser may render itself).
//
// Lights hang from the shirorekha — the line Devanagari already draws across the top of every
// word — and they are real lights: each bulb carries a THREE.PointLight, so the colour falling
// on the letters is light actually landing on a lit surface, not a text-shadow pretending to be
// one. The words stand in front of their own drop shadows and the bulbs hang in front of the
// words, so the depth is real depth, resolved by the depth buffer.
//
// The glyphs come from the browser's own text engine: each word is rasterised to a canvas with
// fillText and used as a texture. That matters more here than anywhere else — Devanagari needs
// real shaping (matra reordering, conjuncts, the unbroken shirorekha), and no WebGL text library
// does it as reliably as the engine already running the page. Nothing splits a character; a word
// is rasterised whole.
//
// One render loop, drawn on demand: the page's own rAF drives everything else, so this renders
// only when the pointer moves or the caption changes (web3d-integration-patterns: coordinate the
// loops, never run two).

import {
  AmbientLight,
  DataTexture,
  RGBAFormat,
  BufferGeometry,
  CanvasTexture,
  Color,
  Float32BufferAttribute,
  Group,
  Line,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  PointLight,
  PCFSoftShadowMap,
  Scene,
  ShadowMaterial,
  AdditiveBlending,
  SphereGeometry,
  Vector3,
  RepeatWrapping,
  SRGBColorSpace,
  PMREMGenerator,
  EquirectangularReflectionMapping,
  TextureLoader,
  WebGLRenderer,
} from "three";

const FOV = 32;
const PAD = 18; // texture padding around a word, so glow and lighting are not clipped
const BULB_R = 3.6;
const Z_WORD = 0;
const Z_BULB = 34; // bulbs hang in front of the words
const LIGHT_DIST = 320;
const BULB_IDLE = 260; // candela: a bulb at rest, just warming the letters above it
const BULB_LIT = 17000; // and fully lit, when the reader's flame comes near
const FLAME_I = 12000; // kept low: the bulbs' colours must read on the letters, not be
                       // washed out by the reader's own warm light
const CREAM = 0xfff4e0;
const SMOKE_IN_MS = 900;
const SMOKE_OUT_MS = 620;
const VERMILION = 0xe0583a; // abir, at the brightness powder actually has in daylight: the
                            // token red (#b3202a) is too dark to read against the colonnade
const POWDER_IN_MS = 760;
const POWDER_OUT_MS = 680;
const GRAV = 4200; // px/s^2: the world is measured in pixels, so gravity is too
const SWING_DRAG = 0.985; // air: how much of each bead's momentum survives a frame
const GOLD = 0xd8a73f; // the murti's gilding
const PEARL = 0xe98ba8; // and the pink pearls set into it
const LAMP_I = 5200; // candela, in a world measured in pixels
const MALA_HEADS = 9; // how many flowers on each strand
const POINTER_REACH = 130; // px around the cursor that actually disturbs the flowers
const INK = 0x14181f; // the crow's blue-black: dark type, because this frame is bright everywhere
const BITES = 7; // how many times the crow goes at the line
const PECK_MS = 480; // a crow pecks fast; at 820ms the line outstayed every other caption
const LAY_RAD = 0.82; // how far the words tip onto the ledge they are lying on
const WOOD = 0xe3c79a; // aged wood, pale enough to stay legible over a dark chamber
const MARGIN = 70; // room round the caption for the drops and the light that spills off it

const HUES = [0xf2a33a, 0x6fb0e0, 0x8ccfa2, 0xe291ad]; // the valley's own lights

/** A normal map for one word, built from its own glyph coverage.
 *
 *  The alpha of the rasterised word is read as a height field, softened, and turned into
 *  surface normals with a Sobel pass. The height is NEGATIVE inside the strokes, so the letters
 *  read as cut INTO the surface rather than raised off it: a raking light then catches one wall
 *  of every stroke and leaves the other in shadow, the way a chisel cut in the chamber's
 *  woodwork would. Nothing about the glyphs is altered — only how light falls on them.
 */
function carveNormals(ctx, w, h) {
  const src = ctx.getImageData(0, 0, w, h).data;
  const height = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) height[i] = -src[i * 4 + 3] / 255; // alpha, cut inward

  // separable box blur: a hard edge gives a hard, plastic bevel
  const R = 2;
  const tmp = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let sum = 0;
      let n = 0;
      for (let k = -R; k <= R; k++) {
        const xx = x + k;
        if (xx < 0 || xx >= w) continue;
        sum += height[y * w + xx];
        n++;
      }
      tmp[y * w + x] = sum / n;
    }
  }
  for (let x = 0; x < w; x++) {
    for (let y = 0; y < h; y++) {
      let sum = 0;
      let n = 0;
      for (let k = -R; k <= R; k++) {
        const yy = y + k;
        if (yy < 0 || yy >= h) continue;
        sum += tmp[yy * w + x];
        n++;
      }
      height[y * w + x] = sum / n;
    }
  }

  const out = new Uint8Array(w * h * 4);
  const S = 2.6; // how deep the cut reads
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const l = height[i - (x > 0 ? 1 : 0)];
      const r = height[i + (x < w - 1 ? 1 : 0)];
      const u = height[i - (y > 0 ? w : 0)];
      const d = height[i + (y < h - 1 ? w : 0)];
      const nx = (l - r) * S;
      const ny = (u - d) * S;
      const len = Math.hypot(nx, ny, 1);
      out[i * 4] = ((nx / len) * 0.5 + 0.5) * 255;
      out[i * 4 + 1] = ((ny / len) * 0.5 + 0.5) * 255;
      out[i * 4 + 2] = (1 / len) * 255;
      out[i * 4 + 3] = 255;
    }
  }
  const tex = new DataTexture(out, w, h, RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}

/** Soft value noise, shared by every word: the shape the smoke takes as it gives up the letters. */
let smokeTex = null;
function smokeNoise() {
  if (smokeTex) return smokeTex;
  const N = 128;
  const c = document.createElement("canvas");
  c.width = c.height = N;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(N, N);
  const grid = 10;
  const pts = [];
  for (let i = 0; i < grid * grid; i++) pts.push(Math.random());
  const at = (gx, gy) => pts[((gy + grid) % grid) * grid + ((gx + grid) % grid)];
  const fade = (t) => t * t * (3 - 2 * t);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const fx = (x / N) * grid;
      const fy = (y / N) * grid;
      const gx = Math.floor(fx);
      const gy = Math.floor(fy);
      const tx = fade(fx - gx);
      const ty = fade(fy - gy);
      const a = at(gx, gy) * (1 - tx) + at(gx + 1, gy) * tx;
      const b = at(gx, gy + 1) * (1 - tx) + at(gx + 1, gy + 1) * tx;
      // a second, finer octave frays the edge so it tears like smoke, not like a wipe
      const v = (a * (1 - ty) + b * ty) * 0.75 + Math.random() * 0.25;
      const i = (y * N + x) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v * 255;
      img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  ctx.filter = "blur(2px)";
  ctx.drawImage(c, 0, 0);
  smokeTex = new CanvasTexture(c);
  smokeTex.wrapS = smokeTex.wrapT = RepeatWrapping;
  return smokeTex;
}

/** Let a word be eaten by smoke: the standard material keeps its lighting, and loses its alpha
 *  wherever the smoke has not yet cleared. uReveal 0 = all smoke, 1 = the word fully given up. */
function addSmoke(material, uniforms) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uReveal = uniforms.uReveal;
    shader.uniforms.uSmoke = uniforms.uSmoke;
    shader.uniforms.uDrift = uniforms.uDrift;
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
         uniform float uReveal;
         uniform float uDrift;
         uniform sampler2D uSmoke;`
      )
      .replace(
        "#include <dithering_fragment>",
        `#include <dithering_fragment>
         float n = texture2D(uSmoke, vMapUv * vec2(1.6, 0.9) + vec2(uDrift * 0.5, -uDrift)).r;
         float edge = smoothstep(n - 0.22, n + 0.10, uReveal);
         // the letters glow warm along the line where the smoke is still letting go
         float lip = (1.0 - abs(uReveal - n) * 7.0) * 0.6;
         gl_FragColor.rgb += vec3(0.55, 0.32, 0.12) * max(lip, 0.0) * edge;
         gl_FragColor.a *= edge;`
      );
  };
  material.customProgramCacheKey = () => "smoke";
}

/** Abir: the word is powder rather than paint.
 *
 *  The fill is broken up by a fine grain and the edge is left slightly crumbly, so it reads as
 *  pigment pressed onto a surface instead of type drawn on one. uPress blooms each word outward
 *  from its own centre, the way a tika is pressed on with the thumb; uScatter lifts the powder
 *  off and carries it away. The glyphs themselves are never touched.
 */
function addPowder(material, uniforms, seed) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uPress = uniforms.uPress;
    shader.uniforms.uScatter = uniforms.uScatter;
    shader.uniforms.uGrain = uniforms.uGrain;
    shader.uniforms.uSeed = { value: seed };
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
         uniform float uPress;
         uniform float uScatter;
         uniform float uSeed;
         uniform sampler2D uGrain;`
      )
      .replace(
        "#include <dithering_fragment>",
        `#include <dithering_fragment>
         float grain = texture2D(uGrain, vMapUv * 7.0 + uSeed).r;
         // a crumbly edge: the grain eats into the outline, never evenly
         gl_FragColor.a *= 0.70 + 0.30 * grain;
         gl_FragColor.rgb *= 0.86 + 0.26 * grain;

         // pressed on from the middle outward
         float d = distance(vMapUv, vec2(0.5, 0.5));
         gl_FragColor.a *= smoothstep(d - 0.26, d + 0.02, uPress * 1.3);

         // and lifted away again: the powder drifts up and thins as it goes
         if (uScatter > 0.0) {
           vec2 drift = vec2((grain - 0.5) * 0.10, -0.13) * uScatter;
           float lifted = texture2D(map, vMapUv + drift).a;
           gl_FragColor.a = mix(gl_FragColor.a, lifted * (0.5 + 0.5 * grain), uScatter);
           gl_FragColor.a *= 1.0 - uScatter * uScatter;
         }`
      );
  };
  material.customProgramCacheKey = () => "powder";
}

/** Bites taken out of a word, one after another, the way the crow takes the sel roti.
 *  Each bite is a disc in the word's own UV space that opens quickly once its turn comes; the
 *  glyphs are never redrawn, only eaten. uEaten 0 = whole, 1 = gone. */
function addPeck(material, uniforms) {
  const bites = [];
  for (let i = 0; i < BITES; i++) {
    // across the word, roughly on the line of the glyphs, each a different size
    bites.push(
      new Vector3(0.12 + (i / BITES) * 0.78 + (Math.random() - 0.5) * 0.08, 0.38 + Math.random() * 0.26, 0.13 + Math.random() * 0.1)
    );
  }
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uEaten = uniforms.uEaten;
    shader.uniforms.uBites = { value: bites };
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
         uniform float uEaten;
         uniform vec3 uBites[${BITES}];`
      )
      .replace(
        "#include <dithering_fragment>",
        `#include <dithering_fragment>
         float bitten = 1.0;
         for (int i = 0; i < ${BITES}; i++) {
           float turn = clamp((uEaten - float(i) * ${(1 / BITES).toFixed(3)}) * 5.0, 0.0, 1.0);
           float r = uBites[i].z * turn;
           bitten *= smoothstep(r * 0.72, r, distance(vMapUv, uBites[i].xy));
         }
         gl_FragColor.a *= bitten;`
      );
  };
  material.customProgramCacheKey = () => "peck";
}

/** One sayapatri head, painted petal by petal.
 *
 *  A marigold is not a bead: it is a tight ball of many short, ruffled petals, deeper orange in
 *  the hollow at its centre and paler at the rim, and its outline is lumpy rather than round.
 *  So the texture is drawn as rings of individual petals — more of them, and larger, further
 *  out — each with its own jitter of hue, size and angle, over a dark centre that reads as the
 *  shadow between them. Wrapped on a sphere and lit by the scene's own light, that is enough to
 *  pass at the size these sit at.
 */
let marigoldTex = null;
function marigoldTexture() {
  if (marigoldTex) return marigoldTex;
  const N = 320;
  const c = document.createElement("canvas");
  c.width = c.height = N;
  const x = c.getContext("2d");
  const mid = N / 2;

  // Petals are drawn onto transparency, so the head keeps the lumpy outline a marigold has.
  // A sphere wrapped in this read as a shiny ball with a smear on it; a flat head that faces
  // the reader, with the shading painted in, reads as the flower.
  const petal = (cx, cy, r, ang, hue, light) => {
    x.save();
    x.translate(cx, cy);
    x.rotate(ang);
    const g = x.createLinearGradient(0, r * 0.6, 0, -r);
    g.addColorStop(0, `hsl(${hue - 8} 95% ${Math.max(12, light - 20)}%)`); // shaded root
    g.addColorStop(1, `hsl(${hue} 96% ${light}%)`); // lit tip
    x.fillStyle = g;
    x.beginPath();
    x.moveTo(0, r * 0.75);
    x.quadraticCurveTo(r * 0.85, r * 0.3, r * 0.46, -r * 0.78);
    x.quadraticCurveTo(r * 0.2, -r * 0.5, 0, -r * 0.92); // the notch in the tip
    x.quadraticCurveTo(-r * 0.2, -r * 0.5, -r * 0.46, -r * 0.78);
    x.quadraticCurveTo(-r * 0.85, r * 0.3, 0, r * 0.75);
    x.fill();
    x.restore();
  };

  // outer rings first, so the inner ones sit on top the way the head packs
  const rings = [
    { at: 0.4, n: 20, r: 0.15, hue: 36, light: 52 },
    { at: 0.32, n: 17, r: 0.14, hue: 33, light: 56 },
    { at: 0.23, n: 14, r: 0.13, hue: 29, light: 52 },
    { at: 0.14, n: 11, r: 0.12, hue: 25, light: 45 },
    { at: 0.06, n: 7, r: 0.1, hue: 22, light: 38 },
  ];
  for (const ring of rings) {
    for (let i = 0; i < ring.n; i++) {
      const a = (i / ring.n) * Math.PI * 2 + Math.random() * 0.3;
      const rad = N * (ring.at + (Math.random() - 0.5) * 0.04);
      petal(
        mid + Math.cos(a) * rad,
        mid + Math.sin(a) * rad,
        N * ring.r * (0.82 + Math.random() * 0.36),
        a + Math.PI / 2 + (Math.random() - 0.5) * 0.6,
        ring.hue + (Math.random() - 0.5) * 10,
        ring.light + (Math.random() - 0.5) * 10
      );
    }
  }

  // one light direction over the whole head, so a rope of them shares a sun
  x.globalCompositeOperation = "source-atop";
  const lit = x.createLinearGradient(0, 0, N * 0.9, N);
  lit.addColorStop(0, "rgba(255,230,150,0.34)");
  lit.addColorStop(0.5, "rgba(0,0,0,0)");
  lit.addColorStop(1, "rgba(60,20,0,0.42)");
  x.fillStyle = lit;
  x.fillRect(0, 0, N, N);

  marigoldTex = new CanvasTexture(c);
  marigoldTex.colorSpace = SRGBColorSpace;
  return marigoldTex;
}

// The marks a diyo may stand in for: candrabindu, anusvara, visarga. Each is a small round
// thing already sitting above the line — a moon-dot waiting to be a lamp.
const LAMP_MARKS = /[\u0901\u0902\u0903]/;

/** Where each such mark sits along a word, in px from the word's left edge.
 *  These marks carry no advance of their own, so the mark belongs over the middle of the
 *  letter before it: measure the text up to that letter, and up to and including it. */
function markSpots(ctx, text) {
  const out = [];
  for (let i = 1; i < text.length; i++) {
    if (!LAMP_MARKS.test(text[i])) continue;
    const upToBase = ctx.measureText(text.slice(0, i)).width;
    const beforeBase = ctx.measureText(text.slice(0, i - 1)).width;
    out.push((beforeBase + upToBase) / 2);
  }
  return out;
}

/** The diyo is not drawn: it is cut from the film.
 *
 *  Scene 0 is a photoreal close-up of a clay diyo burning, rendered in Blender like everything
 *  else on this site, so the lamps on the caption are that same lamp — the bowl below the flame
 *  and the flame above it, keyed out of the render by luminance (scripts kept the originals in
 *  renders/s00_enter). Hand-drawing a lamp could only ever be a worse version of one we have.
 */
const sprites = new TextureLoader();
let bowlTex = null;
let flameTex = null;
function diyoTexture() {
  if (!bowlTex) {
    bowlTex = sprites.load(`${import.meta.env.BASE_URL}sprites/diyo_bowl.png`);
    bowlTex.colorSpace = SRGBColorSpace;
  }
  return bowlTex;
}
function flameTexture() {
  if (!flameTex) {
    flameTex = sprites.load(`${import.meta.env.BASE_URL}sprites/diyo_flame.png`);
    flameTex.colorSpace = SRGBColorSpace;
  }
  return flameTex;
}

/** Metal with nothing to reflect is just black, so the gilt captions get a room to stand in:
 *  a warm lamp-lit haze above, dark floor below, which is what the shrine actually looks like.
 *  Cheap — one 64px gradient, convolved once. */
let envTex = null;
function roomEnv(renderer) {
  if (envTex) return envTex;
  const c = document.createElement("canvas");
  c.width = 32;
  c.height = 64;
  const x = c.getContext("2d");
  const g = x.createLinearGradient(0, 0, 0, 64);
  g.addColorStop(0, "#5a3a1c");
  g.addColorStop(0.45, "#c98b43");
  g.addColorStop(0.62, "#54301a");
  g.addColorStop(1, "#120a06");
  x.fillStyle = g;
  x.fillRect(0, 0, 32, 64);
  const tex = new CanvasTexture(c);
  tex.mapping = EquirectangularReflectionMapping;
  tex.colorSpace = SRGBColorSpace;
  const pmrem = new PMREMGenerator(renderer);
  envTex = pmrem.fromEquirectangular(tex).texture;
  pmrem.dispose();
  tex.dispose();
  return envTex;
}

export function createCaption3D({ reduceMotion }) {
  const canvas = document.createElement("canvas");
  canvas.className = "caption3d";
  canvas.setAttribute("aria-hidden", "true");

  // antialias off and the pixel ratio capped: this canvas sits over a full-screen film that is
  // already decoding frames, so every pixel it costs is taken from the scrub.
  const renderer = new WebGLRenderer({ canvas, alpha: true, antialias: false });
  renderer.setClearAlpha(0);
  const scene = new Scene();
  const camera = new PerspectiveCamera(FOV, 1, 1, 6000);
  const root = new Group();
  scene.add(root);

  // base light: without it a MeshStandardMaterial word is simply black
  const ambient = new AmbientLight(CREAM, 1.05);
  scene.add(ambient);
  // the flame the reader carries, now an actual light in the scene
  const flame = new PointLight(0xffc06a, 0, 900, 2);
  scene.add(flame);

  let W = 0;
  let H = 0;
  let frame = { x: 0, y: 0 }; // the canvas covers the caption and a margin, never the whole viewport
  let items = []; // { mesh, texture, rect }
  let bulbs = []; // { mesh, light, hue, home }
  let wire = null;
  let dirty = true;
  let fontReady = false;
  let hideTimer = 0;
  let visible = false;
  let style = { lights: false, wood: false, smoke: false, lay: false, feather: false, peck: false, powder: false, mala: false, diyo: false, gilt: false };
  let peckTimer = 0;
  const peckUniforms = { uEaten: { value: 0 } };
  let powderTimer = 0;
  const powderUniforms = { uPress: { value: 1 }, uScatter: { value: 0 }, uGrain: { value: null } };
  let ledge = null;
  let mala = [];
  let strands = [];
  let lamps = [];
  let pearls = [];
  let lampTimer = 0;
  let swingTimer = 0;
  let swingLast = 0;
  let pointerVX = 0;
  let lastPX = null;
  let lastPT = 0;
  let pointerAt = null; // the surface the words lie on: invisible, but it catches their shadow
  let smokeTimer = 0;
  const smokeUniforms = {
    uReveal: { value: 1 },
    uSmoke: { value: null },
    uDrift: { value: 0 },
  };

  document.fonts?.ready.then(() => {
    fontReady = true;
  });

  // viewport pixels -> world units, measured from the middle of the canvas
  const toWorld = (x, y) => [x - frame.x - W / 2, H / 2 - (y - frame.y)];

  /** Put the canvas over just this rectangle of the page, and no more of it.
   *  `pad` may widen one side: a strand of flowers hangs well below the words and swings wide
   *  of them, and anything outside the canvas is simply cut off — which looked like the flowers
   *  vanishing along an invisible straight line. */
  function fit(box, pad = {}) {
    const l = pad.left ?? MARGIN;
    const t = pad.top ?? MARGIN;
    const rt = pad.right ?? MARGIN;
    const b = pad.bottom ?? MARGIN;
    const x = Math.max(0, Math.round(box.left - l));
    const y = Math.max(0, Math.round(box.top - t));
    const w = Math.min(window.innerWidth - x, Math.round(box.width + l + rt));
    const h = Math.min(window.innerHeight - y, Math.round(box.height + t + b));
    frame = { x, y };
    W = w;
    H = h;
    canvas.style.left = `${x}px`;
    canvas.style.top = `${y}px`;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.position.z = h / 2 / Math.tan((FOV / 2) * (Math.PI / 180));
    camera.updateProjectionMatrix();
    dirty = true;
  }

  function resize() {
    dirty = true;
    if (visible) renderer.render(scene, camera);
  }

  /** One word, rasterised by the browser so its shaping and shirorekha are exactly right. */
  function wordTexture(word) {
    const cs = getComputedStyle(word);
    const r = word.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const c = document.createElement("canvas");
    c.width = Math.ceil((r.width + PAD * 2) * dpr);
    c.height = Math.ceil((r.height + PAD * 2) * dpr);
    const ctx = c.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    ctx.fillStyle = "#fff"; // white: the scene's lights do the colouring
    ctx.fillText(word.textContent, (r.width + PAD * 2) / 2, (r.height + PAD * 2) / 2);
    const tex = new CanvasTexture(c);
    tex.colorSpace = SRGBColorSpace;
    tex.anisotropy = 4;
    return { tex, ctx, cw: c.width, ch: c.height, w: r.width + PAD * 2, h: r.height + PAD * 2 };
  }

  function clear() {
    for (const it of items) {
      root.remove(it.mesh);
      it.mesh.geometry.dispose();
      it.mesh.material.map?.dispose();
      it.mesh.material.dispose();
    }
    for (const b of bulbs) {
      root.remove(b.mesh);
      b.mesh.geometry.dispose();
      b.mesh.material.dispose();
      b.light.dispose?.();
    }
    cancelAnimationFrame(swingTimer);
    swingTimer = 0;
    cancelAnimationFrame(lampTimer);
    lampTimer = 0;
    for (const pearl of pearls) {
      root.remove(pearl);
      pearl.geometry.dispose();
      pearl.material.dispose();
    }
    pearls = [];
    for (const lamp of lamps) {
      root.remove(lamp.bowl, lamp.flame, lamp.light);
      lamp.bowl.geometry.dispose();
      lamp.bowl.material.dispose();
      lamp.flame.geometry.dispose();
      lamp.flame.material.dispose();
    }
    lamps = [];
    for (const st of strands) {
      root.remove(st.cord);
      st.cord.geometry.dispose();
      st.cord.material.dispose();
    }
    strands = [];
    for (const f of mala) {
      root.remove(f);
      f.geometry.dispose();
      f.material.dispose();
    }
    mala = [];
    if (ledge) {
      root.remove(ledge);
      ledge.geometry.dispose();
      ledge.material.dispose();
      ledge = null;
    }
    if (wire) {
      root.remove(wire);
      wire.geometry.dispose();
      wire.material.dispose();
      wire = null;
    }
    items = [];
    bulbs = [];
  }

  /** Anchors on the shirorekha, and how far each light hangs below it. */
  function hangs(rect, i) {
    const fs = rect.height / 1.3;
    const shiro = rect.top + fs * 0.36;
    const at = rect.width > 150 ? [0.26, 0.63, 0.9] : rect.width > 72 ? [0.33, 0.78] : [0.5];
    return at.map((t, k) => ({
      x: rect.left + t * rect.width,
      y0: shiro,
      y1: rect.top + rect.height * (k % 2 ? 0.86 : 1.0), // uneven: a real string never hangs level
      hue: HUES[(i + k) % HUES.length],
    }));
  }

  /** Put every flower where its bead of the chain has ended up, and redraw the cord. */
  function placeStrands() {
    for (const st of strands) {
      const pos = st.cord.geometry.attributes.position;
      st.pts.forEach((pt, k) => pos.setXYZ(k, pt.x, pt.y, 0));
      pos.needsUpdate = true;
      st.cord.geometry.computeBoundingSphere();
      st.heads.forEach((m, k) => {
        const pt = st.pts[k + 1];
        const above = st.pts[k];
        m.position.set(pt.x, pt.y, k % 2 ? 26 : -22);
        // each head lies along its own link, so the whole strand curls rather than staying straight
        m.rotation.z = Math.atan2(pt.x - above.x, -(pt.y - above.y)) * -1 + st.tilt[k];
      });
    }
  }

  /** A rope, not a pendulum.
   *
   *  Each flower is a bead carrying its own momentum, and the links between them are solved as
   *  distance constraints (Verlet). That is what makes a swing look like a swing: the top of the
   *  strand turns first, the lower beads lag and overshoot, the whole thing curls, and it keeps
   *  going after the pointer has left. Rotating a straight line about its anchor — which is what
   *  this did before — can only ever read as a stick.
   */
  function stepStrands(dt, lx, ly) {
    const g = GRAV * dt * dt;
    let moving = false;

    for (const st of strands) {
      st.pts[0].x = st.x; // the anchor never moves
      st.pts[0].y = st.y;

      for (let i = 1; i < st.pts.length; i++) {
        const pt = st.pts[i];
        let vx = (pt.x - pt.px) * SWING_DRAG;
        let vy = (pt.y - pt.py) * SWING_DRAG;
        pt.px = pt.x;
        pt.py = pt.y;

        if (lx !== null) {
          const d = Math.hypot(pt.x - lx, pt.y - ly);
          if (d < POINTER_REACH) {
            const near = 1 - d / POINTER_REACH;
            vx += pointerVX * dt * 0.9 * near; // carried along by the pointer
            vx += ((pt.x - lx) / (d || 1)) * near * 2.2; // and shouldered aside by it
            vy += ((pt.y - ly) / (d || 1)) * near * 1.1;
          }
        }

        pt.x += vx;
        pt.y += vy - g;
        if (Math.abs(vx) + Math.abs(vy) > 0.05) moving = true;
      }

      // hold the links together: several passes, so the constraint travels down the strand
      for (let pass = 0; pass < 5; pass++) {
        for (let i = 1; i < st.pts.length; i++) {
          const a = st.pts[i - 1];
          const b = st.pts[i];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 0.0001;
          const fix = (len - st.step) / len;
          const take = i === 1 ? 1 : 0.5; // the anchor cannot give
          if (i > 1) {
            a.x += dx * fix * 0.5;
            a.y += dy * fix * 0.5;
          }
          b.x -= dx * fix * take;
          b.y -= dy * fix * take;
        }
      }
    }

    placeStrands();
    return moving;
  }

  /** Light the lamps the pointer has reached, and keep them burning.
   *  Nothing else on the site leaves a mark: here the reader lights the lamps and they stay
   *  lit, which is what the line is about — घरघर दियो बालिन्छ. */
  function touchLamps(px, py) {
    let caught = false;
    for (const pearl of pearls) {
      root.remove(pearl);
      pearl.geometry.dispose();
      pearl.material.dispose();
    }
    pearls = [];
    for (const lamp of lamps) {
      if (lamp.lit) continue;
      if (Math.hypot(lamp.x - px, lamp.y - py) < lamp.size * 1.9) {
        lamp.lit = true;
        lamp.flame.visible = true;
        lamp.bowl.material.color.setHex(0xffffff); // the clay comes up as its own flame lights it
        caught = true;
      }
    }
    if (caught || lamps.some((l) => l.lit)) startFlicker();
  }

  /** A lit flame is never still: the light and the flame shape breathe, out of step with
   *  each other and with the next lamp along. */
  function startFlicker() {
    if (lampTimer || reduceMotion()) return;
    const step = (now) => {
      let any = false;
      const t = now / 1000;
      for (const pearl of pearls) {
      root.remove(pearl);
      pearl.geometry.dispose();
      pearl.material.dispose();
    }
    pearls = [];
    for (const lamp of lamps) {
        if (!lamp.lit) continue;
        any = true;
        const f =
          0.78 +
          0.22 * Math.sin(t * 7.3 + lamp.seed) * Math.sin(t * 3.1 + lamp.seed * 2.2) +
          0.06 * Math.sin(t * 19 + lamp.seed * 5);
        lamp.light.intensity = LAMP_I * f;
        lamp.flame.scale.set(0.9 + f * 0.16, 0.84 + f * 0.3, 1);
        lamp.flame.material.opacity = 0.75 + f * 0.25;
      }
      renderer.render(scene, camera);
      lampTimer = any && visible ? requestAnimationFrame(step) : 0;
    };
    lampTimer = requestAnimationFrame(step);
  }

  /** Run the rope while anything is still moving, then stop. A fixed step keeps the constraint
   *  solver stable no matter what the display is doing. */
  function startSwing() {
    if (swingTimer || reduceMotion()) return;
    swingLast = performance.now();
    const step = (now) => {
      const dt = Math.min(0.033, (now - swingLast) / 1000);
      swingLast = now;
      const moving = stepStrands(dt, pointerAt ? pointerAt[0] : null, pointerAt ? pointerAt[1] : null);
      renderer.render(scene, camera);
      pointerVX *= 0.86; // the shove fades once the pointer stops
      if (moving || Math.abs(pointerVX) > 2) swingTimer = requestAnimationFrame(step);
      else swingTimer = 0;
    };
    swingTimer = requestAnimationFrame(step);
  }

  /** Press the powder on, or lift it off. Same short self-cancelling ticker as the others. */
  function runPowder(on) {
    cancelAnimationFrame(powderTimer);
    const press = on;
    const from = press ? powderUniforms.uPress.value : powderUniforms.uScatter.value;
    const ms = press ? POWDER_IN_MS : POWDER_OUT_MS;
    const t0 = performance.now();
    if (press) powderUniforms.uScatter.value = 0;
    const step = (now) => {
      const t = Math.min(1, (now - t0) / ms);
      const e = t * t * (3 - 2 * t);
      if (press) powderUniforms.uPress.value = from + (1 - from) * e;
      else powderUniforms.uScatter.value = from + (1 - from) * e;
      dirty = true;
      renderer.render(scene, camera);
      if (t < 1) powderTimer = requestAnimationFrame(step);
    };
    powderTimer = requestAnimationFrame(step);
  }

  /** The crow takes the line apart on the way out: bites open one after another until it is
   *  gone. Like the smoke, a short self-cancelling ticker, never a second permanent loop. */
  function runPeck(onDone) {
    cancelAnimationFrame(peckTimer);
    const t0 = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - t0) / PECK_MS);
      peckUniforms.uEaten.value = t;
      dirty = true;
      renderer.render(scene, camera);
      if (t < 1) peckTimer = requestAnimationFrame(step);
      else onDone?.();
    };
    peckTimer = requestAnimationFrame(step);
  }

  /** Run the smoke either way: 0 is all smoke, 1 is the word entirely given up.
   *  A short self-cancelling ticker, not a second permanent loop — it stops the moment the
   *  dissolve finishes, and the page's own rAF goes back to driving everything. */
  function runSmoke(reveal) {
    smokeUniforms.uSmoke.value = smokeNoise();
    cancelAnimationFrame(smokeTimer);
    const from = smokeUniforms.uReveal.value;
    const to = reveal ? 1 : 0;
    const ms = reveal ? SMOKE_IN_MS : SMOKE_OUT_MS; // it gathers slower than it lets go
    const t0 = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - t0) / ms);
      const e = t * t * (3 - 2 * t);
      smokeUniforms.uReveal.value = from + (to - from) * e;
      smokeUniforms.uDrift.value = (now - t0) / 5200; // the smoke keeps moving while it clears
      dirty = true;
      renderer.render(scene, camera);
      if (t < 1) smokeTimer = requestAnimationFrame(step);
    };
    smokeTimer = requestAnimationFrame(step);
  }

  return {
    canvas,
    mount(parent) {
      parent.append(canvas);
      window.addEventListener("resize", resize);
    },

    /** Rebuild from the DOM words: they own layout and accessibility, this owns the picture. */
    build(words, opts = {}) {
      clear();
      style = {
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
      };
      const rects = words.map((w) => w.getBoundingClientRect()).filter((r) => r.width);
      if (!rects.length) return;
      const left = Math.min(...rects.map((r) => r.left));
      const top = Math.min(...rects.map((r) => r.top));
      const box = {
        left,
        top,
        width: Math.max(...rects.map((r) => r.right)) - left,
        height: Math.max(...rects.map((r) => r.bottom)) - top,
      };
      if (style.mala) {
        // the strands hang this far down, and may swing most of that distance sideways
        const fs0 = rects[0].height / 1.3;
        const reach = fs0 * 0.27 * 1.55 * MALA_HEADS + fs0;
        fit(box, { bottom: reach + MARGIN, left: reach * 0.8, right: reach * 0.8, top: MARGIN });
      } else if (style.diyo) {
        fit(box, { bottom: rects[0].height * 1.5 + MARGIN });
      } else {
        fit(box);
      }
      const segs = [];
      words.forEach((word, i) => {
        const r = word.getBoundingClientRect();
        if (!r.width) return;
        const { tex, ctx, cw, ch, w, h } = wordTexture(word);
        // depthWrite off: the word planes are padded, so they overlap each other and the line
        // below. With depth writing on, a plane's empty pixels punch holes in its neighbours.
        const mat = style.feather
          ? new MeshPhysicalMaterial({
              map: tex,
              transparent: true,
              depthWrite: false,
              color: INK, // the crow's blue-black
              roughness: 0.26,
              metalness: 0.45,
              // thin-film interference: the sheen slides across the strokes as the light moves,
              // the way it runs over a feather
              iridescence: 1,
              iridescenceIOR: 1.32,
              iridescenceThicknessRange: [120, 420],
              sheen: 0.6,
              sheenColor: new Color(0x3f6ea8),
            })
          : new MeshStandardMaterial({
          map: tex,
          transparent: true,
          depthWrite: false,
          roughness: style.lay ? 0.5 : style.wood ? 0.82 : 0.55,
          metalness: style.lay ? 0.12 : 0,
          color: style.powder ? VERMILION : style.lay ? INK : style.wood ? WOOD : CREAM,
        });
        if (style.gilt) {
          // gilded like the murti: real metal, so it needs the room above to reflect
          scene.environment = roomEnv(renderer);
          mat.color.setHex(GOLD);
          mat.metalness = 0.72; // full metal with only a dim room to reflect renders near-black
          mat.roughness = 0.34;
          mat.envMapIntensity = 2.6;
          mat.emissive = new Color(0x4a3108); // a floor of warmth, so it is legible unlit
          mat.emissiveIntensity = 0.9;
          mat.normalMap = carveNormals(ctx, cw, ch);
          mat.normalScale.set(0.55, 0.55);
        }
        if (style.powder) {
          mat.roughness = 0.97; // abir has no shine at all
          mat.metalness = 0;
          // pigment carries its own brightness: without this it is only as bright as whatever
          // light happens to reach it, and this scene's top corner is nearly black
          mat.emissive = new Color(0x8e2a18);
          mat.emissiveIntensity = 0.75;
          mat.normalMap = carveNormals(ctx, cw, ch);
          mat.normalScale.set(0.45, 0.45);
        }
        if (style.feather) {
          // a little surface, so the sheen has something to run across
          mat.normalMap = carveNormals(ctx, cw, ch);
          mat.normalScale.set(0.7, 0.7);
        }
        if (style.lay) {
          // a shadow takes the shape of the glyphs only if the depth pass can see their alpha
          mat.alphaTest = 0.34;
          mat.normalMap = carveNormals(ctx, cw, ch);
          mat.normalScale.set(0.9, 0.9);
        }
        if (style.wood) {
          // cut into the surface: a raking light now finds one wall of each stroke
          mat.normalMap = carveNormals(ctx, cw, ch);
          mat.normalScale.set(1.5, 1.5);
        }
        if (style.smoke) addSmoke(mat, smokeUniforms);
        if (style.peck) addPeck(mat, peckUniforms);
        if (style.powder) addPowder(mat, powderUniforms, i * 0.137); // a different grain per word
        const mesh = new Mesh(new PlaneGeometry(w, h), mat);
        mesh.renderOrder = 1;
        const [wx, wy] = toWorld(r.left + r.width / 2, r.top + r.height / 2);
        mesh.position.set(wx, wy, Z_WORD);
        if (style.lay) {
          mesh.rotation.x = -LAY_RAD; // tipped onto the ledge, receding from the reader
          mesh.position.z = Z_WORD + 10;
          mesh.castShadow = true;
        }
        root.add(mesh);
        items.push({ mesh, rect: r });

        for (const h2 of style.lights ? hangs(r, i) : []) {
          const bulb = new Mesh(
            new SphereGeometry(BULB_R, 16, 12),
            new MeshBasicMaterial({ color: h2.hue })
          );
          const [bx, by] = toWorld(h2.x, h2.y1);
          bulb.position.set(bx, by, Z_BULB);
          bulb.renderOrder = 3;
          const light = new PointLight(h2.hue, 0, LIGHT_DIST, 2);
          bulb.add(light);
          root.add(bulb);
          bulbs.push({ mesh: bulb, light, hue: h2.hue, home: { x: h2.x, y: h2.y1 } });

          const [sx, sy] = toWorld(h2.x, h2.y0);
          segs.push(sx, sy, Z_BULB, bx, by, Z_BULB);
        }
      });

      if (style.lay) {
        // An invisible plane lying in the same tilt as the words, a little behind them:
        // ShadowMaterial draws nothing but the shadow, so what appears on screen is the words'
        // own shadow falling across the ledge that is already in the rendered frame.
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = PCFSoftShadowMap;
        flame.castShadow = true;
        flame.shadow.mapSize.set(512, 512);
        flame.shadow.radius = 4;
        flame.shadow.bias = -0.004;
        const g = new PlaneGeometry(W * 1.6, H * 2.4);
        ledge = new Mesh(g, new ShadowMaterial({ opacity: 0.42, transparent: true, depthWrite: false }));
        ledge.rotation.x = -LAY_RAD;
        ledge.position.set(0, 0, Z_WORD - 6);
        ledge.receiveShadow = true;
        ledge.renderOrder = 0;
        root.add(ledge);
      } else {
        renderer.shadowMap.enabled = false;
        flame.castShadow = false;
      }
      if (style.gilt) {
        // A few pearls, set in the gaps BETWEEN words rather than strung along every bar: on
        // the murti they punctuate the gilding, they do not cover it. One every other gap, so
        // a nine-word line wears four, and none of them sits on a letter.
        const fs5 = rects[0].height / 1.3;
        const rad = fs5 * 0.1;
        const geom = new SphereGeometry(rad, 20, 14);
        const byLine = new Map();
        for (const r of rects) {
          const line = Math.round(r.top);
          if (!byLine.has(line)) byLine.set(line, []);
          byLine.get(line).push(r);
        }
        for (const [, row] of byLine) {
          row.sort((a, b) => a.left - b.left);
          for (let k = 0; k + 1 < row.length; k += 2) {
            const gapMid = (row[k].right + row[k + 1].left) / 2;
            const [gx, gy] = toWorld(gapMid, row[k].top + fs5 * 0.46);
            const pearl = new Mesh(
              geom.clone(),
              new MeshPhysicalMaterial({
                color: PEARL,
                // a pearl is lit, never lit up: no emissive, a hard clearcoat for the highlight,
                // and the room to reflect, which is what gives it its depth
                roughness: 0.22,
                metalness: 0,
                clearcoat: 1,
                clearcoatRoughness: 0.06,
                sheen: 0.8,
                sheenColor: new Color(0xfff0f4),
                iridescence: 0.35,
                iridescenceIOR: 1.25,
                envMapIntensity: 2.2,
              })
            );
            pearl.position.set(gx, gy, rad * 1.1);
            pearl.renderOrder = 5;
            root.add(pearl);
            pearls.push(pearl);
          }
        }
      }
      if (style.diyo) {
        // A row of lamps standing along the foot of the caption, the way they are set out on a
        // sill or a step: evenly spaced, because a line of diyos is a line, not a sprinkle.
        const fs4 = rects[0].height / 1.3;
        const lw = fs4 * 1.05;
        const blockL = Math.min(...rects.map((r) => r.left));
        const blockR = Math.max(...rects.map((r) => r.right));
        const foot = Math.max(...rects.map((r) => r.bottom));
        const n = Math.max(3, Math.round((blockR - blockL) / (lw * 1.5)));
        for (let k = 0; k < n; k++) {
          const px3 = blockL + ((k + 0.5) / n) * (blockR - blockL);
          const [bx, by] = toWorld(px3, foot + lw * 0.3);
          const bowl = new Mesh(
            new PlaneGeometry(lw, lw * 0.5),
            new MeshBasicMaterial({ map: diyoTexture(), transparent: true, depthWrite: false, color: 0x4a4038 })
          );
          bowl.position.set(bx, by, 34);
          bowl.renderOrder = 5;
          root.add(bowl);
          const flame = new Mesh(
            new PlaneGeometry(lw * 0.3, lw * 0.5),
            new MeshBasicMaterial({ map: flameTexture(), transparent: true, depthWrite: false, blending: AdditiveBlending })
          );
          flame.position.set(bx + lw * 0.012, by + lw * 0.42, 35);
          flame.visible = false;
          flame.renderOrder = 6;
          root.add(flame);
          const light = new PointLight(0xffb45a, 0, 320, 2);
          light.position.set(bx, by + lw * 0.5, 70);
          root.add(light);
          lamps.push({ bowl, flame, light, x: px3, y: foot + lw * 0.3, lit: false, seed: Math.random() * 10, size: lw });
        }
      }
      if (style.mala) {
        // Two long marigold strands, hung at the outer edges of the whole paragraph rather than
        // off every word: they frame the text instead of falling across it. Each hangs as a
        // pendulum and is pushed by the pointer passing through it (see stepStrands).
        const fs = rects[0].height / 1.3;
        const R = fs * 0.27;
        const leftX = Math.min(...rects.map((r) => r.left)) - R * 1.5;
        const rightX = Math.max(...rects.map((r) => r.right)) + R * 1.5;
        const topY2 = Math.min(...rects.map((r) => r.top)) + fs * 0.36; // the shirorekha line
        const count = MALA_HEADS;
        for (const ax of [leftX, rightX]) {
          const [wx, wy] = toWorld(ax, topY2);
          const heads = [];
          for (let k = 0; k < count; k++) {
            const m = new Mesh(
              new PlaneGeometry(R * 2, R * 2),
              new MeshStandardMaterial({
                map: marigoldTexture(),
                transparent: true,
                depthWrite: false,
                roughness: 0.9,
                metalness: 0,
                color: new Color().setHSL(0.075 + Math.random() * 0.05, 0.95, 0.56 + Math.random() * 0.16),
              })
            );
            m.rotation.z = (Math.random() - 0.5) * 0.7;
            m.scale.setScalar(0.84 + Math.random() * 0.3);
            m.renderOrder = 4;
            root.add(m);
            heads.push(m);
            mala.push(m);
          }
          const geo = new BufferGeometry();
          geo.setAttribute("position", new Float32BufferAttribute(new Float32Array((count + 1) * 3), 3));
          const cord = new Line(geo, new LineBasicMaterial({ color: 0x7a5a33, transparent: true, opacity: 0.55 }));
          cord.renderOrder = 3;
          root.add(cord);
          const step = R * 1.55;
          const pts = [];
          for (let k = 0; k <= count; k++) pts.push({ x: wx, y: wy - k * step, px: wx, py: wy - k * step });
          strands.push({
            x: wx,
            y: wy,
            heads,
            cord,
            pts,
            step,
            len: step * count,
            tilt: heads.map(() => (Math.random() - 0.5) * 0.5),
          });
        }
        placeStrands();
      }
      if (style.smoke) smokeUniforms.uReveal.value = reduceMotion() ? 1 : 0;
      if (style.peck) peckUniforms.uEaten.value = 0;
      if (style.powder) {
        powderUniforms.uGrain.value = smokeNoise(); // the same soft noise, read much finer
        powderUniforms.uPress.value = reduceMotion() ? 1 : 0;
        powderUniforms.uScatter.value = 0;
      }
      queueMicrotask(() => renderer.render(scene, camera));
      if (segs.length) {
        const g = new BufferGeometry();
        g.setAttribute("position", new Float32BufferAttribute(segs, 3));
        wire = new LineSegments(
          g,
          new LineBasicMaterial({ color: CREAM, transparent: true, opacity: 0.3, depthWrite: false })
        );
        wire.renderOrder = 2;
        root.add(wire);
      }
      dirty = true;
    },

    /** The pointer is the flame; a bulb near it burns brighter and throws its colour on the word. */
    pointer(px, py) {
      // the pointer's speed is what actually shoves a strand, so track it before anything else
      if (px === null) {
        pointerAt = null;
        pointerVX = 0;
        lastPX = null;
      } else {
        const now = performance.now();
        if (lastPX !== null && now > lastPT) pointerVX = ((px - lastPX) / (now - lastPT)) * 1000;
        lastPX = px;
        lastPT = now;
        pointerAt = toWorld(px, py);
        if (strands.length) startSwing();
        if (lamps.length) touchLamps(px, py);
      }
      if (px === null) {
        flame.intensity = 0;
        for (const b of bulbs) {
          b.light.intensity = BULB_IDLE;
          b.mesh.material.color.setHex(b.hue);
        }
      } else {
        const [fx, fy] = toWorld(px, py);
        flame.position.set(fx, fy, style.lay ? 150 : style.wood ? 44 : 120); // raking for a cut, high for a shadow
        flame.intensity = reduceMotion() ? FLAME_I * 0.5 : FLAME_I;
        for (const b of bulbs) {
          const d = Math.hypot(b.home.x - px, b.home.y - py);
          const near = Math.max(0, 1 - d / 300);
          b.light.intensity = BULB_IDLE + near * near * BULB_LIT;
          // the glass itself brightens toward white as it lights
          b.mesh.material.color.copy(new Color(b.hue).lerp(new Color(0xffffff), near * 0.55));
        }
      }
      if (!reduceMotion()) {
        const tx = px === null ? 0 : (px / W - 0.5) * 0.1;
        const ty = px === null ? 0 : (py / H - 0.5) * 0.06;
        root.rotation.y = tx;
        root.rotation.x = ty;
      }
      dirty = true;
    },

    setVisible(on) {
      // called every frame: without this guard the hide timer below is rescheduled forever and
      // the canvas keeps compositing at opacity 0
      if (!!on === visible) return;
      visible = !!on;
      if (style.smoke && !reduceMotion()) runSmoke(on);
      // with smoke, the dissolve IS the transition: fading the whole canvas on top of it would
      // cut the smoke off halfway, which is exactly what it did before this.
      const smoked = style.smoke && !reduceMotion();
      const pecked = style.peck && !reduceMotion();
      const powdered = style.powder && !reduceMotion();
      if (on) {
        clearTimeout(hideTimer);
        cancelAnimationFrame(peckTimer);
        peckUniforms.uEaten.value = 0; // whole again for the next time it is read
        if (powdered) {
          powderUniforms.uPress.value = 0;
          powderUniforms.uScatter.value = 0;
          runPowder(true);
        }
        canvas.style.display = "block";
        requestAnimationFrame(() => {
          canvas.style.opacity = "1";
          canvas.style.transform = "translateY(0)";
          renderer.render(scene, camera);
        });
      } else if (powdered) {
        runPowder(false);
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => {
          canvas.style.display = "none";
          canvas.style.opacity = "0";
        }, POWDER_OUT_MS + 70);
      } else if (pecked) {
        runPeck();
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => {
          canvas.style.display = "none";
          canvas.style.opacity = "0";
        }, PECK_MS + 70);
      } else {
        if (!smoked) {
          canvas.style.opacity = "0";
          canvas.style.transform = "translateY(-14px)";
        }
        clearTimeout(hideTimer);
        hideTimer = setTimeout(
          () => {
            canvas.style.display = "none";
            canvas.style.opacity = "0";
            canvas.style.transform = "translateY(-14px)";
          },
          smoked ? SMOKE_OUT_MS + 90 : 340
        );
      }
      dirty = true;
    },

    /** Called from the page's own loop; draws only when something changed. */
    render() {
      if (!dirty) return;
      dirty = false;
      renderer.render(scene, camera);
    },

    /** Play the entrance for the caption just built.
     *  The entrances used to hang off setVisible, which only fires when the layer goes from
     *  hidden to shown. Scroll straight from one lit caption into the next and the layer never
     *  hides, so the new caption kept the old one's finished state — for powder that meant
     *  uPress stayed at 0 and half of every word was missing. */
    restart() {
      if (!visible || reduceMotion()) return;
      if (style.smoke) runSmoke(true);
      if (style.powder) {
        powderUniforms.uPress.value = 0;
        powderUniforms.uScatter.value = 0;
        runPowder(true);
      }
      if (style.peck) peckUniforms.uEaten.value = 0;
      dirty = true;
    },

    /** how far the smoke has let the words go, 0..1 (read by the ?probe hook) */
    get reveal() {
      return smokeUniforms.uReveal.value;
    },

    /** powder state, for the same hook */
    get powder() {
      return [powderUniforms.uPress.value, powderUniforms.uScatter.value];
    },

    get fontReady() {
      return fontReady;
    },

    dispose() {
      cancelAnimationFrame(smokeTimer);
      cancelAnimationFrame(peckTimer);
      cancelAnimationFrame(powderTimer);
      cancelAnimationFrame(swingTimer);
      cancelAnimationFrame(lampTimer);
      clearTimeout(hideTimer);
      window.removeEventListener("resize", resize);
      clear();
      renderer.dispose();
      canvas.remove();
    },
  };
}
