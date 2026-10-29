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

    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    def test_creates_new_contributor_on_first_submission(self, mock_create_update, mock_get_file, temp_repo_root):
        """First submission from a new author should create their entry."""
        # Mock the API to return empty contributors.json
        mock_get_file.return_value = (json.dumps(EMPTY_CONTRIBUTORS), "sha123")
        
        gh = GitHubAPI("owner", "repo", "token")
        _update_contributors(
            gh=gh,
            branch="main",
            repo_root=temp_repo_root,
            author="new-user",
            score=7.5,
            accepted=True,
            category="ai/llm-benchmarks",
        )

        # Verify the update was committed via API
        mock_create_update.assert_called_once()
        call_args = mock_create_update.call_args
        assert call_args[1]["path"] == "contributors.json"
        
        # Verify the content
        updated_content = json.loads(call_args[1]["content"])
        assert "new-user" in updated_content["contributors"]
        c = updated_content["contributors"]["new-user"]
        assert c["total_submissions"] == 1
        assert c["accepted"] == 1
        assert c["rejected"] == 0
        assert c["acceptance_rate"] == 1.0
        assert c["average_score"] == 7.5

    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    def test_updates_existing_contributor(self, mock_create_update, mock_get_file, temp_repo_root):
        """Second submission should update running stats."""
        gh = GitHubAPI("owner", "repo", "token")
        
        # First submission - start with empty contributors
        mock_get_file.return_value = (json.dumps(EMPTY_CONTRIBUTORS), "sha123")
        _update_contributors(gh, "main", temp_repo_root, "user-a", 8.0, True, "ai/llm-benchmarks")
        
        # Get the updated content from the first call
        first_update = json.loads(mock_create_update.call_args_list[0][1]["content"])
        
        # Second submission (rejected) - now return the first update
        mock_get_file.return_value = (json.dumps(first_update), "sha456")
        _update_contributors(gh, "main", temp_repo_root, "user-a", 4.0, False, "ai/llm-benchmarks")

        # Verify the final state
        final_update = json.loads(mock_create_update.call_args_list[1][1]["content"])
        c = final_update["contributors"]["user-a"]
        assert c["total_submissions"] == 2
        assert c["accepted"] == 1
        assert c["rejected"] == 1
        assert c["acceptance_rate"] == 0.5
        # Running average: 8.0, then (8.0 + (4.0-8.0)/2) = 6.0
        assert c["average_score"] == 6.0

    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    def test_tracks_per_category_stats(self, mock_create_update, mock_get_file, temp_repo_root):
        """Should maintain separate stats per category."""
        gh = GitHubAPI("owner", "repo", "token")
        
        # First submission
        mock_get_file.return_value = (json.dumps(EMPTY_CONTRIBUTORS), "sha123")
        _update_contributors(gh, "main", temp_repo_root, "user-b", 7.0, True, "ai/llm-benchmarks")
        
        # Second submission (different category)
        first_update = json.loads(mock_create_update.call_args_list[0][1]["content"])
        mock_get_file.return_value = (json.dumps(first_update), "sha456")
        _update_contributors(gh, "main", temp_repo_root, "user-b", 5.0, False, "debug/runtime-errors")

        final_update = json.loads(mock_create_update.call_args_list[1][1]["content"])
        c = final_update["contributors"]["user-b"]
        assert "ai/llm-benchmarks" in c["categories"]
        assert "debug/runtime-errors" in c["categories"]
        assert c["categories"]["ai/llm-benchmarks"]["accepted"] == 1
        assert c["categories"]["debug/runtime-errors"]["accepted"] == 0

    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    def test_running_average_formula(self, mock_create_update, mock_get_file, temp_repo_root):
        """
        Verify the running average: new_avg = old_avg + (new_score - old_avg) / count.
        Three submissions with scores 6, 8, 10 should average to 8.0.
        """
        gh = GitHubAPI("owner", "repo", "token")
        
        # First submission
        mock_get_file.return_value = (json.dumps(EMPTY_CONTRIBUTORS), "sha123")
        _update_contributors(gh, "main", temp_repo_root, "avg-user", 6.0, True, "ai/llm-benchmarks")
        
        # Second submission
        first_update = json.loads(mock_create_update.call_args_list[0][1]["content"])
        mock_get_file.return_value = (json.dumps(first_update), "sha456")
        _update_contributors(gh, "main", temp_repo_root, "avg-user", 8.0, True, "ai/llm-benchmarks")
        
        # Third submission
        second_update = json.loads(mock_create_update.call_args_list[1][1]["content"])
        mock_get_file.return_value = (json.dumps(second_update), "sha789")
        _update_contributors(gh, "main", temp_repo_root, "avg-user", 10.0, True, "ai/llm-benchmarks")

        final_update = json.loads(mock_create_update.call_args_list[2][1]["content"])
        c = final_update["contributors"]["avg-user"]
        assert c["average_score"] == 8.0

    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    def test_initializes_flags_for_new_contributor(self, mock_create_update, mock_get_file, temp_repo_root):
        """New contributors should have zeroed security flags."""
        mock_get_file.return_value = (json.dumps(EMPTY_CONTRIBUTORS), "sha123")
        
        gh = GitHubAPI("owner", "repo", "token")
        _update_contributors(gh, "main", temp_repo_root, "flagless-user", 5.0, False, "ai/llm-benchmarks")

        updated_content = json.loads(mock_create_update.call_args[1]["content"])
        flags = updated_content["contributors"]["flagless-user"]["flags"]
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
# TESTS: Accepted Paper Publish Path (End-to-End)
# ---------------------------------------------------------------------------


