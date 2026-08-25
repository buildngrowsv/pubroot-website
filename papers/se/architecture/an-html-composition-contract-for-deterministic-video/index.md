---
title: "An HTML composition contract for deterministic video"
paper_id: "2026-188"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-08-25T06:41:18Z"
abstract: "HyperFrames renders video from HTML, but the interesting software artifact is not the capture loop. It is the composition contract that makes a static document a seekable timeline. A root element carries `data-composition-id`, pixel size, and a compile-time `data-duration`. Timed visual children take `class=\"clip\"`, a stable `id`, `data-start`, `data-duration`, and `data-track-index`. Tracks are a temporal occupancy rule, not paint order; same-track overlap is undefined and lint-fails. `data-start` may be seconds or a same-file clip-id expression. Visual clips must be direct children of the composition root, while `<video>` and `<audio>` are discovered by a flat query and may nest. Nested compositions travel through `<template>` and must share one id with the host slot and the paused timeline registry. This tutorial cites the public Apache-2.0 repository, the HTML schema, and the launch-video host. Capture details already covered in HeyGen's research post are treated as prior art."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

# An HTML composition contract for deterministic video

A video renderer that seeks HTML in headless Chrome is not a new idea. Remotion proved the shape; HeyGen's [HTML-to-video research post](https://www.heygen.com/research/html-to-video) already documents the HyperFrames capture path (seek-don't-play, `HeadlessExperimental.beginFrame`, FFmpeg JPEG flipbooks for `<video>`). This tutorial does not retell that pipeline. It documents the **authoring contract** that makes the pipeline possible: timing lives in HTML `data-*` attributes, not in a proprietary timeline JSON and not in wall-clock JavaScript.

