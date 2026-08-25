---
title: "Browser-First Leased Client Tasks with Fenced Cloud FFmpeg Fallback"
paper_id: "2026-189"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-08-25T06:41:58Z"
abstract: "Interactive AI video products can run frame extraction, continuity tails, timeline stitch, and export in the already-open browser. That path is cheaper and lower-latency than a cloud FFmpeg sidecar, but a tab is not a durability owner: reload, sleep, crash, or a second tab can leave a half-finished artifact with no server identity. GenFlick treats browser execution as a leased client task attached to a durable workflow command. The server creates a stable task id from run, kind, target, and source hash before offering work. A tab leases that row with owner id, heartbeat, deadline, and a signed upload session. Cloud FFmpeg starts only after explicit browser failure, unsupported capability, or atomic lease expiry into fallback_started. Completing a task is a compare-and-set on the live lease, so a late browser result cannot overwrite an accepted fallback. This is execution fencing, not vendor-generation idempotency (Pubroot 2026-162). The canonical policy lists ten required regression cases; divergence between that policy and code is a regression."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Problem

Studio media work is not all vendor generation. Frame grabs, continuity tails, timeline stitch, and export can run in the already-open tab with `video`/canvas, WebCodecs, Remotion, or MediaRecorder. That is cheaper than a Cloudflare FFmpeg sidecar. It is also a trap if the tab is treated as the owner. Reload, sleep, crash, or a second tab can leave a half-finished blob with no server identity, while the UI reports failure as if the movie job itself died.

The product rule in `docs/BROWSER-FIRST-MEDIA-PROCESSING-AND-CLOUD-FFMPEG-FALLBACK-RULES.md` is explicit. Use the browser first when it is open, capable, and can reach the source. Do not let it own durability. The server creates a durable command and a client-task row first. The browser then leases that row. Cloud FFmpeg is the fallback after explicit failure, unsupported capability, or atomic lease expiry — not a speculative second copy.

## Distinct from vendor at-most-once

Pubroot 2026-162, "At-Most-Once Media Generation for Browser-Driven AI Pipelines," is about duplicate *vendor* calls. Two tabs hydrating the same Generate All queue could each hit a paid image or video provider. The fix was a logical render idempotency key claimed before the provider call, plus a queue lease as UX coordination. Correctness sat on the idempotency row, not on which browser was dispatching.

This paper is a different fence. The side effect here is *execution*: who extracts the frame, stitches the timeline, or packages the export. Browser and cloud share one semantic command. Only one executor may apply the artifact. A late browser upload must not replace an accepted FFmpeg result. Vendor generation identity (clip, take, provider attempt) is out of scope.

## Durable ownership before browser work

The policy lists routing families from interactive single-frame extraction to unattended batch work that should skip the browser. The shared contract is: create the command and stable semantic ID first; represent browser execution as a leased client task with owner tab, heartbeat, deadline, source hash, target fence, and expected artifact contract; persist output through authenticated ingress before marking complete; start cloud fallback only after eligible failure or atomic lease expiry; never let a late browser result overwrite a cloud result or a newer target epoch.

Client-task rows live in `workflow_client_tasks`, implemented by `app/src/lib/workflows/workflow-client-tasks-service.ts`. Status is a closed set:

```ts
export type WorkflowClientTaskStatus =
  | "available"
  | "leased"
  | "completed"
  | "failed"
  | "fallback_started"
  | "cancelled";
```

IDs are deterministic at the (run, kind, target, source hash) grain, so upsert is idempotent across retries:

```ts
export function createDeterministicWorkflowClientTaskId(input: {
  runId: string;
  taskKind: string;
  targetId: string;
  sourceHash?: string | null;
}): string {
  const hash = createHash("sha256")
    .update(input.runId).update("\0")
    .update(input.taskKind).update("\0")
    .update(input.targetId).update("\0")
    .update(input.sourceHash ?? "")
    .digest("hex")
    .slice(0, 32);
  return `wfc_${hash}`;
}
```

`workflow-client-tasks-service.test.ts` asserts the `wfc_[a-f0-9]{32}` shape and that a different target, run, kind, or source hash yields a different id.

## Lease, heartbeat, and compare-and-set complete

`leaseWorkflowClientTasks` claims `available` rows or leases whose deadline has already passed. Default lease is two minutes, clamped to 15 seconds–10 minutes, at most ten tasks per call. The claim stores `leaseOwnerTabId`, `leaseExpiresAt`, and a `signedUploadSessionId` used as the upload token.

Heartbeat, fail, and complete all go through the same mutation predicate: the row must still be `leased`, owned by this tab, and bound to this session.

```ts
function activeLeaseMutationClause(input: {
  taskId: string;
  projectId: string;
  leaseOwnerTabId: string;
  signedUploadSessionId: string;
}): SQL {
  return and(
    eq(workflowClientTasksTable.id, input.taskId),
    eq(workflowClientTasksTable.projectId, input.projectId),
    eq(workflowClientTasksTable.status, "leased"),
    eq(workflowClientTasksTable.leaseOwnerTabId, input.leaseOwnerTabId),
    eq(workflowClientTasksTable.signedUploadSessionId,
      input.signedUploadSessionId),
  )!;
}
```

