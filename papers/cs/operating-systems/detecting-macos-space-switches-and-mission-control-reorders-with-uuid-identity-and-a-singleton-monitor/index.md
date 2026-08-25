---
title: "Detecting macOS Space switches and Mission Control reorders with UUID identity and a singleton monitor"
paper_id: "2026-191"
author: "buildngrowsv"
category: "cs/operating-systems"
date: "2026-08-25T06:43:33Z"
abstract: "macOS posts NSWorkspace.activeSpaceDidChangeNotification on a Space switch but does not identify which Space became active, and a Mission Control drag that reorders Spaces posts no notification at all. SuperDimmer's SpaceChangeMonitor combines that workspace notification (debounced 0.3 s) with a 0.5 s poll of ~/Library/Preferences/com.apple.spaces.plist. Switch detection compares the 1-based plist-array index of the current Space. Reorder detection is the predicate same UUID set, different UUID sequence. Per-Space visit history migrated from integer positions to UUID strings so state follows the Space rather than the Mission Control slot. Three features originally each constructed a SpaceChangeMonitor, tripling observers and timers; logs showed 6-7 copies of each switch and a 55.5 percent CPU sample. The shipping type is a singleton with an observer list. CGSGetActiveSpace is used only as optional ManagedSpaceID corroboration, not as a vulnerability."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Context

macOS Spaces (virtual desktops) have no public current-Space-ID API that is sufficient for an app that must freeze window-decay timers, pause inactivity clocks, or keep per-Space state across Mission Control rearrangements. `NSWorkspace.activeSpaceDidChangeNotification` fires on a switch and carries no payload. A Mission Control drag that reorders Spaces fires no notification at all. SuperDimmer's `SpaceChangeMonitor` therefore combines three pieces: the workspace notification for switches, a 500 ms poll of `~/Library/Preferences/com.apple.spaces.plist` for identity and order, and a singleton observer list so three features do not each subscribe to the same notification. Per-Space state is keyed by UUID, not by the Mission Control position "Space 3".

## Switch: a notification without a Space ID

`SpaceChangeMonitor.startMonitoringInternal` registers for `NSWorkspace.activeSpaceDidChangeNotification` and starts a repeating 0.5 s `Timer` on the main `RunLoop` (`.common`). The selector `handleWorkspaceSpaceChange` does not read the notification object. It invalidates a debounce timer and reschedules `checkForSpaceChange` after `debounceInterval` (0.3 s), because a Space transition can emit more than one event during the animation. The poll path calls the same checker, so a missed or delayed notification is still caught within one interval.

`checkForSpaceChange` asks `SpaceDetector.getCurrentSpace()` for a 1-based `spaceNumber`. If that number differs from `lastKnownSpace`, the monitor updates the cache and invokes every registered space-change callback. The shipping consumers are `DimmingCoordinator.setupSpaceMonitoring` (freeze and resume window-decay timers via `WindowInactivityTracker`), `AppInactivityTracker.setupSpaceTracking` (count inactivity only for apps with a window on the current Space), and `SuperSpacesHUD.setupSpaceMonitoring` (refresh the current-Space highlight). Those consumers need the new number; the notification does not provide it.

`SpaceDetector` reads the plist with `PropertyListSerialization`, not `defaults read`. The path is `NSHomeDirectory()` plus `/Library/Preferences/com.apple.spaces.plist`. Navigation is `SpacesDisplayConfiguration` → `Management Data` → `Monitors` → the first monitor's `Spaces` array. Comments in `getCurrentSpace` and `getAllSpaces` state that Mission Control displays Spaces in plist array order, not sorted by `ManagedSpaceID`. When the user rearranges Spaces, identifiers stay put and their array index changes. The 1-based `spaceNumber` SuperDimmer reports is that array position.

To know which array entry is active, `getCurrentSpace` matches `ManagedSpaceID`. The matcher also calls two undocumented CoreGraphics Services functions, declared with `@_silgen_name` in `SpaceDetector.swift` and independently in the test harnesses `test-cgs-space.swift` and `test-space-reorder-ids.swift`:

```swift
@_silgen_name("CGSMainConnectionID")
func CGSMainConnectionID() -> CGSConnectionID

@_silgen_name("CGSGetActiveSpace")
func CGSGetActiveSpace(_ cid: CGSConnectionID) -> Int
```

`CGSGetActiveSpace` returns the live `ManagedSpaceID`. The detector walks the plist `Spaces` array and returns the matching UUID and 1-based index. This is a SkyLight client pattern used by other Mac window-management tools. It is a compatibility risk if the symbols move, not a vulnerability, and it is not required to understand the reorder predicate below. Header comments put the CGS call under 1 ms and the plist read at about 2–4 ms. Those timings are comments, not an Instruments table. The same comments record that the plist can lag a switch by about 100–200 ms, which is why the live ID and the plist metadata are combined rather than trusting `Current Space` in the file at the instant the workspace notification fires.

## Reorder: same UUID set, different sequence

A Mission Control drag does not change the active Space and does not post `activeSpaceDidChangeNotification`. `SpaceChangeMonitor` therefore treats reorder as a poll-only event. On start, and on every `checkForSpaceChange`, it snapshots `SpaceDetector.getAllSpaces().map { $0.uuid }` into `lastKnownSpaceUUIDOrder`. `checkForSpaceReorder` then compares:

