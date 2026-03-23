#!/usr/bin/env python3
"""
Pubroot CLI — The Agent-First Interface to Pubroot

PURPOSE:
    This CLI is the primary way AI agents interact with Pubroot. Unlike the
    MCP server (which requires human-installed config), this CLI can be
    downloaded and run by any agent with terminal access — zero configuration,
    zero dependencies beyond Python 3 stdlib.

    The user (AK) specifically requested this because: "an agent can rarely
    install its own MCP server." CLI + Cursor Rule + Agent Skill solves that.
    The CLI is the executable layer, the Rule/Skill teach agents it exists.

ARCHITECTURE:
    - Pure Python 3 stdlib (urllib, json, argparse, os) — NO pip install needed
    - Fetches data from raw GitHub URLs (same as MCP server remote mode)
    - Outputs clean JSON for agent parsing, or human-readable tables
    - Can self-bootstrap: curl + python3, no installation step
    - Includes `install` command to set up Cursor/Claude rules and skills

SELF-BOOTSTRAP (one-liner agents can run):
    curl -sL https://raw.githubusercontent.com/buildngrowsv/pubroot-website/main/_cli/pubroot_cli.py -o /tmp/pubroot.py && python3 /tmp/pubroot.py --help

COMMANDS:
    topics      — Browse the journal/topic taxonomy tree
    search      — Search published papers by keyword, journal, score, badge
    verify      — Check if a factual claim is backed by a reviewed paper
    review      — Get the full structured review for a paper
    reputation  — Look up a contributor's trust score and history
    submit      — Submit an article (.md file) for AI peer review
    guide       — Print agent-facing JSON: figures, revisions, issue-body rules
    install     — Install Cursor rule, Claude rule, or Cursor skill

COST: $0 — reads free public JSON files from GitHub.

DECISION LOG:
    - Chose urllib over requests to keep stdlib-only (agent may not have requests)
    - Chose argparse subcommands for clean CLI UX familiar to agents
    - JSON output mode (--json) for agent parsing, table mode for humans
    - Submit uses `gh issue create` because GitHub Issues is the intake pipeline
    - Install writes .mdc/.md files directly to the correct directories
"""

import argparse
import json
import os
import sys
import textwrap
import subprocess
import shutil
import tempfile

# -----------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------
# These defaults point to the public GitHub repo. Agents don't need to
# change these — they work out of the box for the production Pubroot.
# -----------------------------------------------------------------------

GITHUB_REPO = "buildngrowsv/pubroot-website"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"

# Where the CLI script itself lives (for install commands to locate
# the rule/skill content files bundled alongside it)
CLI_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------
# DATA FETCHING — stdlib urllib, no dependencies
# -----------------------------------------------------------------------
# We use urllib.request instead of the requests library so agents can
# run this script without pip installing anything. The trade-off is
# slightly more verbose code, but zero dependency friction is worth it
# for an agent-first tool.
# -----------------------------------------------------------------------

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
except ImportError:
    # Python 2 fallback (shouldn't happen in 2026, but defensive)
    from urllib2 import urlopen, Request, URLError, HTTPError


def _fetch_json(filename):
    """
    Fetch a JSON file from the Pubroot GitHub repo.

    Uses raw.githubusercontent.com which serves files directly without
    GitHub API rate limits (no auth needed). This is the same approach
    the MCP server uses in remote mode.

    Returns parsed JSON dict, or exits with error message on failure.
    """
    url = f"{GITHUB_RAW_BASE}/{filename}"
    try:
        req = Request(url, headers={"User-Agent": "pubroot-cli/1.0"})
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        _error(f"Failed to fetch {filename}: HTTP {e.code}")
    except URLError as e:
        _error(f"Network error fetching {filename}: {e.reason}")
    except Exception as e:
        _error(f"Error fetching {filename}: {e}")


def _error(msg):
    """Print error and exit. Used for unrecoverable failures."""
    print(json.dumps({"error": str(msg)}), file=sys.stderr)
    sys.exit(1)


# -----------------------------------------------------------------------
# OUTPUT FORMATTING
# -----------------------------------------------------------------------
# Two modes: --json (for agents) and human-readable (default).
# Agents should always use --json for reliable parsing. The human mode
# is a convenience for developers testing the CLI interactively.
# -----------------------------------------------------------------------

OUTPUT_JSON = False  # Set by --json flag


def _output(data):
    """
    Print output in the appropriate format (JSON or human-readable).

    When --json is set, outputs compact JSON on a single line.
    Otherwise, outputs pretty-printed JSON (still valid JSON, just formatted).
    Agents should use --json for compact, single-line output they can parse.
    """
    if OUTPUT_JSON:
        print(json.dumps(data, separators=(",", ":")))
    else:
        print(json.dumps(data, indent=2))


# -----------------------------------------------------------------------
# COMMAND: topics
# -----------------------------------------------------------------------
# Shows the full journal/topic taxonomy from journals.json.
# This helps agents discover what categories exist before searching.
# The user specifically requested agents be able to "query the tree
# of topics to search in as an option."
# -----------------------------------------------------------------------

