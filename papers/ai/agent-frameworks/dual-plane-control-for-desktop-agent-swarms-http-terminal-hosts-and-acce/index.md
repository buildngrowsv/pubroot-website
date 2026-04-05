---
title: "Dual-Plane Control for Desktop Agent Swarms \u2014 HTTP Terminal Hosts and Accessibility Automation (VCC)"
paper_id: "2026-065"
author: "buildngrowsv"
category: "ai/agent-frameworks"
date: "2026-04-05T03:17:28Z"
abstract: "We describe how the VibeSwarm stack splits agent-driven control into two deliberate planes. The first plane is a loopback HTTP control server in the desktop shell that exposes PTY lifecycle and stdin writes (list terminals, create sessions, write bytes, resize). The second plane is VCC, a Rust CLI that drives macOS Accessibility and HID to operate browsers and native UIs when PTY APIs are insufficient. We explain why these layers are kept separate, how the VibeSwarm CLI maps to host endpoints, and where gaps remain (scrollback over HTTP, agent-targeted PTY routing). This is operational architecture from an active codebase, not a benchmark."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Article drafted with Cursor Composer from repository docs and source layout; claims traceable to the linked commit."
---

## Introduction

Autonomous coding agents need two different kinds of "hands." Sometimes the work is entirely inside a shell: run tests, call package managers, tail logs. Sometimes the work is in a GUI: a browser with a third-party dashboard, a desktop IDE panel that does not expose a clean API, or a consent screen. The VibeSwarm / WebMCP research tree implements both paths without pretending they are the same primitive.

## The HTTP terminal host plane

The desktop application exposes a **control server** on loopback. Client code — including the `vibeswarm` CLI — calls JSON endpoints for health checks, swarm state, and terminal operations. Representative CLI surface names include `host probe`, `host terminals-list`, `host terminal-create`, `host terminal-write`, and related resize/visibility commands. Those commands are thin HTTP clients over the same actions the UI uses to spawn PTY-backed sessions.

**Design intent:** keep terminal automation on a stable, testable network boundary. Scripts and agents can integrate without driving the Accessibility stack. The product spec explicitly marks "headless and scripted control" as a vibeswarm concern distinct from HID.

**Current limits (documented in-repo):** server-side scrollback for arbitrary "read last N lines" is not universally exposed over HTTP; output is primarily streamed to the embedded webview. Multicast "send to all agent terminals" is still a gap relative to the checklist. These limits matter when judging what agents can do with HTTP alone.

## The VCC plane (Accessibility / HID)

VCC is the recommended tool when the target is not a PTY. The documented loop is: locate the right window, list windows with URLs when needed, prefer `read-page`, narrow with `lookup` before heavy `discover`, then act with `click`, `type`, or `key`. Session identifiers isolate discovery caches when multiple agents run.

Chrome-specific enhancements such as DOM `innerText` line deltas (`chrome-diff`) are explicitly **not** OCR; they reduce cost versus vision-only approaches. Geometry and OCR-style extras are treated as opt-in per session.

## Why we do not merge the two planes

Mixing PTY control and HID in one abstraction would blur failure modes: HTTP errors versus AX tree drift, rate limits versus focus stealing. The engineering choice is to **name the layer** in runbooks so operators know whether they need a loopback client or a window handle.

## Relation to swarm mail

Swarm mail (`vibeswarm mail` and related file drops) is a **coordination channel** (JSON payloads, auditability), not a substitute for raw terminal bytes. The spec tells implementers to choose PTY stdin versus mail deliberately.

## Conclusion

Dual-plane control — HTTP for PTY sessions, VCC for GUI — lets agents pick the smallest powerful interface. The approach trades a larger conceptual surface for predictable debugging and parallel development of the host server and the control CLI.

## References

- VibeSwarm CLI terminal orchestration spec: `vibeswarm/docs/VIBESWARM-CLI-TERMINAL-ORCHESTRATION-SPEC.md`
- VCC README agent control flow: `vibeswarm/vcc/README.md`
- Agent session toggles and chrome-diff: `docs/AGENT-SESSION-TOGGLES-AND-VCC-EXTRAS.md`