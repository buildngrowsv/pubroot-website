---
title: "Capping CGWindowListCreateImage to three captures per cycle to stop SLSWindowListCreateImageProxying timeouts"
paper_id: "2026-187"
author: "buildngrowsv"
category: "se/performance"
date: "2026-08-25T06:40:01Z"
abstract: "SuperDimmer's per-region brightness analysis called CGWindowListCreateImage for every visible window on a two-second timer. During idle and active transitions, Console.app recorded clusters of the named WindowServer error SLSWindowListCreateImageProxying timeout \u2014 thirteen consecutive failures on one idle transition, two on the matching return-to-active. We capped captures at three per analysis cycle, kept an analysis cache for the rest, and routed window and display captures through ScreenCaptureKit's SCScreenshotManager when useModernAPI is true (macOS 13+). Separately, wrapping each capture-and-analyze step in autoreleasepool dropped launch resident memory from 298 MB to 214 MB and cut per-cycle spikes by about 90 percent. WindowServer CPU percentages in our notes (80\u2013100 percent hypothesized; 40\u201380 percent versus 5\u201310 percent in a service header) were not backed by an Instruments trace and are not claimed as measurements."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## The named timeout

SuperDimmer is a macOS menu-bar app that dims bright window regions by capturing window pixels, measuring luminance, and placing click-through overlay windows. The capture path originally used CoreGraphics `CGWindowListCreateImage`. That call is deprecated as of macOS 15.0, and under load it fails with a WindowServer error we logged as:

```
[ERROR] SLSWindowListCreateImageProxying:156 unable to complete request due to timeout: [13 consecutive errors]
```

The failures were not uniformly random. They clustered on idle and active transitions. After the 30-second idle threshold, `ActiveUsageTracker` published IDLE, inactivity trackers paused decay and auto-hide timers, and the next dimming analysis cycle still tried to capture every visible window. One idle log cluster recorded 13 consecutive `SLSWindowListCreateImageProxying` timeouts. The matching return-to-active sequence (idle for 412 seconds) recorded 2 of the same error. Internal notes described the typical pattern as 10–15 consecutive timeouts on going idle and 2–5 on returning.

Dimming did not crash. Overlays stayed up on cached brightness, so the product still looked alive while WindowServer dropped capture requests. The cost was stale overlays plus a capture storm against WindowServer already handling system-wide idle or wake work.

We hypothesized that WindowServer was CPU-saturated (community reports of 100 percent CPU; our own notes used 80 percent peak as a working estimate). We did not attach an Instruments WindowServer trace to those notes, so those percentages remain hypotheses. What we did measure is the timeout cluster itself, the capture fan-out that produced it, and a separate resident-memory drop from `autoreleasepool`.

## Burst captures on a two-second cycle

Brightness analysis runs on `scanInterval`, default 2.0 seconds. In per-region mode the coordinator walked the visible window list and captured each window that missed the analysis cache. Ten to twenty windows in that loop meant ten to twenty `CGWindowListCreateImage` calls in one cycle, with no timeout handling, no backoff, and no circuit breaker. Failed captures retried on the next tick.

`ScreenCaptureService.captureWindow` used the window's own bounds, `.optionIncludingWindow`, and skipped the 100 ms full-display throttle so intelligent mode could fire many window captures in succession:

```swift
let image = CGWindowListCreateImage(
    .null,
    .optionIncludingWindow,
    windowID,
    options
)
```

That is a synchronous WindowServer round-trip. When idle or active notifications already had WindowServer busy, the burst queued past the proxying timeout and the next 2-second cycle repeated the same set.

## Three captures per cycle, then cache

The first shipping fix is a capture budget, not a new API. `DimmingCoordinator` keeps `maxCapturesPerCycle = 3` and a rotating `windowCaptureIndex`. Cache hits still apply immediately (`cacheMaxAge` is 10.0 seconds). Cache misses increment a per-cycle counter; once it hits 3, remaining windows are deferred to the next cycle. An earlier comment still says "one window per cycle"; the constant that actually ships is 3.

```swift
if capturesThisCycle >= maxCapturesPerCycle {
    debugLog("⏸️ Reached capture limit (\(maxCapturesPerCycle)) for this cycle, deferring window \(window.id)")
    continue
}
autoreleasepool {
    capturesThisCycle += 1
    guard let windowImage = screenCapture.captureWindow(window.id) else {
        return
    }
    // detect regions, write analysisCache, emit decisions
}
```

The same cap is applied in `performPerWindowAnalysis()` and `performPerRegionAnalysis()`. The documented trade-off is slower first-look at a cold window list: about 3–6 seconds to cover 10 new windows at a 2-second interval, with a stated cache-hit rate around 80 percent so most cycles do not capture at all. That 80 percent figure is an estimate in the implementation notes, not a logged hit-rate table.

The design target after the cap was zero `SLSWindowListCreateImageProxying` timeouts on idle transitions (the testing notes used 12 timeouts per transition as the "before" column, consistent with the 10–15 log pattern). Phase 2 of those notes still listed Console verification as pending, so we do not treat post-fix timeout rate as a measured Instruments result.

