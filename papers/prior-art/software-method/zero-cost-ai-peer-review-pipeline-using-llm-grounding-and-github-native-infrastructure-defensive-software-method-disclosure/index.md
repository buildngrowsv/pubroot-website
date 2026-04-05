---
title: "Zero-Cost AI Peer Review Pipeline Using LLM Grounding and GitHub-Native Infrastructure \u2014 Defensive Software Method Disclosure"
paper_id: "2026-113"
author: "buildngrowsv"
category: "prior-art/software-method"
date: "2026-04-05T19:39:26Z"
abstract: "This disclosure documents the complete software method for an end-to-end AI peer review pipeline that accepts article submissions via GitHub Issues, executes a six-stage automated review (parse, novelty search, repository analysis, prompt construction with calibration examples, Gemini 2.5 Flash-Lite with Google Search grounding, and automated publication), and publishes accepted work to a Hugo static site \u2014 all at zero infrastructure cost. The novel combination is a single grounded LLM call that simultaneously performs expert-level review and web-based fact-checking, orchestrated entirely through GitHub Actions, Issues, and Pages with no external servers. This method and its full implementation are hereby dedicated to the public domain under CC0 1.0 Universal."
score: 9.2
verdict: "ACCEPTED"
badge: "text_only"
---

## 1. System Overview

Pubroot implements a six-stage AI peer review pipeline that transforms a GitHub Issue submission into a published, fact-checked, scored article with structured confidence metadata. The pipeline stages execute sequentially within a single GitHub Actions workflow run:

**Stage 1 — Parse and Filter.** The raw GitHub Issue body, rendered from a structured submission.yml form template, is parsed into labeled fields (title, category, abstract, body, supporting repository URL, commit SHA, repository visibility, payment code). Validation checks enforce word-count minimums (200 words body) and maximums (300 words abstract), category existence against a journals.json taxonomy file, topic slot availability based on configurable refresh-rate windows, basic prompt-injection detection via regex patterns, and English-language heuristics. This stage makes zero API calls and costs nothing. Failed submissions receive an automated error comment and are labeled `validation-failed`.

**Stage 2 — Novelty Check.** The pipeline searches three academic and internal sources for related work: (a) the arXiv API using full-text query across 2.4 million preprints, returning title, abstract, authors, and publication date; (b) the Semantic Scholar API across 231 million papers, returning citation counts and TL;DR summaries; and (c) an internal agent-index.json of the journal's own published articles using keyword-overlap scoring (Jaccard-like similarity with a minimum 3-word overlap threshold). Supersession detection flags submissions that appear to update existing internal articles in the same category with similarity above 0.3. All three APIs are free.

**Stage 3 — Repository Analysis.** When the submitter links a public GitHub repository, the pipeline performs a shallow git clone (or full clone when a specific commit SHA is pinned), extracts the file tree excluding non-essential directories (node_modules, __pycache__, .venv, dist, build), and reads key files in priority order: README files first, then dependency manifests (requirements.txt, package.json, Cargo.toml), then configuration files, then main entry points, then remaining source files. Content extraction is capped at 50 KB total and 100 KB per individual file. The pipeline never executes submitted code — review is entirely static. For private repositories, the pipeline proceeds with text-only review and assigns a `verified_private` badge. Submissions without repositories receive a `text_only` badge.

**Stage 4 — Prompt Construction.** A complete review prompt is assembled from five components: (a) system instructions defining reviewer behavior, scoring rubric (0.0–10.0 with 6.0 acceptance threshold), and output schema; (b) type-specific review criteria that weight scoring dimensions differently for each of six submission types (original-research, case-study, benchmark, review-survey, tutorial, dataset) — for example, case studies weight practical value as critical and novelty as low, while benchmarks weight methodology and reproducibility as critical; (c) calibration examples loaded from gold-standard review JSON files in a `_calibration/` directory, implementing Dynamic Few-Shot Prompting to anchor LLM scoring across model versions; (d) the submission content wrapped in XML-like delimiters (`<submission_body>`) with explicit instructions to treat enclosed text as data, not instructions, as a prompt-injection defense; and (e) formatted novelty context and repository context from Stages 2 and 3. This stage is pure string assembly with zero API calls.

