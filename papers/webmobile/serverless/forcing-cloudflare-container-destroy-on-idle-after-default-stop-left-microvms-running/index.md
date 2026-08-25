---
title: "Forcing Cloudflare Container destroy() on idle after default stop() left microVMs RUNNING"
paper_id: "2026-206"
author: "buildngrowsv"
category: "webmobile/serverless"
date: "2026-08-25T07:00:31Z"
abstract: "Cloudflare Workers cannot run native ffmpeg or Remotion inside the V8 isolate. GenFlick therefore puts Debian ffmpeg and a Remotion HTTP server in Cloudflare Containers, addressed through Container-backed Durable Objects owned by sidecar Workers. Service-binding requests are HMAC-signed; heavy export jobs arrive on queues with max_batch_size 1. In July 2026 we observed Container instances remaining listed as RUNNING for days after jobs finished, including a staging extract-frame instance present since 2026-07-22T00:34Z. The runtime default for onActivityExpired is stop(); on this account that did not tear the microVMs down. We cut sleepAfter from 10 minutes to 30 seconds, override onActivityExpired to destroy() with a SIGKILL fallback, destroy one-shot jobId-export instances in a finally block, and destroy Remotion render-jobId instances on terminal status. Shared sync names stay warm for the 30-second window so Studio frame extracts do not cold-start on every click. This is an operational observation on one account plus the code we shipped, not a Cloudflare platform bug report."
score: 8.2
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Native binaries do not run in the isolate

Cloudflare Workers execute JavaScript in a V8 isolate. They have no `child_process`, no Debian userland, and no place to run ffmpeg or headless Chromium. GenFlick still needs both. Studio frame extracts seek a last or middle frame from a signed provider URL. Multi-clip export normalizes mixed codecs and concatenates them. Motion tiles that the browser cannot encode need Remotion plus Chromium.

The fleet rule is isolate-only. `infra/policies/EXCEPTIONS.md` records the codec exception as EX-001 (2026-04-18, still Active): `/api/extract-frame`, `/api/export`, and `/api/export-project` need native ffmpeg. ffmpeg.wasm was rejected for the sync path as too large and memory-bound for the isolate and the Studio spinner.

The exception is not "bind a Container to the Next.js Worker." The app Worker stays V8. A sidecar Worker owns the Container-backed Durable Object, talks to it over HTTP, and writes artifacts to the shared R2 bucket the app already serves. This paper is about what happens to the microVM after the job is done. It is not the durable-command paper and not the leased-browser FFmpeg paper.

The ffmpeg image is `debian:bookworm-slim` plus apt ffmpeg and Node. The process is `node /app/run-ffmpeg-job.mjs`: an HTTP server on port 8080 that accepts one JSON job and runs `execFile`. The Remotion image is `node:22-bookworm-slim` with Chromium; `node /app/src/server.mjs` bundles `motion_spec_v1` and calls `@remotion/renderer`.

## Sidecar, HMAC, and queue batch size 1

`workers/ffmpeg-sidecar/` handles `fetch` and `queue`. The Durable Object class is `FfmpegContainer` from `@cloudflare/containers`, bound as `FFMPEG_CONTAINER`, with `containers[].image` pointing at `./container/Dockerfile`. The sidecar has no public hostname. The app Worker reaches it through a service binding.

Platform service bindings are already authenticated. We still HMAC-SHA256 the request body and require `x-genflick-sidecar-signature` before any work, so a bug that exposed sidecar `fetch` would not mean unauthenticated ffmpeg (`app/src/lib/ffmpeg-sidecar-client.ts`). Unsigned requests return 401. Sync RPC is limited to extract, probe, and detect families. Export is rejected on `fetch` and accepted only from the queue consumer.

Export is heavyweight. Wrangler sets `max_batch_size` to 1 on `genflick-export-jobs` and `genflick-extract-frame-jobs` so a batch of ten jobs cannot share one consumer budget. Each consumer has a dead-letter queue. `max_concurrency` stays at or under `max_instances` after a 2026-07-18 oversubscribe caused thrash and false timeouts. ffmpeg runs inside the container, not the isolate. The queue handler stages clip-normalize messages, concatenates, and updates the Neon `generations` row so `/api/export/status/[jobId]` can poll.

## Named instances: warm sync versus one-shot export

`getContainer(env.FFMPEG_CONTAINER, instanceName)` addresses a named Durable Object, which is the Container instance. Sync operations use stable names such as `extract-frame`. Those names are shared across users on purpose. A Studio click burst should reuse a warm microVM for a few seconds instead of cold-starting Debian and ffmpeg on every frame grab.

Export uses a different name:

```ts
function exportContainerInstanceName(jobId: string): string {
  return `${jobId}-export`;
}

function isOneShotExportContainerInstanceName(instanceName: string): boolean {
  return instanceName.endsWith("-export");
}
```

A `{jobId}-export` instance is created once per export and is never reused across users. Leaving it listed after finalize or fail is wasted Container lifetime. Shared sync names stay up for the `sleepAfter` window. The split was chosen after we listed production instances and saw many inactive `{uuid}-export` names still present.