That is the two-tab and late-result fence. `completeWorkflowClientTask` returns `null` unless the compare-and-set matches. The Movie Studio V2 adapter maps that to `stale-or-not-leased` and does not overwrite task state. Heartbeat from the wrong tab is the same no-op (`workflow-client-tasks-lease-service.test.ts`). Continuity completion additionally validates that the report includes the leased target clip and required frame, video-tail, and audio-tail artifacts before the compare-and-set (`movie-studio-v2-client-task-leases.ts`).

## Fallback starts only after the lease is fenced

A sweeper calls `markExpiredWorkflowClientTasksFallbackStarted`. It selects `leased` rows with `leaseExpiresAt < now` (or a null deadline), then updates only while status is still `leased`. Promotion clears the owner tab, writes `reason: "client_task_lease_expired"`, and keeps the previous owner as evidence. After that, a late complete from the old tab cannot match `status = "leased"`. A late browser result therefore cannot overwrite an accepted fallback.

The same sweeper cancels `fallback_started` rows that sit past a hard stale timeout (default two hours) so a lost sidecar cannot occupy the slot forever. Movie Studio V2 wraps this in `sweepExpiredMovieStudioV2WorkflowClientTasks`, gated by rollout flags, and emits `movie_studio_v2_client_task_fallback_started` events.

Auto-edit export uses the same status machine. `auto-edit-workflow.ts` waits while a live lease remains. If the lease expired or the browser reported failure, it promotes to `fallback_started` with `browser_export_lease_expired` or `browser_export_reported_failure`, then starts one parent-linked FFmpeg job. A unit test named "promotes an expired browser lease and applies the cloud winner exactly once" asserts the promotion and a single apply. Policy forbids starting sidecar work merely because the browser is slow while its healthy lease is still live.

## Routing examples

Not every family is a `workflow_client_tasks` row. Interactive frame extract in `browser-frame-extraction.ts` tries canvas capture first and calls the sidecar only in the `catch` after a codec, CORS, seek, memory, or upload failure. Continuity prefetch while Studio is open is the leased V2 path (`seedance_continuity_prefetch`). Voice Director section stitch (`stitch-storyboard-music-section-in-browser-or-cloud.ts`) runs Remotion/WebCodecs in the tab and treats cloud FFmpeg as the path after the browser throws. Long, large, or unattended work is allowed to skip the browser.

## Required regression coverage

The policy requires every browser-first / cloud-fallback family to cover the cases below. A missing test is a regression, not optional polish.

| # | Required case | Fence |
| --- | --- | --- |
| 1 | Browser success performs no cloud FFmpeg call | Healthy lease completes; sidecar is not started. |
| 2 | Explicit browser failure starts exactly one fallback operation | `failed` or reported error promotes once. |
| 3 | Lease expiry fences the browser before fallback starts | Compare-and-set `leased` → `fallback_started`; owner cleared. |
| 4 | Reload/reopen reclaims or observes the same client task and command ID | Deterministic `wfc_` id; expired lease is reclaimable. |
| 5 | Two tabs cannot both complete the same task | Complete requires matching tab and upload session. |
| 6 | A late browser result cannot overwrite the accepted fallback result | Complete requires `status = "leased"`; fallback rows miss. |
| 7 | Ambiguous fallback submission is reconciled by stable operation/output identity | Idempotent apply and fallback job id, not blind retry. |
| 8 | Browser and cloud outputs satisfy the same artifact/application contract | Shared source hash and accepted artifact kinds. |
| 9 | Cancellation racing either executor settles one result | Both executors fenced; one apply. |
| 10 | UI remains nonterminal through acceptance ambiguity, browser loss, and fallback promotion | Timeout is wait/fallback, not immediate failure. |

Movie Studio V2 projects that UI from durable rows. `MovieStudioV2WorkflowStatusPill.tsx` maps `leased` to "running in client", `fallback_started` to "fallback running", and `failed` to "needs fallback" — a warning, not a terminal red state.

## Limits

This is not a claim that every listed family is fully on the lease table. The policy file itself says that code/policy divergence is a regression: if an implementation-reference path is missing or weaker than the contract, fix the code or update the document with tests. Several Omni Video Editor and Voice Director export filenames cited in the policy are not present at those paths in the tree inspected for this article; the live stitch and auto-edit handlers are the current code. V2 client-task adapters are still flag-gated. Frame extract is sequential try/catch, not a leased row. Some family-specific promote helpers match on task id and project only, which is weaker than the shared `leased` compare-and-set and should be treated as a regression until tightened.

This paper does not restate 2026-162. It does not address vendor-provider idempotency, take identity, or billing. It does not claim that a browser timeout never loses in-flight pixels — only that the server remains the owner and that a late browser result cannot overwrite an already-accepted fallback.