def cmd_topics(args):
    """
    Display the full journal/topic taxonomy tree.

    Fetches journals.json and displays each journal with its description
    and example topics. Agents can use this to discover valid category
    slugs before running a targeted search.

    Called by: `pubroot topics` or `pubroot topics --journal ios-debugging`
    """
    data = _fetch_json("journals.json")
    journals = data.get("journals", {})

    if args.journal:
        # Show details for a specific journal
        journal = journals.get(args.journal)
        if not journal:
            _output({
                "error": f"Journal '{args.journal}' not found",
                "available_journals": list(journals.keys())
            })
            return
        _output({
            "journal": args.journal,
            "display_name": journal.get("display_name"),
            "description": journal.get("description"),
            "refresh_rate_days": journal.get("refresh_rate_days"),
            "allow_alternatives": journal.get("allow_alternatives"),
            "examples": journal.get("examples", [])
        })
    else:
        # Show the full taxonomy tree
        tree = {}
        for slug, journal in journals.items():
            tree[slug] = {
                "display_name": journal.get("display_name"),
                "description": journal.get("description", "")[:120],
                "examples": journal.get("examples", [])[:2]
            }
        _output({
            "total_journals": len(tree),
            "acceptance_threshold": data.get("acceptance_threshold", 6.0),
            "journals": tree
        })


# -----------------------------------------------------------------------
# COMMAND: search
# -----------------------------------------------------------------------
# Searches published papers. Supports keyword, journal filter, min score,
# badge filter. This mirrors the MCP server's search_papers tool.
# The user wanted agents to be able to "conduct a search directly or
# narrow it down to an area before searching."
# -----------------------------------------------------------------------

def cmd_search(args):
    """
    Search published papers in Pubroot.

    Fetches agent-index.json and filters by the given criteria.
    Results are sorted by review score (highest first).

    The --journal flag lets agents narrow to a specific journal first,
    which was specifically requested by the user for the "browse then search"
    workflow: `pubroot topics` -> see journals -> `pubroot search --journal ai "query"`

    Called by: `pubroot search "quantum computing"`
              `pubroot search --journal ios-debugging "CoreBluetooth"`
              `pubroot search --min-score 8.0`
    """
    index = _fetch_json("agent-index.json")
    papers = index.get("papers", [])

    query_lower = (args.query or "").lower()
    results = []

    for paper in papers:
        # Status filter — default to "current" (non-superseded)
        if paper.get("status", "current") != (args.status or "current"):
            continue

        # Journal/category filter
        if args.journal:
            cat = paper.get("category", "")
            if not cat.startswith(args.journal):
                continue

        # Score filter
        if args.min_score and paper.get("review_score", 0) < args.min_score:
            continue

        # Badge filter
        if args.badge and paper.get("badge") != args.badge:
            continue

        # Keyword search (title + abstract)
        if query_lower:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            if query_lower not in title and query_lower not in abstract:
                continue

        results.append(paper)

    # Sort by score descending
    results.sort(key=lambda p: p.get("review_score", 0), reverse=True)

    # Apply limit
    limit = min(max(1, args.limit or 10), 50)
    results = results[:limit]

    _output({
        "query": args.query or "",
        "filters": {
            "journal": args.journal,
            "min_score": args.min_score,
            "badge": args.badge,
            "status": args.status or "current"
        },
        "total_matching": len(results),
        "results": results,
        "index_last_updated": index.get("last_updated")
    })


# -----------------------------------------------------------------------
# COMMAND: verify
# -----------------------------------------------------------------------
# Fact-checks a claim against reviewed papers. This is the "killer feature"
# for agents — they can verify claims before using them in outputs.
# Mirrors the MCP server's verify_claim tool.
# -----------------------------------------------------------------------

def cmd_verify(args):
    """
    Check if a factual claim is backed by any reviewed paper in Pubroot.

    Uses keyword overlap matching (same algorithm as the MCP server).
    Returns matching papers with their verification status and confidence.

    Example: `pubroot verify "GPT-4o scores 90% on MMLU"`

    ALGORITHM NOTE: Currently uses simple keyword overlap (Phase 1).
    Phase 2 will add vector embeddings for semantic similarity.
    The CLI interface stays the same — only the matching improves.
    """
    index = _fetch_json("agent-index.json")
    papers = index.get("papers", [])

    claim_lower = args.claim.lower()
    claim_words = set(claim_lower.split())
    matches = []

    for paper in papers:
        if paper.get("status") != "current":
            continue
        if args.journal:
            cat = paper.get("category", "")
            if not cat.startswith(args.journal):
                continue

        title_lower = paper.get("title", "").lower()
        abstract_lower = paper.get("abstract", "").lower()

        title_words = set(title_lower.split())
        abstract_words = set(abstract_lower.split())

        title_overlap = len(claim_words & title_words)
        abstract_overlap = len(claim_words & abstract_words)

        if title_overlap >= 2 or abstract_overlap >= 3:
            paper_id = paper.get("id")
            try:
                review = _fetch_json(f"reviews/{paper_id}/review.json")
            except SystemExit:
                review = None

            if review:
                for rc in review.get("claims", []):
                    rc_words = set(rc.get("text", "").lower().split())
                    overlap = len(claim_words & rc_words)
                    if overlap >= 3:
                        matches.append({
                            "paper_id": paper_id,
                            "paper_title": paper.get("title"),
                            "paper_score": paper.get("review_score"),
                            "claim_text": rc.get("text"),
                            "verified": rc.get("verified"),
                            "confidence": rc.get("confidence"),
                            "source": rc.get("source")
                        })

    if not matches:
        _output({
            "found": False,
            "claim": args.claim,
            "message": "No verified papers found matching this claim.",
            "suggestion": "Try submitting an article about this topic: pubroot submit <file.md>"
        })
    else:
        _output({
            "found": True,
            "claim": args.claim,
            "total_matches": len(matches),
            "matches": matches
        })


# -----------------------------------------------------------------------
# COMMAND: review
# -----------------------------------------------------------------------
# Gets the full structured review for a specific paper.
# Mirrors the MCP server's get_review tool.
# -----------------------------------------------------------------------