The Worker POSTs to `http://container/job` or `http://container/job-binary`. `fetchContainerWithHardTimeout` races that fetch against a deadline so a hung container can fail the queue invocation and retry. The caller's `finally` block destroys the one-shot instance, including on timeout. Binary jobs buffer the body into an `ArrayBuffer` before returning: destroying the instance while still streaming `response.body` into R2 produced "Network connection lost" on large Storyboard exports.

## Default stop() left microVMs RUNNING

`@cloudflare/containers` exposes `sleepAfter` and `onActivityExpired`. The documented default for expiry is `stop()`. After a job finished we expected the microVM to leave the RUNNING set once the idle timer fired.

On this account that is not what `wrangler containers instances` showed. Production comments dated 2026-07-25 record the observation: GenFlick staging `extract-frame` was still listed as RUNNING with a start time of `2026-07-22T00:34Z`, days after the last job. Remotion bench instances on the same account were in the same state. Relying on `sleepAfter` alone was not enough when activity never expired cleanly. We treat this as an operational observation on one account, not as a general Cloudflare platform defect and not as a vulnerability report. We changed our subclass.

The Remotion Worker comment states the previous idle timeout explicitly: `sleepAfter` was 10 minutes. That left Remotion microVMs idle far longer than the ffmpeg sidecar after a render finished. Both classes now set `sleepAfter = "30s"`. Shared sync names still get a short warm window. One-shot names should not need it, because they are destroyed at the end of the job.

## Force-destroy on idle and after the job

`FfmpegContainer` overrides expiry to tear the microVM down instead of requesting a soft stop:

```ts
export class FfmpegContainer extends Container {
  defaultPort = 8080;
  requiredPorts = [8080];
  sleepAfter = "30s";
  enableInternet = true;
  pingEndpoint = "localhost:8080/ready";

  override async onActivityExpired(): Promise<void> {
    try {
      await this.destroy();
    } catch (error) {
      await this.stop("SIGKILL");
    }
  }
}
```

`destroy()` is the public RPC on the Container subclass. The comment next to the override says it sends SIGKILL and tears the microVM down. If `destroy()` throws, we fall back to `stop("SIGKILL")` and log a warning. That fallback is not a claim that `stop()` without SIGKILL is always a no-op; it is the last call we make from the expiry hook.

One-shot export instances do not wait for the 30-second timer. `runContainerJob` and `runContainerBinaryJob` call `destroyContainerInstanceBestEffort` from `finally` when the name ends with `-export`. The helper races `container.destroy()` against a 15-second timeout and swallows errors. Destroy must not throw out of a path that already has a success or failure result. A race with an already-stopped instance is expected.

The same helper is a signed admin path. During the July incident there was no in-repo way to tear down a leaked `extract-frame` Durable Object without deleting the whole Containers application. HMAC-authenticated `destroy_container_instance` destroys one named instance.

## Remotion uses the same idle-destroy contract

`workers/remotion-renderer/` is a twin, not a copy of the queue machine. It is an HTTP service: `POST /render`, `GET /render/status/:jobId`, `POST /render/cancel`. Auth is a Bearer token, not HMAC. There is no queue consumer. Jobs require `job_id` and `motion_spec`. On complete, the Worker copies the MP4 to `remotion-renders/{jobId}.mp4` with immutable cache headers.

Routing is still a named Container. `instanceNameForJob` returns `render-{jobId}`. Each job owns a stable microVM for its lifetime. `RemotionRendererContainer` uses the same `sleepAfter = "30s"`, the same `pingEndpoint`, and the same `onActivityExpired` force-`destroy()` with `stop("SIGKILL")` fallback.

Status and cancel do not wait for idle. After the artifact is persisted, terminal statuses destroy immediately:

```ts
  if (
    persisted.status === "complete" ||
    persisted.status === "failed" ||
    persisted.status === "cancelled"
  ) {
    await destroyRemotionJobContainerBestEffort(
      env,
      jobId,
      `terminal-status:${persisted.status}`,
    );
  }
```

Cancel destroys even if the inner cancel RPC is messy. Destroy is best-effort; the status JSON still returns if teardown races a stopped instance. Leaving `render-{jobId}` up after complete, failed, or cancelled burns Container duration until `sleepAfter`, and `sleepAfter` was the layer that had already failed us once.

## Limits

We do not claim that Cloudflare Containers always leak RUNNING instances after `stop()`, that `onActivityExpired` is defective on every account, or that `destroy()` is the documented platform requirement. The July 22–25 2026 listing of a staging `extract-frame` instance since `2026-07-22T00:34Z` is an observation on this account, recorded in production comments, not a vendor bug ticket.

We do not report spend, plan prices, or savings. We do not claim the 30-second `sleepAfter` is optimal, only that 10 minutes was long enough to notice idle instances and that 30 seconds is the value now in both sidecars. We did not measure cold-start distributions after the cut. Shared names can still be RUNNING for up to that window by design.

Destroy is best-effort. Timeouts, already-stopped instances, and RPC failures are logged and swallowed. We do not claim every historical leak is now impossible: a shared name whose expiry hook never runs would still need the admin destroy path. The supporting repository is private; excerpts above are from `workers/ffmpeg-sidecar/src/index.ts`, `workers/ffmpeg-sidecar/wrangler.jsonc`, `workers/remotion-renderer/src/index.ts`, and `infra/policies/EXCEPTIONS.md` at commit `529267b988ef7dbb1dcd1d89946ac415c14886d0`.