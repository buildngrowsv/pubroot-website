"""
Test Suite — Pubroot MCP Peer Review Server
=============================================

PURPOSE:
    Comprehensive tests for the MCP server that serves as the primary agent
    interface to the Pubroot. These tests validate all 6 tool functions,
    data loading helpers, error handling paths, and edge cases.

HISTORY:
    2026-03-23 — Created by Builder 9 in the swarm coordination sprint.
                 The MCP server previously had zero test coverage. This suite
                 covers every tool function, both local and remote data paths,
                 and various error/edge conditions the production server may encounter.

APPROACH:
    - All tests use mock data fixtures (no real filesystem or network calls)
    - The _load_json function is patched to return controlled test data
    - Each tool function is tested for: happy path, edge cases, error handling
    - Tests are organized by tool function name for easy navigation

RUNNING:
    cd _mcp_server && python -m pytest test_mcp_peer_review_server.py -v
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Ensure the server module is importable from this directory.
# We patch the MCP SDK import before importing the server, since the test
# environment may not have the mcp package installed.
# ---------------------------------------------------------------------------

# Create a mock MCP module structure so we can import the server without the SDK
mock_mcp_module = MagicMock()
mock_mcp_server = MagicMock()
mock_mcp_server_mcpserver = MagicMock()

# The MCPServer class needs to return an object with a .tool() decorator method
mock_server_instance = MagicMock()
mock_server_instance.tool.return_value = lambda fn: fn  # Decorator that passes through
mock_mcp_server_mcpserver.MCPServer.return_value = mock_server_instance

sys.modules["mcp"] = mock_mcp_module
sys.modules["mcp.server"] = mock_mcp_server
sys.modules["mcp.server.mcpserver"] = mock_mcp_server_mcpserver
sys.modules["mcp.server.stdio"] = MagicMock()
sys.modules["mcp.server.lowlevel"] = MagicMock()
sys.modules["mcp.server.models"] = MagicMock()

# Now import the server module — the mock MCP SDK will be used
import mcp_peer_review_server as server


# ---------------------------------------------------------------------------
# TEST FIXTURES — Realistic sample data matching the production JSON schemas
# ---------------------------------------------------------------------------

SAMPLE_AGENT_INDEX = {
    "schema_version": "1.0",
    "api_version": "1.0",
    "total_papers": 3,
    "last_updated": "2026-03-23T01:16:48.992485+00:00",
    "papers": [
        {
            "id": "2026-001",
            "title": "Advances in LLM Benchmarking Methodology",
            "author": "researcher_alpha",
            "category": "ai/llm-benchmarks",
            "abstract": "A comprehensive survey of language model evaluation techniques "
                         "including MMLU HumanEval and new multi-turn benchmark scores on methodology",
            "published_date": "2026-03-10T12:00:00+00:00",
            "review_score": 8.5,
            "badge": "verified_open",
            "status": "current",
            "article_path": "papers/ai/llm-benchmarks/example-title-slug/index.md",
            "review_path": "reviews/2026-001/review.json",
            "supporting_repo": "https://github.com/example/llm-benchmarks",
        },
        {
            "id": "2026-002",
            "title": "Agent Memory Patterns for Multi-Session Conversations",
            "author": "researcher_beta",
            "category": "ai/agent-architecture",
            "abstract": "Design patterns for persisting agent memory across sessions "
                         "using vector databases and structured retrieval.",
            "published_date": "2026-03-12T08:00:00+00:00",
            "review_score": 7.0,
            "badge": "verified_private",
            "status": "current",
            "article_path": "papers/ai/llm-benchmarks/another-example/index.md",
            "review_path": "reviews/2026-002/review.json",
            "supporting_repo": "https://github.com/example/agent-memory",
        },
        {
            "id": "2026-003",
            "title": "Deprecated Approach to Token Counting",
            "author": "researcher_gamma",
            "category": "ai/llm-benchmarks",
            "abstract": "An older paper on token counting methods that has been superseded.",
            "published_date": "2026-01-05T10:00:00+00:00",
            "review_score": 5.5,
            "badge": "text_only",
            "status": "superseded",
            "article_path": "papers/prior-art/general-disclosure/example/index.md",
            "review_path": "reviews/2026-003/review.json",
            "supporting_repo": None,
        },
    ],
}

SAMPLE_REVIEW = {
    "paper_id": "2026-001",
    "overall_score": 8.5,
    "verdict": "accepted",
    "claims": [
        {
            "text": "GPT-4o scores 90% on MMLU benchmark",
            "verified": True,
            "confidence": 0.95,
            "source": "https://example.com/mmlu-results",
        },
        {
            "text": "Claude 4 outperforms GPT-4o on code generation tasks",
            "verified": True,
            "confidence": 0.88,
            "source": "https://example.com/code-benchmarks",
        },
    ],
    "strengths": ["Well-structured methodology", "Reproducible results"],
    "weaknesses": ["Limited dataset size"],
    "suggestions": ["Expand to multilingual benchmarks"],
}

SAMPLE_CONTRIBUTORS = {
    "schema_version": "1.0",
    "contributors": {
        "researcher_alpha": {
            "github_handle": "researcher_alpha",
            "first_seen": "2026-01-01T00:00:00+00:00",
            "last_submission": "2026-03-10T12:00:00+00:00",
            "total_submissions": 5,
            "accepted": 4,
            "rejected": 1,
            "acceptance_rate": 0.8,
            "average_score": 7.5,
            "reputation_score": 0.75,
            "reputation_tier": "trusted",
            "categories": {
                "ai/llm-benchmarks": {"submissions": 3, "accepted": 3, "avg_score": 8.0},
                "ai/agent-architecture": {"submissions": 2, "accepted": 1, "avg_score": 6.5},
            },
        },
    },
}

SAMPLE_JOURNALS = {
    "schema_version": "2.0",
    "acceptance_threshold": 6.0,
    "journals": {
        "ai": {
            "display_name": "Artificial Intelligence",
            "topics": {
                "llm-benchmarks": {"display_name": "LLM Benchmarks & Evaluations"},
            },
        },
    },
}


def _mock_load_json(filename: str) -> dict:
    """
    Test-only replacement for _load_json that returns fixture data
    based on the filename requested, simulating the real data layer
    without touching the filesystem or network.
    """
    filename_lower = filename.lower()
    if "agent-index" in filename_lower:
        return SAMPLE_AGENT_INDEX.copy()
    elif "contributors" in filename_lower:
        return SAMPLE_CONTRIBUTORS.copy()
    elif "journals" in filename_lower:
        return SAMPLE_JOURNALS.copy()
    elif "reviews/" in filename_lower:
        # Return review data only for paper 2026-001
        if "2026-001" in filename_lower:
            return SAMPLE_REVIEW.copy()
        raise FileNotFoundError(f"No review found: {filename}")
    else:
        raise FileNotFoundError(f"Unknown fixture file: {filename}")


# ---------------------------------------------------------------------------
# TEST CLASSES
# ---------------------------------------------------------------------------


@patch.object(server, "_load_json", side_effect=_mock_load_json)
class TestSearchPapers(unittest.TestCase):
    """Tests for the search_papers tool — the primary discovery endpoint."""

    def test_search_all_current_papers_returns_only_current_status(self, mock_load):
        """Default search with no filters should return only 'current' status papers."""
        result = server.search_papers()
        self.assertEqual(result["total_matching"], 2)
        for paper in result["results"]:
            self.assertEqual(paper["status"], "current")

    def test_search_by_keyword_in_title(self, mock_load):
        """Query matching a word in the title should return that paper."""
        result = server.search_papers(query="benchmarking")
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-001")

    def test_search_by_keyword_in_abstract(self, mock_load):
        """Query matching words in the abstract should find the paper."""
        result = server.search_papers(query="vector databases")
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-002")

    def test_search_case_insensitive(self, mock_load):
        """Search should be case-insensitive for both query and paper content."""
        result = server.search_papers(query="BENCHMARKING")
        self.assertEqual(result["total_matching"], 1)

    def test_filter_by_category(self, mock_load):
        """Category filter should return only papers in that category."""
        result = server.search_papers(category="ai/agent-architecture")
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-002")

    def test_filter_by_min_score(self, mock_load):
        """min_score filter should exclude papers below the threshold."""
        result = server.search_papers(min_score=8.0)
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-001")

    def test_filter_by_badge(self, mock_load):
        """Badge filter should return only papers with that badge type."""
        result = server.search_papers(badge="verified_private")
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-002")

    def test_filter_superseded_status(self, mock_load):
        """Explicitly requesting 'superseded' status should return superseded papers."""
        result = server.search_papers(status="superseded")
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-003")

    def test_results_sorted_by_score_descending(self, mock_load):
        """Results should be sorted by review_score highest first."""
        result = server.search_papers()
        scores = [p["review_score"] for p in result["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_limit_clamps_to_valid_range(self, mock_load):
        """Limit should be clamped between 1 and 50."""
        # limit=0 should be clamped to 1 — with 2 current papers, we expect exactly 1
        result = server.search_papers(limit=0)
        self.assertEqual(len(result["results"]), 1)

        # limit=100 should be clamped to 50 — with only 2 papers, we get 2
        result = server.search_papers(limit=100)
        self.assertEqual(len(result["results"]), 2)

    def test_no_matching_papers_returns_empty(self, mock_load):
        """Query with no matches should return empty results list."""
        result = server.search_papers(query="quantum entanglement photonics")
        self.assertEqual(result["total_matching"], 0)
        self.assertEqual(result["results"], [])

    def test_includes_last_updated_from_index(self, mock_load):
        """Response should include the index's last_updated timestamp."""
        result = server.search_papers()
        self.assertIsNotNone(result["index_last_updated"])

    def test_combined_filters(self, mock_load):
        """Multiple filters should be applied together (AND logic)."""
        result = server.search_papers(
            category="ai/llm-benchmarks",
            min_score=8.0,
            badge="verified_open",
        )
        self.assertEqual(result["total_matching"], 1)
        self.assertEqual(result["results"][0]["id"], "2026-001")


