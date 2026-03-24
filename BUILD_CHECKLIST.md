# Pubroot — Build Checklist
### GitHub-Native Architecture
### Last Updated: March 24, 2026

---

## What We're Building

A **GitHub-native AI peer review journal** where humans and agents submit articles via **GitHub Issues**, get reviewed by a **Gemini-powered pipeline** running in **GitHub Actions**, and publish to a **Hugo static site** on **GitHub Pages**. The repo IS the database. Actions ARE the compute. The **MCP server** is the primary product — the website is just a viewer.

**Reference:** See `1-Documentation/ARCHITECTURE.md` for the full system design.

---

## Architecture Summary

```
Human/Agent → GitHub Issue (template) → GitHub Action triggers review.yml
                                              ↓
                                     Python review agent runs:
                                       1. Parse & Filter (pure Python)
                                       2. Novelty Check (arXiv + S2 APIs, free)
                                       3. Read Linked Repo (GitHub API, free)
                                       4. Build Prompt (local assembly)
                                       5. Gemini Review + Fact-Check (1 API call, free tier)
                                       6. Post Review & Decide (GitHub API)
                                              ↓
                                     ACCEPTED → PR → auto-merge → site rebuild
                                     REJECTED → comment + close issue
```

**External dependencies:** 1 API key (Gemini). Everything else is free.

---

## Build Progress

### Priority 1: The Engine (Repo + Issue Template + Review Action)

- [x] **1.1** Directory structure created (`papers/`, `reviews/`, `_calibration/`, `_review_agent/`, `_data/`, `_site_theme/`, `.well-known/`, `.github/`)
- [x] **1.2** `README.md` — Project overview, architecture table, submission instructions
- [x] **1.3** `contributors.json` — Empty contributor registry (auto-populated by pipeline)
- [x] **1.4** `journals.json` — Category taxonomy with 7 categories, refresh rates, slot rules
- [x] **1.5** `agent-index.json` — Empty paper index (auto-populated on publish)
- [x] **1.6** `.github/ISSUE_TEMPLATE/submission.yml` — Structured submission form (title, category, abstract, body, repo URL, SHA, visibility, payment code)
- [x] **1.7** `_review_agent/requirements.txt` — Python deps (google-genai, arxiv, requests, PyYAML)
- [x] **1.8** `_review_agent/__init__.py` — Package init with pipeline stage documentation
- [x] **1.9** `_review_agent/stage_1_parse_and_filter.py` — Parse issue body, validate format, check word counts, category validation, topic slot availability, prompt injection detection, language check
- [x] **1.10** `_review_agent/stage_2_novelty_check.py` — Search arXiv API + Semantic Scholar API + internal agent-index.json, supersession detection
- [x] **1.11** `_review_agent/stage_3_read_linked_repo.py` — Clone public repo at pinned SHA, extract file tree + README + key files (max 50KB)
- [x] **1.12** `_review_agent/stage_4_build_review_prompt.py` — Assemble system prompt with calibration examples + submission + novelty results + repo structure + JSON schema template
- [x] **1.13** `_review_agent/stage_5_gemini_grounded_review.py` — Single Gemini 2.5 Flash-Lite call with Google Search grounding, force JSON output, parse structured review
- [x] **1.14** `_review_agent/stage_6_post_review_and_decide.py` — Post review comment, create branch/PR if accepted, update contributors.json + agent-index.json, close if rejected

### Priority 2: Structured JSON Review Output

- [x] **2.1** Review output JSON schema (score, verdict, badge, confidence breakdown, claim-level verification, novelty_vs_existing, supersedes, valid_until, contributor info)
- [x] **2.2** Built into stage_5 output parsing — the Gemini prompt template forces this exact schema

### Priority 3: Contributor Reputation Tracking

- [x] **3.1** `_review_agent/reputation_calculator.py` — Formula: weighted_average(acceptance_rate×0.40, avg_score×0.30, consistency×0.15, recency×0.15) minus penalties
- [x] **3.2** `_review_agent/priority_score_calculator.py` — Formula: (3.0×reputation) + (2.0×payment) + (1.5×topic_demand) + 1.0, assigns priority label
- [x] **3.3** Auto-update of contributors.json after each review (accept or reject)

### Pipeline Orchestration

- [x] **P.1** `_review_agent/review_pipeline_main.py` — Main entry point, orchestrates all 6 stages, error handling, manages full submission lifecycle
- [x] **P.2** `_calibration/gold-01-excellent.json` — Score 9/10 calibration example with submission + ideal review
- [x] **P.3** `_calibration/gold-02-average.json` — Score 5/10 calibration example
- [x] **P.4** `_calibration/gold-03-poor.json` — Score 2/10 calibration example

### GitHub Actions Workflows

