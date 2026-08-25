---
title: "A seek-adapter contract for mixed animation runtimes in HyperFrames"
paper_id: "2026-198"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-08-25T06:50:38Z"
abstract: "HyperFrames owns the clock. Animation libraries do not play. Each motion runtime implements RuntimeDeterministicAdapter with discover, seek, and pause, plus optional duration inference and readiness. One renderSeek pass fans out to every registered adapter. GSAP registers a paused timeline on window.__timelines keyed by data-composition-id. Lottie and Anime.js push instances onto arrays. CSS and WAAPI are discovered from computed styles and document.getAnimations. Three.js and TypeGPU receive hf-seek CustomEvents. Duration is a real fork. CSS, WAAPI, and Lottie can floor length from finite animations. Three.js cannot inspect AnimationMixer and requires root data-duration. GSAP 3.x skips a render when totalTime equals _tTime, so the adapter nudges then seeks. This tutorial cites the public Apache-2.0 adapters at commit 2ca578f9455ca928ab168e7dd08a1a3a9d834788. It is not the HTML data-* composition contract."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

# A seek-adapter contract for mixed animation runtimes in HyperFrames

The HTML authoring contract (`data-composition-id`, clips, tracks, `data-*` timing) is a separate artifact. This paper is the adapter interface: how HyperFrames seeks GSAP, Lottie, CSS keyframes, the Web Animations API, Anime.js, Three.js, and TypeGPU on one clock. HeyGen's [HTML-to-video research post](https://www.heygen.com/research/html-to-video) already covers capture (seek-don't-play, `beginFrame`) as a three-method `FrameAdapter`. It does not document per-runtime registries, duration floors, or the GSAP `_tTime` nudge.