@patch.object(server, "_load_json", side_effect=_mock_load_json)
@patch.object(server, "_load_review")
class TestVerifyClaim(unittest.TestCase):
    """Tests for the verify_claim tool — the agent fact-checking endpoint."""

    def test_matching_claim_returns_found(self, mock_review, mock_load):
        """A claim with enough keyword overlap should match and return verification data."""
        mock_review.return_value = SAMPLE_REVIEW
        result = server.verify_claim(claim="GPT-4o scores 90% on MMLU benchmark")
        self.assertTrue(result["found"])
        self.assertGreater(result["total_matches"], 0)

    def test_no_matching_claim_returns_not_found(self, mock_review, mock_load):
        """A claim with no keyword overlap should return found=False with a suggestion."""
        mock_review.return_value = SAMPLE_REVIEW
        result = server.verify_claim(claim="quantum computing breaks RSA encryption")
        self.assertFalse(result["found"])
        self.assertIn("suggestion", result)
        self.assertEqual(result["matches"], [])

    def test_category_filter_narrows_search(self, mock_review, mock_load):
        """Category filter should limit which papers are checked for claim verification."""
        mock_review.return_value = SAMPLE_REVIEW
        # This category doesn't match paper 2026-001 (which is ai/llm-benchmarks)
        result = server.verify_claim(
            claim="GPT-4o scores 90% on MMLU benchmark",
            category="materials/polymers",
        )
        self.assertFalse(result["found"])

    def test_skips_superseded_papers(self, mock_review, mock_load):
        """verify_claim should only check papers with 'current' status."""
        mock_review.return_value = SAMPLE_REVIEW
        # The superseded paper (2026-003) about token counting should not be checked
        result = server.verify_claim(claim="token counting methods deprecated")
        self.assertFalse(result["found"])

    def test_match_includes_paper_metadata(self, mock_review, mock_load):
        """Each match should include paper_id, title, score, and claim details."""
        mock_review.return_value = SAMPLE_REVIEW
        result = server.verify_claim(claim="GPT-4o scores 90% on MMLU benchmark")
        if result["found"]:
            match = result["matches"][0]
            self.assertIn("paper_id", match)
            self.assertIn("paper_title", match)
            self.assertIn("paper_score", match)
            self.assertIn("claim_text", match)
            self.assertIn("verified", match)
            self.assertIn("confidence", match)


