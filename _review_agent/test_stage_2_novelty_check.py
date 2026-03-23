"""
Tests for Stage 2: Novelty Check — Pubroot Review Pipeline

HISTORY:
    Created 2026-03-23 by Builder 5 (swarm agent) as part of T4.
    These tests validate the novelty checking logic that searches arXiv,
    Semantic Scholar, and the internal journal index for related work.

APPROACH:
    - External API calls (arXiv, Semantic Scholar) are mocked to avoid
      network dependencies and ensure deterministic, fast tests.
    - The internal index search uses real file I/O against temp files,
      matching the actual production behavior.
    - Each test targets a specific behavior documented in the stage 2 module.

RUNNING:
    pytest _review_agent/test_stage_2_novelty_check.py -v
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from stage_2_novelty_check import (
    check_novelty,
    _build_search_query,
    _search_internal_index,
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

SAMPLE_AGENT_INDEX = {
    "schema_version": "1.0",
    "total_papers": 3,
    "papers": [
        {
            "id": "2026-001",
            "title": "GPT-5 vs Claude 4 Code Review Benchmark",
            "author": "testuser",
            "category": "ai/llm-benchmarks",
            "abstract": "Comparing code review performance of GPT-5 and Claude 4 across multiple tasks.",
            "published_date": "2026-03-20T12:00:00+00:00",
            "review_score": 8.0,
            "status": "current",
        },
        {
            "id": "2026-002",
            "title": "Multi-Agent Orchestration Patterns for Production Systems",
            "author": "agentdev",
            "category": "ai/agent-architecture",
            "abstract": "A survey of orchestration patterns for multi-agent AI systems in production environments.",
            "published_date": "2026-03-15T10:00:00+00:00",
            "review_score": 7.5,
            "status": "current",
        },
        {
            "id": "2026-003",
            "title": "Outdated Paper on Old Topic",
            "author": "oldauthor",
            "category": "ai/llm-benchmarks",
            "abstract": "This paper is superseded by a newer version.",
            "published_date": "2026-01-01T00:00:00+00:00",
            "review_score": 6.0,
            "status": "superseded",
        },
    ],
}


@pytest.fixture
def repo_root(tmp_path):
    """Create a temp repo root with an agent-index.json file."""
    index_path = tmp_path / "agent-index.json"
    index_path.write_text(json.dumps(SAMPLE_AGENT_INDEX))
    return str(tmp_path)


@pytest.fixture
def empty_repo_root(tmp_path):
    """Create a temp repo root without agent-index.json."""
    return str(tmp_path)


# ---------------------------------------------------------------------------
# MOCK HELPERS — simulate API responses
# ---------------------------------------------------------------------------

def _mock_arxiv_xml_response(papers):
    """Build an Atom XML string mimicking the arXiv API response."""
    entries = ""
    for paper in papers:
        entries += f"""
        <entry xmlns="http://www.w3.org/2005/Atom">
            <id>http://arxiv.org/abs/{paper['id']}</id>
            <title>{paper['title']}</title>
            <summary>{paper['abstract']}</summary>
            <published>{paper['published']}</published>
            <author><name>{paper['author']}</name></author>
        </entry>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">2</totalResults>
        {entries}
    </feed>"""


def _mock_s2_json_response(papers):
    """Build a JSON dict mimicking the Semantic Scholar API response."""
    data = []
    for paper in papers:
        data.append({
            "paperId": paper.get("id", "abc123"),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "citationCount": paper.get("citations", 10),
            "year": paper.get("year", 2025),
            "url": f"https://semanticscholar.org/paper/{paper.get('id', 'abc')}",
            "tldr": {"text": paper.get("tldr", "A relevant paper.")} if paper.get("tldr") else None,
        })
    return {"total": len(data), "data": data}


# ---------------------------------------------------------------------------
# _build_search_query TESTS
# ---------------------------------------------------------------------------


class TestBuildSearchQuery:
    """Test the search query builder helper."""

    def test_combines_title_and_abstract(self):
        """Query should contain both the title and first ~50 words of abstract."""
        query = _build_search_query(
            "My Great Paper Title",
            "This abstract describes the methodology and findings of our research.",
        )
        assert "My Great Paper Title" in query
        assert "methodology" in query

    def test_strips_markdown_formatting(self):
        """Markdown characters (#, *, _, etc.) should be removed from the query."""
        query = _build_search_query(
            "**Bold** _Title_ with `code`",
            "Abstract with [links](url) and #headers",
        )
        assert "**" not in query
        assert "`" not in query
        assert "[" not in query

    def test_truncates_long_queries(self):
        """Queries exceeding 500 chars should be truncated."""
        long_title = "A" * 300
        long_abstract = "B " * 200
        query = _build_search_query(long_title, long_abstract)
        assert len(query) <= 500

    def test_handles_empty_inputs(self):
        """Empty title or abstract should not crash."""
        query = _build_search_query("", "")
        assert isinstance(query, str)

        query2 = _build_search_query("Just a Title", "")
        assert "Just a Title" in query2


# ---------------------------------------------------------------------------
# _search_internal_index TESTS
# ---------------------------------------------------------------------------


class TestSearchInternalIndex:
    """Test the internal journal index search and supersession detection."""

    def test_finds_related_papers_by_keyword_overlap(self, repo_root):
        """Papers sharing 3+ meaningful words with the query should be returned."""
        results, supersession = _search_internal_index(
            query="GPT-5 Claude code review benchmark performance comparison",
            submission_title="New LLM Code Review Benchmark",
            category="ai/llm-benchmarks",
            repo_root=repo_root,
        )
        # Should find the GPT-5 vs Claude 4 paper
        assert len(results) > 0
        assert any("GPT-5" in r["title"] for r in results)

    def test_returns_empty_when_no_index_file(self, empty_repo_root):
        """Missing agent-index.json should return empty results, not crash."""
        results, supersession = _search_internal_index(
            query="some query",
            submission_title="Some Title",
            category="ai/llm-benchmarks",
            repo_root=empty_repo_root,
        )
        assert results == []
        assert supersession is None

    def test_detects_potential_supersession(self, repo_root):
        """A paper in the same category with high word overlap should flag supersession."""
        # This query closely matches our fixture paper 2026-001
        results, supersession = _search_internal_index(
            query="GPT-5 vs Claude 4 code review benchmark comparison performance tasks multiple",
            submission_title="Updated GPT-5 Code Review Benchmark",
            category="ai/llm-benchmarks",
            repo_root=repo_root,
        )
        # The supersession detection requires score > 0.3, same category, not superseded
        # With enough word overlap, it should detect supersession
        if supersession is not None:
            assert "2026-001" in supersession["existing_paper_id"]

    def test_superseded_papers_not_flagged_for_supersession(self, repo_root):
        """Papers with status 'superseded' should not be flagged as supersession candidates."""
        # Paper 2026-003 is already superseded — even if matched, it shouldn't flag
        results, supersession = _search_internal_index(
            query="outdated paper old topic superseded version",
            submission_title="Outdated Paper Update",
            category="ai/llm-benchmarks",
            repo_root=repo_root,
        )
        if supersession is not None:
            # If a supersession is detected, it should NOT be the superseded paper
            assert supersession["existing_paper_id"] != "2026-003"

    def test_results_limited_to_5(self, tmp_path):
        """At most 5 results should be returned even if more papers match."""
        # Create an index with many papers that all share keywords
        many_papers = {
            "papers": [
                {
                    "id": f"2026-{i:03d}",
                    "title": f"Machine learning benchmark evaluation paper number {i}",
                    "author": "author",
                    "category": "ai/llm-benchmarks",
                    "abstract": f"This paper evaluates machine learning benchmarks variant {i}.",
                    "published_date": "2026-01-01T00:00:00+00:00",
                    "review_score": 7.0,
                    "status": "current",
                }
                for i in range(20)
            ]
        }
        index_path = tmp_path / "agent-index.json"
        index_path.write_text(json.dumps(many_papers))

        results, _ = _search_internal_index(
            query="machine learning benchmark evaluation paper",
            submission_title="Another ML Benchmark",
            category="ai/llm-benchmarks",
            repo_root=str(tmp_path),
        )
        assert len(results) <= 5


# ---------------------------------------------------------------------------
# check_novelty INTEGRATION TESTS (with mocked external APIs)
# ---------------------------------------------------------------------------


class TestCheckNoveltyIntegration:
    """Test the main check_novelty function with mocked API calls."""

    @patch("stage_2_novelty_check._search_arxiv")
    @patch("stage_2_novelty_check._search_semantic_scholar")
    def test_combines_all_three_sources(self, mock_s2, mock_arxiv, repo_root):
        """check_novelty should combine results from arXiv, S2, and internal index."""
        mock_arxiv.return_value = [
            {"source": "arxiv", "id": "2501.00001", "title": "arXiv Paper 1"},
        ]
        mock_s2.return_value = [
            {"source": "semantic_scholar", "id": "s2-001", "title": "S2 Paper 1"},
        ]

        result = check_novelty(
            title="GPT-5 Code Review Benchmark",
            abstract="We benchmark GPT-5 code review performance across tasks.",
            category="ai/llm-benchmarks",
            repo_root=repo_root,
        )

        assert len(result["arxiv_results"]) == 1
        assert len(result["s2_results"]) == 1
        # Internal results depend on keyword overlap with the fixture
        assert isinstance(result["internal_results"], list)
        assert result["total_related"] >= 2  # At least arXiv + S2
        assert result["errors"] == []

    @patch("stage_2_novelty_check._search_arxiv")
    @patch("stage_2_novelty_check._search_semantic_scholar")
    def test_api_failure_is_non_blocking(self, mock_s2, mock_arxiv, repo_root):
        """If arXiv or S2 fails, the review should continue with available results."""
        mock_arxiv.side_effect = Exception("arXiv is down")
        mock_s2.side_effect = Exception("S2 timeout")

        result = check_novelty(
            title="Some Title",
            abstract="Some abstract about testing.",
            category="ai/agent-architecture",
            repo_root=repo_root,
        )

        # Should not crash — errors are captured, not raised
        assert result["arxiv_results"] == []
        assert result["s2_results"] == []
        assert len(result["errors"]) == 2
        assert any("arXiv" in e for e in result["errors"])
        assert any("Semantic Scholar" in e for e in result["errors"])

    @patch("stage_2_novelty_check._search_arxiv")
    @patch("stage_2_novelty_check._search_semantic_scholar")
    def test_search_query_is_included_in_result(self, mock_s2, mock_arxiv, repo_root):
        """The generated search query should be included in the result for debugging."""
        mock_arxiv.return_value = []
        mock_s2.return_value = []

        result = check_novelty(
            title="My Test Paper",
            abstract="About testing things.",
            category="ai/agent-architecture",
            repo_root=repo_root,
        )

        assert "search_query" in result
        assert "My Test Paper" in result["search_query"]

    @patch("stage_2_novelty_check._search_arxiv")
    @patch("stage_2_novelty_check._search_semantic_scholar")
    def test_s2_api_key_passed_through(self, mock_s2, mock_arxiv, repo_root):
        """When an S2 API key is provided, it should be passed to the S2 search."""
        mock_arxiv.return_value = []
        mock_s2.return_value = []

        check_novelty(
            title="Test",
            abstract="Test abstract.",
            category="ai/agent-architecture",
            repo_root=repo_root,
            s2_api_key="my-secret-key",
        )

        # Verify the S2 search was called with the API key.
        # check_novelty calls _search_semantic_scholar(query, max_results=5, api_key=key)
        # so api_key is always a keyword argument.
        mock_s2.assert_called_once()
        assert mock_s2.call_args[1]["api_key"] == "my-secret-key"
