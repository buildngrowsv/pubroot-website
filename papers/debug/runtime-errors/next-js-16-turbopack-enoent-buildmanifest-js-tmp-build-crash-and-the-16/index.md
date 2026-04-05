---
title: "\"Next.js 16 Turbopack ENOENT _buildManifest.js.tmp Build Crash and the 16.2.1 Fix\""
paper_id: "2026-031"
author: "buildngrowsv"
category: "debug/runtime-errors"
date: "2026-03-24T06:17:23Z"
abstract: "\"Next.js 16.1.6 crashes during `next build` with an ENOENT error on `_buildManifest.js.tmp` when Turbopack is active. The error is a race condition in the Turbopack bundler's manifest write phase, reproducible on macOS with Node v23. This article documents the symptom, environment, failed workarounds (clean .next, missing --no-turbopack flag, removed webpack:true option, env vars), and the definitive fix: upgrading to Next.js 16.2.1. A workaround using the --webpack flag is also provided for teams that cannot upgrade immediately.\""
score: 8.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "\"Drafted with Claude Sonnet 4.6 (Anthropic) based on observed production build failures.\""
aliases:
  - "/2026-031/article/"
  - "/2026-031/"
---

## Symptom

Running `next build` with Next.js 16.1.6 fails with an error similar to:

```
Error: ENOENT: no such file or directory, rename '/path/to/.next/static/chunks/pages/_buildManifest.js.tmp'
  -> '/path/to/.next/static/chunks/pages/_buildManifest.js'
```

The crash occurs late in the production build, after compilation appears to complete. The `.tmp` intermediate file is created by Turbopack as part of an atomic rename write pattern, but the rename fails because the file is not present at the moment the rename is attempted — a race condition in the Turbopack bundler path.

The build process exits non-zero. No `_buildManifest.js` is produced in `.next/static/chunks/pages/`, making the output undeployable.

## Environment

- **Next.js:** 16.1.6
- **Bundler:** Turbopack (default in Next.js 16)
- **Node.js:** v23.10.0
- **OS:** macOS (Darwin 25.x)
- **Project type:** App Router, TypeScript

The issue was consistently reproducible on a clean checkout with `npm run build`. It did not appear on every run — roughly 60–80% of build attempts failed, consistent with a timing-sensitive race condition.

## What We Tried (and Why It Did Not Work)

### Clean `.next` directory

Deleting `.next/` and re-running `next build` did not prevent the crash. The race occurs during the current build's write phase, not due to stale cache.

### `--no-turbopack` flag

`next build --no-turbopack` is not a recognized flag in Next.js 16. The flag does not exist and the command errors immediately.

### `webpack: true` in `next.config.ts`

Next.js 16 removed the `webpack: true` bundler-switch option that existed in Next.js 15 as an escape hatch. Passing it causes a configuration validation error:

```
Error: Invalid next.config.ts options detected:
  Unrecognized key(s) in object: 'webpack'
```

This path is fully closed in Next.js 16.

### Environment variable overrides

Setting `NEXT_TURBOPACK=0`, `TURBOPACK=0`, and related environment variables had no effect. The Turbopack path is not gated on these variables in 16.1.6.

### Increasing Node.js file handle limits

Raising the open file limit via `ulimit -n` did not change the failure rate. The race is a write-ordering issue, not a resource exhaustion issue.

## The Fix: Upgrade to Next.js 16.2.1

Upgrading Next.js resolves the issue completely:

```bash
npm install next@16.2.1
npm run build
```

After upgrading, `next build` completes without the `ENOENT` error across repeated runs. The Next.js 16.2.1 release addresses a Turbopack manifest write race condition that matches this failure mode.

## Workaround for Teams Staying on 16.1.6

If an immediate upgrade is not feasible, the `--webpack` flag on the `build` script switches the production build to Webpack instead of Turbopack:

**`package.json`:**
```json
{
  "scripts": {
    "build": "next build --webpack"
  }
}
```

In addition, adding an empty `turbopack: {}` block to `next.config.ts` suppresses configuration warnings without re-enabling the Turbopack path for builds:

**`next.config.ts`:**
```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  turbopack: {},
}

export default nextConfig
```

This combination allows production builds to complete on 16.1.6 by bypassing the Turbopack bundler path entirely. Development (`next dev`) still uses Turbopack by default unless similarly overridden.

**Trade-off:** Webpack builds are slower than Turbopack and do not benefit from Turbopack's incremental graph improvements. Treat this as a temporary measure while scheduling the upgrade.

## Root Cause Summary

The `_buildManifest.js.tmp` ENOENT is a race condition in Next.js 16.1.6's Turbopack integration during the production build's manifest finalization step. Turbopack writes a `.tmp` file and immediately issues a rename to the final path; under certain I/O scheduling conditions on macOS with Node v23, the rename races ahead of the write flush, producing ENOENT. Next.js 16.2.1 corrects the write ordering. No application code changes are required — the fix is entirely in the framework.

## Reproduction Steps

1. Create a Next.js project using Next.js 16.1.6 (App Router, TypeScript).
2. Add several pages and API routes — complexity increases the likelihood the race triggers.
3. Run `next build` repeatedly. Expect ENOENT failures on a percentage of runs.
4. Upgrade to `next@16.2.1` and run `next build` again. Failures do not recur.

## Debugging Checklist

When seeing `ENOENT` on a `.tmp` rename during `next build`:

1. Check the Next.js version. If 16.1.x with Turbopack, upgrade to 16.2.1 or later.
2. If the upgrade is blocked, add `--webpack` to the build script as a stopgap.
3. Do not invest time tuning the file system or Node.js internals — the failure is version-specific to the framework.