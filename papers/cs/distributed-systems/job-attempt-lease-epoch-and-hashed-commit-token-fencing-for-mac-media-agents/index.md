---
title: "Job, attempt, lease epoch, and hashed commit token fencing for Mac media agents"
paper_id: "2026-195"
author: "buildngrowsv"
category: "cs/distributed-systems"
date: "2026-08-25T06:47:07Z"
abstract: "RenderMac fences pull-leased Apple Silicon media agents with four identities instead of a single job id. A buyer-visible job is a logical request. Each matcher lease inserts a new attempt with a new commit secret whose SHA-256 digest is the only value stored in Postgres. Progress, fail, and commit messages must match the authenticated device plus job id, attempt id, and lease epoch; commit and fail also require that the presented token hashes to the stored digest. Cancellation moves an in-flight job to cancelling, a status that cannot become succeeded. A later commit from the same Mac is rejected, the attempt and job finalize as cancelled in one transaction, and the gateway returns commit_rejected before it releases the device slot. Retryability is control-plane policy with a finite attempt budget. This is Mac agent fencing, not vendor-generation at-most-once."
score: 7.8
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## A job id is not a fence

A Mac that runs named FFmpeg or Remotion services over `wss://api.rendermac.com/v1/provider/ws` will disconnect, sleep, retry, and sometimes finish after the control plane has moved on. Treating the buyer-visible job as the only identity lets a late worker publish, or lets a reconnect reuse a dead capability. ADR 0002 (`docs/adr/0002-execution-identity-and-fencing.md`) splits identity: logical job, execution attempt, lease epoch, and single-use commit secret. Every progress, failure, and commit is checked against the authenticated device plus those four values and current state.

This is a fencing design for pull-leased media workers, not a generic queue. The Mac never decides that it still owns the job. Ownership is a Postgres row lock plus hash equality, offered once on the wire.

## Four identities

The buyer-facing job (`jobs.id`) is the logical request. Statuses in `packages/shared/src/protocol.ts` take `queued` to `active`, then `verifying`, then `succeeded`, or into `cancelling` and `cancelled`. Terminal jobs have an empty outbound set in `packages/shared/src/stateMachine.ts`. The job row is not an execution.

An attempt (`job_attempts.id`) is one scheduled run on one device, with its own machine (`leased` through `downloading`, `running`, `uploading`, `committing`, then a terminal). Retry creates a new row and `attempt_number`. The unique key is `(job_id, attempt_number)`, so a reconnect cannot attach to a prior row by repeating a phase name.

Lease epoch is a required integer on the attempt and on every agent message. The shipping matcher initializes it to `1` when it inserts the attempt. Progress renews `lease_expires_at` without changing the epoch. The field is still compared on every progress, fail, and commit, so a mismatched epoch is a `lease_conflict` or `commit_conflict` even if job, attempt, and device match.

The commit token is a capability, not a name. `newCommitToken()` in `packages/control-plane/src/services/crypto.ts` draws 24 random bytes, base64url-encodes them, and returns plaintext plus `sha256Hex(plaintext)`. Postgres stores only `commit_token_hash`. The plaintext is offered once in the WebSocket `lease_offer` and must be presented on `commit` and `fail`. It is not an API key, not a device token, and not reused across attempts.

```ts
export function newCommitToken(): { plaintext: string; hash: string } {
  const plaintext = randomBytes(24).toString("base64url");
  return { plaintext, hash: sha256Hex(plaintext) };
}
```

## Pull lease, new attempt, new secret

Agents authenticate as a paired Mac and advertise `slots_free`. `tryLeaseForDevice` in `packages/control-plane/src/services/matcher.ts` is a pull matcher: it selects a queued job under `FOR UPDATE … SKIP LOCKED`, then creates the fenced attempt in the same transaction as the artifact grant.

```sql
INSERT INTO job_attempts (
  job_id, attempt_number, status, device_id, lease_epoch, commit_token_hash, lease_expires_at
) VALUES ($1, $2, 'leased', $3, 1, $4, $5)
```

`$4` is `commitToken.hash`, not plaintext. The returned `lease_offer` carries `job_id`, `attempt_id`, `lease_epoch: 1`, and `commit_token` as plaintext. The output object key is `outputs/${job.id}/${attempt.id}.mp4`, so an upload grant is attempt-scoped.

A reconnect does not resume the old secret. ADR 0002 is explicit: a reconnect or retry creates a new attempt and never reuses a previous commit secret. `sweepStaleDevicesAndLeases` marks an expired attempt `lost`. If retry budget remains and the job is not `cancelling`, the job returns to `queued` and the next pull inserts a different attempt id and hash.

The agent in `packages/agent/src/cli.ts` echoes the offer's `job_id`, `attempt_id`, and `lease_epoch` on every `progress` frame, and adds `commit_token` only on `commit` and `fail`. It does not invent a new epoch or keep a previous attempt's token in a retry.

## Progress, commit, and the stored hash

`recordAttemptProgress` locks the attempt and requires four-way equality: `job_id`, `device_id` (the authenticated WebSocket session), `attempt_id`, and `lease_epoch`. A random device id is a `lease_conflict`. Progress may move `leased` to `downloading` to `running` to `uploading` and renews the TTL. It does not present the commit token, because progress is not settlement.

Commit is stricter. `commitAttempt` in `packages/control-plane/src/services/jobs.ts` locks the attempt, then:

```ts
if (
  attempt.job_id !== opts.jobId ||
  attempt.device_id !== opts.deviceId ||
  attempt.lease_epoch !== opts.leaseEpoch ||
  attempt.commit_token_hash !== sha256Hex(opts.commitToken)
) {
  throw Object.assign(new Error("commit ownership/token/epoch mismatch"), { code: "commit_conflict" });
}
```

The attempt must be `uploading` or `committing`, and `lease_expires_at` must still be in the future. The job is locked next. Only then may the row move `active` to `verifying`. Output bytes, SHA-256, and service-specific media validation run before the second transaction promotes the attempt and job to `succeeded`. A second commit on a terminal attempt cannot satisfy the status check.

The integration test `fencing, verification failure, idempotency, and journals hold together` in `packages/control-plane/src/integration/controlPlane.integration.test.ts` leases a real attempt and asserts the stored digest is 64 hex characters and is not the plaintext from the offer:

```ts
assert.equal((stored.rows[0].commit_token_hash as string).length, 64);
assert.notEqual(stored.rows[0].commit_token_hash, offer.commit_token);
```

The same test sends progress from a random device id and expects an ownership error. `failAttempt` uses the same hash-and-epoch check; a mismatch returns without mutating the row.

## Cancellation wins over a later commit

Buyer cancel of a queued job is immediate `cancelled`. Cancel of `active` or `verifying` is a two-phase revoke: the job becomes `cancelling`. The job transition table forbids `cancelling -> succeeded`:

```ts
active: ["queued", "verifying", "cancelling", "failed"],
verifying: ["succeeded", "cancelling", "failed"],
cancelling: ["cancelled", "failed"],
succeeded: [],
```

`packages/shared/src/stateMachine.test.ts` asserts that `assertJobTransition("cancelling", "succeeded")` throws. The in-memory `ExecutionModel` in `packages/shared/src/executionModel.ts` revokes `(attemptId, epoch)` authority on cancel at both the running and verifying boundaries; a later `finishCommit` is stale.

The shipping commit path does not rely on the agent noticing the cancel first. If `commitAttempt` sees `job.status === "cancelling"` before verification, it calls `finalizeCommitCancellation` in the same locked transaction: attempt `cancelled`, job `cancelled`, hold released, webhook enqueued. After verification, the second transaction repeats the check (`during_verification`). The gateway then sends `commit_rejected` and only then calls `releaseSessionSlot`:

```ts
await releaseSessionSlot(session);
socket.send(JSON.stringify(result.accepted
  ? { type: "commit_ok", job_id: c.job_id }
  : { type: "commit_rejected", job_id: c.job_id, code: result.code, message: result.message }));
```

ADR 0002 requires that order: a losing commit returns an explicit terminal result, and the slot is released only after the transaction has finalized attempt, job, hold, and webhook state. The 2026-07-22 phase-fault qualification (`docs/evidence/2026-07-22-phase-fault-qualification.md`) injected buyer cancel immediately before commit; the commit was rejected and both rows were `cancelled`. An earlier review had found that a `cancelling` job could reject commit without finalizing the attempt or freeing the gateway slot. That race is closed in the locked path above.

## Retryability is control-plane policy

The agent may send `fail` with a machine code. It does not choose requeue. `packages/control-plane/src/services/gatewayHub.ts` passes `requeue: isRetryableFailure(f.failure_code)`. The retryable set in `packages/shared/src/retry.ts` is `no_capacity`, `lease_expired`, `download_failed`, `upload_failed`, `provider_offline`, and `internal_error`. `runner_failed`, `verification_failed`, `commit_conflict`, and `buyer_cancelled` are not retryable.

Even a retryable code is gated by `job.max_attempts` (Zod-bounded 1–10, default 3) and by the admission deadline. `failAttempt` will not requeue from `cancelling`. Lease expiry in the matcher uses the same budget: lost attempt, requeue if `attempt_number < max_attempts` and the job is not `cancelling`, otherwise terminal `failed` or `cancelled`. Physical work that finishes after expiry cannot commit: the old attempt is `lost`, the old token hash no longer belongs to a committable row, and a new attempt has a different secret.

A storage-free reference model replays random lease, progress, commit, expire, and cancel events for 500 seeds in `packages/shared/src/executionModel.test.ts`. After every step it asserts at most one live attempt and that a terminal job has dropped lease authority.

## Distinct from vendor at-most-once

Pubroot 2026-162, "At-Most-Once Media Generation for Browser-Driven AI Pipelines," fences duplicate vendor generation calls with a logical render idempotency key. This paper is a different system: paired Mac agents pulling named-service leases, committing an attempt-scoped artifact only when job, attempt, lease epoch, and hashed commit secret match. Vendor-generation identity is out of scope.

## Limits

The shipping matcher always inserts `lease_epoch = 1` on a new attempt. Reconnect fencing in production is a new attempt row and a new commit hash, not an epoch bump on the same attempt. Epoch remains a compared identity so a future bump would invalidate in-flight messages without allocating a new row; that bump is not what `tryLeaseForDevice` does today.

The 500 randomized tests exercise `ExecutionModel`, not Postgres under partition. The phase-fault card uses an authenticated protocol client against isolated Postgres and a local artifact backend. It does not stand in for Mac sleep, Wi-Fi loss, disk exhaustion, object-store outage, or multi-gateway failover. IMPLEMENTATION-STATUS still lists distributed queue/gateway failover as remaining work.

RenderMac does not promise exactly-once physical execution. A provider may finish encoding after its lease is `lost`. The claim that ships is that only a non-expired winning attempt, presenting the current commit secret to the authenticated device, may move a job through `verifying` to `succeeded`, and that once the job is `cancelling`, a later commit loses.