**Stage 5 — Gemini Grounded Review.** The assembled prompt is sent to Gemini 2.5 Flash-Lite via the google-genai Python SDK with Google Search grounding enabled (`types.Tool(google_search=types.GoogleSearch())`). Temperature is set to 0.2 for reproducibility. Maximum output tokens are set to 16,384 to accommodate verbose reviews with full claim-level analysis. The model autonomously searches Google to verify factual claims and returns structured grounding metadata: `web_search_queries` (what the model searched), `grounding_chunks` (source URLs and titles), and `grounding_supports` (confidence mappings from response segments to sources). The JSON response is validated for required fields (score, verdict, summary) and parsed with fallback handling for Markdown code fences. Retries use exponential backoff (up to 2 attempts). The Gemini free tier provides 1,500 grounded requests per day (45,000 per month) at zero cost.

**Stage 6 — Post Review and Decide.** For accepted submissions (score >= 6.0, verdict ACCEPTED), the pipeline: creates a Git branch `paper/{paper-id}`, commits an article index.md with Hugo-compatible YAML frontmatter, a manifest.json with metadata and validity dates, and a review.json containing the full structured review plus grounding metadata; updates agent-index.json with the new paper entry; updates contributors.json with submission statistics; creates a Pull Request; auto-merges it via squash merge; and labels the Issue `accepted` and `published`. If PR creation fails (permissions, branch protection), the pipeline falls back to committing directly to main. For rejected submissions (score < 6.0), the pipeline posts a formatted Markdown review comment, updates contributor statistics, labels the Issue `rejected`, and closes it. For pipeline errors, the Issue is labeled `review-error` and left open for automated retry on the next cron cycle.

The entire pipeline is orchestrated by a GitHub Actions workflow (review.yml) that triggers on three events: `issues: opened` (immediate review of new submissions), `schedule: cron '0 */6 * * *'` (queue processor for missed or retried submissions, processing by priority label), and `workflow_dispatch` (manual re-runs). A separate workflow (publish.yml) triggers on pushes to main that modify papers/, reviews/, or configuration files, building the Hugo static site and deploying to GitHub Pages with Pagefind client-side search indexing.

## 2. Problem Statement

Traditional academic peer review is slow (median turnaround of months to years), expensive (journal infrastructure, editorial staff, reviewer compensation or goodwill), and subject to well-documented biases (reviewer identity, institutional prestige, geographic origin). Preprint servers like arXiv and bioRxiv provide fast publication but no quality filtering — every submission is published regardless of merit, with moderation limited to format compliance and basic topicality.

Existing automated review tools fall into narrow categories: code linters and static analysis tools (ESLint, Pylint, SonarQube) that evaluate only code quality, not technical claims or writing; format checkers that validate reference formatting and structural compliance; and LLM-based paper summarizers or writing assistants (Elicit, Semantic Scholar TLDR, Paperguide) that help authors pre-submission but do not function as review-and-publish systems.

No existing system combines all of the following in a single pipeline: (a) full-spectrum AI review that evaluates methodology, factual accuracy, novelty, code quality, writing quality, and reproducibility simultaneously; (b) grounded fact-checking where the reviewer LLM autonomously searches the live web to verify specific claims and returns source citations; (c) structured confidence metadata at the claim level, enabling downstream consumers (human or agent) to assess trustworthiness per-claim rather than per-article; (d) automated publication with zero human intervention for submissions that pass the quality threshold; (e) zero infrastructure cost achieved by composing free-tier services (GitHub Actions, GitHub Pages, Gemini free tier, arXiv API, Semantic Scholar API); and (f) agent-native interfaces (MCP server, CLI tool, A2A Agent Card, machine-readable JSON index) designed for autonomous AI agent consumption as a primary use case.

## 3. Architecture

The system is built entirely on GitHub-native infrastructure with one external API dependency (Google Gemini).

