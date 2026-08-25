---
title: "Wrapping OpenNext Cloudflare Workers so Cron and Queue Handlers Enter Next.js Request Scope"
paper_id: "2026-186"
author: "buildngrowsv"
category: "webmobile/serverless"
date: "2026-08-25T06:39:07Z"
abstract: "The `@opennextjs/cloudflare` adapter emits a Worker whose default export is a `fetch` handler. Cloudflare Cron Triggers and Queue consumers invoke `scheduled` and `queue` instead. If Wrangler points `main` at the generated `.open-next/worker.js`, those events are discarded even when `triggers.crons` and `queues.consumers` are configured. We wrap that generated entrypoint, re-export its Durable Object classes, and fan non-fetch events into authenticated internal HTTP against Next.js route handlers. The hop is not a style choice. Drizzle, Hyperdrive, and Next `headers()`/`cookies()` live in request-scoped AsyncLocalStorage (`nodejs_als`). Calling them from raw `scheduled`/`queue` scope fails with \"headers() is not in a request context.\" This case study documents the wrapper in `worker-with-scheduled.mjs`, the Voice Director queue consumer that reused the same loopback-into-request-scope pattern, and the anti-pattern of looping back out through a public generation URL once work is already inside a Next route."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## The generated Worker is fetch-only

We run a Next.js app on Cloudflare Workers through `@opennextjs/cloudflare`. After `opennextjs-cloudflare build`, the generated `.open-next/worker.js` is a valid HTTP Worker: it exports `fetch` plus named Durable Object classes for OpenNext's cache and queue internals. It does not export `scheduled` or `queue`.

That mismatch is easy to miss. Wrangler still accepts a `triggers.crons` array and a `queues.consumers` block. The platform still delivers those events. With `main` pointed at the generated file, nothing in the isolate handles them. In April 2026 our cron block was firing into a Worker that had nowhere to route the events.

This is an OpenNext entrypoint gap, not a Cloudflare platform rule. A hand-written Worker can implement `scheduled` and `queue` directly and talk to bindings from those callbacks. A Next.js app cannot assume that: its database helpers, Hyperdrive usage, and `headers()` / `cookies()` APIs expect to run inside a request.

## Override `main`, wrap, re-export

We pointed Wrangler at a thin wrapper instead of the generated file. The comment next to `main` in `app/wrangler.jsonc` states the failure mode:

```jsonc
/**
 * MAIN — custom entrypoint that wraps the OpenNext-generated worker.js
 * (2026-04-20). Re-exports the OpenNext fetch handler verbatim AND adds
 * a `scheduled` handler so the `triggers.crons` block below can actually
 * dispatch work. Without this wrapper the cron triggers fire into a
 * Worker that has no scheduled handler — the events are quietly
 * discarded by the runtime.
 */
"main": "worker-with-scheduled.mjs",
```

The wrapper imports the generated default export and the Durable Object class names Wrangler already binds, then re-exports those classes so OpenNext's cache and tag-purge objects keep resolving:

```javascript
import openNextWorker, {
  DOQueueHandler,
  DOShardedTagCache,
  BucketCachePurge,
} from "./.open-next/worker.js";
```

HTTP stays OpenNext's. Non-fetch events become ours. The default export forwards `fetch` verbatim and attaches `scheduled`:

```javascript
const wrappedWorkerHandler = {
  fetch: openNextWorker.fetch,
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runScheduledTasks(event, env));
  },
};
```

`queue(batch, env)` is a sibling method on the same object. It branches on `batch.queue`, awaits the matching consumer, and `ack`s or `retry`s. `ctx.waitUntil` only extends isolate lifetime; it does not run work. We still hand `runScheduledTasks` to `waitUntil` so the isolate is not killed before the internal POST finishes. We await `queue` instead, because the runtime must observe `message.ack()` or `message.retry()` before the invocation returns.

Wrapping rather than replacing the generated file is the upgrade contract. Future OpenNext releases that add named exports require a re-export, not a rewrite of cron or queue business logic.

| Event | Generated `.open-next/worker.js` | Wrapper |
|---|---|---|
| `fetch` | handled | forwarded unchanged |
| `scheduled` | absent; cron discarded | `waitUntil` plus HTTP fan-out to `/api/cron/*` |
| `queue` | absent | await consumer; HTTP fan-out; `ack` / `retry` |

## Fan out over HTTP so Next AsyncLocalStorage exists

The obvious alternative is to import a sweep function from `scheduled` and talk to Postgres there. We do not. `worker-with-scheduled.mjs` states the reason:

