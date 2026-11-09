#!/usr/bin/env python3
r"""
Regenerate agent-index.json and priorroot-index.json from every Hugo paper bundle
under papers/{journal}/{topic}/{slug}/index.md.

Run from repo root:
  python3 scripts/regenerate_agent_index_from_papers.py

DEFINITION OF "PUBLISHED":
    See index_builder.should_include_paper() for the canonical definition.
    This script now delegates to the shared index_builder module to ensure
    byte-identical output with stage 6 (Bug B22 fix - Oct 2026).

WHY:
    Keeps article_path and reader_url aligned with the on-disk SEO layout when
    folders are renamed or papers exist that were never added by an older pipeline run.
    Ensures published_date and supporting_repo are taken from manifest.json (the
    authoritative source), not front matter, to prevent field drift (Root Cause C).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add _review_agent to sys.path for index_builder import
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "_review_agent"))

from index_builder import (
    build_agent_index,
    build_priorroot_index,
    serialize_index,
)

PAPERS_ROOT = REPO_ROOT / "papers"
INDEX_OUT = REPO_ROOT / "agent-index.json"
PRIORROOT_INDEX_OUT = REPO_ROOT / "priorroot-index.json"


def main() -> int:
    """
    Regenerate both index files from scratch by calling the shared index builder.
    
    This ensures byte-identical output with stage 6 by using the same code path.
    """
    # Build agent-index.json (excludes prior-art)
    agent_index = build_agent_index(PAPERS_ROOT, REPO_ROOT)
    INDEX_OUT.write_text(serialize_index(agent_index), encoding="utf-8")
    print(f"Wrote {agent_index['total_papers']} papers to {INDEX_OUT.relative_to(REPO_ROOT)}")
    
    # Build priorroot-index.json (only prior-art)
    priorroot_index = build_priorroot_index(PAPERS_ROOT, REPO_ROOT)
    PRIORROOT_INDEX_OUT.write_text(serialize_index(priorroot_index), encoding="utf-8")
    print(f"Wrote {priorroot_index['total_papers']} priorroot papers to {PRIORROOT_INDEX_OUT.relative_to(REPO_ROOT)}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
