#!/usr/bin/env python3
"""
Validate that agent-index.json and priorroot-index.json match the published papers on disk.

This script checks for index drift by comparing:
1. Papers on disk (papers/**/index.md with paper_id in frontmatter)
2. Papers in agent-index.json
3. Papers in priorroot-index.json
4. Review files (reviews/*/review.json)

Exit codes:
    0 - All indexes match papers on disk, no drift detected
    1 - Index drift detected (missing papers, extra entries, or dangling review.json links)

Usage:
    python3 scripts/validate_index_integrity.py

This can be added to CI to catch index drift early, or run manually to audit the indexes.
Added as part of the Bug B3 fix (index lost-update race condition) on 2026-10-24.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def _fm_and_body(path: Path) -> tuple[dict | None, str]:
    """Extract YAML frontmatter and body from a Hugo markdown file."""
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


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    papers_root = repo_root / "papers"
    reviews_root = repo_root / "reviews"
    
    # Collect all paper IDs from disk
    disk_papers: dict[str, Path] = {}
    for index_md in sorted(papers_root.rglob("index.md")):
        rel_from_papers = index_md.relative_to(papers_root)
        if rel_from_papers.parts and rel_from_papers.parts[0].startswith("_"):
            continue
        
        fm, _ = _fm_and_body(index_md)
        if not fm or not fm.get("paper_id"):
            continue
        
        pid = str(fm["paper_id"]).strip().strip('"').strip("'")
        disk_papers[pid] = index_md
    
    # Collect review IDs from disk
    disk_reviews: set[str] = set()
    for review_json in sorted(reviews_root.rglob("review.json")):
        rel_from_reviews = review_json.relative_to(reviews_root)
        if len(rel_from_reviews.parts) >= 2:
            paper_id = rel_from_reviews.parts[0]
            disk_reviews.add(paper_id)
    
    # Load agent-index.json
    agent_index_path = repo_root / "agent-index.json"
    agent_index_data = json.loads(agent_index_path.read_text(encoding="utf-8"))
    agent_index_papers = {p["id"]: p for p in agent_index_data.get("papers", [])}
    
    # Load priorroot-index.json
    priorroot_index_path = repo_root / "priorroot-index.json"
    priorroot_index_data = json.loads(priorroot_index_path.read_text(encoding="utf-8"))
    priorroot_index_papers = {p["id"]: p for p in priorroot_index_data.get("papers", [])}
    
    # Combine both indexes for validation
    all_index_papers = {**agent_index_papers, **priorroot_index_papers}
    
    # Separate disk papers by category
    disk_priorart_papers = {pid: path for pid, path in disk_papers.items() 
                            if "prior-art" in str(path)}
    disk_main_papers = {pid: path for pid, path in disk_papers.items() 
                        if "prior-art" not in str(path)}
    
    # Validation checks
    errors = []
    warnings = []
    
    # Check 1: Papers on disk but missing from indexes
    missing_from_agent_index = set(disk_main_papers.keys()) - set(agent_index_papers.keys())
    if missing_from_agent_index:
        errors.append(f"Papers on disk missing from agent-index.json: {sorted(missing_from_agent_index)}")
    
    missing_from_priorroot_index = set(disk_priorart_papers.keys()) - set(priorroot_index_papers.keys())
    if missing_from_priorroot_index:
        errors.append(f"Prior-art papers on disk missing from priorroot-index.json: {sorted(missing_from_priorroot_index)}")
    
    # Check 2: Papers in indexes but not on disk (orphaned entries)
    extra_in_agent_index = set(agent_index_papers.keys()) - set(disk_papers.keys())
    if extra_in_agent_index:
        errors.append(f"Papers in agent-index.json but not on disk: {sorted(extra_in_agent_index)}")
    
    extra_in_priorroot_index = set(priorroot_index_papers.keys()) - set(disk_papers.keys())
    if extra_in_priorroot_index:
        errors.append(f"Papers in priorroot-index.json but not on disk: {sorted(extra_in_priorroot_index)}")
    
    # Check 3: Index entries pointing to non-existent review.json
    dangling_review_links = []
    for pid, entry in all_index_papers.items():
        review_path = entry.get("review_path")
        if review_path:
            # Extract paper ID from review path (e.g., "reviews/2026-123/review.json" -> "2026-123")
            review_pid = review_path.replace("reviews/", "").replace("/review.json", "")
            if review_pid not in disk_reviews:
                dangling_review_links.append(pid)
    
    if dangling_review_links:
        errors.append(f"Index entries with missing review.json files: {sorted(dangling_review_links)}")
    
    # Check 4: Review files without corresponding papers (orphaned reviews)
    orphaned_reviews = disk_reviews - set(disk_papers.keys())
    if orphaned_reviews:
        warnings.append(f"Review files without corresponding papers: {sorted(orphaned_reviews)}")
    
    # Check 5: Verify index counts match disk
    total_disk = len(disk_papers)
    total_agent_index = len(agent_index_papers)
    total_priorroot_index = len(priorroot_index_papers)
    total_indexes = total_agent_index + total_priorroot_index
    
    print(f"Papers on disk: {total_disk}")
    print(f"Papers in agent-index.json: {total_agent_index}")
    print(f"Papers in priorroot-index.json: {total_priorroot_index}")
    print(f"Total in indexes: {total_indexes}")
    print(f"Reviews on disk: {len(disk_reviews)}")
    print()
    
    if total_disk != total_indexes:
        errors.append(f"Index count mismatch: {total_disk} papers on disk != {total_indexes} in indexes")
    
    # Report results
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
        print()
    
    if errors:
        print("ERRORS - Index drift detected:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("Run: python3 scripts/regenerate_agent_index_from_papers.py")
        print("Then commit the updated indexes to fix the drift.")
        return 1
    
    if warnings:
        print("Index validation passed with warnings.")
        return 0
    
    print("Index validation passed: all papers on disk are in indexes, no dangling links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
