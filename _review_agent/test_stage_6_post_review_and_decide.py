"""
Tests for Stage 6: Post Review & Decide — Pubroot Review Pipeline

HISTORY:
    Created 2026-03-23 by Builder 6 (swarm agent) as part of T5.
    These tests validate the final pipeline stage that acts on the review:
    posting comments, creating PRs, updating contributor stats, and
    managing the agent-index.json.

APPROACH:
    - We mock the GitHub API (requests library) to avoid real API calls.
    - We create temp files for contributors.json and agent-index.json to
      test file read/write operations.
    - Key areas per Scout 11: _update_agent_index reads local file that
      may be stale with concurrent runs (no file locking), and
      _update_contributors has running average calculation to verify.

RUNNING:
    pytest _review_agent/test_stage_6_post_review_and_decide.py -v
"""

import json
import os
import tempfile
import pytest
import requests
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from stage_6_post_review_and_decide import (
    post_review_and_decide,
    GitHubAPI,
    _format_review_comment,
    _format_error_comment,
    _build_article_md,
    _build_manifest,
    _build_index_entry,
    _update_contributors,
    _score_to_bar,
    _hugo_date_string_utc,
)


# ---------------------------------------------------------------------------
# FIXTURES — sample data matching earlier stage outputs
# ---------------------------------------------------------------------------

SAMPLE_REVIEW_SUCCESS = {
    "success": True,
    "review": {
        "paper_id": "2026-042",
        "score": 7.5,
        "verdict": "ACCEPTED",
        "badge": "verified_open",
        "summary": "A solid benchmark of LLM code review capabilities.",
        "strengths": ["Novel dataset", "Rigorous methodology"],
        "weaknesses": ["Limited to Python only"],
        "suggestions": ["Expand to more languages"],
        "confidence": {
            "methodology": 0.85,
            "factual_accuracy": 0.9,
            "novelty": 0.7,
            "code_quality": 0.8,
            "writing_quality": 0.75,
            "reproducibility": 0.8,
        },
        "claims": [
            {
                "text": "GPT-4 achieves 92% accuracy",
                "verified": True,
                "source": "https://arxiv.org/abs/2511.00001",
                "confidence": 0.85,
            }
        ],
        "review_metadata": {
            "reviewer": "gemini-2.5-flash-lite",
        },
    },
    "grounding_metadata": {
        "available": True,
        "sources": [{"title": "ArXiv", "uri": "https://arxiv.org"}],
    },
    "raw_response_text": "{}",
    "model_used": "gemini-2.5-flash-lite",
    "error": None,
}

SAMPLE_REVIEW_REJECTED = {
    "success": True,
    "review": {
        "paper_id": "2026-043",
        "score": 3.5,
        "verdict": "REJECTED",
        "badge": "text_only",
        "summary": "The article lacks evidence and contains factual errors.",
        "strengths": ["Interesting topic"],
        "weaknesses": ["No evidence", "Factual errors"],
        "suggestions": ["Add citations"],
        "confidence": {},
        "claims": [],
        "review_metadata": {"reviewer": "gemini-2.5-flash-lite"},
    },
    "grounding_metadata": {"available": False},
    "raw_response_text": "{}",
    "model_used": "gemini-2.5-flash-lite",
    "error": None,
}

SAMPLE_REVIEW_ERROR = {
    "success": False,
    "review": None,
    "grounding_metadata": None,
    "raw_response_text": "",
    "model_used": "gemini-2.5-flash-lite",
    "error": "Gemini API rate limit exceeded",
}

SAMPLE_PARSED = {
    "title": "Testing LLM Accuracy in Code Review",
    "category": "ai/llm-benchmarks",
    "abstract": "We tested 5 leading LLMs.",
    "body": "Article body text here.",
    "author": "test-user",
    "supporting_repo": "https://github.com/test/repo",
    "commit_sha": "abc123",
    "submission_type": "original-research",
    "word_count_body": 1500,
}

SAMPLE_NOVELTY = {
    "arxiv_results": [],
    "s2_results": [],
    "internal_results": [],
    "potential_supersession": None,
}

SAMPLE_REPO_DATA = {
    "available": True,
    "badge_type": "verified_open",
    "file_count": 10,
    "total_content_bytes": 5000,
}

# Minimal contributors.json structure
EMPTY_CONTRIBUTORS = {"contributors": {}}

