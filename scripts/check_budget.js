// Warn when a scene's encoded frames exceed the budget in PIPELINE.md:
// <= 300 KB per desktop frame (d/), <= 150 KB per mobile frame (m/).
// Usage: node scripts/check_budget.js        (exit code 1 if any scene is over)
const fs = require("fs");
const path = require("path");

const FRAMES = path.join(__dirname, "..", "web", "public", "frames");
const BUDGET_KB = { d: 300, m: 150 };

if (!fs.existsSync(FRAMES)) {
  console.log("no frames yet:", FRAMES);
  process.exit(0);
}

let over = false;
let grand = 0;
for (const scene of fs.readdirSync(FRAMES).sort()) {
  for (const set of ["d", "m"]) {
    const dir = path.join(FRAMES, scene, set);
    if (!fs.existsSync(dir)) continue;
    const sizes = fs.readdirSync(dir)
      .filter((f) => f.endsWith(".webp") || f.endsWith(".avif"))
      .map((f) => fs.statSync(path.join(dir, f)).size / 1024);
    if (!sizes.length) continue;
    const total = sizes.reduce((a, b) => a + b, 0);
    const avg = total / sizes.length;
    const max = Math.max(...sizes);
    const big = sizes.filter((s) => s > BUDGET_KB[set]).length;
    const status = avg > BUDGET_KB[set] ? "OVER" : big ? "warn" : "ok";
    if (status === "OVER") over = true;
    grand += total;
    console.log(
      `${status.padEnd(4)} ${scene}/${set}: ${sizes.length} frames, ` +
      `${(total / 1024).toFixed(1)} MB, avg ${avg.toFixed(0)} KB, max ${max.toFixed(0)} KB` +
      ` (budget ${BUDGET_KB[set]} KB/frame${big ? `, ${big} frames over` : ""})`
    );
  }
}
console.log(`total ${(grand / 1024).toFixed(1)} MB`);
process.exit(over ? 1 : 0);
