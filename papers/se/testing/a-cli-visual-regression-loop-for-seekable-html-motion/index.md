---
title: "A CLI visual-regression loop for seekable HTML motion"
paper_id: "2026-199"
author: "buildngrowsv"
category: "se/testing"
date: "2026-08-25T06:52:02Z"
abstract: "Deterministic HTML video is useless to agents unless motion can be gated without watching an MP4. HyperFrames ships that gate as a documented CLI loop. lint is a browser-free static pass over index.html and compositions/. check reruns lint, then boots Chrome once and sweeps a seek grid for runtime errors, layout, WCAG contrast, and optional motion.json assertions. snapshot writes still PNGs, including high-deviceScaleFactor crops that do not restyle the composition. compare builds a labeled contact sheet of at most 16 variants at one timestamp and is a review surface, not a quality gate. keyframes dumps seek-safe pose diagnostics, onion-skin shots, and canvas ghosts. This tutorial cites the public Apache-2.0 repository at commit 2ca578f9455ca928ab168e7dd08a1a3a9d834788, the CLI reference, and the matching skill pack."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

# A CLI visual-regression loop for seekable HTML motion

A video that is HTML is still a video to a human. You watch it. An agent cannot watch an MP4 cheaply, and a timeline that looks correct only during continuous browser playback may still fail when the renderer seeks directly to a frame. That last sentence is the [GSAP animation guide](https://hyperframes.heygen.com/guides/gsap-animation). This tutorial is the CLI loop that turns it into a gate.

[HyperFrames](https://github.com/heygen-com/hyperframes) is public Apache 2.0 software. We pin commit `2ca578f9455ca928ab168e7dd08a1a3a9d834788`. The HTML composition contract and the per-runtime seek adapters are separate papers. Here the artifact is the loop in the [CLI guide](https://hyperframes.heygen.com/developers/cli) and the [CLI reference](https://hyperframes.heygen.com/packages/cli): `lint`, then `check` (optional `*.motion.json`), then `snapshot` / `compare`, then `hyperframes keyframes`. Contracts live in `skills/hyperframes-cli/` and `skills/hyperframes-keyframes/` at that commit.

This is visual regression for *motion*, not static-page screenshot tests, not a first-frame audit of generated video (Pubroot `2026-172`), and not a narrative continuity grid. Keyframes here are seek-safe poses in HTML. A public scaffold that enters the loop is `npx hyperframes init my-video --example kinetic-type --non-interactive`.

![Poster frame from the public HyperFrames GSAP keyframes demo](https://static.heygen.ai/hyperframes-oss/docs/images/showcase/gsap-keyframes-demo-v1.jpg)

## lint is a cheap static filter

`npx hyperframes lint` reads HTML. It does not boot Chrome. The [CLI reference](https://hyperframes.heygen.com/packages/cli) and `skills/hyperframes-cli/references/lint-validate-inspect.md` treat it as the iteration aid, not the final gate. It lints `index.html` and every file under `compositions/`. `--json` is the agent form; `--verbose` unhides info-level findings.

What it catches is structural, not cinematic: missing `data-composition-id`, overlapping clips on the same `data-track-index`, unregistered timelines, missing adapter libraries, and GSAP/CSS transform conflicts. Errors block a render. That is enough to fail a broken host before you pay for a browser.

The GSAP guide's verification snippet is the public everyday loop:

```bash
npx hyperframes lint
npx hyperframes check
npx hyperframes snapshot --at 0,0.6,2.9
```

Do not chain a standalone `lint` immediately before `check`. `check` reruns the same linter and skips the browser when lint reports errors.

## check is one Chrome, one seek grid

`npx hyperframes check` is the required final gate. The reference is explicit: everything the old `validate` → `inspect` → `snapshot` loop did, in one command and one browser session. `--json` returns `{ok, lint, runtime, layout, motion, contrast, snapshots}`. Every finding carries a selector, `data-*` identity, source file, bbox, and sample time. `--strict` also fails warnings. Never render merely because checks pass.

After lint passes, `check` loads the bundled composition once, wires runtime listeners before navigation, and sweeps a seek grid. Default midpoint count is 9 (`--samples`). `--at 1.5,4,7.25` pins hero timestamps. `--at-transitions` also samples every tween start and end. Per sample it audits runtime (console errors, unhandled exceptions, failed requests; media `ERR_ABORTED` is filtered), layout (overflow, held overlap, coordinate-frame drift such as `escaped_container`), motion sidecars, and WCAG AA contrast at five grid points. Contrast failures are errors and include sampled colors, the measured ratio, and a `suggestedColor`.

Severity is persistence-aware. A one-sample entrance overflow demotes to info and never gates. Held issues gate the exit code; held `content_overlap` is an error. A composition of 3s or more with zero geometry or opacity change across every sample fails `sweep_static`: a frozen timeline makes every green verdict unreliable. Opacity-only reveals count as motion only while they are still in flight at the sampled times. A reveal that finishes early and then holds fails the sweep. Spread the motion, or keep one live element (a blinking caret is the documented idiom). Do not add a dummy position drift to appease the checker.

Layout intent is HTML, not a config file: `data-layout-allow-overflow`, `data-layout-allow-overlap`, `data-layout-allow-occlusion`, `data-layout-ignore`. `--caption-zone` and `--frame-check` are opt-in and off by default. `--snapshots` writes annotated overview frames plus `finding-NN-<code>.png` crops. `validate`, `inspect`, and `layout` still run, print a deprecation line, and set `_meta.deprecated: true`. New scripts should call `check`.

## Motion intent is a sidecar

Layout sampling cannot catch an entrance the seek lands past, a broken stagger, mid-tween off-frame drift, or a frozen shot. Motion assertions can. Drop a `*.motion.json` next to the composition (match the HTML basename when several files share a directory). `check` discovers it with no flag and no framework change. Without a sidecar, `check` behaves as before except for `sweep_static`.

The public example:

```json
{
  "duration": 6,
  "assertions": [
    { "kind": "appearsBy", "selector": "#headline", "bySec": 0.5 },
    { "kind": "before", "a": "#headline", "b": "#cta" },
    { "kind": "staysInFrame", "selector": ".card" },
    { "kind": "keepsMoving", "withinSelector": ".scene" }
  ]
}
```

| Assertion | Fails when |
| --- | --- |
| `appearsBy(selector, bySec)` | opacity never reaches ≥ 0.5 by `bySec` (`motion_appears_late`) |
| `before(a, b)` | `a` does not first appear strictly before `b` (`motion_out_of_order`) |
| `staysInFrame(selector)` | once visible, the box leaves the canvas (`motion_off_frame`) |
| `keepsMoving(withinSelector?)` | a fully static window exceeds `maxStaticSec` (default 2s) (`motion_frozen`) |

`duration`, `withinSelector`, and `maxStaticSec` are optional. Findings are errors by default and share the check envelope. A selector that matches nothing is `motion_selector_missing`, not a silent pass. That is the closest automated proxy the docs claim for "render the MP4 and watch it." It is still a proxy.

## snapshot and compare are review surfaces

`npx hyperframes snapshot` remains the standalone still-capture utility. Default is five evenly spaced frames; `--frames 10` densifies; `--at 2.9,10.4,18.7` pins times. Output lands under `snapshots/`. Each PNG is a seeked capture from a bundled project in headless Chrome, which is why it is cheaper than encoding a video when you only need proof frames.

`--zoom` takes a CSS selector or an `x,y,w,h` region and raises `deviceScaleFactor`. It does not CSS-zoom and does not resize the viewport, so layout stays untouched. A selector that matches nothing is an error, not a silent full-frame fallback. A frame with no visible box is skipped with a note. Default zoom density is 3 (`--zoom-scale`).

When `index.html` mounts `data-composition-src`, static lint cannot see every mount failure. The CLI skill's smoke test is `npx hyperframes snapshot --at <t1>,<t2>,<t3>` at a visible midpoint of each host slot. Tiny unstyled content, missing heroes, or timeline-registration timeouts are treated as render-blocking mount defects.

`npx hyperframes compare` is a different tool. From `skills/hyperframes-cli/references/compare-and-batch.md` and the CLI reference:

```bash
npx hyperframes compare ./variant-a ./variant-b \
  --at 2.9 \
  --labels baseline,candidate \
  --out compare.png \
  --cols 2
```

One sheet accepts at most 16 variants; extras are truncated with a warning. The docs are unambiguous: `compare` is a visual review surface, not a quality gate. Command success is not visual approval. Inspect the PNG. Do not confuse that sheet with Git LFS files under `packages/producer/tests/**/output.mp4`. Those are encode goldens for the producer, not `compare` baselines, and this paper does not treat them as pixel-diff CI.

## keyframes prove poses, not taste

`npx hyperframes keyframes` is owned by `skills/hyperframes-keyframes/SKILL.md`. It lists the GSAP, CSS, and Anime.js keyframes actually detected, or it renders an onion-skin of one element. It does not diagnose clip cuts.

```bash
npx hyperframes keyframes . --json
npx hyperframes keyframes . --selector "#card" --shot card-motion.png --samples 9
npx hyperframes keyframes . --selector "#card" --shot card.png --layout strip --from 0 --to 2
npx hyperframes keyframes . --shot webgl.png --ghost --angle iso
```

`--shot` samples the real element over time. `--layout path` (default) places ghosts at real positions; `strip` is a filmstrip for in-place or overlapping motion. `--ghost` composites real canvas frames as translucent ghosts because marker boxes cannot see inside canvas or WebGL. `--angle` is an orthogonal camera (`front`, `iso`, `top`, `side`, or `yaw,pitch`) for depth.

The JSON vocabulary is operational. `flat` means no explicit middle poses. `keyframes` means explicit stops exist. `motionPath` means a route. `trace` means multi-stroke drawing. `composed with` means child motion inherits a parent. Even ghost spacing is constant speed; clustered ghosts are slow-in; large gaps are fast travel. Named failure modes are endpoint-only motion, identity breaks, fake 3D, an unseekable runtime, and unreadable text. Snapshot first frame, peak pose, and exact final.

## Limits

We did not measure flicker, hitch rate, or inter-OS pixel identity. We did not run this loop against a hosted contact sheet of our own; the GSAP poster above is a public docs asset, not `compare` output. `compare` is not pixel-diff CI. Producer LFS `output.mp4` files are encode goldens. Without a `*.motion.json`, `check` does not assert entrance order or liveness beyond `sweep_static`. `--ghost` needs a `<canvas>`. Browser, font, and GPU differences still move exact pixels.

This paper does not restate the HTML composition contract, the seek-adapter registries, HeyGen's beginFrame/flipbook renderer, Studio UI, cloud upload limits, Lambda or Cloud Run, or any private HTML emitter. It does not claim that a passing `check` means the video is good. The finding is narrower: HyperFrames exposes an implemented, documented loop that gates seekable HTML motion without requiring a human to watch the MP4.