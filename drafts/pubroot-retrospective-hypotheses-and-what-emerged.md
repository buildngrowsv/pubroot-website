

### Article Title

Pubroot, Six Weeks In: The Hypotheses We Started With, and the Five Things We Only Learned by Running It

### Category

se/architecture

### Submission Type

case-study

### AI / Tooling Attribution (optional)

Written from a direct read of the `buildngrowsv/pubroot-website` repo on 2026-04-16 by a Cursor agent (Claude, Composer-series) working from the public design docs under `1-Documentation/`, the BUILD_CHECKLIST, and the live `papers/`, `reviews/`, and `contributors.json` files. The production AI reviewer referenced throughout is Google Gemini 2.5 Flash-Lite with Google Search grounding; the tooling that builds the pipeline around it was authored with Composer 2 in Cursor. This retrospective is not itself a review produced by either model.

### Abstract

Pubroot started as a two-session conversation in February 2026 about whether you could run an AI-first peer-reviewed journal for free on GitHub, and whether the result would be worth anything. Six weeks after the engine first ran end-to-end, there are 51 published papers, 47 structured reviews with claim-level verification, an MCP server exposing the corpus to agents, a live site at pubroot.com, and — quietly — five substantive technical comments from an external maintainer working in the same problem space. This retrospective restates the original hypotheses, reports which ones survived contact with a running system, and names five things we only learned by actually operating it. The zero-cost architecture worked as designed and has not broken. The reputation-driven priority queue was designed around *submissions* and has not turned; the thing that *did* start turning — external comments on accepted articles — is a loop the system was not built to reward. Gemini's grounded-search step, bought for fact-checking, quietly became the most valuable artifact the system produces (96.4% claim-verification across 165 extracted claims), a stronger guarantee than the current trust badges advertise. A journal we did not plan for — defensive-disclosure prior art — emerged from operational need and now holds 11 of the 51 papers. And the single most-indexed URL in Google Search Console for pubroot.com is not an article: it is `/agents.txt`, which on its own accounts for every click in the first quarter of organic search traffic. We close with the roadmap those five surprises actually imply, which is meaningfully different from the one we shipped.

### Article Body

## 1. A short ground-truth of the system as it stands

Before reflecting, the numbers so nothing below reads as vibes. All figures pulled from the live repo, the live GA4 property (created 2026-04-02), and Google Search Console on 2026-04-16.

**On disk and on the site:**

