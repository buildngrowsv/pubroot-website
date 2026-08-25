---
title: "Moving macOS windows across Spaces with SIP on using CGEvent grab and System Events Control-Arrow"
paper_id: "2026-192"
author: "buildngrowsv"
category: "cs/operating-systems"
date: "2026-08-25T06:44:32Z"
abstract: "Apple does not expose a public API we could find for placing an already-open window onto another Space. Control-Arrow alone changes the view, not the window. Yabai can move windows but wants System Integrity Protection off and a Dock scripting addition. We keep SIP on and replay the human grab-then-shortcut gesture. A Swift CLI posts CGEvent mouse-down on the title bar, a real multi-step drag so macOS registers a drag, then System Events key code 124 using control down while the button is still held, then mouse-up after the Space animation. CGEvent keyboard events during the hold did not compose into the system move-window-to-space gesture. Persistent app-to-desktop assignment is a separate plist path. com.apple.spaces app-bindings maps a bundle id to AllSpaces or a Space UUID. Visual desktop number is array order in SpacesDisplayConfiguration, not ManagedSpaceID. We tested this on macOS 26.1 as recorded in the lab notes. We do not claim a stable private API or a legal absence of any Spaces SPI."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## The gap

macOS Spaces are virtual desktops. A user can grab a window title bar, start a drag, and press Control-Right Arrow; the window rides onto the next Space. There is no public API we could find that does the same thing for a script. Accessibility APIs we used report window position and size, not the Space a window occupies, and they do not offer a move-to-Space action. Published Accessibility and browser-control papers (2026-026, 2026-034, 2026-115) do not cover Spaces. This case study is the SIP-on result from `2-Desktop-Spaces-Tools/` in mac-vibes at commit `8493d03270fac7071fbc233ecb853c8ea1f7cf54`.

Two jobs got mixed together in early attempts. Persistent assignment is where an app should appear when it launches. Runtime movement is sending an already-open window to another desktop. They are stored and actuated differently. Keyboard-only Control-Arrow does neither of the window jobs; it only changes the view.

## What failed under a SIP-on constraint

System Events `key code 124 using control down` switches the view to the next Space. The focused window stays behind. Control-Shift-Arrow was equally a view change on the machine we used. That matches Mission Control shortcuts; it is not a window-move API.

Yabai's `yabai -m window --space <n>` is the well-known window-manager path. Full space control wants System Integrity Protection off and a Dock scripting addition. Installed yabai 7.1.5 was not a working dependency (`yabai-msg: failed to connect to socket`). We did not disable SIP to make it work.

BetterTouchTool exposes Move Window to Desktop as a named trigger. That is a commercial, GUI-configured action, not a self-contained CLI. URL-scheme calls in this repo assumed triggers that were not present.

A Swift-only CGEvent sequence that mouse-downed the title bar and then posted Control-Arrow as `CGEvent(keyboardEventSource:)` during the hold sent events that did not compose into the system move-this-window gesture. Events that were too fast failed for the same reason a click without motion failed: the window manager did not treat the pointer as in a drag.

## Grab, drag, then Control-Arrow while held

`WindowMover.swift` replays the human gesture with mixed input sources. Mouse is HID via `CGEvent` posted at `.cghidEventTap`. The Space shortcut is AppleScript through System Events, issued while the left button is still down.

Frontmost window bounds come from System Events (name, position, size), joined with a `§§§` delimiter because titles often contain `|`. The click target is the title-bar center, `(x + width/2, y + 15)`.

```swift
func mouseDown(at point: CGPoint) {
    guard let event = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left) else {
        print("❌ Failed to create mouse down event")
        return
    }
    event.post(tap: .cghidEventTap)
}
```

A down event is not a drag. The working sequence then posts `leftMouseDragged` along a short path so macOS registers a drag:

```swift
    let dragDistance: CGFloat = 80
    let dragSteps = 25
    for i in 1...dragSteps {
        let progress = CGFloat(i) / CGFloat(dragSteps)
        let offsetX = dragDistance * progress
        let offsetY = CGFloat(i) * 0.5
        let dragPoint = CGPoint(x: titleBarPoint.x + offsetX, y: titleBarPoint.y + offsetY)
        mouseDrag(to: dragPoint)
        usleep(Config.dragStepDelay)
    }
```