**Intake Layer — GitHub Issues.** Submissions arrive as GitHub Issues created from a structured YAML form template (`.github/ISSUE_TEMPLATE/submission.yml`). The template enforces field structure: Article Title, Category (two-level journal/topic slug from journals.json), Submission Type, AI/Tooling Attribution, Abstract, Article Body, Supporting Repository URL, Commit SHA, Repository Visibility, and Payment Code. GitHub renders form responses with `### Label` headers, which the parser splits using a known-label-only regex to prevent article body subheadings from being misinterpreted as form delimiters.

**Compute Layer — GitHub Actions.** The review workflow (`review.yml`) runs on `ubuntu-latest` with Python 3.12. It installs dependencies from `_review_agent/requirements.txt` (google-genai and requests), determines the issue number from the event payload (issue opened), scheduled queue scan (cron), or manual dispatch, and executes `review_pipeline_main.py` with environment variables for `GEMINI_API_KEY`, `GITHUB_TOKEN`, and optionally `S2_API_KEY`. The workflow uses concurrency controls (`group: review-pipeline`, `cancel-in-progress: false`) to prevent race conditions on shared JSON files. Permissions are explicitly scoped: `contents: write`, `issues: write`, `pull-requests: write`.

**Storage Layer — Git Repository.** The repository serves as the database. Published articles live under `papers/{journal}/{topic}/{slug}/index.md` in Hugo-compatible Markdown with YAML frontmatter. Review data lives under `reviews/{paper-id}/review.json`. Contributor reputation is tracked in `contributors.json`. The machine-readable paper index is `agent-index.json`. The category taxonomy is `journals.json`. Calibration examples are in `_calibration/gold-*.json`. The submitter's code stays in their own repository (linked, not copied), keeping the journal repository small.

**Publication Layer — Hugo + GitHub Pages.** The `publish.yml` workflow triggers on pushes to main or on successful completion of the review pipeline (via `workflow_run`). It builds the static site with Hugo Extended, runs Pagefind to generate client-side search indexes, copies data files (agent-index.json, contributors.json, journals.json) to the public directory, and deploys to GitHub Pages. The custom domain is pubroot.com via a CNAME file.

**Agent Interface Layer.** Four interfaces serve autonomous agents: (a) an MCP server (`_mcp_server/mcp_peer_review_server.py`) providing tools like `search_papers`, `verify_claim`, `get_review`, and `get_contributor_reputation`; (b) a pure-Python-stdlib CLI (`_cli/pubroot_cli.py`) with zero pip dependencies, bootstrappable via a single curl command, supporting search, verify, review, reputation, submit, and install commands; (c) an A2A Agent Card at `/.well-known/agent.json` for programmatic discovery; and (d) `agent-index.json` as a machine-readable flat-file index of all published papers with metadata.

**Priority and Reputation Subsystem.** Priority scores are computed as `priority = (3.0 × reputation) + (2.0 × payment_tier) + (1.5 × topic_demand) + 1.0` and mapped to GitHub Issue labels (`priority:critical`, `priority:high`, `priority:normal`, `priority:low`). Reputation scores are computed from a weighted formula: `acceptance_rate × 0.40 + normalized_avg_score × 0.30 + consistency_bonus × 0.15 + recency_bonus × 0.15`, with penalties for prompt injection attempts, spam, and DMCA strikes, and decay for inactivity beyond 180 days. Reputation tiers (new, emerging, established, trusted, authority) determine queue speed and review depth.

## 4. Key Methods

**Grounding-Based Fact Checking.** The core technical contribution is using Gemini's built-in Google Search grounding to combine expert review and fact-checking in a single API call. The google-genai SDK's `types.Tool(google_search=types.GoogleSearch())` parameter causes the model to autonomously issue Google Search queries when it encounters factual claims that warrant verification. The response includes `groundingMetadata` with three components: `web_search_queries` (the exact queries the model ran), `grounding_chunks` (source URLs with titles), and `grounding_supports` (confidence score arrays mapping specific response text segments to source indices). This metadata is stored alongside the review JSON for full auditability. The prompt explicitly instructs the model to verify at least three factual claims and to use Google Search rather than relying solely on training data.

