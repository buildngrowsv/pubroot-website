---
title: "Universal macOS Application Control via Accessibility API for Autonomous Agents \u2014 Defensive Method Disclosure"
paper_id: "2026-115"
author: "buildngrowsv"
category: "prior-art/device-method"
date: "2026-04-05T19:39:57Z"
abstract: "|"
score: 8.5
verdict: "ACCEPTED"
badge: "text_only"
---

## 1. Method Identification

- **Name:** Universal Accessibility API-based application control for autonomous agents
- **Platform:** macOS 10.15 (Catalina) and later; tested through macOS 15 (Sequoia)
- **Core API:** `AXUIElement` (ApplicationServices.framework / HIServices)
- **Supporting APIs:** `CGEvent` (CoreGraphics.framework), `CGWindowListCopyWindowInfo` (CoreGraphics), `VNRecognizeTextRequest` (Vision.framework), `NSWorkspace` / `NSRunningApplication` (AppKit.framework)
- **Implementation languages:** Rust (VCC), Python via PyObjC (BCL), Swift (HID injection controller)
- **Supporting technologies:** `osascript` / AppleScript bridge for app activation and browser URL retrieval, Chrome DevTools Protocol extension bridge for DOM-level augmentation
- **Interface:** Command-line tools producing structured JSON output consumed by LLM-based autonomous agents
- **First public implementation date:** 2025 (BCL), 2026 (VCC)

## 2. Problem Statement

Current macOS automation approaches each suffer from fundamental limitations when the goal is universal, cross-application control by an autonomous agent:

1. **AppleScript / Open Scripting Architecture (OSA):** Requires per-application scripting dictionaries. Each application exposes a different object model (if any). Many modern applications (Electron-based, Qt-based, unsigned) expose no AppleScript dictionary at all. An agent must learn each application's unique scripting vocabulary.

2. **macOS Shortcuts (Automator successor):** Limited to predefined action types. Cannot discover or interact with arbitrary UI elements. No mechanism for an agent to enumerate what interactive controls exist in a window at runtime.

3. **Screenshot-based Computer Use Agents (CUA):** Tools like Anthropic's Claude Computer Use and OpenAI's operator rely on taking screenshots, sending them to a vision model, receiving pixel coordinates, and clicking at those coordinates. This approach is slow (screenshot capture + model inference per action), expensive (vision model API calls), brittle (pixel coordinates shift with window position, resolution, and theme), and fundamentally unable to read programmatic metadata (element roles, labels, enabled state, focus state) that the operating system already knows.

4. **Hammerspoon / Lua scripting:** Provides some AXUIElement access but is designed as a human power-user tool, not as an agent-consumable interface. No structured JSON output, no element indexing system, no session caching, no HID injection pipeline integrated with discovery.

**The gap:** No existing tool provides a single, generic, application-agnostic interface that (a) discovers all interactive UI elements across any macOS application at runtime, (b) assigns stable indices for agent reference, (c) provides structured metadata (role, label, position, size, enabled state) as JSON, (d) enables interaction (click, type, scroll, key chords) via either programmatic AX actions or synthesized HID events, and (e) supports background operation without requiring screen capture or vision model inference.

## 3. Method Description

The method consists of five integrated subsystems operating in a pipeline:

### 3.1 Application and Window Targeting

The agent specifies a target application by name (e.g., `--app Safari`). The system resolves this to a process identifier (PID) via `pgrep -x <app_name>`. From the PID, an AX application element is created:

```
AXUIElementCreateApplication(pid) → AXUIElementRef (app root)
```

The system enumerates windows by reading the `AXWindows` attribute on the app root. Each window's `AXPosition` and `AXSize` attributes provide frame geometry. A selection heuristic filters out narrow utility windows (width < 200pt) and prefers large content windows (width > 600pt) when no explicit window index is provided. The agent can specify `--window N` for explicit targeting.

**Stable window identity:** To maintain a stable reference across discovery cycles (since window order can change), the system resolves each AX window to a CoreGraphics window identifier by matching AX window bounds against the `CGWindowListCopyWindowInfo` output (`kCGWindowBounds`, `kCGWindowOwnerPID`, `kCGWindowLayer == 0`), within a tolerance of 5 points. The resulting `kCGWindowNumber` is hashed with the app name to produce a `window_ref` (format: `win-{:016x}`) that remains stable across AX tree refreshes.

### 3.2 Accessibility Tree Traversal and Element Discovery