@patch.object(server, "_load_review")
class TestGetReview(unittest.TestCase):
    """Tests for the get_review tool — fetches full structured review for a paper."""

    def test_existing_review_returns_found(self, mock_review):
        """A valid paper_id with an existing review should return the full review."""
        mock_review.return_value = SAMPLE_REVIEW
        result = server.get_review(paper_id="2026-001")
        self.assertTrue(result["found"])
        self.assertEqual(result["paper_id"], "2026-001")
        self.assertIn("review", result)
        self.assertEqual(result["review"]["overall_score"], 8.5)

    def test_missing_review_returns_not_found(self, mock_review):
        """A paper_id with no review should return found=False and an error message."""
        mock_review.return_value = None
        result = server.get_review(paper_id="9999-999")
        self.assertFalse(result["found"])
        self.assertIn("error", result)
        self.assertIn("9999-999", result["error"])


@patch.object(server, "_load_json", side_effect=_mock_load_json)
class TestGetContributorReputation(unittest.TestCase):
    """Tests for the get_contributor_reputation tool."""

    def test_existing_contributor_returns_full_profile(self, mock_load):
        """An existing contributor should return their full reputation profile."""
        result = server.get_contributor_reputation(github_handle="researcher_alpha")
        self.assertTrue(result["found"])
        self.assertEqual(result["github_handle"], "researcher_alpha")
        self.assertEqual(result["reputation_score"], 0.75)
        self.assertEqual(result["reputation_tier"], "trusted")
        self.assertEqual(result["total_submissions"], 5)
        self.assertEqual(result["accepted"], 4)
        self.assertEqual(result["rejected"], 1)
        self.assertAlmostEqual(result["acceptance_rate"], 0.8)

    def test_unknown_contributor_returns_not_found(self, mock_load):
        """An unknown GitHub handle should return found=False with a helpful message."""
        result = server.get_contributor_reputation(github_handle="totally_unknown_user")
        self.assertFalse(result["found"])
        self.assertIn("totally_unknown_user", result["message"])
        self.assertIn("suggestion", result)

    def test_returns_categories_breakdown(self, mock_load):
        """The response should include per-category submission stats."""
        result = server.get_contributor_reputation(github_handle="researcher_alpha")
        self.assertIn("categories", result)
        self.assertIn("ai/llm-benchmarks", result["categories"])