- **51 paper folders** under `papers/`, across 11 journal/topic slots of the 97+ declared in `journals.json`.
- **47 structured `review.json` files** under `reviews/` — the four papers without one predate the current schema.
- **1 submitting contributor** (`buildngrowsv`) across every row of `contributors.json`. That is the same number as at launch.
- **Site live** at [pubroot.com](https://pubroot.com) on GitHub Pages, rebuilt on merge.
- **MCP server** exposing five tools (`search_papers`, `verify_claim`, `get_review`, `get_contributor_reputation`, `get_related_work`) against the repo as the database.
- **Fixed monthly cost**: zero. Variable cost so far: also zero — every review is inside Gemini 2.5 Flash-Lite's free-tier grounding budget.

**On the GitHub issue threads (which is where "peer review" is actually visible):**

- **71 submission issues**, **59 with at least one comment**, **11 with more than one comment**.
- Comment author distribution across the corpus: `github-actions[bot]` 68, the submitter 8, external commenters **6 comments from 2 distinct users**.
- The two external commenters are `**m13v*`* (5 comments, substantive technical engagement across three articles, linked their own macOS MCP server and Rust accessibility crate) and `**Smscodehub**` (1 comment that reads as promotional — a moderation edge case worth naming).

**On the measurement surface (first time we have actually looked):**

- **GA4** (`G-KJ4QTQ2S7C`, property `531004173`, created 2026-04-02): in its first two weeks of data, **10 users, 19 sessions, 34 pageviews, average session duration 2m 38s**. Every session is attributed to `(direct) / (none)` because the property is too young to have captured its first organic-search referrers. 8 US, 1 CA, 1 SG. Desktop:mobile roughly 12:7.
- **Google Search Console** (`sc-domain:pubroot.com`, last 90 days): **234 impressions, 4 clicks, CTR 1.7%, average position 9.4**. The single highest-ranked and highest-trafficked URL on the entire site is not an article — it is `**/agents.txt`** at 145 impressions and all 4 of the organic clicks. `/llms.txt` is second for clicks. The homepage has 54 impressions and zero clicks.

That is the surface. The rest of this article is about what we expected that surface to mean and what it actually means.

## 2. What we set out to prove

The earliest design notes are under `1-Documentation/` in the repo. They are worth reading in order — two raw user-input sessions, then a set of research files, then an architecture document dated 2026-02-15. From those files the hypotheses were roughly these, in the order they got written down:

**H1 — Zero-cost is possible.** GitHub Issues for intake, GitHub Actions for compute, GitHub Pages for hosting, the repo itself as the database, and one free-tier LLM API. No servers, no databases, no subscriptions.

**H2 — An LLM can peer-review well enough if the rubric is fixed and calibrated.** A single prompt with a typed schema and a small number of hand-written gold examples would pin the reviewer's behaviour close enough to make scores meaningful.

**H3 — The primary consumers will be agents, not humans.** Agents do not read websites; they consume structured JSON through MCP, read `agents.txt`/`llms.txt` for discoverability, and chain claims through `/.well-known/agent.json` cards. The human-readable site is a viewer; the machine-readable surfaces are the product.

**H4 — A reputation-driven priority queue replaces human editors.** Contributors who submit good work accumulate reputation; high-reputation contributors get faster reviews; spam submitters sink to the back of the queue. Combined with a paid-acceleration lane (Stripe → `priority:paid`), this gives two ways to move up the queue — earn it or buy it — and keeps the system self-regulating at steady state.

**H5 — Novelty is actually checkable.** Gemini grounded-search plus arXiv plus Semantic Scholar plus an internal embedding index would tell us whether a submission duplicates prior work badly enough to reject.

**H6 — There might be a business here, eventually.** The founding conversation is honest about this: "I don't see a clear business model for it." The architecture doc then optimistically lays out five revenue phases, the earliest of which (pay-to-accelerate + GitHub Sponsors) would not begin until month 3–6.

Six weeks in, H1, H2, and H3 are substantially proven — with caveats. H4, H5, and H6 are largely untested, for the same underlying reason, which is worth stating plainly: the system only has one contributor. Everything that needs a *distribution* of contributors to validate is still waiting.

## 3. What the build actually delivered

The BUILD_CHECKLIST shows that roughly 70% of the originally-scoped work is merged and running. The six-stage Python pipeline (`_review_agent/stage_1` through `stage_6`) is live. The MCP server with five tools is live. The Hugo theme, the calibration goldens, the reputation calculator, the priority queue, the A2A Agent Card, `agents.txt`, `llms.txt`, `agent-index.json`, and `journals.json` are all committed and served.

The deferred items are also worth naming, because most of them are deferred *for a reason that emerged during operation*, not because they are hard:

- **Stripe paid-acceleration** is not wired up. The queue has never been long enough for speed to be worth buying.
- **Embeddings pipeline (Phase 2 vector search)** is not wired up. At 51 papers, Pagefind's static client-side index is still faster to query and cheaper to maintain than anything vector-backed would be.
- **Contributor leaderboard page** is not built. With one contributor it would render as a nameplate, not a leaderboard.
- **Training-data export** is not built. At 47 reviews there is nothing worth licensing.

All three of those items were baseline requirements in the original architecture. All three are now correctly deferred. The interesting pattern is that nothing in the deferred list is *technical debt*; all of it is *demand debt* — infrastructure whose value is a function of inputs we do not yet have.

## 4. The five things we only learned by running it

This is the part of the retrospective that justifies writing one. Everything above could have been written from the architecture document and a git log. The things below only show up in a running system.

### 4.1 Gemini's grounded search was supposed to be the *fact-check step*. It became the most valuable artifact the system produces.

When we picked Gemini 2.5 Flash-Lite with Google Search grounding, we picked it for two boring reasons: (a) it collapses "call the LLM" and "check a fact on the web" into a single API call, and (b) the free tier absorbs the entire expected volume for the foreseeable future. We thought of grounding as a cost-reducer and a pipeline simplifier.

What actually happened, once we had 47 reviews in the bank: the **`claims` array** that Gemini emits for every review — extracted factual statements with per-claim `verified` flags and source URLs — is by a wide margin the most interesting data the pipeline produces. Across the 47 reviews there are 165 extracted claims and 159 of them are marked verified, with sources attached. That is a 96.4% verification rate. It is narrower than it sounds (the reviewer only surfaces claims it thinks it can check, so this is a ceiling), but it is still a structurally new kind of object: a machine-readable trust breakdown of an article at the *claim* level, published alongside the article itself.

The consequence is that the current trust badges understate what Pubroot actually does. Our badge taxonomy is `verified_open`, `verified_private`, `text_only` — it maps to *whether a supporting repo was readable*. It says nothing about *whether the claims in the article were checked*. 83% of our papers are `text_only`. Those same papers carry 96% claim verification. A reader skimming badges sees under-trust where evidence on disk shows high trust. Pubroot needs a grounding-tier badge — **🟣 Grounded** is a working name — that splits those two ideas apart. That redesign was not in the original plan; it falls out of watching the system run.

### 4.2 The reputation flywheel we designed is idle. A different flywheel — external commentary on accepted articles — has already started turning, and the system doesn't reward it.

The reputation system is elegant on paper. `reputation_score = 0.40·acceptance_rate + 0.30·avg_review_score + 0.15·consistency_bonus + 0.15·recency_bonus`, decayed for inactivity, penalised for prompt-injection attempts. Five tiers — *new*, *emerging*, *established*, *trusted*, *authority* — each with its own free-review budget and priority-queue position. It is all there in `_review_agent/reputation_calculator.py` and `priority_score_calculator.py`.

In practice, `contributors.json` has **one** row. The sole submitter sits at `reputation_tier: "new"` with `reputation_score: 0.0` despite 31 accepted submissions and a 7.62 average score. That is almost certainly a tier-promotion bug, but the more honest observation is that it does not *matter* because the queue has always been short enough to process in real time. Paid acceleration would purchase nothing you do not already get for free. The submission-side flywheel is idle, and building more infrastructure for it will not unstick that — only contributors will.

**But something we did not design for *has* started.** The GitHub issue threads show that the Gemini review is no longer the only voice on some papers. On issue #34 ("Background macOS Desktop Automation via Accessibility API"), an external maintainer `m13v` replied with a real peer-review comment: confirmation of the Safari-vs-Chrome observation from hands-on experience, a concrete pattern worth adopting ("use element roles and labels for targeting, not coordinates"), and an important edge case — "Safari can reindex windows when one is closed, so window-by-index needs a verification step." Two minutes later the same commenter posted two open-source references from their own work at `mediar-ai`. A few days later, on issue #115 about `AXUIElement` traversal, they wrote:

> "The part that breaks down in practice is AXUIElement tree traversal performance on Electron apps. A typical Slack or VS Code window can expose 3000+ nodes, and walking the full tree with `AXUIElementCopyAttributeValues` takes 400-800ms per traversal. Your caching approach helps but cache invalidation is the real nightmare … We ended up doing partial tree diffing on a 50ms polling loop, only re-traversing children of nodes whose `AXChildrenChanged` notification fired. Cut our average traversal to under 15ms for incremental updates."

That is peer review in the traditional sense of the word — an expert, reading a claim, stress-testing it against their own production experience, and handing back a specific, checkable improvement. It is substantively better than the automated review on the same paper. And across the corpus there are **five** comments of this kind from this one reviewer across three different articles.

The Pubroot reputation system currently does not see any of this. `contributors.json` only tracks people who open *issues* (submissions); it does not track people who post *comments* on issues. A reviewer providing more value than the acceptance pipeline cannot accrue reputation for it. This is not a small omission; it is the shape of the actual peer community the platform attracted first, and the system was blind to it by construction.

There is also a second external commenter, `Smscodehub`, who posted one comment promoting a third-party service as a way to bypass SMS verification. Fine line between on-topic contribution and promotional spam, but leans promotional. Pubroot has no posted comment policy and no moderation tooling; with two external commenters, one genuinely expert and one promotional, it is already time to write one.

Three concrete consequences follow:

1. **Split the reputation schema.** `submitter_reputation` (what we have) and `commenter_reputation` (what we don't). Commenter reputation accrues from substantive comments on accepted articles, lightly moderated.
2. **Credit commenters on the paper page.** A published article should visually attribute its external comment thread the same way it shows the Gemini review, including outbound attribution to commenter GitHub profiles and any linked work they cited. This turns Pubroot from a "reviewed by Gemini" surface into a genuine hybrid.
3. **Write the comment policy now, not later.** Before the second `Smscodehub` shows up. One page, machine-readable via `pubroot guide --json`, aligned with the spirit of Editorial Guidelines.

### 4.3 A journal we didn't plan for is already our second-biggest.

The original taxonomy had journals like *AI*, *Computer Science*, *Software Engineering*, *Economics*, *Benchmarks*. Those were the "obvious" knowledge domains. There was no journal for **defensive disclosure of prior art**.

What emerged instead: as the solo contributor shipped technical and therapeutic innovations in parallel, the highest-signal use of the pipeline was not "publish a research paper" but "timestamp a public-domain method description so nobody can patent around it later". Twenty-plus years of doing this pattern casually on blogs, mailing lists, and IP.com suddenly had a cheaper, dated, AI-fact-checked version of itself. We added a `prior-art/` journal mid-flight — `general-disclosure`, `device-method`, `software-method`, `therapeutic-use` — and it has absorbed **11 of the 51 papers**, second only to `ai/agent-architecture` at 18.

This is the thing you cannot plan for in an architecture document: a journal is not really a taxonomy problem, it is a shape-of-demand problem, and you can only learn the demand by running the pipeline against real work. Two corollaries fall out. First, the taxonomy must be easier to extend than we made it; currently adding a topic means editing `journals.json`, the issue template enum, and sometimes the parser — a surprising amount of friction for a schema that is supposed to be the adjustable part of the system. Second, the *six submission types* (original research, case study, benchmark, review/survey, tutorial, dataset) may be missing a seventh: **disclosure**. A defensive-disclosure article is judged by different criteria than a research paper — the reviewer should score it on completeness and public-availability-of-prior-art, not on novelty-vs-literature, because the whole point is that it deliberately makes the method un-patentable.

### 4.4 The site runs fine, but the measurement surface was built for humans and the consumers are agents.

The original architecture said *agent-first, human-readable*. The first month of building still leaned human: we wired GA4 into the Hugo theme (`G-KJ4QTQ2S7C`, property created 2026-04-02), added OG cards, added sitemap and canonical URLs, shipped a `ScholarlyArticle` JSON-LD block on paper pages for Google Scholar.

None of that instruments the actual consumer we designed for. GA4 does not see a call to `agent-index.json` from a Cursor agent resolving a claim during a coding session. It does not see an MCP client pulling `review.json` from the repo through `search_papers`. It does not see an A2A card read from `/.well-known/agent.json`. GA4's first two weeks report **10 users, 19 sessions, 34 pageviews**, 100% `(direct) / (none)` — which is partly property-age (organic attribution takes weeks to populate) and partly the structural invisibility described here. The "successful" path of Pubroot is by construction not in GA4.

The short-term move is pragmatic: add a small server-side access log for the JSON endpoints (Cloudflare in front of GitHub Pages is the cheapest path), count agent-identifiable User-Agent strings (OpenAI, Anthropic, Perplexity, Cursor crawlers), and publish the numbers in the quarterly calibration disclosure. The longer-term move is that *how to measure agent publishing* is itself a research topic this journal could host an article on, ideally from someone who is not us.

### 4.5 The most-indexed URL on pubroot.com is not an article. It is `/agents.txt`.

This one is worth reading twice. Google Search Console for `sc-domain:pubroot.com` over the last 90 days reports 234 impressions and 4 organic clicks. Those 4 clicks did not land on a paper. They all landed on the agent-discovery file:


| Page                                        | Impressions | Clicks |
| ------------------------------------------- | ----------- | ------ |
| `/agents.txt`                               | 145         | 4      |
| `/` (homepage)                              | 54          | 0      |
| `/ai/agent-architecture/file-ownership-...` | 24          | 0      |
| `/llms.txt`                                 | 10          | 1      |


The search queries tell the same story. `agents.txt` / `agents txt` / `agents txt file` / `agent.txt` together account for 26 impressions, and the #1 exact-match ranking on `agents.txt` is already inside the first page of Google (avg position 8.5–14.2). There is even `inurl:llms.txt filetype:txt` — someone actively searching for sites that publish an `llms.txt` file — and Pubroot appears for it.

Nobody designed Pubroot to rank for `agents.txt`. We added the file because the standard exists and we believed in publishing everything agents might expect. The consequence is that the *only* channel currently driving organic search traffic to the site is its agent-discovery infrastructure, not its editorial output. That is not a bug. It is a signal about who is finding us and why — and about what a human searching for "agents.txt" on Google probably wants, which is an example of what one looks like in production. We are, currently, one of the examples.

Two things follow:

1. **Own the `agents.txt` / `llms.txt` lane intentionally.** Treat each file as its own landing surface: a concise, discoverable reference that explains what Pubroot exposes to agents, with a link back to the Editorial Guidelines and submission entry point. The files already exist; they deserve the kind of polish we currently reserve for article pages.
2. **Publish a short article *about* the `agents.txt` / `llms.txt` ecosystem** (this qualifies under `ai/agent-frameworks` or `benchmarks/developer-tools`). It is a real, ranking topic. Nobody else is writing the grounded version of it. If Pubroot is already winning that slot by accident, it should win it on purpose.

## 5. What it taught us about AI-native publishing

Stepping back from Pubroot-the-system to AI-native publishing as a shape:

- **Repo-as-database aged better than expected.** Six weeks of daily writes, multiple schema migrations, zero operational incidents. Git is already an audit log. GitHub Actions is already a free compute layer. GitHub Pages is already a CDN. Everything in the stack has a cheap, portable migration path if any single layer changes its mind about pricing.
- **Grounded LLM calls are quietly more valuable than ungrounded ones.** If we had used a non-grounded model, we would still have reviews, but we would not have the `claims` object, and the whole trust story collapses onto subjective prose. The combination of a typed review schema + a grounded model + a commit to publish the raw output together is where Pubroot's credibility actually lives.
- **Zero-cost does not mean zero-accountability.** Because every review is in git, every calibration drift leaves a record, every disagreement between reviewer and reader can be pinned to a SHA. A traditional journal cannot do this; Pubroot's honest advantage is that its mistakes are public by construction.
- **The first "peer" to show up was a commenter, not a submitter.** The design assumed reviewer and submitter were the same role, rotated through the pipeline. Reality: an external expert read an accepted article, replied on the issue thread with substantive follow-up, and gave us the single best data point about the topic in the corpus. The platform has to be built for that shape too.
- **The infrastructure layer is a distribution channel.** `/agents.txt` ranks. `/llms.txt` ranks. In the first 90 days these files, not the article pages, are how Google is indexing Pubroot. If you are building anything agent-facing and expecting articles to carry SEO alone, you are leaving the easy win on the table.
- **The market might not be where we pointed the product.** The architecture optimised for autonomous agents querying verified knowledge. The use that actually showed traction in six weeks was a solo builder using the pipeline as a dated, fact-checked notebook — and a defensive-disclosure engine. That is a different product. It is not worse, it is just not what the spec said.

## 6. An honest roadmap

Condensed from the five lessons above, the next ninety days' work on Pubroot should be, in order:

1. **Ship the grounding-tier badge** so the trust story matches what the pipeline actually does (§4.1).
2. **Split reputation into submitter/commenter, credit external commenters on the paper page, and write a comment policy** (§4.2).
3. **Add a `disclosure` submission type** with criteria tuned for defensive prior-art, and commit to keeping it a first-class shape of the journal (§4.3).
4. **Freeze paid-acceleration, embeddings-v2, and the leaderboard** until there is a second *submitter* (§4.2). Do not build demand infrastructure for absent demand.
5. **Add server-side log counts for the agent endpoints** (JSON files, `/agents.txt`, `/llms.txt`) and publish them quarterly alongside the calibration numbers (§4.4).
6. **Own `/agents.txt` and `/llms.txt` as landing surfaces** and publish a grounded article explaining the ecosystem to the people already searching for it (§4.5).
7. **Publish this retrospective on pubroot.com** and treat the 90-day mark as the first checkable milestone: same shape of evidence, at least one new submitter, at least one rejection, and at least three external commenters across the corpus — or we update the positioning.

Pubroot was built from a skeptical question — "I don't see a clear business model for it" — and a very strong conviction that structured, grounded, agent-readable knowledge would matter. Six weeks in, the conviction is holding and the business-model question is still open. That is an honest place to be. The system works; the market is the next experiment.

## References & linked artifacts

- Design history: `1-Documentation/` in the source repo — two raw user-input sessions, seven research files, and the v1.0 architecture doc dated 2026-02-15.
- Live pipeline: `_review_agent/stage_1` through `stage_6`.
- Build state: `BUILD_CHECKLIST.md` (shows which deferred items are demand-debt vs technical-debt).
- Reproducibility — the three read-only analysis scripts behind every number in this article: `scripts/pubroot_review_score_stats.py` (review dimensions), `scripts/pubroot_github_issue_comments_summary.py` (external commenters), `scripts/pubroot_ga4_and_gsc_analytics_report.py` (GA4 + GSC totals). Each uses only the standard library plus the workspace OAuth helper; no secrets in git.
- Machine-readable surfaces: [`/agent-index.json`](https://pubroot.com/agent-index.json), [`/journals.json`](https://pubroot.com/journals.json), [`/contributors.json`](https://pubroot.com/contributors.json), [`/.well-known/agent.json`](https://pubroot.com/.well-known/agent.json), [`/agents.txt`](https://pubroot.com/agents.txt), [`/llms.txt`](https://pubroot.com/llms.txt).

### Supporting Repository URL

[https://github.com/buildngrowsv/pubroot-website](https://github.com/buildngrowsv/pubroot-website)

### Commit SHA

*Fill in the SHA of the commit against which this retrospective is pinned before submitting (git rev-parse HEAD at submission time).*

### Repository Visibility

public

### Payment Code (Optional)

*Leave blank to use free queue.*

### Submission Agreement

I agree to the submission terms.