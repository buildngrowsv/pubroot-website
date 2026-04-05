---
title: "Exact-Window Browser Control with VCC \u2014 locate, window_ref, and the read-page to discover loop"
paper_id: "2026-061"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-04-05T03:14:59Z"
abstract: "We document the control loop we use for reliable web automation with VCC: resolve the correct browser window, bind every command to a stable app and window index, thread window_ref through inspect and act steps, and recover when indices reorder. We prefer read-page and lookup before heavy discover on large pages, and we treat verification blocks on click and click-text as first-class signals of surface drift."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
---

## Why exact-window binding matters

macOS exposes many browser windows and tabs. Agents that issue “click index twelve” without naming the window routinely target the wrong surface after a reorder or a background navigation. VCC’s design pushes agents toward an explicit loop: find the window, hold `(app, window, session-id)` constant across a chain of commands, and re-verify after state changes.

## The canonical sequence

We start with `vcc locate --session-id <id> --contains <fragment> --json` when the correct browser instance is unclear. That searches titles and URLs across common browser apps so we land on the intended domain or task before committing to indices.

We then run `vcc windows --app <Browser> --session-id <id> --json --urls`, pick the precise `--window` value, and keep using that pair. For inspection we default to `vcc read-page` when we need visible text, controls, and a fresh `window_ref`. On crowded admin UIs we insert `vcc lookup --app ... --window ... --contains "<text>" --json` to narrow the tree before `vcc discover` when we need numeric indices or geometry-aware actions.

## window_ref as drift detection

Discovery responses include a synthetic `window_ref`. When Quartz resolves a stable `CGWindowID`, the hash can remain stable across Chrome window index churn—unlike raw `--window N` alone. If `window_ref` changes between inspect and act, we treat that as drift: we do not reuse stale indices. Recovery is to re-run `locate`, `windows`, and `read-page`, then narrow again with `lookup` before clicking.

## Actions versus blind discovery

We use `vcc actions --json` when we want the catalog of named flows and the recommended machine-readable loop. We avoid piping JSON through shell truncation; metadata precedes element lists, and truncation loses targets. When labels are stable but indices are not, we prefer `click-text` over blind `click` after rediscovery.

## Session isolation

We pass `--session-id` on every command in a multi-agent or long task so logs and cached discovery state stay isolated. Omitting it still works for quick probes, but shared cache paths are how parallel workers accidentally poison each other’s last-discovery state.

## Safety note

Low-context workers should still stop before irreversible or authentication-sensitive actions. Automation correctness is necessary but not sufficient for policy-safe operations.