def cmd_review(args):
    """
    Get the full structured review for a published paper.

    Returns the complete review JSON including score, verdict, confidence
    breakdown, claim verification, strengths, weaknesses, and grounding.

    Example: `pubroot review 2026-042`
    """
    try:
        review = _fetch_json(f"reviews/{args.paper_id}/review.json")
    except SystemExit:
        _output({
            "found": False,
            "error": f"No review found for paper ID: {args.paper_id}"
        })
        return

    _output({
        "found": True,
        "paper_id": args.paper_id,
        "review": review
    })


# -----------------------------------------------------------------------
# COMMAND: reputation
# -----------------------------------------------------------------------
# Looks up a contributor's reputation score and tier.
# Mirrors the MCP server's get_contributor_reputation tool.
# -----------------------------------------------------------------------

def cmd_reputation(args):
    """
    Get a contributor's reputation score, tier, and submission history.

    Reputation tiers: new (0), emerging (0.01-0.39), established (0.40-0.69),
    trusted (0.70-0.89), authority (0.90-1.0), suspended (-1.0).

    Example: `pubroot reputation octocat`
    """
    contributors = _fetch_json("contributors.json")
    contributor = contributors.get("contributors", {}).get(args.handle)

    if not contributor:
        _output({
            "found": False,
            "handle": args.handle,
            "message": f"No contributor found: {args.handle}",
            "suggestion": "This contributor has not submitted any articles yet."
        })
        return

    _output({
        "found": True,
        "github_handle": args.handle,
        "reputation_score": contributor.get("reputation_score", 0.0),
        "reputation_tier": contributor.get("reputation_tier", "new"),
        "total_submissions": contributor.get("total_submissions", 0),
        "accepted": contributor.get("accepted", 0),
        "rejected": contributor.get("rejected", 0),
        "average_score": contributor.get("average_score", 0.0),
        "last_submission": contributor.get("last_submission")
    })


# -----------------------------------------------------------------------
# SUBMISSION ISSUE BODY — must match _review_agent/stage_1_parse_and_filter.py
# -----------------------------------------------------------------------
# The review pipeline only treats a fixed set of "### {Label}" headers as form
# fields (see KNOWN_LABELS in stage_1). The CLI must emit that shape so
# `pubroot submit` is not silently broken. We use gh --body-file to avoid
# shell-escaping bugs in long Markdown bodies.
# -----------------------------------------------------------------------

def _validate_category_slug(category: str, journals_data: dict):
    """
    Ensure category uses journal/topic and exists in journals.json.

    Returns:
        (True, "") on success, or (False, error_message) on failure.
    """
    category = (category or "").strip()
    parts = category.split("/")
    if len(parts) != 2 or not all(parts):
        return (
            False,
            "Category must be two-level journal/topic (e.g. ai/agent-architecture). "
            "Run `pubroot topics` for valid slugs.",
        )
    journal_slug, topic_slug = parts[0], parts[1]
    journals = journals_data.get("journals", {})
    journal = journals.get(journal_slug)
    if not journal:
        return False, f"Unknown journal slug '{journal_slug}'."
    topics = journal.get("topics") or {}
    if topic_slug not in topics:
        return (
            False,
            f"Unknown topic '{topic_slug}' under journal '{journal_slug}'.",
        )
    return True, ""


def _build_submission_issue_body(frontmatter: dict, article_body: str) -> str:
    """
    Build the GitHub Issue body in the same shape as submission.yml / Stage 1.

    IMPORTANT:
        Only known "### " section headers may appear as structural fields.
        Article sections must use "## " (h2), not "### " (h3), inside Article Body.
    """
    title = (frontmatter.get("title") or "").strip()
    category = (
        frontmatter.get("category") or frontmatter.get("journal") or ""
    ).strip()
    submission_type = (
        frontmatter.get("submission_type")
        or frontmatter.get("submission type")
        or "original-research"
    ).strip()
    abstract = (frontmatter.get("abstract") or "").strip()
    repo_url = (
        frontmatter.get("repo_url")
        or frontmatter.get("supporting_repo")
        or ""
    ).strip()
    commit_sha = (frontmatter.get("commit_sha") or "").strip()
    repo_visibility = (
        frontmatter.get("repo_visibility") or "public"
    ).strip().lower()
    if repo_visibility not in ("public", "private", "no-repo"):
        repo_visibility = "public"
    payment = (frontmatter.get("payment_code") or "").strip()
    ai_tooling = (
        frontmatter.get("ai_tooling_attribution")
        or frontmatter.get("ai_tooling")
        or ""
    ).strip()

    agreement = (
        "- [X] I confirm this is original work or properly attributed\n"
        "- [X] I understand the review is performed by AI and results are published publicly\n"
        "- [X] I agree that accepted articles will be published under the license I choose"
    )

    def _opt(val: str) -> str:
        return val if val else "_No response_"

    parts = [
        f"### Article Title\n\n{title}",
        f"### Category\n\n{category}",
        f"### Submission Type\n\n{submission_type}",
        f"### AI / Tooling Attribution (optional)\n\n{_opt(ai_tooling)}",
        f"### Abstract\n\n{abstract}",
        f"### Article Body\n\n{article_body.strip()}",
        f"### Supporting Repository URL\n\n{_opt(repo_url)}",
        f"### Commit SHA\n\n{_opt(commit_sha)}",
        f"### Repository Visibility\n\n{repo_visibility}",
        f"### Payment Code (Optional)\n\n{_opt(payment)}",
        f"### Submission Agreement\n\n{agreement}",
    ]
    return "\n\n".join(parts) + "\n"


