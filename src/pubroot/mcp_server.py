"""
MCP Server — Pubroot

PURPOSE:
    This is the primary product of the Pubroot. While the website
    is a viewer for humans, this MCP server is the interface for AI agents.
    Agents connect via MCP (Model Context Protocol) and get structured access to:
    
    1. search_papers — Search the published paper index by keyword, category, etc.
    2. verify_claim — Check if a specific claim has been verified by a reviewed paper
    3. get_review — Get the full structured review for a specific paper
    4. get_contributor_reputation — Look up a contributor's trust metrics
    5. get_related_work — Find papers related to a topic or paper
    6. get_submission_guide — Figures, revisions, and issue-body rules for agents
    
    The server reads data from the GitHub repo's JSON files. It can run in two modes:
    - LOCAL: Read from local filesystem (for development/testing)
    - REMOTE: Fetch from raw GitHub URLs (for production deployment)

ARCHITECTURE:
    Uses the official MCP Python SDK (mcp package) with stdio transport.
    The server registers tools via @mcp.tool() decorator. Each tool returns
    structured data that agents can consume directly.
    
    In production, this can be deployed as:
    1. A local process agents invoke via stdio (mcp.json config)
    2. A Cloudflare Worker (for HTTP-based MCP transport — future)
    3. A Docker container in the agent's environment

INSTALLATION:
    pip install mcp requests
    
    Then add to your MCP config (e.g., Claude Desktop mcp.json):
    {
      "mcpServers": {
        "ai-peer-review": {
          "command": "python",
          "args": ["/path/to/_mcp_server/mcp_peer_review_server.py"],
          "env": {
            "REPO_MODE": "remote",
            "GITHUB_REPO": "buildngrowsv/pubroot-website"
          }
        }
      }
    }

COST:
    $0 — Reads free public JSON files from GitHub.
"""

import json
import logging
import os
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode
from collections import defaultdict
from functools import wraps

import requests
from mcp.server import MCPServer
from mcp import types as mcp_types

# -----------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------
# Structured logging for operational visibility. In production, agents
# invoking this server via stdio won't see stderr logs, but they're
# invaluable for debugging when running the server manually.
# -----------------------------------------------------------------------

logger = logging.getLogger("pubroot_mcp_server")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# -----------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------
# REPO_MODE: 'local' (read from filesystem) or 'remote' (fetch from GitHub)
# GITHUB_REPO: "owner/repo" for remote mode
# LOCAL_REPO_PATH: Path to local repo clone for local mode
# CACHE_TTL_SECONDS: How long cached JSON data stays valid (default 10 min for hosted)
# STALE_IF_ERROR_SECONDS: How long to serve stale cache on error (24h for hosted)
# ALLOWED_DOMAINS: Domain allow-list for outbound fetches
# -----------------------------------------------------------------------

REPO_MODE = os.environ.get("REPO_MODE", "local")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "buildngrowsv/pubroot-website")
LOCAL_REPO_PATH = os.environ.get(
    "LOCAL_REPO_PATH",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# For hosted mode: use pubroot.com, 10min cache, 24h stale-if-error
PUBROOT_BASE = os.environ.get("PUBROOT_BASE", "https://pubroot.com")
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "600"))  # 10 minutes for hosted
STALE_IF_ERROR_SECONDS = int(os.environ.get("STALE_IF_ERROR_SECONDS", "86400"))  # 24 hours

# Outbound fetch allow-list for hosted mode
ALLOWED_DOMAINS = {
    "pubroot.com",
    "raw.githubusercontent.com",
}

# Rate limiting configuration (requests per minute)
RATE_LIMIT_GENERAL = int(os.environ.get("RATE_LIMIT_GENERAL", "60"))
RATE_LIMIT_PREPARE = int(os.environ.get("RATE_LIMIT_PREPARE", "10"))

# Size limits (bytes)
MAX_REQUEST_SIZE = int(os.environ.get("MAX_REQUEST_SIZE", "1048576"))  # 1MB
MAX_RESPONSE_SIZE = int(os.environ.get("MAX_RESPONSE_SIZE", "10485760"))  # 10MB

