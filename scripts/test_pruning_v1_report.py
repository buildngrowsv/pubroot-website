"""
Tests for pruning_v1_report.py

This test suite validates the pruning report logic without requiring
the full corpus or external dependencies.

Test strategy:
- Create minimal paper fixtures with known issues
- Verify each detection function catches the right cases
- Check report structure and formatting
- Test both with and without embeddings available

Run from repo root:
  python3 -m pytest scripts/test_pruning_v1_report.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent))
from pruning_v1_report import PruningReporter


@pytest.fixture
def temp_repo(tmp_path):
    """
    Create a temporary repo structure with test papers.
    
    This fixture sets up:
    - papers/ directory with test papers
    - reviews/ directory with review.json files
    
    The papers are designed to trigger specific flags:
    - A near-duplicate pair (similar titles/abstracts)
    - A paper with missing review.json
    - An expired paper (past valid_until)
    - A paper with verified_private badge
    - A paper with grounding_used=true but no grounding_metadata
    """
    papers_root = tmp_path / "papers"
    reviews_root = tmp_path / "reviews"
    papers_root.mkdir()
    reviews_root.mkdir()
    
    # Paper 1: normal paper, will be used as the "original" for duplicate detection
    paper1_dir = papers_root / "cs" / "ai" / "paper-one"
    paper1_dir.mkdir(parents=True)
    paper1_fm = {
        "paper_id": "2026-001",
        "title": "A Novel Approach to Machine Learning",
        "author": "alice",
        "category": "cs/ai",
        "abstract": "We present a novel machine learning approach that improves accuracy.",
        "date": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "score": 7.5,
        "badge": "verified_open",
        "supporting_repo": "https://github.com/example/ml-paper",
        "status": "current",
    }
    (paper1_dir / "index.md").write_text(
        f"---\n{yaml.dump(paper1_fm)}---\n\nPaper content here.",
        encoding='utf-8'
    )
    
    # Create review for paper 1
    review1_dir = reviews_root / "2026-001"
    review1_dir.mkdir()
    review1 = {
        "paper_id": "2026-001",
        "score": 7.5,
        "verdict": "ACCEPTED",
        "review_metadata": {
            "grounding_used": True,
        },
        "grounding_metadata": {
            "available": True,
            "sources": ["https://example.com"],
        }
    }
    (review1_dir / "review.json").write_text(json.dumps(review1), encoding='utf-8')
    
    # Paper 2: near-duplicate of paper 1 (similar title and abstract)
    paper2_dir = papers_root / "cs" / "ai" / "paper-two"
    paper2_dir.mkdir(parents=True)
    paper2_fm = {
        "paper_id": "2026-002",
        "title": "A New Approach to Machine Learning",  # Very similar to paper 1
        "author": "alice",
        "category": "cs/ai",
        "abstract": "We present a new machine learning approach that improves accuracy.",  # Very similar
        "date": datetime(2026, 2, 1, tzinfo=timezone.utc),  # Newer than paper 1
        "score": 7.0,
        "badge": "verified_open",
        "supporting_repo": "https://github.com/example/ml-paper-2",
        "status": "current",
    }
    (paper2_dir / "index.md").write_text(
        f"---\n{yaml.dump(paper2_fm)}---\n\nPaper content here.",
        encoding='utf-8'
    )
    
    # Create review for paper 2
    review2_dir = reviews_root / "2026-002"
    review2_dir.mkdir()
    review2 = {
        "paper_id": "2026-002",
        "score": 7.0,
        "verdict": "ACCEPTED",
        "review_metadata": {
            "grounding_used": True,
        },
        "grounding_metadata": {
            "available": True,
        }
    }
    (review2_dir / "review.json").write_text(json.dumps(review2), encoding='utf-8')
    
    # Paper 3: missing review.json
    paper3_dir = papers_root / "cs" / "theory" / "paper-three"
    paper3_dir.mkdir(parents=True)
    paper3_fm = {
        "paper_id": "2026-003",
        "title": "Theoretical Foundations of Computing",
        "author": "bob",
        "category": "cs/theory",
        "abstract": "A theoretical exploration of computation.",
        "date": datetime(2026, 3, 1, tzinfo=timezone.utc),
        "score": 8.0,
        "badge": "text_only",
        "status": "current",
    }
    (paper3_dir / "index.md").write_text(
        f"---\n{yaml.dump(paper3_fm)}---\n\nPaper content here.",
        encoding='utf-8'
    )
    # Note: no review.json created for this paper
    
    # Paper 4: expired (past valid_until)
    paper4_dir = papers_root / "cs" / "systems" / "paper-four"
    paper4_dir.mkdir(parents=True)
    expired_date = datetime.now(timezone.utc) - timedelta(days=30)
    paper4_fm = {
        "paper_id": "2026-004",
        "title": "Distributed Systems Architecture",
        "author": "carol",
        "category": "cs/systems",
        "abstract": "A distributed systems architecture for scalability.",
        "date": datetime(2026, 4, 1, tzinfo=timezone.utc),
        "score": 7.2,
        "badge": "verified_open",
        "valid_until": expired_date,
        "supporting_repo": "https://github.com/example/systems",
        "status": "current",  # Should be expired but isn't
    }
    (paper4_dir / "index.md").write_text(
        f"---\n{yaml.dump(paper4_fm)}---\n\nPaper content here.",
        encoding='utf-8'
    )
    
    # Create review for paper 4
    review4_dir = reviews_root / "2026-004"
    review4_dir.mkdir()
    review4 = {
        "paper_id": "2026-004",
        "score": 7.2,
        "verdict": "ACCEPTED",
        "review_metadata": {
            "grounding_used": False,
        },
        "grounding_metadata": {
            "available": False,
        }
    }
    (review4_dir / "review.json").write_text(json.dumps(review4), encoding='utf-8')
    
    # Paper 5: unverifiable badge (verified_private)
    paper5_dir = papers_root / "cs" / "security" / "paper-five"
    paper5_dir.mkdir(parents=True)
    paper5_fm = {
        "paper_id": "2026-005",
        "title": "Private Security Protocol",
        "author": "dave",
        "category": "cs/security",
        "abstract": "A security protocol with private implementation.",
        "date": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "score": 7.8,
        "badge": "verified_private",  # This is unverifiable per bugs.md
        "supporting_repo": "https://github.com/example/private-repo",
        "status": "current",
    }
    (paper5_dir / "index.md").write_text(
        f"---\n{yaml.dump(paper5_fm)}---\n\nPaper content here.",
        encoding='utf-8'
    )
    
    # Create review for paper 5
    review5_dir = reviews_root / "2026-005"
    review5_dir.mkdir()
    review5 = {
        "paper_id": "2026-005",
        "score": 7.8,
        "verdict": "ACCEPTED",
        "review_metadata": {
            "grounding_used": True,
        },
        "grounding_metadata": {
            "available": False,  # Claims grounding but no metadata
            "error": "No grounding metadata in response",
        }
    }
    (review5_dir / "review.json").write_text(json.dumps(review5), encoding='utf-8')
    
    return tmp_path


def test_pruning_reporter_initialization():
    """Test that PruningReporter initializes correctly."""
    reporter = PruningReporter(use_llm=False)
    assert reporter.use_llm is False
    assert reporter.papers == []
    assert reporter.paper_embeddings == {}


def test_load_papers(temp_repo, monkeypatch):
    """Test that papers are loaded correctly from the temp repo."""
    # Monkeypatch the REPO_ROOT and PAPERS_ROOT constants
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    reporter._load_papers()
    
    # Should have loaded 5 papers
    assert len(reporter.papers) == 5
    
    # Check paper IDs
    paper_ids = {p['paper_id'] for p in reporter.papers}
    assert paper_ids == {"2026-001", "2026-002", "2026-003", "2026-004", "2026-005"}
    
    # Check that paper 1 has the expected data
    paper1 = next(p for p in reporter.papers if p['paper_id'] == "2026-001")
    assert paper1['title'] == "A Novel Approach to Machine Learning"
    assert paper1['author'] == "alice"
    assert paper1['badge'] == "verified_open"


def test_token_overlap_similarity():
    """Test the fallback token overlap similarity measure."""
    reporter = PruningReporter(use_llm=False)
    
    # Identical texts
    assert reporter._token_overlap_similarity("hello world", "hello world") == 1.0
    
    # Completely different
    assert reporter._token_overlap_similarity("hello world", "foo bar") == 0.0
    
    # Partial overlap
    sim = reporter._token_overlap_similarity("hello world foo", "hello world bar")
    assert 0 < sim < 1
    
    # Case insensitive
    assert reporter._token_overlap_similarity("Hello World", "hello world") == 1.0


def test_check_duplicates_with_token_overlap(temp_repo, monkeypatch):
    """Test duplicate detection using token overlap (no embeddings)."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    # Force embeddings to be unavailable
    reporter = PruningReporter(use_llm=False)
    reporter.embedder = None
    reporter._load_papers()
    
    duplicates = reporter._check_duplicates()
    
    # Paper 2 should be flagged as a duplicate of paper 1
    # (they have very similar titles and abstracts)
    assert "2026-002" in duplicates
    dup_info = duplicates["2026-002"][0]
    assert dup_info["duplicate_of"] == "2026-001"
    assert dup_info["same_author"] is True


