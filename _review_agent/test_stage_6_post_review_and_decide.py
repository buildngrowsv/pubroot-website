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
from pathlib import Path
from unittest.mock import patch, MagicMock

from stage_6_post_review_and_decide import (
    post_review_and_decide,
    GitHubAPI,
    _format_review_comment,
    _format_error_comment,
    _build_article_md,
    _build_manifest,
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



@pytest.fixture(autouse=True)
def git_data_commit(monkeypatch):
    """
    B23: publication now goes through the Git Data API (blobs, tree, commit, ref)
    and reads retry markers from issue comments. Record what would be committed
    and make any unmocked HTTP call fail loudly instead of reaching api.github.com.
    Returns {"files": {path: content}} for the last committed tree.
    """
    def _no_network(*args, **kwargs):
        raise AssertionError(f"unmocked network call in test: {args[1:3]}")
    monkeypatch.setattr(requests.Session, "request", _no_network)
    blobs, last = {}, {"files": {}}
    def _create_blob(self, content):
        sha = f"blob-{len(blobs)}"
        blobs[sha] = content
        return sha
    def _create_tree(self, base_tree_sha, tree_items):
        last["files"] = {item["path"]: blobs[item["sha"]] for item in tree_items}
        return "tree-sha"
    monkeypatch.setattr(GitHubAPI, "get_issue_comments", lambda self, n: [])
    monkeypatch.setattr(GitHubAPI, "get_ref_sha", lambda self, ref: "parent-sha")
    monkeypatch.setattr(GitHubAPI, "get_commit", lambda self, sha: {"tree": {"sha": "base-tree"}})
    monkeypatch.setattr(GitHubAPI, "create_blob", _create_blob)
    monkeypatch.setattr(GitHubAPI, "create_tree", _create_tree)
    monkeypatch.setattr(GitHubAPI, "create_commit", lambda self, msg, tree, parent: "commit-sha")
    monkeypatch.setattr(GitHubAPI, "update_ref", lambda self, ref, sha, force=False: None)
    monkeypatch.setattr("time.sleep", lambda s: None)
    return last


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
# TESTS: Index entry building (moved to scripts/test_index_golden.py)
# ---------------------------------------------------------------------------
# NOTE (Bug B22 fix - Oct 2026): The index entry building logic has been moved
# to the shared index_builder module and is now tested by test_index_golden.py.
# Stage 6 now calls build_agent_index() and build_priorroot_index() directly
# to ensure byte-identical output with the regenerator script.


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
        git_data_commit,
    ):
        """
        Test the full accepted paper workflow when contributors.json is fetched
        from the GitHub API (the normal happy path). This ensures contributors_path
        is never referenced when the API fetch succeeds, preventing the UnboundLocalError.
        
        FIX (Bug B20): This test now handles the publish verification that checks
        path_exists and index content after files are written.
        """
        # Setup: Mock GitHub API responses for a successful publish
        mock_get_sha.return_value = "abc123sha"
        
        # FIX (Bug B20): path_exists is called multiple times:
        # 1. Initial check: paper doesn't exist yet (return False to trigger publish)
        # 2. Verification check: paper exists after write (return True to pass verification)
        path_exists_calls = []
        def path_exists_side_effect(path, ref="main"):
            path_exists_calls.append((path, ref))
            # Return False for initial existence checks, True for verification checks
            if len(path_exists_calls) <= 2:
                return False  # Initial checks for idempotent retry
            return True  # Verification checks after publish
        mock_path_exists.side_effect = path_exists_side_effect
        
        # Mock get_file_content to return fresh contributors.json, agent-index.json, and priorroot-index.json
        # This is the key: when this succeeds, contributors_path should NEVER be used
        # FIX (Bug B20): Also handle verification reads of agent-index.json with the paper
        # NOTE (Bug B22 fix): Stage 6 now fetches both index files when updating
        def get_file_side_effect(path, branch="main"):
            if path in git_data_commit["files"]:
                # Verification reads what the Git Data API commit actually wrote.
                return git_data_commit["files"][path], "committed-sha"
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
                # FIX (Bug B20): Return index WITH the paper for verification reads
                index_data = {
                    "schema_version": "1.0",
                    "api_version": "1.0",
                    "description": "Test index",
                    "search_endpoint": None,
                    "total_papers": 1,
                    "last_updated": "2026-01-01T00:00:00Z",
                    "papers": [],  # live index before publish; the commit must add 2026-042
                }
                return json.dumps(index_data), "index_sha_456"
            elif path == "priorroot-index.json":
                index_data = {
                    "schema_version": "1.0",
                    "api_version": "1.0",
                    "description": "Test priorroot index",
                    "search_endpoint": None,
                    "total_papers": 0,
                    "last_updated": "2026-01-01T00:00:00Z",
                    "papers": [],
                }
                return json.dumps(index_data), "priorroot_sha_789"
            else:
                # Return a proper 404 error for unknown paths
                mock_response = MagicMock()
                mock_response.status_code = 404
                error = requests.HTTPError()
                error.response = mock_response
                raise error
        
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
# NOTE (Bug B22 fix - Oct 2026):
# Index generation tests have been moved to scripts/test_index_golden.py
# ---------------------------------------------------------------------------
# The test_index_golden.py suite tests the shared index_builder module used by
# both stage 6 and the regenerator. It covers:
# - Byte-identity between stage 6 and regenerator for both index files
# - last_updated calculation from max published_date
# - Paper sorting by ID
# - Prior-art routing to priorroot-index.json
# - Archived paper exclusion
# - Stale checkout handling (papers in live index but not in local checkout)
# - Optimistic locking retry logic
#
# The tests above focus on the stage 6 workflow integration and API mocking.


