// Scene 8 backdrop — the hybrid finale (owner 2026-11-21).
//
// Blender renders the hilltop view once, not 72 times (a full 3 s loop cost ~6 min a frame): a
// clean still with no tree, grass, kite or flag; the tree, kite and grass cut from a second still
// by their render masks (colour un-mixed from the clean still, so no halo); and the flag as its own
// 72-frame, 3 s loop rendered in the same scene and graded for the haze
// (scripts/s08_hybrid_assets.py -> public/frames/s08_finale/hybrid/).
//
// One full-screen shader puts them together and moves them in ONE wind: the flag's own waves
// (scripts/s08_flag_wave.py pass 8 — 1 / 2 / 3 Hz, all at 1.25 m/s along the wind, a gust swell
// once per loop) run across the tree crown, the grass and the kite. The tree and grass are warped
// from their roots, the kite swings on its top corner and rides its branch. Everything is periodic
// in the 3 s loop, so it repeats for as long as the scene is on screen.
//
// The canvas takes the old still's place (class finale__still: object-fit cover, and the focus
// pull the finale drives). Until every texture has loaded it stays hidden and the still shows.

import {
  LinearFilter,
  Mesh,
  OrthographicCamera,
  PlaneGeometry,
  Scene,
  ShaderMaterial,
  Texture,
  TextureLoader,
  WebGLRenderer,
} from "three";

const BASE = "/frames/s08_finale/hybrid/";
const LOOP_S = 3; // seconds; the flag loop is 72 frames at 24 fps

const frag = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform sampler2D uHill, uTree, uKite, uGrass, uFlag;
  uniform vec2 uSize;        // 1920 x 1080
  uniform vec4 uFlagRect;    // x, y, w, h in px, top-left origin
  uniform vec2 uPivot;       // kite's top corner, px
  uniform float uPoleX;      // flag pole, px: the wind's distances are measured from it
  uniform float uT;          // loop phase 0..1

  const float TAU = 6.2831853;

  vec4 tex(sampler2D s, vec2 p) { return texture2D(s, vec2(p.x / uSize.x, 1.0 - p.y / uSize.y)); }

  // straight-alpha layer c over a premultiplied accumulator
  vec4 over(vec4 acc, vec4 c) { return vec4(c.rgb * c.a + acc.rgb * (1.0 - c.a), c.a + acc.a * (1.0 - c.a)); }

  float swell(float t) { return 1.0 + 0.22 * sin(TAU * t) + 0.14 * sin(2.0 * TAU * t + 1.1); }

  // the flag's wave field at metres-along-the-wind x (normalised to about -1..1)
  float wind(float x, float t) {
    return (0.100 * sin(TAU * (x / 1.25   - 3.0 * t))
          + 0.025 * sin(TAU * (x / 0.625  - 6.0 * t) + 1.7)
          + 0.009 * sin(TAU * (x / 0.4167 - 9.0 * t) + 4.1)) / 0.134;
  }

  // the wind blows toward screen-left (the flag flies left from its pole)
  float along(vec2 p, float mpp) { return (uPoleX - p.x) * mpp + p.y * mpp * 0.25; }

  vec2 treeShift(vec2 p, float t) {
    float h = clamp((1075.0 - p.y) / 1000.0, 0.0, 1.0);
    float env = pow(h, 1.5) * swell(t);
    float w = wind(along(p, 0.0067), t);                      // tree ~17 m away: 6.7 mm a pixel
    float flutter = 0.45 * sin(TAU * 9.0 * t + p.x * 0.13 + p.y * 0.17)
                  + 0.30 * sin(TAU * 6.0 * t - p.x * 0.21 + p.y * 0.11);
    return vec2(-(1.6 + 2.8 * w) * env + flutter * env, 0.7 * w * env);
  }

  void main() {
    vec2 p = vec2(vUv.x * uSize.x, (1.0 - vUv.y) * uSize.y);
    float t = uT;
    // FRONT layer only, transparent elsewhere (premultiplied): the fireworks are drawn between the
    // clean still (sky, peaks, city) and this, so they rise from behind the hill, tree, flag and kite
    vec4 acc = vec4(0.0);

    // flag loop, in its rectangle (already cut where the ridge stands in front of the pole)
    vec2 fq = (p - uFlagRect.xy) / uFlagRect.zw;
    if (all(greaterThanEqual(fq, vec2(0.0))) && all(lessThanEqual(fq, vec2(1.0)))) {
      vec4 f = texture2D(uFlag, vec2(fq.x, 1.0 - fq.y));
      acc = over(acc, f);
    }

    // the hill we stand on and the front ridge (static)
    acc = over(acc, tex(uHill, p));

    // kite: rides its branch, swings on its top corner (behind the tree, which is drawn next)
    vec2 ts = treeShift(uPivot, t);
    float th = (0.035 + 0.055 * wind(along(uPivot, 0.0067), t)) * swell(t);
    vec2 d = p - uPivot - ts;
    vec2 kq = uPivot + vec2(cos(th) * d.x - sin(th) * d.y, sin(th) * d.x + cos(th) * d.y);
    acc = over(acc, tex(uKite, kq));

    // tree, warped from its root
    acc = over(acc, tex(uTree, p - treeShift(p, t)));

    // grass, each tuft bending from the bottom of the strip
    float gh = clamp((1080.0 - p.y) / 230.0, 0.0, 1.0);
    float genv = pow(gh, 1.5) * swell(t);
    float gw = wind(along(p, 0.004), t);
    float gfl = 0.35 * sin(TAU * 9.0 * t + p.x * 0.31);
    acc = over(acc, tex(uGrass, p - vec2(-(1.2 + 3.0 * gw) * genv + gfl * genv, 0.0)));

    gl_FragColor = acc;
  }
