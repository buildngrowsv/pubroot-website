# Pubroot read-only MCP server (Cloudflare Worker, Free plan)

This directory holds the hosted, **read-only** Pubroot MCP server for
`https://mcp.pubroot.com/mcp`. It is the endpoint `server.json` advertises under
`remotes` (streamable-http, no auth). Decision D-23 (9 Nov 2026): build it on the
Cloudflare **Workers Free** plan with no spend.

**Status: not deployed.** Nothing in this repo deploys it. CI only typechecks and
tests it. Adam deploys it by hand with the steps below.

- Transport: MCP Streamable HTTP, stateless, JSON responses (`POST /mcp`).
  `GET /mcp` returns `405` because this server has no standalone SSE stream,
  which the spec allows. There are no sessions, so `DELETE /mcp` is `405` too.
- Other routes: `GET /healthz` returns `{"ok": true, ...}`. `GET /` is a short
  HTML page linking to https://pubroot.com and `/mcp`. CORS is open for
  GET/POST/OPTIONS.
- Built with the official `@modelcontextprotocol/sdk`
  (`WebStandardStreamableHTTPServerTransport` in stateless mode).
- Data: the same public files `src/pubroot/mcp_server.py` uses, fetched read-only
  from `DATA_BASE_URL` (a plain `[vars]` entry in `wrangler.jsonc`, default
  `https://raw.githubusercontent.com/buildngrowsv/pubroot-website/main`):
  `agent-index.json`, `priorroot-index.json`, `journals.json`,
  `contributors.json` and `reviews/<id>/review.json`.
- No bindings: no Durable Objects, KV, D1, R2, Queues, AI, Rate Limiting binding
  or secrets. No `account_id` is committed.

## Tools

All tools are annotated `readOnlyHint: true`. None of them write anything.

| Tool | What it returns |
|---|---|
| `search_papers` | Papers filtered by `query`, `category`, `min_score`, `badge`, `status`, `limit` (1–50), sorted by score |
| `verify_claim` | Claims in published reviews that overlap with `claim` (verified flag, confidence, source) |
| `get_review` | Full review JSON for `paper_id` |
| `get_contributor_reputation` | Public contributor record for `github_handle` |
| `get_related_work` | Related papers for `query` and/or `paper_id` |
| `get_submission_guide` | Submission rules (same content as `pubroot guide --json`) |
| `prepare_submission` | Validates a draft and returns a prefilled GitHub issue URL plus a `gh` command. **It never creates the issue.** |
| `list_journals` *(new)* | Journals and their `journal/topic` categories |
| `get_paper` *(new)* | Index entry for `paper_id` from `agent-index.json` or `priorroot-index.json` |

The first seven tools use the Python server's names, input parameters and output
shapes. Differences from the Python server:

- **Input validation.** `paper_id` must match `YYYY-NNN`, `github_handle` must be a
  valid GitHub login, and strings have length caps (query 500, claim 1,000,
  title 300, abstract 10,000, body 200,000). A bad argument returns a tool result
  with `isError: true` and `{"error": "..."}`. An unknown tool name returns a
  JSON-RPC `-32602` error.
- **`verify_claim` fetch cap.** It reads at most 20 review files per call, taking
  the strongest title/abstract matches first. This keeps every call under the
  Free plan's 50-subrequest limit.
- **Category validation in `prepare_submission`.** It reads `journals.json` in its
  real shape (an object keyed by journal slug, with `topics` keyed by topic slug).
  The Python server expects a list here, so it only adds a "could not validate"
  warning and never checks the category.
- **Long URL warning.** `prepare_submission` adds a warning when the prefilled
  issue URL is longer than 8,000 characters.

## Free-plan design

| Free-plan limit | How the Worker stays inside it |
|---|---|
| 100,000 requests/day | Responses are small and stateless. Best-effort per-IP limits in isolate memory: 60 MCP requests/min and 10 `prepare_submission` calls/min, the same as the Python HTTP server. Counters are per isolate, so the limits are approximate. No paid Rate Limiting binding is used. |
| 10 ms CPU per request | Parsed upstream JSON is kept in isolate memory for `CACHE_TTL_SECONDS` (600). If upstream fails, the last good copy is served for up to 24 h. Upstream fetches also pass `cf: { cacheTtl }`, which is free. Tool schemas are plain JSON Schema, so nothing is converted per request. Bodies are capped at 1 MiB. |
| 50 subrequests per request | The most any call uses is 21 (`verify_claim`: 1 index plus at most 20 reviews). |
| Worker size | The dry-run bundle is 740.53 KiB (148.53 KiB gzip). Older docs gave a 3 MB compressed limit for Free; the current limits page lists 64 MiB uncompressed. The bundle is under both. |

Sources: https://developers.cloudflare.com/workers/platform/limits/ and
https://developers.cloudflare.com/workers/platform/pricing/

## Develop and test locally

```bash
cd mcp-worker
npm ci
npm run typecheck   # tsc --noEmit
npm test            # vitest; upstream fetch is mocked with fixture JSON, so no network
npx wrangler deploy --dry-run --outdir dist   # bundles only; no login needed
npx wrangler dev    # local workerd at http://localhost:8787 (reads the live public JSON)
```

## Deploy (Adam, manual)

### 1. Prerequisite: where pubroot.com's DNS lives

Checked on 9 Nov 2026 with `dig`:

