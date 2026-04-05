---
title: "Session-Scoped Discovery, Mutex Discipline, and Full-Output Rules for IDE Terminal Automation"
paper_id: "2026-059"
author: "buildngrowsv"
category: "se/devops"
date: "2026-04-05T03:21:15Z"
abstract: "This note captures operational rules we use when an agent drives the integrated terminal inside Cursor (or similar IDEs) via Accessibility tooling rather than a raw SSH PTY. Topics include stable session identifiers for discovery cache isolation, a practical sequence to expose the terminal panel when the Accessibility tree omits it, mutex coordination so multiple agents do not fight HID input, and a strict prohibition on truncating JSON tool output that places metadata before element lists. It is written for practitioners automating developer environments on macOS."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Tutorial drafted with Cursor Composer; automation policies originate from workspace runbooks in the linked repository ecosystem."
---

## Problem statement

IDE-embedded terminals are not standard files. Agents that only `read` a log miss interactive state: prompts, pagers, hung processes. Accessibility-driven control can send keystrokes to the PTY, but only if focus and element indices are correct. Without discipline, automation burns context on stale indices or partial JSON.

## Session identifiers

VCC supports `--session-id` on its commands so discovery caches and optional chrome-diff logs do not collide when multiple automations run. Treat a session id as a **per-task namespace**, not a username.

## Bringing the terminal forward

macOS focus is fragile. Runbooks recommend activating the correct Cursor window before keys, toggling the bottom panel (for example Command-J), and when radios for "Terminal" are missing, using the Command Palette path: "Toggle Terminal." Only after focus is in the PTY should arrow-up/down be used for shell history.

## Mutex between agents

HID is single-writer. Operational policy assigns one runner at a time for VCC (or legacy BCL) on a machine, with explicit claim and release messages on shared coordination channels. Parallel agents without mutexing produce nondeterministic clicks — a class of failures that looks like "flaky CI" but is actually input interleaving.

## Never truncate VCC or BCL JSON

Control tooling often prints **metadata before** the element list. Piping through `head` or `tail` loses actionable indices. Narrow with lookup/discovery filters instead. This rule exists because we repeatedly paid duplicate round-trips when agents truncated output.

## When to prefer PTY HTTP instead

If the stack exposes loopback terminal APIs (as VibeSwarm does for embedded sessions), prefer that interface for bulk stdin and lifecycle. Reserve Accessibility for cases where the IDE or host does not expose the needed surface.

## Checklist

1. Resolve the correct window every run; titles drift.
2. Set `--session-id` per automation task.
3. Claim HID mutex if other agents share the host.
4. Avoid shell pipes that clip JSON control output.
5. Fall back to Command Palette when panel controls are absent from the tree.

## Conclusion

IDE terminal automation fails for boring reasons: focus, stale indices, and clipped logs. Session ids, mutex discipline, and full-output hygiene are the difference between occasional demos and reliable loops.

## References

- VCC README — agent control flow: `vibeswarm/vcc/README.md`
- Cursor terminal bridging notes (UserRoot workspace rules): operational runbooks under `.cursor/rules/`