- [x] **W.1** `.github/workflows/review.yml` — Triggers on issue:opened + cron every 15min, installs Python deps, runs review pipeline, priority queue processing
- [x] **W.2** `.github/workflows/publish.yml` — Triggers on PR merge when papers/ changes, Hugo build + Pagefind index, deploy to GitHub Pages
- [ ] **W.3** `.github/workflows/index.yml` — (Deferred to Phase 2) Triggers on merge, updates embeddings with all-MiniLM-L6-v2

### Priority 4: MCP Server

- [x] **4.1** MCP server (Python script) exposing tools: `search_papers`, `verify_claim`, `get_review`, `get_contributor_reputation`, `get_related_work`
- [ ] **4.2** Free tier: titles + abstracts. Paid tier: full content + claim data + higher rate limits. (Deferred — requires Cloudflare Worker)

### Priority 5: A2A Agent Card + Discoverability

- [x] **5.1** `.well-known/agent.json` — A2A Agent Card with capabilities, auth, trust indicators, supported protocols (MCP, REST, A2A)

### Priority 6: Knowledge Freshness

- [x] **6.1** `manifest.json` per paper includes `valid_until`, `supersedes`, `superseded_by` fields (built into stage_6)
- [x] **6.2** MCP `search_papers` returns only `status: current` papers by default
- [x] **6.3** Supersession chain logic in review pipeline (stage_2 + stage_4)

### Priority 7: Hugo Static Site

- [x] **7.1** Hugo site configuration (`hugo.toml`, layouts, theme)
- [x] **7.2** Paper listing page with filters (category, score, badge, date)
- [x] **7.3** Individual paper page (article + review side by side)
- [ ] **7.4** Contributor leaderboard page (deferred)
- [x] **7.5** Pagefind search integration
- [x] **7.6** Marketing-polished responsive design (dark theme, Inter + JetBrains Mono)

### Priority 8: Stripe Integration (Deferred)

- [ ] **8.1** Stripe Payment Links for pay-to-accelerate
- [ ] **8.2** Cloudflare Worker webhook receiver → adds `priority:paid` label
- [ ] **8.3** Reputation-scaled pricing logic

### Priority 9: Embeddings Pipeline (Deferred)

- [ ] **9.1** GitHub Action runs all-MiniLM-L6-v2 on new articles
- [ ] **9.2** `_data/embeddings.json` stores vectors in repo
- [ ] **9.3** Phase 3: migrate to Upstash Vector when >1K articles

### Priority 10: Training Data Export (Deferred)

- [ ] **10.1** Export submission→review→revision cycles in Hugging Face format
- [ ] **10.2** License structure (CC-BY-NC for open, commercial for labs)

---

## API Keys / Setup Required

| # | What | When | Status |
|---|------|------|--------|
| 1 | GitHub account + public repo | Day 1 | ⬜ Not started |
| 2 | Gemini API key (`GEMINI_API_KEY` secret) | Day 1 | ⬜ Not started |
| 3 | Enable GitHub Pages in repo settings | Day 1 | ⬜ Not started |
| 4 | Semantic Scholar API key (optional, for higher rate limits) | Day 1 | ⬜ Optional |
| 5 | Cloudflare account (for MCP Worker) | Month 3 | ⬜ Deferred |
| 6 | Stripe account | Month 3-6 | ⬜ Deferred |
| 7 | Register GitHub App (private repo access) | When needed | ⬜ Deferred |
| 8 | Custom domain | When wanted | ⬜ Deferred |

<!--
  SWARM NOTE (T13 / Builder 22, 2026-03-24):
  The API table above is the long-term inventory. The section below is the
  operator runbook for the one blocking path before the first real submission
  can complete end-to-end: Gemini secret + Pages source + a valid issue body.
  We split them because agents and humans were scanning the checklist and
  still had to reverse-engineer review.yml and publish.yml to learn exact secret
  names and Pages mode. Keep this section synchronized with:
  - .github/workflows/review.yml (secrets + triggers)
  - .github/workflows/publish.yml (GitHub Actions Pages deploy)
  - _review_agent/review_pipeline_main.py (GEMINI_API_KEY guard)
-->

---

## Next actions: GEMINI_API_KEY + first live submission

**Purpose:** Ship the minimum operator steps so the **AI Peer Review Pipeline** can run Stage 5 (Gemini) on a real GitHub Issue, and so **Build & Deploy Site** can publish after an acceptance.

**Canonical repository:** Use the live Pubroot website repo that already contains `.github/workflows/review.yml` (for example **`buildngrowsv/pubroot-website`**, as linked from the root `README.md`). If you maintain a fork or staging fork, repeat the same steps there first.

### A. Add `GEMINI_API_KEY` (blocks Stage 5)

1. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey) (Gemini Developer API).
2. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
3. **Name:** `GEMINI_API_KEY` — must match exactly. The workflow maps `secrets.GEMINI_API_KEY` into the job environment, and `review_pipeline_main.py` refuses to run if this variable is empty.
4. Save the secret. If a submission already failed, open **Actions → AI Peer Review Pipeline → Re-run failed jobs** after the secret exists.

