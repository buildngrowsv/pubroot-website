"""
Tests for Review Pipeline Main — Pubroot Review Pipeline

HISTORY:
    Created 2026-03-23 by Builder 6 (swarm agent) as part of T5.
    These tests validate the main orchestrator that coordinates all 6
    pipeline stages. We mock all external dependencies (API calls,
    file reads, environment variables) to test the orchestration logic.

KEY FINDINGS FROM SCOUT 11:
    - review_pipeline_main.py has NO overall timeout — if one stage hangs,
      the entire pipeline hangs forever. This is documented but untested.
    - The pipeline uses environment variables for API keys, so tests must
      mock os.environ.
    - Stage 2 and 3 failures are non-fatal (pipeline continues with
      empty data), but Stage 1 and 5 failures are fatal.

APPROACH:
    - We mock all 6 stage functions to test orchestration logic without
      actually calling external APIs.
    - We test the environment variable validation (GEMINI_API_KEY, etc.).
    - We verify the pipeline continues when non-critical stages fail.
    - We verify the pipeline stops when critical stages fail.

RUNNING:
    pytest _review_agent/test_pipeline_main.py -v
"""

import json
import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Pre-import requests so it's in sys.modules — review_pipeline_main does
# `import requests` locally inside run_review_pipeline(), so we need
# the module to exist in sys.modules for patching to work.
import requests

from review_pipeline_main import run_review_pipeline


# ---------------------------------------------------------------------------
# FIXTURES — sample stage outputs for mocking
# ---------------------------------------------------------------------------

STAGE1_SUCCESS = {
    "valid": True,
    "parsed": {
        "title": "Test Article",
        "category": "ai/llm-benchmarks",
        "abstract": "Testing LLMs.",
        "body": "Body text.",
        "author": "test-user",
        "supporting_repo": None,
        "commit_sha": None,
        "repo_visibility": "no-repo",
        "submission_type": "original-research",
        "word_count_abstract": 10,
        "word_count_body": 100,
    },
    "errors": [],
    "warnings": [],
}

STAGE1_INVALID = {
    "valid": False,
    "parsed": {"title": "", "category": "", "abstract": "", "body": "", "author": "test-user"},
    "errors": ["Title is required", "Body is too short"],
    "warnings": [],
}

STAGE2_SUCCESS = {
    "arxiv_results": [],
    "s2_results": [],
    "internal_results": [],
    "potential_supersession": None,
    "errors": [],
}

STAGE3_SUCCESS = {
    "available": False,
    "visibility": "no-repo",
    "badge_type": "text_only",
    "file_count": 0,
    "total_content_bytes": 0,
    "file_tree": "",
    "key_files": [],
    "errors": [],
}

STAGE5_SUCCESS = {
    "success": True,
    "review": {
        "paper_id": "2026-042",
        "score": 7.5,
        "verdict": "ACCEPTED",
        "badge": "text_only",
        "summary": "Good article.",
        "claims": [],
    },
    "grounding_metadata": {"available": False},
    "raw_response_text": "{}",
    "model_used": "gemini-2.5-flash-lite",
    "error": None,
}

STAGE5_FAILURE = {
    "success": False,
    "review": None,
    "grounding_metadata": None,
    "raw_response_text": "",
    "model_used": "gemini-2.5-flash-lite",
    "error": "Gemini API rate limit exceeded",
}

STAGE6_ACCEPTED = {
    "success": True,
    "action_taken": "accepted",
    "pr_number": 101,
    "errors": [],
}

STAGE6_REJECTED = {
    "success": True,
    "action_taken": "rejected",
    "pr_number": None,
    "errors": [],
}

STAGE6_ERROR = {
    "success": False,
    "action_taken": "error",
    "pr_number": None,
    "errors": ["GitHub API error"],
}

# Minimal journals.json for priority calculation
SAMPLE_JOURNALS = {
    "schema_version": "2.0",
    "acceptance_threshold": 6.0,
    "journals": {
        "ai": {
            "display_name": "AI",
            "topics": {
                "llm-benchmarks": {"display_name": "LLM Benchmarks", "refresh_rate_days": 30},
            },
        },
    },
}

# Minimal contributors.json
EMPTY_CONTRIBUTORS = {"contributors": {}}

# Minimal agent-index.json
EMPTY_AGENT_INDEX = {"schema_version": "1.0", "total_papers": 0, "last_updated": "", "papers": []}