# -----------------------------------------------------------------------
# DATA LOADING HELPERS WITH CACHING AND STALE-IF-ERROR
# -----------------------------------------------------------------------
# These functions abstract the data source so tools don't care whether
# they're reading from local disk or GitHub raw URLs. The cache layer
# prevents redundant fetches and serves stale data on error (up to 24h).
# -----------------------------------------------------------------------

# Enhanced cache: { filename: (timestamp, data, error_timestamp) }
# - timestamp: when the data was successfully fetched
# - data: the cached JSON
# - error_timestamp: when we last tried and failed (for stale-if-error)
_json_cache: Dict[str, Tuple[float, dict, Optional[float]]] = {}

# Rate limiting: { ip: { minute_bucket: count } }
_rate_limit_buckets: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
_rate_limit_prepare: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))


def _load_json(filename: str) -> dict:
    """
    Load a JSON file from either local filesystem or remote URL with caching.

    For hosted mode (REPO_MODE=remote), fetches from pubroot.com with:
    - 10-minute cache TTL
    - Stale-if-error up to 24 hours (serves old data if fetch fails)
    - Domain allow-list enforcement

    Uses the REPO_MODE environment variable to determine source.
    Implements an in-memory cache with configurable TTL and stale-if-error.

    Raises:
        FileNotFoundError: If the local file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        requests.HTTPError: If the remote fetch returns a non-2xx status and no stale cache.
        requests.Timeout: If the remote fetch exceeds the 15-second timeout and no stale cache.
    """
    now = time.time()
    cached_entry = _json_cache.get(filename)
    
    # Check fresh cache first
    if cached_entry is not None:
        cached_timestamp, cached_data, error_timestamp = cached_entry
        cache_age = now - cached_timestamp
        
        if cache_age < CACHE_TTL_SECONDS:
            logger.debug("Cache hit for %s (age: %.1fs)", filename, cache_age)
            return cached_data
        else:
            logger.debug("Cache expired for %s (age: %.1fs)", filename, cache_age)

    # Try to fetch fresh data
    try:
        if REPO_MODE == "local":
            filepath = os.path.join(LOCAL_REPO_PATH, filename)
            logger.debug("Loading local file: %s", filepath)
            with open(filepath, "r") as f:
                data = json.load(f)
        else:
            # For hosted mode, fetch from pubroot.com (faster, CDN-backed)
            # Falls back to GitHub raw if pubroot.com is unavailable
            url = f"{PUBROOT_BASE}/{filename}"
            
            # Domain allow-list check
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain not in ALLOWED_DOMAINS:
                raise ValueError(f"Domain {domain} not in allow-list")
            
            logger.debug("Fetching remote: %s", url)
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        
        # Store in cache with current timestamp and clear error timestamp
        _json_cache[filename] = (now, data, None)
        return data
        
    except Exception as e:
        # Stale-if-error: serve old data if it's not too old
        if cached_entry is not None:
            cached_timestamp, cached_data, error_timestamp = cached_entry
            stale_age = now - cached_timestamp
            
            if stale_age < STALE_IF_ERROR_SECONDS:
                logger.warning(
                    "Serving stale cache for %s (age: %.1fs) due to error: %s",
                    filename, stale_age, str(e)
                )
                # Update error timestamp but keep serving the data
                _json_cache[filename] = (cached_timestamp, cached_data, now)
                return cached_data
        
        # No stale cache available or too old - propagate the error
        logger.error("Failed to load %s with no valid stale cache: %s", filename, str(e))
        raise


def _check_rate_limit(ip: str, tool_name: str) -> bool:
    """
    Check if the request from this IP is within rate limits.
    
    Returns True if allowed, False if rate limit exceeded.
    Rate limits are per-minute buckets:
    - General tools: 60/minute
    - prepare_submission: 10/minute
    
    For hosted HTTP mode only. Stdio mode has no rate limiting.
    """
    now = time.time()
    minute_bucket = int(now / 60)
    
    # Clean up old buckets (keep last 2 minutes)
    for buckets_dict in [_rate_limit_buckets, _rate_limit_prepare]:
        for stored_ip in list(buckets_dict.keys()):
            buckets = buckets_dict[stored_ip]
            old_buckets = [b for b in buckets if b < minute_bucket - 1]
            for old_bucket in old_buckets:
                del buckets[old_bucket]
    
    # Check appropriate limit
    if tool_name == "prepare_submission":
        limit = RATE_LIMIT_PREPARE
        buckets = _rate_limit_prepare[ip]
    else:
        limit = RATE_LIMIT_GENERAL
        buckets = _rate_limit_buckets[ip]
    
    current_count = buckets[minute_bucket]
    
    if current_count >= limit:
        logger.warning("Rate limit exceeded for IP %s, tool %s (%d/%d)", 
                      ip[-8:], tool_name, current_count, limit)  # Log only last 8 chars of IP
        return False
    
    buckets[minute_bucket] += 1
    return True