From the selected window element, the system performs a depth-first recursive traversal of the AX element tree:

```
walk_interactive(element, results, depth, max_depth=25):
    role ← AXUIElementCopyAttributeValue(element, "AXRole")
    if role ∈ INTERACTIVE_ROLES:
        attrs ← AXUIElementCopyMultipleAttributeValues(element,
            ["AXPosition", "AXSize", "AXDescription", "AXTitle", "AXValue"], 
            kAXCopyMultipleAttributeOptionIgnoreErrors)
        build_element(role, attrs) → append to results with index = len(results)
    children ← AXUIElementCopyAttributeValue(element, "AXChildren")
    for child in children:
        walk_interactive(child, results, depth+1, max_depth)
```

**Role filtering:** Two discovery modes exist:
- **Interactive discovery** (`INTERACTIVE_ROLES`): buttons, links, text fields, checkboxes, radio buttons, pop-up buttons, combo boxes, sliders, menu items, tabs, toggle buttons, increment/decrement buttons, disclosure triangles, toolbars, and similar actionable controls.
- **All-text discovery** (`ALL_TEXT_ROLES`): adds static text, headings, web areas, images, groups — used by the `read-page` command for full page content extraction.

**Batch attribute reads:** To minimize Accessibility IPC round-trips (each being a Mach message to the target process), the system uses `AXUIElementCopyMultipleAttributeValues` to fetch up to 5 attributes in a single call. Error sentinels (`AXValueGetType == 5`, type `AX_VALUE_TYPE_AX_ERROR`) are mapped to null rather than causing failures. Thread-local `CFString` caches avoid repeated allocation of hot attribute name strings.

**Geometry decoding:** `AXPosition` and `AXSize` are `AXValue` wrappers decoded via `AXValueGetValue` with type discriminants: `1` = `CGPoint`, `2` = `CGSize`. In the Python implementation (BCL), position and size are parsed from string representations using regex patterns (`x:… y:…`, `w:… h:…`) because the PyObjC bridge returns displayable strings.

**Index assignment:** Each discovered element receives a sequential integer index in depth-first traversal order (interactive discovery) or reading order sorted by `(y, x)` coordinates (all-text / read-page discovery). These indices serve as the agent's handle for subsequent interaction commands.

### 3.3 Structured JSON Output for Agent Consumption

Discovery results are serialized as JSON with a standard envelope:

```json
{
  "app": "Safari",
  "window_title": "Example Website",
  "url": "https://example.com",
  "window_ref": "win-a1b2c3d4e5f60718",
  "session_id": "cli-1712345678901",
  "element_count": 47,
  "elements": [
    {
      "index": 0,
      "role": "button",
      "text": "Submit",
      "title": "Submit Form",
      "description": "Submit the registration form",
      "value": null,
      "enabled": true,
      "focused": false,
      "metadata": { "ax_identifier": "submit-btn", "ax_role": "AXButton" }
    }
  ]
}
```

Coordinates are retained in the session cache but omitted from JSON output by default to reduce context window consumption by LLM agents. The `--compact` mode further strips help text, available flows, and session history from the envelope.

### 3.4 Element Interaction via HID Injection

Once an agent selects an element by index, interaction proceeds through a tiered system:

**Tier 1 — Programmatic AX Action:** `AXUIElementPerformAction(element, "AXPress")` — the system re-walks the tree to the same index, retrieves the live `AXUIElementRef`, and performs the action. No coordinate calculation needed. Works for buttons, links, checkboxes, menu items.

**Tier 2 — CGEvent HID Injection (coordinates):** When AX actions fail or are unavailable, the system calculates the element's screen center from cached geometry and injects CoreGraphics events:

- **Mouse click:** `CGEventCreateMouseEvent(source, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)` → `CGEventPost(kCGSessionEventTap, event)`, followed by a randomized hold duration (40–120ms) and mouse-up. Right-click and middle-click use corresponding event types.
- **Keyboard typing (Unicode):** `CGEventCreateKeyboardEvent(source, 0, keyDown)` → `CGEventKeyboardSetUnicodeString(event, length, utf16_chars)` — virtual key 0 with Unicode string override, posted as key-down then key-up for each character.
- **Keyboard chords:** `CGEventCreateKeyboardEvent` with the real virtual key code, then `CGEventSetFlags` with the appropriate modifier masks (`kCGEventFlagMaskCommand`, `kCGEventFlagMaskShift`, etc.).
- **Scroll:** `CGEventCreateScrollWheelEvent2(source, kCGScrollEventUnitLine, 2, vertical_delta, horizontal_delta)`.

