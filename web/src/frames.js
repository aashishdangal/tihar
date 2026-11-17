// Image-sequence loading and decoding (WEB.md "Loading").
// Compressed WebP blobs stay in memory (~17 KB each); only a small window of frames is
// decoded to ImageBitmaps at a time (a 1920x1080 bitmap is ~8 MB of memory).

const pad = (n) => String(n).padStart(4, "0");

export class FrameSequence {
  constructor({ id, count, set, maxDecoded = 12 }) {
    this.count = count;
    this.url = (i) => `${import.meta.env.BASE_URL}frames/${id}/${set}/${pad(i + 1)}.webp`;
    this.blobs = new Array(count);
    this.bitmaps = new Map(); // frame index -> ImageBitmap
    this.pending = new Set();
    this.maxDecoded = maxDecoded;
    this.loaded = 0;
    this.closed = false;
  }

  /** Fetch every frame; frame 0 first and alone, so it can paint as early as possible. */
  async load(onProgress, concurrency = 6) {
    await this.#fetchOne(0);
    onProgress?.(this.loaded / this.count);
    let next = 1;
    const worker = async () => {
      while (next < this.count && !this.closed) {
        await this.#fetchOne(next++);
        onProgress?.(this.loaded / this.count);
      }
    };
    await Promise.all(Array.from({ length: concurrency }, worker));
  }

  async #fetchOne(i) {
    try {
      const res = await fetch(this.url(i));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.blobs[i] = await res.blob();
      this.loaded++;
    } catch (err) {
      console.warn("frame failed", this.url(i), err);
    }
  }

  /** Start decoding frame i. Returns true if a new decode was started. */
  decode(i) {
    if (this.closed || !this.blobs[i] || this.bitmaps.has(i) || this.pending.has(i)) return false;
    this.pending.add(i);
    createImageBitmap(this.blobs[i])
      .then((bmp) => {
        this.pending.delete(i);
        if (this.closed) bmp.close();
        else this.bitmaps.set(i, bmp);
      })
      .catch(() => this.pending.delete(i));
    return true;
  }

  #dist(k, i, loop) {
    return loop ? (k - i + this.count) % this.count : Math.abs(k - i);
  }

  /** Frame i if decoded, otherwise the nearest decoded frame (WEB.md: never show a blank). */
  nearest(i, loop = false) {
    if (this.bitmaps.has(i)) return this.bitmaps.get(i);
    let best = null;
    let bestD = Infinity;
    for (const [k, bmp] of this.bitmaps) {
      const d = Math.min(this.#dist(k, i, loop), this.#dist(i, k, loop));
      if (d < bestD) [best, bestD] = [bmp, d];
    }
    return best;
  }

  /** Free decoded frames furthest from i (for loops: furthest ahead = just played), keeping
   *  `keep` of them (default maxDecoded; fewer for a scene out of view). */
  evict(i, loop = false, keep = this.maxDecoded) {
    if (this.bitmaps.size <= keep) return;
    const order = [...this.bitmaps.keys()].sort((a, b) => this.#dist(b, i, loop) - this.#dist(a, i, loop));
    for (const k of order.slice(0, this.bitmaps.size - keep)) {
      this.bitmaps.get(k).close();
      this.bitmaps.delete(k);
    }
  }

  close() {
    this.closed = true;
    for (const bmp of this.bitmaps.values()) bmp.close();
    this.bitmaps.clear();
  }
}