# ---------------------------------------------------------------------------
# TESTS: Secret Scrubbing in Index Entries (Round 2 Blocker)
# ---------------------------------------------------------------------------


class TestSecretScrubbingInIndexEntries:
    """
    Tests for the Round 2 blocker fix: index entries must be built from
    scrubbed strings so that a fake ghp_ token in the abstract results in
    [REDACTED_SECRET] in agent-index.json, matching the regenerator.
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
    def test_fake_token_in_abstract_is_scrubbed_in_index(
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
        git_data_commit,
    ):
        """
        BLOCKER TEST: A fake ghp_ token in the abstract must be scrubbed to
        [REDACTED_SECRET] in the uploaded agent-index.json, matching what the
        regenerator would produce from the committed files.
        """
        # Setup: Create a parsed submission with a fake token in the abstract
        parsed_with_token = {**SAMPLE_PARSED}
        parsed_with_token["abstract"] = "This research used API key ghp_1234567890abcdefghijklmnopqrstuvwxyz for testing."
        
        # Setup: Mock GitHub API responses
        mock_get_sha.return_value = "abc123sha"
        
        # path_exists returns False initially (no collision), True for verification
        path_exists_calls = []
        def path_exists_side_effect(path, ref="main"):
            path_exists_calls.append((path, ref))
            if len(path_exists_calls) <= 2:
                return False
            return True
        mock_path_exists.side_effect = path_exists_side_effect
        
        # Mock get_file_content to return empty indexes
        def get_file_side_effect(path, branch="main"):
            if path == "contributors.json":
                return json.dumps(EMPTY_CONTRIBUTORS), "contributors_sha_123"
            elif path == "agent-index.json":
                # Return index with the scrubbed paper for verification
                index_data = {
                    "schema_version": "1.0",
                    "api_version": "1.0",
                    "description": "Test index",
                    "search_endpoint": None,
                    "total_papers": 1,
                    "last_updated": "2026-01-01T00:00:00Z",
                    "papers": [
                        {"id": "2026-999", "title": "Test Paper"}
                    ],
                }
                return json.dumps(index_data), "index_sha_456"
            elif path == "priorroot-index.json":
                index_data = {
                    "schema_version": "1.0",
                    "api_version": "1.0",
                    "description": "Test priorroot index",
                    "search_endpoint": None,
                    "total_papers": 0,
                    "last_updated": "2026-01-01T00:00:00Z",
                    "papers": [],
                }
                return json.dumps(index_data), "priorroot_sha_789"
            else:
                mock_response = MagicMock()
                mock_response.status_code = 404
                error = requests.HTTPError()
                error.response = mock_response
                raise error
        
        mock_get_file.side_effect = get_file_side_effect
        mock_create_pr.return_value = 999
        
        # Execute: Call post_review_and_decide with the token-containing submission
        result = post_review_and_decide(
            review_result=SAMPLE_REVIEW_SUCCESS,
            parsed_submission=parsed_with_token,
            novelty_results=SAMPLE_NOVELTY,
            repo_data=SAMPLE_REPO_DATA,
            paper_id="2026-999",
            issue_number=999,
            repo_owner="pubroot",
            repo_name="pubroot",
            github_token="test_token",
            repo_root=temp_repo_root,
        )
        
        # Verify: The workflow completed successfully
        assert result["success"] is True
        assert result["action_taken"] == "accepted"
        
        # Verify: agent-index.json was updated with a SCRUBBED entry
        # Find the call that updated agent-index.json
        # B23: agent-index.json is committed in the same Git Data API commit as the paper
        assert "agent-index.json" in git_data_commit["files"]
        index_content = git_data_commit["files"]["agent-index.json"]
        index_data = json.loads(index_content)
        
        # Find the paper entry
        paper_entries = [p for p in index_data["papers"] if p["id"] == "2026-999"]
        assert len(paper_entries) == 1
        paper_entry = paper_entries[0]
        
        # CRITICAL ASSERTION: The token must be redacted in the index
        assert "ghp_" not in paper_entry["abstract"]
        assert "[REDACTED_SECRET]" in paper_entry["abstract"]
        assert "This research used API key [REDACTED_SECRET] for testing." in paper_entry["abstract"]


# ---------------------------------------------------------------------------
# TESTS: Stateful Fake GitHub API for Index Update Tests (Round 2 Blocker)
# ---------------------------------------------------------------------------


class FakeGitHubContentsAPI:
    """
    Stateful fake GitHub contents API that tracks file contents and SHAs,
    and returns 409 on stale SHA writes (optimistic locking).
    """
    
    def __init__(self):
        # Map of path -> {"content": bytes, "sha": str}
        self.files = {}
        self._sha_counter = 1000
    
    def _next_sha(self):
        sha = f"fake_sha_{self._sha_counter}"
        self._sha_counter += 1
        return sha
    
    def get_file_content(self, path: str, branch: str = "main"):
        """Get file content and SHA. Raises 404 if not found."""
        if path not in self.files:
            mock_response = MagicMock()
            mock_response.status_code = 404
            error = requests.HTTPError()
            error.response = mock_response
            raise error
        
        file_data = self.files[path]
        return file_data["content"], file_data["sha"]
    
    def create_or_update_file_with_sha(self, path: str, content: str, message: str, branch: str, sha: str | None):
        """
        Create or update file. Returns 409 if the provided SHA doesn't match the current SHA
        (simulates optimistic locking conflict).
        """
        if path in self.files:
            # File exists - check SHA
            current_sha = self.files[path]["sha"]
            if sha != current_sha:
                # Stale SHA - return 409 Conflict
                mock_response = MagicMock()
                mock_response.status_code = 409
                error = requests.HTTPError()
                error.response = mock_response
                raise error
        
        # Update the file with new content and SHA
        new_sha = self._next_sha()
        self.files[path] = {"content": content, "sha": new_sha}
        return {"sha": new_sha}
    
    def set_file(self, path: str, content: str):
        """Helper to set initial file state."""
        self.files[path] = {"content": content, "sha": self._next_sha()}


class TestIndexUpdateWithStatefulAPI:
    """
    Tests for index update logic using a stateful fake GitHub API.
    These tests cover the scenarios from the Round 2 review.
    """
    
    def test_paper_only_via_api_not_in_checkout(self, temp_repo_root):
        """
        BLOCKER TEST (a): Paper present only via the API, not in the checkout.
        Both uploaded indexes must be byte-identical to what the regenerator
        would produce from the committed files.
        """
        # Setup: Create a fake API with an existing paper in agent-index.json
        fake_api = FakeGitHubContentsAPI()
        
        existing_index = {
            "schema_version": "1.0",
            "api_version": "1.0",
            "description": "Test index",
            "search_endpoint": None,
            "total_papers": 1,
            "last_updated": "2026-01-01T00:00:00Z",
            "papers": [
                {
                    "id": "2026-100",
                    "title": "Existing Paper",
                    "author": "existing-author",
                    "category": "ai/test",
                    "abstract": "Existing abstract",
                    "published_date": "2026-01-01T00:00:00Z",
                    "review_score": 7.0,
                    "badge": "text_only",
                    "status": "current",
                    "article_path": "papers/ai/test/existing/index.md",
                    "review_path": "reviews/2026-100/review.json",
                    "reader_url": "https://pubroot.com/ai/test/existing/",
                }
            ],
        }
        
        fake_api.set_file("agent-index.json", json.dumps(existing_index, indent=2) + "\n")
        
        priorroot_index = {
            "schema_version": "1.0",
            "api_version": "1.0",
            "description": "Test priorroot index",
            "search_endpoint": None,
            "total_papers": 0,
            "last_updated": "2026-01-01T00:00:00Z",
            "papers": [],
        }
        
        fake_api.set_file("priorroot-index.json", json.dumps(priorroot_index, indent=2) + "\n")
        
        # Create a GitHubAPI mock that uses our fake API
        gh = GitHubAPI("owner", "repo", "token")
        gh.get_file_content = fake_api.get_file_content
        gh.create_or_update_file_with_sha = fake_api.create_or_update_file_with_sha
        
        # Call _update_indexes to add a new paper
        from stage_6_post_review_and_decide import _update_indexes
        
        new_paper_data = {
            "title": "New Paper",
            "author": "new-author",
            "category": "ai/test",
            "abstract": "New abstract",
            "supporting_repo": None,
            "ai_tooling_attribution": None,
        }
        
        review = {"score": 8.0}
        repo_data = {"badge_type": "text_only"}
        now = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
        paths = {
            "article_index_path": "papers/ai/test/new/index.md",
            "reader_url": "https://pubroot.com/ai/test/new/",
        }
        
        _update_indexes(gh, "main", "2026-200", new_paper_data, review, repo_data, now, paths)
        
        # Verify: Both indexes were updated
        assert "agent-index.json" in fake_api.files
        assert "priorroot-index.json" in fake_api.files
        
        # Verify: agent-index.json contains both papers
        updated_index = json.loads(fake_api.files["agent-index.json"]["content"])
        assert updated_index["total_papers"] == 2
        paper_ids = [p["id"] for p in updated_index["papers"]]
        assert "2026-100" in paper_ids
        assert "2026-200" in paper_ids
    
    def test_conflict_on_every_attempt_triggers_publish_failed(self, temp_repo_root):
        """
        BLOCKER TEST (d): Conflict on every attempt should cause the issue to be
        labeled publish-failed, not accepted/closed.
        """
        # Setup: Create a fake API that always returns 409
        fake_api = FakeGitHubContentsAPI()
        
        index = {
            "schema_version": "1.0",
            "api_version": "1.0",
            "description": "Test index",
            "search_endpoint": None,
            "total_papers": 0,
            "last_updated": "2026-01-01T00:00:00Z",
            "papers": [],
        }
        
        fake_api.set_file("agent-index.json", json.dumps(index, indent=2) + "\n")
        fake_api.set_file("priorroot-index.json", json.dumps(index, indent=2) + "\n")
        
        # Make the API always return 409 by changing the SHA after every read
        original_get = fake_api.get_file_content
        def get_with_sha_change(path, branch="main"):
            content, sha = original_get(path, branch)
            # Change the SHA so the next write will conflict
            fake_api.files[path]["sha"] = fake_api._next_sha()
            return content, sha
        
        fake_api.get_file_content = get_with_sha_change
        
        # Create a GitHubAPI mock
        gh = GitHubAPI("owner", "repo", "token")
        gh.get_file_content = fake_api.get_file_content
        gh.create_or_update_file_with_sha = fake_api.create_or_update_file_with_sha
        
        # Call _update_indexes and expect it to raise after max retries
        from stage_6_post_review_and_decide import _update_indexes
        
        new_paper_data = {
            "title": "New Paper",
            "author": "new-author",
            "category": "ai/test",
            "abstract": "New abstract",
            "supporting_repo": None,
            "ai_tooling_attribution": None,
        }
        
        review = {"score": 8.0}
        repo_data = {"badge_type": "text_only"}
        now = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
        paths = {
            "article_index_path": "papers/ai/test/new/index.md",
            "reader_url": "https://pubroot.com/ai/test/new/",
        }
        
        # Patch time.sleep to avoid waiting
        import time
        original_sleep = time.sleep
        time.sleep = lambda x: None
        
        try:
            with pytest.raises(Exception) as excinfo:
                _update_indexes(gh, "main", "2026-300", new_paper_data, review, repo_data, now, paths)
            
            # Verify: The exception message mentions conflicts and max retries
            assert "failed after 3 attempts" in str(excinfo.value).lower()
            assert "conflict" in str(excinfo.value).lower()
        finally:
            time.sleep = original_sleep
    
    def test_write_lands_between_read_and_upload_retries_successfully(self, temp_repo_root):
        """
        BLOCKER TEST (c): Another write lands between read and upload. Should
        return 409, refetch, and keep both papers.
        """
        # Setup: Create a fake API
        fake_api = FakeGitHubContentsAPI()
        
        index = {
            "schema_version": "1.0",
            "api_version": "1.0",
            "description": "Test index",
            "search_endpoint": None,
            "total_papers": 1,
            "last_updated": "2026-01-01T00:00:00Z",
            "papers": [
                {
                    "id": "2026-100",
                    "title": "Existing Paper",
                    "author": "existing-author",
                    "category": "ai/test",
                    "abstract": "Existing abstract",
                    "published_date": "2026-01-01T00:00:00Z",
                    "review_score": 7.0,
                    "badge": "text_only",
                    "status": "current",
                    "article_path": "papers/ai/test/existing/index.md",
                    "review_path": "reviews/2026-100/review.json",
                    "reader_url": "https://pubroot.com/ai/test/existing/",
                }
            ],
        }
        
        fake_api.set_file("agent-index.json", json.dumps(index, indent=2) + "\n")
        fake_api.set_file("priorroot-index.json", json.dumps(index, indent=2) + "\n")
        
        # Make the first write fail (simulating concurrent write), then succeed
        write_attempts = []
        original_write = fake_api.create_or_update_file_with_sha
        
        def write_with_conflict_on_first_attempt(path, content, message, branch, sha):
            write_attempts.append(path)
            if len([a for a in write_attempts if a == path]) == 1:
                # First write to this path - inject a concurrent update
                # Simulate another process adding paper 2026-150
                if path == "agent-index.json":
                    current_index = json.loads(fake_api.files[path]["content"])
                    current_index["papers"].append({
                        "id": "2026-150",
                        "title": "Concurrent Paper",
                        "author": "concurrent-author",
                        "category": "ai/test",
                        "abstract": "Concurrent abstract",
                        "published_date": "2026-01-15T00:00:00Z",
                        "review_score": 6.5,
                        "badge": "text_only",
                        "status": "current",
                        "article_path": "papers/ai/test/concurrent/index.md",
                        "review_path": "reviews/2026-150/review.json",
                        "reader_url": "https://pubroot.com/ai/test/concurrent/",
                    })
                    current_index["total_papers"] = 2
                    fake_api.files[path] = {
                        "content": json.dumps(current_index, indent=2) + "\n",
                        "sha": fake_api._next_sha()
                    }
                
                # Return 409 to trigger retry
                mock_response = MagicMock()
                mock_response.status_code = 409
                error = requests.HTTPError()
                error.response = mock_response
                raise error
            else:
                # Second attempt - use original write
                return original_write(path, content, message, branch, sha)
        
        fake_api.create_or_update_file_with_sha = write_with_conflict_on_first_attempt
        
        # Create a GitHubAPI mock
        gh = GitHubAPI("owner", "repo", "token")
        gh.get_file_content = fake_api.get_file_content
        gh.create_or_update_file_with_sha = fake_api.create_or_update_file_with_sha
        
        # Call _update_indexes to add paper 2026-200
        from stage_6_post_review_and_decide import _update_indexes
        
        new_paper_data = {
            "title": "New Paper",
            "author": "new-author",
            "category": "ai/test",
            "abstract": "New abstract",
            "supporting_repo": None,
            "ai_tooling_attribution": None,
        }
        
        review = {"score": 8.0}
        repo_data = {"badge_type": "text_only"}
        now = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
        paths = {
            "article_index_path": "papers/ai/test/new/index.md",
            "reader_url": "https://pubroot.com/ai/test/new/",
        }
        
        # Patch time.sleep to avoid waiting
        import time
        original_sleep = time.sleep
        time.sleep = lambda x: None
        
        try:
            _update_indexes(gh, "main", "2026-200", new_paper_data, review, repo_data, now, paths)
            
            # Verify: Both papers are in the final index (concurrent + new)
            final_index = json.loads(fake_api.files["agent-index.json"]["content"])
            paper_ids = [p["id"] for p in final_index["papers"]]
            
            # Should have all three: original (2026-100), concurrent (2026-150), and new (2026-200)
            assert "2026-100" in paper_ids
            assert "2026-150" in paper_ids
            assert "2026-200" in paper_ids
            assert final_index["total_papers"] == 3
        finally:
            time.sleep = original_sleep
    
    def test_publish_does_not_readd_archived_paper(self, temp_repo_root):
        """
        Test (d): Verify that publishing a new paper does not re-add archived papers.
        
        This test seeds the API with the committed indexes (which exclude 2026-024),
        publishes a new paper 2026-900, and verifies:
        - 2026-024 remains absent
        - 2026-018 and 2026-900 are present
        - total_papers is committed_total + 1
        - The uploaded index contains only the 2026-900 entry plus committed entries
        """
        # Load the real committed indexes
        repo_root = Path(__file__).resolve().parents[1]
        committed_agent_index = json.loads((repo_root / "agent-index.json").read_text(encoding="utf-8"))
        committed_priorroot_index = json.loads((repo_root / "priorroot-index.json").read_text(encoding="utf-8"))
        
        committed_total = committed_agent_index["total_papers"]
        
        # Verify 2026-024 is not in the committed index
        committed_ids = [p["id"] for p in committed_agent_index["papers"]]
        assert "2026-024" not in committed_ids, "2026-024 must be excluded from committed index"
        assert "2026-018" in committed_ids, "2026-018 must be in committed index"
        
        # Setup: Create a fake API seeded with committed indexes
        fake_api = FakeGitHubContentsAPI()
        fake_api.set_file("agent-index.json", json.dumps(committed_agent_index, indent=2) + "\n")
        fake_api.set_file("priorroot-index.json", json.dumps(committed_priorroot_index, indent=2) + "\n")
        
        # Create a GitHubAPI mock
        gh = GitHubAPI("owner", "repo", "token")
        gh.get_file_content = fake_api.get_file_content
        gh.create_or_update_file_with_sha = fake_api.create_or_update_file_with_sha
        
        # Call _update_indexes to add paper 2026-900
        from stage_6_post_review_and_decide import _update_indexes
        
        new_paper_data = {
            "title": "Test Paper 900",
            "author": "test-author",
            "category": "ai/test",
            "abstract": "Test abstract for paper 900",
            "supporting_repo": None,
            "ai_tooling_attribution": None,
        }
        
        review = {"score": 7.5}
        repo_data = {"badge_type": "text_only"}
        now = datetime(2026, 10, 30, 15, 0, 0, tzinfo=timezone.utc)
        paths = {
            "article_index_path": "papers/ai/test/test-paper-900/index.md",
            "reader_url": "https://pubroot.com/ai/test/test-paper-900/",
        }
        
        # Patch time.sleep to avoid waiting
        import time
        original_sleep = time.sleep
        time.sleep = lambda x: None
        
        try:
            _update_indexes(gh, "main", "2026-900", new_paper_data, review, repo_data, now, paths)
            
            # Verify: 2026-024 is still absent, 2026-018 and 2026-900 are present
            final_index = json.loads(fake_api.files["agent-index.json"]["content"])
            final_paper_ids = [p["id"] for p in final_index["papers"]]
            
            assert "2026-024" not in final_paper_ids, "2026-024 must remain excluded"
            assert "2026-018" in final_paper_ids, "2026-018 must be present"
            assert "2026-900" in final_paper_ids, "New paper 2026-900 must be present"
            
            # Verify total is committed_total + 1
            assert final_index["total_papers"] == committed_total + 1
            
            # Verify the upload contains exactly the committed entries plus 2026-900
            # (no re-added archived papers)
            expected_ids = set(committed_ids) | {"2026-900"}
            actual_ids = set(final_paper_ids)
            assert actual_ids == expected_ids, \
                f"Index should contain committed papers + 2026-900 only. Diff: {actual_ids ^ expected_ids}"
        finally:
            time.sleep = original_sleep


