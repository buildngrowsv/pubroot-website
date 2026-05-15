---
title: "Borrowing Eval Harness Boundaries for Production Agent Recovery"
paper_id: "2026-166"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-05-15T09:34:46Z"
abstract: "Production agent systems often share core planner and dispatcher code with eval harnesses, yet production failures are harder to recover because the runtime lacks eval-style run boundaries. GenFlick's chat recovery audit found that production already had provider retry, phase retry, stream timeout, dispatch recovery, deduplication, and observability. The eval harness was better at explicit run status, complete artifact capture, no-media side-effect declaration, deterministic quality checks, and operator console semantics. This article argues that production agent recovery should borrow those harness contracts: durable turn status, phase checkpoints, intended side effects, replayable artifacts, and stale-run finalization. The lesson generalizes to multimodal agents, coding agents, and tool-using assistants."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from GenFlick production chat recovery audit notes and no-media agent-flow harness documentation."
---

## Problem

Production agent failures are often not failures of reasoning alone. They are failures of run boundaries.

In GenFlick, a production chat incident showed a recoverable AI-director failure where the user interface kept stale "building" affordances, retry appeared to create a new assistant surface, and it was not obvious which phase had failed or whether media generation should continue. The interesting finding was that production and evaluation shared much of the same core agent path. The safer behavior in eval came from wrapper contracts, not a fundamentally different agent.

## Shared Core

The no-media agent-flow harness calls the same major surfaces as production:

- planner
- phase executor
- streaming action parser
- action dispatcher
- project-context builder
- dispatch-result merge logic

This is good architecture. It means evals are exercising real production behavior for planning and project mutation.

But shared code is not enough. Production still has to decide when a turn is running, complete, failed, stale, recoverable, or partially dispatched. The eval harness had stronger answers to those questions.

## What Production Already Had

GenFlick production already had several important protections.

The client retried the initial chat request for transient network and 5xx failures before consuming the stream body. Each phase provider call had retry logic with backoff before visible deltas were emitted, which avoided duplicating visible assistant output after a partial stream.

The phase executor retried failed phases, marked failures, and continued later phases when possible. The browser stream reader used a progress-based timeout rather than a fixed wall-clock cutoff. Stream-error recovery could route already-dispatched project changes into image, video, reference, poster, and frame-generation queues even when the stream failed before happy-path reconciliation.

Dispatch results were deduplicated for idempotent queues such as scene ids, character names, set names, prop names, and posters. Production also persisted useful observability in API logs, chat turn logs, generation rows, request ids, planner metadata, phase execution logs, assistant raw response, parsed actions, dispatch summaries, and prompt provenance.

Those are real protections. The gap was that production still relied heavily on the browser stream lifecycle and final client reconciliation to make partial work legible.

## What The Eval Harness Did Better

The eval harness had explicit run status:

- running
- passed
- failed
- timed out
- stopped

Each run had a timeout, declared outputs, and a durable directory of artifacts. A production chat turn needs a similar durable state machine. A stale stream should become a recoverable server-side state, not an ambiguous browser condition.

The harness captured full artifacts:

- project before
- context before
- provider input per phase
- raw provider output per phase
- aggregated assistant output
- SSE events
- phase outputs
- parsed actions
- dispatch result
- skipped media queue
- project after
- context after
- quality rubric

Production logs many of these concepts, but not always as one replayable per-turn bundle. That makes incidents harder to reconstruct.

The harness also had a no-media mode. It could verify planned side effects without spending image or video credits. Production cannot skip media in normal user flows, but it can borrow the idea of declaring intended side effects before executing them. That declaration is the bridge to idempotency and recovery.

Finally, the harness ran deterministic quality checks after dispatch. Production did not yet have an equivalent lightweight integrity audit that could say, for example, "nine phases were planned but only one landed" or "video generation was queued but no route fired."

## Production Pattern

A production agent turn should have a durable run record with:

- turn id and request id
- planner output
- phase list and status per phase
- provider inputs and outputs, redacted as needed
- parsed action batches
- dispatch result
- intended side effects
- media queue ids or idempotency keys
- terminal status
- recoverability classification

The server should be able to finalize stale runs. If the stream stops but dispatched actions exist, the run can be marked partially completed and recovery can continue media routing. If no usable actions exist, the run can be marked failed with a retry entry point. If a phase failed but later phases completed, the UI should show that exact state rather than a generic spinner.

## Operator Console Semantics

The eval console offered a model for operations: start, stop, watch, inspect, and link to artifacts. A production admin surface for agent turns should expose:

- current phase checkpoint
- intended side effects
- parsed actions
- dispatch summary
- media jobs created
- stale or timed-out status
- retry-from-checkpoint options
- dry-run recovery against a project snapshot

This is not just for internal comfort. It affects user experience. Clear operator state makes it easier to surface precise user messages, such as "the story and scene updates landed, but video generation did not start" instead of "something went wrong."

## Generalization

The pattern applies beyond AI video. Coding agents, support agents, browser-use agents, data-analysis agents, and multimodal creative agents all need durable run boundaries.

Tool-using agents frequently complete some side effects before failing. Without a turn-level ledger, retry can duplicate work, lose partial progress, or confuse users. With a ledger, the system can separate reasoning failure, stream failure, tool failure, dispatch failure, and UI reconciliation failure.

## Conclusion

Eval harnesses are not only for scoring quality. They are prototypes for production recovery contracts. GenFlick's audit found that the eval path was safer because it had explicit status, artifact capture, side-effect declarations, deterministic checks, and operator-visible run semantics. Production agent systems should promote those harness ideas into runtime infrastructure.