def test_check_missing_reviews(temp_repo, monkeypatch):
    """Test detection of papers with missing review.json files."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    reporter._load_papers()
    
    missing = reporter._check_missing_reviews()
    
    # Paper 3 should be flagged as missing review
    assert "2026-003" in missing
    assert "review.json" in missing["2026-003"]["expected_path"]


def test_check_expired_papers(temp_repo, monkeypatch):
    """Test detection of papers past their valid_until date."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    reporter._load_papers()
    
    expired = reporter._check_expired_papers()
    
    # Paper 4 should be flagged as expired
    assert "2026-004" in expired
    assert expired["2026-004"]["days_overdue"] > 0
    assert expired["2026-004"]["current_status"] == "current"


def test_check_unverifiable_badges(temp_repo, monkeypatch):
    """Test detection of unverifiable badge claims."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    reporter._load_papers()
    
    unverifiable = reporter._check_unverifiable_badges()
    
    # Paper 5 should be flagged for verified_private
    assert "2026-005" in unverifiable
    assert unverifiable["2026-005"]["badge"] == "verified_private"


def test_check_missing_grounding(temp_repo, monkeypatch):
    """Test detection of papers claiming grounding without metadata."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    reporter._load_papers()
    
    missing_grounding = reporter._check_missing_grounding()
    
    # Paper 5 should be flagged for missing grounding
    assert "2026-005" in missing_grounding
    assert missing_grounding["2026-005"]["grounding_used"] is True
    assert missing_grounding["2026-005"]["grounding_available"] is False