`;

const vert = /* glsl */ `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

export function createBackdrop(stage, still) {
  // the FRONT layer (hill, flag, kite, tree, grass); finale.js puts it above the fireworks canvas.
  // The BACK layer is the page's own still <img>, switched to the clean render once loaded.
  const canvas = document.createElement("canvas");
  canvas.className = "finale__fore";
  canvas.setAttribute("aria-hidden", "true");
  canvas.hidden = true;

  let renderer = null;
  let material = null;
  let meta = null;
  const flagImgs = [];
  let flagTex = null;
  let shownFlag = -1;
  let t = 0;
  let ready = false;

  async function load() {
    try {
      meta = await (await fetch(BASE + "hybrid.json")).json();
      const loader = new TextureLoader();
      const get = (name) =>
        loader.loadAsync(BASE + name + ".webp").then((tx) => {
          tx.minFilter = tx.magFilter = LinearFilter;
          tx.generateMipmaps = false;
          return tx;
        });
      const n = meta.loop_frames;
      const flags = Array.from({ length: n }, (_, i) => {
        const im = new Image();
        im.src = `${BASE}flag/${String(i + 1).padStart(4, "0")}.webp`;
        flagImgs.push(im);
        return im.decode();
      });
      const [hill, tree, kite, grass] = await Promise.all(["hill", "tree", "kite", "grass"].map(get));
      const back = new Image();
      back.src = BASE + "clean.webp";
      await Promise.all([...flags, back.decode()]);

      flagTex = new Texture(flagImgs[0]);
      flagTex.minFilter = flagTex.magFilter = LinearFilter;
      flagTex.generateMipmaps = false;
      flagTex.needsUpdate = true;

      renderer = new WebGLRenderer({ canvas, antialias: false, alpha: true, premultipliedAlpha: true });
      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(1);
      renderer.setSize(meta.size[0], meta.size[1], false); // drawn at the render's own size; CSS covers
      const [fx, fy, fw, fh] = meta.flag.rect;
      material = new ShaderMaterial({
        vertexShader: vert,
        fragmentShader: frag,
        depthTest: false,
        depthWrite: false,
        uniforms: {
          uHill: { value: hill },
          uTree: { value: tree },
          uKite: { value: kite },
          uGrass: { value: grass },
          uFlag: { value: flagTex },
          uSize: { value: meta.size },
          uFlagRect: { value: [fx, fy, fw, fh] },
          uPivot: { value: meta.kite.pivot },
          uPoleX: { value: fx + fw * 0.7 },
          uT: { value: 0 },
        },
      });
      const scene = new Scene();
      scene.add(new Mesh(new PlaneGeometry(2, 2), material));
      const camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
      draw = () => renderer.render(scene, camera);

      if (still) {
        canvas.style.filter = still.style.filter;
        still.src = back.src; // the back layer: sky, peaks, city (its Nepali alt text stays)
      }
      setFlag(0);
      draw();
      canvas.hidden = false;
      ready = true;
    } catch (err) {
      console.warn("[finale] hybrid backdrop not loaded, keeping the still", err);
    }
  }

  let draw = () => {};

  function setFlag(i) {
    if (i === shownFlag) return;
    flagTex.image = flagImgs[i];
    flagTex.needsUpdate = true;
    shownFlag = i;
  }

  return {
    canvas,
    load,
    get ready() {
      return ready;
    },
    /** advance the loop by dt seconds and draw */
    tick(dt) {
      if (!ready) return;
      t = (t + dt / LOOP_S) % 1;
      material.uniforms.uT.value = t;
      setFlag(Math.floor(t * meta.loop_frames) % meta.loop_frames);
      draw();
    },
    setFilter(css) {
      canvas.style.filter = css;
    },
    /** ?probe: loop phase, and a PNG of the frame drawn right now (the buffer is not preserved) */
    get t() {
      return t;
    },
    snapshot(atT = t) {
      if (!ready) return null;
      material.uniforms.uT.value = atT;
      setFlag(Math.floor(atT * meta.loop_frames) % meta.loop_frames);
      draw();
      return canvas.toDataURL("image/png");
    },
    dispose() {
      renderer?.dispose();
      material?.dispose();
      canvas.remove();
    },
  };
}