- Nameservers are GoDaddy: `ns31.domaincontrol.com` and `ns32.domaincontrol.com`.
- Apex `A` records point to GitHub Pages: `185.199.108.153`, `185.199.109.153`,
  `185.199.110.153`, `185.199.111.153`.
- Apex `AAAA` records point to GitHub Pages: `2606:50c0:8000::153`,
  `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`.
- `www` is a `CNAME` to `buildngrowsv.github.io`.
- TXT records: `google-site-verification=…` on the apex,
  `_github-pages-challenge-buildngrowsv` (GitHub Pages domain verification), and
  `_dmarc`.
- No `MX` records, no `DS` record (DNSSEC is off), and `mcp.pubroot.com` does not
  exist yet.

Workers Custom Domains need the zone to be **active on Cloudflare**, which means
Cloudflare must be the nameserver
(https://developers.cloudflare.com/workers/configuration/routing/custom-domains/).
Moving DNS to Cloudflare is a **DNS-provider change, and it is Adam's decision.**
GitHub Pages hosting does not change, and `publish.yml` and `CNAME` stay as they are.

**Option A: free path, move DNS to Cloudflare (needed for `mcp.pubroot.com`).**

1. In the Cloudflare dashboard, add the site `pubroot.com` and pick the **Free** plan.
2. Let Cloudflare import the existing records. Compare them with the list above
   and add any that are missing: all 4 `A`, all 4 `AAAA`, the `www` CNAME and
   all three TXT records.
3. Set the GitHub Pages records to **DNS only (grey cloud)**: the apex
   `A`/`AAAA` records and the `www` CNAME. GitHub Pages then keeps serving the
   site and renewing its TLS certificate exactly as it does today.
4. Do not create a record for `mcp`. `wrangler deploy` creates it in step 2.
5. At GoDaddy, under Domain → DNS → Nameservers → "I'll use my own nameservers",
   enter the two nameservers Cloudflare gives you. DNSSEC is currently off, so
   there is nothing to disable first.
6. Wait until Cloudflare shows the zone as **Active**. This usually takes minutes
   but can take up to 24 h. Then check `https://pubroot.com` still loads from
   GitHub Pages:
   `curl -sI https://pubroot.com | grep -i server` should still show `GitHub.com`.

**Option B: no DNS change (fallback).** Skip step 1 and deploy anyway. The Worker
is still reachable on its free `workers.dev` URL:
`https://pubroot-mcp.<your-subdomain>.workers.dev/mcp`. With the zone not on
Cloudflare, the `mcp.pubroot.com` custom-domain route in `wrangler.jsonc` is
expected to make `wrangler deploy` fail, because the zone can't be found. For a
workers.dev-only deploy, delete the `routes` block from your local, uncommitted
copy of `wrangler.jsonc` before deploying. `server.json` keeps advertising
`mcp.pubroot.com`, so only use this path as a stopgap.

### 2. Deploy

```bash
cd mcp-worker
npm ci
npx wrangler login     # opens a browser; log in to the Cloudflare account (Free plan)
npx wrangler deploy
```

Once the zone is active on Cloudflare, `wrangler deploy` creates the
`mcp.pubroot.com` Custom Domain (DNS record and certificate) from the `routes`
entry. The output also prints the `workers.dev` URL.

### 3. Verify

```bash
curl -s https://mcp.pubroot.com/healthz
# {"ok":true,"service":"pubroot-mcp","version":"0.2.0"}

curl -s https://mcp.pubroot.com/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'

curl -s https://mcp.pubroot.com/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -H 'mcp-protocol-version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

curl -s https://mcp.pubroot.com/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -H 'mcp-protocol-version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_papers","arguments":{"query":"agent","limit":2}}}'
```

Optional interactive check: run `npx @modelcontextprotocol/inspector`, choose
transport "Streamable HTTP" and URL `https://mcp.pubroot.com/mcp`.

With Option B, use `https://pubroot-mcp.<your-subdomain>.workers.dev` in place of
`https://mcp.pubroot.com`.

### Roll back

Run `npx wrangler delete` (removes the Worker and its custom domain), or remove
the custom domain in the dashboard. The Pages site is not affected either way.

## Cost

- **Workers Free plan only.** Nothing here needs Workers Paid: no Durable Objects,
  KV, D1, R2, Queues, Workers AI, Rate Limiting binding, Logpush, paid Smart
  Placement, secrets or other paid add-ons. `observability` is off in
  `wrangler.jsonc`.
- **Card.** Cloudflare's pricing page says new accounts start on the Workers Free
  plan by default. It does not say whether signup asks for a payment card. Do not
  add one. If the dashboard ever demands a card for anything in these steps,
  stop: that would be outside D-23.
- **Custom domain and DNS.** Neither the Custom Domains docs nor the pricing page
  lists a charge for them, and the zone uses the Cloudflare **Free** plan.
- **The 100,000 requests/day limit.** It resets at midnight UTC. Past the limit,
  requests to the Worker fail with Cloudflare **Error 1027**: the route either
  returns the 1027 page (fail closed) or bypasses the Worker (fail open), and
  `mcp.pubroot.com` has no origin behind it either way. The account is not moved
  to a paid plan, and Cloudflare's docs describe no automatic billing for going
  over the limit, so there is no surprise bill.
- **Upstream.** It reads public files from `raw.githubusercontent.com`, which is
  free, and the edge and in-memory caching keep request volume low.