The event source is created with `CGEventSourceCreate(kCGEventSourceStateHIDSystemState)` (state ID 1), and events are posted to `kCGSessionEventTap` (tap location 1) for mouse/keyboard, or `kCGHIDEventTap` (tap location 0) for scroll events.

**Tier 3 — Guarded Input with Event Tap:** For high-reliability scenarios where user input during agent operation could interfere, a `CGEventTap` is installed at the session level:

```
CGEvent.tapCreate(
    tap: .cgSessionEventTap,
    place: .headInsertEventTap,
    options: .defaultTap,
    eventsOfInterest: mouseMask | keyboardMask,
    callback: guardedTapCallback
)
```

The callback returns `nil` to swallow user-originated events while passing through agent-originated events identified by a sentinel value (`0x42434C475244`) set via `CGEventSetIntegerValueField(.eventSourceUserData, value: sentinel)`. The tap auto-re-enables itself on `tapDisabledByTimeout` or `tapDisabledByUserInput` events. After the guarded operation completes, the previous cursor position and frontmost application are restored.

### 3.5 Text-Based Element Matching and Scroll-Into-View

Beyond index-based interaction, the system supports text-based element lookup:

- **Contains-text lookup:** The agent specifies a text fragment; the system filters discovered elements by case-insensitive substring match against `text`, `title`, `description`, and `value` fields.
- **Click-text with auto-scroll:** When the target element's center falls outside the visible window bounds (with an 8px inset guard), the system synthesizes scroll events (`CGEventCreateScrollWheelEvent2`, half-page increments), re-discovers elements after each scroll (refreshing the cache), and retries for up to 18 attempts. This is synthetic wheel injection + AX cache refresh, not DOM `scrollIntoView`.

### 3.6 OCR Fallback via Vision Framework

When AX tree traversal yields fewer than a threshold number of text elements (< 5), the system falls back to optical character recognition:

1. **Window screenshot:** `screencapture -l<CGWindowID> -x -o` captures a single window as PNG.
2. **Vision OCR:** `VNImageRequestHandler` initialized from the image URL, performing `VNRecognizeTextRequest` at `VNRequestTextRecognitionLevelAccurate`.
3. **Coordinate normalization:** Vision's bottom-left-origin normalized bounding boxes are converted to screen coordinates using the image pixel dimensions, display scale factor, and window origin offset.
4. **Deduplication:** OCR results are merged with AX results using a proximity threshold (30pt) and substring text match; AX elements take priority, and only non-duplicate OCR elements are appended.

## 4. Architecture

### 4.1 Element Discovery Pipeline

```
Agent Command (JSON args)
    │
    ▼
App Targeting: pgrep -x <name> → PID → AXUIElementCreateApplication(pid)
    │
    ▼
Window Selection: AXWindows → filter by geometry → resolve CGWindowID
    │                                                    │
    ▼                                                    ▼
AX Tree Walk: recursive DFS,              window_ref hash (stable ID)
    depth limit 25,
    role filter (interactive / all-text),
    batch attribute reads
    │
    ▼
Index Assignment: sequential (DFS) or reading-order (y,x sort)
    │
    ▼
Cache Write: session-scoped JSON + global last_discovery.json
    │
    ▼
JSON Output → Agent (LLM context window)
```

### 4.2 Interaction Pipeline

```
Agent Command: click <index> | type <index> <text> | key <chord>
    │
    ▼
Cache Load: session cache → global cache → auto-rediscovery on miss
    │
    ▼
Element Resolution: retrieve AXUIElementRef by index (re-walk)
    │
    ▼
Tier Selection:
    ├─ AXPress available? → AXUIElementPerformAction
    ├─ Coordinates available? → CGEvent injection
    └─ High-reliability? → Guarded event tap + CGEvent
    │
    ▼
Verification (optional): re-discover, match by ax_identifier
    or geometry score, confirm state change
```

### 4.3 Key Architectural Patterns