The contract is public. [HyperFrames](https://github.com/heygen-com/hyperframes) is Apache 2.0. The HTML schema is at [hyperframes.heygen.com/reference/html-schema](https://hyperframes.heygen.com/reference/html-schema); clip timing is at [concepts/data-attributes](https://hyperframes.heygen.com/concepts/data-attributes). Agent-facing detail lives in `skills/hyperframes-core/` at commit `2ca578f9455ca928ab168e7dd08a1a3a9d834788`. We inspect those sources, plus the public [launch-video](https://github.com/heygen-com/hyperframes-launch-video) host.

## A sized root with locked duration

A composition is an HTML file. The top-level root sits in `<body>` with no `<template>` wrapper. It must be a real box with pixel `width`/`height`, and it must carry:

- `data-composition-id` — unique id; must equal the animation registry key
- `data-width` / `data-height` — authored frame size
- `data-start="0"` on the top-level root (`root_composition_missing_data_start` otherwise)
- `data-duration` — **render length**, not GSAP timeline length

A static root `data-duration` is read **before scripts run**, like frame size. A later `setAttribute` or `--variables` rewrite does not change the frame count. Clip-level `data-duration` is re-read from the live DOM. The root attribute may be omitted only when a finite duration is inferable (GSAP timeline, finite CSS/WAAPI, Lottie). Three.js, unbounded CSS/WAAPI, and a page with no animation signal require it. Lint: `root_composition_missing_duration_source`.

The public README registers a paused timeline on that same id:

```html
<div id="stage" data-composition-id="launch" data-start="0" data-width="1920" data-height="1080">
  <h1 id="title" class="clip" data-start="1" data-duration="4" data-track-index="1">Launch day</h1>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.from("#title", { opacity: 0, y: 40, duration: 0.8 }, 1);
    window.__timelines = window.__timelines || {};
    window.__timelines.launch = tl;
  </script>
</div>
```

One paused timeline per composition, built synchronously at load. Do not `play()`. Do not nest a child GSAP timeline into the host; HyperFrames seeks nested compositions independently.

## Clips: class, window, and parentage

A clip is any element with `data-start`, `data-duration` (where required), and `data-track-index`. Visual timed elements (`<div>`, `<img>`, `<section>`, …) also need `class="clip"`. Without the class, the runtime keeps the element visible for the whole composition and **ignores** its start/duration. `<video>` visibility is owned by the media runtime; `<audio>` has no visual lifecycle.

The visibility window is inclusive: a clip shows while `start ≤ t ≤ start + duration`, so the last frame holds the resolved end state.

Parentage is the silent failure. Visual `class="clip"` nodes must be **direct children of the composition root**. A clip wrapped in an extra `<div>` is not registered, so its timing is ignored and it stays on screen. Put wrappers *inside* the clip, or animate the clip itself. That rule is in `skills/hyperframes-core/references/data-attributes.md` at the pinned commit. Media is the exemption, covered below. Duplicate `<video>`/`<img>` ids across assembled files render blank: the producer injects frames by `getElementById`.

## Tracks occupy time; CSS paints

`data-track-index` is a **temporal occupancy** lane, not a z-stack. Two clips on the same track must not overlap. `hyperframes lint` flags the collision; the render is undefined. Paint order is CSS `z-index`. A clip on track `10` is not "in front of" track `1`.

Put sequential scenes on one visual track. Put an intentional overlap — a crossfade, a caption over B-roll — on a second track. The launch video puts voiceover on track `0` and scenes on `1`; skill docs often put audio at `10+` so visual lint stays readable. Either works if same-track ranges do not collide. Legacy aliases: `data-layer` → `data-track-index`, `data-end` → `data-duration`.

## Start times as numbers or clip ids

A numeric `data-start` is seconds from the start of **this** composition. A non-numeric value is a same-file clip-id expression: `intro` means "when `intro` ends"; `intro + 0.5` is a gap; `intro - 0.5` is an overlap.

```html
<video id="intro" data-start="0" data-duration="4" data-track-index="0"
       src="./intro.mp4" muted playsinline></video>
<section id="result" class="clip" data-start="intro - 0.5" data-duration="3" data-track-index="1">
  The result
</section>
```

References do not cross composition boundaries. The target must have a known duration. Cycles are rejected. A value that parses as a number is always absolute seconds. Negative offsets require a different track.

## Nested compositions as template transport

A host slot is itself a clip. `data-composition-src` names a file; paths resolve from the **project root**. The host's `data-composition-id` must equal the inner file's `data-composition-id` **and** the `window.__timelines["<id>"]` key — no `-mount`/`-slot` suffix. Per-file lint will not catch a rename; render then waits 45s for a timeline that never registers and captures static frames.

The runtime `fetch`es the file, `DOMParser`s it, and **clones only `<template>` contents** — `<head>` is discarded. Inlined CSS is rewritten to `[data-composition-id="<id>"] S`. A class on the inner root then fails to match; lint `subcomposition_root_styled_by_class` flags it. Prefer `#root`, which the scoper special-cases.

Host `data-duration` is the **slot window**, not the child timeline length. A short child holds its last frame. A short slot goes blank (`subcomposition_blanks_before_host`). Prefer `gsap.fromTo` inside sub-comps: the host re-seeks on each visibility, and `from()` records start state at registration.

## Media is discovered flat

`<video>` and `<audio>` work at any nesting depth, including inside a sub-comp `<template>`. The runtime does a flat `querySelectorAll("video, audio")` and rebases local `data-start` by ancestor composition starts. Do not call `play()`, `pause()`, or set `currentTime`. Videos are `muted` and `playsinline`; sound is a separate `<audio>` even when the file is the same.

The remaining constraint is timelines, not placement. A sub-comp timeline cannot reach host-root elements. If media lives on the host, drive its motion on the **main** timeline at global time, or keep the media inside the sub-comp that animates it. `data-media-start` offsets into the source file; for nested hosts the schema's child-timeline offset is `data-playback-start`.

## Author rules that keep a seek honest

The renderer samples time; it does not play. Visual state at time `t` must be a function of `t` alone. Banned for visual state: `Date.now()`, `performance.now()`, unseeded `Math.random()`, render-time network, input state, `repeat: -1`. Finite repeats use `floor`, not `ceil` (`gsap_repeat_ceil_overshoot`).

Do not tween `display` or raw `visibility` on a `.clip` — the framework owns clip lifecycle. GSAP `autoAlpha` and zero-duration `tl.set(..., { visibility })` are allowed only on non-clip wrappers inside a clip. Do not `gsap.set` later-scene clips at page load; they are not in the DOM yet. Motion belongs on a paused, seekable runtime registered to the composition id.

## A public host, not a demo card

![First five seconds of the public HyperFrames launch video](https://raw.githubusercontent.com/heygen-com/hyperframes-launch-video/main/docs/preview.gif)

[heygen-com/hyperframes-launch-video](https://github.com/heygen-com/hyperframes-launch-video) documents a 49.77s, 1920×1080, 30fps project: one root plus 17 sub-composition files. Sequential scene slots share `data-track-index="1"`; the root timeline is registered empty and paused. Voiceover is a host-page `<audio>` whose `data-duration` matches the root. Modular pattern: scenes in `compositions/*.html`, continuous audio at the host, one visual track unless a seam needs overlap.

```html
<div id="master-root" data-composition-id="master"
     data-width="1920" data-height="1080" data-start="0" data-duration="49.77">
  <div id="c-glass-intro" data-composition-id="glass-intro"
       data-composition-src="compositions/glass-intro.html"
       data-start="0" data-duration="18.24"
       data-width="1920" data-height="1080" data-track-index="1"></div>
  <!-- further slots on the same track, adjoining in time -->
  <script>
    window.__timelines = window.__timelines || {};
    window.__timelines["master"] = gsap.timeline({ paused: true });
  </script>
</div>
```

The project's README notes that `hyperframes lint` still reports overlapping clips and GSAP tween overlap as known punch-list items. The contract is checkable; a production host can still violate it and render.

## Checking the contract

`npx hyperframes lint` is the static gate (missing ids, same-track overlap, unregistered timelines, duration-source, CSS/GSAP transform fights). `npx hyperframes check` boots Chrome once for runtime errors, layout boxes, contrast, and optional motion assertions. Sub-compositions need `snapshot --at` midpoints: the three mount pitfalls (styles outside `<template>`, id mismatch, class-styled root) pass per-file lint and fail only when assembled.

## Limits

We did not invent HTML-as-video. Remotion, WebVideoCreator, and the HeyGen research post already cover seek-driven capture; this paper does not re-measure `beginFrame`, JPEG flipbooks, or font inlining. We do not claim pixel-identical output across OS images, a lint-clean launch-video host, equal use of every animation adapter, or that `class="clip"` is required on `<video>`. We do not document Studio UI, cloud pricing, or any private emitter of HyperFrames HTML.

The finding is narrower: a seekable video can be a static HTML document whose timing, occupancy, and nesting rules are declared in attributes the linter can check and the renderer can seek.