```swift
if currentUUIDOrder != lastKnownSpaceUUIDOrder {
    let oldSet = Set(lastKnownSpaceUUIDOrder)
    let newSet = Set(currentUUIDOrder)
    if oldSet == newSet {
        // same Spaces, different Mission Control order
    } else {
        // UUID added or removed
    }
    lastKnownSpaceUUIDOrder = currentUUIDOrder
    notifyReorderObservers()
}
```

The identity test is same UUID set, different UUID sequence. Create and delete change the set. Both reorder and add/remove still fire `reorderCallbacks`, because consumers re-read the full list. The monitor does not watch the plist with FSEvents; there is no reorder notification to debounce.

Empirical confirmation is in `test-space-reorder-ids.swift`. That harness dumps, every two seconds, each Space's array index, `ManagedSpaceID`, UUID, `id64`, and type, plus `CGSGetActiveSpace()`. After a drag, `ManagedSpaceID`, UUID, and `id64` stayed the same; only array position changed. `id64` equalled `ManagedSpaceID` in those dumps. SuperDimmer therefore treats UUID (and, equivalently, `ManagedSpaceID`) as the stable key and the plist index as the display position.

![Five macOS Spaces labeled by UUID being rearranged, with a reorder-detected indicator](https://superdimmer.com/assets/promo/blog-hero-space-reorder-detection.png)

## Key state by UUID, not by position

Before 11 February 2026, `SpaceVisitTracker.visitOrder` was `[Int]`: Mission Control position numbers persisted in UserDefaults under `superdimmer.spaceVisitOrder`. After a reorder, "Space 3" still meant position 3, which was a different Space. The tracker now stores `[String]` UUIDs, most recent first, trimmed to 20. `recordVisit(to:)` removes the UUID if present and inserts it at index 0.

On load, `loadVisitOrder` decodes `[String]` first. If that fails, it decodes the old `[Int]` array and maps each number through `SpaceDetector.getAllSpaces()` (`index == spaceNumber` → `uuid`). Space numbers that no longer exist are dropped. If both decodes fail, visit history starts empty. That is a one-time identity migration.

Space-change callbacks still receive a 1-based number because decay and inactivity code keys windows by current Space position for "is this window visible." Reorder callbacks take no argument: observers call `getAllSpaces()` again. Mixing those two signals is the point of the split.

## Three monitors, one notification

On 26 January 2026, logs during a switch showed the same line six or seven times:

```
SpaceChangeMonitor: Space changed: 5 -> 6  (×6)
SpaceVisitTracker: Recorded visit to Space 6  (×6)
SpaceChangeMonitor: Space changed: 6 -> 5  (×7)
```

The process (PID 36082) was sampled at 55.5% CPU, state RX. Keyboard input lagged. A search for `SpaceChangeMonitor()` found three constructors: `DimmingCoordinator`, `AppInactivityTracker`, and `SuperSpacesHUD`. Each instance registered for `activeSpaceDidChangeNotification` and started its own 0.5 s poll. One system notification became three detection paths, three log lines, and three downstream callback graphs. The 6–7× amplification is more than 3× because callbacks retriggered visit recording and further work on the main thread.

The shipping type is a singleton:

```swift
final class SpaceChangeMonitor {
    static let shared = SpaceChangeMonitor()
    private init() {}
    private var spaceChangeCallbacks: [(Int) -> Void] = []
    private var reorderCallbacks: [() -> Void] = []
    func addObserver(_ callback: @escaping (Int) -> Void) { ... }
    func addReorderObserver(_ callback: @escaping () -> Void) { ... }
}
```

`startMonitoringInternal` runs once. All three call sites now use `SpaceChangeMonitor.shared.addObserver`. The HUD also calls `addReorderObserver`. The writeup's after-fix target was one log line per switch and CPU under 5%. That after-fix CPU number is a test criterion in `NOTIFICATION_STORM_FIX.md` (verification was still listed as pending there). What shipped is the singleton and the converted call sites.

## Limits

This is a case study of one menu-bar app's Space-identity path, not a public Spaces API and not a WindowServer security report. `CGSMainConnectionID` / `CGSGetActiveSpace` are undocumented SkyLight client symbols; they may change, and we do not document other CGS calls or Space-switching recipes. The plist schema (`SpacesDisplayConfiguration`, `ManagedSpaceID`) is similarly unofficial. `getCurrentSpace` and `getAllSpaces` read only the first monitor entry; per-display numbering is not a measured multi-display matrix here. Header timings (CGS under 1 ms, plist about 2–4 ms, plist lag about 100–200 ms, debounce matching a ~300 ms animation) are comments, not traces. Reorder detection latency is bounded by the 0.5 s poll, not by a notification. The 55.5% CPU figure is one process sample during the fan-out bug; we do not claim a measured post-singleton CPU of under 5%. We do not claim FSEvents on the plist is impossible. Visit-history migration maps old integers through the plist at upgrade time; if the user reordered after the old data was written and before the upgrade, that mapping can attach history to the wrong UUID.