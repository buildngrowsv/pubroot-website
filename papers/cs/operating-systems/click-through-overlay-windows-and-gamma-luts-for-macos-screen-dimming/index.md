---
title: "Click-through overlay windows and gamma LUTs for macOS screen dimming"
paper_id: "2026-179"
author: "buildngrowsv"
category: "cs/operating-systems"
date: "2026-08-25T06:29:02Z"
abstract: "SuperDimmer dims macOS windows without injecting into WindowServer or the display compositor. Per-window and per-region dimming is implemented as borderless, non-opaque NSWindow overlays that ignore mouse events and occupy the ordinary client window stack. The non-obvious part is hybrid z-order: overlays on the frontmost window use NSWindow.Level.floating; overlays on background windows use .normal plus order(.above, relativeTo: Int(windowID)) so a dim sheet covers only its target. Overlay lifecycle is equally constrained. OverlayManager never calls close() on live overlays. safeHideOverlay stops CALayer animations, sets dim to 0, flushes CATransaction, then orderOut; dropping dictionary references then lets ARC deallocate. deinit and close() must not touch dimView?.layer \u2014 doing so produced intermittent EXC_BAD_ACCESS in objc_release after AppKit had already torn down the view hierarchy. Color temperature is a separate display-pipeline path: 256-entry gamma LUTs via CGSetDisplayTransferByTable. CGSetDisplayTransferByFormula with min=0, gamma=1, and max set to an RGB multiplier produced no visible tint. SuperDimmer does not use DDC/CI. We contrast overlay, gamma LUT, and DDC/CI, and we state what this architecture does not claim."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator submits via pubroot CLI."
---

## Context

Software screen dimming on macOS has three well-known levers: a click-through overlay window, a display gamma lookup table, and DDC/CI backlight commands. SuperDimmer uses the first for dimming and the second for color temperature. It does not talk to WindowServer’s compositor, does not inject into another process, and does not send DDC/CI. This case study records the overlay configuration, the hybrid z-order that keeps a dim sheet on its target window, the overlay teardown sequence that stopped `EXC_BAD_ACCESS` in `objc_release`, and the gamma-table change that made color temperature actually tint.

`OverlayManager` holds three overlay maps: display-wide, per-region, and decay overlays keyed by `CGWindowID`. `DimmingCoordinator` picks full-screen or per-window/per-region mode and then creates, updates, or hides sheets. It is a client of the overlay manager, not a compositor hook.

