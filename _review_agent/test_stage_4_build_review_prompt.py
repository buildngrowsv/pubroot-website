"""
Tests for Stage 4: Build Review Prompt — Pubroot Review Pipeline

HISTORY:
    Created 2026-03-23 by Builder 6 (swarm agent) as part of T5.
    These tests validate the prompt assembly logic that combines outputs
    from Stages 1-3 into a single string sent to Gemini. Since Stage 4
    is pure string assembly with no API calls ($0 cost), these tests run
    instantly and verify the structural integrity of the assembled prompt.

APPROACH:
    - We mock the filesystem for calibration example loading by creating
      a temp directory with gold-standard JSON files.
    - We test each private helper function independently, then test the
      main build_review_prompt() function end-to-end.
    - Key things to verify: prompt injection sanitization, body truncation,
      type-specific criteria selection, calibration loading, novelty/repo
      context formatting.

RUNNING:
    pytest _review_agent/test_stage_4_build_review_prompt.py -v
"""

import json
import os
import tempfile
import pytest

from stage_4_build_review_prompt import (
    build_review_prompt,
    _build_type_specific_criteria,
    _load_calibration_examples,
    _format_novelty_context,
    _format_repo_context,
)


# ---------------------------------------------------------------------------
# FIXTURES — reusable test data
# ---------------------------------------------------------------------------

# A minimal parsed submission that mimics Stage 1 output.
# These fields are the ones Stage 4 actually reads from the parsed dict.
SAMPLE_PARSED_SUBMISSION = {
    "title": "Testing LLM Accuracy in Code Review",
    "category": "ai/llm-benchmarks",
    "abstract": "We tested 5 leading LLMs on code review tasks across 200 PRs.",
    "body": "This is the article body with technical content about LLM benchmarks.",
    "author": "test-user",
    "supporting_repo": "https://github.com/test/repo",
    "commit_sha": "abc123",
    "submission_type": "original-research",
    "word_count_body": 1500,
}

# A minimal novelty result that mimics Stage 2 output.
SAMPLE_NOVELTY_RESULTS = {
    "arxiv_results": [
        {
            "title": "LLM Code Review Benchmark 2025",
            "published": "2025-11-01",
            "id": "2511.00001",
            "abstract": "We evaluate LLMs on code review tasks using 100 repositories.",
        }
    ],
    "s2_results": [
        {
            "title": "Automated Code Review with AI",
            "year": 2025,
            "citation_count": 42,
            "tldr": "Survey of AI-assisted code review tools.",
        }
    ],
    "internal_results": [],
    "potential_supersession": None,
}

# A minimal repo data result that mimics Stage 3 output.
SAMPLE_REPO_DATA_AVAILABLE = {
    "available": True,
    "visibility": "public",
    "badge_type": "verified_open",
    "file_count": 15,
    "total_content_bytes": 12000,
    "file_tree": "src/\n  main.py\n  utils.py\ntests/\n  test_main.py",
    "key_files": [
        {
            "path": "src/main.py",
            "content": "def evaluate_llm():\n    pass",
            "truncated": False,
        }
    ],
    "errors": [],
}

SAMPLE_REPO_DATA_NO_REPO = {
    "available": False,
    "visibility": "no-repo",
    "badge_type": "text_only",
    "file_count": 0,
    "total_content_bytes": 0,
    "file_tree": "",
    "key_files": [],
    "errors": [],
}

SAMPLE_REPO_DATA_PRIVATE = {
    "available": False,
    "visibility": "private",
    "badge_type": "verified_private",
    "file_count": 0,
    "total_content_bytes": 0,
    "file_tree": "",
    "key_files": [],
    "errors": [],
}

# A minimal calibration example matching the gold-standard JSON format.
SAMPLE_CALIBRATION_EXAMPLE = {
    "label": "Excellent",
    "score": 9.0,
    "verdict": "ACCEPTED",
    "submission_abstract": "A thorough benchmark of 5 LLMs on code review accuracy.",
    "scoring_reasoning": "High novelty, rigorous methodology, verified claims.",
}


# ---------------------------------------------------------------------------
# HELPER — create a temporary repo root with calibration files
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_repo_root_with_calibration():
    """
    Create a temporary directory structure that mimics the repo root
    with _calibration/ containing gold-standard JSON files. This is
    needed because _load_calibration_examples reads from the filesystem.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cal_dir = os.path.join(tmpdir, "_calibration")
        os.makedirs(cal_dir)

        # Write one calibration file
        cal_path = os.path.join(cal_dir, "gold-01-excellent.json")
        with open(cal_path, "w") as f:
            json.dump(SAMPLE_CALIBRATION_EXAMPLE, f)

        yield tmpdir


@pytest.fixture
def temp_repo_root_no_calibration():
    """
    Create a temporary directory without _calibration/ to test the
    cold-start case where no calibration examples exist yet.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ---------------------------------------------------------------------------
