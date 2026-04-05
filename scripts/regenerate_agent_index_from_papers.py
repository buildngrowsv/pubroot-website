#!/usr/bin/env python3
"""
Regenerate agent-index.json from every Hugo paper bundle under papers/{journal}/{topic}/{slug}/index.md.

Run from repo root:
  python3 scripts/regenerate_agent_index_from_papers.py

WHY:
    Keeps article_path and reader_url aligned with the on-disk SEO layout when
    folders are renamed or papers exist that were never added by an older pipeline run.
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


def _scalar_to_iso(val) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _abstract_excerpt(fm: dict) -> str:
    ab = fm.get("abstract")
    if ab is None:
        return ""
    if isinstance(ab, str):
        s = ab
    else:
        s = str(ab)
    return s[:500]


def main() -> int:
    entries: list[dict] = []

    for index_md in sorted(PAPERS_ROOT.rglob("index.md")):
        rel_from_papers = index_md.relative_to(PAPERS_ROOT)
        if rel_from_papers.parts and rel_from_papers.parts[0].startswith("_"):
            continue

        fm, _ = _fm_and_body(index_md)
        if not fm or not fm.get("paper_id"):
            continue

        pid = str(fm["paper_id"]).strip().strip('"').strip("'")
        rel_repo = index_md.relative_to(REPO_ROOT)
        article_path = str(rel_repo).replace("\\", "/")

        url_rel = str(index_md.parent.relative_to(PAPERS_ROOT)).replace("\\", "/")
        reader_url = f"{SITE_BASE}/{url_rel}/" if url_rel else f"{SITE_BASE}/"

        title = fm.get("title")
        if title is None:
            title = ""
        elif not isinstance(title, str):
            title = str(title)
        title = title.strip()

        entry: dict = {
            "id": pid,
            "title": title or "Untitled",
            "author": fm.get("author") or "unknown",
            "category": fm.get("category") or "general/general",
            "abstract": _abstract_excerpt(fm),
            "published_date": _scalar_to_iso(
                fm.get("original_submitted_date") or fm.get("date")
            ),
            "review_score": fm.get("score"),
            "badge": fm.get("badge") or "text_only",
            "status": "current",
            "article_path": article_path,
            "review_path": f"reviews/{pid}/review.json",
            "reader_url": reader_url,
        }

        if fm.get("last_revised_date") is not None:
            entry["last_revised_date"] = _scalar_to_iso(fm["last_revised_date"])

        sr = fm.get("supporting_repo")
        if sr is not None and sr != "":
            entry["supporting_repo"] = sr

        if fm.get("ai_tooling_attribution"):
            entry["ai_tooling_attribution"] = fm["ai_tooling_attribution"]

        entries.append(entry)

    entries.sort(key=lambda e: e["id"])

    payload = {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": (
            "Machine-readable index of all published papers in the Pubroot. "
            "Updated automatically by the review pipeline when a paper is accepted and published. "
            "Agents consume this file via the MCP server's search_papers tool, or by fetching it "
            "directly from the raw GitHub URL. Each entry includes enough metadata for agents to "
            "decide whether to fetch the full article."
        ),
        "search_endpoint": None,
        "total_papers": len(entries),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "papers": entries,
    }

    INDEX_OUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(entries)} papers to {INDEX_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