![Exploded view of an NSWindow overlay, dim view, and CALayer stack used for macOS screen dimming](https://superdimmer.com/assets/promo/blog-hero-overlay-windows-crash-proof.png)

## Overlay windows, not compositor injection

Each dim sheet is a `DimOverlayWindow`, an `NSWindow` subclass created borderless with a layer-backed black `NSView`. The factory path is `DimOverlayWindow.create(frame:dimLevel:id:)`. Configuration that makes the window a dimmer rather than a UI surface lives in `configureForOverlay()`:

```swift
self.isOpaque = false
self.backgroundColor = .clear
self.hasShadow = false
self.ignoresMouseEvents = true
self.level = .normal
self.collectionBehavior = [
    .canJoinAllSpaces,
    .fullScreenAuxiliary,
    .stationary,
    .ignoresCycle
]
self.hidesOnDeactivate = false
```

`ignoresMouseEvents = true` is the click-through contract: clicks, drags, and scrolls reach the window underneath. `canBecomeKey` and `canBecomeMain` both return `false`, so the overlay never takes focus. Collection behavior keeps the sheet on every Space, beside fullscreen apps, out of Cmd-Tab / Cmd-`, and stationary while other windows move. Default level is `.normal`, not `.screenSaver`. A global `.floating` or `.screenSaver` overlay covers windows that should remain undimmed. Relative ordering is applied later, per target.

The dim itself is `NSColor.black.withAlphaComponent(clampedLevel)` on `dimView.layer`. `setDimLevel` animates that color inside an `autoreleasepool` and a `CATransaction` (ease-in-ease-out, default 0.35 s) so CA temporaries drain before the run-loop pool.

## Hybrid z-order

A dim overlay must sit immediately above its target and below every window in front of that target. Putting every overlay at `.floating` covers the wrong windows. Leaving every overlay at `.normal` without a relative order can leave it behind its target. The shipping rule, added after an earlier “all windows of the frontmost app get `.floating`” bug, is per **window**, not per app:

```swift
if decision.isFrontmostWindow {
    overlay.level = .floating
    overlay.orderFront(nil)
} else {
    overlay.level = .normal
    overlay.orderAboveWindow(decision.windowID)
}
```

`orderAboveWindow` is a one-line WindowServer client call:

```swift
func orderAboveWindow(_ windowID: CGWindowID) {
    guard !isClosing else { return }
    self.order(.above, relativeTo: Int(windowID))
}
```

`Int(windowID)` is the AppKit window number. On focus change, `updateOverlayLevelsForFrontmostApp()` asks `WindowTrackerService` for the frontmost `CGWindowID`, promotes matching region overlays to `.floating` + `orderFront(nil)`, and demotes the rest to `.normal` + `orderAboveWindow`, in one pass under `overlayLock`. Decay overlays stay at `.normal` and are re-ordered above their `CGWindowID` when visible.

## Overlay lifecycle: never close()

Calling `NSWindow.close()` on a live overlay was the first crash class. `close()` is not idempotent, AppKit autoreleases internal objects, and Core Animation can still hold the layer. `OverlayManager.safeHideOverlay` is the only teardown path for live sheets:

```swift
private func safeHideOverlay(_ overlay: DimOverlayWindow) {
    autoreleasepool {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        overlay.contentView?.layer?.removeAllAnimations()
        overlay.setDimLevel(0.0, animated: false)
        CATransaction.commit()
        CATransaction.flush()
    }
    overlay.orderOut(nil)
}
```

Order matters: stop CA, dim to zero, flush, then `orderOut`. The caller then removes the overlay from `windowOverlays`, `displayOverlays`, `regionOverlays`, or `decayOverlays`. With no remaining strong refs, ARC deallocates. There is no hidden pool. `removeAllOverlays()` and `removeAllDecayOverlays()` both go through this path. `removeAllDecayOverlays` copies values out of the dictionary, unlocks, then hides — `CATransaction.flush()` can pump the run loop, so the recursive lock is not held across the flush.

`DimOverlayWindow.close()` remains as a guarded override. It sets `isClosing`, flushes CA, and calls `super.close()` without touching `dimView`. `setDimLevel`, `updatePosition`, and `orderAboveWindow` no-op when `isClosing` is true. Production hide paths should not call it.

`overlayLock` is an `NSRecursiveLock` because overlay methods nest. Decay overlays get a 5 s minimum age before orphan cleanup: `applyDecayDimming` and `cleanupOrphanedOverlays` take different window snapshots, and AutoHide between them produced create-then-hide churn. `applyDecayDimming` is also throttled to once per 500 ms.

On Space change, `OverlayManager` observes `NSWorkspace.activeSpaceDidChangeNotification`, `orderOut`s every overlay type, waits 0.5 s for the Mission Control animation, then `orderFront`s if the manager is still active. That delay is empirical. Restoring mid-animation puts dim sheets in the slide.

## deinit must not touch the layer

After we stopped calling `close()`, a second crash remained: `EXC_BAD_ACCESS (code=1)` in `libobjc.A.dylib` `objc_release` on the main thread. Console order was:

```
DimOverlayWindow deallocated by ARC: window-298618
App unhidden (PID 76826) - reset all window timers
```

The crash followed immediately. `deinit` still did `dimView?.layer.removeAllAnimations()`. By the time ARC ran `deinit`, AppKit could already have deallocated `contentView` and subviews. `dimView` then pointed at freed memory. The access was intermittent because deallocation order is not guaranteed — the same path survived some hide/unhide cycles and died on others.

The fix is to leave the view hierarchy alone in `deinit`. Animations are already stopped in `safeHideOverlay` before dictionary refs drop. `deinit` only logs. The same rule applies inside `close()`: flush, then `super.close()`, never `dimView?.layer`.

That is the whole overlay contract: hide and drain CA while the window is still a valid AppKit object; never close as the steady-state path; never touch layers from `deinit`.

## Gamma LUT versus formula versus DDC/CI

Color temperature is not an overlay. It writes the display transfer table. The first implementation called `CGSetDisplayTransferByFormula` with min 0.0, gamma 1.0, and max set to the Kelvin-derived RGB multiplier (`output = min + (max − min) * pow(input, gamma)`). Mathematically that scales the channel; on the hardware we tested it produced no visible tint. The gamma-formula API is for gamma correction, not a reliable tint.

The shipping path builds 256-entry tables and calls `CGSetDisplayTransferByTable`:

```swift
let gamma = 2.2
for i in 0..<tableSize {
    let normalized = Double(i) / Double(tableSize - 1)
    let gammaAdjusted = pow(normalized, 1.0 / gamma)
    redTable[i] = Float(gammaAdjusted * rgb.red)
    greenTable[i] = Float(gammaAdjusted * rgb.green)
    blueTable[i] = Float(gammaAdjusted * rgb.blue)
}
let result = CGSetDisplayTransferByTable(
    displayID, UInt32(tableSize), &redTable, &greenTable, &blueTable)
```

RGB multipliers come from Tanner Helland’s Kelvin-to-RGB conversion (CIE-based; clamped here to 1900–6500 K). At 3000 K the blue channel is scaled by about 0.4. Disable restores with `CGDisplayRestoreColorSyncSettings()`. `ColorTemperatureManager.swift`’s file header still mentions `CGSetDisplayTransferByFormula`; the applied function is the table path.

The three mechanisms are not interchangeable:

| Mechanism | What it changes | Granularity | SuperDimmer |
| --- | --- | --- | --- |
| Overlay `NSWindow` | Extra black (or region) sheet in the window list | Per window / per region / per display | Yes — dimming |
| Gamma LUT (`CGSetDisplayTransferByTable`) | Display transfer function | Entire display | Yes — color temperature |
| DDC/CI | Monitor backlight over I²C | Entire panel, if the link works | No |

Overlays can dim one window or region and leave the rest of the screen alone; they cannot lower a panel’s backlight. Gamma LUTs tint or darken the whole display and are the closest SuperDimmer gets to a display-pipeline control; they cannot isolate one window. DDC/CI is the real backlight and fails on many built-in panels. SuperDimmer does not implement it.

## Limits

We do not claim compositor injection, WindowServer injection, or a private CGS filter. Overlays are ordinary `NSWindow` objects with relative z-order. We do not claim DDC/CI, hardware backlight control, or equivalence to f.lux / Night Shift beyond the shared use of display transfer tables. The 0.5 s Space delay and the 5 s decay-overlay grace period are empirical, not OS contracts. `CGSetDisplayTransferByTable` is display-global; it is not per-window. Crash evidence cited here is the January 2026 `objc_release` use-after-free on overlay `deinit`, not a formal reliability study. Window-list capture, Rec. 709 region merge, and Space UUID tracking are out of scope.