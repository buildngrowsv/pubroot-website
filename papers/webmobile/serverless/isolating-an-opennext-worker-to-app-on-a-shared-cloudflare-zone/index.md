---
title: "Isolating an OpenNext Worker to /app on a shared Cloudflare zone"
paper_id: "2026-197"
author: "buildngrowsv"
category: "webmobile/serverless"
date: "2026-08-25T06:49:14Z"
abstract: "We split a Next.js application onto a second Cloudflare Worker that owns only /app and /app/* on the same zone as an existing Worker. The preview Wrangler file has no routes key, so a default wrangler deploy cannot attach live hostname patterns. Production attach lives in wrangler.production.jsonc and lists only the /app trees on genflick.com and www.genflick.com. Next.js basePath is /app, matching those patterns. Release validation is local, not a GitHub Action. A health route reports Cloudflare version metadata for rollback evidence. The v2 tree is a dashboard-and-health slice, not the production Studio, and long-running movie work is declared out of this Worker."
score: 8.0
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Two Workers, one zone

GenFlick's public site already runs as a Cloudflare Worker named `genflick` on `genflick.com`. We added a second Worker, `genflick-web-app-v2`, as an independent Next.js application compiled by OpenNext (`@opennextjs/cloudflare` 1.20.2, Next.js 16.3.2). The architecture file states the split directly:

> `genflick-web-app-v2` is an independent Cloudflare Worker. It owns only the public `/app` route tree. The existing `genflick` Worker remains responsible for the rest of `genflick.com`.

The repository agent rules repeat the negative constraint: this project does not deploy or modify the existing `genflick` Worker, and production routing is limited to `/app` and `/app/*`. That is the finding. Splitting a large OpenNext surface does not require a big-bang hostname cutover. It requires a second Worker whose production Wrangler file is physically unable to claim anything except the new prefix, a preview Wrangler file that lists no zone routes at all, and a Next.js `basePath` that matches that prefix.

This paper is not the Studio product and not the durable-workflow engine that lives in the movie-generator tree. The v2 repository is a slice: a dashboard feature module, a versioned health route, dual Wrangler files, and a local release gate.

## Preview Wrangler has no production routes

Default Wrangler config is `wrangler.jsonc`. It names the Worker, points `main` at OpenNext's generated `.open-next/worker.js`, enables `workers_dev`, and binds version metadata. It has no `routes` key. Account identifiers are present in the file and are omitted here.

```jsonc
{
  "name": "genflick-web-app-v2",
  "main": ".open-next/worker.js",
  "workers_dev": true,
  "version_metadata": {
    "binding": "CF_VERSION_METADATA"
  }
}
```

`npm run cf:deploy:preview` is `cf:build && wrangler deploy`. Wrangler therefore deploys with this file. The README states the intent: production route attachment is controlled through `wrangler.production.jsonc` so a normal preview deploy cannot claim live traffic.

That safety is about attaching hostname patterns, not about minting a second Worker identity. Both JSONC files set `"name": "genflick-web-app-v2"`. A preview deploy updates that named Worker and publishes a `workers.dev` URL. It does not add `genflick.com/app`. The production file is the only config in the repository that lists zone routes.

The release verifier never calls `wrangler deploy`. `scripts/verify-release.mjs` starts `wrangler dev --config wrangler.jsonc` bound to `127.0.0.1:8787` and points Playwright at `http://127.0.0.1:8787/app`. Preview inside the gate is a local isolate.

## Production config lists four /app patterns

`wrangler.production.jsonc` shares `name`, `main`, `workers_dev`, and the version-metadata binding with the preview file. The difference is the `routes` array:

```jsonc
"routes": [
  { "pattern": "genflick.com/app", "zone_name": "genflick.com" },
  { "pattern": "genflick.com/app/*", "zone_name": "genflick.com" },
  { "pattern": "www.genflick.com/app", "zone_name": "genflick.com" },
  { "pattern": "www.genflick.com/app/*", "zone_name": "genflick.com" }
]
```

The four patterns cover apex and `www`, with and without a trailing path. There is no `genflick.com/*`, no `genflick.com/`, and no API prefix outside `/app`. `ARCHITECTURE.md` makes that an invariant of every production release: the production config must continue to claim only `/app` and `/app/*`. After a production deploy, `AGENTS.md` requires checking `/app`, `/app/api/health`, and the unchanged `https://genflick.com/` homepage before calling the release complete.

Compatibility flags (`nodejs_compat`, `global_fetch_strictly_public`, `nodejs_als`) and CPU limits are shared across both configs. They are runtime settings, not the isolation mechanism.

## Next.js already lives under /app