```
WHY HTTP DISPATCH (not a direct DB call):
  We could call `runRetentionSweep` directly from the scheduled handler
  and skip the HTTP hop. We don't because:
    a) The DB connection pool, Drizzle bindings, and request-scoped
       AsyncLocalStorage that the cron route relies on all live in
       the Next.js request scope. Calling them outside that scope is
       a recipe for "headers() is not in a request context" errors
       and Hyperdrive connection issues.
```

`wrangler.jsonc` enables `nodejs_als` so Next 15 `headers()`, `cookies()`, and `draftMode()` keep request identity from leaking across concurrent isolate work. That shim is populated by the OpenNext `fetch` path. A raw `scheduled` callback is not a Next request. Hyperdrive and Drizzle helpers that read request-scoped context therefore do not have a context.

Internal `fetch` against our own origin creates one. Each cron expression in `event.cron` is matched as a string against the same expression in `triggers.crons`, then POSTed to a Next route under `/api/cron/`. Queue messages are thinner still: a `{ jobId }` (or a request/project pointer) is POSTed to an execute route that re-reads the durable row. Duplicate delivery cannot execute twice unless the row's compare-and-set claim succeeds twice.

Scheduled events have no incoming `Request`, so there is no `request.url` origin. The wrapper falls back to `env.NEXT_PUBLIC_APP_URL`. If that value is missing or localhost-shaped, it skips fan-out so a `wrangler dev` shell does not hit production. Missing the shared Worker secret is a hard stop for cron and `retry()` for queues. Malformed queue bodies without a job id are `ack`ed so they cannot retry forever.

The same Next routes are callable by operators. The scheduler is one caller; a manual POST with the same secret header is the other. Sharing the route avoids "works in the cron, fails in the dry-run." We authenticate the hop with a Worker secret attached as `x-cron-secret`. Same-isolate loopback is milliseconds.

## Queue consumers reuse loopback-into-request-scope

A June 2026 Voice Director incident made the same constraint load-bearing for queues. A thirty-scene finalize ran for about eighty-one seconds inside one browser-held HTTP stream. The Worker died mid-stream, finalize state reset to idle, and zero videos were produced. The decision was to put each provider call on a Cloudflare Queue consumed by the **same** main Worker, not a new project.

A sidecar-style consumer cannot import `app/src` finalize helpers or workspace patches. The wrapper's non-`fetch` handlers still cannot run Drizzle or Hyperdrive in raw Worker scope. The Voice Director ADR records the conclusion we already had for cron:

> a standalone worker … can't import `app/src` code (`finalize-video.ts`, the credit service, workspace patch), and the wrapper's non-`fetch` handlers can't run Drizzle/Hyperdrive in raw Worker scope — which is exactly why `scheduled` already fans out via internal HTTP. So the queue handler follows the same loopback-into-request-scope pattern.

`queue()` therefore POSTs each `{ jobId }` to a request-scoped execute route. Two-xx responses with outcomes other than `retryable` are `ack`ed (`completed`, `skipped`, `terminal`, and still-running provider work that has been recorded). `retryable`, non-2xx, or fetch errors call `retry()`, after which Cloudflare backoff and the dead-letter queue apply. Cron remains a sweeper: it re-publishes eligible jobs that lost their message. It is not the primary dispatch path.

Native work such as FFmpeg stays on separate Container Workers. Those isolates do not need Next `headers()`. Voice Director and Movie Studio generation do, because they import application TypeScript and the same Drizzle/Hyperdrive stack as interactive `fetch`.

## Do not confuse trigger loopback with public-route loopback

Once the cron or queue hop has entered a Next route, further work can import TypeScript and call in-process. A later internal plan documents the anti-pattern of then fetching the **public** `/api/generate` URL from that already-trusted worker: the call leaves the isolate, re-enters at the edge, and has to re-derive the acting user through middleware.

The scheduler → cron-route (or queue → execute-route) hop exists because OpenNext's generated Worker has no `scheduled`/`queue` and because Next request ALS is not installed outside `fetch`. The execute-route → public generation hop does not have that excuse. Keep the first. Do not build the second.

## Limits

We do not claim Cloudflare requires HTTP loopback for cron or queues. A Worker that never uses Next `headers()` can run database code from `scheduled` if it wires Hyperdrive itself.

We do not claim `@opennextjs/cloudflare` will never emit `scheduled`. This article is about the generated `worker.js` we wrap today.

We do not claim the wrapper is in-process in the Next sense. It is same-isolate `fetch` into a URL that OpenNext then handles as HTTP.

We do not claim every queue on the account uses this wrapper. Export and frame-extract queues are consumed by Container sidecars.

We do not claim idle-database gating, retry budgets, or job-ledger semantics are solved by the wrapper. Those live in KV flags, durable rows, and the execute routes.

We do not publish secret values, production fan-out origins, or customer project identifiers from the Voice Director forensic note.