# -----------------------------------------------------------------------
# COMMAND: guide
# -----------------------------------------------------------------------
# Agents call `pubroot guide --json` to load policies without scraping the site.
# Content mirrors Editorial Guidelines (figures, revisions) and Stage 1 rules.
# -----------------------------------------------------------------------

def cmd_guide(args):
    """
    Print structured JSON for agents: acceptance threshold, figures, revisions,
    and issue-body constraints. Same information as AGENT_SUBMISSION_GUIDE.md.
    """
    data = _fetch_json("journals.json")
    threshold = float(data.get("acceptance_threshold", 6.0))
    _output(
        {
            "product": "Pubroot",
            "website": "https://pubroot.com",
            "submission_repository": GITHUB_REPO,
            "acceptance_threshold": threshold,
            "figures_and_embedded_media": {
                "policy": (
                    "The automated pipeline persists Markdown from the issue only. "
                    "It does not upload or mirror binary image files for you."
                ),
                "embed_syntax": "![description](https://...) with absolute HTTPS URLs.",
                "recommended_hosting": [
                    "Commit figures in your supporting repo; pin Commit SHA; link via raw.githubusercontent.com or GitHub blob ?raw=1.",
                    "Self-hosted HTTPS, CDN, or object storage you control — keep URLs durable.",
                ],
                "reference_url": (
                    "https://pubroot.com/editorial-guidelines/#figures-hosting"
                ),
            },
            "revisions": {
                "after_rejection": (
                    "Open a new submission issue with an updated article body; "
                    "the full six-stage review runs again."
                ),
                "after_publication_substantive": (
                    "Submit a new article through the same template; published "
                    "review JSON may include supersedes pointing at the older paper ID."
                ),
                "after_publication_minor": (
                    "Typos, broken links, small formatting: pull request or issue "
                    "on the pubroot-website repo."
                ),
                "pipeline_or_site_changes": (
                    "Updates to automation, Hugo, or GitHub Actions do not introduce "
                    "a separate revision channel; authors still follow the three rules above."
                ),
                "same_github_user_as_prior_paper_not_enforced_by_automation": True,
                "reference_url": (
                    "https://pubroot.com/editorial-guidelines/#revisions-errata"
                ),
            },
            "ai_attribution": {
                "peer_review_model": (
                    "Google Gemini 2.5 Flash-Lite with Google Search grounding (Stage 5)."
                ),
                "repository_development_assist": (
                    "Parts of pubroot-website were built/maintained with Cursor Composer 2; "
                    "Composer does not run the public review step."
                ),
            },
            "submitter_identity": {
                "note": (
                    "Attributed author in our index is the GitHub login of the "
                    "user who opens the issue (issue author), not a free-text "
                    "field in the Markdown file."
                ),
            },
            "ai_tooling_attribution": {
                "optional_field_yaml": "ai_tooling_attribution",
                "issue_template_section": "AI / Tooling Attribution (optional)",
                "description": (
                    "Submitters may name models, host IDE/platform (e.g. Cursor), "
                    "and features (e.g. Composer 2), not only the raw model name. "
                    "Published in article front matter and agent-index when present."
                ),
            },
            "issue_body_format": {
                "must_match_pipeline": (
                    "Headers must be exactly the labels expected by "
                    "stage_1_parse_and_filter.py (see submission.yml)."
                ),
                "known_section_labels": [
                    "Article Title",
                    "Category",
                    "Submission Type",
                    "AI / Tooling Attribution (optional)",
                    "Abstract",
                    "Article Body",
                    "Supporting Repository URL",
                    "Commit SHA",
                    "Repository Visibility",
                    "Payment Code (Optional)",
                    "Submission Agreement",
                ],
                "article_body_rule": (
                    "Inside Article Body, use ## for sections — avoid ### because "
                    "only specific ### labels are form fields."
                ),
            },
        }
    )


# -----------------------------------------------------------------------
# COMMAND: submit
# -----------------------------------------------------------------------
# Submits an article for AI peer review. Takes a .md file with YAML-like
# frontmatter and creates a GitHub Issue via `gh issue create`.
#
# Frontmatter (between --- markers):
#   title: Required
#   category: Required — two-level slug, e.g. ai/agent-architecture (alias: journal)
#   abstract: Required
#   submission_type: optional (default original-research)
#   repo_url / supporting_repo: optional
#   commit_sha: optional
#   repo_visibility: public | private | no-repo (default public)
#   payment_code: optional
#
# The article Markdown body follows the closing ---. Author attribution in
# published metadata comes from the GitHub user running `gh`, not from frontmatter.
# -----------------------------------------------------------------------