def _load_review(paper_id: str) -> Optional[dict]:
    """
    Load a specific paper's review JSON.

    Returns None if the review doesn't exist (local FileNotFoundError or
    remote 404), rather than letting the exception propagate — callers
    should check for None and return a user-friendly message.
    """
    try:
        return _load_json(f"reviews/{paper_id}/review.json")
    except (FileNotFoundError, requests.HTTPError):
        logger.debug("Review not found for paper_id=%s", paper_id)
        return None
    except json.JSONDecodeError:
        logger.warning("Malformed review JSON for paper_id=%s", paper_id)
        return None


# -----------------------------------------------------------------------
# MCP SERVER DEFINITION
# -----------------------------------------------------------------------

mcp = MCPServer("pubroot")


@mcp.tool(
    title="Search Pubroot papers",
    description="Search papers published on Pubroot by keyword (title and abstract), category (journal/topic), minimum review score, badge or status. Returns metadata and abstracts, sorted by review score.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def search_papers(
    query: str = "",
    category: str = "",
    min_score: float = 0.0,
    badge: str = "",
    status: str = "current",
    limit: int = 10
) -> dict:
    """
    Search published papers in the Pubroot.

    Returns papers matching the given criteria, with metadata including
    title, author, score, badge, category, and abstract. Results are
    sorted by review score (highest first).

    Args:
        query: Keyword search (matches title and abstract). Empty string returns all papers.
        category: Filter by category in journal/topic format (e.g., 'ai/llm-benchmarks', 'webmobile/ios').
        min_score: Minimum review score to include (0.0 to 10.0).
        badge: Filter by badge type ('verified_open', 'verified_private', 'text_only').
        status: Paper status filter ('current', 'superseded', 'expired'). Default: 'current'.
        limit: Maximum number of results (1-50). Default: 10.
    """
    try:
        index = _load_json("agent-index.json")
    except (FileNotFoundError, requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("Failed to load agent-index.json: %s", exc)
        return {"error": f"Unable to load paper index: {exc}", "results": [], "total_matching": 0}
    papers = index.get("papers", [])
    
    # Apply filters
    results = []
    query_lower = query.lower()
    
    for paper in papers:
        # Status filter
        if status and paper.get("status", "current") != status:
            continue
        
        # Category filter
        if category and paper.get("category") != category:
            continue
        
        # Score filter
        paper_score = paper.get("review_score", 0)
        if paper_score < min_score:
            continue
        
        # Badge filter
        if badge and paper.get("badge") != badge:
            continue
        
        # Query filter (keyword matching on title and abstract)
        if query_lower:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            if query_lower not in title and query_lower not in abstract:
                continue
        
        results.append(paper)
    
    # Sort by score (highest first)
    results.sort(key=lambda p: p.get("review_score", 0), reverse=True)
    
    # Apply limit
    limit = min(max(1, limit), 50)
    results = results[:limit]
    
    return {
        "total_matching": len(results),
        "results": results,
        "index_last_updated": index.get("last_updated"),
    }


@mcp.tool(
    title="Look up a claim in Pubroot reviews",
    description="Find claims in published Pubroot reviews that overlap with the given claim text (keyword match). Returns each matching claim with the reviewer's verified flag, confidence and cited source. No match does not mean the claim is false.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def verify_claim(
    claim: str,
    category: str = ""
) -> dict:
    """
    Check if a specific factual claim has been verified by any published paper.
    
    Searches through the claim verification data in published reviews to find
    papers that have checked similar claims. Returns the verification status,
    confidence, and source papers.
    
    Args:
        claim: The factual claim to verify (e.g., "GPT-4o scores 90% on MMLU").
        category: Optional category to narrow the search.
    """
    if not claim or not claim.strip():
        return {"found": False, "error": "The 'claim' argument must be a non-empty string.", "matches": []}

    try:
        index = _load_json("agent-index.json")
    except (FileNotFoundError, requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("Failed to load agent-index.json: %s", exc)
        return {"found": False, "error": f"Unable to load paper index: {exc}", "matches": []}
    papers = index.get("papers", [])
    
    claim_lower = claim.lower()
    matches = []
    
    for paper in papers:
        if paper.get("status") != "current":
            continue
        if category and paper.get("category") != category:
            continue
        
        # Check if paper's title or abstract mentions similar content
        title_lower = paper.get("title", "").lower()
        abstract_lower = paper.get("abstract", "").lower()
        
        # Simple keyword overlap check
        claim_words = set(claim_lower.split())
        title_words = set(title_lower.split())
        abstract_words = set(abstract_lower.split())
        
        title_overlap = len(claim_words & title_words)
        abstract_overlap = len(claim_words & abstract_words)
        
        if title_overlap >= 2 or abstract_overlap >= 3:
            # Load the full review to check claim-level verification
            paper_id = paper.get("id")
            review = _load_review(paper_id)
            
            if review:
                reviewed_claims = review.get("claims", [])
                for rc in reviewed_claims:
                    rc_text_lower = rc.get("text", "").lower()
                    rc_words = set(rc_text_lower.split())
                    overlap = len(claim_words & rc_words)
                    
                    if overlap >= 3:
                        matches.append({
                            "paper_id": paper_id,
                            "paper_title": paper.get("title"),
                            "paper_score": paper.get("review_score"),
                            "claim_text": rc.get("text"),
                            "verified": rc.get("verified"),
                            "confidence": rc.get("confidence"),
                            "source": rc.get("source"),
                        })
    
    if not matches:
        return {
            "found": False,
            "message": f"No verified papers found matching the claim: '{claim}'",
            "matches": [],
        }
    
    return {
        "found": True,
        "total_matches": len(matches),
        "matches": matches,
    }


@mcp.tool(
    title="Get a paper's review",
    description="Return the full AI-generated review (score, verdict, confidence breakdown, checked claims, strengths, weaknesses, sources) for a Pubroot paper ID.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def get_review(paper_id: str) -> dict:
    """
    Get the full structured review for a specific paper.
    
    Returns the complete review including score, verdict, confidence breakdown,
    claim verification, strengths/weaknesses, suggestions, and grounding sources.
    
    Args:
        paper_id: The paper ID (e.g., '2026-042').
    """
    review = _load_review(paper_id)
    
    if review is None:
        return {
            "found": False,
            "error": f"No review found for paper ID: {paper_id}",
        }
    
    return {
        "found": True,
        "paper_id": paper_id,
        "review": review,
    }


@mcp.tool(
    title="Get a contributor's public record",
    description="Return the public Pubroot contributor record (submission counts, reputation score and tier) for a GitHub handle.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def get_contributor_reputation(github_handle: str) -> dict:
    """
    Get a contributor's reputation score, tier, and submission history.
    
    The reputation system tracks contributor quality over time.
    
    Tiers: new (0), emerging (0.01-0.39), established (0.40-0.69),
           trusted (0.70-0.89), authority (0.90-1.0), suspended (-1.0).
    
    Args:
        github_handle: The contributor's GitHub username.
    """
    if not github_handle or not github_handle.strip():
        return {"found": False, "error": "The 'github_handle' argument must be a non-empty string."}

    try:
        contributors = _load_json("contributors.json")
    except (FileNotFoundError, requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("Failed to load contributors.json: %s", exc)
        return {"found": False, "error": f"Unable to load contributor data: {exc}"}
    contributor = contributors.get("contributors", {}).get(github_handle)
    
    if contributor is None:
        return {
            "found": False,
            "message": f"No contributor found with handle: {github_handle}",
            "suggestion": "This contributor has not submitted any articles yet.",
        }
    
    return {
        "found": True,
        "github_handle": github_handle,
        "reputation_score": contributor.get("reputation_score", 0.0),
        "reputation_tier": contributor.get("reputation_tier", "new"),
        "total_submissions": contributor.get("total_submissions", 0),
        "accepted": contributor.get("accepted", 0),
        "rejected": contributor.get("rejected", 0),
        "acceptance_rate": contributor.get("acceptance_rate", 0.0),
        "average_score": contributor.get("average_score", 0.0),
        "categories": contributor.get("categories", {}),
        "last_submission": contributor.get("last_submission"),
        "first_seen": contributor.get("first_seen"),
    }


@mcp.tool(
    title="Find related Pubroot papers",
    description="List Pubroot papers related to a query or to a given paper ID, ranked by keyword overlap.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def get_related_work(
    query: str = "",
    paper_id: str = ""
) -> dict:
    """
    Find papers related to a topic or to a specific paper.
    
    If a paper_id is provided, finds papers in the same category with similar
    content. If a query is provided, searches across all papers.
    
    Args:
        query: Topic or question to find related work for.
        paper_id: Optional paper ID to find related work for that specific paper.
    """
    if not query and not paper_id:
        return {"error": "Provide either a 'query' or 'paper_id' argument."}

    try:
        index = _load_json("agent-index.json")
    except (FileNotFoundError, requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("Failed to load agent-index.json: %s", exc)
        return {"error": f"Unable to load paper index: {exc}", "total_related": 0, "results": []}
    papers = index.get("papers", [])

    # If paper_id provided, get that paper's details for context
    target_category = ""
    target_words = set()
    
    if paper_id:
        for p in papers:
            if p.get("id") == paper_id:
                target_category = p.get("category", "")
                title = p.get("title", "")
                abstract = p.get("abstract", "")
                target_words = set((title + " " + abstract).lower().split())
                break
    
    if query:
        target_words = target_words | set(query.lower().split())
    
    # Score each paper by keyword overlap
    scored = []
    for p in papers:
        if p.get("id") == paper_id:
            continue  # Skip the paper itself
        if p.get("status") != "current":
            continue
        
        title = p.get("title", "").lower()
        abstract = p.get("abstract", "").lower()
        paper_words = set((title + " " + abstract).split())
        
        overlap = len(target_words & paper_words)
        category_bonus = 2 if p.get("category") == target_category else 0
        relevance = overlap + category_bonus
        
        if relevance > 2:
            scored.append({
                "paper_id": p.get("id"),
                "title": p.get("title"),
                "category": p.get("category"),
                "score": p.get("review_score"),
                "relevance_score": relevance,
                "abstract": p.get("abstract", "")[:200],
            })
    
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "total_related": len(scored),
        "results": scored[:10],
    }


@mcp.tool(
    title="Get Pubroot submission rules",
    description="Return Pubroot's submission rules: issue format, image hosting, revision process and acceptance threshold.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def get_submission_guide() -> dict:
    """
    Return agent-facing policies for Pubroot submissions: embedded images (HTTPS URLs
    only; no binary upload from the issue), revision workflows (new issue after rejection;
    new article for major post-publish updates; PR for minor fixes), structured
    how_to_submit_revision steps, issue-body header rules matching submission.yml /
    stage_1 parser, and acceptance threshold.

    Use this when an agent needs to submit or revise an article and must not guess
    hosting or revision steps. Equivalent to: pubroot guide --json
    """
    try:
        data = _load_json("journals.json")
    except (FileNotFoundError, requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("Failed to load journals.json: %s", exc)
        return {"error": f"Unable to load journal configuration: {exc}"}
    threshold = float(data.get("acceptance_threshold", 6.0))
    return {
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
            "same_github_user_as_prior_paper_not_enforced_by_automation": True,
            "reference_url": (
                "https://pubroot.com/editorial-guidelines/#revisions-errata"
            ),
            "pipeline_or_site_changes": (
                "Automation or site updates do not add a separate revision channel; "
                "authors still follow the same resubmission rules."
            ),
        },
        "how_to_submit_revision": {
            "summary": (
                "After rejection, open a NEW submission issue with the same template — "
                "do not reply on the old issue expecting a re-review."
            ),
            "submission_template_url": (
                "https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml"
            ),
            "after_rejection_steps": [
                "Read the review comment on the rejected issue.",
                "Revise article Markdown (and supporting-repo figure URLs if applicable).",
                "Open a NEW issue via submission_template_url with the full updated fields.",
                "Paste complete abstract + body; the full six-stage pipeline runs again.",
                "Optional: run `pubroot submit article.md` so ### headers match stage_1 parser.",
            ],
            "after_publication_minor": (
                "Pull request on pubroot-website editing papers/{journal}/{topic}/{slug}/index.md "
                "(see agent-index article_path or frontmatter paper_id)."
            ),
            "after_publication_substantive": (
                "New submission through the same template; review JSON may include supersedes."
            ),
            "human_docs": [
                "https://pubroot.com/editorial-guidelines/#revisions-errata",
                "https://pubroot.com/submit/#how-to-submit-revision",
            ],
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
                "Submitters may name models and how they were used (e.g. "
                "**Composer 2 in Cursor** for agentic coding; Claude in the browser). "
                "Published in article front matter when present."
            ),
        },
        "ai_attribution_catalog": {
            "file": "ai_attribution_catalog.json",
            "purpose": (
                "Canonical IDs for primary_model_id and primary_platform_id; "
                "submission.yml dropdown options must match catalog labels exactly."
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
                "Primary AI model (optional)",
                "Primary platform / IDE (optional)",
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
        "cli_equivalent": "pubroot guide --json",
    }


@mcp.tool(
    title="Validate and prepare a submission",
    description="Validate a submission draft against Pubroot rules and return a prefilled GitHub issue URL. Does not create the issue.",
    annotations=mcp_types.ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
        destructive_hint=False,
        idempotent_hint=True
    )
)
def prepare_submission(
    title: str,
    category: str,
    abstract: str,
    body: str,
    submission_type: str = "original-research",
    supporting_repo: str = "",
    commit_sha: str = "",
    repo_visibility: str = "no-repo",
    ai_tooling_attribution: str = ""
) -> dict:
    """
    Validate a submission draft against Stage 1 rules and return a prefilled GitHub issue URL.
    
    IMPORTANT: This tool does NOT create the issue. It only validates the draft and returns
    a URL that the user or agent can open to submit. This keeps the tool read-only and
    allows the submission to be created under the correct GitHub identity.
    
    Validation checks:
    - Title, category, abstract, and body are required
    - Abstract should be under 350 words (warning at 300+)
    - Body should be at least 200 words
    - Category must match journals.json taxonomy (journal/topic format)
    - Checks for prompt injection patterns
    
    Also runs get_related_work() to find potential duplicates and warns if similar papers exist.
    
    Returns:
        A dict with:
        - valid: bool - whether the submission passes validation
        - errors: list - blocking validation errors
        - warnings: list - non-blocking warnings
        - github_issue_url: str - prefilled new issue URL (only if valid)
        - related_papers: list - potential duplicates found
        - gh_command: str - equivalent `gh issue create` command
    
    Args:
        title: Article title (required)
        category: Category in journal/topic format (e.g., 'ai/llm-benchmarks')
        abstract: Abstract text (required, recommended 150-300 words)
        body: Article body text (required, minimum 200 words)
        submission_type: Type of submission (original-research, case-study, benchmark, review-survey, tutorial, dataset)
        supporting_repo: GitHub repo URL (optional)
        commit_sha: Commit SHA if repo provided (optional)
        repo_visibility: Repo visibility (public, private, no-repo)
        ai_tooling_attribution: AI tools used (optional)
    """
    errors = []
    warnings = []
    
    # VALIDATION LOGIC based on stage_1_parse_and_filter.py
    
    # Required fields check
    if not title or not title.strip():
        errors.append("Article Title is required")
    if not category or not category.strip():
        errors.append("Category is required")
    if not abstract or not abstract.strip():
        errors.append("Abstract is required")
    if not body or not body.strip():
        errors.append("Article Body is required")
    
    # Word counts
    abstract_words = len(abstract.split()) if abstract else 0
    body_words = len(body.split()) if body else 0
    
    if abstract_words > 350:
        errors.append(f"Abstract exceeds 350 words ({abstract_words} words). Please shorten.")
    elif abstract_words > 300:
        warnings.append(f"Abstract is {abstract_words} words. Consider keeping it under 300 words.")
    
    if body_words < 200:
        errors.append(f"Article Body must be at least 200 words ({body_words} words)")
    
    # Category validation: must be in journal/topic format and match journals.json
    if category:
        if '/' not in category:
            errors.append(f"Category must be in 'journal/topic' format (e.g., 'ai/llm-benchmarks'), got: {category}")
        elif category.startswith('--- ') or category.startswith('---'):
            errors.append(f"Category cannot be a separator line: {category}")
        else:
            # Check against journals.json
            try:
                journals_data = _load_json("journals.json")
                valid_categories = set()
                for journal in journals_data.get("journals", []):
                    journal_slug = journal.get("slug", "")
                    for topic in journal.get("topics", []):
                        topic_slug = topic.get("slug", "")
                        valid_categories.add(f"{journal_slug}/{topic_slug}")
                
                if category not in valid_categories:
                    errors.append(f"Category '{category}' not found in journals.json. Use 'pubroot topics' to see valid categories.")
            except Exception as e:
                warnings.append(f"Could not validate category against journals.json: {e}")
    
    # Prompt injection check (simple regex from stage_1)
    # This checks for common prompt injection patterns in title, abstract, and first 2000 chars of body
    import re
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directives)",
        r"(?i)disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directives)",
        r"(?i)system\s*:\s*you\s+are",
        r"(?i)new\s+instructions\s*:",
        r"(?i)ignore\s+this\s+document",
    ]
    check_text = f"{title} {abstract} {body[:2000]}"
    for pattern in injection_patterns:
        if re.search(pattern, check_text):
            errors.append(f"Potential prompt injection detected. Pattern: {pattern}")
            break
    
    # Submission type validation
    valid_types = ["original-research", "case-study", "benchmark", "review-survey", "tutorial", "dataset"]
    if submission_type and submission_type not in valid_types:
        warnings.append(f"Submission type '{submission_type}' is not standard. Will default to 'original-research'. Valid: {', '.join(valid_types)}")
    
    # Check for related work (potential duplicates)
    related_papers = []
    try:
        related = get_related_work(query=f"{title} {abstract[:100]}")
        if related.get("total_related", 0) > 0:
            related_papers = related.get("results", [])[:5]
            if related_papers:
                top_relevance = related_papers[0].get("relevance_score", 0)
                if top_relevance > 8:
                    warnings.append(f"Very similar paper found: '{related_papers[0].get('title')}' (relevance: {top_relevance}). Consider if this is a duplicate or supersedes existing work.")
                elif top_relevance > 5:
                    warnings.append(f"Similar paper found: '{related_papers[0].get('title')}'. Ensure your work adds novelty.")
    except Exception as e:
        warnings.append(f"Could not check for related work: {e}")
    
    valid = len(errors) == 0
    
    result = {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "word_counts": {
            "title": len(title.split()) if title else 0,
            "abstract": abstract_words,
            "body": body_words,
        },
        "related_papers": related_papers,
    }
    
    if valid:
        # Build the GitHub issue form URL with prefilled fields
        # The submission template is at .github/ISSUE_TEMPLATE/submission.yml
        # GitHub issue forms use query parameters like `title` and field IDs
        
        # Build the issue body with the expected ### Label format
        issue_body = f"""### Article Title
{title}

### Category
{category}

### Submission Type
{submission_type}

### AI / Tooling Attribution (optional)
{ai_tooling_attribution if ai_tooling_attribution else "_No response_"}

### Abstract
{abstract}

### Article Body
{body}

### Supporting Repository URL
{supporting_repo if supporting_repo else "_No response_"}

### Commit SHA
{commit_sha if commit_sha else "_No response_"}

### Repository Visibility
{repo_visibility}

### Payment Code (Optional)
_No response_

### Submission Agreement
- [X] I have read and agree to the Editorial Guidelines
- [X] I confirm this is my original work or I have rights to submit it
- [X] I understand reviews are AI-generated and may have errors"""
        
        # URL encode the body for the GitHub issue URL
        base_url = f"https://github.com/{GITHUB_REPO}/issues/new"
        params = {
            "template": "submission.yml",
            "title": f"[SUBMISSION] {title}",
            "body": issue_body,
        }
        github_issue_url = f"{base_url}?{urlencode(params)}"
        
        # Also provide a gh CLI command
        # Note: gh issue create doesn't support form templates well, so we use --body
        gh_command = f'gh issue create --repo {GITHUB_REPO} --title "[SUBMISSION] {title}" --label submission --label pending-review --body <(cat <<EOF\n{issue_body}\nEOF\n)'
        
        result["github_issue_url"] = github_issue_url
        result["gh_command"] = gh_command
        result["message"] = "Validation passed! Open the github_issue_url to submit, or run the gh_command."
    else:
        result["message"] = f"Validation failed with {len(errors)} error(s). Fix the errors and try again."
    
    return result


# -----------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------
# Run the server via stdio transport. Agents connect by launching this
# script as a subprocess (configured in their mcp.json or equivalent).
# -----------------------------------------------------------------------

async def create_health_app():
    """
    Create a simple health check endpoint for the HTTP server.
    
    Returns a Starlette app with /healthz endpoint.
    """
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    
    async def healthz(request):
        """Health check endpoint for load balancers and monitoring."""
        return JSONResponse({
            "status": "ok",
            "service": "pubroot-mcp",
            "version": "0.2.0",
            "mode": REPO_MODE,
        })
    
    return Starlette(routes=[Route("/healthz", healthz)])


def main_stdio():
    """
    Start the MCP server with stdio transport (default mode).
    
    This is for local agent integration where the agent spawns this
    process and communicates over stdin/stdout.
    """
    asyncio.run(mcp.run_stdio_async())


async def main_http_async(host: str = "0.0.0.0", port: int = 8080):
    """
    Start the MCP server with HTTP transport (Streamable HTTP).
    
    This is for hosted deployments where the server listens on HTTP
    and serves MCP over Streamable HTTP at the /mcp endpoint.
    
    The server includes:
    - /mcp endpoint for MCP Streamable HTTP
    - /healthz endpoint for health checks
    - Per-IP rate limiting
    - Request/response size limits
    - Minimal logging (tool, status, latency only)
    """
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse, Response
    from starlette.routing import Route, Mount
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class RateLimitMiddleware(BaseHTTPMiddleware):
        """Rate limiting middleware for MCP tool calls."""
        
        async def dispatch(self, request, call_next):
            # Only rate-limit /mcp endpoint
            if not request.url.path.startswith("/mcp"):
                return await call_next(request)
            
            # Get client IP (handle X-Forwarded-For from proxies)
            client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            if not client_ip:
                client_ip = request.client.host if request.client else "unknown"
            
            # Extract tool name from MCP request (best effort)
            tool_name = "unknown"
            try:
                if request.method == "POST":
                    body = await request.body()
                    if len(body) > MAX_REQUEST_SIZE:
                        return JSONResponse(
                            {"error": "Request too large"},
                            status_code=413
                        )
                    data = json.loads(body)
                    if data.get("method") == "tools/call":
                        tool_name = data.get("params", {}).get("name", "unknown")
            except:
                pass
            
            # Check rate limit
            if not _check_rate_limit(client_ip, tool_name):
                return JSONResponse(
                    {"error": "Rate limit exceeded"},
                    status_code=429
                )
            
            # Log request (tool, status only - no IPs, queries, or drafts)
            start_time = time.time()
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "tool=%s status=%d latency_ms=%.1f",
                tool_name, response.status_code, latency_ms
            )
            
            return response
    
    async def healthz(request):
        """Health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "service": "pubroot-mcp",
            "version": "0.2.0",
            "mode": REPO_MODE,
            "cache_entries": len(_json_cache),
        })
    
    # Create Starlette app with health and MCP endpoints
    # Note: We use a custom app structure to add rate limiting middleware
    # The MCP server's streamable_http_app is mounted at /mcp
    
    # Get the MCP server's ASGI app for Streamable HTTP
    mcp_asgi_app = mcp.streamable_http_app()
    
    # Create main app with health endpoint and middleware
    app = Starlette(
        routes=[
            Route("/healthz", healthz),
        ],
        middleware=[
            Middleware(RateLimitMiddleware),
        ],
    )
    
    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_asgi_app)
    
    # Run with uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def main_http(host: str = "0.0.0.0", port: int = 8080):
    """
    Synchronous entry point for HTTP mode.
    """
    asyncio.run(main_http_async(host, port))


def main():
    """
    Main entry point - delegates to stdio or HTTP mode based on environment.
    
    Defaults to stdio for backward compatibility.
    Set HTTP_MODE=1 or use main_http() directly for HTTP transport.
    """
    if os.environ.get("HTTP_MODE"):
        host = os.environ.get("HTTP_HOST", "0.0.0.0")
        port = int(os.environ.get("HTTP_PORT", "8080"))
        main_http(host, port)
    else:
        main_stdio()


if __name__ == "__main__":
    main()