- **Session-based discovery caching:** Each agent session (`--session-id`) maintains its own discovery snapshot under `~/.vcc/sessions/session_<id>/last_discovery.json` (VCC) or `~/.bcl/last_discovery.json` (BCL). Indexed actions load from cache, avoiding redundant tree walks. Cache is invalidated and refreshed on miss (`prime_action_cache`).
- **Self-healing cache:** When a cached element index doesn't match the current AX tree (element removed, page navigated), the system automatically re-discovers and rebuilds the cache before retrying the action.
- **Contains-text lookup:** `vcc lookup --contains "Submit"` filters elements by text content without requiring the agent to hold the full element list in context, reducing LLM token consumption.
- **Scroll-into-view loop:** Synthetic scroll + cache refresh cycle (up to 18 iterations) brings off-screen elements into view without relying on application-specific scroll APIs.
- **HID mutex (operational):** When multiple agents share a single macOS machine, a social/messaging protocol (bs-mail CLAIM/WAIT/RELEASE pattern with task identifiers) prevents concurrent HID injection conflicts. Only one agent operates the physical input channel at a time.
- **Background operation:** Actions target specific `--app` and `--window` parameters. Window focusing occurs only when necessary for CGEvent delivery, and the system restores the previous frontmost application after guarded operations.
- **Type verification:** After typing into a text field, the system optionally re-discovers the element, matches by `ax_identifier` or geometry proximity score, reads the new `AXValue`, and retries with select-all/delete/retype if the content doesn't match.

## 5. Prior Art

The following prior art exists in the space of macOS automation and accessibility-based control:

1. **Apple Accessibility API (AXUIElement):** Apple's documentation describes the `AXUIElement` C API for assistive technology access to application UI elements. The API provides element attributes (role, title, value, position, size), tree traversal (children, parent), and actions (press, confirm, cancel). *Reference: Apple Developer Documentation, "Accessibility Programming Guide for macOS" (developer.apple.com); HIServices/AXUIElement.h headers.*

2. **AppleScript / Open Scripting Architecture:** Apple's inter-application communication mechanism allows scripting of applications that implement scripting dictionaries. Limited to cooperating applications; no generic element discovery. *Reference: Apple Developer Documentation, "AppleScript Language Guide."*

3. **macOS Shortcuts (née Automator):** Apple's visual automation tool provides predefined action blocks. Cannot enumerate arbitrary UI elements or inject HID events programmatically. *Reference: Apple Developer Documentation, "Shortcuts for macOS."*

4. **Hammerspoon:** Open-source macOS automation tool using Lua scripting. Provides `hs.axuielement` module wrapping `AXUIElement` for element inspection. Designed for human power users; outputs Lua tables, not agent-consumable JSON; no integrated HID injection pipeline or session caching. *Reference: github.com/Hammerspoon/hammerspoon.*

5. **System Events (UI Scripting via AppleScript):** Apple's `System Events` process provides `entire contents` access to AX trees via AppleScript. Extremely slow for large windows (minutes for complex web pages). No batch attribute reads. No structured output format. *Reference: Apple's Accessibility Inspector documentation.*

6. **Screenshot-based Computer Use Agents (CUA):** Anthropic's Claude Computer Use (2024), OpenAI's Operator (2025), and similar systems use screen capture → vision model → coordinate prediction → mouse/keyboard injection. Requires per-action vision model inference (high latency, high cost). Cannot access programmatic element metadata. Fragile under resolution/theme/position changes. *Reference: Anthropic blog, "Introducing Computer Use" (2024); OpenAI blog, "Operator" (2025).*

7. **CGEvent API:** Apple's CoreGraphics event synthesis API allows programmatic creation and posting of mouse, keyboard, and scroll events. Well-documented for input simulation but provides no element discovery capability. *Reference: Apple Developer Documentation, "Quartz Event Services Reference."*

8. **Accessibility Inspector (Xcode):** Apple's developer tool for inspecting AX trees. GUI application; not programmatically scriptable by agents. *Reference: Apple Developer Documentation, "Accessibility Inspector User Guide."*

## 6. Novel Contribution

This disclosure identifies the following elements that, in combination, constitute the novel method:

1. **Universal element discovery across all macOS applications via a single API call pattern:** Rather than per-application scripting dictionaries, the method uses `AXUIElement` tree traversal with role-based filtering to discover interactive elements in *any* application that exposes an Accessibility tree — which is all AppKit, SwiftUI, Catalyst, Electron, Chrome, Firefox, and most Qt applications on macOS. This universality is the core differentiator from AppleScript, which requires per-app dictionaries.

2. **Integer-indexed element addressing for LLM agent consumption:** Discovered elements receive sequential integer indices that agents reference in subsequent commands. This is a deliberate design for LLM context efficiency — an agent can say "click 7" rather than describing element location, CSS selectors, or pixel coordinates. No prior tool assigns stable, cacheable integer indices to AX elements for programmatic agent use.