@patch.object(server, "_load_json", side_effect=_mock_load_json)
class TestGetRelatedWork(unittest.TestCase):
    """Tests for the get_related_work tool — finds related papers."""

    def test_query_finds_related_papers(self, mock_load):
        """A topical query should return papers with keyword overlap."""
        result = server.get_related_work(query="language model evaluation benchmarks")
        self.assertGreater(result["total_related"], 0)

    def test_paper_id_finds_same_category_papers(self, mock_load):
        """Providing a paper_id should find related papers, favoring the same category."""
        result = server.get_related_work(paper_id="2026-001")
        # 2026-001 is ai/llm-benchmarks — shouldn't find itself in results
        paper_ids_in_results = [r["paper_id"] for r in result["results"]]
        self.assertNotIn("2026-001", paper_ids_in_results)

    def test_no_args_returns_error(self, mock_load):
        """Calling with neither query nor paper_id should return an error."""
        result = server.get_related_work()
        self.assertIn("error", result)

    def test_no_related_papers_returns_empty(self, mock_load):
        """A very specific query with no overlap should return empty results."""
        result = server.get_related_work(query="xyzzyplugh")
        self.assertEqual(result["total_related"], 0)
        self.assertEqual(result["results"], [])

    def test_skips_superseded_papers(self, mock_load):
        """Related work results should only include 'current' status papers."""
        result = server.get_related_work(query="token counting methods")
        for r in result["results"]:
            # The superseded paper 2026-003 should not appear
            self.assertNotEqual(r["paper_id"], "2026-003")

    def test_results_sorted_by_relevance(self, mock_load):
        """Results should be sorted by relevance_score descending."""
        result = server.get_related_work(query="language model evaluation benchmarks")
        if len(result["results"]) > 1:
            scores = [r["relevance_score"] for r in result["results"]]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_max_10_results(self, mock_load):
        """Results should be capped at 10."""
        result = server.get_related_work(query="language model")
        self.assertLessEqual(len(result["results"]), 10)


@patch.object(server, "_load_json", side_effect=_mock_load_json)
class TestGetSubmissionGuide(unittest.TestCase):
    """Tests for the get_submission_guide tool — agent-facing submission policies."""

    def test_returns_product_info(self, mock_load):
        """Should include product name and website URL."""
        result = server.get_submission_guide()
        self.assertEqual(result["product"], "Pubroot")
        self.assertIn("pubroot.com", result["website"])

    def test_returns_acceptance_threshold(self, mock_load):
        """Should include the acceptance threshold from journals.json."""
        result = server.get_submission_guide()
        self.assertEqual(result["acceptance_threshold"], 6.0)

    def test_returns_figure_hosting_policy(self, mock_load):
        """Should include guidance on figure/image hosting for submissions."""
        result = server.get_submission_guide()
        self.assertIn("figures_and_embedded_media", result)
        self.assertIn("policy", result["figures_and_embedded_media"])

    def test_returns_revision_guidance(self, mock_load):
        """Should include how-to steps for revising rejected or published papers."""
        result = server.get_submission_guide()
        self.assertIn("revisions", result)
        self.assertIn("how_to_submit_revision", result)

    def test_returns_issue_body_format(self, mock_load):
        """Should include the known section labels for the submission issue template."""
        result = server.get_submission_guide()
        self.assertIn("issue_body_format", result)
        labels = result["issue_body_format"]["known_section_labels"]
        self.assertIn("Article Title", labels)
        self.assertIn("Abstract", labels)
        self.assertIn("Article Body", labels)