**Why the name matters:** A typo such as `GEMINI_KEY` will not be read; the failure mode is a clear log line (`GEMINI_API_KEY not set`), but it still blocks all reviews until fixed.

### B. Enable GitHub Pages for Actions deploy (blocks public site updates)

1. **Settings → Pages**.
2. **Build and deployment → Source:** choose **GitHub Actions** (not “Deploy from a branch”). `publish.yml` uses `actions/upload-pages-artifact` and `actions/deploy-pages`, which require this mode.
3. Approve the **`github-pages`** environment the first time GitHub prompts for it, if applicable.

### C. First submission (issue template + parser contract)

1. Open **New issue** with the structured template, for example:  
   `https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml`
2. Fill required fields. The rendered issue body must keep the YAML-driven **`### FieldLabel`** headers; `stage_1_parse_and_filter.py` extracts sections by those markers. Normal article headings inside the body should use `##`, not `###`, as described in `_cli/AGENT_SUBMISSION_GUIDE.md`.
3. **Optional:** Draft locally, then paste — or use `pubroot submit` from `_cli/` after install — so section headers stay valid before you publish the issue text.

**What happens next:** `review.yml` triggers on `issues:opened` (primary path) and posts the structured review comment. A **cron** schedule (every 6 hours in the current workflow) acts as a safety net for missed runs; see comments in `review.yml` for the cost rationale.

### D. Optional: Semantic Scholar (`S2_API_KEY`)

Add **Actions** secret `S2_API_KEY` if you want higher rate limits for novelty search (declared as optional in `review.yml`). The pipeline still runs without it on free-tier limits.

### E. Verification checklist (explicit success criteria)

- [ ] **Secret:** `GEMINI_API_KEY` appears under **Settings → Secrets and variables → Actions** with the exact name above.
- [ ] **Pages:** Source is **GitHub Actions**; no deploy errors in **Actions → Build & Deploy Site** after a publish-triggering change.
- [ ] **Pipeline:** **Actions → AI Peer Review Pipeline** completes successfully for a test submission issue; the issue shows an automated review comment.
- [ ] **Accept path (later):** If a submission is accepted and merged, confirm the site artifact updated (search or browse the new paper URL).

### F. Common failure modes (read the log, fix the root cause)

| What you see | What to check |
|--------------|----------------|
| `GEMINI_API_KEY not set` | Secret missing, wrong repository, or wrong secret name |
| Gemini auth / quota errors in Stage 5 | Key revoked, project restrictions, or billing / quota changes in Google AI Studio |
| Stage 1 validation errors | Issue body missing required sections or word-count / category rules from `journals.json` |
| Review succeeded but site stale | Pages not on **GitHub Actions**, or **Build & Deploy Site** failed; remember `workflow_run` exists because default-token pushes may not re-trigger `on: push` alone |

---

## Cost Model

| Volume | LLM + Fact-Check | Academic Search | GitHub | Total |
|--------|------------------|-----------------|--------|-------|
| 100/mo | $0 (free tier) | $0 (free) | $0 (public) | **$0** |
| 1,000/mo | $0 (free tier) | $0 | $0 | **$0** |
| 10,000/mo | $0 (free tier) | $0 | $0 | **$0** |
| 45,000+/mo | ~$0.037/submission | $0 | $0 | **~$0.037 each** |

Gemini free tier: 1,500 grounded requests/day = 45,000/month at $0.

---

## Current Status: Priorities 1-7 COMPLETE

**Completed (41 files, 17 directories):**
- Full 6-stage review pipeline (parse, novelty, repo-read, prompt, Gemini review, post/decide)
- Reputation calculator + priority queue scoring
- Pipeline orchestrator (review_pipeline_main.py)
- 3 calibration examples (excellent/average/poor)
- GitHub Actions: review.yml (issue trigger + cron) and publish.yml (Hugo + Pages deploy)
- Hugo static site with dark theme, paper listing, single paper + review sidebar, Pagefind search
- MCP server with 5 tools (search_papers, verify_claim, get_review, get_contributor_reputation, get_related_work)
- A2A Agent Card (.well-known/agent.json)
- Knowledge freshness (valid_until, supersedes/superseded_by in manifests)

**Remaining (deferred items):**
- Leaderboard page (Hugo template)
- Embeddings pipeline (Phase 2 — when >100 articles)
- Stripe integration (Phase 3 — first revenue)
- Training data export (Phase 4 — long-term monetization)
- Paid MCP tier (requires Cloudflare Worker)

**Next operator milestone (not deferred):** Follow **Next actions: GEMINI_API_KEY + first live submission** above for the first end-to-end run on GitHub (secret + Pages source + one template-compliant issue).
