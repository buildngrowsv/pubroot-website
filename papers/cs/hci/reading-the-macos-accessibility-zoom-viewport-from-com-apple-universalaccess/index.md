---
title: "Reading the macOS Accessibility Zoom viewport from com.apple.universalaccess"
paper_id: "2026-201"
author: "buildngrowsv"
category: "cs/hci"
date: "2026-08-25T06:53:56Z"
abstract: "macOS Accessibility Zoom has no documented public geometry API, so applications still place windows and notifications in the region the user cannot see. We show that zoom state is readable from the com.apple.universalaccess defaults suite with no extra TCC grant. Three keys are enough for a working detector. closeViewZoomedIn is the toggle, closeViewZoomFactor is the magnification, and closeViewZoomMode is 0 fullscreen, 1 picture-in-picture, or 2 split. The visible pixel rectangle in fullscreen zoom is the display frame divided by the factor, centered on NSEvent.mouseLocation, and clamped to that display. Control of the viewport is a different problem. Option-Command-Arrow pans only if the user enabled zoom keyboard shortcuts; CGWarpMouseCursorPosition only works when zoom follows the cursor; SkyLight symbols were not recovered as a callable API. This is a detection-versus-control case study for overlay UIs and computer-use agents, not a private-API recipe."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Apps are blind to Accessibility Zoom

macOS Accessibility Zoom magnifies a subset of the display so a low-vision user can read it. Applications still layout against `NSScreen.frame`. At 20× fullscreen zoom that user sees 1/400 of the frame: each axis shrinks by the factor, so visible area shrinks by its square. New windows, banners, and agent click targets can land entirely outside the magnified region. Apple does not document a public Zoom geometry API. We needed the visible rectangle anyway, for overlay placement and for computer-use agents that should not act on pixels the user cannot see.

This note records what we could actually read from `com.apple.universalaccess`, how we turn those values into a Cocoa rectangle, and where control of the viewport stops. It is not an Accessibility-tree paper (that is 2026-115). The source is the `AccessibilityZoomDetection/` tree in mac-vibes: `CASE_STUDY.md`, `AccessibilityZoomDetector.swift`, `ZoomWindowCalculator.swift`, plus `MultiDisplayZoomDetector.swift` and the small pan script.

## Reading state without a Zoom API

The defaults suite `com.apple.universalaccess` is readable from an ordinary AppKit process. `AccessibilityZoomDetector.getCurrentZoomStateViaDefaults()` does not call `AXIsProcessTrusted`, does not prompt, and does not request Screen Recording or Input Monitoring. Three keys are enough for a working detector:

```swift
let defaults = UserDefaults(suiteName: "com.apple.universalaccess")
let isZoomed = defaults?.bool(forKey: "closeViewZoomedIn")
let zoomFactor = defaults?.float(forKey: "closeViewZoomFactor")
let zoomMode = defaults?.integer(forKey: "closeViewZoomMode")
```

`closeViewZoomedIn` is the toggle. `closeViewZoomFactor` is the magnification (`1.0` means no zoom, `2.0` means 2×). `closeViewZoomMode` is an integer we mapped as 0 fullscreen, 1 picture-in-picture, and 2 split, matching `AccessibilityZoomDetector.ZoomMode`. Adjacent keys we also read, but do not need for the rectangle, include `closeViewZoomDisplayID`, `closeViewZoomIndividualDisplays`, `closeViewScrollWheelToggle`, `closeViewTrackpadGestureZoomEnabled`, and `closeViewSmoothImages`.

If the process is already trusted, `getCurrentZoomState()` prefers the system-wide `AXUIElement` attributes `AXCloseViewZoomedIn`, `AXCloseViewZoomFactor`, `AXCloseViewZoomMode`, `AXCloseViewZoomDisplayID`, plus `AXCloseViewWindowPosition` and `AXCloseViewWindowSize` as `AXValue` `CGPoint`/`CGSize`. The AX path is the only place we recover picture-in-picture window chrome. The defaults path leaves those fields nil; the detector comments that they are stored as binary plists we did not decode. Permission checks use `AXIsProcessTrustedWithOptions` with `kAXTrustedCheckOptionPrompt` false so a status UI does not spawn a dialog.

For live updates we subscribe to `DistributedNotificationCenter` names `com.apple.accessibility.cache.zoom` and `com.apple.accessibility.api`. We treat those names as observed in this tree, not as a documented contract.

## Visible rectangle from mouse and zoom factor

`ZoomWindowCalculator.getCurrentZoomWindow()` returns nil unless zoom is active. It takes `NSEvent.mouseLocation` as the zoom center and picks the `NSScreen` that contains the cursor via `NSMouseInRect`, falling back to `NSScreen.main`. Fullscreen zoom is then a division and a clamp, in Cocoa coordinates (origin at the bottom-left of the primary display):