# TESTS: _build_type_specific_criteria
# ---------------------------------------------------------------------------


class TestBuildTypeSpecificCriteria:
    """
    Tests for the type-specific review criteria builder. Each submission
    type should produce different emphasis instructions that tell the LLM
    how to weight its scoring. This was added in Feb 2026 when we introduced
    6 submission types to prevent unfair reviews (e.g., penalizing case
    studies for low novelty).
    """

    def test_original_research_emphasizes_novelty(self):
        """Original research should have novelty as CRITICAL."""
        criteria = _build_type_specific_criteria("original-research")
        assert "Original Research" in criteria
        assert "Novelty" in criteria
        assert "CRITICAL" in criteria

    def test_case_study_deemphasizes_novelty(self):
        """Case studies should mark novelty as LOW importance."""
        criteria = _build_type_specific_criteria("case-study")
        assert "Case Study" in criteria
        assert "Practical Value" in criteria
        # Novelty should be LOW for case studies
        assert "LOW" in criteria

    def test_benchmark_emphasizes_methodology(self):
        """Benchmarks should have methodology as CRITICAL."""
        criteria = _build_type_specific_criteria("benchmark")
        assert "Benchmark" in criteria
        assert "Methodology" in criteria

    def test_tutorial_emphasizes_completeness(self):
        """Tutorials should prioritize completeness and working code."""
        criteria = _build_type_specific_criteria("tutorial")
        assert "Tutorial" in criteria
        assert "Completeness" in criteria

    def test_dataset_emphasizes_documentation(self):
        """Dataset submissions should prioritize documentation."""
        criteria = _build_type_specific_criteria("dataset")
        assert "Dataset" in criteria
        assert "Documentation" in criteria

    def test_review_survey_emphasizes_comprehensiveness(self):
        """Review/survey should emphasize comprehensiveness."""
        criteria = _build_type_specific_criteria("review-survey")
        assert "Review/Survey" in criteria
        assert "Comprehensiveness" in criteria

    def test_unknown_type_falls_back_to_original_research(self):
        """
        Unknown submission types should default to original-research criteria.
        This handles legacy submissions from before the 6-type system was added.
        """
        criteria = _build_type_specific_criteria("unknown-type")
        assert "Original Research" in criteria

    def test_all_six_types_return_nonempty_string(self):
        """Every valid type should produce non-empty criteria text."""
        valid_types = [
            "original-research", "case-study", "benchmark",
            "review-survey", "tutorial", "dataset",
        ]
        for sub_type in valid_types:
            result = _build_type_specific_criteria(sub_type)
            assert len(result) > 50, f"Type '{sub_type}' returned too-short criteria"


# ---------------------------------------------------------------------------
# TESTS: _load_calibration_examples
# ---------------------------------------------------------------------------