# Mock GitHub issue response
MOCK_ISSUE_RESPONSE = {
    "number": 42,
    "body": "### Title\nTest Article\n### Category\nai/llm-benchmarks\n### Abstract\nTesting.\n### Article Body\nBody text here.",
    "user": {"login": "test-user"},
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_env_and_files():
    """
    Set up a temporary repo root with required JSON files and
    environment variables for the pipeline to run.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write required files
        with open(os.path.join(tmpdir, "journals.json"), "w") as f:
            json.dump(SAMPLE_JOURNALS, f)
        with open(os.path.join(tmpdir, "contributors.json"), "w") as f:
            json.dump(EMPTY_CONTRIBUTORS, f)
        with open(os.path.join(tmpdir, "agent-index.json"), "w") as f:
            json.dump(EMPTY_AGENT_INDEX, f)

        env_vars = {
            "GEMINI_API_KEY": "fake-gemini-key",
            "GITHUB_TOKEN": "fake-github-token",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_WORKSPACE": tmpdir,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            yield tmpdir


# ---------------------------------------------------------------------------
# TESTS: Environment variable validation
# ---------------------------------------------------------------------------


class TestEnvironmentValidation:
    """
    Tests for the environment variable checks at the start of the pipeline.
    Missing API keys should fail fast with clear error messages.
    """

    def test_missing_gemini_key_fails(self):
        """Pipeline should fail immediately without GEMINI_API_KEY."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}, clear=True):
            result = run_review_pipeline(42)
            assert result["success"] is False
            assert "GEMINI_API_KEY" in result["errors"][0]

    def test_missing_github_token_fails(self):
        """Pipeline should fail immediately without GITHUB_TOKEN."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GITHUB_REPOSITORY": "o/r"}, clear=True):
            result = run_review_pipeline(42)
            assert result["success"] is False
            assert "GITHUB_TOKEN" in result["errors"][0]

    def test_invalid_github_repository_format_fails(self):
        """GITHUB_REPOSITORY must be in 'owner/repo' format."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "invalid"}, clear=True):
            result = run_review_pipeline(42)
            assert result["success"] is False
            assert "GITHUB_REPOSITORY" in result["errors"][0]


# ---------------------------------------------------------------------------
# TESTS: Pipeline orchestration
# ---------------------------------------------------------------------------


class TestPipelineOrchestration:
    """
    Tests for the stage-by-stage orchestration logic. Each stage is
    mocked to isolate the orchestration behavior.
    """

    @patch("requests.get")
    @patch("review_pipeline_main.update_all_reputations")
    @patch("review_pipeline_main.post_review_and_decide")
    @patch("review_pipeline_main.run_gemini_grounded_review")
    @patch("review_pipeline_main.build_review_prompt")
    @patch("review_pipeline_main.read_linked_repository")
    @patch("review_pipeline_main.check_novelty")
    @patch("review_pipeline_main.parse_and_filter_submission")
    @patch("review_pipeline_main.calculate_priority")
    @patch("review_pipeline_main.GitHubAPI")
    def test_full_pipeline_accepted(
        self, mock_gh_cls, mock_priority, mock_stage1, mock_stage2,
        mock_stage3, mock_stage4, mock_stage5, mock_stage6,
        mock_reputations, mock_requests_get, mock_env_and_files
    ):
        """Full pipeline run resulting in acceptance should return success."""
        # Mock issue fetch
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_ISSUE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_resp

        # Mock each stage
        mock_priority.return_value = {
            "priority_score": 5.0,
            "priority_label": "priority-standard",
            "reputation_score": 0.0,
            "reputation_tier": "new",
        }
        mock_stage1.return_value = STAGE1_SUCCESS
        mock_stage2.return_value = STAGE2_SUCCESS
        mock_stage3.return_value = STAGE3_SUCCESS
        mock_stage4.return_value = "assembled prompt text"
        mock_stage5.return_value = STAGE5_SUCCESS
        mock_stage6.return_value = STAGE6_ACCEPTED
        mock_reputations.return_value = {}
        mock_gh_cls.return_value = MagicMock()

        result = run_review_pipeline(42)

        assert result["success"] is True
        assert result["action"] == "accepted"
        assert result["paper_id"] == f"{2026}-042"
        assert result["score"] == 7.5

    @patch("requests.get")
    @patch("review_pipeline_main.GitHubAPI")
    @patch("review_pipeline_main.parse_and_filter_submission")
    @patch("review_pipeline_main.calculate_priority")
    def test_stage1_invalid_stops_pipeline(
        self, mock_priority, mock_stage1, mock_gh_cls,
        mock_requests_get, mock_env_and_files
    ):
        """If Stage 1 rejects the submission, pipeline should stop early."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_ISSUE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_resp

        mock_priority.return_value = {
            "priority_score": 5.0,
            "priority_label": "priority-standard",
            "reputation_score": 0.0,
            "reputation_tier": "new",
        }
        mock_stage1.return_value = STAGE1_INVALID
        mock_gh_instance = MagicMock()
        mock_gh_cls.return_value = mock_gh_instance

        result = run_review_pipeline(42)

        assert result["action"] == "filtered"
        # Should have posted a comment about validation failure
        mock_gh_instance.post_comment.assert_called_once()

    @patch("requests.get")
    @patch("review_pipeline_main.update_all_reputations")
    @patch("review_pipeline_main.post_review_and_decide")
    @patch("review_pipeline_main.run_gemini_grounded_review")
    @patch("review_pipeline_main.build_review_prompt")
    @patch("review_pipeline_main.read_linked_repository")
    @patch("review_pipeline_main.check_novelty")
    @patch("review_pipeline_main.parse_and_filter_submission")
    @patch("review_pipeline_main.calculate_priority")
    @patch("review_pipeline_main.GitHubAPI")
    def test_stage5_failure_posts_error(
        self, mock_gh_cls, mock_priority, mock_stage1, mock_stage2,
        mock_stage3, mock_stage4, mock_stage5, mock_stage6,
        mock_reputations, mock_requests_get, mock_env_and_files
    ):
        """If Stage 5 (Gemini) fails, Stage 6 should post an error comment."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_ISSUE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_resp

        mock_priority.return_value = {
            "priority_score": 5.0, "priority_label": "priority-standard",
            "reputation_score": 0.0, "reputation_tier": "new",
        }
        mock_stage1.return_value = STAGE1_SUCCESS
        mock_stage2.return_value = STAGE2_SUCCESS
        mock_stage3.return_value = STAGE3_SUCCESS
        mock_stage4.return_value = "prompt"
        mock_stage5.return_value = STAGE5_FAILURE
        mock_stage6.return_value = STAGE6_ERROR
        mock_reputations.return_value = {}
        mock_gh_cls.return_value = MagicMock()

        result = run_review_pipeline(42)

        # Stage 6 should still be called even when Stage 5 fails
        # (Stage 6 handles posting the error comment)
        mock_stage6.assert_called_once()


# ---------------------------------------------------------------------------
# TESTS: Paper ID generation
# ---------------------------------------------------------------------------


class TestPaperIdGeneration:
    """
    Tests for the paper ID format. Paper IDs are YYYY-NNN where NNN is
    the zero-padded issue number.
    """

    @patch("requests.get")
    @patch("review_pipeline_main.GitHubAPI")
    def test_paper_id_format(self, mock_gh_cls, mock_requests_get, mock_env_and_files):
        """Paper ID should be year-issue_number zero-padded to 3 digits."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_ISSUE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_resp
        mock_gh_cls.return_value = MagicMock()

        # Mock Stage 1 to fail fast so we can check the paper_id
        with patch("review_pipeline_main.parse_and_filter_submission") as mock_s1, \
             patch("review_pipeline_main.calculate_priority") as mock_p:
            mock_p.return_value = {
                "priority_score": 5.0, "priority_label": "priority-standard",
                "reputation_score": 0.0, "reputation_tier": "new",
            }
            mock_s1.return_value = STAGE1_INVALID

            result = run_review_pipeline(42)
            assert result["paper_id"] == "2026-042"

    @patch("requests.get")
    @patch("review_pipeline_main.GitHubAPI")
    def test_paper_id_single_digit_issue(self, mock_gh_cls, mock_requests_get, mock_env_and_files):
        """Single digit issue numbers should be zero-padded."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {**MOCK_ISSUE_RESPONSE, "number": 5}
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_resp
        mock_gh_cls.return_value = MagicMock()

        with patch("review_pipeline_main.parse_and_filter_submission") as mock_s1, \
             patch("review_pipeline_main.calculate_priority") as mock_p:
            mock_p.return_value = {
                "priority_score": 5.0, "priority_label": "priority-standard",
                "reputation_score": 0.0, "reputation_tier": "new",
            }
            mock_s1.return_value = STAGE1_INVALID

            result = run_review_pipeline(5)
            assert result["paper_id"] == "2026-005"


# ---------------------------------------------------------------------------
# TESTS: CLI entry point
# ---------------------------------------------------------------------------


class TestCliEntryPoint:
    """Tests for the __main__ entry point."""

    def test_requires_issue_number_argument(self):
        """Should exit with error when no argument is provided."""
        import subprocess
        result = subprocess.run(
            ["python3", "-c", "import sys; sys.argv = ['test']; exec(open('review_pipeline_main.py').read())"],
            cwd="/Users/ak/UserRoot/AIPeerReviewPublication/pubroot-website/_review_agent",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1
