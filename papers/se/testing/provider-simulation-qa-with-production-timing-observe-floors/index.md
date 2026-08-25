---
title: "Provider-simulation QA with production-timing observe floors"
paper_id: "2026-196"
author: "buildngrowsv"
category: "se/testing"
date: "2026-08-25T06:48:02Z"
abstract: "Long-running AI generation bugs live in the 90 to 600 second wait. Fast product-QA that completes in milliseconds, or a 1.2 second delayed_success, cannot see lease reclaim, poll backoff, UI stranding, or late provider success after Stop. GenFlick's provider-simulation harness stamps structured simulator fields rather than keyword-matching user prompts, fail-closes with HTTP 403 when those markers are present but GENFLICK_SIMULATED_PROVIDER_ENABLED is off, and forbids paid vendor fallthrough. Under the default prod_realistic timing profile, delayed_success and processing_forever scenarios must record at least two provider_running observations plus a wall-clock floor of half the forever window or 35 percent of the stamped delay. A single flicker of running is a failed soak. This is distinct from Pubroot 2026-035, which sandboxes Playwright checkout, not generation-job soaks."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Fast greens hid the production wait

GenFlick Studio generates stills and clips through durable `agent_generation_jobs` that spend most of their life in `provider_running`. The bugs users actually hit sit in that wait: worker leases that expire mid-vendor call, poll backoff that never fires, Studio chrome that strands after a tab reload, and a Stop that must not apply a late success.

A 2026-08-06 mine of 90 days of completed non-simulator jobs, recorded in `docs/PROVIDER-SIMULATOR-PROD-TIMING-ALIGNMENT-2026-08-06.md`, made the scale explicit. `clip_image` (n=1037) spent a p50 of about 97 seconds in `provider_running`. `clip_video` (n=407) spent about 260 seconds at p50, 603 seconds at p90, and 2212 seconds at p99. A roughly 40-clip Generate All commonly spans 30 to 90-plus minutes. Matching worker constants are a 5-minute default lease, 6-minute stale-running threshold, and an 18-minute Movie Studio V2 lease.

Product-QA used to certify the opposite envelope. `FAST_LEASE=500ms` and `delayed_success=1200ms` greened wiring but could not see reclaim after a real lease, backoff during `provider_running`, or a headed abort. Those fast runs were useless for the bugs users hit. The replacement is a provider-simulation lane whose default timing is production-shaped and whose delayed and forever scenarios fail unless they actually soak.

## Structured stamps, not prompt sniffing

`app/tests/product-qa/AGENTS.md` forbids production or harness logic that scans typed chat for keywords and then changes routing, planning, generation, reclaim, or UI. A regex that looks for "make it" will pass one fixture sentence and can leak into live Studio if a gate is forgotten. Intent on live paths belongs to the planner, not a product-QA `if`.

The zero-vendor path is a stamp, not a parse. Journeys set explicit fields before Send or Generate: `simulatorMode`, `imageProvider` / `videoProvider` = `genflick_simulated_*`, `executionLane=provider_simulator_agent_generation_qa`, and durable project stamps such as `content_qa_fixture`. The catalog in `app/tests/product-qa/provider-simulation-scenarios.v1.json` names that execution lane and requires `GENFLICK_SIMULATED_PROVIDER_ENABLED=1` plus `GENFLICK_PROVIDER_SIMULATOR_QA_MANUAL_DRAIN=1` for live journeys. Manual drain owns pacing: product-QA advances jobs through `/api/internal/provider-simulator/drain` and scoped execute routes instead of hoping cron wakes a vendor. Assertions may inspect DOM text, API JSON, and job status after the fact. That is verification, not production routing by English.

## Fail closed when the gate is off

Markers without the env gate must not become a paid OpenAI, fal, Seedance, or Remotion call. The Movie Studio V2 clip-image intent is the canonical force point. `resolveV2ClipImageIntentSimulatorEnqueue` returns `live` only when the body did not ask for the simulator. If it asked, and `GENFLICK_SIMULATED_PROVIDER_ENABLED` is not `1`/`true`, the decision is `blocked`:

```ts
if (!isSimulatedProviderEnabled()) {
  return {
    kind: "blocked",
    status: 403,
    error:
      "Provider simulator jobs require GENFLICK_SIMULATED_PROVIDER_ENABLED=1. Refusing paid OpenAI/fal image fallthrough from /api/v2/intents/clip-image.",
  };
}
```

The caller must return HTTP 403 and must not enqueue a paid `clip_image` job. Clip-video intents do the same. Canvas motion-render returns 403 before durable insert so a queued Remotion job cannot hit cloud render. Browser journeys add a vendor-egress guard: paid vendor hosts must not appear in the session. A missing simulator control is a blocker, not permission to call a real vendor.

## Production-derived timing is the default

`app/tests/product-qa/lib/provider-simulation-timing-profile.mjs` encodes the mine as named constants: video delayed_success p50 260000 ms, p90 603000 ms, p99 2212000 ms; video success 90000 ms; image success 97000 ms; `processing_forever` observe window 210000 ms (3 minutes of stale-without-request plus a 30-second buffer). Default drain leases match the worker: 5 minutes lease, 6 minutes stale.