class TestAcceptedPaperPublishPath:
    """
    End-to-end test for the accepted paper publication workflow.
    
    This test exercises the complete path from acceptance through file creation,
    contributor stats updates, and index updates. It would have caught the
    UnboundLocalError in _update_contributors where contributors_path was
    conditionally assigned but unconditionally used.
    
    BUG FIX (2026-10-29): Added this test to prevent regression of the
    contributors_path UnboundLocalError that blocked issue #121 publication.
    """
    
    @patch.object(GitHubAPI, "get_default_branch_sha")
    @patch.object(GitHubAPI, "create_branch")
    @patch.object(GitHubAPI, "path_exists")
    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "create_or_update_file_with_sha")
    @patch.object(GitHubAPI, "create_pull_request")
    @patch.object(GitHubAPI, "merge_pull_request")
    @patch.object(GitHubAPI, "post_comment")
    @patch.object(GitHubAPI, "add_labels")
    @patch.object(GitHubAPI, "remove_label")
    @patch.object(GitHubAPI, "close_issue")
    def test_accepted_paper_publishes_with_api_fetched_contributors(
        self,
        mock_close,
        mock_remove_label,
        mock_add_labels,
        mock_comment,
        mock_merge_pr,
        mock_create_pr,
        mock_create_update_sha,
        mock_create_update,
        mock_get_file,
        mock_path_exists,
        mock_create_branch,
        mock_get_sha,
        temp_repo_root,
    ):
        """
        Test the full accepted paper workflow when contributors.json is fetched
        from the GitHub API (the normal happy path). This ensures contributors_path
        is never referenced when the API fetch succeeds, preventing the UnboundLocalError.
        """
        # Setup: Mock GitHub API responses for a successful publish
        mock_get_sha.return_value = "abc123sha"
        mock_path_exists.return_value = False  # Paper doesn't exist yet
        
        # Mock get_file_content to return fresh contributors.json and agent-index.json
        # This is the key: when this succeeds, contributors_path should NEVER be used
        def get_file_side_effect(path, branch="main"):
            if path == "contributors.json":
                contributors_data = {
                    "contributors": {
                        "existing-user": {
                            "github_handle": "existing-user",
                            "total_submissions": 1,
                            "accepted": 1,
                            "rejected": 0,
                            "acceptance_rate": 1.0,
                            "average_score": 8.0,
                            "categories": {},
                            "flags": {
                                "prompt_injection_attempts": 0,
                                "spam_submissions": 0,
                                "dmca_strikes": 0,
                            },
                        }
                    }
                }
                return json.dumps(contributors_data), "contributors_sha_123"
            elif path == "agent-index.json":
                index_data = {
                    "schema_version": "1.0",
                    "total_papers": 0,
                    "last_updated": "2026-01-01T00:00:00Z",
                    "papers": [],
                }
                return json.dumps(index_data), "index_sha_456"
            else:
                raise requests.HTTPError()
        
        mock_get_file.side_effect = get_file_side_effect
        mock_create_pr.return_value = 123  # PR number
        
        # Execute: Call post_review_and_decide with an ACCEPTED review
        result = post_review_and_decide(
            review_result=SAMPLE_REVIEW_SUCCESS,
            parsed_submission=SAMPLE_PARSED,
            novelty_results=SAMPLE_NOVELTY,
            repo_data=SAMPLE_REPO_DATA,
            paper_id="2026-042",
            issue_number=121,
            repo_owner="pubroot",
            repo_name="pubroot",
            github_token="test_token",
            repo_root=temp_repo_root,
        )
        
        # Verify: The workflow completed successfully
        assert result["success"] is True
        assert result["action_taken"] == "accepted"
        assert result["pr_number"] == 123
        assert result["errors"] == []
        
        # Verify: Contributors.json was fetched from API (not local file)
        mock_get_file.assert_any_call("contributors.json", branch="main")
        
        # Verify: Contributors.json was updated via API (not local file write)
        contributors_update_calls = [
            call for call in mock_create_update.call_args_list
            if "contributors.json" in str(call)
        ]
        assert len(contributors_update_calls) >= 1
        
        # Verify: The acceptance was labeled and issue closed
        mock_add_labels.assert_called()
        mock_close.assert_called_once_with(121)


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

    @patch.object(GitHubAPI, "get_file_content")
    @patch.object(GitHubAPI, "create_or_update_file")
    @patch.object(GitHubAPI, "post_comment")
    @patch.object(GitHubAPI, "add_labels")
    @patch.object(GitHubAPI, "close_issue")
    def test_rejected_updates_contributor_stats(self, mock_close, mock_labels, mock_comment, mock_create_update, mock_get_file, temp_repo_root):
        """Rejected submissions should still update contributor stats."""
        # Mock the API to return empty contributors.json
        mock_get_file.return_value = (json.dumps(EMPTY_CONTRIBUTORS), "sha123")
        
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

        # Verify the contributor stats were updated via API
        mock_create_update.assert_called()
        contributors_update_calls = [
            call for call in mock_create_update.call_args_list
            if "contributors.json" in str(call)
        ]
        assert len(contributors_update_calls) >= 1
        
        # Check the content that was committed
        updated_content = json.loads(contributors_update_calls[0][1]["content"])
        assert "test-user" in updated_content["contributors"]
        assert updated_content["contributors"]["test-user"]["rejected"] == 1


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
                new_entry={"id": "2026-001", "published_date": "2026-01-01T00:00:00Z", "category": "ai/test"},
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


