---
title: "Spreading macOS windows onto concentric rectangular orbits with greedy pairing and 2-opt"
paper_id: "2026-205"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-08-25T06:59:02Z"
abstract: "SuperDimmer's Spread Windows Evenly action is a one-shot deterministic layout of the windows on the primary macOS display. It is not a tiling window manager and it does not call a language model. Visible windows are assigned to concentric rectangular orbits inset 4 percent from NSScreen.visibleFrame. The outer orbit holds up to 12 perimeter slots (four corners plus two points on each edge when the count is 12). Inner orbits, when N requires them, are the same rectangle scaled to 0.6\u00d7 and 0.3\u00d7 about the center. For N \u2265 2 one slot is reserved at the exact center. Assignment is global smallest-pair greedy over all (window, slot) Euclidean distances, then a 2-opt local search of at most ten iterations with a 0.5 px improvement epsilon. That pair replaced an earlier uniform grid that left corners empty and a rank-based perimeter walk that rotated windows across the screen. Moves are applied through Accessibility: kAXPositionAttribute and kAXSizeAttribute, with the private but widely used _AXUIElementGetWindow mapping from CGWindowID to AXUIElement so two windows that share a frame mid-move are not confused. Recording and call apps are excluded by bundle ID and owner name. An idle drift daemon described in a companion spec is not implemented."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Context

A crowded macOS desktop is a geometric assignment problem, not a taste problem. SuperDimmer's `EquidistantSpreadService` (shipped with v1.0.8 on 2026-04-20) redistributes every movable window on the primary display onto a fixed set of orbit slots in one user-triggered action, kept out of the dimming pipeline so a bulk Accessibility write cannot steal that frame budget. The engine runs in Quartz coordinates (top-left origin, matching `CGWindowList` and `AXPosition`). `NSScreen.visibleFrame` is Cocoa (bottom-left origin) and is converted once at the boundary.

The companion file `EQUIDISTANT-DRIFT-SPEC.md` still describes an order-preserving rectangular *grid* and an idle launchd daemon. That grid is the v0.1–v0.3 design. The idle daemon is not built. This case study is the shipping v0.8 path in `EquidistantSpreadService.swift` and the matching algorithm in `tools/equidistant-drift/equidistant_spread.swift`.