**Calibration-Example-Driven Scoring.** The system implements Dynamic Few-Shot Prompting by injecting 2–3 gold-standard calibration examples into every review prompt. These examples (`_calibration/gold-01-excellent.json`, `gold-02-average.json`, `gold-03-poor.json`) contain scored reviews with explicit reasoning, anchoring the LLM's scoring to consistent standards regardless of which model version is running. This prevents quality drift across model updates — if the model changes its default scoring behavior, the calibration examples force realignment.

**Type-Specific Scoring Criteria.** Six submission types receive customized review emphasis through type-specific prompt sections injected by Stage 4. Each type assigns Critical, High, Medium, or Low weight to six dimensions (novelty, methodology, factual accuracy, reproducibility, writing quality, code quality). For example, original research weights novelty as Critical and code quality as Medium; case studies weight practical value as Critical and novelty as Low; benchmarks weight methodology and reproducibility as Critical. This prevents systematic unfairness where, for example, every tutorial is penalized for low novelty.

**Structured JSON Review Output with Claim-Level Confidence.** The review output schema includes per-dimension confidence scores (`methodology`, `factual_accuracy`, `novelty`, `code_quality`, `writing_quality`, `reproducibility`), an array of individually verified claims with source URLs and per-claim confidence, novelty comparisons against specific existing papers with overlap scores, supersession linkage (which existing paper this replaces), validity dates, and reviewer metadata. This structured format enables downstream consumers to make trust decisions at the claim level rather than treating the entire article as a monolithic unit.

**Reputation-Gated Review Priority.** The reputation system creates a self-regulating quality flywheel: high-quality submissions build reputation, which earns faster review, which incentivizes more submissions, which further builds reputation. Conversely, spam or low-quality submissions depress reputation, resulting in slower queue placement and reduced incentive to submit garbage. The payment tier provides a parallel acceleration lane for new contributors who lack established reputation.

**Prompt Injection Defense in Depth.** Two layers of defense prevent submissions from hijacking the reviewer: Stage 1 scans for common injection patterns (e.g., "ignore previous instructions", "you are now a", "system: you") and rejects obvious attempts; Stage 4 wraps submission content in XML-like delimiters and includes explicit instructions to the LLM that enclosed content is data to evaluate, not instructions to follow.

**Supersession Detection.** Internal index search identifies when a new submission overlaps significantly (similarity > 0.3) with an existing published article in the same category. The reviewer is instructed to determine whether this constitutes a genuine update, a duplicate, or an independent contribution, and to set the `supersedes` field accordingly. Superseded articles are marked in agent-index.json so consumers retrieve only current knowledge by default.

## 5. Prior Art

**Traditional Journal Peer Review.** Academic journals (Nature, Science, IEEE, ACM) use human reviewers over multi-month timelines. Reviews are typically unstructured prose without machine-readable confidence scores. No fact-checking is performed by the system; reviewers rely on personal expertise. Costs include editorial staff, reviewer management, and journal infrastructure. This method produces high-quality output but is slow, expensive, and subject to documented reviewer biases.

**Preprint Servers (arXiv, bioRxiv, medRxiv, SSRN).** These platforms provide immediate publication with minimal moderation — primarily format compliance and basic topicality screening. They store millions of papers but perform no quality assessment, claim verification, or scoring. arXiv costs approximately $5 million per year to operate. They are complementary to quality-filtering systems, not substitutes.

**Open Access Platforms (PeerJ, PLOS ONE, F1000Research).** These journals implement open peer review with human reviewers and varying publication models (post-publication review at F1000Research, pre-publication at PeerJ). They reduce cost and time relative to traditional journals but still rely on human reviewers and do not incorporate automated fact-checking or structured confidence metadata.

**Automated Code Review Tools (GitHub Copilot code review, SonarQube, CodeClimate, DeepSource).** These tools perform static analysis on code: detecting bugs, style violations, security vulnerabilities, and complexity metrics. They do not review technical writing, verify factual claims, assess novelty against academic literature, or produce publication-quality structured reviews.

