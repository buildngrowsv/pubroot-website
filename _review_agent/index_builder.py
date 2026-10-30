"""
Shared index building functions for agent-index.json and priorroot-index.json.

This module provides the single source of truth for:
1. Paper selection logic (what gets indexed)
2. Index entry building (field order, formatting, normalization)
3. Index file generation (serialization settings)

Used by:
- scripts/regenerate_agent_index_from_papers.py (full rebuild from disk)
- _review_agent/stage_6_post_review_and_decide.py (incremental updates in CI)
- scripts/validate_index_integrity.py (validation)
- scripts/test_index_golden.py (testing)

This ensures byte-identical output across all code paths, preventing index drift
(Bug B22 fix - Oct 2026).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


# Site base URL for building reader_url fields in index entries.
# Override via PUBROOT_SITE_BASE environment variable if needed.
SITE_BASE = "https://pubroot.com"


def _fm_and_body(path: Path) -> tuple[dict | None, str]:
    """
    Extract YAML frontmatter and body from a Hugo markdown file.
    
    This parses the --- delimited frontmatter block at the start of a markdown file.
    If the frontmatter is missing or malformed, returns (None, full_text).
    
    Args:
        path: Path to the markdown file
        
    Returns:
        tuple of (frontmatter_dict, body_text). frontmatter_dict is None if parsing failed.
    """
    text = path.read_text(encoding="utf-8")
    if not text.lstrip().startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None, text
    return fm, parts[2]


def _normalize_date_to_second_precision(date_str: str) -> str:
    """
    Normalize published_date to second precision with Z timezone (RFC3339).
    
    This fixes Root Cause C (field drift): stage 6 wrote dates with microseconds
    and +00:00, while the old generator used front-matter dates. We now normalize
    to Z format at second precision for consistency.
    
    Input: ISO-8601 string (from manifest.json), possibly with microseconds and +00:00 offset.
    Output: YYYY-MM-DDTHH:MM:SSZ
    
    Args:
        date_str: ISO-8601 datetime string
        
    Returns:
        Normalized datetime string in YYYY-MM-DDTHH:MM:SSZ format
    """
    if not date_str:
        return ""
    try:
        # Parse the ISO string (handles both Z and +00:00 formats)
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Convert to UTC and format to second precision with Z
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, AttributeError):
        # If parsing fails, return the original or empty
        return date_str if isinstance(date_str, str) else ""


def _abstract_excerpt(fm: dict) -> str:
    """
    Extract and truncate abstract from front matter to 500 chars, rstripped.
    
    The abstract is shown in search results and index listings, so we limit it
    to 500 chars to keep the index file size manageable.
    
    Args:
        fm: Frontmatter dictionary
        
    Returns:
        Abstract string, rstripped and truncated to 500 chars
    """
    ab = fm.get("abstract")
    if ab is None:
        return ""
    if isinstance(ab, str):
        s = ab
    else:
        s = str(ab)
    # rstrip() per the brief, then truncate to 500 chars
    return s.rstrip()[:500]


def should_include_paper(
    index_md: Path,
    papers_root: Path,
    fm: dict | None,
    manifest: dict | None,
) -> bool:
    r"""
    Determine if a paper should be included in the index files.
    
    DEFINITION OF "PUBLISHED" (single source of truth):
        A paper is published if and only if ALL of these hold:
        1. A file papers/{journal}/{topic}/{slug}/index.md exists on main, exactly three
           directories deep. Use the glob papers/*/*/*/index.md, not **, and skip any path
           segment starting with _ or .
        2. Its front matter has a paper_id matching ^\d{4}-\d{3}$.
        3. draft is not true.
        4. type is not policy. (Policy pages like papers/privacy.md, support.md, and terms.md
           are excluded; they are not index.md bundles, so rule 1 already excludes them.)
        5. status is missing or 'current' (not 'archived'). Papers with status='archived' are
           excluded from indexes but their pages still build.
        6. A sibling manifest.json exists and its paper_id matches.
        
    Prior-art means front-matter category starts with prior-art/.
    review.json is NOT required to be published (when missing, review_path is null).
    GitHub labels are NOT a source of truth.
    
    This function centralizes the paper selection logic so that the regenerator,
    stage 6, the validator, and the golden tests all use the same definition.
    
    Args:
        index_md: Path to the paper's index.md file
        papers_root: Path to the papers/ directory (for relative path checks)
        fm: Parsed front matter from index.md (or None if parsing failed)
        manifest: Parsed manifest.json from the same directory (or None if missing/invalid)
        
    Returns:
        True if the paper should be included in the index, False otherwise
    """
    # Rule 1: Must be exactly three directories deep under papers/
    try:
        rel_from_papers = index_md.relative_to(papers_root)
    except ValueError:
        return False
    
    # Must be papers/{journal}/{topic}/{slug}/index.md (4 parts)
    if len(rel_from_papers.parts) != 4 or rel_from_papers.parts[-1] != "index.md":
        return False
    
    # Skip paths starting with _ or .
    if any(part.startswith(("_", ".")) for part in rel_from_papers.parts):
        return False
    
    # Rule 2: Front matter must have a valid paper_id
    if not fm or not fm.get("paper_id"):
        return False
    
    # Rule 3: draft must not be true
    if fm.get("draft") is True:
        return False
    
    # Rule 4: type must not be "policy"
    if fm.get("type") == "policy":
        return False
    
    # Rule 5: status must be missing or 'current' (not 'archived')
    # This is the archiving feature: papers with status='archived' are excluded
    # from the index but their pages still build.
    status = fm.get("status")
    if status is not None and status != "current":
        return False
    
    # Rule 6: manifest.json must exist and paper_id must match
    if not manifest:
        return False
    
    fm_pid = str(fm["paper_id"]).strip().strip('"').strip("'")
    manifest_pid = str(manifest.get("paper_id", "")).strip().strip('"').strip("'")
    if fm_pid != manifest_pid:
        return False
    
    return True


def build_index_entry_from_data(
    paper_id: str,
    title: str,
    author: str,
    category: str,
    abstract: str,
    published_date: str,
    review_score: float | None,
    badge: str,
    article_path: str,
    reader_url: str,
    review_path: str | None = None,
    supporting_repo: str | None = None,
    ai_tooling_attribution: str | None = None,
) -> dict:
    """
    Build an index entry from in-memory data (used by stage 6).
    
    This is the entry-building function that stage 6 uses when uploading a new paper.
    It takes the same data that's being written to frontmatter and manifest, and builds
    an index entry without needing to read from disk.
    
    Args:
        paper_id: The paper ID (e.g., "2026-042")
        title: Paper title
        author: Author name
        category: Category (e.g., "ai/llm-benchmarks")
        abstract: Abstract text (will be truncated to 500 chars)
        published_date: Publication date in YYYY-MM-DDTHH:MM:SSZ format
        review_score: Review score (0-10)
        badge: Badge type (e.g., "verified_open", "text_only")
        article_path: Path to article file (e.g., "papers/ai/test/paper/index.md")
        reader_url: URL to published article (e.g., "https://pubroot.com/ai/test/paper/")
        review_path: Path to review.json (e.g., "reviews/2026-042/review.json")
        supporting_repo: GitHub repo URL (optional)
        ai_tooling_attribution: AI tooling attribution text (optional)
        
    Returns:
        dict: An index entry with normalized fields in the correct order
    """
    # rstrip() all text fields
    title_str = str(title).rstrip() if title else "Untitled"
    author_str = str(author).rstrip() if author else "unknown"
    category_str = str(category).rstrip() if category else "general/general"
    abstract_str = str(abstract).rstrip()[:500] if abstract else ""
    
    # Build entry in canonical field order
    entry: dict = {
        "id": paper_id,
        "title": title_str,
        "author": author_str,
        "category": category_str,
        "abstract": abstract_str,
        "published_date": published_date,
        "review_score": review_score,
        "badge": badge or "text_only",
        "status": "current",
        "article_path": article_path,
        "review_path": review_path,  # review_path comes BEFORE reader_url
        "reader_url": reader_url,    # reader_url comes AFTER review_path
    }
    
    # Optional fields
    if supporting_repo:
        supporting_repo_str = str(supporting_repo).strip().strip('"').strip("'")
        if supporting_repo_str:
            entry["supporting_repo"] = supporting_repo_str
    
    if ai_tooling_attribution:
        ai_attr_str = str(ai_tooling_attribution).rstrip() if isinstance(ai_tooling_attribution, str) else str(ai_tooling_attribution)
        entry["ai_tooling_attribution"] = ai_attr_str
    
    return entry


def build_index_entry(
    index_md: Path,
    fm: dict,
    manifest: dict,
    repo_root: Path,
    papers_root: Path,
    site_base: str = SITE_BASE,
) -> dict:
    """
    Build a single index entry from front matter and manifest.json.
    
    This function is the single source of truth for index entry structure.
    It's used by both the regenerator (full rebuild) and stage 6 (incremental update).
    
    FIELD ORDER (critical for byte-identity):
        The dict is built in a specific order to match the regenerator's output.
        Python 3.7+ dicts maintain insertion order, and json.dumps preserves it.
        
    FIELD NORMALIZATION:
        - published_date: second-precision Z format (YYYY-MM-DDTHH:MM:SSZ)
        - text fields: rstrip()
        - supporting_repo: strip quotes, omit if null/empty
        - review_path: null if review.json doesn't exist
        
    Args:
        index_md: Path to the paper's index.md file
        fm: Parsed front matter from index.md
        manifest: Parsed manifest.json from the same directory
        repo_root: Path to the repository root (for building article_path)
        papers_root: Path to the papers/ directory (for building reader_url)
        site_base: Base URL for the site (default: https://pubroot.com)
        
    Returns:
        dict: An index entry with normalized fields in the correct order
    """
    # Extract and normalize paper_id
    pid = str(fm["paper_id"]).strip().strip('"').strip("'")
    
    # Build article_path (relative to repo root)
    rel_repo = index_md.relative_to(repo_root)
    article_path = str(rel_repo).replace("\\", "/")
    
    # Build reader_url (relative to papers root)
    url_rel = str(index_md.parent.relative_to(papers_root)).replace("\\", "/")
    reader_url = f"{site_base}/{url_rel}/" if url_rel else f"{site_base}/"
    
    # Get published_date from manifest.json and normalize to second precision Z
    # This is the authoritative source for published_date (not front matter)
    published_date = _normalize_date_to_second_precision(
        manifest.get("published_date", "")
    )
    
    # Get supporting_repo from manifest.json, strip quotes, omit if null/empty
    # This is the authoritative source for supporting_repo (not front matter)
    supporting_repo = manifest.get("supporting_repo")
    if supporting_repo:
        # Strip surrounding quotes (fix for papers with literal quotes in manifest)
        supporting_repo = str(supporting_repo).strip().strip('"').strip("'")
        if not supporting_repo:
            supporting_repo = None
    else:
        supporting_repo = None
    
    # rstrip() all text fields per the brief
    title = fm.get("title")
    if title is None:
        title = ""
    elif not isinstance(title, str):
        title = str(title)
    title = title.rstrip()
    
    author = fm.get("author") or "unknown"
    if not isinstance(author, str):
        author = str(author)
    author = author.rstrip()
    
    category = fm.get("category") or "general/general"
    if not isinstance(category, str):
        category = str(category)
    category = category.rstrip()
    
    # Check if review.json exists
    review_path_candidate = repo_root / "reviews" / pid / "review.json"
    review_path = f"reviews/{pid}/review.json" if review_path_candidate.exists() else None
    
    # Build the entry dict in the correct field order (matches regenerator output)
    # CRITICAL: This order must match the order in which the regenerator builds entries.
    # The old stage 6 had reader_url before review_path, while the regenerator had it after.
    # We now use the regenerator's order as the canonical order.
    entry: dict = {
        "id": pid,
        "title": title or "Untitled",
        "author": author,
        "category": category,
        "abstract": _abstract_excerpt(fm),
        "published_date": published_date,
        "review_score": fm.get("score"),
        "badge": fm.get("badge") or "text_only",
        "status": "current",
        "article_path": article_path,
        "review_path": review_path,  # review_path comes BEFORE reader_url
        "reader_url": reader_url,    # reader_url comes AFTER review_path
    }
    
    # Optional fields (only include if present)
    
    if fm.get("last_revised_date") is not None:
        entry["last_revised_date"] = _normalize_date_to_second_precision(
            str(fm["last_revised_date"])
        )
    
    # supporting_repo: omit the key if null or empty per the brief
    if supporting_repo:
        entry["supporting_repo"] = supporting_repo
    
    ai_attr = fm.get("ai_tooling_attribution")
    if ai_attr:
        # rstrip() this too
        if isinstance(ai_attr, str):
            ai_attr = ai_attr.rstrip()
        entry["ai_tooling_attribution"] = ai_attr
    
    return entry


def _collect_all_published_papers(
    papers_root: Path,
    repo_root: Path,
    site_base: str = SITE_BASE,
) -> list[dict]:
    """
    Collect all published papers from the papers/ directory.
    
    This is the shared scanning logic used by both build_agent_index and build_priorroot_index.
    It ensures both indexes are built from the same set of papers and can use the same
    last_updated timestamp (max published_date across all papers).
    
    Args:
        papers_root: Path to the papers/ directory
        repo_root: Path to the repository root
        site_base: Base URL for the site
        
    Returns:
        list[dict]: All published paper entries
    """
    entries: list[dict] = []
    
    # Iterate through published papers using should_include_paper
    for index_md in sorted(papers_root.glob("*/*/*/index.md")):
        fm, _ = _fm_and_body(index_md)
        
        # Check for sibling manifest.json
        manifest_path = index_md.parent / "manifest.json"
        manifest = None
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"WARNING: Failed to read manifest for {index_md}: {e}")
                continue
        
        # Apply paper selection logic
        if not should_include_paper(index_md, papers_root, fm, manifest):
            continue
        
        # Build the entry
        entry = build_index_entry(index_md, fm, manifest, repo_root, papers_root, site_base)
        entries.append(entry)
    
    # Sort by ID
    entries.sort(key=lambda e: e["id"])
    return entries


def _calculate_last_updated(entries: list[dict]) -> str:
    """
    Calculate last_updated from the newest published_date in a list of entries.
    
    This is used by both build_agent_index and build_priorroot_index to ensure
    they use the same last_updated value (max across ALL papers, not just the
    papers in each specific index).
    
    Args:
        entries: List of paper entries
        
    Returns:
        str: The max published_date in YYYY-MM-DDTHH:MM:SSZ format
    """
    all_dates = [e["published_date"] for e in entries if e.get("published_date")]
    if all_dates:
        # all_dates are already in YYYY-MM-DDTHH:MM:SSZ format, so max() works
        return max(all_dates)
    else:
        # Fallback to now() if there are no papers (shouldn't happen in production)
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_agent_index(
    papers_root: Path,
    repo_root: Path,
    site_base: str = SITE_BASE,
) -> dict:
    """
    Build agent-index.json from all published papers (excluding prior-art).
    
    This is the full index rebuild logic. It scans the papers/ directory and
    builds an index from scratch. Used by the regenerator script.
    
    Args:
        papers_root: Path to the papers/ directory
        repo_root: Path to the repository root
        site_base: Base URL for the site (default: https://pubroot.com)
        
    Returns:
        dict: The complete agent-index.json structure
    """
    # Collect ALL published papers (for consistent last_updated calculation)
    all_entries = _collect_all_published_papers(papers_root, repo_root, site_base)
    
    # Filter to only non-prior-art papers
    entries = [e for e in all_entries if not e["category"].startswith("prior-art/")]
    
    # Calculate last_updated from ALL papers (not just agent-index papers)
    # This ensures both indexes have the same last_updated value
    last_updated = _calculate_last_updated(all_entries)
    
    # Build the final index structure
    return {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": (
            "Machine-readable index of published papers in the Pubroot (excludes prior-art "
            "defensive disclosures, which are in priorroot-index.json). "
            "Updated automatically by the review pipeline when a paper is accepted and published. "
            "Agents consume this file via the MCP server's search_papers tool, or by fetching it "
            "directly from the raw GitHub URL. Each entry includes enough metadata for agents to "
            "decide whether to fetch the full article."
        ),
        "search_endpoint": None,
        "total_papers": len(entries),
        "last_updated": last_updated,
        "papers": entries,
    }


def build_priorroot_index(
    papers_root: Path,
    repo_root: Path,
    site_base: str = SITE_BASE,
) -> dict:
    """
    Build priorroot-index.json from all prior-art papers.
    
    This is the full priorroot index rebuild logic. It scans the papers/ directory
    and builds an index of prior-art/* papers. Used by the regenerator script.
    
    Args:
        papers_root: Path to the papers/ directory
        repo_root: Path to the repository root
        site_base: Base URL for the site (default: https://pubroot.com)
        
    Returns:
        dict: The complete priorroot-index.json structure
    """
    # Collect ALL published papers (for consistent last_updated calculation)
    all_entries = _collect_all_published_papers(papers_root, repo_root, site_base)
    
    # Filter to only prior-art papers
    entries = [e for e in all_entries if e["category"].startswith("prior-art/")]
    
    # Calculate last_updated from ALL papers (not just priorroot papers)
    # This ensures both indexes have the same last_updated value
    last_updated = _calculate_last_updated(all_entries)
    
    # Build the final index structure
    return {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": (
            "Machine-readable index of Priorroot defensive disclosures (prior-art/*). "
            "Separated from the main agent-index.json to keep the general Pubroot index "
            "focused on community submissions while giving Priorroot its own discoverable "
            "endpoint. The /priorroot/ page on pubroot.com consumes this file."
        ),
        "search_endpoint": None,
        "total_papers": len(entries),
        "last_updated": last_updated,
        "papers": entries,
    }


def merge_entry_into_index(index_dict: dict, new_entry: dict) -> dict:
    """
    Merge a new paper entry into an existing index dict.
    
    This is used by stage 6 to upsert a new paper entry into the live index fetched
    from the target branch. If an entry with the same ID already exists, it's replaced.
    
    Args:
        index_dict: The existing index dict (will be modified in place)
        new_entry: The new paper entry to merge
        
    Returns:
        dict: The modified index dict (same object as input)
    """
    # Find and replace existing entry with same ID, or append if new
    paper_id = new_entry["id"]
    papers = index_dict.get("papers", [])
    
    # Replace existing entry or append new
    found = False
    for i, entry in enumerate(papers):
        if entry.get("id") == paper_id:
            papers[i] = new_entry
            found = True
            break
    
    if not found:
        papers.append(new_entry)
    
    index_dict["papers"] = papers
    return index_dict


def apply_selection_and_sort(index_dict: dict, all_entries: list[dict]) -> dict:
    """
    Apply paper selection (filter archived) and sorting to an index dict.
    
    This ensures the index only contains publishable papers (not archived) and they're
    sorted by ID. It also recalculates last_updated from the max published_date.
    
    Args:
        index_dict: The index dict to update (will be modified in place)
        all_entries: All paper entries (for calculating last_updated across both indexes)
        
    Returns:
        dict: The modified index dict (same object as input)
    """
    # Filter out archived papers (status != 'current' and status is not None)
    # Note: This is a simplified check since we're working with already-built entries.
    # The should_include_paper() function is the authoritative check, but entries
    # that made it into the index were already filtered.
    # We keep this for consistency with the shared logic.
    papers = index_dict.get("papers", [])
    filtered_papers = [e for e in papers if e.get("status") == "current"]
    
    # Sort by ID
    filtered_papers.sort(key=lambda e: e["id"])
    
    # Calculate last_updated from max published_date across ALL entries (both indexes)
    all_dates = [e["published_date"] for e in all_entries if e.get("published_date")]
    if all_dates:
        last_updated = max(all_dates)
    else:
        # Fallback to now() if there are no papers
        last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    index_dict["papers"] = filtered_papers
    index_dict["total_papers"] = len(filtered_papers)
    index_dict["last_updated"] = last_updated
    
    return index_dict


def serialize_index(index_data: dict) -> str:
    r"""
    Serialize an index dict to JSON with canonical formatting.
    
    CRITICAL: This is the single source of truth for JSON serialization settings.
    All index files must be serialized with these exact settings to ensure byte-identity.
    
    Settings:
    - indent=2: Pretty-printed with 2-space indentation
    - ensure_ascii=False: Allow Unicode characters (don't escape them as \uXXXX)
    - Trailing newline: Add a final newline at the end of the file
    
    Args:
        index_data: The index dict to serialize
        
    Returns:
        str: JSON string with canonical formatting and trailing newline
    """
    return json.dumps(index_data, indent=2, ensure_ascii=False) + "\n"