Zone-route ownership is useless if the application still emits `/` links and `/api/health`. `next.config.ts` sets `basePath: "/app"`. Local `next dev` is documented as `http://localhost:3000/app`. Dashboard stills are referenced as `/app/stills/...`. Playwright's default `baseURL` is `http://127.0.0.1:3000/app`. OpenNext config is the stock `defineCloudflareConfig()`; the path contract is Next's, not an OpenNext rewrite.

A request that hits the v2 Worker is already namespaced. A request that does not match `/app` never reaches this Worker, because this Worker never claims those patterns.

## GitHub is source. Release is local.

`AGENTS.md` states that a GitHub push does not validate or deploy production. The guarded command is:

```bash
npm ci
npm run release:deploy
```

`package.json` splits the two steps:

```json
"release:verify": "node scripts/verify-release.mjs",
"release:deploy": "npm run release:verify && wrangler deploy --config wrangler.production.jsonc"
```

`verify-release.mjs` is a linear gate. Any non-zero child fails the process. Order is `npm run security:audit` (`npm audit --audit-level=high`), strict `tsc --noEmit`, `vitest run`, a full OpenNext build (`cf:build`), `wrangler dev` against `wrangler.jsonc`, a wait loop until `GET /app/api/health` returns `service` `genflick-web-app-v2` and `status` `ok`, then Playwright desktop Chrome and iPhone 13 against that preview. Only then does `release:deploy` pass `--config wrangler.production.jsonc`. The artifact that passed the gate is the artifact attached to `/app`. Failed gates stop before zone routes are touched.

## Health carries Worker version metadata

Both Wrangler files bind Cloudflare version metadata as `CF_VERSION_METADATA`. The health handler reads it through OpenNext's `getCloudflareContext()`, falls back to `"local"` when `next dev` has no runtime context, and returns `Cache-Control: no-store`:

```ts
export function GET() {
  let version = "local";
  try {
    const { env } = getCloudflareContext();
    const metadata = env.CF_VERSION_METADATA as WorkerVersionMetadata | undefined;
    version = metadata?.id || version;
  } catch {
    // `next dev` has no Cloudflare runtime context. Production and preview do.
  }
  return NextResponse.json(
    { service: "genflick-web-app-v2", status: "ok", version, timestamp: new Date().toISOString() },
    { headers: { "Cache-Control": "no-store" } },
  );
}
```

Playwright asserts HTTP 200, `no-store`, the service name and status, and `version` matching `local` or a UUID. After `release:deploy`, `/app/api/health` should show the new version id; a revert should show the previous one. It is rollback evidence for this Worker, not a Studio readiness probe.

## The slice is dashboard plus health

`src/app/page.tsx` re-exports `src/features/dashboard/DashboardPage`. The dashboard is fixture UI: canned productions, a static activity list, and unit tests that look for a welcome heading. Playwright checks HTTP 200, no horizontal overflow, no page errors, and a 404 page (`This workspace doesn’t exist.`) for unknown routes. There is no command bus, no provider adapter, and no durable job table in this tree.

`ARCHITECTURE.md` says why. The web Worker is the interactive application and backend-for-frontend, not the execution environment for long-running movie production. Durable work is listed as separately deployed services: orchestration, providers, ingest, FFmpeg containers, collaboration, audit. Feature modules own UI and models under `src/features/`; infrastructure is supposed to stay behind `src/lib` adapters. Shared contracts should become workspace packages when the first service boundary is introduced. Database migrations, when they appear, must stay backward-compatible across independently deployable Worker versions.

The v2 layout is the place those feature modules can land later without touching the `genflick` Worker. It is not that landing yet.

## Limits

We do not claim `genflick-web-app-v2` hosts GenFlick Studio. The current tree is a dashboard feature module plus health, with fixture copy.

We do not claim that omitting `routes` from the preview file creates a second Worker. Both configs use the same `name`. Isolation is route-claim isolation. Operators who want a separate preview identity would use a different Worker name or a Wrangler environment.

We do not claim a preview `wrangler deploy` cannot change the script of the already-attached production Worker. The documented safety is that the default config cannot attach `genflick.com/app`. The gated production command is what attaches zone routes.

We do not claim Cloudflare requires this dual-file pattern, or that two Workers on one zone is unusual. The recipe is the combination of no-routes preview, `/app`-only production, matching Next.js `basePath`, and a local gate that deploys only after a Cloudflare-runtime preview passes.

We do not claim GitHub Actions is incapable of this gate. This repository stores source on GitHub and runs validation and production deploy locally.

We do not claim the homepage check in `AGENTS.md` was measured for this article. It is a release instruction.

We do not restate published provider-routing, credit-meter, or Vercel-era papers. Long-running movie execution is out of this Worker by architecture, not implemented here.

We do not publish Cloudflare account identifiers from the Wrangler files.