3. **Tiered interaction model (AX action → CGEvent injection → guarded event tap):** The system attempts the most reliable method first (programmatic `AXPress`) and falls back through coordinate-based `CGEvent` injection to guarded event-tap mode. No prior tool combines these three tiers in a single agent-facing command.

4. **Session-scoped discovery caching with self-healing:** Discovery results are cached per session; actions load from cache to avoid re-traversal; cache misses trigger automatic rediscovery. This pattern enables multi-step agent workflows without redundant tree walks, while self-healing on page navigation or element mutation.

5. **CGWindowList-based stable window identity:** Matching AX window bounds against `CGWindowListCopyWindowInfo` output to derive `kCGWindowNumber` and hash it into a stable `window_ref` that persists across AX tree refreshes. This allows agents to maintain window identity across discovery cycles.

6. **Vision OCR fallback with AX deduplication:** When the AX tree is sparse (< 5 text elements), the system captures a window screenshot via `screencapture -l<windowID>`, runs `VNRecognizeTextRequest`, converts Vision coordinates to screen coordinates, and deduplicates against existing AX elements by proximity and text match. This hybrid approach covers applications with incomplete AX tree exposure.

7. **Guarded HID injection with event-source tagging:** Installing a `CGEventTap` that filters events by a sentinel value in `eventSourceUserData`, allowing agent-originated events to pass while suppressing concurrent user input. The sentinel pattern (`0x42434C475244`) enables coexistence of guarded operation with event delivery, and post-operation restoration of cursor position and frontmost application.

8. **Text-based element matching with synthetic scroll-into-view:** Combining contains-text filtering of AX elements with a scroll → re-discover → retry loop (up to 18 iterations of half-page CGEvent scroll wheel injection) to bring off-screen elements into the visible area and then interact with them. This is application-agnostic scroll-into-view without DOM access.

9. **Agent-native JSON interface with context-window-aware compaction:** Output envelopes are designed for LLM consumption with configurable verbosity (`--compact`), geometry omission from default output (retained in cache), and structured metadata (session ID, window ref, URL, app name) that agents use for state tracking across multi-step workflows.

## 7. Supporting Implementation

Two complete implementations of this method exist:

### 7.1 VCC (Vibeswarm Computer Control) — Rust

- **Repository:** github.com/buildngrowsv (WebMCP-Control-Layer-Research/vibeswarm/vcc)
- **Language:** Rust, using `core-foundation`, `core-graphics` crate bindings and raw FFI to `AXUIElement*` functions
- **Key source files:**
  - `crates/vcc-platform-macos/src/discovery.rs` — AX tree traversal, `AXUIElementCopyMultipleAttributeValues`, batch attribute reads, role filtering, window selection
  - `crates/vcc-platform-macos/src/hid_controller.rs` — `CGEventCreateMouseEvent`, `CGEventCreateKeyboardEvent`, `CGEventKeyboardSetUnicodeString`, `CGEventCreateScrollWheelEvent2`
  - `crates/vcc-platform-macos/src/cg_window_resolve.rs` — `CGWindowListCopyWindowInfo` matching for stable window ID
  - `crates/vcc-platform-macos/src/ax_element_mapper.rs` — Role normalization (`AXButton` → `button`)
  - `crates/vcc-core/src/cache.rs` — Session-scoped `CachedDiscoverySnapshot` serialization
  - `crates/vcc-core/src/element.rs` — `Element` struct definition
  - `crates/vcc-cli/src/main.rs` — CLI commands: discover, read-page, click, click-text, type, key, scroll, lookup, locate, windows, activate
- **CLI commands:** `vcc discover`, `vcc read-page`, `vcc click <index>`, `vcc click-text "Submit"`, `vcc type <index> "hello"`, `vcc key cmd+a`, `vcc scroll down`, `vcc lookup --contains "text"`, `vcc locate --contains "url-fragment"`, `vcc windows --app Safari --urls`

### 7.2 BCL (Browser Control HID Layer) — Python/Swift

