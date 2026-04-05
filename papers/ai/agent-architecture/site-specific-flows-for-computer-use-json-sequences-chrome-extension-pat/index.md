---
title: "Site-Specific Flows for Computer Use \u2014 JSON Sequences, Chrome Extension Path, and Multisurface Patterns"
paper_id: "2026-062"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-04-05T03:15:40Z"
abstract: "This case study explains how we layer general VCC primitives into repeatable website and vendor flows. We maintain JSON sequence drafts for high-value paths such as analytics admin, tag manager, DNS, and email vendor consoles. We default to accessibility-tree control for Safari and Chrome, and we escalate to the MV3 Chrome extension and localhost bridge when the page needs DOM-grounded discovery or visible-text diff that AX alone does not expose cleanly."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
---

## From primitives to playbooks

Raw `discover` and `click` are building blocks. Production work packages them into ordered sequences: locate the window, run preflight doctor checks, execute menu steps such as enabling JavaScript from Apple Events when Chrome is involved, then walk a known path with `read-page`, `lookup`, and `click-text` to survive layout churn. We store these as JSON drafts under a flows directory so operators and agents share the same source of truth instead of re-deriving steps from memory.

## When AX is enough

Most marketing and admin surfaces expose sufficient Accessibility nodes for buttons, links, and form fields. For those, we stay on the standard loop and avoid pulling in extension or OCR paths. That keeps latency and context size lower and reduces moving parts in CI or remote sandboxes.

## When we add the Chrome extension path

We reach for the bundled MV3 extension when tasks involve `chrome://extensions`, unpacked extension reload workflows, or DOM-level probes that pair with a localhost HTTP bridge. Separately, `vcc chrome-diff` compares visible innerText line deltas between ticks for cheap “did the copy change?” polling; we still run `discover` or `read-page` when we need indices for clicks. We do not treat line diff as a substitute for structured discovery.

## Site-specific examples in practice

Our draft sequences include navigation patterns for cloud dashboards, DNS and email routing panels, and analytics measurement setup. The filenames encode browser and intent—for example Chrome versus Safari variants when account switching or profile behavior differs. Sequences are versioned as JSON so we can diff them when a vendor moves a button label or adds a consent interstitial.

## Multisurface coordination

Real operations often combine IDE terminals, browsers, and native dialogs. VCC supports native menu paths and file-picker dialogs for upload flows. Those steps are inherently sequential and human-visible; we document them beside browser steps so agents do not assume every control lives in the page AX tree.

## Failure modes we plan for

TLS interstitials, consent banners, and account-picker modals appear as separate layers of state. Our sequences include recovery branches where we dismiss known interstitials or re-run account-switch steps. If a sequence is stale, the first symptom is usually drift in `window_ref` or failed `wait` targets; we fix the JSON and re-run rather than improvising one-off shell hacks in production.

## Limitations

Vendor UIs change without notice. Automated peer review should treat these flows as operational documentation tied to a repository revision, not universal guarantees for every tenant configuration.