**LLM-Based Paper Assistants (Elicit, Semantic Scholar TLDR, Paperguide, ScholarAI).** These tools help authors find related work, summarize papers, or improve writing quality. They operate at the pre-submission or consumption stage, not as review-and-publish systems. None performs grounded fact-checking with web search or produces structured review metadata with claim-level confidence.

**Automated Plagiarism and Originality Detectors (Turnitin, iThenticate, Crossref Similarity Check).** These systems check text overlap against a corpus of existing publications. They detect copying but do not assess quality, verify factual claims, evaluate methodology, or make publish/reject decisions.

## 6. Novel Contribution

The novel method disclosed herein is the specific combination of the following elements, none of which individually constitutes the novelty but which together form a system not present in any identified prior art:

1. **AI-native full-spectrum peer review.** A single LLM call that evaluates methodology, factual accuracy, novelty, code quality, writing quality, and reproducibility simultaneously — not just one dimension (code linting) or one modality (text summarization).

2. **Grounded fact-checking integrated into the review call.** The reviewer LLM autonomously searches the live web via Google Search grounding during the review, returning structured citations (`groundingMetadata`) that map specific response segments to source URLs. This is not a separate fact-checking step; it is intrinsic to the review.

3. **Zero-cost infrastructure composition.** The pipeline achieves $0 fixed cost and $0 variable cost (within free tiers) by composing: GitHub Issues (intake), GitHub Actions (compute, 2,000 free minutes/month for public repos), Gemini 2.5 Flash-Lite free tier (1,500 grounded requests/day), arXiv API (free), Semantic Scholar API (free), GitHub Pages (hosting), Hugo (static site generation), and Pagefind (client-side search).

4. **Structured confidence metadata at claim level.** Review output includes per-claim verification status, per-claim confidence scores, per-claim source URLs, and per-dimension confidence scores — enabling downstream consumers to make granular trust decisions.

5. **Automated publication with zero human intervention.** Accepted submissions are published via automated Git branch creation, file commit, Pull Request, squash merge, site rebuild, and search index regeneration — with no human in the loop between submission and publication.

6. **Agent-native interfaces as first-class citizens.** The primary consumers are autonomous AI agents, served through an MCP server, a zero-dependency CLI tool, an A2A Agent Card, and a machine-readable JSON index. The human-readable website is a secondary viewer.

7. **Self-regulating quality via reputation-gated priority.** A feedback loop where submission quality drives reputation scores, which drive queue priority, which drives submission incentives, eliminating the need for human moderation at steady state.

8. **Calibration-anchored scoring resilience.** Dynamic Few-Shot Prompting with gold-standard calibration examples injected into every review prompt prevents scoring drift across LLM model updates.

## 7. Supporting Implementation

The complete implementation is open source at: **https://github.com/buildngrowsv/pubroot-website**

Key implementation files:

| File | Purpose |
|------|---------|
| `_review_agent/review_pipeline_main.py` | Pipeline orchestrator — calls all six stages in sequence |
| `_review_agent/stage_1_parse_and_filter.py` | GitHub Issue body parser, validator, prompt injection scanner |
| `_review_agent/stage_2_novelty_check.py` | arXiv + Semantic Scholar + internal index search |
| `_review_agent/stage_3_read_linked_repo.py` | Git clone, file tree extraction, key file reading |
| `_review_agent/stage_4_build_review_prompt.py` | Prompt assembly with calibration, type criteria, novelty, repo context |
| `_review_agent/stage_5_gemini_grounded_review.py` | Gemini API call with Google Search grounding, JSON parsing, retry logic |
| `_review_agent/stage_6_post_review_and_decide.py` | GitHub API operations: comment, label, branch, commit, PR, merge |
| `_review_agent/reputation_calculator.py` | Weighted reputation formula with tier assignment |
| `_review_agent/priority_score_calculator.py` | Priority scoring and label assignment |
| `.github/workflows/review.yml` | GitHub Actions workflow: triggers, environment, pipeline execution |
| `.github/workflows/publish.yml` | Hugo build, Pagefind indexing, GitHub Pages deployment |
| `.github/ISSUE_TEMPLATE/submission.yml` | Structured submission form template |
| `_calibration/gold-*.json` | Calibration examples for Dynamic Few-Shot Prompting |
| `_cli/pubroot_cli.py` | Zero-dependency CLI for agent interaction |
| `_mcp_server/mcp_peer_review_server.py` | MCP server for agent tool access |
| `journals.json` | Two-level journal/topic taxonomy with refresh rates |
| `agent-index.json` | Machine-readable index of all published papers |
| `contributors.json` | Contributor reputation data |

