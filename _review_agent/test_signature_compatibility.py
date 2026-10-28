"""
Tests for Review Pipeline Signature Compatibility — Pubroot

PURPOSE:
    This test suite ensures that all cross-module function calls in the review
    pipeline use the correct function signatures. It was created to prevent
    regressions like the TypeError in issue #121 where calculate_priority() was
    called with the wrong arguments (issue_body, category, payment_code_verified)
    instead of the actual signature (author, category, payment_code, repo_root).

APPROACH:
    We mock all external dependencies (GitHub API, file I/O, network calls) and
    exercise both entry point modules (stages_1_to_3_analyzer.py and 
    stages_4_to_6_reviewer.py) with realistic input. The test verifies that:
    
    1. All function calls use correct parameter names and types
    2. All required arguments are provided
    3. The modules can be imported without errors
    4. The artifact JSON produced by job 1 can be consumed by job 2

RUNNING:
    pytest _review_agent/test_signature_compatibility.py -v

COVERAGE:
    This test covers the actual runtime call paths through both analyzer and
    reviewer, ensuring that signature changes are caught before merging.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest


# Sample GitHub issue data
SAMPLE_ISSUE_BODY = """
### Article Title

Test Gemini 3.8 Flash Performance Analysis

### Category

ai/llm-benchmarks

### Submission Type

benchmark

### Abstract

This paper analyzes the performance of Google's Gemini 3.8 Flash model across
various benchmarks to understand its capabilities and limitations.

### Article Body

""" + " ".join(["word"] * 300) + """

### Supporting Repository URL

https://github.com/test-user/test-repo

### Commit SHA

abc1234567890def

### Repository Visibility

public

### Payment Code (Optional)

