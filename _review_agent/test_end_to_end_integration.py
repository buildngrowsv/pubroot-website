"""
End-to-End Integration Tests for Review Pipeline

PURPOSE:
    These tests run the real stages_1_to_3_analyzer and stages_4_to_6_reviewer
    functions (not mocked), exercising all cross-module function calls with their
    actual signatures. Only network edges (GitHub API, OpenRouter API, git clone)
    are mocked.
    
    This catches signature mismatches that mock-based tests miss, because mocking
    the called functions hides signature errors that only appear at runtime.

APPROACH:
    1. Mock HTTP/network boundaries: requests.get (GitHub API), openai.OpenAI (OpenRouter),
       subprocess.run (git clone)
    2. Run run_stages_1_to_3() with a realistic issue body
    3. Verify the artifact JSON structure
    4. Run run_stages_4_to_6() with that artifact
    5. Use inspect.signature().bind() to verify every cross-module call signature
    6. Assert that post_review_and_decide is reached and produces a decision

RUNNING:
    pytest _review_agent/test_end_to_end_integration.py -v
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from inspect import signature
import pytest


# Sample GitHub issue body in the real submission template format
SAMPLE_ISSUE_BODY = """
### Article Title

Evaluating Gemini 3.8 Flash Performance on Code Review Tasks

### Category

ai/llm-benchmarks

### Submission Type

benchmark

### AI / Tooling Attribution (optional)

_No response_

### Abstract

This paper presents a comprehensive benchmark evaluation of Google's Gemini 3.8 Flash model
on automated code review tasks, comparing performance against GPT-5, Claude Opus, and
other state-of-the-art models across correctness, style, security, and efficiency dimensions.

### Article Body

""" + " ".join(["word"] * 250) + """

## Methodology

We evaluated 500 pull requests across 50 open-source repositories spanning Python, TypeScript,
Rust, and Go. Each PR was reviewed by all models, and outputs were scored by human reviewers
on a 1-10 scale across four dimensions: correctness, style, security, and efficiency.

## Results

Gemini 3.8 Flash achieved a mean score of 8.2/10 on correctness (vs. 8.5 for GPT-5 and 8.3 for
Claude Opus), 7.9/10 on style, 8.1/10 on security, and 8.4/10 on efficiency. The model showed
particular strength in identifying subtle race conditions and memory safety issues.

## Conclusion

Gemini 3.8 Flash demonstrates competitive performance on code review tasks while offering
significantly lower latency (median 2.1s vs. 4.3s for GPT-5) and cost ($0.825/1M tokens prompt).

### Supporting Repository URL

https://github.com/test-user/gemini-code-review-benchmark

### Commit SHA

abc1234567890defabcd

### Repository Visibility

public

### Payment Code (Optional)