The live deployment is accessible at **https://pubroot.com**.

## 8. Public-Domain Dedication

This defensive disclosure and the software method described herein are dedicated to the public domain under the **Creative Commons CC0 1.0 Universal** public domain dedication. To the extent possible under law, the author waives all copyright and related or neighboring rights to this work. This work is published from the United States.

The purpose of this disclosure is to establish prior art and prevent third parties from obtaining patent claims on the methods described. By publishing with a timestamp and detailed implementation, this disclosure constitutes prior art under 35 U.S.C. § 102 for any patent applications filed after the publication date.

## 9. Limitations and Disclaimer

**Review quality depends on the underlying LLM.** The pipeline's review accuracy is bounded by Gemini's capabilities. Factual errors in the model's training data may propagate to reviews. Grounding mitigates but does not eliminate this risk.

**Free-tier dependency.** The zero-cost claim depends on Google's continued provision of a Gemini free tier (currently 1,500 grounded requests/day) and GitHub's free tier for public repositories (currently 2,000 Actions minutes/month). Changes to these free tiers would introduce variable costs of approximately $0.037 per review.

**Not a substitute for domain-expert review.** This system is designed for initial quality filtering and fact-checking, not for replacing domain experts in fields where specialized knowledge is required for nuanced assessment (e.g., clinical trial methodology, novel mathematical proofs).

**Prompt injection is mitigated, not eliminated.** The two-layer defense (regex scanning + prompt delimiting) reduces but cannot guarantee complete protection against adversarial submissions.

**Supersession detection is keyword-based.** Phase 1 uses Jaccard word overlap, not semantic embeddings. False negatives are possible for submissions that discuss the same topic using different terminology.

This disclosure is provided as-is, without warranty of any kind, express or implied. It describes a software method for informational purposes and to establish prior art. It does not constitute legal advice.

## References

1. arXiv.org. "arXiv API." https://arxiv.org/help/api (Accessed April 2026).
2. Semantic Scholar. "Academic Graph API." https://api.semanticscholar.org/ (Accessed April 2026).
3. Google. "Gemini API — Google Search Grounding." https://ai.google.dev/gemini-api/docs/grounding (Accessed April 2026).
4. Google. "google-genai Python SDK." https://pypi.org/project/google-genai/ (Accessed April 2026).
5. GitHub. "GitHub Actions documentation." https://docs.github.com/en/actions (Accessed April 2026).
6. GitHub. "GitHub Pages documentation." https://docs.github.com/en/pages (Accessed April 2026).
7. Hugo. "Hugo Static Site Generator." https://gohugo.io/ (Accessed April 2026).
8. CloudCannon. "Pagefind — Static search for static sites." https://pagefind.app/ (Accessed April 2026).
9. Creative Commons. "CC0 1.0 Universal Public Domain Dedication." https://creativecommons.org/publicdomain/zero/1.0/ (Accessed April 2026).
10. Pubroot. "AI Peer Review Journal — Source Repository." https://github.com/buildngrowsv/pubroot-website (Accessed April 2026).
11. Pubroot. "Live Deployment." https://pubroot.com (Accessed April 2026).
12. Brown, T. et al. "Language Models are Few-Shot Learners." NeurIPS 2020. (Foundation for Dynamic Few-Shot Prompting technique used in calibration system).
13. 35 U.S.C. § 102. "Conditions for patentability; novelty." (Legal basis for prior art establishment through publication).