def test_generate_report_structure(temp_repo, monkeypatch):
    """Test that the generated report has the correct structure."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    report = reporter.generate_report()
    
    # Check report structure
    assert "report_metadata" in report
    assert "flagged_candidates" in report
    assert "summary_by_flag" in report
    
    # Check metadata
    meta = report["report_metadata"]
    assert "generated_at" in meta
    assert meta["total_papers_scanned"] == 5
    assert meta["total_flagged"] > 0
    
    # Check summary
    summary = report["summary_by_flag"]
    assert summary["near_duplicate"] >= 1  # Paper 2
    assert summary["missing_review"] >= 1  # Paper 3
    assert summary["expired"] >= 1  # Paper 4
    assert summary["unverifiable_badge"] >= 1  # Paper 5
    assert summary["missing_grounding"] >= 1  # Paper 5
    
    # Check flagged candidates structure
    assert len(report["flagged_candidates"]) > 0
    candidate = report["flagged_candidates"][0]
    assert "paper_id" in candidate
    assert "title" in candidate
    assert "flags" in candidate
    assert "evidence" in candidate


def test_write_json_report(temp_repo, monkeypatch):
    """Test that JSON report is written correctly."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    report = reporter.generate_report()
    
    output_path = temp_repo / "test_report.json"
    reporter.write_json_report(report, output_path)
    
    assert output_path.exists()
    
    # Verify it's valid JSON
    loaded = json.loads(output_path.read_text(encoding='utf-8'))
    assert loaded["report_metadata"]["total_papers_scanned"] == 5


def test_write_markdown_report(temp_repo, monkeypatch):
    """Test that Markdown report is written correctly."""
    import pruning_v1_report
    monkeypatch.setattr(pruning_v1_report, 'REPO_ROOT', temp_repo)
    monkeypatch.setattr(pruning_v1_report, 'PAPERS_ROOT', temp_repo / 'papers')
    monkeypatch.setattr(pruning_v1_report, 'REVIEWS_ROOT', temp_repo / 'reviews')
    
    reporter = PruningReporter(use_llm=False)
    report = reporter.generate_report()
    
    output_path = temp_repo / "test_report.md"
    reporter.write_markdown_report(report, output_path)
    
    assert output_path.exists()
    
    content = output_path.read_text(encoding='utf-8')
    assert "# Pubroot Pruning v1 Report" in content
    assert "Executive Summary" in content
    assert "Flagged Candidates" in content
    assert "REPORT-ONLY" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