_No response_
"""


@pytest.fixture
def mock_files(tmp_path):
    """Create mock config files (journals.json, contributors.json, etc.)."""
    # journals.json
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
    
    # agent-index.json
    index = {"papers": []}
    index_path = tmp_path / "agent-index.json"
    index_path.write_text(json.dumps(index))
    
    # contributors.json
    contributors = {"contributors": {}}
    contributors_path = tmp_path / "contributors.json"
    contributors_path.write_text(json.dumps(contributors))
    
    # payments/_verified_payments.json
    payments_dir = tmp_path / "payments"
    payments_dir.mkdir()
    payments = {"payments": {}}
    payments_path = payments_dir / "_verified_payments.json"
    payments_path.write_text(json.dumps(payments))
    
    # _calibration directory
    calibration_dir = tmp_path / "_calibration"
    calibration_dir.mkdir()
    
    return tmp_path


def test_end_to_end_analyzer_to_reviewer(mock_files):
    """
    Test the full pipeline from analyzer to reviewer with real function calls.
    
    This test runs both entry modules with their real stage functions, mocking
    only the network boundaries. It verifies:
    1. Analyzer produces valid artifact JSON
    2. Reviewer can consume that artifact
    3. All cross-module calls use correct signatures
    4. post_review_and_decide is reached with valid arguments
    """
    from stages_1_to_3_analyzer import run_stages_1_to_3
    from stages_4_to_6_reviewer import run_stages_4_to_6
    
    # Mock GitHub issue API response
    mock_github_response = MagicMock()
    mock_github_response.status_code = 200
    mock_github_response.json.return_value = {
        "body": SAMPLE_ISSUE_BODY,
        "user": {"login": "test-user"},
    }
    
    # Mock arXiv/S2 API responses (novelty check)
    mock_arxiv_response = MagicMock()
    mock_arxiv_response.status_code = 200
    mock_arxiv_response.content = b'<?xml version="1.0"?><feed></feed>'
    
    mock_s2_response = MagicMock()
    mock_s2_response.status_code = 200
    mock_s2_response.json.return_value = {"data": []}
    
    # Mock git clone subprocess (for repo reading)
    mock_subprocess_result = MagicMock()
    mock_subprocess_result.returncode = 0
    mock_subprocess_result.stdout = ""
    mock_subprocess_result.stderr = ""
    
    # Mock OpenRouter API response (for stage 5)
    mock_openai_client = MagicMock()
    mock_chat_completion = MagicMock()
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "paper_id": "2026-121",
        "score": 7.5,
        "verdict": "ACCEPTED",
        "badge": "verified_open",
        "summary": "Strong benchmark paper with solid methodology.",
        "strengths": ["Comprehensive evaluation", "Clear methodology", "Reproducible results"],
        "weaknesses": ["Limited discussion of model versions", "Could use more diverse languages"],
        "novelty_score": 7,
        "technical_quality": 8,
        "reproducibility": 9,
        "clarity": 8,
        "claims": []
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_chat_completion.choices = [mock_choice]
    mock_chat_completion.usage = MagicMock(total_tokens=1000)
    mock_openai_client.chat.completions.create.return_value = mock_chat_completion
    
    # Mock GitHubAPI for stage 6
    with patch("requests.get") as mock_requests_get, \
         patch("subprocess.run", return_value=mock_subprocess_result), \
         patch("shutil.rmtree"), \
         patch("openai.OpenAI", return_value=mock_openai_client), \
         patch("stage_6_post_review_and_decide.GitHubAPI") as mock_github_api_class, \
         patch.dict(os.environ, {
             "GITHUB_TOKEN": "test-token",
             "GITHUB_REPOSITORY": "test-owner/test-repo",
             "GITHUB_WORKSPACE": str(mock_files),
             "OPENROUTER_API_KEY": "sk-or-v1-test",
             "PUBROOT_MODEL": "google/gemini-3.8-flash",
         }):
        
        # Route requests.get to appropriate mocks
        def requests_get_side_effect(url, *args, **kwargs):
            if "github.com/repos" in url:
                return mock_github_response
            elif "export.arxiv.org" in url:
                return mock_arxiv_response
            elif "semanticscholar.org" in url:
                return mock_s2_response
            else:
                mock_resp = MagicMock()
                mock_resp.status_code = 404
                return mock_resp
        
        mock_requests_get.side_effect = requests_get_side_effect
        
        # Mock GitHubAPI instance methods
        mock_gh_instance = MagicMock()
        mock_gh_instance.post_comment.return_value = None
        mock_gh_instance.add_labels.return_value = None
        mock_gh_instance.close_issue.return_value = None
        
        # FIX: Mock path_exists with side_effect to handle both collision check and verification
        # First call is collision check (should return False), subsequent calls are verification (should return True)
        path_exists_calls = [False, True, True, True]  # First False for collision check, then True for verifications
        mock_gh_instance.path_exists.side_effect = path_exists_calls
        
        # FIX: Mock get_file_content to return valid index JSON for verification
        # The publish verification checks if paper_id is in the index
        mock_index_json = json.dumps({
            "papers": [
                {"id": "2026-121", "title": "Test Paper", "category": "ai/llm-benchmarks"}
            ]
        })
        mock_gh_instance.get_file_content.return_value = (mock_index_json, "sha")
        
        # Mock other methods used by publisher
        mock_gh_instance.create_or_update_file.return_value = {"commit": {"sha": "abc123"}}
        mock_gh_instance.create_pr.return_value = None
        
        mock_github_api_class.return_value = mock_gh_instance
        
        # ===================================================================
        # PART 1: Run analyzer (stages 1-3)
        # ===================================================================
        
        print("\n=== Running Analyzer (Stages 1-3) ===")
        analysis_result = run_stages_1_to_3(121)
        
        # Verify analyzer produced valid output
        assert analysis_result["success"] is True
        assert analysis_result["action"] == "continue"
        assert "parsed" in analysis_result
        assert "novelty" in analysis_result
        assert "repo_data" in analysis_result
        assert "priority_info" in analysis_result
        assert "payment_verification" in analysis_result
        
        # Verify the parsed structure contains the inner "parsed" dict
        parsed_wrapper = analysis_result["parsed"]
        assert "valid" in parsed_wrapper
        assert "parsed" in parsed_wrapper
        assert parsed_wrapper["valid"] is True
        
        parsed_fields = parsed_wrapper["parsed"]
        assert "category" in parsed_fields
        assert parsed_fields["category"] == "ai/llm-benchmarks"
        assert "title" in parsed_fields
        assert "author" in parsed_fields
        
        print(f"✓ Analyzer produced valid artifact with category: {parsed_fields['category']}")
        
        # ===================================================================
        # PART 2: Verify signature compatibility using inspect.signature
        # ===================================================================
        
        print("\n=== Verifying Function Signatures ===")
        
        # Import all functions to check their signatures
        from stage_1_parse_and_filter import parse_and_filter_submission
        from stage_2_novelty_check import check_novelty
        from stage_3_read_linked_repo import read_linked_repository
        from priority_score_calculator import calculate_priority
        from verify_payment_code import verify_payment_code
        from stage_4_build_review_prompt import build_review_prompt
        from stage_5_gemini_grounded_review import run_openrouter_review
        from stage_6_post_review_and_decide import post_review_and_decide
        
        # Verify parse_and_filter_submission signature
        sig = signature(parse_and_filter_submission)
        test_args = {
            "issue_body": SAMPLE_ISSUE_BODY,
            "repo_root": str(mock_files),
            "issue_author": "test-user"
        }
        bound = sig.bind(**test_args)
        print(f"✓ parse_and_filter_submission signature valid")
        
        # Verify check_novelty signature
        sig = signature(check_novelty)
        test_args = {
            "title": "Test",
            "abstract": "Abstract",
            "category": "ai/llm-benchmarks",
            "repo_root": str(mock_files),
            "s2_api_key": None
        }
        bound = sig.bind(**test_args)
        print(f"✓ check_novelty signature valid")
        
        # Verify read_linked_repository signature
        sig = signature(read_linked_repository)
        test_args = {
            "repo_url": "https://github.com/test/repo",
            "commit_sha": "abc123",
            "repo_visibility": "public"
        }
        bound = sig.bind(**test_args)
        print(f"✓ read_linked_repository signature valid")
        
        # Verify calculate_priority signature
        sig = signature(calculate_priority)
        test_args = {
            "author": "test-user",
            "category": "ai/llm-benchmarks",
            "payment_code": None,
            "repo_root": str(mock_files)
        }
        bound = sig.bind(**test_args)
        print(f"✓ calculate_priority signature valid")
        
        # Verify verify_payment_code signature
        sig = signature(verify_payment_code)
        test_args = {
            "payment_code": None,
            "repo_root": str(mock_files)
        }
        bound = sig.bind(**test_args)
        print(f"✓ verify_payment_code signature valid")
        
        # Verify build_review_prompt signature
        sig = signature(build_review_prompt)
        test_args = {
            "parsed_submission": parsed_fields,
            "novelty_results": analysis_result["novelty"],
            "repo_data": analysis_result["repo_data"],
            "repo_root": str(mock_files),
            "paper_id": "2026-121"
        }
        bound = sig.bind(**test_args)
        print(f"✓ build_review_prompt signature valid")
        
        # Verify run_openrouter_review signature
        sig = signature(run_openrouter_review)
        test_args = {
            "review_prompt": "Test prompt",
            "openrouter_api_key": "sk-or-v1-test",
            "model_name": "google/gemini-3.8-flash"
        }
        bound = sig.bind(**test_args)
        print(f"✓ run_openrouter_review signature valid")
        
        # Verify post_review_and_decide signature
        sig = signature(post_review_and_decide)
        test_args = {
            "review_result": {"success": True, "review": {}, "grounding_metadata": {}},
            "parsed_submission": parsed_fields,
            "novelty_results": analysis_result["novelty"],
            "repo_data": analysis_result["repo_data"],
            "paper_id": "2026-121",
            "issue_number": 121,
            "repo_owner": "test-owner",
            "repo_name": "test-repo",
            "github_token": "test-token",
            "repo_root": str(mock_files)
        }
        bound = sig.bind(**test_args)
        print(f"✓ post_review_and_decide signature valid")
        
        # ===================================================================
        # PART 3: Run reviewer (stages 4-6)
        # ===================================================================
        
        print("\n=== Running Reviewer (Stages 4-6) ===")
        review_result = run_stages_4_to_6(analysis_result)
        
        # Verify reviewer completed successfully
        assert review_result["success"] is True
        assert "action" in review_result
        assert review_result["action"] in ["accepted", "rejected"]
        
        # Verify post_review_and_decide was called
        assert mock_gh_instance.post_comment.called
        assert mock_gh_instance.add_labels.called
        
        print(f"✓ Reviewer completed with action: {review_result['action']}")
        print(f"✓ GitHub API calls made: post_comment={mock_gh_instance.post_comment.call_count}, "
              f"add_labels={mock_gh_instance.add_labels.call_count}")


def test_analyzer_output_structure():
    """
    Test that the analyzer's output JSON has the correct structure for the reviewer.
    
    This verifies that the "parsed" field contains the wrapper dict with "valid",
    "errors", "warnings", and the inner "parsed" dict with actual submission fields.
    """
    from stages_1_to_3_analyzer import run_stages_1_to_3
    
    mock_github_response = MagicMock()
    mock_github_response.status_code = 200
    mock_github_response.json.return_value = {
        "body": SAMPLE_ISSUE_BODY,
        "user": {"login": "test-user"},
    }
    
    with patch("requests.get", return_value=mock_github_response), \
         patch("subprocess.run", return_value=MagicMock(returncode=0)), \
         patch("shutil.rmtree"), \
         patch.dict(os.environ, {
             "GITHUB_TOKEN": "test-token",
             "GITHUB_REPOSITORY": "test-owner/test-repo",
             "GITHUB_WORKSPACE": "/tmp",
         }):
        
        # Create minimal config files in /tmp
        os.makedirs("/tmp/payments", exist_ok=True)
        Path("/tmp/journals.json").write_text(json.dumps({
            "journals": {"ai": {"topics": {"llm-benchmarks": {"refresh_rate_days": 0}}}}
        }))
        Path("/tmp/agent-index.json").write_text(json.dumps({"papers": []}))
        Path("/tmp/contributors.json").write_text(json.dumps({"contributors": {}}))
        Path("/tmp/payments/_verified_payments.json").write_text(json.dumps({"payments": {}}))
        
        result = run_stages_1_to_3(121)
        
        # Verify top-level structure
        assert "parsed" in result
        assert isinstance(result["parsed"], dict)
        
        # Verify wrapper structure
        parsed_wrapper = result["parsed"]
        assert "valid" in parsed_wrapper
        assert "errors" in parsed_wrapper
        assert "warnings" in parsed_wrapper
        assert "parsed" in parsed_wrapper
        
        # Verify inner parsed structure has actual fields
        parsed_fields = parsed_wrapper["parsed"]
        assert "category" in parsed_fields
        assert "title" in parsed_fields
        assert "author" in parsed_fields
        assert "abstract" in parsed_fields
        assert "body" in parsed_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
