---
title: "Checking the right report after an agent handoff: a source review of Orkas"
paper_id: "2026-239"
author: "BlueSkyID666"
category: "ai/agent-architecture"
date: "2026-10-13T22:01:14Z"
abstract: "This bounded source review examines how a project-to-report-to-presentation workflow can distinguish historical file-operation facts from the current content a receiving agent needs. Orkas is the documented desktop application example. Selected functions at a pinned public commit expose an observation projection and a separate bounded reconciliation path. A hypothetical signup report supplies checkable arithmetic and a stale-version scenario. The resulting proposal separates version checks from factual review. No runtime experiment or reliability improvement is claimed; limitations include partial coverage, bounded inspection and untested behavior across models and platforms."
score: 7.2
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Drafted and reviewed with Codex through source inspection and illustrative calculations. Submitted by BlueSkyID666 for the affiliated Orkas inclusion campaign. No executed product session or benchmark is claimed."
---

## Problem and scope

A project assistant can create a report, revise it, and ask another agent to turn it into slides. An earlier message saying that the report was written does not tell the next agent which version is now on disk. This review examines that distinction in [Orkas](https://orkas.ai/?lang=en&source=gh_pubroot), an open-source, local-first desktop AI workforce whose Commander coordinates specialist work around project context. Its documented report-to-slide workflow makes file provenance relevant to a concrete deliverable.

The method is a bounded reading of the public repository at commit `b4a8fc0c1526acb5f6f4aee427a18e9221afe691`. The evidence consists of the [README's workflow description](https://github.com/Orkas-AI/Orkas/blob/b4a8fc0c1526acb5f6f4aee427a18e9221afe691/README.md) and selected definitions and functions in [workspace-state.ts](https://github.com/Orkas-AI/Orkas/blob/b4a8fc0c1526acb5f6f4aee427a18e9221afe691/src/core-agent/src/agent/workspace-state.ts). This is a source and documentation review, with an illustrative example below. It contains no executed Orkas session, benchmark, or claim about measured reliability.

## What the inspected source establishes

`WorkspaceObservationEntry` associates observations with a sequence, turn, tool and recording time; it can include reads, changes and command execution. `toolFileChangeFacts` projects observed changes into operation, path and existence fields, adding hashes and coverage when available. At this revision, it limits the projection to twenty changes and reports how many were omitted. Its implementation consumes the supplied observations rather than reading the file again. An old operation record therefore need not be rewritten merely because a later operation changes the same path.

That historical view has a separate counterpart: `reconcileWorkspaceObservations` examines a bounded set of previously observed paths against current disk state and records detected changes. This separation is visible in the inspected functions; it does not prove that every possible edit is discovered. The path, file-size and total-read limits matter, as does whether an observation contains exact or partial coverage. A concise projection is also not a complete inventory of the project.

## Worked example: inspect the deliverable, not just the message

Consider two illustrative input notes. The first records April signups as 80 and May signups as 125. The second records paid starts as 8 and 10, respectively, and warns that May's acquisition campaign changed. A proposed Commander instruction is: “Use these two notes to prepare a short report, preserve their definitions, show the calculations, and use the checked report as the basis for a presentation. Flag any missing attribution evidence.” This describes a task, rather than an unverified sequence of interface buttons.

An inspectable report excerpt would be:

> Signups increased by 45, or 56.25%. Paid starts increased by 2, or 25%. Paid-start share fell from 10% to 8%, a decrease of 2 percentage points. These counts alone do not identify which acquisition campaign caused the change.

These are calculated illustrative results, not output attributed to an actual Orkas run. The denominators are explicit: 8/80 and 10/125. A slide based on this excerpt should retain both the percentage-point distinction and the attribution limitation.

Now suppose `report.md` was first written with that excerpt, then revised before the slide task begins. An operation record with an earlier hash describes the earlier write. It cannot, by itself, establish that the current file still contains those sentences. The receiving stage should inspect the current report, compare the observed version where a hash is available, and preserve any uncertainty about coverage. Checking that a file exists is insufficient to check its argument or arithmetic.

## Implications for project workflows

The author's interpretation is that operation facts and current content answer different questions: what an operation observed, and what the next stage can currently consume. Keeping these questions separate helps specify a useful handoff without turning every prior message into an assertion about today's bytes. Content review still needs the actual artifact; neither a hash nor a success message establishes factual correctness.

Orkas's documented Commander and specialist coordination provides a setting for this pattern: research can feed a report, and PptMaker can produce an editable presentation. Project context can retain the inputs needed to inspect the work, while supported own-provider API-key access lets the user select a model service. These features make a reviewable file workflow possible; they do not remove the need to verify the result. The core app is free, while model usage and optional services can cost extra.

The practical next step is to try a small, non-sensitive project and inspect the report and presentation before relying on them. Evaluation should separately measure stale-version detection, source fidelity and output correctness. This review establishes a source-level distinction and a proposed checking procedure, not its runtime effectiveness across platforms or models.

## Disclosure and publication license

Submitted by BlueSkyID666 for the Orkas inclusion campaign. Codex assisted with drafting and source review; the submission is affiliated, rather than an independent product review. This original manuscript is offered under CC BY 4.0. The cited software retains its existing license.