_No response_
"""

SAMPLE_ISSUE_DATA = {
    "body": SAMPLE_ISSUE_BODY,
    "user": {"login": "test-user"},
}

# Sample stage outputs for the analyzer
SAMPLE_PARSED = {
    "valid": True,
    "errors": [],
    "warnings": [],
    "parsed": {
        "title": "Test Gemini 3.8 Flash Performance Analysis",
        "category": "ai/llm-benchmarks",
        "journal": "ai",
        "topic": "llm-benchmarks",
        "submission_type": "benchmark",
        "abstract": "This paper analyzes performance...",
        "body": "word " * 300,
        "supporting_repo": "https://github.com/test-user/test-repo",
        "commit_sha": "abc1234567890def",
        "repo_visibility": "public",
        "payment_code": None,
        "author": "test-user",
        "word_count_abstract": 10,
        "word_count_body": 300,
        "ai_tooling_attribution": None,
    }
}

SAMPLE_NOVELTY = {
    "arxiv_results": [],
    "s2_results": [],
    "internal_results": [],
    "potential_supersession": None,
    "total_related": 0,
    "search_query": "Test Gemini",
    "errors": [],
}

SAMPLE_REPO_DATA = {
    "available": True,
    "visibility": "public",
    "file_tree": "README.md\nmain.py",
    "file_count": 2,
    "key_files": [
        {"path": "README.md", "content": "# Test Repo", "size_bytes": 100, "truncated": False}
    ],
    "total_content_bytes": 100,
    "badge_type": "verified_open",
    "errors": [],
}

SAMPLE_PRIORITY_INFO = {
    "priority_score": 2.5,
    "priority_label": "priority:normal",
    "reputation_score": 0.0,
    "reputation_tier": "new",
    "payment_tier": 0,
    "topic_demand": 1.0,
}

SAMPLE_PAYMENT_VERIFICATION = {
    "valid": False,
    "product": None,
    "amount_cents": 0,
    "already_used": False,
    "error": None,
}

# Sample analysis output (from stages 1-3)
SAMPLE_ANALYSIS = {
    "success": True,
    "action": "continue",
    "issue_number": 121,
    "paper_id": "2026-121",
    "parsed": SAMPLE_PARSED["parsed"],
    "novelty": SAMPLE_NOVELTY,
    "repo_data": SAMPLE_REPO_DATA,
    "priority_info": SAMPLE_PRIORITY_INFO,
    "payment_verification": SAMPLE_PAYMENT_VERIFICATION,
    "errors": [],
}

# Sample review output (from stage 5)
SAMPLE_REVIEW_RESULT = {
    "success": True,
    "review": {
        "paper_id": "2026-121",
        "score": 7.5,
        "verdict": "ACCEPTED",
        "badge": "verified_open",
        "summary": "Good benchmark paper.",
        "strengths": ["Well-written", "Good data"],
        "weaknesses": ["Could use more detail"],
        "novelty_score": 7,
        "technical_quality": 8,
        "claims": [],
    },
    "grounding": {"web_searches": [], "source_urls": []},
    "raw_response_text": '{"paper_id": "2026-121", "score": 7.5, "verdict": "ACCEPTED"}',
    "model_used": "google/gemini-3.8-flash",
    "error": None,
}


@pytest.fixture
def mock_env():
    """Mock environment variables needed by both analyzer and reviewer."""
    with patch.dict(os.environ, {
        "GITHUB_TOKEN": "test-token",
        "GITHUB_REPOSITORY": "test-owner/test-repo",
        "GITHUB_WORKSPACE": "/tmp/test-workspace",
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "PUBROOT_MODEL": "google/gemini-3.8-flash",
        "S2_API_KEY": "test-s2-key",
    }):
        yield


@pytest.fixture
def mock_files(tmp_path):
    """Create mock config files (journals.json, contributors.json, etc.)."""
    # Create journals.json
    journals = {
        "journals": {
            "ai": {
                "name": "Artificial Intelligence",
                "topics": {
                    "llm-benchmarks": {
                        "name": "LLM Benchmarks",
                        "refresh_rate_days": 0,
                    }
                }
            }
        }
    }
    journals_path = tmp_path / "journals.json"
    journals_path.write_text(json.dumps(journals))
    
    # Create agent-index.json
    index = {"papers": []}
    index_path = tmp_path / "agent-index.json"
    index_path.write_text(json.dumps(index))
    
    # Create contributors.json
    contributors = {"contributors": {}}
    contributors_path = tmp_path / "contributors.json"
    contributors_path.write_text(json.dumps(contributors))
    
    # Create payments/_verified_payments.json
    payments_dir = tmp_path / "payments"
    payments_dir.mkdir()
    payments = {"payments": {}}
    payments_path = payments_dir / "_verified_payments.json"
    payments_path.write_text(json.dumps(payments))
    
    return tmp_path


def test_analyzer_imports():
    """Test that stages_1_to_3_analyzer.py can be imported without errors."""
    try:
        import stages_1_to_3_analyzer
        assert hasattr(stages_1_to_3_analyzer, "run_stages_1_to_3")
        assert hasattr(stages_1_to_3_analyzer, "fetch_issue_data")
    except ImportError as e:
        pytest.fail(f"Failed to import stages_1_to_3_analyzer: {e}")


def test_reviewer_imports():
    """Test that stages_4_to_6_reviewer.py can be imported without errors."""
    try:
        import stages_4_to_6_reviewer
        assert hasattr(stages_4_to_6_reviewer, "run_stages_4_to_6")
    except ImportError as e:
        pytest.fail(f"Failed to import stages_4_to_6_reviewer: {e}")


def test_analyzer_function_signatures(mock_env, mock_files):
    """
    Test that stages_1_to_3_analyzer calls all functions with correct signatures.
    
    This test mocks the GitHub API and all stage functions, then runs the
    analyzer to verify it calls parse_and_filter_submission, check_novelty,
    read_linked_repository, calculate_priority, and verify_payment_code with
    the correct argument names and types.
    """
    from stages_1_to_3_analyzer import run_stages_1_to_3
    
    # Mock GitHub API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ISSUE_DATA
    
    with patch("requests.get", return_value=mock_response), \
         patch("stages_1_to_3_analyzer.parse_and_filter_submission", return_value=SAMPLE_PARSED) as mock_parse, \
         patch("stages_1_to_3_analyzer.check_novelty", return_value=SAMPLE_NOVELTY) as mock_novelty, \
         patch("stages_1_to_3_analyzer.read_linked_repository", return_value=SAMPLE_REPO_DATA) as mock_repo, \
         patch("stages_1_to_3_analyzer.calculate_priority", return_value=SAMPLE_PRIORITY_INFO) as mock_priority, \
         patch("stages_1_to_3_analyzer.verify_payment_code", return_value=SAMPLE_PAYMENT_VERIFICATION) as mock_payment, \
         patch.dict(os.environ, {"GITHUB_WORKSPACE": str(mock_files)}):
        
        result = run_stages_1_to_3(121)
        
        # Verify parse_and_filter_submission was called with correct args
        assert mock_parse.called
        call_kwargs = mock_parse.call_args.kwargs
        assert "issue_body" in call_kwargs
        assert "repo_root" in call_kwargs
        assert "issue_author" in call_kwargs
        
        # Verify check_novelty was called with correct args
        assert mock_novelty.called
        call_kwargs = mock_novelty.call_args.kwargs
        assert "title" in call_kwargs
        assert "abstract" in call_kwargs
        assert "category" in call_kwargs
        assert "repo_root" in call_kwargs
        assert "s2_api_key" in call_kwargs
        
        # Verify read_linked_repository was called with correct args
        assert mock_repo.called
        call_kwargs = mock_repo.call_args.kwargs
        assert "repo_url" in call_kwargs
        assert "commit_sha" in call_kwargs
        assert "repo_visibility" in call_kwargs
        
        # Verify calculate_priority was called with correct args
        assert mock_priority.called
        # Should be called at least twice (initial + after parsing)
        call_kwargs = mock_priority.call_args.kwargs
        assert "author" in call_kwargs
        assert "category" in call_kwargs
        assert "payment_code" in call_kwargs
        assert "repo_root" in call_kwargs
        # Verify the old signature arguments are NOT present
        assert "issue_body" not in call_kwargs
        assert "payment_code_verified" not in call_kwargs
        
        # Verify verify_payment_code was called with correct args
        assert mock_payment.called
        call_kwargs = mock_payment.call_args.kwargs
        assert "payment_code" in call_kwargs
        assert "repo_root" in call_kwargs
        
        # Verify result structure
        assert result["success"] is True
        assert result["action"] == "continue"
        assert "parsed" in result
        assert "novelty" in result
        assert "repo_data" in result


def test_reviewer_function_signatures(mock_env, mock_files):
    """
    Test that stages_4_to_6_reviewer calls all functions with correct signatures.
    
    This test mocks all stage 4-6 functions and GitHub API, then runs the
    reviewer to verify it calls build_review_prompt and run_openrouter_review
    with the correct argument names and types.
    """
    from stages_4_to_6_reviewer import run_stages_4_to_6
    
    # Sample prompt from stage 4
    sample_prompt = "Review this paper: Test Gemini 3.8 Flash Performance Analysis..."
    
    with patch("stages_4_to_6_reviewer.build_review_prompt", return_value=sample_prompt) as mock_prompt, \
         patch("stages_4_to_6_reviewer.run_openrouter_review", return_value=SAMPLE_REVIEW_RESULT) as mock_review, \
         patch("stages_4_to_6_reviewer.post_review_and_decide", return_value={"success": True, "action": "accepted"}) as mock_post, \
         patch("stages_4_to_6_reviewer.update_all_reputations") as mock_reputation, \
         patch.dict(os.environ, {"GITHUB_WORKSPACE": str(mock_files)}):
        
        result = run_stages_4_to_6(SAMPLE_ANALYSIS)
        
        # Verify build_review_prompt was called with correct args
        assert mock_prompt.called
        call_kwargs = mock_prompt.call_args.kwargs
        assert "parsed_submission" in call_kwargs
        assert "novelty_results" in call_kwargs
        assert "repo_data" in call_kwargs
        assert "repo_root" in call_kwargs
        assert "paper_id" in call_kwargs
        # Verify the old argument name is NOT present
        assert "calibration_dir" not in call_kwargs
        
        # Verify run_openrouter_review was called with correct args
        assert mock_review.called
        call_kwargs = mock_review.call_args.kwargs
        assert "review_prompt" in call_kwargs
        assert "openrouter_api_key" in call_kwargs
        assert "model_name" in call_kwargs
        # Verify the old argument names are NOT present
        assert "prompt" not in call_kwargs
        assert "api_key" not in call_kwargs
        assert "gemini_api_key" not in call_kwargs
        assert "submission_type" not in call_kwargs
        
        # Verify post_review_and_decide was called with correct args
        assert mock_post.called
        call_kwargs = mock_post.call_args.kwargs
        assert "gh" in call_kwargs
        assert "review" in call_kwargs
        assert "grounding" in call_kwargs
        assert "parsed_submission" in call_kwargs
        
        # Verify result structure
        assert result["success"] is True
        assert result["action"] == "accepted"


def test_artifact_json_compatibility(mock_env, mock_files):
    """
    Test that the JSON artifact produced by the analyzer can be consumed by the reviewer.
    
    This simulates the artifact handoff between GitHub Actions jobs 1 and 2.
    """
    from stages_1_to_3_analyzer import run_stages_1_to_3
    from stages_4_to_6_reviewer import run_stages_4_to_6
    
    # Mock GitHub API and all stage functions
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ISSUE_DATA
    
    sample_prompt = "Review this paper..."
    
    with patch("requests.get", return_value=mock_response), \
         patch("stages_1_to_3_analyzer.parse_and_filter_submission", return_value=SAMPLE_PARSED), \
         patch("stages_1_to_3_analyzer.check_novelty", return_value=SAMPLE_NOVELTY), \
         patch("stages_1_to_3_analyzer.read_linked_repository", return_value=SAMPLE_REPO_DATA), \
         patch("stages_1_to_3_analyzer.calculate_priority", return_value=SAMPLE_PRIORITY_INFO), \
         patch("stages_1_to_3_analyzer.verify_payment_code", return_value=SAMPLE_PAYMENT_VERIFICATION), \
         patch("stages_4_to_6_reviewer.build_review_prompt", return_value=sample_prompt), \
         patch("stages_4_to_6_reviewer.run_openrouter_review", return_value=SAMPLE_REVIEW_RESULT), \
         patch("stages_4_to_6_reviewer.post_review_and_decide", return_value={"success": True, "action": "accepted"}), \
         patch("stages_4_to_6_reviewer.update_all_reputations"), \
         patch.dict(os.environ, {"GITHUB_WORKSPACE": str(mock_files)}):
        
        # Run analyzer (job 1)
        analysis_result = run_stages_1_to_3(121)
        
        # Verify analyzer produced a valid result
        assert analysis_result["success"] is True
        assert analysis_result["action"] == "continue"
        assert "parsed" in analysis_result
        assert "novelty" in analysis_result
        assert "repo_data" in analysis_result
        assert "priority_info" in analysis_result
        assert "payment_verification" in analysis_result
        
        # Serialize to JSON (simulating artifact upload/download)
        artifact_json = json.dumps(analysis_result)
        analysis_data = json.loads(artifact_json)
        
        # Run reviewer (job 2) with the artifact data
        review_result = run_stages_4_to_6(analysis_data)
        
        # Verify reviewer consumed the artifact correctly
        assert review_result["success"] is True
        assert review_result["action"] == "accepted"
        assert "paper_id" in review_result


def test_priority_calculator_signature():
    """
    Test that calculate_priority has the correct signature and behavior.
    
    This test directly calls the function to verify its signature matches
    what the analyzer expects.
    """
    from priority_score_calculator import calculate_priority
    
    # Create a minimal repo structure
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create minimal config files
        journals = {
            "journals": {
                "ai": {
                    "topics": {
                        "llm-benchmarks": {"refresh_rate_days": 0}
                    }
                }
            }
        }
        with open(os.path.join(tmp_dir, "journals.json"), "w") as f:
            json.dump(journals, f)
        
        with open(os.path.join(tmp_dir, "contributors.json"), "w") as f:
            json.dump({"contributors": {}}, f)
        
        with open(os.path.join(tmp_dir, "agent-index.json"), "w") as f:
            json.dump({"papers": []}, f)
        
        # Call with correct signature
        result = calculate_priority(
            author="test-user",
            category="ai/llm-benchmarks",
            payment_code=None,
            repo_root=tmp_dir,
        )
        
        # Verify result structure
        assert "priority_score" in result
        assert "priority_label" in result
        assert "reputation_score" in result
        assert "payment_tier" in result
        assert "topic_demand" in result


def test_verify_payment_code_signature():
    """
    Test that verify_payment_code has the correct signature.
    """
    from verify_payment_code import verify_payment_code
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create payments directory
        payments_dir = os.path.join(tmp_dir, "payments")
        os.makedirs(payments_dir)
        
        # Call with correct signature
        result = verify_payment_code(
            payment_code="PAID-test123",
            repo_root=tmp_dir,
        )
        
        # Verify result structure (should be invalid since we have no payments file)
        assert "valid" in result
        assert "error" in result
        assert result["valid"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
