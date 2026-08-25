---
title: "Per-region zone dimming on macOS using Rec. 709 luminance, an 8\u00d78 grid, and connected-component merge"
paper_id: "2026-180"
author: "buildngrowsv"
category: "cs/hci"
date: "2026-08-25T06:30:39Z"
abstract: "Whole-window dimming is the wrong unit when a macOS window is dark in its chrome and bright in its content\u2014Mail in dark mode with a white message body is the running example in SuperDimmer\u2019s detector. We document the shipped per-region pipeline. BrightnessAnalysisEngine computes perceived luminance with Rec. 709 coefficients Y = 0.2126R + 0.7152G + 0.0722B through Accelerate/vDSP, and it can sample an N\u00d7N cell grid (the documented balanced size is 8\u00d78 = 64 cells). BrightRegionDetector.detectBrightRegions still accepts that gridSize, but the live path ignores it, downsamples the window image to a fixed 80\u00d780 analysisResolution, thresholds a binary mask, flood-fills 4-connected components, and unions nearby bounding boxes. Overlay placement then converts the detector\u2019s top-down normalizedRect into Cocoa\u2019s bottom-up window coordinates. We cite those code constants, including SettingsManager.regionGridSize (commented default 8, stored default 6) and ScreenCaptureService.downsampleFactor = 0.25. A header comment on BrightnessAnalysisEngine lists a target of under 50 ms for a full screen at quarter resolution; that is a target, not a measurement. We do not report a timed benchmark."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Dark chrome and bright content

A screen-dimming overlay that covers an entire `NSWindow` treats the window as one luminance. That is the wrong HCI unit when the chrome is already dark and a content pane is not. SuperDimmer’s `BrightRegionDetector` is written for that mixed case: a dark-mode Mail window whose message body is a bright rectangle, a code editor with a rendered preview, or any window whose average luminance is low while a sub-rectangle is high. Per-window mode (`DetectionMode.perWindow`) still exists; it asks `BrightnessAnalysisEngine.averageLuminance` whether the whole capture exceeds the user threshold and, if so, dims the window. Per-region mode (`DetectionMode.perRegion`) is the path that finds *where* the bright pixels are, then places one overlay per merged rectangle.

