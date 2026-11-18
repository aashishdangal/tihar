// Scroll pacing report: how many frames one scroll step moves, through each scene.
//
//   node scripts/scroll_profile.mjs            # smoothed map (what the site uses)
//   node scripts/scroll_profile.mjs 0          # the old step map, for comparison
//   node scripts/scroll_profile.mjs 6 --csv    # frame,vh-per-frame for plotting
//
// "x jump" is the worst speed change between two neighbouring sample points: 1.00x is a perfectly
// even scrub, 3.00x means the same gesture moves three times fewer frames just after that point.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { layout, RAMP_FRAMES } from "../web/src/scroll_map.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const scenes = JSON.parse(readFileSync(join(root, "web/src/scenes.json"), "utf8")).filter((s) => s.beats);
const ramp = process.argv[2] !== undefined && !process.argv[2].startsWith("--") ? Number(process.argv[2]) : RAMP_FRAMES;
const csv = process.argv.includes("--csv");

if (csv) console.log("scene,frame,vh_per_frame");
let worstAll = { x: 1 };

for (const scene of scenes) {
  const map = layout(scene, ramp);
  const step = 0.5;
  const samples = [];
  for (let f = 1; f <= scene.frames; f += step) samples.push([f, map.speedAt(f)]);

  if (csv) {
    for (const [f, v] of samples) console.log(`${scene.id},${f},${v.toFixed(4)}`);
    continue;
  }

  let worst = { x: 1, f: null };
  for (let i = 1; i < samples.length; i++) {
    const a = samples[i - 1][1];
    const b = samples[i][1];
    const x = Math.max(a / b, b / a);
    if (x > worst.x) worst = { x, f: samples[i][0] };
  }
  if (worst.x > worstAll.x) worstAll = { ...worst, scene: scene.id };

  const lo = Math.min(...samples.map((s) => s[1]));
  const hi = Math.max(...samples.map((s) => s[1]));
  console.log(
    `${scene.id.padEnd(14)} ${String(scene.frames).padStart(4)} frames  ${map.totalVh.toFixed(0).padStart(4)}vh  ` +
      `speed ${lo.toFixed(2)}-${hi.toFixed(2)} vh/frame  worst step ${worst.x.toFixed(2)}x` +
      (worst.f ? ` at frame ${worst.f}` : "")
  );
}

if (!csv) {
  console.log(`\nramp = ${ramp} frames`);
  console.log(
    worstAll.scene
      ? `worst speed change anywhere: ${worstAll.x.toFixed(2)}x (${worstAll.scene}, frame ${worstAll.f})`
      : "no speed change anywhere"
  );
}
