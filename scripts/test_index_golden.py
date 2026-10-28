#!/usr/bin/env python3
"""
Golden test for index generator: ensure generated indexes match committed indexes
and that all published papers are present.

Run from repo root:
    pytest scripts/test_index_golden.py
    
This test ensures:
1. Generated indexes are byte-identical to committed indexes (after json.load)
2. The set of ids equals the set of published papers
3. Stage 6's _build_index_entry produces the same output as the generator's build_entry
4. validate_index_integrity.py passes in strict mode
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

# Add repo root and _review_agent to path for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "_review_agent"))

from scripts.regenerate_agent_index_from_papers import build_entry, main as regenerate_main
from stage_6_post_review_and_decide import _build_index_entry


def _fm_and_body(path: Path) -> tuple[dict | None, str]:
    """Parse front matter from a markdown file."""
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


def test_generated_indexes_match_committed():
    """
    Test (a): Build the indexes from the working tree and assert they are
    byte-identical to the committed agent-index.json and priorroot-index.json.
    """
    # Backup the committed indexes
    committed_agent = (REPO_ROOT / "agent-index.json").read_text(encoding="utf-8")
    committed_priorroot = (REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8")
    
    # Run the generator
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "regenerate_agent_index_from_papers.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Generator failed: {result.stderr}"
    
    # Read the generated indexes
    generated_agent = (REPO_ROOT / "agent-index.json").read_text(encoding="utf-8")
    generated_priorroot = (REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8")
    
    # Parse as JSON and compare (this ignores formatting differences)
    committed_agent_json = json.loads(committed_agent)
    generated_agent_json = json.loads(generated_agent)
    committed_priorroot_json = json.loads(committed_priorroot)
    generated_priorroot_json = json.loads(generated_priorroot)
    
    # Compare (deep equality)
    assert committed_agent_json == generated_agent_json, (
        "Generated agent-index.json differs from committed version. "
        "Run regenerate_agent_index_from_papers.py and commit the changes."
    )
    assert committed_priorroot_json == generated_priorroot_json, (
        "Generated priorroot-index.json differs from committed version. "
        "Run regenerate_agent_index_from_papers.py and commit the changes."
    )


def test_all_published_papers_are_indexed():
    """
    Test (b): Assert the set of ids equals the set of published papers under
    the definition from the generator docstring.
    """
    # Read the committed indexes
    agent_index = json.loads((REPO_ROOT / "agent-index.json").read_text(encoding="utf-8"))
    priorroot_index = json.loads((REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8"))
    
    indexed_ids = {e["id"] for e in agent_index["papers"]}
    indexed_ids.update(e["id"] for e in priorroot_index["papers"])
    
    # Find all published papers using the same definition as the generator
    papers_root = REPO_ROOT / "papers"
    published_ids = set()
    
    for index_md in papers_root.glob("*/*/*/index.md"):
        rel_from_papers = index_md.relative_to(papers_root)
        
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
            continue
        
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        
        # Verify paper_id matches between front matter and manifest
        fm_pid = str(fm["paper_id"]).strip().strip('"').strip("'")
        manifest_pid = str(manifest.get("paper_id", "")).strip().strip('"').strip("'")
        if fm_pid != manifest_pid:
            continue
        
        published_ids.add(fm_pid)
    
    # Assert sets match
    assert indexed_ids == published_ids, (
        f"Mismatch between indexed and published papers.\n"
        f"Indexed but not published: {indexed_ids - published_ids}\n"
        f"Published but not indexed: {published_ids - indexed_ids}"
    )


def test_stage_6_matches_generator():
    """
    Test (c): Assert stage 6's _build_index_entry gives the same dict as the
    generator's build_entry for one fixture paper.
    """
    # Pick a fixture paper (use 2026-071 as a representative example)
    fixture_path = REPO_ROOT / "papers/ai/agent-architecture/shipping-43-ai-tools-in-one-week-lessons-from-coordinating-an-autonomous-agent-swarm/index.md"
    
    if not fixture_path.exists():
        pytest.skip("Fixture paper 2026-071 not found")
    
    # Read front matter and manifest
    fm, _ = _fm_and_body(fixture_path)
    assert fm is not None
    
    manifest_path = fixture_path.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    # Build entry using generator
    generator_entry = build_entry(fixture_path, fm, manifest)
    
    # Build entry using stage 6 (mock the review and repo_data)
    paper_id = "2026-071"
    now = datetime.now(timezone.utc)
    review = {"score": 7.5}
    repo_data = {"badge_type": "text_only"}
    parsed = {
        "title": fm.get("title"),
        "author": fm.get("author"),
        "category": fm.get("category"),
        "abstract": fm.get("abstract"),
        "supporting_repo": manifest.get("supporting_repo"),
        "ai_tooling_attribution": fm.get("ai_tooling_attribution"),
    }
    article_index_path = str(fixture_path.relative_to(REPO_ROOT)).replace("\\", "/")
    reader_url = "https://pubroot.com/ai/agent-architecture/shipping-43-ai-tools-in-one-week-lessons-from-coordinating-an-autonomous-agent-swarm/"
    
    stage_6_entry = _build_index_entry(
        parsed, review, repo_data, paper_id, now, article_index_path, reader_url
    )
    
    # Compare fields (ignore published_date since stage 6 uses now() while generator uses manifest)
    # and review_score since we're using a mock
    for key in ["id", "title", "author", "category", "abstract", "badge", "status", "article_path", "reader_url", "review_path"]:
        assert generator_entry.get(key) == stage_6_entry.get(key), (
            f"Field {key} differs between generator and stage 6:\n"
            f"Generator: {generator_entry.get(key)}\n"
            f"Stage 6: {stage_6_entry.get(key)}"
        )
    
    # Check supporting_repo handling (both should omit or include consistently)
    gen_has_repo = "supporting_repo" in generator_entry
    s6_has_repo = "supporting_repo" in stage_6_entry
    if gen_has_repo or s6_has_repo:
        # If either has it, both should have it with the same value (or both null)
        assert generator_entry.get("supporting_repo") == stage_6_entry.get("supporting_repo"), (
            f"supporting_repo differs:\n"
            f"Generator: {generator_entry.get('supporting_repo')}\n"
            f"Stage 6: {stage_6_entry.get('supporting_repo')}"
        )


def test_validate_index_integrity():
    """
    Test (d): Run validate_index_integrity.py in strict mode and assert it passes.
    """
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_index_integrity.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"validate_index_integrity.py failed:\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


if __name__ == "__main__":
    # Allow running directly: python scripts/test_index_golden.py
    pytest.main([__file__, "-v"])