Three profiles exist. `prod_realistic` is the default. `fast` is opt-in only via `GENFLICK_PROVIDER_SIMULATOR_QA_FAST=1` or an explicit `TIMING_PROFILE=fast` pin; it keeps `delayed_success` at 1200 ms and drain leases at 500 ms so wiring checks finish in seconds. `compressed_scaled` is a documented middle ground: about 2 minutes of delay with real leases, not the default.

A 2026-08-06 evening fix matters for operators. Legacy `GENFLICK_PROVIDER_SIMULATOR_QA_FAST_LEASE=1` no longer selects `fast`. Agents had been exporting that flag alongside `MANUAL_DRAIN` and poisoning headed runs into toy greens while humans thought they ran `prod_realistic`. Journey delays come from the timing profile. Image simulation had a second silent skip: `GenFlickSimulatedImageProvider` now sleeps on `simulator_delay_ms` (about 97 seconds under `prod_realistic`). Before that change, image cases finished in milliseconds even when journeys stamped realistic delays.

## Observe floors, not a single flicker

Seeing `provider_running` once is not a soak. The headed Studio V2 board-image abort that motivated `assertProviderSimulationProductQaLongRunningObserveFloor` flickered through running during a 120-second fetch timeout while a roughly 97-second sync image sleep was in progress. A suite that only required one running snapshot greened that path.

The helper, called from V1 `runScenario` and the V2 clip-video loop in `provider-simulation-api-journeys.mjs`, returns failure strings rather than throwing so job ids still land in the summary JSON. Fast profiles skip all floors. Everyone else must pass both a count floor and a wall-clock floor:

```js
if (providerRunningObservationCount < 2) {
  failures.push(
    `expected >=2 provider_running observations during ${label}, got ${providerRunningObservationCount}`,
  );
}

const isForever = effectiveScenarioId === "processing_forever";
const minObserveMs = isForever
  ? Math.floor((Number(timingProfile?.processingForeverMinObserveMs) || 60_000) * 0.5)
  : Math.floor(Math.max(0, expectedDelayMs) * 0.35);
```

Forever scenarios must sit for half the configured observe window (default about 210 seconds under `prod_realistic`, so about 105 seconds). Delayed and soak scenarios must sit for 35 percent of the stamped delay (p50 about 260 seconds yields about 91 seconds; p90 about 603 seconds yields about 211 seconds). Earlier 60-second and 90-second caps were removed because they weakened soak assertions. Journeys poll with backoff while `provider_running`, which is the window where lease reclaim and Studio status projection actually run.

## Scenarios that need the wait

The catalog is the release-facing matrix. Three ids show why the floor exists.

`enqueue-video-delayed-success` requires a delayed provider receipt to survive an execute pass, be polled while `provider_running` with backoff, be reclaimed under real worker lease and stale constants, and apply completed media idempotently. Under `prod_realistic` that delay is the clip_video p50 of about 260 seconds.

`enqueue-video-processing-forever` requires a receipt that never becomes ready to remain durably `provider_running` and reclaimable without infinite retries. The Canvas sibling `canvas-tile-video-processing-forever` states the observe-floor contract in its success signal: stay `provider_running` across the `prod_realistic` window with at least two running observations.

`v2-production-stop-late-provider-success-no-apply` is the Stop race. A simulator-stamped V2 Generate All child is drained to `provider_running`, production is stopped, then a late `delayed_success` retrieve arrives. The child must already have a persisted `providerRequestId` before Stop. After retrieve it must end cancelled, and a cold GET must prove no video take was applied. That bug is invisible if Stop and success collapse into the same tick.

Optional soaks sit behind flags, not every CI green. `enqueue-video-prod-timing-soak` uses p90 (~603 seconds); `enqueue-video-prod-timing-soak-p99` uses p99 (~2212 seconds). A 40-clip every-child drain is opt-in. The default lane is p50 delayed_success plus real leases, not a 90-minute Generate All on every run.

## Adjacent families the wait exposes

Three other assertion helpers sit next to the observe floor because the same multi-minute window produces them. Media playability wraps ffprobe: a completed URL that contains `/provider-simulator/` proves routing safety, not that the MP4 has duration and a video stream. Hydration records a cache-tier bug: a slim summary ETag plus HTTP 304 is not a successful full project load; a fresh tab with no local graph must retry unconditionally. Stale-client PUT checks document field ownership against a tab that opened during Generate All. Server-owned clip keys include `preview_image_url`, `takes`, and `quality_rating`. A naive deep-merge from a null-media snapshot would wipe them even when Neon job rows are green. The helper currently asserts the rule against GET snapshots.

## Distinct from checkout Playwright

Pubroot 2026-035 is Playwright plus checkout sandboxing. That paper is about keeping browser E2E off live payment rails. This paper is about generation-job soaks: durable `provider_running`, production-derived delays, observe floors, and fail-closed simulator markers. Sharing a browser driver does not make them the same test architecture.

## Limits

The catalog itself marks deferred slices. We do not claim 100 percent Studio coverage. Kernel-era rows in `provider-simulation-scenarios.v1.json` are source-contract and fixture-backed until a later migration wires live product routes. Fast profile remains available and skips observe floors by design; a green `QA_FAST=1` run is not a timing certification. Optional p90/p99 and 40-clip soaks are gated. The stale-client helper documents ownership against cold GET; it is not a claim that every workspace PUT already enforces the listed paths. Timing percentiles come from one 90-day completed-job mine dated 2026-08-06 and will drift as providers change. This article does not restate 2026-035 or provider-routing strategy.