- **Repository:** github.com/buildngrowsv (WebMCP-Control-Layer-Research/browser-control-hid-layer)
- **Language:** Python (PyObjC bindings to `ApplicationServices`), Swift (HID injection controller)
- **Key source files:**
  - `orchestrator/fast_ax_discovery.py` — PyObjC `AXUIElementCreateApplication`, `AXUIElementCopyMultipleAttributeValues`, recursive `walk_tree_for_interactive`, `walk_tree_for_all_text`, `read_page_text`
  - `orchestrator/apple_vision_ocr_fallback_service.py` — `VNRecognizeTextRequest`, `CGWindowListCopyWindowInfo`, coordinate normalization, AX/OCR deduplication
  - `mouse-controller/mouse_controller.swift` — `CGEventCreateMouseEvent`, guarded event tap (`CGEvent.tapCreate`), `eventSourceUserData` sentinel tagging, smooth motion (ease-in-out), `guardedClickAtPoint`, `guardedType`
  - `cli/bcl` — Argparse CLI: discover, read-page, click, safe-click, type, safe-type, key, scroll, windows, lookup
  - `orchestrator/bcl_daemon_server.py` — HTTP daemon for persistent session management
- **CLI commands:** `bcl discover --app Safari --json`, `bcl read-page --app Safari`, `bcl click <index>`, `bcl safe-click <index>`, `bcl type <index> "hello"`, `bcl safe-type <index> "hello"`, `bcl key cmd+a`, `bcl scroll down`, `bcl windows --app Safari`

## 8. Public-Domain Dedication

This disclosure and the method described herein are dedicated to the public domain under the **Creative Commons CC0 1.0 Universal** public domain dedication.

To the extent possible under law, the author has waived all copyright and related or neighboring rights to this work. This work is published from the United States.

The purpose of this dedication is to ensure that the described method constitutes prior art that is freely available to all, preventing any party from obtaining patent claims that would restrict the practice of this method.

See: https://creativecommons.org/publicdomain/zero/1.0/

## 9. Limitations and Disclaimer

1. **Not legal advice.** This document is a technical disclosure, not a legal opinion. Consult a patent attorney for specific intellectual property questions.

2. **macOS Accessibility permission required.** The method requires the controlling process to be granted Accessibility permission via System Settings → Privacy & Security → Accessibility. This is a deliberate Apple security gate that requires explicit user consent (or MDM configuration).

3. **AX tree completeness varies.** Applications that do not implement the NSAccessibility protocol (rare on modern macOS, but possible with custom rendering engines or games) will have sparse or empty AX trees. The OCR fallback partially mitigates this but cannot recover programmatic metadata (roles, labels, enabled state).

4. **HID injection requires trust.** `CGEvent` posting requires the process to be trusted for Accessibility. On macOS 10.15+, `CGEventPost` from untrusted processes is silently dropped.

5. **Single-machine limitation.** The HID injection and AX IPC mechanisms operate on the local machine only. Remote control would require a relay layer (not described here).

6. **Event tap fragility.** `CGEventTap` can be disabled by the system if the callback takes too long or encounters errors. The guarded input implementation re-enables the tap on `tapDisabledByTimeout` / `tapDisabledByUserInput`, but rapid system-level changes can cause brief gaps.

7. **No warranty.** THE METHOD IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

## References

1. Apple Inc. "Accessibility Programming Guide for macOS." Apple Developer Documentation. https://developer.apple.com/library/archive/documentation/Accessibility/Conceptual/AccessibilityMacOSX/

2. Apple Inc. "AXUIElement.h — HIServices Framework." macOS SDK Headers. ApplicationServices.framework/Frameworks/HIServices.framework/Headers/AXUIElement.h

3. Apple Inc. "Quartz Event Services Reference." Apple Developer Documentation. https://developer.apple.com/documentation/coregraphics/quartz_event_services

4. Apple Inc. "CGWindowListCopyWindowInfo." Apple Developer Documentation. https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo

5. Apple Inc. "VNRecognizeTextRequest." Apple Developer Documentation. https://developer.apple.com/documentation/vision/vnrecognizetextrequest

6. Apple Inc. "NSWorkspace." Apple Developer Documentation. https://developer.apple.com/documentation/appkit/nsworkspace

7. Hammerspoon contributors. "Hammerspoon — Staggeringly powerful macOS desktop automation with Lua." https://github.com/Hammerspoon/hammerspoon

8. Anthropic. "Introducing Computer Use." Anthropic Blog, October 2024. https://www.anthropic.com/news/3-5-models-and-computer-use

9. Apple Inc. "AppleScript Language Guide." Apple Developer Documentation. https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/

10. Apple Inc. "CGEvent — Creating Events." Apple Developer Documentation. https://developer.apple.com/documentation/coregraphics/cgevent

11. Apple Inc. "CGEventTapCreate." Apple Developer Documentation. https://developer.apple.com/documentation/coregraphics/1454426-cgeventtapcreate