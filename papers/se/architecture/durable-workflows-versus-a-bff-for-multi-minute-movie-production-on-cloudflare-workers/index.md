---
title: "Durable workflows versus a BFF for multi-minute movie production on Cloudflare Workers"
paper_id: "2026-185"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-08-25T06:38:09Z"
abstract: "Interactive Next.js on Cloudflare Workers is a capable backend-for-frontend, but it is a poor execution environment for multi-minute AI movie production. GenFlick\u2019s 2026-06-14 Voice Director ADR records a concrete failure: a 30-scene finalize ran for about 81 seconds inside one browser-held HTTP stream, the Worker died before any video rendered, workspace status reset to idle, and the client showed a non-recoverable error with zero videos. The replacement architecture treats the OpenNext Worker as a command plane. The browser (or any API client) posts a typed command with a client command id, idempotency key, and a stable JSON dedupe hash. Durable jobs then own leases, heartbeats, provider receipts, and UI projection. Cloudflare Queues carry only `{jobId}` pointers; consumers re-read the Neon job row so duplicate delivery cannot double-execute. A KV-gated minute cron remains lost-message insurance, not the primary drain. This case study describes the live command/job/executor contract in `app/src/lib/workflows/` and the remaining queue-primary gaps the same documents still list. It is not a provider-routing paper, not a billing paper, and not an at-most-once vendor-call paper."
score: 7.8
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## The stream that could not outlive the tab

GenFlick Studio is a Next.js application deployed through OpenNext on Cloudflare Workers. For interactive reads, short mutations, and streaming chat, that Worker is a conventional backend-for-frontend. For movie production it is not.

On 2026-06-14 we recorded a Voice Director finalize that made the distinction unavoidable. A user approved a 30-scene storyboard. `POST /api/tools/advanced/voice-director/finalize` opened one long NDJSON `ReadableStream` and, inside that single Worker request, sequentially upscaled a reference sheet, upscaled N grids, and rendered N videos. For a 30-scene film that is 31 image upscales plus 30 video renders: 61 provider round-trips tethered to one browser HTTP stream. The finalize ran for about 81 seconds, the Worker or stream died before any video rendered, the cloud project reset `finalizeStatus` to `idle`, and the browser—never having received a terminal `done` or `error` event—showed “Generation ended before it finished. Please try again.” Zero videos. The storyboard was intact. The ADR classifies this as a fragile-architecture failure, not a content failure.

Recovery at the time was a four-second workspace poll that only helped a *refreshed* tab and was disarmed in the same tab when the stream died. There was no durable run id to resume.

That incident is the forensic reason the later shared workflow substrate exists. The rest of this paper is the contract that replaced “keep the request alive.”

## A BFF is not the execution environment

The 2026-06-16 orchestration plan names the split directly: the interactive Worker accepts intent and returns receipts; request lifetime and `waitUntil()` are not the durable engine. The browser is an observer plus optional client-task worker. SSE is a presentation channel, not allowed to own execution after a `202 Accepted` receipt.

Two shortcuts were rejected. A Neon table plus KV-gated minute cron (Movie Studio V2’s earlier `agent_generation_jobs` drain) is durable but slow: 0–60 second pickup and a stall if the KV work-pending signal is lost. A pure queue cannot answer run status, express a DAG, or rebuild UI after reconnect. Cloudflare Workflows was considered for finalize and deferred: unbound in the account, limited step output and in-instance parallelism, and it would have split storyboard and finalize onto two models.

The hybrid that shipped as the target model is therefore:

- Neon holds runs, jobs, attempts, receipts, and DAG eligibility.
- Cloudflare Queues dispatch eligible work as pointer messages.
- The OpenNext `fetch` handler remains the BFF and the request-scoped place where Drizzle/Hyperdrive and Next `headers()` actually work.
- A KV-gated cron sweeper republishes orphans.

Voice Director already ran this shape as a product-specific pipeline. `app/src/lib/workflows/` generalizes it: typed commands, a job ledger with leases and attempt rows, a pointer queue client, a control executor, and adapters that project UI status from those rows.

## Commands accept intent; they do not run media

User-visible mutations that can outlive a tab become rows in `workflow_commands`. The kinds are closed:

`new_turn`, `follow_up`, `steer`, `retry`, `cancel`, `generation`, `utility`, `export`.

Statuses are a small machine: `accepted` → `attached` / `scheduled` / `running` → `applied` / `completed` / `failed` / `cancelled` / `superseded`. `createOrGetWorkflowCommand` takes a client `clientCommandId`, hashes canonical JSON of kind, project, chat, text, targets, payload, and attachments, and stores `workflow-command:{actorUserId}:{clientCommandId}`. Insert uses `onConflictDoNothing`; a replay returns the same row. A reused client command id with a different hash is rejected.

That uniqueness unit is *intent*, not a vendor generation id. Collapsing two Generate All clicks into one provider call is a different paper. Here the question is whether the server accepted a command that survives the HTTP stream.

After accept the BFF is short: persist the command, attach a run, mark dependency-free jobs eligible, enqueue `{ jobId }` pointers, return ids and poll URLs. The Voice Director finalize sketch is the same shape: insert the run and N jobs, send pointers, return `{ pipelineRunId }` in well under a second.

## Jobs own leases, heartbeats, and receipts

`workflow-jobs-service.ts` stores the executable unit: idempotency key, payload hash, dependencies, attempt count, `leaseOwner` / `leaseExpiresAt` / `heartbeatAt`, and receipt columns (`providerRequestId`, `providerStatus`, `providerAssetUrl`, `providerResultPayload`). Attempts are a child table—one immutable row per claim.

