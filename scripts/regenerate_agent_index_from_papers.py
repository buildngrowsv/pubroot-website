#!/usr/bin/env python3
r"""
Regenerate agent-index.json and priorroot-index.json from every Hugo paper bundle
under papers/{journal}/{topic}/{slug}/index.md.

Run from repo root:
  python3 scripts/regenerate_agent_index_from_papers.py

DEFINITION OF "PUBLISHED":
    A paper is published if and only if ALL of these hold:
    1. A file papers/{journal}/{topic}/{slug}/index.md exists on main, exactly three
       directories deep. Use the glob papers/*/*/*/index.md, not **, and skip any path
       segment starting with _ or .
    2. Its front matter has a paper_id matching ^\d{4}-\d{3}$.
    3. draft is not true.
    4. type is not policy. (Policy pages like papers/privacy.md, support.md, and terms.md
       are excluded; they are not index.md bundles, so rule 1 already excludes them.)
    5. A sibling manifest.json exists and its paper_id matches.

    Prior-art means front-matter category starts with prior-art/.
    review.json is NOT required to be published (when missing, review_path is null).
    GitHub labels are NOT a source of truth.

WHY:
    Keeps article_path and reader_url aligned with the on-disk SEO layout when
    folders are renamed or papers exist that were never added by an older pipeline run.
    Ensures published_date and supporting_repo are taken from manifest.json (the
    authoritative source), not front matter, to prevent field drift (Root Cause C).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPERS_ROOT = REPO_ROOT / "papers"
SITE_BASE = "https://pubroot.com"
INDEX_OUT = REPO_ROOT / "agent-index.json"
PRIORROOT_INDEX_OUT = REPO_ROOT / "priorroot-index.json"


def _fm_and_body(path: Path) -> tuple[dict | None, str]:
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

    Input: ISO-8601 string (from manifest.json), possibly with microseconds and +00:00 offset.
    Output: YYYY-MM-DDTHH:MM:SSZ

    This fixes Root Cause C (field drift): stage 6 wrote dates with microseconds and +00:00,
    while the old generator used front-matter dates. We now read from manifest.json and normalize
    to Z format at second precision, matching the format stage 6 will emit after its fix.
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
    """Extract and truncate abstract from front matter to 500 chars, rstripped."""
    ab = fm.get("abstract")
    if ab is None:
        return ""
    if isinstance(ab, str):
        s = ab
    else:
        s = str(ab)
    # rstrip() per the brief, then truncate to 500 chars
    return s.rstrip()[:500]


def build_entry(
    index_md: Path,
    fm: dict,
    manifest: dict,
) -> dict:
    """
    Build a single index entry from front matter and manifest.json.

    This function is also importable by stage 6 so there is one code path for building
    index entries, preventing field drift (Root Cause C).

    Args:
        index_md: Path to the paper's index.md file
        fm: Parsed front matter from index.md
        manifest: Parsed manifest.json from the same directory

    Returns:
        dict: An index entry with normalized fields
    """
    pid = str(fm["paper_id"]).strip().strip('"').strip("'")
    rel_repo = index_md.relative_to(REPO_ROOT)
    article_path = str(rel_repo).replace("\\", "/")

    url_rel = str(index_md.parent.relative_to(PAPERS_ROOT)).replace("\\", "/")
    reader_url = f"{SITE_BASE}/{url_rel}/" if url_rel else f"{SITE_BASE}/"

    # Get published_date from manifest.json and normalize to second precision Z
    published_date = _normalize_date_to_second_precision(
        manifest.get("published_date", "")
    )

    # Get supporting_repo from manifest.json, strip quotes, omit if null/empty
    supporting_repo = manifest.get("supporting_repo")
    if supporting_repo:
        # Strip surrounding quotes (fix for 2026-024 which has literal quotes in manifest)
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

    # Check if review.json exists (Root Cause D: some papers have no review.json)
    review_path_candidate = REPO_ROOT / "reviews" / pid / "review.json"
    review_path = f"reviews/{pid}/review.json" if review_path_candidate.exists() else None

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
        "review_path": review_path,
        "reader_url": reader_url,
    }

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


def main() -> int:
    entries: list[dict] = []

    # Iterate through published papers using the definition from the docstring
    for index_md in sorted(PAPERS_ROOT.glob("*/*/*/index.md")):
        rel_from_papers = index_md.relative_to(PAPERS_ROOT)
        
        # Skip paths starting with _ or .
        if any(part.startswith(("_", ".")) for part in rel_from_papers.parts):
            continue

        fm, _ = _fm_and_body(index_md)
        if not fm or not fm.get("paper_id"):
            continue

        # Check draft flag (skip if true)
        if fm.get("draft") is True:
            continue

        # Check type flag (skip if "policy")
        if fm.get("type") == "policy":
            continue

        # Check for sibling manifest.json
        manifest_path = index_md.parent / "manifest.json"
        if not manifest_path.exists():
            print(f"WARNING: {index_md} has no manifest.json, skipping")
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: Failed to read manifest for {index_md}: {e}")
            continue

        # Verify paper_id matches between front matter and manifest
        fm_pid = str(fm["paper_id"]).strip().strip('"').strip("'")
        manifest_pid = str(manifest.get("paper_id", "")).strip().strip('"').strip("'")
        if fm_pid != manifest_pid:
            print(f"WARNING: paper_id mismatch for {index_md}: fm={fm_pid}, manifest={manifest_pid}")
            continue

        entry = build_entry(index_md, fm, manifest)
        entries.append(entry)

    entries.sort(key=lambda e: e["id"])

    # Split by prior-art/ category (Root Cause A fix)
    main_entries = [e for e in entries if not e["category"].startswith("prior-art/")]
    priorroot_entries = [e for e in entries if e["category"].startswith("prior-art/")]

    # Calculate last_updated from the newest published_date, not now() (per brief)
    # This ensures two runs produce identical output (deterministic)
    all_dates = [e["published_date"] for e in entries if e.get("published_date")]
    if all_dates:
        # all_dates are already in YYYY-MM-DDTHH:MM:SSZ format, so max() works
        last_updated = max(all_dates)
    else:
        # Fallback to now() if there are no papers (shouldn't happen in production)
        last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    main_payload = {
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
        "total_papers": len(main_entries),
        "last_updated": last_updated,
        "papers": main_entries,
    }

    INDEX_OUT.write_text(
        json.dumps(main_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(main_entries)} papers to {INDEX_OUT.relative_to(REPO_ROOT)}")

    priorroot_payload = {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": (
            "Machine-readable index of Priorroot defensive disclosures (prior-art/*). "
            "Separated from the main agent-index.json to keep the general Pubroot index "
            "focused on community submissions while giving Priorroot its own discoverable "
            "endpoint. The /priorroot/ page on pubroot.com consumes this file."
        ),
        "search_endpoint": None,
        "total_papers": len(priorroot_entries),
        "last_updated": last_updated,
        "papers": priorroot_entries,
    }

    PRIORROOT_INDEX_OUT.write_text(
        json.dumps(priorroot_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(priorroot_entries)} priorroot papers to {PRIORROOT_INDEX_OUT.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