The contract is implemented TypeScript, not a wishlist. At commit [`2ca578f9455ca928ab168e7dd08a1a3a9d834788`](https://github.com/heygen-com/hyperframes/tree/2ca578f9455ca928ab168e7dd08a1a3a9d834788), adapters live under [`packages/core/src/runtime/adapters/`](https://github.com/heygen-com/hyperframes/tree/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters). Authoring recipes live in [`skills/hyperframes-animation/adapters/`](https://github.com/heygen-com/hyperframes/tree/2ca578f9455ca928ab168e7dd08a1a3a9d834788/skills/hyperframes-animation/adapters). GSAP is the default authoring path. The other adapters exist so a composition can mix runtimes and still be seeked in one pass.

## The adapter type

[`packages/core/src/runtime/types.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/types.ts) names the interface `RuntimeDeterministicAdapter`:

```ts
export type RuntimeDeterministicAdapter = {
  name: string;
  discover: () => void;
  seek: (ctx: { time: number; suppressEvents?: boolean }) => void;
  pause: () => void;
  play?: () => void;
  revert?: () => void;
  getReadyPromise?: () => PromiseLike<unknown> | null;
  getInferredDurationSeconds?: () => number | null;
};
```

Required methods are `discover`, `seek`, and `pause`. `play` and `revert` are optional. `getReadyPromise` is the async gate (Three.js `DefaultLoadingManager`, map `whenReady`, D3 `transition.end`). `getInferredDurationSeconds` is how a non-GSAP runtime reports a finite end time so root `data-duration` can be omitted. Returning `null` means "nothing usable yet" — still-loading Lottie JSON, or an infinite CSS iteration — not "zero length."

HyperFrames owns time. Authors register paused instances; they do not call `play()` for render-critical motion. Multiple runtimes may coexist. The runtime seeks all of them on each `renderSeek`.

## One seek, every runtime

[`init.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/init.ts) installs the adapters once:

```ts
state.deterministicAdapters = [
  createWaapiAdapter(),
  createCssAdapter({
    resolveStartSeconds: (element) => resolveStartForElement(element, 0),
  }),
  createAnimeJsAdapter(),
  createLottieAdapter(),
  createThreeAdapter(),
  createMapboxAdapter(),
  createLeafletAdapter(),
  createGoogleMapsAdapter(),
  createMaplibreAdapter(),
  createD3Adapter(),
  createTypegpuAdapter(),
  createGsapAdapter({ getTimeline: () => state.capturedTimeline }),
];
```

`renderSeek` quantizes to the canonical fps, then `seekTimelineAndAdapters` walks that array. If a captured GSAP timeline is bound, the transport seeks it directly and **skips** the `gsap` adapter so GSAP is not double-sought. Every other adapter still receives the raw time `t`. Adapter failures are swallowed (`runtime.init.transport.adapter`); one broken Lottie instance does not freeze CSS.

Map and D3 adapters in the same directory implement the same type but do not seek. They are `createReadinessAdapter` wrappers ([`_readiness.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/_readiness.ts)): empty `seek`/`pause`, and `getReadyPromise` waiting on `window.__hfLeaflet` / `__hfMapbox` / `__hfD3`. They share the interface so `collectAdapterReadyPromises` can delay `__renderReady` until tiles or transitions settle. They are not a second motion catalog.

## How each runtime is found and driven

| Runtime | Registry or discovery | Seek | Duration inference |
| --- | --- | --- | --- |
| GSAP | `window.__timelines[<data-composition-id>]` | `totalTime` nudge, else `seek` | captured `timeline.duration()` |
| Lottie | `window.__hfLottie[]`; also `lottie.getRegisteredAnimations()` | `goToAndStop(ms)` or dotLottie frame/`seek(%)` | `totalFrames / frameRate`, or player `duration` |
| Anime.js | `window.__hfAnime[]` | `instance.seek(timeMs)` | none in the adapter |
| CSS | computed `animation-name` ≠ `none` | WAAPI `currentTime`, else negative `animation-delay` | finite `endTime` + clip `data-start` |
| WAAPI | `document.getAnimations()` plus an `Element.animate` hook | `currentTime` then `pause` | finite `effect.getComputedTiming().endTime` |
| Three.js | none | `window.__hfThreeTime` + `hf-seek` | none; root `data-duration` required |
| TypeGPU | none | `window.__hfTypegpuTime` + `hf-seek` | none; root `data-duration` required |

GSAP registration is a keyed object, not an array. The key must equal the root `data-composition-id`. [`gsap.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/gsap.ts) is short because the interesting work is a 3.x render skip:

```ts
timeline.pause();
const safeTime = Math.max(0, Number(ctx.time) || 0);
if (typeof timeline.totalTime === "function") {
  // GSAP 3.x skips rendering when the new totalTime equals _tTime.
  // Nudge first to force a dirty state, then seek to the exact time.
  timeline.totalTime(safeTime + 0.001, true);
  timeline.totalTime(safeTime, suppressEvents);
} else {
  timeline.seek(safeTime, suppressEvents);
}
```

When the transport already owns `state.capturedTimeline`, it does a related refresh itself: seek, then `totalTime(t + 0.001, true)` / `totalTime(t, true)` unless `suppressEvents` or a zero-duration callback tween is present. The GSAP seek is also clamped to `totalDuration()` so a host window longer than the last tween holds the end pose; adapters still receive the raw `t`.

Lottie ([`lottie.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/lottie.ts)) type-guards on `goToAndStop` versus `pause` plus `totalFrames`/`duration`. lottie-web is sought with `goToAndStop(time * 1000, false)` (milliseconds, not frames). dotLottie v2 uses `setCurrentRawFrameValue`; v1 uses `seek(percentage)`. Auto-discovery copies `lottie.getRegisteredAnimations()` into `__hfLottie` so a forgotten `push` still works. `totalFrames === 0` returns `null` from `getInferredDurationSeconds` so a not-yet-loaded JSON is not treated as zero duration.

Anime.js v4 is stricter. [`animejs.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/animejs.ts) seeks `instance.seek(timeMs)` on `__hfAnime`. `discover()` still looks at `anime.running`, which v4 no longer exports, so it is inert on current bundles. An unregistered v4 instance is never seeked. Skill recipes use `autoplay: false` and an explicit `push`.

CSS ([`css.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/css.ts)) scans every element for a computed `animation-name`. Local time is `max(0, t - start) * 1000`, with `start` from the composition start resolver (clip `data-start`). If the element exposes WAAPI handles, those are sought and paused. Otherwise the adapter pauses and sets `animation-delay` to a negative local time. Unbounded `endTime` is skipped for duration inference.

WAAPI ([`waapi.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/waapi.ts)) snapshots `document.getAnimations()`, then wraps `Element.prototype.animate` so later animations are still tracked. A per-animation baseline stores composition time and animation time so a handle created mid-composition is not rewound to global `t`. After an empty discover, the per-frame global scan is skipped until the hook sees an `animate()` call.

## Duration is a per-runtime floor

`resolveAdapterDurationFloorSeconds` in `init.ts` folds every adapter's `getInferredDurationSeconds()` into the same duration floor that already considers root `data-duration` and media windows. That is why CSS-only or Lottie-only compositions can omit root `data-duration` when every animation is finite. Infinite CSS/WAAPI iterations have no finite `endTime`, so they never contribute. Lint `root_composition_missing_duration_source` (see [`skills/hyperframes-core/references/determinism-rules.md`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/skills/hyperframes-core/references/determinism-rules.md)) fires when nothing remaining can supply a length.

Three.js and TypeGPU deliberately omit the hook. The Three adapter does not inspect `AnimationMixer` or `AnimationClip` duration; it only publishes time. Anime.js instances expose `duration`, but the adapter does not read it. Those compositions need an authored root `data-duration` (or some other finite signal such as a GSAP timeline). Render length is still the root attribute when present, not GSAP timeline length — do not pad a timeline with empty tweens to extend the video.

## GPU events share one dispatcher

Three.js and TypeGPU cannot be introspected. [`three.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/three.ts) sets `window.__hfThreeTime` and calls `dispatchSeekEvent`. [`typegpu.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/typegpu.ts) does the same for `__hfTypegpuTime`. Both fire `new CustomEvent("hf-seek", { detail })` through [`seek-dispatch.ts`](https://github.com/heygen-com/hyperframes/blob/2ca578f9455ca928ab168e7dd08a1a3a9d834788/packages/core/src/runtime/adapters/seek-dispatch.ts).

The dispatcher deduplicates by exact float equality so a composition that loads both adapters does not render twice per scrub. `detail.waitUntil(promise)` must be called **synchronously** from the listener; a late call throws. TypeGPU authors register `device.queue.onSubmittedWorkDone()` there so capture waits for the GPU queue. After video-frame injection, the engine calls `window.__hfReseekGpu`, which uses `forceDispatchSeekEvent` to bypass the dedup at the same `t`. TypeGPU `pause()` starts a 250 ms present heartbeat when `[data-composition-id][data-requires-webgpu]` is present.

Compositions listen and render from event time, not `performance.now()`:

```js
window.addEventListener("hf-seek", (e) => {
  mixer.setTime(e.detail.time);
  renderer.render(scene, camera);
});
```

WebGPU init is async; GSAP tweens that the player must read at load still have to be registered synchronously, before `await navigator.gpu.requestAdapter()`. Html-in-canvas plus WebGPU needs Chromium flags (`CanvasDrawElement`, `--enable-unsafe-webgpu`). That is an engine launch constraint, not part of the adapter type.

## Limits

We did not invent seek-driven HTML video. Remotion and the HeyGen research post already cover the capture loop; this paper does not re-measure `beginFrame`, font inlining, or flipbooks. We do not claim equal production use of every adapter, pixel-identical GPU output across OS images, or that Anime.js duration is auto-inferred (the adapter does not implement `getInferredDurationSeconds`). Map and D3 entries are readiness gates, not sought timelines. We do not document Studio UI, cloud pricing, or any private HTML emitter.

The finding is narrower: mixed animation runtimes become one deterministic video clock if each runtime implements a small seek/pause/discover adapter, duration is inferred only where the library can name a finite end, and GPU scenes subscribe to a shared `hf-seek` event instead of running their own rAF loop.