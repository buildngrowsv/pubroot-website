/**
 * capture_straw_compare_screenshot_for_publication.mjs
 *
 * PURPOSE:
 *   Reproducibly screenshot the gravity-hinged straw **article-facing** band: `h1`, lead
 *   paragraph, the three synchronized `.compare-row` canvases, and `.controls-outer`
 *   (sliders) so published figures can reference on-screen tilt/fill honestly.
 *
 * WHY THIS EXISTS:
 *   Headless `--screenshot` without waiting leaves canvases blank; tight crops at tilt 0°
 *   fail to show why pendulum straws beat a lid-rigid straw. We sweep `?tilt=` in the demo
 *   URL, wait for the physics loop to settle, then clip to the semantic region (not raw
 *   viewport guesses) so maintainers can iterate angles until teal/coral/violet separation
 *   reads clearly — “a bit less than horizontal” is usually mid‑80s degrees for this sim.
 *
 * SETUP (once):
 *   cd _cli && npm install
 *
 * RUN (serve the supporting-repo demo on PORT, e.g. python3 -m http.server 58410):
 *   node _cli/capture_straw_compare_screenshot_for_publication.mjs 85 \
 *     http://127.0.0.1:58410/SixtyFourOunceFlexibleJointStrawBottleConceptAnimation.html \
 *     /tmp/straw-compare.png
 *
 * DEPENDS:
 *   Playwright driving channel=chrome when present (macOS); otherwise bundled Chromium.
 */
import { chromium } from "playwright";

const tilt = process.argv[2] || "85";
const pageUrl = process.argv[3];
const outPath = process.argv[4] || `/tmp/straw-compare-tilt-${tilt}.png`;

if (!pageUrl) {
  console.error(
    "Usage: node capture_straw_compare_screenshot_for_publication.mjs <tiltDeg> <demoUrl> [outPath]"
  );
  process.exit(1);
}

const vw = 1760;
/* Tall viewport: mechanisms SVG + reference plate sit above the h1; keep everything in one window. */
const vh = 3200;

const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: vw, height: vh } });
const url = new URL(pageUrl);
url.searchParams.set("tilt", tilt);
url.searchParams.set("fill", "66");

await page.goto(url.toString(), { waitUntil: "networkidle", timeout: 60_000 });
await page.waitForTimeout(9500);

await page.locator("h1").first().scrollIntoViewIfNeeded();
await page.waitForTimeout(400);

const h1 = await page.locator("h1").first().boundingBox();
const row = await page.locator(".compare-row").first().boundingBox();
const controls = await page.locator(".controls-outer").first().boundingBox();
if (!h1 || !row) {
  console.error("Missing h1 or .compare-row");
  await browser.close();
  process.exit(1);
}

const pad = 16;
const top = Math.max(0, Math.floor(h1.y - pad));
const bottom = Math.ceil(
  (controls ? controls.y + controls.height : row.y + row.height) + pad
);
let clipHeight = bottom - top;
if (top + clipHeight > vh) {
  clipHeight = vh - top;
}
if (clipHeight < 50) {
  console.error("Degenerate clip", { top, bottom, vh });
  await browser.close();
  process.exit(1);
}
const clip = {
  x: 0,
  y: top,
  width: vw,
  height: clipHeight,
};

await page.screenshot({ path: outPath, clip });
console.log(JSON.stringify({ tilt, outPath, clip, url: url.toString() }));
await browser.close();