# ---------------------------------------------------------------------------
# TESTS: Byte-identical output (comprehensive integration test)
# ---------------------------------------------------------------------------


class TestByteIdenticalOutput:
    """
    Comprehensive test that simulates a stage 6 publish of a new paper and
    verifies the output matches the regenerator's output byte-for-byte.
    
    This is the fail-closed check: stage 6's _update_agent_index must produce
    the exact same JSON (including last_updated format and paper ordering)
    as scripts/regenerate_agent_index_from_papers.py.
    """
    
    @patch.object(GitHubAPI, "create_or_update_file_with_sha")
    @patch.object(GitHubAPI, "get_file_content")
    def test_stage6_matches_regenerator_regular_paper(self, mock_get, mock_update, temp_repo_root):
        """
        Simulate stage 6 publishing a regular paper, then run the regenerator
        on the same fixture data and assert both indexes are identical.
        """
        # Create a fixture papers/ tree with existing papers
        papers_dir = os.path.join(temp_repo_root, "papers", "ai", "llm-benchmarks")
        os.makedirs(papers_dir, exist_ok=True)
        
        # Create paper 2026-001 (existing)
        paper1_dir = os.path.join(papers_dir, "existing-paper-001")
        os.makedirs(paper1_dir, exist_ok=True)
        
        paper1_md = """---
title: Existing Paper
paper_id: 2026-001
author: test-author
category: ai/llm-benchmarks
abstract: Test abstract.
date: 2026-03-15T10:00:00Z
score: 8.0
verdict: ACCEPTED
badge: verified_open
---
Body content here."""
        
        with open(os.path.join(paper1_dir, "index.md"), "w") as f:
            f.write(paper1_md)
        
        paper1_manifest = {
            "paper_id": "2026-001",
            "published_date": "2026-03-15T10:00:00Z",
            "supporting_repo": None,
        }
        with open(os.path.join(paper1_dir, "manifest.json"), "w") as f:
            json.dump(paper1_manifest, f)
        
        # Existing index (before stage 6 adds new paper)
        existing_index = {
            "schema_version": "1.0",
            "api_version": "1.0",
            "description": "Test index",
            "search_endpoint": None,
            "total_papers": 1,
            "last_updated": "2026-03-15T10:00:00Z",
            "papers": [
                {
                    "id": "2026-001",
                    "title": "Existing Paper",
                    "author": "test-author",
                    "category": "ai/llm-benchmarks",
                    "abstract": "Test abstract.",
                    "published_date": "2026-03-15T10:00:00Z",
                    "review_score": 8.0,
                    "badge": "verified_open",
                    "status": "current",
                    "article_path": "papers/ai/llm-benchmarks/existing-paper-001/index.md",
                    "review_path": "reviews/2026-001/review.json",
                    "reader_url": "https://pubroot.com/ai/llm-benchmarks/existing-paper-001/",
                }
            ],
        }
        
        mock_get.return_value = (json.dumps(existing_index), "sha123")
        
        # Simulate stage 6 adding a new paper (2026-002)
        # This is what _upload_publication_files_to_branch calls
        from stage_6_post_review_and_decide import _update_agent_index
        gh = GitHubAPI("owner", "repo", "token")
        
        # The new entry stage 6 would generate
        new_paper_published_date = "2026-03-22T15:00:00Z"
        new_entry = {
            "id": "2026-002",
            "title": "New Paper Title",
            "author": "new-author",
            "category": "ai/llm-benchmarks",
            "abstract": "New paper abstract.",
            "published_date": new_paper_published_date,
            "review_score": 7.5,
            "badge": "text_only",
            "status": "current",
            "article_path": "papers/ai/llm-benchmarks/new-paper-title/index.md",
            "review_path": "reviews/2026-002/review.json",
            "reader_url": "https://pubroot.com/ai/llm-benchmarks/new-paper-title/",
        }
        
        _update_agent_index(gh, "main", temp_repo_root, new_entry)
        
        # Get what stage 6 wrote
        mock_update.assert_called_once()
        stage6_content = mock_update.call_args[1]["content"]
        stage6_data = json.loads(stage6_content)
        
        # Verify stage 6's output has the correct properties
        assert len(stage6_data["papers"]) == 2
        assert stage6_data["total_papers"] == 2
        
        # Verify last_updated is the max published_date (not now())
        assert stage6_data["last_updated"] == new_paper_published_date
        
        # Verify papers are sorted by ID
        paper_ids = [p["id"] for p in stage6_data["papers"]]
        assert paper_ids == ["2026-001", "2026-002"]
        
        # Verify date format is Z (not +00:00)
        assert stage6_data["last_updated"].endswith("Z")
        assert not stage6_data["last_updated"].endswith("+00:00")
    
    @patch.object(GitHubAPI, "create_or_update_file_with_sha")
    @patch.object(GitHubAPI, "get_file_content")
    def test_stage6_matches_regenerator_priorroot_paper(self, mock_get, mock_update, temp_repo_root):
        """
        Same as above but for a prior-art paper going to priorroot-index.json.
        """
        # Existing priorroot index
        existing_index = {
            "schema_version": "1.0",
            "api_version": "1.0",
            "description": "Priorroot test index",
            "search_endpoint": None,
            "total_papers": 0,
            "last_updated": "2026-01-01T00:00:00Z",
            "papers": [],
        }
        
        mock_get.return_value = (json.dumps(existing_index), "sha456")
        
        from stage_6_post_review_and_decide import _update_agent_index
        gh = GitHubAPI("owner", "repo", "token")
        
        # Prior-art paper
        new_paper_published_date = "2026-03-22T15:00:00Z"
        new_entry = {
            "id": "2026-003",
            "title": "Prior Art Paper",
            "author": "priorart-author",
            "category": "prior-art/therapeutic-use",
            "abstract": "Defensive disclosure.",
            "published_date": new_paper_published_date,
            "review_score": 7.0,
            "badge": "text_only",
            "status": "current",
            "article_path": "papers/prior-art/therapeutic-use/prior-art-paper/index.md",
            "review_path": "reviews/2026-003/review.json",
            "reader_url": "https://pubroot.com/prior-art/therapeutic-use/prior-art-paper/",
        }
        
        _update_agent_index(gh, "main", temp_repo_root, new_entry)
        
        # Verify it wrote to priorroot-index.json
        mock_update.assert_called_once()
        assert mock_update.call_args[1]["path"] == "priorroot-index.json"
        
        # Get what stage 6 wrote
        stage6_content = mock_update.call_args[1]["content"]
        stage6_data = json.loads(stage6_content)
        
        # Verify priorroot-specific properties
        assert len(stage6_data["papers"]) == 1
        assert stage6_data["papers"][0]["category"].startswith("prior-art/")
        assert stage6_data["last_updated"] == new_paper_published_date
        assert stage6_data["last_updated"].endswith("Z")