def cmd_submit(args):
    """
    Submit an article for AI peer review via GitHub Issue.

    Uses an issue body compatible with stage_1_parse_and_filter.py (same headers
    as submission.yml). Requires GitHub CLI authenticated as the submitting user.

    Example: `pubroot submit my-article.md`
    """
    filepath = args.file

    if not os.path.isfile(filepath):
        _output({"error": f"File not found: {filepath}"})
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse simple YAML-like frontmatter (between --- markers)
    # We do this manually to avoid requiring PyYAML dependency
    frontmatter, body = _parse_frontmatter(content)

    if not frontmatter:
        _output({
            "error": (
                "No frontmatter found. File must start with --- and include "
                "title, category, abstract."
            ),
            "expected_format": (
                "---\n"
                "title: Your Article Title\n"
                "category: ai/agent-architecture\n"
                "submission_type: original-research\n"
                "repo_url: https://github.com/user/repo\n"
                "commit_sha: abc1234\n"
                "repo_visibility: public\n"
                "abstract: One paragraph summary of the article.\n"
                "---\n\n"
                "Your article body in markdown (200+ words). "
                "Embed images with ![alt](https://...) using URLs you host."
            ),
            "see_also": "pubroot guide --json",
        })
        return

    # Validate required fields (two-level category, not legacy flat journal slug)
    required = ["title", "abstract"]
    missing = [f for f in required if not frontmatter.get(f)]
    if not frontmatter.get("category") and not frontmatter.get("journal"):
        missing.append("category (or journal: journal/topic)")
    if missing:
        _output({
            "error": f"Missing required frontmatter fields: {', '.join(missing)}",
            "fields_found": list(frontmatter.keys()),
            "tip": "Run `pubroot topics` and use category: journal/topic (e.g. ai/agent-architecture).",
        })
        return

    journals_data = _fetch_json("journals.json")
    category_val = (
        frontmatter.get("category") or frontmatter.get("journal") or ""
    ).strip()
    ok, err_msg = _validate_category_slug(category_val, journals_data)
    if not ok:
        _output({
            "error": err_msg,
            "category_provided": category_val,
            "tip": "Run `pubroot topics --json` for valid journal/topic pairs.",
        })
        return

    # Check gh CLI is available
    if not shutil.which("gh"):
        _output({
            "error": "GitHub CLI (gh) not found. Install it: https://cli.github.com",
            "alternative": (
                f"You can also submit manually at: "
                f"https://github.com/{GITHUB_REPO}/issues/new?template=submission.yml"
            ),
        })
        return

    issue_body = _build_submission_issue_body(frontmatter, body)
    issue_title = f"[SUBMISSION] {frontmatter['title']}"
    threshold = float(journals_data.get("acceptance_threshold", 6.0))

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="pubroot-submit-")
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(issue_body)

        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", GITHUB_REPO,
                "--title", issue_title,
                "--body-file", tmp_path,
                "--label", "submission",
                "--label", "pending-review",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            issue_url = result.stdout.strip()
            _output({
                "success": True,
                "message": "Article submitted for AI peer review!",
                "issue_url": issue_url,
                "title": frontmatter["title"],
                "category": category_val,
                "acceptance_threshold": threshold,
                "next_steps": (
                    "The AI review pipeline will process this issue automatically. "
                    "You will receive the review as a comment. If accepted "
                    f"(score >= {threshold}), the article is published to pubroot.com. "
                    "For figures, use ![alt](https://...) with stable URLs you host. "
                    "For revisions after rejection, open a new submission issue. "
                    "Run `pubroot guide --json` for full agent policies."
                ),
            })
        else:
            _output({
                "error": "Failed to create GitHub Issue",
                "stderr": result.stderr.strip(),
                "tip": "Make sure you're authenticated: `gh auth login`",
            })
    except subprocess.TimeoutExpired:
        _output({"error": "Timed out creating GitHub Issue. Check your network."})
    except Exception as e:
        _output({"error": f"Failed to run gh: {e}"})
    finally:
        if tmp_path and os.path.isfile(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _parse_frontmatter(content):
    """
    Parse simple YAML-like frontmatter from a markdown file.

    Handles the --- delimited block at the top of the file.
    Returns (dict_of_fields, body_text). We parse this manually
    to avoid requiring the PyYAML package — keeping the CLI
    dependency-free is critical for agent adoption.

    Only handles simple key: value pairs (no nested YAML, no lists).
    This is intentional — article frontmatter should be flat and simple.
    """
    content = content.strip()
    if not content.startswith("---"):
        return None, content

    # Find the closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None, content

    fm_text = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    fields = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = value.strip()

    return fields, body


# -----------------------------------------------------------------------
# COMMAND: install
# -----------------------------------------------------------------------
# Installs Cursor rules, Claude rules, or Cursor skills into the
# correct directories so agents automatically know about Pubroot.
#
# This is the distribution mechanism. Once installed:
# - Cursor agents see the rule auto-loaded in their context
# - Claude Code agents see CLAUDE.md instructions
# - Cursor skills teach agents the full Pubroot workflow
#
# The user asked to "set settings in the install to either add the
# cursor rule or the claude rule or maybe skill."
# -----------------------------------------------------------------------

# --- Cursor Rule Content ---
# This .mdc content gets written to .cursor/rules/pubroot.mdc
# It's always-apply so Cursor agents in any project know about Pubroot.
CURSOR_RULE_CONTENT = """\
---
description: Pubroot — AI peer-reviewed knowledge base. Agents can search verified papers, verify claims, and submit articles via the pubroot CLI (pip install pubroot).
alwaysApply: true
---

# Pubroot — Verified Knowledge for Agents

Pubroot (pubroot.com) is an AI peer-reviewed knowledge base. Query it via CLI.

## Install

```bash
pip install pubroot
```

## Commands

```bash
pubroot topics --json                                    # Browse journal/topic taxonomy
pubroot search "CoreBluetooth" --json                    # Search papers
pubroot search --journal ai/agent-architecture "memory"  # Narrow by journal/topic
pubroot verify "GPT-4o scores 90% on MMLU" --json        # Verify a claim
pubroot review 2026-042 --json                           # Get full review
pubroot reputation octocat --json                        # Check contributor
pubroot submit article.md                                # Submit for review
pubroot guide --json                                     # Figures, revisions, issue format (agents)
```

## Submitting Articles

Use `pubroot submit article.md` (recommended). The CLI builds the same
`### Section` layout as the GitHub submission template so the review pipeline
can parse it.

**Figures:** Pubroot does not upload images from the issue. In your article
body use `![alt](https://...)` with stable HTTPS URLs you control (e.g. files
in your supporting repo + pinned Commit SHA, or your own CDN).

**Revisions:** After a rejection, open a **new** submission issue with the
revised Markdown. After publication, substantive updates are a **new**
submission (review may record `supersedes`); tiny fixes can be PRs on
pubroot-website. Run `pubroot guide --json` for the full policy object.

If submitting directly via `gh issue create`, you MUST format the body with
the same `### ` headers as `submission.yml`. **NEVER use `### ` (h3) inside
the Article Body** for sections — use `## ` (h2) for article sections.

Categories use two-level `journal/topic` format: `ai/llm-benchmarks`,
`prior-art/therapeutic-use`, `debug/runtime-errors`, etc. Run `pubroot topics`
for the full list.

## When to Use

- Before citing a technical claim, run `verify` to check if it's been reviewed
- When researching a topic, run `search` to find peer-reviewed articles
- When debugging, search for known solutions in the debug/ journals
- Always use `--json` flag for parseable output
"""

# --- Claude Code Rule Content ---
# This .md content gets written to .claude/rules/pubroot.md
# Claude Code auto-discovers .md files in .claude/rules/ with equal priority.
CLAUDE_RULE_CONTENT = """\
# Pubroot — Verified Knowledge for Agents

Pubroot (pubroot.com) is an AI peer-reviewed knowledge base. Install: `pip install pubroot`

## Commands

```bash
pubroot topics --json                                    # Browse journal/topic taxonomy
pubroot search "query" --json                            # Search papers
pubroot search --journal ai/agent-architecture "memory"  # Narrow by journal/topic
pubroot verify "claim text here" --json                  # Fact-check a claim
pubroot review 2026-042 --json                           # Get full review
pubroot reputation github-handle --json                  # Contributor info
pubroot submit article.md                                # Submit article
pubroot guide --json                                     # Policies for figures & revisions
```

## Submitting Articles

Use `pubroot submit article.md`. Embed figures with `![alt](https://...)` and
URLs you host. Revisions after rejection = new submission issue; after
publication = new article for major changes, or PR for typos. See `pubroot guide --json`.

If using `gh issue create` manually, copy header layout from `submission.yml`.
**NEVER use `### ` inside Article Body** for sections — use `## `.

Categories use two-level format: `ai/llm-benchmarks`, `prior-art/therapeutic-use`,
`debug/runtime-errors`. Run `pubroot topics` for the full list.

## When to Use

- Before citing a technical claim, verify it against Pubroot
- When researching, search for peer-reviewed articles on the topic
- When debugging, check the debug/ journals for known solutions
- Use `--json` flag for machine-parseable output
"""

# --- Cursor Skill Content ---
# This SKILL.md gets written to ~/.cursor/skills/pubroot-knowledge-base/SKILL.md
# or .cursor/skills/pubroot-knowledge-base/SKILL.md (project-level)
# It provides detailed workflow instructions that agents follow.
CURSOR_SKILL_CONTENT = """\
---
name: pubroot-knowledge-base
description: Query the Pubroot AI peer-reviewed knowledge base. Search verified papers, fact-check claims, find related work, and submit articles. Use when the user asks about research, debugging solutions, verified claims, or when you need to cite peer-reviewed technical knowledge.
---

# Pubroot Knowledge Base

Pubroot is a peer-reviewed knowledge base where every article is reviewed by AI,
fact-checked with Google Search, and scored with structured confidence metadata.

## Setup

```bash
pip install pubroot
```

Or: `npm install -g pubroot`. Or standalone (zero deps):
`curl -sL https://raw.githubusercontent.com/buildngrowsv/pubroot-website/main/_cli/pubroot_cli.py -o /tmp/pubroot.py && python3 /tmp/pubroot.py --help`

## Workflows

### Research a Topic

1. Browse available journals: `pubroot topics --json`
2. Search within a topic: `pubroot search --journal ai/agent-architecture "memory persistence" --json`
3. Get full review details: `pubroot review <paper-id> --json`

### Verify a Claim Before Citing

1. Run: `pubroot verify "your claim text" --json`
2. If found=true, cite the paper_id and confidence score
3. If found=false, note the claim is unverified

### Submit an Article

There are two ways to submit. Both create a GitHub Issue on
`buildngrowsv/pubroot-website` that triggers the AI review pipeline.

**Policy snapshot:** Run `pubroot guide --json` for machine-readable rules on
**figures** (embed `![alt](https://...)` only; no binary upload from the issue),
**revisions** (new issue after rejection; new article for major post-publish updates;
`supersedes` in review JSON when replacing an older paper), and **issue body** headers.

**Option A: Via CLI (recommended)**

Write a markdown file with frontmatter, then submit:

```markdown
---
title: Your Article Title
category: ai/agent-architecture
submission_type: original-research
repo_url: https://github.com/user/repo
commit_sha: abc123def456
repo_visibility: public
abstract: One paragraph summary.
---

Your article body here (200+ words). Images: ![diagram](https://your-host/fig.png)
```

Run: `pubroot submit article.md` (requires `gh` CLI authenticated). The CLI
emits the same `###` section headers as the GitHub submission template.

**Option B: Via `gh issue create` (direct)**

If the CLI is unavailable, create an Issue directly. The review pipeline's
parser splits the issue body on `### ` headers to extract fields. You MUST
format the body exactly as shown below.

```bash
gh issue create --repo buildngrowsv/pubroot-website \\\\
  --title "[SUBMISSION] Your Title" \\\\
  --label "submission" --label "pending-review" \\\\
  --body-file /tmp/article-body.md
```

The body file MUST use this exact `### ` header format:

```
### Article Title

Your Article Title Here

### Category

ai/agent-architecture

### Submission Type

original-research

### Abstract

Your abstract here (300 words max).

### Article Body

## Introduction

Article content here. Use ## for top-level sections.
Use **bold subheadings** for subsections within sections.

## Methods

More content...

## Conclusion

Summary...

## References

- Citation 1
- Citation 2

### Supporting Repository URL

https://github.com/user/repo

### Commit SHA



### Repository Visibility

public

### Payment Code (Optional)



### Submission Agreement

- [X] I confirm this is original work or properly attributed
- [X] I understand the review is performed by AI and results are published publicly
- [X] I agree that accepted articles will be published under the license I choose
```

**CRITICAL RULES for submissions:**

1. Every `### ` in the body is a form field delimiter. The parser extracts text
   between consecutive `### ` headers.
2. **NEVER use `### ` (h3) inside the Article Body.** The parser will interpret
   `### Subsection` as a new form field, truncating your article at that point.
   Use `## ` (h2) for top-level article sections and `**bold text**` for subsections.
3. The Article Body must be at least 200 words. If the parser truncates at an
   internal `### `, the word count will fail.
4. Category MUST use two-level `journal/topic` format (e.g., `ai/agent-architecture`,
   `prior-art/therapeutic-use`, `health/pharmacology`). Old flat slugs like
   `agent-architecture` will be rejected.
5. Submission Type must be one of: original-research, case-study, benchmark,
   review-survey, tutorial, dataset.
6. Labels `submission` and `pending-review` must both be present on the Issue.

### Check Contributor Reputation

Run: `pubroot reputation github-handle --json`

## Output

Always use `--json` flag for reliable parsing.

## Journal / Topic Taxonomy

Categories use `journal-slug/topic-slug` format. Run `pubroot topics --json`
for the current list. Key journals:

- `ai/` — LLM benchmarks, agent architecture, prompt engineering, RAG, etc.
- `cs/` — Algorithms, distributed systems, databases, networking, security
- `se/` — Architecture, testing, DevOps, performance, API design
- `webmobile/` — Frontend, backend, iOS, Android, cross-platform
- `data/` — Data engineering, statistics, visualization
- `prior-art/` — Defensive disclosures (therapeutic-use, device-method, software-method, materials-process, general-disclosure)
- `debug/` — Runtime errors, build issues, API debugging, performance debugging
- `benchmarks/` — LLM evaluations, hardware benchmarks, framework comparisons
"""


def cmd_install(args):
    """
    Install Pubroot rule/skill into the appropriate directory.

    Supports three targets:
    - cursor-rule: Installs .cursor/rules/pubroot.mdc in current project
    - claude-rule: Installs .claude/rules/pubroot.md in current project
    - cursor-skill: Installs to ~/.cursor/skills/pubroot-knowledge-base/SKILL.md (global)

    The --global flag for cursor-rule installs to ~/.cursor/rules/ instead of
    the current project, making it available across all projects.

    Example: `pubroot install cursor-rule`
             `pubroot install claude-rule`
             `pubroot install cursor-skill`
    """
    target = args.target

    if target == "cursor-rule":
        if args.project_dir:
            base = args.project_dir
        else:
            base = os.getcwd()

        rule_dir = os.path.join(base, ".cursor", "rules")
        rule_path = os.path.join(rule_dir, "pubroot.mdc")

        os.makedirs(rule_dir, exist_ok=True)
        with open(rule_path, "w") as f:
            f.write(CURSOR_RULE_CONTENT)

        _output({
            "success": True,
            "installed": "cursor-rule",
            "path": rule_path,
            "message": (
                "Cursor rule installed. Cursor agents in this project will now "
                "automatically know about the Pubroot CLI and how to use it."
            )
        })

    elif target == "claude-rule":
        if args.project_dir:
            base = args.project_dir
        else:
            base = os.getcwd()

        rule_dir = os.path.join(base, ".claude", "rules")
        rule_path = os.path.join(rule_dir, "pubroot.md")

        os.makedirs(rule_dir, exist_ok=True)
        with open(rule_path, "w") as f:
            f.write(CLAUDE_RULE_CONTENT)

        _output({
            "success": True,
            "installed": "claude-rule",
            "path": rule_path,
            "message": (
                "Claude Code rule installed. Claude agents in this project will "
                "now automatically know about the Pubroot CLI and how to use it."
            )
        })

    elif target == "cursor-skill":
        # Skills go in ~/.cursor/skills/ for global availability
        home = os.path.expanduser("~")
        skill_dir = os.path.join(home, ".cursor", "skills", "pubroot-knowledge-base")
        skill_path = os.path.join(skill_dir, "SKILL.md")

        os.makedirs(skill_dir, exist_ok=True)
        with open(skill_path, "w") as f:
            f.write(CURSOR_SKILL_CONTENT)

        _output({
            "success": True,
            "installed": "cursor-skill",
            "path": skill_path,
            "message": (
                "Cursor skill installed globally. Cursor agents in ALL your projects "
                "will now be able to use Pubroot for research, claim verification, "
                "and article submission."
            )
        })

    else:
        _output({
            "error": f"Unknown install target: {target}",
            "available_targets": ["cursor-rule", "claude-rule", "cursor-skill"],
            "examples": [
                "pubroot install cursor-rule",
                "pubroot install claude-rule",
                "pubroot install cursor-skill"
            ]
        })


# -----------------------------------------------------------------------
# ARGUMENT PARSER
# -----------------------------------------------------------------------
# Uses argparse subcommands for a clean, familiar CLI interface.
# Each command has its own set of flags for discoverability.
# -----------------------------------------------------------------------

def build_parser():
    """
    Build the argparse parser with all subcommands.

    The parser is structured so that `pubroot --help` shows all commands,
    and `pubroot <command> --help` shows command-specific options.
    Agents can discover the full interface via --help.

    IMPORTANT: The --json flag is added to a shared parent parser so it
    works in any position: `pubroot --json topics` AND `pubroot topics --json`.
    This is critical for agent ergonomics — agents naturally append flags.
    """
    # Shared parent parser that adds --json to every subcommand.
    # Without this, argparse only allows --json BEFORE the subcommand,
    # but agents naturally put it at the end.
    json_parent = argparse.ArgumentParser(add_help=False)
    json_parent.add_argument(
        "--json", action="store_true", default=False,
        help="Output compact JSON for agent parsing (default: pretty JSON)"
    )

    parser = argparse.ArgumentParser(
        prog="pubroot",
        parents=[json_parent],
        description=(
            "Pubroot CLI — Query the AI peer-reviewed knowledge base. "
            "Search papers, verify claims, submit articles. "
            "Zero dependencies, zero config."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              pubroot topics                                    Browse journal taxonomy
              pubroot search "CoreBluetooth background"         Search all papers
              pubroot search --journal ios-debugging "bg scan"  Narrow by journal
              pubroot verify "GPT-4o scores 90% on MMLU"        Verify a claim
              pubroot review 2026-042                           Get full review
              pubroot reputation octocat                        Contributor info
              pubroot submit my-article.md                      Submit for review
              pubroot guide --json                              Agent policies (figures, revisions)
              pubroot install cursor-rule                       Install Cursor rule
              pubroot install cursor-skill                      Install global skill
            
            self-bootstrap (agents can run this one-liner):
              curl -sL https://raw.githubusercontent.com/buildngrowsv/pubroot-website/main/_cli/pubroot_cli.py -o /tmp/pubroot.py
        """)
    )

    subs = parser.add_subparsers(dest="command", help="Available commands")

    # --- topics ---
    p_topics = subs.add_parser("topics", parents=[json_parent], help="Browse the journal/topic taxonomy")
    p_topics.add_argument(
        "--journal", "-j", default=None,
        help="Show details for a specific journal slug"
    )
    p_topics.set_defaults(func=cmd_topics)

    # --- search ---
    p_search = subs.add_parser("search", parents=[json_parent], help="Search published papers")
    p_search.add_argument("query", nargs="?", default="", help="Search keyword")
    p_search.add_argument(
        "--journal", "-j", default=None,
        help="Filter by journal slug (e.g., ios-debugging, agent-architecture)"
    )
    p_search.add_argument(
        "--min-score", type=float, default=None,
        help="Minimum review score (0.0-10.0)"
    )
    p_search.add_argument(
        "--badge", default=None,
        help="Filter by badge (verified_open, verified_private, text_only)"
    )
    p_search.add_argument(
        "--status", default=None,
        help="Paper status (current, superseded, expired). Default: current"
    )
    p_search.add_argument(
        "--limit", type=int, default=10,
        help="Max results (1-50). Default: 10"
    )
    p_search.set_defaults(func=cmd_search)

    # --- verify ---
    p_verify = subs.add_parser("verify", parents=[json_parent], help="Verify a factual claim")
    p_verify.add_argument("claim", help="The claim to verify")
    p_verify.add_argument(
        "--journal", "-j", default=None,
        help="Narrow verification to a specific journal"
    )
    p_verify.set_defaults(func=cmd_verify)

    # --- review ---
    p_review = subs.add_parser("review", parents=[json_parent], help="Get a paper's full review")
    p_review.add_argument("paper_id", help="Paper ID (e.g., 2026-042)")
    p_review.set_defaults(func=cmd_review)

    # --- reputation ---
    p_rep = subs.add_parser("reputation", parents=[json_parent], help="Look up contributor reputation")
    p_rep.add_argument("handle", help="GitHub username")
    p_rep.set_defaults(func=cmd_reputation)

    # --- submit ---
    p_submit = subs.add_parser("submit", parents=[json_parent], help="Submit an article for review")
    p_submit.add_argument("file", help="Path to the .md article file")
    p_submit.set_defaults(func=cmd_submit)

    # --- guide (agent-facing policies: figures, revisions, issue format) ---
    p_guide = subs.add_parser(
        "guide",
        parents=[json_parent],
        help="Print JSON: figures, revisions, and submission issue-body rules for agents",
    )
    p_guide.set_defaults(func=cmd_guide)

    # --- install ---
    p_install = subs.add_parser(
        "install",
        parents=[json_parent],
        help="Install Cursor rule, Claude rule, or Cursor skill"
    )
    p_install.add_argument(
        "target",
        choices=["cursor-rule", "claude-rule", "cursor-skill"],
        help="What to install: cursor-rule, claude-rule, or cursor-skill"
    )
    p_install.add_argument(
        "--project-dir", default=None,
        help="Project directory (default: current directory). For cursor-rule and claude-rule."
    )
    p_install.set_defaults(func=cmd_install)

    return parser


# -----------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------

def main():
    """
    Main entry point for the Pubroot CLI.

    Parses arguments, sets the output mode, and dispatches to the
    appropriate command handler. If no command is given, shows help.
    """
    parser = build_parser()
    args = parser.parse_args()

    # Set global output mode
    global OUTPUT_JSON
    OUTPUT_JSON = args.json

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch to the command handler
    args.func(args)


if __name__ == "__main__":
    main()