![Dark-themed window with a bright content pane and a zone-detection grid overlay](https://superdimmer.com/assets/promo/blog-hero-zone-dimming-analysis.png)

The pipeline is capture → luminance → mask → connected components → size filter → Cocoa coordinate conversion → overlay. The rest of this note pins each step to constants in the shipping Swift, including two facts that comments and call sites disagree on: which luma formula the detector uses, and whether the 8×8 grid is still the analysis lattice.

## Rec. 709 luminance in BrightnessAnalysisEngine

`BrightnessAnalysisEngine` is the shared luminance calculator. Its coefficients are Rec. 709 (ITU-R BT.709) luma:

```swift
private let redCoefficient: Float = 0.2126
private let greenCoefficient: Float = 0.7152
private let blueCoefficient: Float = 0.0722
```

Pixels are unpacked from a DeviceRGB `CGContext` with premultiplied-last alpha, each 8-bit channel is divided by 255, and the weighted sum is assembled with `vDSP_vsmul` and `vDSP_vadd`. `vDSP_normalize` then yields mean and standard deviation; `vDSP_minv` / `vDSP_maxv` yield extrema. The engine also counts the share of samples above 0.7 (“bright”) and 0.9 (“very bright”). `SettingsManager.brightnessThreshold` is documented against the same Rec. 709 formula; the stored default is 0.85.

The engine can partition a capture into a square grid via `brightnessGrid(of:gridSize:)`. That helper’s Swift default is `gridSize: Int = 3` (a 3×3). Each cell is an `averageLuminance(of:inRect:)` over a slice of the image. This is the Rec. 709 grid path. The detector’s file header and usage example describe a coarser, larger grid for region finding: “Divide the image into a grid (e.g., 8x8 = 64 cells)” and `gridSize: 8`.

`SettingsManager.regionGridSize` is the user-facing N for that NxN lattice. Its comment still lists the design points: 4 → 16 cells (coarse), 8 → 64 cells (balanced), 16 → 256 cells (precise), “Default: 8”. First-launch load, however, was reduced on 8 January 2026 from 8 to 6 (“smaller grids = fewer, larger cells = larger bright region detections”). `DimmingProfile.regionGridSize` is 6. The settings-reset path still writes `regionGridSize = 8`. The coordinator always passes the live setting into `detectBrightRegions(..., gridSize: gridSize, minRegionSize: 4)`.

A header comment on `BrightnessAnalysisEngine` states a performance *target*: “Target: <50ms for full screen at 1/4 resolution.” The same comment also says the engine “Processes millions of pixels in milliseconds.” We do not treat either sentence as a measurement. Quarter-resolution matches `ScreenCaptureService.downsampleFactor`, whose default is `0.25`.

## What detectBrightRegions actually samples

The live `detectBrightRegions` signature still takes `gridSize` (default 6) and `minRegionSize` (default 4). Both parameters are marked deprecated in the method comment and are unused in the body. Detection downsamples the window `CGImage` to a square whose side is `analysisResolution`:

```swift
private let analysisResolution: Int = 80
func detectBrightRegions(
    in image: CGImage,
    threshold: Float,
    gridSize: Int = 6,  // Ignored - using analysisResolution instead
    minRegionSize: Int = 4  // Ignored - using pixel-based filtering
) -> [BrightRegion]
```

`getPixelBrightnessData` draws into an 80×80 8-bit RGBA context with `interpolationQuality = .low`, then computes a row-major luminance buffer. That inner loop does **not** use the Rec. 709 coefficients above. It uses BT.601 luma `0.299R + 0.587G + 0.114B`. The Rec. 709 constants remain the documented formula for the engine, the settings comments, and `brightnessGrid`; the per-region mask is currently BT.601. Grid helpers (`createBrightnessGrid`, `findConnectedComponents`, `calculateBoundingBox`) are still in the class and are used by `hasBrightRegions(in:threshold:gridSize:)` (default `gridSize: 4`), not by the overlay-producing entry point.

So the 8×8 figure is a real code constant—header example, settings comment, reset default—not the lattice of the current mask. The current lattice is an 80×80 buffer (6,400 samples). That is not native-resolution “pixel-level” analysis; a 2560×1440 window has 3,686,400 pixels, so the analysis buffer is 1/576 of that count.

## Connected components and merge

After downsampling, every sample above the threshold becomes `true` in a binary mask. `findPixelConnectedComponents` flood-fills 4-connected neighbors (up, down, left, right; no diagonals) with an explicit stack. Components smaller than `minComponentPixels = 10` (~1.5% of the 80×80 field) are dropped as noise. Each surviving component becomes an axis-aligned bounding box in normalized image coordinates `[0, 1]`, with `cellCount` equal to the number of samples in the component and `brightness` equal to their mean.

Axis-aligned boxes of adjacent bright blobs still produce a patchwork of overlays, so `mergeOverlappingRegions` unions boxes that sit within 15% of the window:

```swift
// Expansion was 0.05; raised to 0.15 on 8 January 2026
let expanded = combinedRect.insetBy(dx: -0.15, dy: -0.15)
if expanded.intersects(other.normalizedRect) {
    used.insert(other.id)
    combinedRect = combinedRect.union(other.normalizedRect)
}
```

If a pass both reduces the count and leaves more than one region, the function calls itself on the merged set, so adjacent unions can chain. After merge, `filterByMinimumSize` maps each normalized box through `rect(in: windowBounds)` and keeps regions whose width and height are at least `minimumRegionPixelSize = 100` and that are not larger than `maximumRegionPixelSize = 2000` in both dimensions. The max filter is an OR on the two axes (`width ≤ 2000 || height ≤ 2000`): a region that exceeds 2000 px in only one axis still passes. The intent in the comment is to fall back to per-window dimming when the “region” is the whole window.

## Cocoa y-flip

`BrightRegion.normalizedRect` is in image space: `y = 0` is the top row of the downsampled buffer. `NSWindow` frames are Cocoa: `y = 0` is the bottom of the screen. Placing an overlay on `normalizedRect.origin` without a flip puts a top-of-window bright pane at the bottom of the window. The conversion is:

```swift
func rect(in bounds: CGRect) -> CGRect {
    let flippedY = bounds.origin.y
        + (1.0 - normalizedRect.origin.y - normalizedRect.height) * bounds.height
    return CGRect(
        x: bounds.origin.x + normalizedRect.origin.x * bounds.width,
        y: flippedY,
        width: normalizedRect.width * bounds.width,
        height: normalizedRect.height * bounds.height
    )
}
```

That is `cocoaY = bounds.y + (1 - normalizedY - normalizedHeight) * bounds.height`. `DimmingCoordinator` stores the flipped rectangle on `RegionDimmingDecision.regionRect` and hands it to the overlay manager. The overlays themselves are click-through `NSWindow`s; this note does not describe z-order or WindowServer.

## Coordinator cycle

`performPerRegionAnalysis` runs on `analysisQueue` from a timer at `scanInterval` (stored default 2.0 s; comment range 0.5–5.0 s). Window list enumeration and overlay tracking run on a separate 0.5 s timer. For each visible window the coordinator checks `CachedAnalysis`: a hit is reused unless the entry is older than `cacheMaxAge = 10.0` s, the bounds hash changed, or the window became frontmost. A miss captures at most `maxCapturesPerCycle = 3` windows per cycle, each capture and detect wrapped in `autoreleasepool`, then writes the new regions into the cache. Dim level for a region is a function of how far the region mean sits above threshold, scaled from `globalDimLevel`, then capped by `activeDimLevel` (default 0.15) when the window is frontmost and `differentiateActiveInactive` is on, with a floor of `max(0.15, baseDimLevel * 0.5)`.

## Limits

This is a case study of a shipping overlay pipeline, not a compositor or gamma-LUT paper, not a user study, and not a timed benchmark. We do not claim that analysis finishes in milliseconds on millions of pixels, and we do not treat the engine’s comment target of under 50 ms for a full screen at 1/4 resolution as a measured result. The Rec. 709 coefficients `0.2126 / 0.7152 / 0.0722` are the engine’s constants; the live 80×80 mask uses BT.601 `0.299 / 0.587 / 0.114`. The 8×8 grid is the documented balanced `regionGridSize` and the reset value; the stored default is 6, and `detectBrightRegions` currently ignores `gridSize` in favor of `analysisResolution = 80`. Bounding boxes are rectangles around 4-connected blobs, not pixel-shaped overlays. Size cutoffs 100 px and 2000 px are heuristics. Cache entries can be up to ten seconds stale. Capture requires Screen Recording permission and is budgeted at three windows per cycle; capture-timeout history is out of scope here. We do not report eye-strain outcomes, competitor measurements, or product pricing.