class TestLoadCalibrationExamples:
    """
    Tests for calibration example loading. These gold-standard reviews
    anchor the LLM's scoring across model versions (prevents drift).
    """

    def test_loads_existing_calibration_files(self, temp_repo_root_with_calibration):
        """Should load calibration examples when _calibration/ exists."""
        result = _load_calibration_examples(temp_repo_root_with_calibration, "ai/llm-benchmarks")
        assert "CALIBRATION EXAMPLES" in result
        assert "Excellent" in result
        assert "9.0" in result or "9" in result

    def test_returns_empty_when_no_calibration_dir(self, temp_repo_root_no_calibration):
        """Should return empty string when _calibration/ doesn't exist (cold start)."""
        result = _load_calibration_examples(temp_repo_root_no_calibration, "ai/llm-benchmarks")
        assert result == ""

    def test_returns_empty_when_calibration_dir_is_empty(self):
        """Should return empty string when _calibration/ exists but has no gold-*.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "_calibration"))
            result = _load_calibration_examples(tmpdir, "ai/llm-benchmarks")
            assert result == ""

    def test_handles_malformed_calibration_json(self):
        """
        Should gracefully skip calibration files with invalid JSON.
        This could happen if someone edits a calibration file and introduces
        a syntax error — the pipeline should not crash.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cal_dir = os.path.join(tmpdir, "_calibration")
            os.makedirs(cal_dir)
            # Write an invalid JSON file
            with open(os.path.join(cal_dir, "gold-01-bad.json"), "w") as f:
                f.write("{invalid json here}")
            result = _load_calibration_examples(tmpdir, "ai/llm-benchmarks")
            # Should return empty because the only file was malformed
            assert result == ""

    def test_loads_max_three_calibration_files(self):
        """Should load at most 3 calibration examples (to bound prompt size)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cal_dir = os.path.join(tmpdir, "_calibration")
            os.makedirs(cal_dir)
            # Create 5 calibration files
            for i in range(5):
                path = os.path.join(cal_dir, f"gold-{i:02d}-test.json")
                with open(path, "w") as f:
                    json.dump({
                        "label": f"Example {i}",
                        "score": 5.0 + i,
                        "verdict": "ACCEPTED",
                        "submission_abstract": f"Abstract {i}",
                        "scoring_reasoning": f"Reason {i}",
                    }, f)

            result = _load_calibration_examples(tmpdir, "ai/llm-benchmarks")
            # Count how many "Calibration" headers appear
            calibration_count = result.count("### Calibration")
            assert calibration_count == 3


# ---------------------------------------------------------------------------
# TESTS: _format_novelty_context
# ---------------------------------------------------------------------------


class TestFormatNoveltyContext:
    """
    Tests for novelty context formatting. This section gives the LLM
    awareness of existing related work so it can properly assess novelty.
    """

    def test_formats_arxiv_results(self):
        """Should include arXiv paper titles and IDs in the output."""
        result = _format_novelty_context(SAMPLE_NOVELTY_RESULTS)
        assert "arXiv" in result
        assert "LLM Code Review Benchmark 2025" in result
        assert "2511.00001" in result

    def test_formats_s2_results(self):
        """Should include Semantic Scholar papers with citation counts."""
        result = _format_novelty_context(SAMPLE_NOVELTY_RESULTS)
        assert "Semantic Scholar" in result
        assert "Automated Code Review with AI" in result
        assert "42" in result  # citation count

    def test_formats_internal_results(self):
        """Should include papers from our own journal when present."""
        novelty_with_internal = {
            **SAMPLE_NOVELTY_RESULTS,
            "internal_results": [
                {
                    "title": "Previous LLM Benchmark",
                    "id": "2025-010",
                    "score": 7.5,
                    "published_date": "2025-06-01",
                    "similarity_score": 0.72,
                }
            ],
        }
        result = _format_novelty_context(novelty_with_internal)
        assert "Our Journal" in result
        assert "Previous LLM Benchmark" in result

    def test_formats_supersession_warning(self):
        """Should include supersession warning when detected."""
        novelty_with_supersession = {
            "arxiv_results": [],
            "s2_results": [],
            "internal_results": [],
            "potential_supersession": {
                "message": "This appears to update paper 2025-010",
                "existing_paper_id": "2025-010",
            },
        }
        result = _format_novelty_context(novelty_with_supersession)
        assert "SUPERSESSION" in result
        assert "2025-010" in result

    def test_returns_novel_topic_message_when_no_results(self):
        """When no related work is found, should say topic may be novel."""
        empty_novelty = {
            "arxiv_results": [],
            "s2_results": [],
            "internal_results": [],
            "potential_supersession": None,
        }
        result = _format_novelty_context(empty_novelty)
        assert "novel" in result.lower()


# ---------------------------------------------------------------------------
# TESTS: _format_repo_context
# ---------------------------------------------------------------------------


class TestFormatRepoContext:
    """
    Tests for repository context formatting. This section gives the LLM
    the file tree and key file contents from the linked code repository.
    """

    def test_formats_available_repo(self):
        """Should include file tree and key files when repo is available."""
        result = _format_repo_context(SAMPLE_REPO_DATA_AVAILABLE)
        assert "SUPPORTING REPOSITORY" in result
        assert "src/main.py" in result
        assert "def evaluate_llm" in result

    def test_handles_no_repo(self):
        """Should explain no repo was provided when visibility is no-repo."""
        result = _format_repo_context(SAMPLE_REPO_DATA_NO_REPO)
        assert "No supporting repository" in result
        assert "text_only" in result

    def test_handles_private_repo(self):
        """Should explain private repos aren't supported yet."""
        result = _format_repo_context(SAMPLE_REPO_DATA_PRIVATE)
        assert "private" in result.lower()

    def test_handles_repo_with_errors(self):
        """Should show errors when repo reading failed."""
        repo_data_with_errors = {
            "available": False,
            "visibility": "public",
            "badge_type": "text_only",
            "file_count": 0,
            "total_content_bytes": 0,
            "errors": ["Clone failed: timeout after 30s"],
        }
        result = _format_repo_context(repo_data_with_errors)
        assert "could not be read" in result.lower()
        assert "Clone failed" in result


# ---------------------------------------------------------------------------
# TESTS: build_review_prompt (main function, end-to-end)
# ---------------------------------------------------------------------------