`executeWorkflowControlJob` treats queue fields as hints. The executor comment is explicit: “Legacy queue-pointer hints. The durable job/run rows are authoritative.” The first read is `getWorkflowJobById(input.jobId)`. A missing row is `skipped`, not a retry storm.

A claim is a compare-and-set. Only due `ready`, `queued`, or `retry_scheduled` jobs below `maxAttempts` move to `leased`, with a random `leaseOwner` (`workflow:{uuid}`), expiry, heartbeat, and incremented attempt count. A second delivery sees `not_claimable` and acks.

Leases are shorter than the longest provider call. The default profile is a 5-minute lease and a 45-second heartbeat (12 minutes for LLM phases; 3 minutes for poll-or-reconcile). The executor heartbeats around the handler. A dead isolate expires; a live one renews. Expired leases become `retry_scheduled` or terminal `lease_expired_attempts_exhausted`, and the attempt row is closed.

Provider success is persisted *before* project apply. A crash after a vendor result is receipt replay, not a second vendor call. UI status is projected from run/job/attempt rows. `AGENTS.md` states the same rule: anything that can outlive the request needs a job id, lease, heartbeat, attempts, and a sweeper that can distinguish still-running from terminal success from retryable failure from terminal failure.

Unchanged dependency waits call `quietRescheduleWorkflowDependencyWait` and bump `nextAttemptAt` without a new attempt row or parent recompute. Waits that exceed the stall window become `blocked` instead of looping every few seconds.

## Pointers, loopback, and the sweeper

Queue messages are not the work. `enqueueWorkflowControlJob` sends:

```ts
const message = {
  schemaVersion: 2 as const,
  jobId: input.jobId,
  enqueuedAt: new Date().toISOString(),
};
```

`runId`, user ids, and job kind stay on the Neon row. A source-guard test asserts the client does not put `runId` on the message, that the executor reloads by `jobId`, and that `worker-with-scheduled.mjs` posts `{ jobId }` to `/api/internal/workflow-control-jobs/execute`.

OpenNext emits `fetch` only. Cron and queue events have no Next request-scoped AsyncLocalStorage, so the wrapper loopback-fetches an internal execute route. Ack versus retry follows that HTTP outcome; the batch is awaited (not `waitUntil`) so the runtime sees the decision:

```js
body: JSON.stringify({ jobId }),
// ...
if (response.ok) {
  message.ack();
} else {
  message.retry();
}
```

A missing `jobId` is acked, not retried, so a poison pointer cannot spin the queue.

Cron is insurance. `listDispatchableWorkflowJobs` re-selects `ready` / `retry_scheduled` / stale `queued` rows after a two-minute visibility timeout. The ADR’s sweeper is the same idea: re-send eligible jobs with no in-flight message and reset orphaned leases. KV is a work-pending signal, not job truth. The queue client arms it on live sends and on a missing binding so production repair still runs, but not when the queue is intentionally disabled—a local isolate sharing production Neon previously woke the production minute cron.

The intended user-visible sequence is therefore:

```text
browser/API  --command-->  BFF (OpenNext fetch)
                          insert command + run + jobs
                          QUEUE.send({ jobId })
                          202 + poll URLs
queue consumer            loopback POST /execute { jobId }
executor                  re-read row, CAS lease, heartbeat,
                          persist receipt, apply, enqueue dependents
browser                   GET status from ledger (tab may be gone)
cron sweeper              re-pointer lost eligible / expired leases
```

For the 30-scene finalize the ADR expects 61 independently retried jobs, about `max_concurrency` in flight, with the tab free to close.

| Failure | Browser-held stream | Durable command/job |
|---|---|---|
| Worker or tab dies mid-finalize | Stream ends; `finalizeStatus` idle; non-recoverable UI; zero videos | Job row remains; queue or sweeper reclaims |
| Duplicate queue delivery | Not modeled | CAS lease; second delivery is `not_claimable` |
| Lost queue message | Not modeled | Cron re-pointers after visibility timeout |
| Crash after vendor success | No receipt; work looks unfinished | Receipt on the job before apply |
| Unchanged dependency wait | Not modeled | Quiet reschedule, then `blocked` |

## Limits

This is not a claim that every GenFlick surface is queue-primary, and it is not a claim that jobs never get lost.

The 2026-06-16 plan and V2-first tracker still list remaining gaps. V2 media dispatch and accepted-prompt execution have queue clients and internal execute routes, but production flags default off until a non-local Cloudflare Queue consumer proves delivery; cron remains fallback. V2-3 still records missing non-local consumer proof and provider-complete rows that can stick in `applying`. V2-7 and V2-10 keep queue-primary off for real users until a non-local executor proves submit, tab close, cancellation, media drain, and cron retirement. V2-11 (staging soak and rollback) was `not_started`. The open backlog still asks to prove queue-owned accepted prompt execution outside local loopback.

Voice Director remains a physically separate reference pipeline. The shared `workflow_*` substrate rolled out first behind V2 adapters; V1 Studio still has browser-owned chat dispatch. Remotion jobs in a `globalThis` Map are remaining in-memory state. Cloudflare Workflows is a future evaluation, not the engine. Quiet-reschedule exists because an earlier wait loop wrote thousands of attempt rows; bounded retries are required.

What we do claim, at the cited commit, is narrower: the interactive Worker is the BFF; multi-minute production is typed commands plus durable jobs (lease, heartbeat, receipts) plus queue pointers plus a KV-gated sweeper; and the 81-second finalize stream death is the ADR’s evidence that keeping the HTTP request open is not an execution strategy.