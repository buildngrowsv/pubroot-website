---
title: "Configuring VCC on macOS \u2014 Setup, Doctor, and the Unattended Readiness Gate"
paper_id: "2026-067"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-04-05T03:18:03Z"
abstract: "This case study documents how we operationalize VCC (Vibe Computer Control), a Rust CLI that drives macOS UIs via the accessibility tree and OS-level input. We treat first-run configuration as a product requirement: agents must not assume permissions exist. The workflow is provision the sandbox once with setup, then gate every unattended run on doctor reporting ok true, with explicit remediation when Automation or Accessibility blocks browser control."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
---

## Context

VCC is a cross-platform computer-control tool aimed at AI agents. On macOS it discovers UI elements through Accessibility, then issues clicks, typing, scrolling, and shortcuts through real HID-style events. Unlike brittle screen-coordinate-only approaches, the primary path uses structured discovery so agents can reason about controls by role, label, and index.

## What we configure before any flow

We run `vcc setup --json` once per machine or operator session when onboarding automation. That command is designed to return the permission surface up front: Accessibility for discovery and input, Automation for AppleScript-driven browser behavior where applicable, Input Monitoring when host policy requires it for key delivery, and Screen Recording for future screenshot or OCR paths. Presenting this list early prevents agents from failing halfway through a vendor dashboard flow because a toggle was never granted.

## The doctor gate

We do not treat “it worked once in the IDE” as sufficient. We run `vcc doctor --json` immediately before unattended sequences. The payload distinguishes `ok`, `mode` (`ready` versus `blocked`), and machine-readable remediation: `checks.unattended_ready`, `checks.permissions_required`, `checks.blocked_reasons`, and `checks.remediation_steps`. If doctor does not report `ok: true`, we stop and fix permissions rather than looping on flaky clicks. This is how we keep automation failures attributable to application state rather than invisible OS denial.

## Browser-specific preflight

For browsers—especially Google Chrome—we enable “Allow JavaScript from Apple Events” under the Developer menu when extension or automation-backed flows are in scope. That is an operator-visible step; it is not something a low-context worker can infer from HTTP alone.

## Why this matters for agent swarms

Parallel coding tasks can proceed independently, but GUI automation shares a singleton control plane. Serializing setup and doctor checks avoids races where two sessions fight for Accessibility trust prompts or half-enabled terminals. Documenting the gate as part of VCC configuration makes the difference between “sometimes works in Cursor” and “reliable enough for revenue-critical vendor flows.”

## Boundaries

Permission names and exact Settings paths can change between macOS releases; always prefer the strings returned by `setup` and `doctor` on the target OS. This article describes operational practice in our workspace, not a guarantee about third-party app AX quality.