```swift
let visibleWidth = displayRect.width / CGFloat(zoomFactor)
let visibleHeight = displayRect.height / CGFloat(zoomFactor)
var visibleX = centerPoint.x - (visibleWidth / 2.0)
var visibleY = centerPoint.y - (visibleHeight / 2.0)
if visibleX < displayRect.minX { visibleX = displayRect.minX }
if visibleY < displayRect.minY { visibleY = displayRect.minY }
if visibleX + visibleWidth > displayRect.maxX {
    visibleX = displayRect.maxX - visibleWidth
}
if visibleY + visibleHeight > displayRect.maxY {
    visibleY = displayRect.maxY - visibleHeight
}
```

The clamp is against `displayRect.minX` / `minY`, not against `(0, 0)`. A secondary display’s frame origin is not the global Cocoa origin; clamping to zero would be wrong on that screen. `move-zoom-applescript.swift` still uses `NSScreen.main` and clamps to zero, which is a real limitation of that helper, not of the calculator.

Without the clamp, the computed origin would hang off-screen while the magnified view is actually pinned to the display. Visible area as a fraction of the display is `1 / zoomFactor²` (25% at 2×, 1% at 10×, 0.25% at 20×). Helpers on the same type implement the HCI tests we wanted: `isPointVisible` (true for every point when zoom is off), `getVisibleScreenPercentage`, and `screenPointToZoomWindowPoint` (nil if the point is outside the magnified region). Standalone scripts `test-zoom-window-position.swift` and `monitor-zoom-position.swift` print the same rectangle as JSON or a live console overlay.

## Picture-in-picture, split, and extra displays

Picture-in-picture is a smaller magnifier, not a full-screen crop. When AX gives us a PiP origin and size, the calculator treats the source region as `pipWindowSize / zoomFactor`, still centered on the mouse and still clamped to the display. If those AX values are missing it falls back to the fullscreen formula. Split-screen zoom is also routed through the fullscreen formula; that is an approximation, not a recovered split geometry.

On several displays, `MultiDisplayZoomDetector` reads `closeViewZoomIndividualDisplays`. When that flag is on, only the display that currently contains the mouse is treated as zoomed; other displays are reported idle. When the flag is off, the same `closeViewZoomedIn` / `closeViewZoomFactor` pair is applied to every screen. `closeViewZoomDisplayID` is stored, but the detector comments that the mapping to `CGDirectDisplayID` is not assumed to be one-to-one, so we key off cursor containment rather than that integer.

## Detection is not control

Reading the rectangle does not move it. The case study records three control attempts. Two of them work only under a user setting; the third is incomplete.

Keyboard pan. Option-Command-Arrow pans the zoom window, but only if the user enabled System Settings → Accessibility → Zoom → Advanced → Controls → Use keyboard shortcuts to adjust zoom window. `move-zoom-applescript.swift` computes a delta from the current viewport center to the focused window center, then emits System Events `key code` 123–126 (left, right, down, up) with option and command held:

```
tell application "System Events"
    key code 126 using {option down, command down}
end tell
```

That path needs Automation permission to talk to System Events. The script prints a reminder if the viewport does not move. It also mixes AX window position (top-left, Core Graphics) with `NSEvent.mouseLocation` (Cocoa). That is a coordinate footgun on the pan helper; the calculator stays in Cocoa.

Cursor warp. `CGWarpMouseCursorPosition` recenters fullscreen zoom only when zoom is set to follow the cursor continuously. If the user chose a different follow mode, warping the cursor does not pan the viewport.

Private WindowServer entry points. The case study names `CGSZoomPoint` and `SLSSetZoomParameters` in SkyLight as symbols that exist. We did not recover calling conventions, and we do not publish guessed signatures as a working API. That section is incomplete on purpose.

What we actually use the rectangle for is placement, not pan: put a new window or a notification inside `visibleScreenRect`; treat off-viewport pixels as not currently visible to the user; capture the magnified region rather than the full unzoomed frame if the screenshot is meant to match what is on screen.

## Limits

We do not claim a public Apple Zoom API, a stable ABI for `com.apple.universalaccess`, or that these keys exist with the same names on every macOS release. We did not decode the binary-plist PiP chrome from defaults. Split-screen geometry is an admitted fullscreen stand-in. The AX attribute names are what the detector requests; we do not claim they are documented. Distributed notification names are observed in this tree, not specified. Keyboard pan is preference-gated and goes through System Events. Cursor warp is follow-mode-gated. SkyLight is not offered as a recipe. We did not measure how often shipping apps place windows or banners outside the magnified region. This is a detection-versus-control note for overlay UIs and agents, not a substitute for honoring the user’s zoom settings in AppKit itself.