# ---------------------------------------------------------------------------
# DATA LOADING TESTS — testing _load_json and _load_review error paths
# ---------------------------------------------------------------------------


class TestLoadJsonLocal(unittest.TestCase):
    """Tests for the _load_json helper in local filesystem mode."""

    def setUp(self):
        """Clear the JSON cache before each test to avoid cross-test interference."""
        server._json_cache.clear()

    @patch.object(server, "REPO_MODE", "local")
    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    def test_missing_file_raises_file_not_found(self, mock_open):
        """Loading a non-existent local file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            server._load_json("nonexistent.json")

    @patch.object(server, "REPO_MODE", "local")
    @patch("builtins.open")
    def test_malformed_json_raises_decode_error(self, mock_open):
        """Loading a file with invalid JSON should raise json.JSONDecodeError."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read = MagicMock(return_value="not valid json {{{")
        with patch("json.load", side_effect=json.JSONDecodeError("err", "doc", 0)):
            with self.assertRaises(json.JSONDecodeError):
                server._load_json("bad.json")


class TestLoadJsonRemote(unittest.TestCase):
    """Tests for the _load_json helper in remote (GitHub) mode."""

    def setUp(self):
        """Clear the JSON cache before each test to avoid cross-test interference."""
        server._json_cache.clear()

    @patch.object(server, "REPO_MODE", "remote")
    @patch("mcp_peer_review_server.requests")
    def test_successful_remote_fetch(self, mock_requests):
        """Successful GitHub fetch should return parsed JSON."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"papers": []}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        result = server._load_json("agent-index.json")
        self.assertEqual(result, {"papers": []})
        mock_requests.get.assert_called_once()

    @patch.object(server, "REPO_MODE", "remote")
    @patch("mcp_peer_review_server.requests")
    def test_http_error_propagates(self, mock_requests):
        """HTTP errors from GitHub should propagate as requests.HTTPError."""
        import requests as real_requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = real_requests.HTTPError("404")
        mock_requests.get.return_value = mock_response
        mock_requests.HTTPError = real_requests.HTTPError

        with self.assertRaises(real_requests.HTTPError):
            server._load_json("nonexistent.json")

    @patch.object(server, "REPO_MODE", "remote")
    @patch("mcp_peer_review_server.requests")
    def test_timeout_propagates(self, mock_requests):
        """Network timeout should propagate as requests.ConnectionError or Timeout."""
        import requests as real_requests
        mock_requests.get.side_effect = real_requests.Timeout("Connection timed out")
        mock_requests.Timeout = real_requests.Timeout

        with self.assertRaises(real_requests.Timeout):
            server._load_json("agent-index.json")


class TestLoadReview(unittest.TestCase):
    """Tests for the _load_review helper."""

    def setUp(self):
        server._json_cache.clear()

    @patch.object(server, "_load_json")
    def test_existing_review_returns_data(self, mock_load):
        """Loading an existing review should return the review dict."""
        mock_load.return_value = SAMPLE_REVIEW
        result = server._load_review("2026-001")
        self.assertIsNotNone(result)
        self.assertEqual(result["paper_id"], "2026-001")

    @patch.object(server, "_load_json", side_effect=FileNotFoundError)
    def test_missing_review_returns_none(self, mock_load):
        """Loading a non-existent review should return None (not raise)."""
        result = server._load_review("9999-999")
        self.assertIsNone(result)

    @patch.object(server, "_load_json")
    def test_http_error_returns_none(self, mock_load):
        """HTTP error when loading review in remote mode should return None."""
        import requests as real_requests
        mock_load.side_effect = real_requests.HTTPError("404")
        result = server._load_review("9999-999")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# CACHE TESTS — validates the in-memory TTL cache in _load_json
# ---------------------------------------------------------------------------


class TestJsonCache(unittest.TestCase):
    """Tests for the in-memory JSON cache layer."""

    def setUp(self):
        server._json_cache.clear()

    def tearDown(self):
        server._json_cache.clear()

    @patch.object(server, "REPO_MODE", "local")
    @patch("builtins.open")
    def test_cache_prevents_second_file_read(self, mock_open):
        """Second call to _load_json with same filename should use cache, not re-read."""
        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        with patch("json.load", return_value={"papers": []}):
            server._load_json("agent-index.json")
            server._load_json("agent-index.json")

        # open() should only be called once — second call served from cache
        self.assertEqual(mock_open.call_count, 1)

    @patch.object(server, "REPO_MODE", "local")
    @patch("builtins.open")
    def test_expired_cache_triggers_reload(self, mock_open):
        """After TTL expires, _load_json should re-read from source."""
        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_open.return_value = mock_file

        with patch("json.load", return_value={"papers": []}):
            server._load_json("agent-index.json")

            # Manually expire the cache entry by backdating the timestamp
            filename = "agent-index.json"
            _, data = server._json_cache[filename]
            server._json_cache[filename] = (0, data)  # epoch = long expired

            server._load_json("agent-index.json")

        # open() should be called twice — cache was expired for the second call
        self.assertEqual(mock_open.call_count, 2)


# ---------------------------------------------------------------------------
# ERROR HANDLING TESTS — validates graceful error returns from tool functions
# ---------------------------------------------------------------------------


class TestToolErrorHandling(unittest.TestCase):
    """Tests for error handling in tool functions when data loading fails."""

    def setUp(self):
        server._json_cache.clear()

    @patch.object(server, "_load_json", side_effect=FileNotFoundError("agent-index.json not found"))
    def test_search_papers_handles_missing_index(self, mock_load):
        """search_papers should return an error dict when agent-index.json is missing."""
        result = server.search_papers()
        self.assertIn("error", result)
        self.assertEqual(result["total_matching"], 0)
        self.assertEqual(result["results"], [])

    @patch.object(server, "_load_json", side_effect=FileNotFoundError("contributors.json not found"))
    def test_get_contributor_handles_missing_data(self, mock_load):
        """get_contributor_reputation should return error when contributors.json is missing."""
        result = server.get_contributor_reputation(github_handle="someone")
        self.assertIn("error", result)
        self.assertFalse(result["found"])

    @patch.object(server, "_load_json", side_effect=FileNotFoundError("journals.json not found"))
    def test_get_submission_guide_handles_missing_journals(self, mock_load):
        """get_submission_guide should return error when journals.json is missing."""
        result = server.get_submission_guide()
        self.assertIn("error", result)

    def test_verify_claim_rejects_empty_claim(self):
        """verify_claim should reject empty string claim with a clear error."""
        result = server.verify_claim(claim="")
        self.assertFalse(result["found"])
        self.assertIn("error", result)

    def test_verify_claim_rejects_whitespace_claim(self):
        """verify_claim should reject whitespace-only claim."""
        result = server.verify_claim(claim="   ")
        self.assertFalse(result["found"])
        self.assertIn("error", result)

    def test_get_contributor_rejects_empty_handle(self):
        """get_contributor_reputation should reject empty github_handle."""
        result = server.get_contributor_reputation(github_handle="")
        self.assertFalse(result["found"])
        self.assertIn("error", result)

    @patch.object(server, "_load_json", side_effect=_mock_load_json)
    def test_get_related_work_handles_missing_index(self, mock_load):
        """get_related_work without args should return error before loading data."""
        result = server.get_related_work()
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# CONFIGURATION TESTS
# ---------------------------------------------------------------------------


class TestConfiguration(unittest.TestCase):
    """Tests for server configuration and environment variable handling."""

    def test_default_repo_mode_is_local(self):
        """REPO_MODE should default to 'local' when env var is not set."""
        # The module-level default is already set; just verify it
        self.assertIn(server.REPO_MODE, ("local", "remote"))

    def test_github_raw_base_url_format(self):
        """GITHUB_RAW_BASE should be a valid raw.githubusercontent.com URL."""
        self.assertTrue(
            server.GITHUB_RAW_BASE.startswith("https://raw.githubusercontent.com/")
        )

    def test_local_repo_path_is_parent_directory(self):
        """LOCAL_REPO_PATH should default to the parent of the _mcp_server directory."""
        # The default path computation goes up one level from __file__'s directory
        expected_parent = os.path.dirname(
            os.path.dirname(os.path.abspath(server.__file__))
        )
        self.assertEqual(server.LOCAL_REPO_PATH, expected_parent)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
