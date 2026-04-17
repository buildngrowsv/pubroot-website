# Pubroot — Working Roadmap

**Anchor article:** [`2026-125` — Pubroot, Six Weeks In](https://pubroot.com/se/architecture/pubroot-six-weeks-in-the-hypotheses-we-started-with-and-the-five-things-we-only-learned-by-running-it/)
(committed at `3c62fef`, published 2026-04-16, score 8.5/10, badge `text_only`)

**90-day milestone:** **2026-07-15** — at that date the next retrospective ships
under the same template. Acceptance bar for "we held the line": at least one
new submitter, at least one rejection in the corpus, and at least three
distinct external commenters across published issues. Anything weaker than
that and we update the positioning, not the goalposts.

---

## How this document works

This is the **living working list** for the Pubroot platform. The published
article (paper `2026-125`, Section 6) is the **canonical, dated promise** —
it does not change. This file evolves as we learn, and *every change here is
itself a calibration signal* — adding a new item is fine, removing one
without explanation is the kind of thing the next retrospective should call
out by name.

- **Source-of-truth ranking:** BridgeMind tasks (when one exists for a line
  item) > this file > the published article's Section 6 > ad-hoc chat.
- **Status field per item:** `todo` / `in-progress` / `complete` / `frozen`
  / `cancelled-with-reason`. Never delete an item silently — change its
  status and append a one-line "why" so the diff in git tells the story.
- **Adding a new item** that wasn't in paper `2026-125` Section 6: mark it
  with `(post-2026-125)` so the retrospective audit can see what we
  expanded the scope to mid-flight, and why. The first such item is the
  EDU & research-lab cold outreach below.

---

## Tier A — Surface improvements (carried over from paper 2026-125 §6)

These are the lessons-driven product changes the retrospective committed to
publicly. They stay numbered as in the article so external readers can
trace each line back to its evidence section.

| # | Item | Status | Evidence anchor |
|---|---|---|---|
| 1 | **Ship the grounding-tier badge.** Add a `🟣 Grounded` tier awarded when ≥80% of extracted claims in `review.json` are marked `verified`, distinct from `verified_open` (which currently means *we read your code*). Update `_site_theme/static/css/main.css` badges, `agent-index.json` schema, MCP `search_papers` filter, and Editorial Guidelines copy. | `todo` | §4.1 |
| 2 | **Split reputation into submitter / commenter.** Extend `contributors.json` schema to track external comment authors (today only the issue author accrues anything). Visually credit external commenters on the paper page next to the Gemini review. Write a one-page comment policy referenced from `pubroot guide --json` and `Editorial Guidelines`. The `m13v` thread on issues #34, #115, #26 is the proof case; the `Smscodehub` comment on #38 is the moderation edge-case. | `todo` | §4.2 |
| 3 | **Add a `disclosure` submission type.** Seventh submission type (alongside the existing six), with criteria emphasising completeness and public-availability-of-prior-art rather than novelty-vs-literature. Update `submission.yml`, `stage_1_parse_and_filter.py` allowed-types list, `stage_4_build_review_prompt.py` per-type rubric, and Editorial Guidelines. Honest acknowledgement that 11 of 51 published papers already fit this shape. | `todo` | §4.3 |
| 4 | **Freeze paid-acceleration, embeddings-v2, and the contributor leaderboard** until there is a second *submitter*. The infrastructure for those features is partially scaffolded; do not extend it. Status is intentionally `frozen` (not `cancelled`) so it can resume cleanly when contributor count is ≥2. | `frozen — gated on second submitter` | §4.2 |
| 5 | **Server-side log counts for the agent endpoints.** Put Cloudflare in front of GitHub Pages for `agent-index.json`, `journals.json`, `contributors.json`, `/agents.txt`, `/llms.txt`, `/.well-known/agent.json`. Aggregate by user-agent (OpenAI, Anthropic, Perplexity, Cursor, etc.) and publish the totals alongside the next quarterly calibration number. | `todo` | §4.4 |
| 6 | **Own `/agents.txt` and `/llms.txt` as landing surfaces.** Treat each as its own page (header, prose intro, link back to Editorial Guidelines and Submit). Publish a grounded article *about* the agent-discovery ecosystem — the GSC data shows we already rank for it (avg position 8.5–14.2 for `agents.txt` queries). Submit it under `ai/agent-frameworks` or `benchmarks/developer-tools`. | `todo` | §4.5 |
| 7 | **Publish the retrospective on pubroot.com** and run the 90-day audit on **2026-07-15** with the same evidence shape (score distribution, claim-verification rate, contributor count, external-commenter count, GSC + GA4 totals, rejection rate). | **`complete (publish step)` / `pending (90-day audit)`** | §5–§6 |

---

## Tier B — Distribution (post-2026-125)

The retrospective named "the contributor count is at least *two*" as the
unblock condition for half of Tier A. None of Tier A actually causes that
unblock. This tier exists to do the thing that does.

### B1. EDU & research-lab cold outreach **(close next step — post-2026-125)** — `todo`

**Why now:** The retrospective's §4.2 is explicit — every contributor-side
flywheel in the design (reputation tiers, paid acceleration, leaderboard,
priority queue) is *idle for one reason*: there is one submitter. Six weeks
of building more pipeline does not change that. A targeted outreach push to
audiences that *already publish in the open and benefit from speed* is the
shortest path to a second contributor and the only honest way to reach the
2026-07-15 milestone in §6.7.

**Target audiences (ranked by fit):**

1. **PhD students and early-career CS / ML researchers** who get scooped
   on novelty timing by traditional journals. Pubroot's pitch: a
   citable, dated, AI-fact-checked artifact in *minutes*, with a
   structured `review.json` they can include in tenure / fellowship
   packets as evidence of grounded review.
2. **Open-source maintainers in agent-adjacent spaces** — MCP server
   authors, A2A implementors, browser-automation framework leads,
   accessibility-API hackers (the `mediar-ai/terminator` and
   `mcp-server-macos-use` shape — `m13v` is already the proof of demand).
3. **University labs publishing technical reports** that today live in
   slow institutional repositories (DSpace, ePrints) without
   fact-checking, structured trust metadata, or any agent-readable
   surface. Lead with: same author, same content, dated AI-grounded
   review on top, MCP-discoverable.
4. **Independent applied researchers** in the Karpathy / Simon Willison
   / Eugene Yan mould who already publish openly on personal sites.
   Pubroot does not replace their site — it adds a citation surface
   with structured trust metadata and free distribution to agents.
5. **Defensive-disclosure-friendly groups** in pharma, biotech, and IP
   law (the `prior-art/` journal already has 11 papers for a reason).
   Cold outreach to AUTM tech-transfer offices, AAPS public-domain
   advocates, and patent-defensive nonprofits like LOT Network.

**Channels (ranked by signal-to-effort):**

- Cold email — the canonical outreach surface. Resend (org `buildngrowsv@gmail.com`) is already the holding-company default, so no new infra required.
- Replies on adjacent open-source GitHub repos when their issues
  intersect a Pubroot-published article (the `m13v` reverse case).
- X / Twitter DMs to public-figure researchers whose work matches an
  open journal slot. Quote the relevant published article rather than
  pitching cold.
- Lab Slacks and conference Discords — *invited only*, never paste
  links into general channels (that is the `Smscodehub` failure mode).

**Lead with proof, not pitch.** Every message must reference (a) the
8.5/10 self-review of paper `2026-125` as evidence the rubric does not
self-flatter, (b) the GSC data (`/agents.txt` ranking) as evidence
distribution exists, and (c) the `m13v` thread as evidence external
experts already engage. Three concrete artifacts, each linkable, each
public.

**Acceptance criteria for this item:**

- ≥ **30 personalised outreach messages** sent across the five target
  audiences (no mass blasts; every message names the recipient's prior
  work and points to a specific Pubroot journal slot).
- ≥ **5 substantive replies** (not autoresponders).
- ≥ **2 external submissions** received (any verdict).
- ≥ **1 external submission accepted** before 2026-07-15.
- A short outreach-results post submitted to Pubroot under
  `econ/marketing` or `se/open-source` documenting which messages
  worked, which did not, and the response rate by audience tier.

**Tracking:** maintain `tmp/pubroot-outreach-tracker.md` (gitignored,
per the `tmp/` rule) with one row per outreach message: target, link to
their prior work, channel, date sent, reply (yes/no), submission
(yes/no), notes. Roll up the public-safe summary into the outreach-
results submission above.

**Risks and mitigations:**

- *"This reads as spam."* Lead every message with the recipient's
  specific prior work and a single Pubroot article that intersects it;
  no template-only sends.
- *"Pubroot's bus factor is one."* The retrospective is itself the
  honest answer — link to it in every outreach message rather than
  hiding the fact.
- *"AI-only review is not real peer review."* Counter with the
  `m13v` thread: external human peer review is already happening on
  the platform, accreted on top of the AI review.

**Owner:** unassigned (open to a Coordinator pickup; otherwise the
solo maintainer ships the first wave of 10 messages within two weeks
of this roadmap committing).

---

## Tier C — Demand-debt freezes (carried from §6.4)

Repeated here only so the freeze is searchable in this file too:
**Stripe paid-acceleration, embeddings-v2 (vector search), and the
contributor leaderboard** stay frozen until contributor count ≥ 2.
That gate is owned by Tier B1 above. When it lifts, unfreeze Tier A
item 4 first, then prioritise embeddings-v2 (if `papers/` count is
≥ 200 by then) over the leaderboard (which only matters with
multiple contributors).

---

## Index of cross-references

- Article §1 (ground-truth snapshot): `papers/se/architecture/pubroot-six-weeks-in-…/index.md`
- Article §4.1 (grounding-tier badge): see Tier A item 1
- Article §4.2 (reputation flywheel): see Tier A items 2 + 4 + Tier B1
- Article §4.3 (prior-art journal): see Tier A item 3
- Article §4.4 (measurement blind spot): see Tier A item 5
- Article §4.5 (agents.txt SEO): see Tier A item 6
- Article §6 (the public commitment): mirrored in Tier A above
- Reproducibility scripts behind every claim:
  `scripts/pubroot_review_score_stats.py`,
  `scripts/pubroot_github_issue_comments_summary.py`,
  `scripts/pubroot_ga4_and_gsc_analytics_report.py`

---

**Last updated:** 2026-04-16 — initial commit; Tier B1 (EDU + research-lab cold outreach) added as the close next step that the retrospective implied but did not name explicitly.