With the button still held, the CLI runs `tell application "System Events" to key code 124 using control down`. Key code 123 is previous. Numbered desktops use top-row codes 18, 19, 20, 21, 23, 22, 26, 28, 25 for 1 through 9, and they require Switch to Desktop N under Keyboard Shortcuts, Mission Control. After the Space animation, `leftMouseUp` is posted at the drag end, not at the original title-bar point.

Optional `--app` activation is done twice with a 1 s then 0.5 s pause so Terminal does not steal focus mid-gesture. `preview` only moves the cursor to verify the title-bar hit. Without Accessibility granted to the process that posts events, System Events returns `osascript is not allowed to send keystrokes. (1002)`.

## Why the hybrid

CGEvent is precise for cursor position and button state. It was not sufficient, in this test, to inject the Control-Arrow half of a chord that macOS only honors as a window-move when a drag is already recognized. System Events, talking to the same accessibility stack the user enabled, did compose. We are not claiming a documented HID combining rule. We are claiming that on the tested OS, mouse HID plus System Events keyboard, in that order, with a real drag and a held button, moved the window.

Human-like delays are part of recognition, not cosmetics. `Config.longPause` is 0.8 s after positioning the cursor. `transitionWait` is 1.5 s so mouse-up does not land during the Space animation.

## Two timing profiles

`WindowMoverFast.swift` is the same gesture with smaller constants and a batch mode. Lab notes report about 2.5 s per move for the slow CLI and about 1.3 s for Fast (about 48 percent). Three batch runs of next, prev, 2, 6 finished in 5.30 s, 5.36 s, and 5.45 s.

| Stage | WindowMover | WindowMoverFast |
| --- | --- | --- |
| Cursor settle on title bar | 0.8 s | 40 ms |
| Drag | 25 steps, 80 px, 30 ms/step | 10 steps, 50 px, 10 ms/step |
| Space animation wait | 1.5 s | 400 ms |
| Between batch moves | n/a | 200 ms |

Batch mode activates the app once. After a successful move the window is already frontmost on the new Space. Re-activating the app between hops can jump focus to another window of the same app on a different Space and break the chain.

## Persistent assignment in com.apple.spaces.plist

Runtime HID does not persist. Default desktop membership lives in `~/Library/Preferences/com.apple.spaces.plist`. `desktop-assignment-manager.sh` reads the `app-bindings` dictionary with `defaults read com.apple.spaces "app-bindings"`. Values we observed are `AllSpaces` (every desktop), a Space UUID (one desktop), or absence (stay where opened).

Visual desktop number is the index of that UUID in the `Spaces` array inside `SpacesDisplayConfiguration`, starting at one. `ManagedSpaceID` is an internal identifier and is not sequential with Mission Control order. An early parse walked every `uuid` in the plist, including Current Space before the array, and numbered desktops off by one. The script restricts the parse to the array:

```
defaults read com.apple.spaces "SpacesDisplayConfiguration" | sed -n '/Spaces = /,/);/p'
```

Writes use PlistBuddy `Set` or `Add` on `:"app-bindings":"<bundle-id>"`, then `killall Dock`. On this machine, Calculator went from `AllSpaces` to a specific UUID and back. The Dock restart is disruptive. The app may need to be quit and reopened. Changing `app-bindings` does not move an already-open window; that is the HID job. `Space Properties` window-id lists looked cached and were not a reliable runtime location API. We do not publish machine-specific UUIDs as if they were universal.

## Limits

We do not claim Apple has no Spaces SPI of any kind, only that we found no public API that moved a window and that these preference keys and this HID chord worked on the lab Mac running macOS 26.1 as recorded in December 2025 notes (a companion file also labels Sequoia 15.1). We do not claim the gesture is an OS contract, that it survives future Mission Control changes, or that it works in Stage Manager, fullscreen spaces, or every multi-display arrangement.

We do not disable SIP and we do not document Dock injection or yabai's SIP-off path as a recipe. We do not claim CGEvent keyboard injection can never work, only that it did not compose here during a held drag. Fast timings are empirical; 400 ms can lose the animation on a slow machine. Numbered-desktop moves need user-enabled shortcuts. The plist path is undocumented, requires a Dock restart, and sets launch assignment rather than live placement. We did not get a trustworthy which-Space-is-this-window-on query without private APIs or a SIP-off window manager. This is not a window-manager replacement and not a restatement of Accessibility-tree computer use.