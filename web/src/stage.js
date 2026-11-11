// The full-screen canvas. Draws a frame "cover"-style around a focus point and remembers
// where the image landed, so live elements (glow, sparks) can sit on image positions.

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export class Stage {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d", { alpha: false });
    this.fit = null;
    this.resize();
  }

  resize() {
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = window.innerWidth;
    this.h = window.innerHeight;
    this.canvas.width = Math.round(this.w * this.dpr);
    this.canvas.height = Math.round(this.h * this.dpr);
    this.canvas.style.width = `${this.w}px`;
    this.canvas.style.height = `${this.h}px`;
    this.ctx.imageSmoothingQuality = "high";
  }

  /** focus: [x, y] in 0..1 of the image, kept as close to the screen centre as cover allows. */
  draw(bmp, focus = [0.5, 0.5]) {
    const cw = this.canvas.width;
    const ch = this.canvas.height;
    const s = Math.max(cw / bmp.width, ch / bmp.height);
    const w = bmp.width * s;
    const h = bmp.height * s;
    const x = clamp(cw / 2 - focus[0] * w, cw - w, 0);
    const y = clamp(ch / 2 - focus[1] * h, ch - h, 0);
    this.ctx.drawImage(bmp, x, y, w, h);
    const d = this.dpr;
    this.fit = { x: x / d, y: y / d, w: w / d, h: h / d };
  }

  /** Image point (0..1) -> CSS pixels on screen. */
  toScreen([px, py]) {
    const f = this.fit;
    return f ? [f.x + px * f.w, f.y + py * f.h] : [this.w / 2, this.h / 2];
  }
}
