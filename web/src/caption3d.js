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
  BufferGeometry,
  CanvasTexture,
  Color,
  Float32BufferAttribute,
  Group,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  PointLight,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
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
const MARGIN = 70; // room round the caption for the drops and the light that spills off it

const HUES = [0xf2a33a, 0x6fb0e0, 0x8ccfa2, 0xe291ad]; // the valley's own lights

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

  document.fonts?.ready.then(() => {
    fontReady = true;
  });

  // viewport pixels -> world units, measured from the middle of the canvas
  const toWorld = (x, y) => [x - frame.x - W / 2, H / 2 - (y - frame.y)];

  /** Put the canvas over just this rectangle of the page, and no more of it. */
  function fit(box) {
    const m = MARGIN;
    const x = Math.max(0, Math.round(box.left - m));
    const y = Math.max(0, Math.round(box.top - m));
    const w = Math.min(window.innerWidth - x, Math.round(box.width + m * 2));
    const h = Math.min(window.innerHeight - y, Math.round(box.height + m * 2));
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
    return { tex, w: r.width + PAD * 2, h: r.height + PAD * 2 };
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

  return {
    canvas,
    mount(parent) {
      parent.append(canvas);
      window.addEventListener("resize", resize);
    },

    /** Rebuild from the DOM words: they own layout and accessibility, this owns the picture. */
    build(words) {
      clear();
      const rects = words.map((w) => w.getBoundingClientRect()).filter((r) => r.width);
      if (!rects.length) return;
      const left = Math.min(...rects.map((r) => r.left));
      const top = Math.min(...rects.map((r) => r.top));
      fit({
        left,
        top,
        width: Math.max(...rects.map((r) => r.right)) - left,
        height: Math.max(...rects.map((r) => r.bottom)) - top,
      });
      const segs = [];
      words.forEach((word, i) => {
        const r = word.getBoundingClientRect();
        if (!r.width) return;
        const { tex, w, h } = wordTexture(word);
        const mesh = new Mesh(
          new PlaneGeometry(w, h),
          // depthWrite off: the word planes are padded, so they overlap each other and the line
          // below. With depth writing on, a plane's empty pixels punch holes in its neighbours.
          new MeshStandardMaterial({
            map: tex,
            transparent: true,
            depthWrite: false,
            roughness: 0.55,
            metalness: 0,
            color: CREAM,
          })
        );
        mesh.renderOrder = 1;
        const [wx, wy] = toWorld(r.left + r.width / 2, r.top + r.height / 2);
        mesh.position.set(wx, wy, Z_WORD);
        root.add(mesh);
        items.push({ mesh, rect: r });

        for (const h2 of hangs(r, i)) {
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
      if (px === null) {
        flame.intensity = 0;
        for (const b of bulbs) {
          b.light.intensity = BULB_IDLE;
          b.mesh.material.color.setHex(b.hue);
        }
      } else {
        const [fx, fy] = toWorld(px, py);
        flame.position.set(fx, fy, 120);
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
      if (on) {
        clearTimeout(hideTimer);
        canvas.style.display = "block";
        // a frame's grace, so the browser has a painted state to transition away from
        requestAnimationFrame(() => {
          canvas.style.opacity = "1";
          canvas.style.transform = "translateY(0)";
        });
      } else {
        // rise and fade, with the caption, then stop compositing entirely
        canvas.style.opacity = "0";
        canvas.style.transform = "translateY(-14px)";
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => {
          canvas.style.display = "none";
        }, 340);
      }
      dirty = true;
    },

    /** Called from the page's own loop; draws only when something changed. */
    render() {
      if (!dirty) return;
      dirty = false;
      renderer.render(scene, camera);
    },

    get fontReady() {
      return fontReady;
    },

    dispose() {
      window.removeEventListener("resize", resize);
      clear();
      renderer.dispose();
      canvas.remove();
    },
  };
}