# Minimal agent-index.json structure
EMPTY_AGENT_INDEX = {
    "schema_version": "1.0",
    "total_papers": 0,
    "last_updated": "2026-01-01T00:00:00Z",
    "papers": [],
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_repo_root():
    """
    Create a temporary repo root with contributors.json and agent-index.json.
    These files are read and written by Stage 6 during the accept/reject flow.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write contributors.json
        with open(os.path.join(tmpdir, "contributors.json"), "w") as f:
            json.dump(EMPTY_CONTRIBUTORS, f)

        # Write agent-index.json
        with open(os.path.join(tmpdir, "agent-index.json"), "w") as f:
            json.dump(EMPTY_AGENT_INDEX, f)

        yield tmpdir


# ---------------------------------------------------------------------------
# TESTS: _hugo_date_string_utc
# ---------------------------------------------------------------------------


class TestHugoDateStringUtc:
    """
    Tests for the Hugo date formatting function. This was introduced to fix
    a bug in March 2026 where ISO-8601 dates with colons were incorrectly
    treated as multi-line YAML values, breaking Hugo's date parsing.
    """

    def test_formats_aware_datetime(self):
        """Should format a timezone-aware datetime as RFC3339 UTC."""
        dt = datetime(2026, 3, 22, 17, 15, 26, tzinfo=timezone.utc)
        result = _hugo_date_string_utc(dt)
        assert result == "2026-03-22T17:15:26Z"

    def test_formats_naive_datetime_as_utc(self):
        """Naive datetimes should be treated as UTC."""
        dt = datetime(2026, 3, 22, 17, 15, 26)
        result = _hugo_date_string_utc(dt)
        assert result == "2026-03-22T17:15:26Z"

    def test_no_microseconds_in_output(self):
        """Output should not contain microseconds (breaks Hugo)."""
        dt = datetime(2026, 3, 22, 17, 15, 26, 123456, tzinfo=timezone.utc)
        result = _hugo_date_string_utc(dt)
        assert "." not in result
        assert result == "2026-03-22T17:15:26Z"

    def test_converts_non_utc_timezone(self):
        """Should convert non-UTC timezones to UTC."""
        pst = timezone(timedelta(hours=-8))
        dt = datetime(2026, 3, 22, 9, 15, 26, tzinfo=pst)
        result = _hugo_date_string_utc(dt)
        assert result == "2026-03-22T17:15:26Z"


# ---------------------------------------------------------------------------
# TESTS: _score_to_bar
# ---------------------------------------------------------------------------


class TestScoreToBar:
    """
    Tests for the visual score bar used in GitHub comments.
    Converts 0-10 score to a text bar like [|||||||...]
    """

    def test_score_10_is_all_filled(self):
        assert _score_to_bar(10.0) == "[||||||||||]"

    def test_score_0_is_all_empty(self):
        assert _score_to_bar(0.0) == "[..........]"

    def test_score_7_point_5_rounds_to_8(self):
        """7.5 should round to 8 filled bars."""
        result = _score_to_bar(7.5)
        assert result == "[||||||||..]"

    def test_score_6_is_six_filled(self):
        """6.0 (acceptance threshold) should show 6 filled bars."""
        result = _score_to_bar(6.0)
        assert result == "[||||||....]"


# ---------------------------------------------------------------------------
# TESTS: _format_review_comment
# ---------------------------------------------------------------------------


class TestFormatReviewComment:
    """
    Tests for the markdown comment formatter that presents the review
    to the submitter on the GitHub Issue.
    """

    def test_accepted_review_format(self):
        """Accepted review should include all sections."""
        comment = _format_review_comment(
            review=SAMPLE_REVIEW_SUCCESS["review"],
            grounding=SAMPLE_REVIEW_SUCCESS["grounding_metadata"],
            paper_id="2026-042",
            score=7.5,
            verdict="ACCEPTED",
        )
        assert "ACCEPTED" in comment
        assert "2026-042" in comment
        assert "7.5/10" in comment
        assert "Strengths" in comment
        assert "Weaknesses" in comment
        assert "Novel dataset" in comment

    def test_rejected_review_format(self):
        """Rejected review should also include all sections."""
        comment = _format_review_comment(
            review=SAMPLE_REVIEW_REJECTED["review"],
            grounding=SAMPLE_REVIEW_REJECTED["grounding_metadata"],
            paper_id="2026-043",
            score=3.5,
            verdict="REJECTED",
        )
        assert "REJECTED" in comment
        assert "3.5/10" in comment

    def test_includes_claim_verification_table(self):
        """Should include the claims verification table when claims exist."""
        comment = _format_review_comment(
            review=SAMPLE_REVIEW_SUCCESS["review"],
            grounding=SAMPLE_REVIEW_SUCCESS["grounding_metadata"],
            paper_id="2026-042",
            score=7.5,
            verdict="ACCEPTED",
        )
        assert "Claim Verification" in comment
        assert "GPT-4" in comment

    def test_includes_grounding_sources(self):
        """Should include fact-checking sources from grounding metadata."""
        comment = _format_review_comment(
            review=SAMPLE_REVIEW_SUCCESS["review"],
            grounding=SAMPLE_REVIEW_SUCCESS["grounding_metadata"],
            paper_id="2026-042",
            score=7.5,
            verdict="ACCEPTED",
        )
        assert "Sources Used" in comment
        assert "arxiv.org" in comment


# ---------------------------------------------------------------------------
# TESTS: _format_error_comment
# ---------------------------------------------------------------------------


class TestFormatErrorComment:
    """Tests for the error comment formatter."""

    def test_includes_error_message(self):
        """Error comment should include the error message."""
        comment = _format_error_comment("API rate limit exceeded", "2026-042")
        assert "Error" in comment
        assert "API rate limit exceeded" in comment
        assert "2026-042" in comment

    def test_mentions_retry(self):
        """Error comment should mention the issue will be retried."""
        comment = _format_error_comment("Some error", "2026-042")
        assert "retry" in comment.lower() or "retried" in comment.lower()


# ---------------------------------------------------------------------------
# TESTS: _build_article_md
# ---------------------------------------------------------------------------


class TestBuildArticleMd:
    """
    Tests for article markdown generation. The output is a Hugo-compatible
    file with YAML frontmatter that maps to template variables.
    """

    def test_includes_frontmatter_delimiters(self):
        """Article should start with --- and have a closing ---."""
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        content = _build_article_md(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        assert content.startswith("---\n")
        # Should have two --- delimiters
        assert content.count("---") >= 2

    def test_includes_title_in_frontmatter(self):
        """Title should appear in the frontmatter."""
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        content = _build_article_md(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        assert "Testing LLM Accuracy" in content

    def test_includes_score_and_verdict(self):
        """
        Score and verdict must be in frontmatter — this was a bug fix from
        Feb 2026 where they were missing, causing "?" on the published site.
        """
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        content = _build_article_md(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        assert "score: 7.5" in content
        assert "ACCEPTED" in content

    def test_date_is_not_multiline_yaml(self):
        """
        Date must NOT use YAML pipe (|) syntax — this was the March 2026
        bug where colons in ISO dates triggered multiline treatment.
        """
        now = datetime(2026, 3, 22, 17, 15, 26, tzinfo=timezone.utc)
        content = _build_article_md(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        # The date should be a single line, not split with |
        lines = content.split("\n")
        date_lines = [l for l in lines if l.startswith("date:")]
        assert len(date_lines) == 1
        assert "|\n" not in date_lines[0]

    def test_multiline_abstract_uses_pipe_syntax(self):
        """Abstracts with newlines should use YAML pipe (|) syntax."""
        parsed_with_multiline = {**SAMPLE_PARSED, "abstract": "Line one.\nLine two.\nLine three."}
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        content = _build_article_md(parsed_with_multiline, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        assert "abstract: |\n" in content

    def test_includes_article_body(self):
        """The article body should appear after the frontmatter."""
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        content = _build_article_md(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        assert "Article body text here." in content

    def test_numeric_values_not_quoted(self):
        """Numbers like score should not be YAML-quoted (Hugo reads them as numbers)."""
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        content = _build_article_md(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now)
        # Should be "score: 7.5" not "score: \"7.5\""
        assert 'score: 7.5' in content


# ---------------------------------------------------------------------------
# TESTS: _build_manifest
# ---------------------------------------------------------------------------


class TestBuildManifest:
    """Tests for manifest.json generation."""

    def test_includes_all_required_fields(self):
        """Manifest should include all fields used by the pipeline and website."""
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        manifest = _build_manifest(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now, SAMPLE_NOVELTY)
        assert manifest["paper_id"] == "2026-042"
        assert manifest["title"] == "Testing LLM Accuracy in Code Review"
        assert manifest["score"] == 7.5
        assert manifest["verdict"] == "ACCEPTED"
        assert manifest["status"] == "current"

    def test_valid_until_is_6_months_for_tech(self):
        """Technical content should expire in 6 months (180 days)."""
        now = datetime(2026, 3, 22, tzinfo=timezone.utc)
        manifest = _build_manifest(SAMPLE_PARSED, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now, SAMPLE_NOVELTY)
        # Expected: now + 180 days formatted as Z timezone
        expected = (now + timedelta(days=180)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert manifest["valid_until"] == expected

    def test_valid_until_is_12_months_for_humanities(self):
        """Humanities content should expire in 12 months (365 days)."""
        parsed_humanities = {**SAMPLE_PARSED, "category": "humanities/philosophy"}
        now = datetime(2026, 3, 22, tzinfo=timezone.utc)
        manifest = _build_manifest(parsed_humanities, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now, SAMPLE_NOVELTY)
        # Expected: now + 365 days formatted as Z timezone
        expected = (now + timedelta(days=365)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert manifest["valid_until"] == expected

    def test_valid_until_is_12_months_for_social(self):
        """Social science content should also expire in 12 months."""
        parsed_social = {**SAMPLE_PARSED, "category": "social/economics"}
        now = datetime(2026, 3, 22, tzinfo=timezone.utc)
        manifest = _build_manifest(parsed_social, SAMPLE_REVIEW_SUCCESS["review"], SAMPLE_REPO_DATA, "2026-042", now, SAMPLE_NOVELTY)
        # Expected: now + 365 days formatted as Z timezone
        expected = (now + timedelta(days=365)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert manifest["valid_until"] == expected


# ---------------------------------------------------------------------------
# TESTS: _build_index_entry
# ---------------------------------------------------------------------------


class TestBuildIndexEntry:
    """Tests for agent-index.json entry generation."""

    def test_includes_required_fields(self):
        """Index entry should have all fields needed for search and display."""
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        entry = _build_index_entry(
            SAMPLE_PARSED,
            SAMPLE_REVIEW_SUCCESS["review"],
            SAMPLE_REPO_DATA,
            "2026-042",
            now,
            "papers/ai/llm-benchmarks/testing-llm-accuracy-in-code-review/index.md",
            "https://pubroot.com/ai/llm-benchmarks/testing-llm-accuracy-in-code-review/",
        )
        assert entry["id"] == "2026-042"
        assert entry["title"] == "Testing LLM Accuracy in Code Review"
        assert entry["review_score"] == 7.5
        assert entry["article_path"] == (
            "papers/ai/llm-benchmarks/testing-llm-accuracy-in-code-review/index.md"
        )
        assert entry["reader_url"] == (
            "https://pubroot.com/ai/llm-benchmarks/testing-llm-accuracy-in-code-review/"
        )
        assert entry["review_path"] == "reviews/2026-042/review.json"

    def test_truncates_abstract_to_500_chars(self):
        """Abstract in index entry should be capped at 500 chars."""
        parsed_long_abstract = {**SAMPLE_PARSED, "abstract": "A" * 1000}
        now = datetime(2026, 3, 22, 17, 0, 0, tzinfo=timezone.utc)
        entry = _build_index_entry(
            parsed_long_abstract,
            SAMPLE_REVIEW_SUCCESS["review"],
            SAMPLE_REPO_DATA,
            "2026-042",
            now,
            "papers/ai/llm-benchmarks/testing-llm-accuracy-in-code-review/index.md",
            "https://pubroot.com/ai/llm-benchmarks/testing-llm-accuracy-in-code-review/",
        )
        assert len(entry["abstract"]) == 500


# ---------------------------------------------------------------------------
# TESTS: _update_contributors
# ---------------------------------------------------------------------------


class TestUpdateContributors:
    """
    Tests for contributor stats updating. This function manages the
    running average, acceptance rate, and per-category stats.

    SCOUT 11 NOTE: No file locking exists here — concurrent pipeline runs
    could overwrite each other's contributor updates. This is a known
    limitation for Phase 1 where review volume is low.
    """

    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "get_file_content")
    def test_creates_new_contributor_on_first_submission(self, mock_get, mock_update, temp_repo_root):
        """First submission from a new author should create their entry."""
        gh = GitHubAPI("owner", "repo", "token")
        
        # Simulate 404 response so it falls back to local file
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = requests.HTTPError()
        error.response = mock_response
        mock_get.side_effect = error
        
        _update_contributors(
            gh=gh,
            branch="main",
            repo_root=temp_repo_root,
            author="new-user",
            score=7.5,
            accepted=True,
            category="ai/llm-benchmarks",
        )

        # Check what was written via the mock
        mock_update.assert_called_once()
        written_content = mock_update.call_args[1]["content"]
        data = json.loads(written_content)

        assert "new-user" in data["contributors"]
        c = data["contributors"]["new-user"]
        assert c["total_submissions"] == 1
        assert c["accepted"] == 1
        assert c["rejected"] == 0
        assert c["acceptance_rate"] == 1.0
        assert c["average_score"] == 7.5

    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "get_file_content")
    def test_updates_existing_contributor(self, mock_get, mock_update, temp_repo_root):
        """Second submission should update running stats."""
        gh = GitHubAPI("owner", "repo", "token")
        
        # First submission - return empty contributors
        existing_contributors = {"contributors": {}}
        mock_get.return_value = (json.dumps(existing_contributors), "sha123")
        _update_contributors(gh, "main", temp_repo_root, "user-a", 8.0, True, "ai/llm-benchmarks")
        
        # Get the data from the first write
        first_write = json.loads(mock_update.call_args_list[0][1]["content"])
        
        # Second submission - return the result of first write
        mock_get.return_value = (json.dumps(first_write), "sha456")
        _update_contributors(gh, "main", temp_repo_root, "user-a", 4.0, False, "ai/llm-benchmarks")

        # Get the data from the second write
        second_write = json.loads(mock_update.call_args_list[1][1]["content"])
        
        c = second_write["contributors"]["user-a"]
        assert c["total_submissions"] == 2
        assert c["accepted"] == 1
        assert c["rejected"] == 1
        assert c["acceptance_rate"] == 0.5
        # Running average: 8.0, then (8.0 + (4.0-8.0)/2) = 6.0
        assert c["average_score"] == 6.0

    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "get_file_content")
    def test_tracks_per_category_stats(self, mock_get, mock_update, temp_repo_root):
        """Should maintain separate stats per category."""
        gh = GitHubAPI("owner", "repo", "token")
        
        # First submission
        existing_contributors = {"contributors": {}}
        mock_get.return_value = (json.dumps(existing_contributors), "sha123")
        _update_contributors(gh, "main", temp_repo_root, "user-b", 7.0, True, "ai/llm-benchmarks")
        
        # Get the data from the first write
        first_write = json.loads(mock_update.call_args_list[0][1]["content"])
        
        # Second submission with different category
        mock_get.return_value = (json.dumps(first_write), "sha456")
        _update_contributors(gh, "main", temp_repo_root, "user-b", 5.0, False, "debug/runtime-errors")

        # Get the data from the second write
        second_write = json.loads(mock_update.call_args_list[1][1]["content"])
        
        c = second_write["contributors"]["user-b"]
        assert "ai/llm-benchmarks" in c["categories"]
        assert "debug/runtime-errors" in c["categories"]
        assert c["categories"]["ai/llm-benchmarks"]["accepted"] == 1
        assert c["categories"]["debug/runtime-errors"]["accepted"] == 0

    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "get_file_content")
    def test_running_average_formula(self, mock_get, mock_update, temp_repo_root):
        """
        Verify the running average: new_avg = old_avg + (new_score - old_avg) / count.
        Three submissions with scores 6, 8, 10 should average to 8.0.
        """
        gh = GitHubAPI("owner", "repo", "token")
        
        # First submission
        existing_contributors = {"contributors": {}}
        mock_get.return_value = (json.dumps(existing_contributors), "sha1")
        _update_contributors(gh, "main", temp_repo_root, "avg-user", 6.0, True, "ai/llm-benchmarks")
        
        # Second submission
        first_write = json.loads(mock_update.call_args_list[0][1]["content"])
        mock_get.return_value = (json.dumps(first_write), "sha2")
        _update_contributors(gh, "main", temp_repo_root, "avg-user", 8.0, True, "ai/llm-benchmarks")
        
        # Third submission
        second_write = json.loads(mock_update.call_args_list[1][1]["content"])
        mock_get.return_value = (json.dumps(second_write), "sha3")
        _update_contributors(gh, "main", temp_repo_root, "avg-user", 10.0, True, "ai/llm-benchmarks")

        # Get the data from the third write
        third_write = json.loads(mock_update.call_args_list[2][1]["content"])
        
        c = third_write["contributors"]["avg-user"]
        assert c["average_score"] == 8.0
    
    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "get_file_content")
    def test_initializes_flags_for_new_contributor(self, mock_get, mock_update, temp_repo_root):
        """New contributors should have zeroed security flags."""
        gh = GitHubAPI("owner", "repo", "token")
        
        # Simulate 404 response so it falls back to local file
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = requests.HTTPError()
        error.response = mock_response
        mock_get.side_effect = error
        
        _update_contributors(gh, "main", temp_repo_root, "flagless-user", 5.0, False, "ai/llm-benchmarks")

        # Check what was written via the mock
        written_content = mock_update.call_args[1]["content"]
        data = json.loads(written_content)

        flags = data["contributors"]["flagless-user"]["flags"]
        assert flags["prompt_injection_attempts"] == 0
        assert flags["spam_submissions"] == 0
        assert flags["dmca_strikes"] == 0


# ---------------------------------------------------------------------------
# TESTS: GitHubAPI class
# ---------------------------------------------------------------------------


class TestGitHubAPI:
    """
    Tests for the GitHub API wrapper. We mock requests to avoid
    real API calls.
    """

    def test_constructs_base_url(self):
        """Should build correct GitHub API base URL."""
        gh = GitHubAPI("owner", "repo", "token123")
        assert gh.base_url == "https://api.github.com/repos/owner/repo"

    def test_headers_include_token(self):
        """Should include Bearer token in headers."""
        gh = GitHubAPI("owner", "repo", "token123")
        assert gh.headers["Authorization"] == "Bearer token123"

    @patch("stage_6_post_review_and_decide.requests.post")
    def test_post_comment(self, mock_post):
        """Should POST to the issues comments endpoint."""
        mock_post.return_value = MagicMock(status_code=201)
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"id": 1}

        gh = GitHubAPI("owner", "repo", "token")
        gh.post_comment(42, "Great paper!")

        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "/issues/42/comments" in call_url

    @patch("stage_6_post_review_and_decide.requests.patch")
    def test_close_issue(self, mock_patch):
        """Should PATCH the issue to closed state."""
        mock_patch.return_value = MagicMock(status_code=200)
        mock_patch.return_value.raise_for_status = MagicMock()
        mock_patch.return_value.json.return_value = {}

        gh = GitHubAPI("owner", "repo", "token")
        gh.close_issue(42)

        mock_patch.assert_called_once()
        call_data = mock_patch.call_args[1]["json"]
        assert call_data["state"] == "closed"

    @patch("stage_6_post_review_and_decide.requests.get")
    @patch("stage_6_post_review_and_decide.requests.delete")
    @patch("stage_6_post_review_and_decide.requests.post")
    def test_create_branch_handles_existing(self, mock_post, mock_delete, mock_get):
        """
        If the branch already exists (from a failed retry), it should
        delete and recreate it rather than failing with 422.
        """
        # Branch already exists
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"ref": "refs/heads/paper/2026-042"}
        # Delete succeeds
        mock_delete.return_value = MagicMock(status_code=204)
        # Create succeeds
        mock_post.return_value = MagicMock(status_code=201)
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {}

        gh = GitHubAPI("owner", "repo", "token")
        gh.create_branch("paper/2026-042", "abc123sha")

        mock_delete.assert_called_once()  # Old branch deleted
        mock_post.assert_called_once()    # New branch created


# ---------------------------------------------------------------------------
# TESTS: post_review_and_decide (main function)
# ---------------------------------------------------------------------------


class TestPostReviewAndDecide:
    """
    Integration tests for the main decision function. We mock the
    GitHub API to avoid real calls.
    """

    @patch.object(GitHubAPI, "post_comment")
    @patch.object(GitHubAPI, "add_labels")
    def test_error_review_posts_error_comment(self, mock_labels, mock_comment, temp_repo_root):
        """When Stage 5 returned an error, should post error comment."""
        result = post_review_and_decide(
            review_result=SAMPLE_REVIEW_ERROR,
            parsed_submission=SAMPLE_PARSED,
            novelty_results=SAMPLE_NOVELTY,
            repo_data=SAMPLE_REPO_DATA,
            paper_id="2026-042",
            issue_number=42,
            repo_owner="owner",
            repo_name="repo",
            github_token="token",
            repo_root=temp_repo_root,
        )

        assert result["action_taken"] == "error"
        assert result["success"] is False
        mock_comment.assert_called_once()
        mock_labels.assert_called_once_with(42, ["review-error"])

    @patch.object(GitHubAPI, "post_comment")
    @patch.object(GitHubAPI, "add_labels")
    @patch.object(GitHubAPI, "close_issue")
    def test_rejected_review_closes_issue(self, mock_close, mock_labels, mock_comment, temp_repo_root):
        """Rejected submissions should be labeled and issue closed."""
        result = post_review_and_decide(
            review_result=SAMPLE_REVIEW_REJECTED,
            parsed_submission=SAMPLE_PARSED,
            novelty_results=SAMPLE_NOVELTY,
            repo_data=SAMPLE_REPO_DATA,
            paper_id="2026-043",
            issue_number=43,
            repo_owner="owner",
            repo_name="repo",
            github_token="token",
            repo_root=temp_repo_root,
        )

        assert result["action_taken"] == "rejected"
        assert result["success"] is True
        mock_close.assert_called_once_with(43)

    @patch.object(GitHubAPI, "post_comment")
    @patch.object(GitHubAPI, "add_labels")
    @patch.object(GitHubAPI, "close_issue")
    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    def test_rejected_updates_contributor_stats(self, mock_update, mock_get, mock_close, mock_labels, mock_comment, temp_repo_root):
        """Rejected submissions should still update contributor stats."""
        # Simulate 404 response so _update_contributors falls back to local file
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = requests.HTTPError()
        error.response = mock_response
        mock_get.side_effect = error
        
        post_review_and_decide(
            review_result=SAMPLE_REVIEW_REJECTED,
            parsed_submission=SAMPLE_PARSED,
            novelty_results=SAMPLE_NOVELTY,
            repo_data=SAMPLE_REPO_DATA,
            paper_id="2026-043",
            issue_number=43,
            repo_owner="owner",
            repo_name="repo",
            github_token="token",
            repo_root=temp_repo_root,
        )
    
        # Check what was written via the mock
        mock_update.assert_called_once()
        written_content = mock_update.call_args[1]["content"]
        data = json.loads(written_content)

        assert "test-user" in data["contributors"]
        assert data["contributors"]["test-user"]["rejected"] == 1


# ---------------------------------------------------------------------------
# TESTS: Response check bug fixes (e.response is not None)
# ---------------------------------------------------------------------------


class TestResponseCheckFixes:
    """
    Tests for the bug fix where `e.response and e.response.status_code == 404`
    was changed to `e.response is not None and e.response.status_code == 404`.
    
    The bug: requests.Response is falsy for 4xx responses, so the old check
    failed to match 404s when response was truthy but had status_code 404.
    """
    
    @patch.object(GitHubAPI, "get_file_content")
    def test_update_agent_index_handles_404_correctly(self, mock_get, temp_repo_root):
        """
        When GitHub API returns 404 for agent-index.json, should fall back
        to local checkout. Tests the fix for `e.response is not None`.
        """
        # Simulate a 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = requests.HTTPError()
        error.response = mock_response
        mock_get.side_effect = error
        
        # Create a local agent-index.json for fallback
        with open(os.path.join(temp_repo_root, "agent-index.json"), "w") as f:
            json.dump(EMPTY_AGENT_INDEX, f)
        
        # This should not raise, should fall back to local file
        from stage_6_post_review_and_decide import _update_agent_index
        gh = GitHubAPI("owner", "repo", "token")
        
        # Mock create_or_update_file_with_sha to avoid actual API call
        with patch.object(gh, "create_or_update_file_with_sha"):
            _update_agent_index(
                gh=gh,
                branch="main",
                repo_root=temp_repo_root,
                new_entry={"id": "2026-001", "published_date": "2026-01-01T00:00:00Z"},
            )
    
    @patch.object(GitHubAPI, "get_file_content")
    def test_update_contributors_handles_404_correctly(self, mock_get, temp_repo_root):
        """
        When GitHub API returns 404 for contributors.json, should fall back
        to local checkout. Tests the fix for `e.response is not None`.
        """
        # Simulate a 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = requests.HTTPError()
        error.response = mock_response
        mock_get.side_effect = error
        
        # Create a local contributors.json for fallback
        with open(os.path.join(temp_repo_root, "contributors.json"), "w") as f:
            json.dump(EMPTY_CONTRIBUTORS, f)
        
        # This should not raise, should fall back to local file
        from stage_6_post_review_and_decide import _update_contributors
        gh = GitHubAPI("owner", "repo", "token")
        
        # Mock create_or_update_file to avoid actual API call
        with patch.object(gh, "create_or_update_file"):
            _update_contributors(
                gh=gh,
                branch="main",
                repo_root=temp_repo_root,
                author="test-user",
                score=7.0,
                accepted=True,
                category="ai/llm-benchmarks",
            )


# ---------------------------------------------------------------------------
# TESTS: Index generation matches regenerator (Root Cause C fix)
# ---------------------------------------------------------------------------


class TestIndexGenerationMatchesRegenerator:
    """
    Tests that stage 6's index generation produces byte-identical output
    to the regenerator script. This prevents CI failures at the
    'Check indexes match committed versions (fail-closed)' step.
    
    Root Cause C: stage 6 used now() for last_updated (regenerator derives
    from max published_date) and appended entries (regenerator sorts by ID).
    """
    
    @patch.object(GitHubAPI, "create_or_update_file_with_sha")
    @patch.object(GitHubAPI, "get_file_content")
    def test_last_updated_from_max_published_date(self, mock_get, mock_update, temp_repo_root):
        """
        Stage 6 should calculate last_updated from max published_date,
        not from now(), to match the regenerator's output.
        """
        # Create an index with existing papers
        existing_index = {
            "schema_version": "1.0",
            "total_papers": 2,
            "last_updated": "2026-03-20T10:00:00Z",
            "papers": [
                {"id": "2026-001", "published_date": "2026-03-20T10:00:00Z"},
                {"id": "2026-002", "published_date": "2026-03-15T08:30:00Z"},
            ],
        }
        mock_get.return_value = (json.dumps(existing_index), "sha123")
        
        from stage_6_post_review_and_decide import _update_agent_index
        gh = GitHubAPI("owner", "repo", "token")
        
        # Add a new paper with a newer published_date
        new_entry = {
            "id": "2026-003",
            "published_date": "2026-03-22T15:00:00Z",
            "category": "ai/llm-benchmarks",
        }
        
        _update_agent_index(gh, "main", temp_repo_root, new_entry)
        
        # Check what was written
        mock_update.assert_called_once()
        written_content = mock_update.call_args[1]["content"]
        written_data = json.loads(written_content)
        
        # last_updated should be the max published_date (2026-003's date)
        assert written_data["last_updated"] == "2026-03-22T15:00:00Z"
        # Should NOT be datetime.now()
        assert written_data["last_updated"] != datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    @patch.object(GitHubAPI, "create_or_update_file_with_sha")
    @patch.object(GitHubAPI, "get_file_content")
    def test_papers_sorted_by_id(self, mock_get, mock_update, temp_repo_root):
        """
        Stage 6 should sort papers by ID after appending, to match
        the regenerator's sorted output.
        """
        # Create an index with papers in arbitrary order
        existing_index = {
            "schema_version": "1.0",
            "total_papers": 2,
            "last_updated": "2026-03-20T10:00:00Z",
            "papers": [
                {"id": "2026-005", "published_date": "2026-03-20T10:00:00Z"},
                {"id": "2026-001", "published_date": "2026-03-15T08:30:00Z"},
            ],
        }
        mock_get.return_value = (json.dumps(existing_index), "sha123")
        
        from stage_6_post_review_and_decide import _update_agent_index
        gh = GitHubAPI("owner", "repo", "token")
        
        # Add a new paper with an ID that should sort in the middle
        new_entry = {
            "id": "2026-003",
            "published_date": "2026-03-18T12:00:00Z",
            "category": "ai/llm-benchmarks",
        }
        
        _update_agent_index(gh, "main", temp_repo_root, new_entry)
        
        # Check what was written
        mock_update.assert_called_once()
        written_content = mock_update.call_args[1]["content"]
        written_data = json.loads(written_content)
        
        # Papers should be sorted by ID
        paper_ids = [p["id"] for p in written_data["papers"]]
        assert paper_ids == ["2026-001", "2026-003", "2026-005"]
    
    @patch.object(GitHubAPI, "create_or_update_file_with_sha")
    @patch.object(GitHubAPI, "get_file_content")
    def test_priorroot_index_routing(self, mock_get, mock_update, temp_repo_root):
        """
        Papers with category starting with 'prior-art/' should go to
        priorroot-index.json, not agent-index.json.
        """
        # Create both indexes
        agent_index = {
            "schema_version": "1.0",
            "total_papers": 1,
            "last_updated": "2026-03-20T10:00:00Z",
            "papers": [{"id": "2026-001", "published_date": "2026-03-20T10:00:00Z"}],
        }
        priorroot_index = {
            "schema_version": "1.0",
            "total_papers": 0,
            "last_updated": "2026-01-01T00:00:00Z",
            "papers": [],
        }
        
        def get_file_side_effect(filename, branch):
            if filename == "priorroot-index.json":
                return (json.dumps(priorroot_index), "sha456")
            return (json.dumps(agent_index), "sha123")
        
        mock_get.side_effect = get_file_side_effect
        
        from stage_6_post_review_and_decide import _update_agent_index
        gh = GitHubAPI("owner", "repo", "token")
        
        # Add a prior-art paper
        new_entry = {
            "id": "2026-002",
            "published_date": "2026-03-22T15:00:00Z",
            "category": "prior-art/therapeutic-use",
        }
        
        _update_agent_index(gh, "main", temp_repo_root, new_entry)
        
        # Should have called get_file_content with priorroot-index.json
        assert any("priorroot-index.json" in str(call) for call in mock_get.call_args_list)
        
        # Should have written to priorroot-index.json
        mock_update.assert_called_once()
        assert mock_update.call_args[1]["path"] == "priorroot-index.json"

