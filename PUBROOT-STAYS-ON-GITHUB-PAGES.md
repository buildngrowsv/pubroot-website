# PUBROOT STAYS ON GITHUB PAGES + GITHUB ACTIONS

> **Status:** Operator-confirmed long-term carve-out, effective 2026-04-19.
> Do not touch the deploy mechanism without escalating.

## In one sentence

Pubroot is **permanently exempt** from the no-GitHub-Actions deny list and
from the Vercel-to-Cloudflare migration. Its deploy + AI-review pipeline
**stays on GitHub Pages + GitHub Actions** until the Operator (not a
coordinator, not a reviewer, not a builder) explicitly says otherwise.

## Where the binding rule lives

- Canonical rule: `UserRoot/.claude/rules/pubroot-stays-on-github-pages-and-actions.md`
- Cursor mirror: `UserRoot/.cursor/rules/pubroot-stays-on-github-pages-and-actions.mdc`
- Companion deny-list (which this carves out from):
  `UserRoot/.claude/rules/no-github-actions-build-discipline.md`
  → see "Long-term carve-outs (operator decisions)" section.
- Operator-decision evidence:
  `UserRoot/.bridgespace/swarms/pane1776/SCOUT1-GH-ACTIONS-AUDIT-2026-04-19.md`
  §3 class (c), and the SWARM_BOARD pane1776 entry closing T1776-25 with
  "Operator decision = Option B (`--skip-repo buildngrowsv/pubroot-website`)".

Read those files in full before doing anything that would change pubroot's
hosting, deploy mechanism, or workflow files.

## What is forbidden in this repo without an explicit Operator override

1. Adding `wrangler.toml` / `wrangler.jsonc`, OpenNext, D1 / KV / R2 /
   Queues / Durable Objects, or any Cloudflare Workers code.
2. Replacing `.github/workflows/publish.yml` with a `wrangler pages deploy`
   flow (whether local or remote).
3. Replacing `.github/workflows/review.yml` with a Cloudflare Worker on a
   Cron Trigger + Webhook Worker.
4. `git rm` or stubbing either workflow file (no `# DEPRECATED` stub, no
   `on: workflow_dispatch:` neutering).
5. Pointing the `pubroot.com` `CNAME` at any non-GitHub-Pages endpoint.
6. Adding pubroot as a tenant row in `Github/symplyai-platform/`.

## What IS still allowed

- Editing the review pipeline Python under `_review_agent/`.
- Editing the Hugo theme + content (`_site_theme/`, `papers/`, `reviews/`,
  the JSON indexes, the static assets).
- Putting Cloudflare in front of GitHub Pages as a thin reverse proxy for
  agent endpoints (ROADMAP Tier A row 5) — origin stays on Pages.
- A future "paid MCP tier" Worker on its own subdomain (e.g.
  `mcp.pubroot.com`) per `BUILD_CHECKLIST.md` 4.2 + 8.2 — does not replace
  the static site or the review pipeline.
- Adding protective non-build workflows from the
  `no-github-actions-build-discipline.md` §4 allowlist (gitleaks PR scan,
  pr-path-guard, triage automation).

## How to lift the carve-out

The carve-out is a long-term Operator decision, not a TODO. To remove it:

1. The Operator files an instruction that names the carve-out rule file
   (`pubroot-stays-on-github-pages-and-actions.md`) by filename and
   states the new decision.
2. A coordinator opens a tracked migration ticket (`PUBROOT-CF-MIGRATION-XXXX`)
   with hosting target, pipeline re-architecture plan, secret migration
   plan, DNS cutover plan, and rollback plan.
3. The Operator approves the ticket.
4. Only then may any agent edit the workflows here or add Workers
   infrastructure to this repo.

Until step 4, this carve-out is binding.