class TestBuildReviewPrompt:
    """
    End-to-end tests for the main build_review_prompt function.
    This assembles the complete prompt that Stage 5 sends to Gemini.
    """

    def test_assembles_complete_prompt(self, temp_repo_root_with_calibration):
        """The assembled prompt should contain all expected sections."""
        prompt = build_review_prompt(
            parsed_submission=SAMPLE_PARSED_SUBMISSION,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_AVAILABLE,
            repo_root=temp_repo_root_with_calibration,
            paper_id="2026-042",
        )

        # Check all major sections are present
        assert "peer reviewer" in prompt.lower()
        assert "2026-042" in prompt
        assert "Testing LLM Accuracy" in prompt
        assert "original-research" in prompt
        assert "ai/llm-benchmarks" in prompt
        assert "SCORING GUIDELINES" in prompt
        assert "REQUIRED OUTPUT FORMAT" in prompt
        assert "SUPPORTING REPOSITORY" in prompt
        assert "arXiv" in prompt

    def test_prompt_includes_paper_id(self, temp_repo_root_with_calibration):
        """Paper ID should appear in the prompt for the LLM to echo back."""
        prompt = build_review_prompt(
            parsed_submission=SAMPLE_PARSED_SUBMISSION,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_AVAILABLE,
            repo_root=temp_repo_root_with_calibration,
            paper_id="2026-099",
        )
        assert "2026-099" in prompt

    def test_prompt_includes_prompt_injection_warning(self, temp_repo_root_with_calibration):
        """
        The prompt must contain explicit instructions telling the LLM to
        treat the submission body as DATA, not instructions. This is critical
        for security — malicious submissions could try to override the review.
        """
        prompt = build_review_prompt(
            parsed_submission=SAMPLE_PARSED_SUBMISSION,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_AVAILABLE,
            repo_root=temp_repo_root_with_calibration,
            paper_id="2026-042",
        )
        assert "USER-SUPPLIED CONTENT" in prompt
        assert "DATA" in prompt

    def test_body_truncation_for_very_long_articles(self, temp_repo_root_no_calibration):
        """
        Articles longer than 8000 words should be truncated to prevent
        the submission from dominating the context window. This was set
        to 8000 words (~32K tokens) as a safety limit.
        """
        long_body = " ".join(["word"] * 10000)
        parsed_long = {**SAMPLE_PARSED_SUBMISSION, "body": long_body}

        prompt = build_review_prompt(
            parsed_submission=parsed_long,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_NO_REPO,
            repo_root=temp_repo_root_no_calibration,
            paper_id="2026-042",
        )
        assert "[Article truncated" in prompt

    def test_body_not_truncated_for_normal_articles(self, temp_repo_root_no_calibration):
        """Normal-length articles should not be truncated."""
        prompt = build_review_prompt(
            parsed_submission=SAMPLE_PARSED_SUBMISSION,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_NO_REPO,
            repo_root=temp_repo_root_no_calibration,
            paper_id="2026-042",
        )
        assert "[Article truncated" not in prompt

    def test_submission_type_defaults_to_original_research(self, temp_repo_root_no_calibration):
        """
        Submissions without a submission_type (from before Feb 2026) should
        default to original-research criteria, the strictest review type.
        """
        parsed_no_type = {k: v for k, v in SAMPLE_PARSED_SUBMISSION.items() if k != "submission_type"}
        prompt = build_review_prompt(
            parsed_submission=parsed_no_type,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_NO_REPO,
            repo_root=temp_repo_root_no_calibration,
            paper_id="2026-042",
        )
        assert "Original Research" in prompt

    def test_prompt_includes_json_schema(self, temp_repo_root_no_calibration):
        """The prompt must include the expected JSON output schema."""
        prompt = build_review_prompt(
            parsed_submission=SAMPLE_PARSED_SUBMISSION,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_NO_REPO,
            repo_root=temp_repo_root_no_calibration,
            paper_id="2026-042",
        )
        assert '"score"' in prompt
        assert '"verdict"' in prompt
        assert '"claims"' in prompt
        assert '"confidence"' in prompt

    def test_prompt_uses_correct_badge_type(self, temp_repo_root_no_calibration):
        """The badge instruction in the prompt should match the repo data."""
        prompt = build_review_prompt(
            parsed_submission=SAMPLE_PARSED_SUBMISSION,
            novelty_results=SAMPLE_NOVELTY_RESULTS,
            repo_data=SAMPLE_REPO_DATA_AVAILABLE,
            repo_root=temp_repo_root_no_calibration,
            paper_id="2026-042",
        )
        assert "verified_open" in prompt
