---
title: "Configuring VCC on macOS — Setup, Doctor, and the Unattended Readiness Gate"
paper_id: "2026-067"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-04-05T03:18:03Z"
abstract: "AI agents that drive desktop UIs assume permissions exist until they do not, and the resulting failures—halfway through a vendor dashboard flow—are expensive to debug and impossible to retry cleanly. We built VCC (Vibe Computer Control) with first-run configuration as a product requirement: a setup command that surfaces every macOS permission needed upfront, and a doctor command that gates unattended automation on machine-readable readiness. This article explains why treating permissions as a preflight checklist, not a runtime surprise, is the difference between demo-grade and production-grade desktop automation."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
---

## The permission problem nobody plans for

Desktop automation on macOS requires a stack of OS-level permissions: Accessibility for discovering and interacting with UI elements, Automation for AppleScript-driven browser control, Input Monitoring for key delivery under certain security policies, and Screen Recording for screenshot or OCR capabilities.

Most automation tools discover these requirements at runtime. The agent starts a flow, gets 60% through a Stripe dashboard configuration, and then a permission dialog blocks further progress. The agent cannot dismiss the dialog programmatically (it is a system-level prompt), the vendor dashboard session may have timed out by the time a human grants the permission, and the flow must restart from scratch.

We hit this pattern enough times that we made permission management a first-class feature of VCC rather than an afterthought.

## Setup: surface the permission surface once

The `vcc setup` command is designed to run once per machine or operator session during onboarding. It does not assume any permissions exist. Instead, it enumerates every capability VCC might need—Accessibility, Automation, Input Monitoring, Screen Recording—and presents the full list upfront.

The design philosophy is borrowed from mobile app permission flows: ask for everything you will need at a well-defined moment, not scattered across the user's first interaction with each feature. The difference is that macOS permissions require trips to System Settings and sometimes terminal commands, so presenting them as a checklist is more respectful of the operator's time than surfacing them one by one during automation.

## Doctor: the preflight gate for unattended runs

"It worked once in my IDE" is not a reliable baseline for automation that needs to run unattended—overnight batch operations, scheduled vendor checks, or multi-step deployment flows. Permissions can be revoked, macOS updates can reset trust decisions, and a new terminal app might not inherit the Accessibility trust of the old one.

`vcc doctor` is the answer: run it immediately before any unattended sequence. It returns structured JSON with `ok` (boolean), `mode` (ready vs. blocked), and machine-readable diagnostics: which permissions are granted, which are missing, and exact remediation steps for each. The rule is simple: if doctor does not report `ok: true`, the automation does not start.

This converts permission failures from "the click didn't work and we don't know why" into "Automation permission for Chrome is missing, grant it in System Settings > Privacy & Security > Automation." Attributable, fixable, and catchable before the flow begins.

## Why this matters when agents share a machine

In a multi-agent swarm, several coding agents can work independently on separate repositories. But GUI automation is inherently serial—there is one mouse, one keyboard focus, one foreground application. If two agents try to run VCC simultaneously, one gets correct clicks and the other gets chaos.

Serializing the setup and doctor checks prevents a subtler race condition: two sessions simultaneously triggering Accessibility trust prompts, which can leave both in a half-granted state. By documenting the permission gate as part of VCC configuration—not as a troubleshooting step—we made the difference between "this sometimes works when I'm watching" and "this reliably completes vendor flows at 3am."

## Browser-specific considerations

For Chrome automation, one additional manual step matters: enabling "Allow JavaScript from Apple Events" under the Developer menu. This is not something an agent can infer from HTTP behavior or discover through the Accessibility tree—it is a browser-specific gate that must be communicated to the operator.

We include this in the setup checklist rather than burying it in troubleshooting documentation, because the failure mode (AppleScript commands silently ignored) is nearly impossible to debug without knowing the setting exists.

## Takeaway

Treat permissions as product requirements, not runtime exceptions. Surface them early, gate automation on verified readiness, and make failure messages specific enough to act on. The cost of a `setup` + `doctor` preflight is seconds; the cost of a permission failure mid-flow is a wasted session and a confused operator.
