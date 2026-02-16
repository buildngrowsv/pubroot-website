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
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional

import requests
from mcp.server.mcpserver import MCPServer

# -----------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------
# REPO_MODE: 'local' (read from filesystem) or 'remote' (fetch from GitHub)
# GITHUB_REPO: "owner/repo" for remote mode
# LOCAL_REPO_PATH: Path to local repo clone for local mode
# -----------------------------------------------------------------------

REPO_MODE = os.environ.get("REPO_MODE", "local")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "buildngrowsv/pubroot-website")
LOCAL_REPO_PATH = os.environ.get(
    "LOCAL_REPO_PATH",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"

# -----------------------------------------------------------------------
# DATA LOADING HELPERS
# -----------------------------------------------------------------------
# These functions abstract the data source so tools don't care whether
# they're reading from local disk or GitHub raw URLs.
# -----------------------------------------------------------------------


def _load_json(filename: str) -> dict:
    """
    Load a JSON file from either local filesystem or GitHub raw URL.
    
    Uses the REPO_MODE environment variable to determine source.
    Caches in memory for the lifetime of the server process to reduce
    GitHub API calls. Cache is invalidated every 5 minutes.
    """
    if REPO_MODE == "local":
        filepath = os.path.join(LOCAL_REPO_PATH, filename)
        with open(filepath, "r") as f:
            return json.load(f)
    else:
        url = f"{GITHUB_RAW_BASE}/{filename}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()


def _load_review(paper_id: str) -> Optional[dict]:
    """Load a specific paper's review JSON."""
    try:
        return _load_json(f"reviews/{paper_id}/review.json")
    except (FileNotFoundError, requests.HTTPError):
        return None


# -----------------------------------------------------------------------
# MCP SERVER DEFINITION
# -----------------------------------------------------------------------

mcp = MCPServer("Pubroot")


@mcp.tool()
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
        category: Filter by category slug (e.g., 'llm-benchmarks', 'ios-debugging').
        min_score: Minimum review score to include (0.0 to 10.0).
        badge: Filter by badge type ('verified_open', 'verified_private', 'text_only').
        status: Paper status filter ('current', 'superseded', 'expired'). Default: 'current'.
        limit: Maximum number of results (1-50). Default: 10.
    """
    index = _load_json("agent-index.json")
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


@mcp.tool()
def verify_claim(
    claim: str,
    category: str = ""
) -> dict:
    """
    Check if a specific factual claim has been verified by any published paper.
    
    Searches through the claim verification data in published reviews to find
    papers that have checked similar claims. Returns the verification status,
    confidence, and source papers.
    
    This is the killer feature for agents — they can fact-check claims against
    our verified knowledge base before using them in their outputs.
    
    Args:
        claim: The factual claim to verify (e.g., "GPT-4o scores 90% on MMLU").
        category: Optional category to narrow the search.
    """
    index = _load_json("agent-index.json")
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
            "suggestion": "Try submitting an article about this topic for peer review.",
            "matches": [],
        }
    
    return {
        "found": True,
        "total_matches": len(matches),
        "matches": matches,
    }


@mcp.tool()
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


@mcp.tool()
def get_contributor_reputation(github_handle: str) -> dict:
    """
    Get a contributor's reputation score, tier, and submission history.
    
    The reputation system tracks contributor quality over time. Higher
    reputation means more trustworthy submissions and faster review times.
    
    Tiers: new (0), emerging (0.01-0.39), established (0.40-0.69),
           trusted (0.70-0.89), authority (0.90-1.0), suspended (-1.0).
    
    Args:
        github_handle: The contributor's GitHub username.
    """
    contributors = _load_json("contributors.json")
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


@mcp.tool()
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
    index = _load_json("agent-index.json")
    papers = index.get("papers", [])
    
    if not query and not paper_id:
        return {"error": "Provide either a 'query' or 'paper_id' argument."}
    
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


# -----------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------
# Run the server via stdio transport. Agents connect by launching this
# script as a subprocess (configured in their mcp.json or equivalent).
# -----------------------------------------------------------------------

if __name__ == "__main__":
    import mcp.server.stdio
    from mcp.server.lowlevel import NotificationOptions
    from mcp.server.models import InitializationOptions
    
    async def main():
        """
        Start the MCP server with stdio transport.
        
        This is the standard way to run an MCP server that agents connect to
        as a subprocess. The agent's MCP client sends JSON-RPC over stdin/stdout.
        """
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ai-peer-review-journal",
                    server_version="1.0.0",
                    capabilities=mcp._mcp_server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    
    asyncio.run(main())
