---
title: "At-Most-Once Media Generation for Browser-Driven AI Pipelines"
paper_id: "2026-162"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-05-15T09:33:11Z"
abstract: "Browser-driven media generation pipelines can accidentally launch duplicate paid vendor calls when two tabs, browsers, or recovered sessions observe the same persisted work queue. GenFlick's Generate All incident analysis led to a two-layer architecture: server-side idempotency for each logical render request, plus a server-backed lease for queue ownership. The idempotency layer claims a deterministic logical key before credit hold or provider call; duplicate requests return the existing running or completed state. The lease layer improves user experience by making one browser the active queue dispatcher, but correctness remains on the server. This pattern generalizes to AI image, video, audio, and document generation systems where client retries and cross-device hydration can otherwise multiply costs."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from GenFlick duplicate-generation incident notes and idempotency design plans. No production code was changed for this Pubroot packaging step."
---

## Problem

Many AI media products let the browser drive a queue. The client stores user intent, scans for clips or assets that are ready to generate, and calls a server route for each paid provider job. This works in one tab. It becomes dangerous when the same user opens the project in a second tab, a second browser, or a recovered session after refresh.

GenFlick's Generate All investigations found this exact shape. The project had a persisted finish queue, but dispatch guards lived in browser memory. A fresh browser had empty in-flight refs, hydrated the project, saw the finish queue still running, and submitted the same video generation work again. The server route then performed credit hold and provider calls without first claiming a logical render idempotency row.

The result is not just duplicate UI state. It can become duplicate vendor calls, duplicate credit holds, and duplicate takes for the same clip.

## Design Goal

The system should make one logical render happen at most once while preserving legitimate retries after real failures.

This does not require exactly-once distributed execution in the theoretical sense. It requires a server authority that can collapse duplicate browser requests into one logical operation and return the current state of that operation.

## Layer 1: Logical Render Idempotency

The central mechanism is a server table representing one logical media render request.

For video, the logical key should include the user, project, clip, provider, prompt hash, start-frame hash or URL hash, end-frame hash or URL hash, reference input hash, duration, quality, aspect ratio, resolution, audio settings, and seed state. The key must change when the user legitimately changes the render request, but it must remain stable when two browsers submit the same queue item.

A simplified key shape is:

```text
video:v1:
  user_id:
  project_id:
  clip_id:
  provider:
  prompt_sha256:
  start_frame_sha256_or_url_sha256:
  end_frame_sha256_or_url_sha256:
  reference_inputs_sha256:
  duration:
  quality:
  aspect_ratio:
  resolution:
  generate_audio:
  seed_or_no_seed
```

The server also stores a `request_hash` from the normalized full request body. If a duplicate logical key arrives with a different request hash, the safest response is a conflict because either normalization or key derivation is wrong.

## Claim Before Cost

The order of operations matters.

The generation route should authenticate, validate, compute the logical key and request hash, and attempt to insert the idempotency row before holding credits or calling a vendor. Only the inserted or explicitly taken-over request may proceed to billing and generation.

On conflict:

- If the existing row is completed and the request hash matches, return the stored result with `deduped: true`.
- If the existing row is running and not expired, return the running state with `deduped: true` and a retry hint.
- If the existing row failed, allow retry only under an explicit retry policy or a new attempt suffix.
- If the existing row expired, atomically take it over, increment an attempt counter, extend expiration, and proceed.

This mirrors a common idempotent payment pattern: insert the request record first, then perform the expensive or irreversible side effect.

## Layer 2: Queue Lease

Idempotency protects the server from duplicate paid work. A queue lease improves the user's visible experience by preventing multiple browsers from trying to drive the same queue.

The lease should also be server-backed. Project JSON alone is not a reliable authority because optimistic saves from different tabs can race. A table keyed by project id can store queue id, run id, owner id, heartbeat time, expiration, and status.

The active browser acquires the lease, heartbeats while dispatching, and releases or expires it when done. Other browsers observe progress instead of launching work. If the owner disappears, a later browser can take over after expiration.

The lease is not the correctness boundary. It is a coordination and UX boundary. The idempotency row remains the final protection against duplicate vendor calls.

## Idempotent Take Writes

Provider job ids are not enough for deduplication. If duplicate requests already escaped to the provider, the same logical render may produce two vendor job ids.

Completed media takes should carry `generation_request_id` or `generation_logical_key`. The project write path should update an existing take if any of these match:

- take id
- provider job id
- generation request id
- generation logical key

This prevents the project timeline from accumulating duplicate takes even in retry or recovery edges.

## Failure Handling

The idempotency row should store enough state to support recovery:

- status
- provider job id
- video or media URL
- error
- held and charged credits
- estimated cost
- vendor usage summary
- response summary
- expiration

When a server crashes after credit hold but before final project write, the row gives operators and recovery code a durable checkpoint. When a provider call fails with a retryable error, retry policy can be represented explicitly rather than inferred from browser state.

## Why Browser-Only Guards Fail

Browser refs, local storage, BroadcastChannel, and in-memory queues are useful for smoothing one user's current session. They are not enough for correctness.

They do not span browsers, devices, private windows, or hard refreshes. They can be lost during reload. They can be reset by state recovery code. They can disagree with the server's persisted project state.

The server route that calls paid providers is the choke point. It must own idempotency before cost is incurred.

## Generalization

This architecture applies to AI image generation, video generation, music generation, document export, speech synthesis, and any agentic pipeline where a client submits expensive side effects.

The core rule is simple: compute a logical work identity from the normalized request, claim that identity in durable storage, and only then perform the paid or irreversible side effect. Client leases and UI coordination are valuable, but they are secondary.

## Conclusion

Browser-driven queues are convenient until recovery and multi-tab usage turn them into duplicate side-effect launchers. GenFlick's incident analysis points to a practical pattern: server-side logical idempotency for every paid render, plus a server-backed queue lease for ownership and observability. The combination preserves legitimate retries while preventing duplicate costs from normal user behavior.