## ScreenCaptureKit via SCScreenshotManager

The second fix replaces the deprecated one-shot CoreGraphics call on the hot path. `ScreenCaptureService.useModernAPI` defaults to true. On macOS 13.0 or later, `captureWindow` and `captureMainDisplay` delegate to `ModernScreenCaptureService`. That type caches `SCShareableContent` for 2.0 seconds (the file comments that `SCShareableContent.current` takes 50–100 ms; that timing is a comment, not a benchmark table), builds an `SCContentFilter` for the target window, and takes a single frame with `SCScreenshotManager.captureImage`:

```swift
let filter = SCContentFilter(desktopIndependentWindow: window)
let config = SCStreamConfiguration()
config.width = window.frame.width > 0 ? Int(window.frame.width) : 1920
config.height = window.frame.height > 0 ? Int(window.frame.height) : 1080
let image = try await SCScreenshotManager.captureImage(
    contentFilter: filter,
    configuration: config
)
```

The same entitlement already used for `CGWindowListCreateImage` (`com.apple.security.device.screen-capture`) is sufficient; we did not add a second permission. Capture still downsamples with `downsampleFactor = 0.25` for analysis, not for pixels-on-screen overlay drawing.

Callers remain synchronous. `captureWindowSync` bridges async ScreenCaptureKit with a `DispatchSemaphore` that waits up to 2.0 seconds. That wrapper can still block the calling thread; it is a migration bridge, not a fully async coordinator. `captureDisplay` and `captureRegion` still call `CGWindowListCreateImage` directly.

The `ModernScreenCaptureService` header compares old versus new as 40–80 percent versus 5–10 percent WindowServer CPU, 50 MB versus 5–10 MB per capture, and 10–15 timeouts versus 0. Those CPU and per-capture memory figures are hypothesized in the header and in a testing-strategy table (80 percent / 30 percent / 10 percent WindowServer CPU; 50 MB / 50 MB / 5 MB; 200 ms / 180 ms / 50 ms cycle time). They are not Instruments samples. The timeout counts (10–15, and 12 in the table) match the Console clusters described above; the "after = 0" column is the success criterion, not a published post-migration log dump.

## Autoreleasepool around each CGImage

Independent of the timeout, each successful capture allocated a `CGImage` that lived until the run loop drained the default autorelease pool. Notes for 6K displays put that image at 50–100 MB; with 10 windows per cycle the coordinator comment estimated 500–1000 MB of temporaries. `performAnalysisCycle` logs resident size via `mach_task_basic_info` when the delta exceeds 5 MB.

Wrapping capture plus region detection in `autoreleasepool` releases those images when the block exits. Measured launch resident memory went from 298 MB to 214 MB (−84 MB, 28 percent). A later HUD-close test dropped 214 MB to 172 MB: 42 MB for 5 HUD windows, about 8 MB each — a correction of an earlier 80–90 MB-per-HUD guess. The same notes put the no-HUD baseline at about 256 MB before the pool fix and 172 MB after (−84 MB, 33 percent). Per-cycle spikes went from +50–100 MB to +5–10 MB (about 90 percent). An earlier expected-impact line of "~150–180 MB" base memory did not match the 214 MB we actually recorded at launch.

| Observation | Value | Kind |
|---|---|---|
| Idle timeout cluster | 13 consecutive `SLSWindowListCreateImageProxying` errors | Console log |
| Return-to-active cluster | 2 of the same error after 412 s idle | Console log |
| Typical idle / return clusters | 10–15 / 2–5 timeouts | Notes summarizing logs |
| Windows captured per cycle (before) | 10–20 simultaneous `CGWindowListCreateImage` | Coordinator loop |
| Capture budget (after) | `maxCapturesPerCycle = 3` on a 2.0 s `scanInterval` | Shipping constant |
| Launch resident memory | 298 MB → 214 MB (−28 percent) | Measured |
| HUD-closed baseline | 214 MB → 172 MB (5 HUDs, ~8 MB each) | Measured |
| Per-cycle resident spike | +50–100 MB → +5–10 MB (~90 percent) | Measured via `task_info` |
| WindowServer CPU 80–100 percent | hypothesized; also 40–80 vs 5–10 in a header | Not an Instruments table |

## Limits

This is a production case study of one overlay-dimming app, not a general ScreenCaptureKit benchmark. We do not claim compositor injection, GPU-versus-CPU percentages, or a measured post-fix timeout rate of zero. The 80–100 percent WindowServer CPU figures, the 40–80 versus 5–10 percent header comparison, the 70 percent CPU-reduction line, the 5 MB GPU-capture figure, and the 50 ms cycle-time target are hypothesized or planned metrics; only the Console timeout clusters, the three-capture cap, and the 298 → 214 MB (and 214 → 172 MB HUD-close) resident numbers are measured. The ~80 percent cache-hit rate and the 3–6 second cold-list delay are stated trade-offs, not timed user studies. `captureWindowSync` still blocks for up to 2.0 seconds. `captureDisplay` and `captureRegion` still use `CGWindowListCreateImage`. Competitor menu-bar memory numbers in the same notes are informal and are not used as a baseline here.