![Overlapping macOS windows on a single desktop, the layout problem the spread action addresses](https://superdimmer.com/assets/promo/blog-hero-window-management-mac.png)

## Orbits, not a grid

Eight live-use iterations produced the geometry. v0.1–v0.3 placed window centers on a uniform grid whose cell count followed screen aspect (`cols = round(sqrt(N * width/height))`). The leftmost and rightmost columns sat inward of the screen corners, so the four corners stayed empty. v0.4 filled corners with size-proportional rows and an edge-anchor, but smaller windows then occupied disproportionate space. v0.5 switched to concentric rectangular orbits with rank-based perimeter parameter `t`; corners filled, but a cluster in one quadrant was walked around the rectangle and windows rotated across the screen. v0.6 reserved a center slot. v0.7 dropped per-orbit ranking. v0.8 added 2-opt.

Spread bounds are `visibleFrame` inset by `marginPercent` (default 4) on each side. Orbit construction always reserves one degenerate center orbit when `N ≥ 2`:

```swift
if N == 1 { return [center] }
let remaining = N - 1
if remaining <= 12 {
    return [OrbitDef(rect: bounds, capacity: remaining), center]
}
let innerRect = scaleRectAroundCenter(bounds, scale: 0.6)
if remaining <= 24 {
    return [
        OrbitDef(rect: bounds,    capacity: 12),
        OrbitDef(rect: innerRect, capacity: remaining - 12),
        center
    ]
}
```

Above 24 remaining windows a third orbit appears at 0.3×. `computeOrbitPositions` maps capacity `k` to `k` points with `t = i/k` on the rectangle perimeter, `t = 0` at top-left, clockwise. For `k = 12` that is four corners plus two interior points on each edge. Capacities 4 and 8 also land on all four corners because `t = i/k` hits 0, 0.25, 0.5, and 0.75. Other capacities do not; a five-slot outer orbit (`N = 6`) hits `t = 0, 0.2, 0.4, 0.6, 0.8` and only the top-left corner. When `N ≥ 13` the outer capacity is fixed at 12, so the outer orbit includes the corners by construction. Each window keeps its current size. The target origin is the slot point minus half the window size, then `clampToVisibleFrame` so an orbit point plus a large window cannot leave the display. Overlap is accepted when a window is larger than the local spacing; the service does not shrink.

Parameters were tuned on a 6720×3780 display and checked on laptop-sized frames down to 1440×900. That is a comment in `EquidistantSpreadConfig`, not an Instruments table. Enumeration uses `CGWindowListCopyWindowInfo` with `.optionOnScreenOnly` and `.excludeDesktopElements`. Frames smaller than 100×80 are dropped as overlays and popovers.

## Global greedy, then 2-opt

v0.5 assigned windows to an orbit by Chebyshev radius from center, then paired them to perimeter slots by angle rank. A window in the lower-left could rank into the outer 12, find every nearby outer slot taken, and land on the far side of the screen. v0.7 flattened the slot list. Every (window, position) pair across *all* orbits is scored by Euclidean distance from the window's current center, sorted ascending, and claimed greedily: the smallest unused pair takes its window and its slot.

Greedy has a known worst case when two windows want the same slot. The closer window wins; the loser takes its next free slot, which may be far even though a slightly farther window occupies a nearby inner-orbit point that a swap would free. The CLI harness records one live instance: Finder Downloads at `(3359, 1905)` and a Chrome window at `(3360, 1905)` both wanted center. Chrome won. Finder's next free slot was the outer left edge at `(417, 1330)`, a 2997 px move, while an innermost-orbit point at `(3050, 2423)` was 603 px away and already claimed. v0.8 runs 2-opt after the greedy claim. `maxIters = 10`, `epsilon = 0.5` px:

```swift
for _ in 0..<maxIters {
    var improved = false
    for i in 0..<assigned.count {
        let w1 = assigned[i]; guard let p1 = slotMap[w1] else { continue }
        for j in (i+1)..<assigned.count {
            let w2 = assigned[j]; guard let p2 = slotMap[w2] else { continue }
            let cur  = dist(w1, p1) + dist(w2, p2)
            let swap = dist(w1, p2) + dist(w2, p1)
            if swap + epsilon < cur {
                slotMap[w1] = p2; slotMap[w2] = p1; improved = true
            }
        }
    }
    if !improved { break }
}
```

A swap is accepted only when it strictly reduces total Euclidean cost. A window already at distance 0 from center cannot be swapped off center, because that swap would raise cost. If every window already sits on a slot, every self-pair has distance 0, those pairs sort first, greedy claims them, and 2-opt finds no improving swap. That is a property of the assignment, not a timed no-op measurement. Pair construction is `N × P` with `P = N` slots; 2-opt inspects `C(N,2)` pairs per pass. A harness comment puts `N ≤ 40` in milliseconds; we have no benchmark table. Four windows near distinct slots stay local: center claims center, a top-right window claims that corner, a bottom-left window claims that corner, and a cluster-mate takes an adjacent edge or inner-orbit point rather than the opposite corner unless a swap is cheaper. The slot set is the geometry; greedy plus 2-opt is only the matching.

## Accessibility writes and `_AXUIElementGetWindow`

Public Accessibility gives `AXUIElement` objects per process. `CGWindowList` gives `CGWindowID`s. There is no public join. Frame-matching the two lists fails when two windows of the same app occupy the same rectangle, which happens in the middle of a bulk move. SuperDimmer uses the private function every mainstream Mac window manager (Rectangle, yabai, AeroSpace, Hammerspoon) uses for the same join. It is declared in `AutoMinimizeManager.swift` and called from the spread service:

```swift
@_silgen_name("_AXUIElementGetWindow")
func _AXUIElementGetWindow(_ element: AXUIElement,
    _ outWindow: UnsafeMutablePointer<CGWindowID>) -> AXError
```

Resolution is `AXUIElementCreateApplication(pid)` → `kAXWindowsAttribute` → ask each AX window for its `CGWindowID` and compare. A miss skips that window. The shipping spread path has no frame-distance fallback (`apply_layout.swift` in the CLI actuator does). This is a compatibility risk if the symbol moves, not a vulnerability, and Apple has not provided a public equivalent.

Application is snap, not animation. For each assignment the service writes `kAXPositionAttribute`, then `kAXSizeAttribute`, then position again. Electron apps and Terminal's character grid re-anchor during a size change; the second position write is insurance. After each window it sleeps `settleMs` (80 ms), reads the AX frame back, and retries once if any edge of the rect drifted more than `driftThresholdPx` (6 px). Header comments put wall time at about 1–5 seconds as `N × settle`; that is a comment, not a measurement. Multi-display spread is not implemented: `NSScreen.screens.first` is the only target.

The CLI harness can emit a `LayoutPlan` JSON document for `apply_layout.swift`. The menu-bar action does not; it applies AX in-process.

## Recording-safe exclusions

A window is free for assignment only if it is layer 0, its bundle ID is not in the hard exclude set, its owner name is not in the hard exclude set, and, when the optional `anchorEdges` setting is on, it is not already flush to a screen edge or corner (16 px, corners at 2× that threshold). Floating windows (Magnet panels, Stickies, layer > 0) are left alone. System chrome (`com.apple.dock`, Control Center, Notification Center, `SystemUIServer`, `WindowManager`) is excluded, as is SuperDimmer itself. Recording and call apps are excluded by bundle ID (`us.zoom.xos`, `com.google.meet`, `com.microsoft.teams2`) or owner name (`OBS Studio`, `Loom`, `Screen Studio`, `QuickTime Player`, `FaceTime`, `zoom.us`, `CleanShot X`). The shipping service does not read window titles or tab URLs; it only needs geometry.

The CLI config `tools/equidistant-drift/config/exclusions.json` additionally matches title substrings (`Recording`, `Sharing screen`, `On call`) and URL substrings (`meet.google.com`, `zoom.us/j/`). Sample plan `tools/equidistant-drift/samples/plan-anchor-edges-demo.json` (2026-04-20) leaves eight windows alone — three edge-anchored, OBS Studio by name, a title containing `recording`, Notification Center by bundle — and emits 29 moves. That file is a harness artifact with leftover “cell” reason strings, not a screenshot of the shipping orbit geometry.

## Limits

This is not the idle drift daemon. `idle_drift_daemon.swift` is listed as unbuilt in the spec roadmap. There is no 10-minute idle trigger, no recency exclusion of recently fronted windows, no `easeInOutCubic` animation in the app, and no cancel-on-input. The menu action is a snap AX write. We do not implement the Hungarian algorithm; 2-opt is a bounded local search on a greedy matching. We do not claim corners are filled for every `N` — only that capacities 4, 8, and 12, and therefore every outer orbit with `N ≥ 13`, place slots on all four corners. Idempotence is a consequence of zero-distance self-pairs, not a measured no-op. Overlap of large windows is accepted. Spread is primary-display only. `_AXUIElementGetWindow` is a known window-manager technique, not a vulnerability disclosure. Title and URL keyword filters exist in the CLI harness, not in `EquidistantSpreadService`. Overlay dimming, zone luminance, capture timeouts, and Space UUID reorder are out of scope.