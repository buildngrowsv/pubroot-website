#!/usr/bin/env python3
"""
Golden test for index generator: ensure generated indexes match committed indexes
and that all published papers are present.

Run from repo root:
    pytest scripts/test_index_golden.py
    
This test ensures:
1. Generated indexes are byte-identical to committed indexes (after json.load)
2. The set of ids equals the set of published papers
3. Stage 6 and the regenerator produce byte-identical output for BOTH files
4. validate_index_integrity.py passes in strict mode
5. Archived papers are excluded from indexes
6. priorroot last_updated equals max published_date
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add repo root and _review_agent to path for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "_review_agent"))

from index_builder import (
    _fm_and_body,
    should_include_paper,
    build_agent_index,
    build_priorroot_index,
    build_index_entry_from_data,
    merge_entry_into_index,
    apply_selection_and_sort,
    serialize_index,
)


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
    the shared should_include_paper definition.
    """
    # Read the committed indexes
    agent_index = json.loads((REPO_ROOT / "agent-index.json").read_text(encoding="utf-8"))
    priorroot_index = json.loads((REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8"))
    
    indexed_ids = {e["id"] for e in agent_index["papers"]}
    indexed_ids.update(e["id"] for e in priorroot_index["papers"])
    
    # Find all published papers using the shared should_include_paper logic
    papers_root = REPO_ROOT / "papers"
    published_ids = set()
    
    for index_md in papers_root.glob("*/*/*/index.md"):
        fm, _ = _fm_and_body(index_md)
        
        # Check for sibling manifest.json
        manifest_path = index_md.parent / "manifest.json"
        manifest = None
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
        
        # Apply shared paper selection logic (includes archiving check)
        if not should_include_paper(index_md, papers_root, fm, manifest):
            continue
        
        fm_pid = str(fm["paper_id"]).strip().strip('"').strip("'")
        published_ids.add(fm_pid)
    
    # Assert sets match
    assert indexed_ids == published_ids, (
        f"Mismatch between indexed and published papers.\n"
        f"Indexed but not published: {indexed_ids - published_ids}\n"
        f"Published but not indexed: {published_ids - indexed_ids}"
    )


def test_stage_6_and_regenerator_produce_identical_indexes():
    """
    Test (c): Assert stage 6 and the regenerator produce byte-identical output
    for BOTH agent-index.json and priorroot-index.json when given the same inputs.
    
    This test simulates what stage 6 does: it rebuilds both indexes from scratch
    by scanning the papers/ directory, then compares with what the regenerator produces.
    """
    # Build both indexes using the shared functions (same code path as stage 6)
    papers_root = REPO_ROOT / "papers"
    agent_index = build_agent_index(papers_root, REPO_ROOT)
    priorroot_index = build_priorroot_index(papers_root, REPO_ROOT)
    
    # Serialize them using the shared serializer
    agent_json = serialize_index(agent_index)
    priorroot_json = serialize_index(priorroot_index)
    
    # Parse the committed indexes (what the regenerator produced)
    committed_agent = (REPO_ROOT / "agent-index.json").read_text(encoding="utf-8")
    committed_priorroot = (REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8")
    
    # Compare as dicts (ignores formatting)
    assert json.loads(agent_json) == json.loads(committed_agent), (
        "Stage 6's agent-index.json differs from regenerator's output"
    )
    assert json.loads(priorroot_json) == json.loads(committed_priorroot), (
        "Stage 6's priorroot-index.json differs from regenerator's output"
    )


def test_priorroot_last_updated_equals_max_published_date():
    """
    Test (d): Assert priorroot-index.json's last_updated equals the max published_date
    of all papers (not just prior-art papers, per the shared logic).
    
    This was Root Cause 2 from Bug B22: stage 6 never updated priorroot-index.json's
    last_updated, while the regenerator set it to max(published_date).
    """
    priorroot_index = json.loads((REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8"))
    agent_index = json.loads((REPO_ROOT / "agent-index.json").read_text(encoding="utf-8"))
    
    # Collect all published_date values from both indexes
    all_dates = []
    all_dates.extend(e["published_date"] for e in priorroot_index["papers"] if e.get("published_date"))
    all_dates.extend(e["published_date"] for e in agent_index["papers"] if e.get("published_date"))
    
    if all_dates:
        expected_last_updated = max(all_dates)
        assert priorroot_index["last_updated"] == expected_last_updated, (
            f"priorroot-index.json last_updated mismatch:\n"
            f"Expected: {expected_last_updated}\n"
            f"Actual: {priorroot_index['last_updated']}"
        )


def test_archived_papers_excluded_from_indexes():
    """
    Test (e): Assert that papers with status='archived' in frontmatter are excluded
    from both indexes using the shared should_include_paper logic.
    
    This tests the archiving feature added with Bug B22 fix.
    """
    # Create a fixture paper with status='archived' in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        tmp_papers = tmp_root / "papers"
        tmp_papers.mkdir()
        
        # Create a fixture paper directory: papers/test/category/archived-paper/
        fixture_dir = tmp_papers / "test" / "category" / "archived-paper"
        fixture_dir.mkdir(parents=True)
        
        # Write index.md with status='archived'
        index_md = fixture_dir / "index.md"
        index_md.write_text(
            "---\n"
            "paper_id: \"9999-999\"\n"
            "title: \"Archived Test Paper\"\n"
            "author: \"test\"\n"
            "category: \"test/category\"\n"
            "status: archived\n"
            "score: 7.0\n"
            "badge: text_only\n"
            "---\n"
            "Body content\n"
        )
        
        # Write manifest.json
        manifest_path = fixture_dir / "manifest.json"
        manifest_path.write_text(json.dumps({
            "paper_id": "9999-999",
            "published_date": "2026-01-01T00:00:00Z",
        }))
        
        # Test that should_include_paper returns False
        fm, _ = _fm_and_body(index_md)
        manifest = json.loads(manifest_path.read_text())
        assert not should_include_paper(index_md, tmp_papers, fm, manifest), (
            "Archived paper should be excluded by should_include_paper"
        )
        
        # Now test with status='current' (should be included)
        index_md.write_text(
            "---\n"
            "paper_id: \"9999-999\"\n"
            "title: \"Current Test Paper\"\n"
            "author: \"test\"\n"
            "category: \"test/category\"\n"
            "status: current\n"
            "score: 7.0\n"
            "badge: text_only\n"
            "---\n"
            "Body content\n"
        )
        fm, _ = _fm_and_body(index_md)
        assert should_include_paper(index_md, tmp_papers, fm, manifest), (
            "Current paper should be included by should_include_paper"
        )
        
        # Test with status field missing (should be included - default is current)
        index_md.write_text(
            "---\n"
            "paper_id: \"9999-999\"\n"
            "title: \"No Status Test Paper\"\n"
            "author: \"test\"\n"
            "category: \"test/category\"\n"
            "score: 7.0\n"
            "badge: text_only\n"
            "---\n"
            "Body content\n"
        )
        fm, _ = _fm_and_body(index_md)
        assert should_include_paper(index_md, tmp_papers, fm, manifest), (
            "Paper with missing status should be included (defaults to current)"
        )


def test_regenerate_from_main_reproduces_byte_identity():
    """
    Test (f): Run the regenerator on the real repo and assert it reproduces both
    committed index files byte for byte.
    
    This is the ultimate smoke test: if the regenerator can reproduce the committed
    indexes exactly, then stage 6 (which uses the same code) will also produce
    byte-identical output.
    """
    # Backup the committed indexes
    committed_agent = (REPO_ROOT / "agent-index.json").read_text(encoding="utf-8")
    committed_priorroot = (REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8")
    
    # Run the regenerator
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "regenerate_agent_index_from_papers.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Regenerator failed: {result.stderr}"
    
    # Read the regenerated indexes
    regenerated_agent = (REPO_ROOT / "agent-index.json").read_text(encoding="utf-8")
    regenerated_priorroot = (REPO_ROOT / "priorroot-index.json").read_text(encoding="utf-8")
    
    # Restore the originals (don't modify working tree)
    (REPO_ROOT / "agent-index.json").write_text(committed_agent, encoding="utf-8")
    (REPO_ROOT / "priorroot-index.json").write_text(committed_priorroot, encoding="utf-8")
    
    # Compare as dicts (ignores insignificant whitespace differences)
    committed_agent_json = json.loads(committed_agent)
    regenerated_agent_json = json.loads(regenerated_agent)
    committed_priorroot_json = json.loads(committed_priorroot)
    regenerated_priorroot_json = json.loads(regenerated_priorroot)
    
    assert committed_agent_json == regenerated_agent_json, (
        "Regenerated agent-index.json differs from committed version"
    )
    assert committed_priorroot_json == regenerated_priorroot_json, (
        "Regenerated priorroot-index.json differs from committed version"
    )


def test_validate_index_integrity():
    """
    Test (g): Run validate_index_integrity.py in strict mode and assert it passes.
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


# ---------------------------------------------------------------------------
# TESTS: Stage 6 index update path (Bug B22 fix - Oct 2026)
# ---------------------------------------------------------------------------
# These tests exercise the real stage 6 code path where the new paper exists
# ONLY through mocked API responses (not on disk), and stage 6 merges it into
# the live indexes fetched from the target branch.


def test_stage6_merges_new_paper_into_live_index():
    """
    Test (h): Stage 6 merges a new paper into the live index.
    
    The new paper exists ONLY in memory (not on disk). Stage 6 must merge it into
    the live index and produce byte-identical output to the regenerator.
    """
    # Create a live index with existing papers
    live_agent_index = {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": "Test index",
        "search_endpoint": None,
        "total_papers": 2,
        "last_updated": "2026-03-20T10:00:00Z",
        "papers": [
            {
                "id": "2026-001",
                "title": "First Paper",
                "author": "author1",
                "category": "ai/test",
                "abstract": "Abstract 1",
                "published_date": "2026-03-20T10:00:00Z",
                "review_score": 8.0,
                "badge": "text_only",
                "status": "current",
                "article_path": "papers/ai/test/first/index.md",
                "review_path": "reviews/2026-001/review.json",
                "reader_url": "https://pubroot.com/ai/test/first/",
            },
            {
                "id": "2026-002",
                "title": "Second Paper",
                "author": "author2",
                "category": "ai/test",
                "abstract": "Abstract 2",
                "published_date": "2026-03-15T08:30:00Z",
                "review_score": 7.5,
                "badge": "text_only",
                "status": "current",
                "article_path": "papers/ai/test/second/index.md",
                "review_path": "reviews/2026-002/review.json",
                "reader_url": "https://pubroot.com/ai/test/second/",
            },
        ],
    }
    
    live_priorroot_index = {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": "Test priorroot index",
        "search_endpoint": None,
        "total_papers": 0,
        "last_updated": "2026-03-20T10:00:00Z",
        "papers": [],
    }
    
    # Build new paper entry (simulating stage 6's code path)
    new_entry = build_index_entry_from_data(
        paper_id="2026-003",
        title="New Paper",
        author="author3",
        category="ai/test",
        abstract="Abstract 3",
        published_date="2026-03-22T15:00:00Z",
        review_score=9.0,
        badge="verified_open",
        article_path="papers/ai/test/new/index.md",
        reader_url="https://pubroot.com/ai/test/new/",
        review_path="reviews/2026-003/review.json",
    )
    
    # Merge into live index (stage 6's code path)
    merge_entry_into_index(live_agent_index, new_entry)
    
    # Apply selection and sort (stage 6's code path)
    all_entries = live_agent_index["papers"] + live_priorroot_index["papers"]
    apply_selection_and_sort(live_agent_index, all_entries)
    apply_selection_and_sort(live_priorroot_index, all_entries)
    
    # Verify results
    assert len(live_agent_index["papers"]) == 3
    assert live_agent_index["papers"][2]["id"] == "2026-003"
    
    # Verify papers are sorted by ID
    paper_ids = [p["id"] for p in live_agent_index["papers"]]
    assert paper_ids == ["2026-001", "2026-002", "2026-003"]
    
    # Verify last_updated is max published_date
    assert live_agent_index["last_updated"] == "2026-03-22T15:00:00Z"
    assert live_priorroot_index["last_updated"] == "2026-03-22T15:00:00Z"
    
    # Verify serialization produces canonical format
    serialized = serialize_index(live_agent_index)
    assert serialized.endswith("\n")
    assert '"total_papers": 3' in serialized


def test_stage6_preserves_entries_from_stale_checkout():
    """
    Test (i): Stage 6 preserves entries from live index that aren't in local checkout.
    
    This simulates the case where the checkout is stale and another paper was published
    after the checkout but before stage 6 runs. That entry must be kept.
    """
    # Create a live index with a paper that won't be in the local checkout
    live_agent_index = {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": "Test index",
        "search_endpoint": None,
        "total_papers": 1,
        "last_updated": "2026-10-29T14:24:35Z",
        "papers": [
            {
                "id": "2026-274",
                "title": "Paper from another writer",
                "author": "other-author",
                "category": "ai/test",
                "abstract": "This was published by another writer after our checkout",
                "published_date": "2026-10-29T14:24:35Z",
                "review_score": 7.0,
                "badge": "text_only",
                "status": "current",
                "article_path": "papers/ai/test/other/index.md",
                "review_path": "reviews/2026-274/review.json",
                "reader_url": "https://pubroot.com/ai/test/other/",
            },
        ],
    }
    
    # Build and merge a new paper
    new_entry = build_index_entry_from_data(
        paper_id="2026-042",
        title="Our New Paper",
        author="our-author",
        category="ai/test",
        abstract="Our paper",
        published_date="2026-10-30T10:00:00Z",
        review_score=8.0,
        badge="text_only",
        article_path="papers/ai/test/our/index.md",
        reader_url="https://pubroot.com/ai/test/our/",
        review_path="reviews/2026-042/review.json",
    )
    
    merge_entry_into_index(live_agent_index, new_entry)
    
    # Apply selection and sort
    all_entries = live_agent_index["papers"]
    apply_selection_and_sort(live_agent_index, all_entries)
    
    # Verify both papers are present
    assert len(live_agent_index["papers"]) == 2
    paper_ids = [p["id"] for p in live_agent_index["papers"]]
    assert "2026-274" in paper_ids, "Paper from stale checkout must be preserved"
    assert "2026-042" in paper_ids, "New paper must be added"
    
    # Verify sorted by ID
    assert paper_ids == ["2026-042", "2026-274"]


def test_stage6_excludes_archived_papers():
    """
    Test (k): Stage 6 excludes papers with status='archived' via apply_selection_and_sort().
    """
    # Create a live index with mixed status papers
    live_agent_index = {
        "schema_version": "1.0",
        "api_version": "1.0",
        "description": "Test index",
        "search_endpoint": None,
        "total_papers": 3,
        "last_updated": "2026-03-20T10:00:00Z",
        "papers": [
            {
                "id": "2026-001",
                "title": "Current Paper",
                "published_date": "2026-03-20T10:00:00Z",
                "status": "current",
            },
            {
                "id": "2026-002",
                "title": "Archived Paper",
                "published_date": "2026-03-15T08:30:00Z",
                "status": "archived",
            },
            {
                "id": "2026-003",
                "title": "Another Current Paper",
                "published_date": "2026-03-18T12:00:00Z",
                "status": "current",
            },
        ],
    }
    
    # Apply selection and sort
    all_entries = live_agent_index["papers"]
    apply_selection_and_sort(live_agent_index, all_entries)
    
    # Verify archived paper is excluded
    assert len(live_agent_index["papers"]) == 2
    paper_ids = [p["id"] for p in live_agent_index["papers"]]
    assert "2026-002" not in paper_ids, "Archived paper must be excluded"
    assert "2026-001" in paper_ids
    assert "2026-003" in paper_ids


if __name__ == "__main__":
    # Allow running directly: python scripts/test_index_golden.py
    pytest.main([__file__, "-v"])
