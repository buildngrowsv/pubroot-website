"""
Tests for Bug B23 fixes.

Items tested:
1. Picker tier-3 gh api failure makes issue NOT eligible (fail closed)
2. Retry cap for publish-failed (3 attempts max)
3. stage_6 close_issue retries on 5xx with bounded backoff
6. OpenRouter cost logging (usage tokens and cost_usd stored in review_metadata)
7. Hardcoded reviewer name derived from PUBROOT_MODEL
8. Single atomic commit via Git Data API
9. Cron retry repair (re-run index update when article exists)
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch


# ============================================================================
# ITEM 1: Picker tier-3 gh api failure
# ============================================================================


# ============================================================================
# ITEM 2: Retry cap for publish-failed
# ============================================================================

def test_publish_retry_cap():
    """
    Test that publication stops after 3 retry attempts.
    
    When a paper file exists but isn't in the index, the cron will retry.
    After 3 attempts, we should give up and post a human-review comment.
    """
    from stage_6_post_review_and_decide import (
        _get_publish_retry_attempt,
        _handle_acceptance,
        GitHubAPI
    )
    
    # Mock GitHubAPI
    gh = Mock(spec=GitHubAPI)
    
    # Simulate 3 existing retry comments
    gh.get_issue_comments.return_value = [
        {"user": {"login": "github-actions[bot]"}, "body": "<!-- pubroot:publish-retry-attempt-1 -->\nPublication attempt 1 of 3..."},
        {"user": {"login": "github-actions[bot]"}, "body": "<!-- pubroot:publish-retry-attempt-2 -->\nPublication attempt 2 of 3..."},
        {"user": {"login": "github-actions[bot]"}, "body": "<!-- pubroot:publish-retry-attempt-3 -->\nPublication attempt 3 of 3..."},
    ]
    
    # Check retry count
    retry_count = _get_publish_retry_attempt(gh, 123)
    assert retry_count == 3, f"Expected 3 retries, got {retry_count}"
    
    # Now try to handle acceptance - should raise due to cap
    with pytest.raises(Exception) as exc_info:
        _handle_acceptance(
            gh=gh,
            review={"score": 7.0, "verdict": "ACCEPTED"},
            grounding={},
            parsed_submission={"title": "Test", "category": "ai/test", "author": "test"},
            novelty_results={},
            repo_data={"badge_type": "text_only"},
            paper_id="2026-999",
            issue_number=123,
            repo_root="/tmp/test",
        )
    
    assert "retry cap reached" in str(exc_info.value).lower()
    
    # Check that a human-review comment was posted
    gh.post_comment.assert_called_once()
    comment_text = gh.post_comment.call_args[0][1]
    assert "retry cap reached" in comment_text.lower()
    assert "human intervention" in comment_text.lower()


def test_publish_retry_attempt_counter():
    """
    Test _get_publish_retry_attempt and _record_publish_retry_attempt helpers.
    """
    from stage_6_post_review_and_decide import (
        _get_publish_retry_attempt,
        GitHubAPI
    )
    
    gh = Mock(spec=GitHubAPI)
    
    # No retry comments yet
    gh.get_issue_comments.return_value = []
    assert _get_publish_retry_attempt(gh, 123) == 0
    
    # One retry comment
    gh.get_issue_comments.return_value = [
        {"user": {"login": "github-actions[bot]"}, "body": "<!-- pubroot:publish-retry-attempt-1 -->\nAttempt 1"},
    ]
    assert _get_publish_retry_attempt(gh, 123) == 1
    
    # Multiple retry comments (take max)
    gh.get_issue_comments.return_value = [
        {"user": {"login": "github-actions[bot]"}, "body": "<!-- pubroot:publish-retry-attempt-1 -->\nAttempt 1"},
        {"user": {"login": "github-actions[bot]"}, "body": "<!-- pubroot:publish-retry-attempt-2 -->\nAttempt 2"},
        {"user": {"login": "someone-else"}, "body": "<!-- pubroot:publish-retry-attempt-99 -->\nFake"},
    ]
    assert _get_publish_retry_attempt(gh, 123) == 2  # Ignores non-bot comment


# ============================================================================
# ITEM 3: stage_6 close_issue retries on 5xx
# ============================================================================

def test_close_issue_retries_on_5xx():
    """
    Test that GitHubAPI.close_issue retries on 5xx errors with bounded backoff.
    """
    from stage_6_post_review_and_decide import GitHubAPI
    import requests
    
    gh = GitHubAPI("owner", "repo", "fake-token")
    
    # Create a proper HTTPError with a response
    def make_503_error():
        mock_response = Mock()
        mock_response.status_code = 503
        error = requests.HTTPError(response=mock_response)
        error.response = mock_response
        return error
    
    # Mock requests.patch to return 503 twice, then succeed
    call_count = [0]
    def mock_patch_fn(*args, **kwargs):
        call_count[0] += 1
        mock_response = Mock()
        if call_count[0] <= 2:
            # First two calls: 503 error
            mock_response.status_code = 503
            error = requests.HTTPError(response=mock_response)
            error.response = mock_response
            mock_response.raise_for_status.side_effect = error
        else:
            # Third call: success
            mock_response.status_code = 200
            mock_response.json.return_value = {"state": "closed"}
        return mock_response
    
    with patch('requests.patch', side_effect=mock_patch_fn):
        with patch('time.sleep') as mock_sleep:  # Don't actually sleep in tests
            # This should succeed after 2 retries
            gh.close_issue(123)
            
            # Check that we slept with correct backoff
            assert mock_sleep.call_count == 2
            # First sleep: 2s, second sleep: 4s
            assert mock_sleep.call_args_list[0][0][0] == 2
            assert mock_sleep.call_args_list[1][0][0] == 4


def test_close_issue_gives_up_after_max_retries():
    """
    Test that close_issue gives up after 3 attempts on persistent 5xx.
    """
    from stage_6_post_review_and_decide import GitHubAPI
    import requests
    
    gh = GitHubAPI("owner", "repo", "fake-token")
    
    # Mock requests.patch to always return 503
    def mock_patch_fn(*args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 503
        error = requests.HTTPError(response=mock_response)
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        return mock_response
    
    with patch('requests.patch', side_effect=mock_patch_fn):
        with patch('time.sleep'):
            # This should raise after 3 attempts
            with pytest.raises(Exception) as exc_info:
                gh.close_issue(123)
            
            assert "failed to close issue" in str(exc_info.value).lower()
            assert "3 attempts" in str(exc_info.value)


# ============================================================================
# ITEM 6: OpenRouter cost logging
# ============================================================================

def test_openrouter_cost_logging():
    """
    Test that OpenRouter usage and cost are logged and stored in review_metadata.
    Uses real ChatCompletion objects with OpenRouter's usage shape.
    """
    from stage_5_gemini_grounded_review import run_openrouter_review
    import openai.types.chat
    
    # Create a real ChatCompletion with OpenRouter's usage shape
    completion_dict = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "test/model",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"score": 7.5, "verdict": "ACCEPTED", "summary": "Good paper", "review_metadata": {"reviewer": "test-model"}}'
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 5200,
            "completion_tokens": 1800,
            "total_tokens": 7000,
            "completion_tokens_details": {
                "reasoning_tokens": 600
            },
            "cost": 0.0117
        }
    }
    mock_response = openai.types.chat.ChatCompletion.model_validate(completion_dict)
    
    # Mock OpenAI client (imported inside function)
    with patch('openai.OpenAI') as mock_openai_class:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Mock the parsed attribute
        review_json = {
            "score": 7.5,
            "verdict": "ACCEPTED",
            "summary": "Good paper",
            "review_metadata": {
                "reviewer": "test-model"
            }
        }
        mock_response.choices[0].message.parsed = review_json
        
        # Run review
        result = run_openrouter_review(
            review_prompt="Test prompt",
            openrouter_api_key="fake-key",
            model_name="test/model"
        )
        
        # Check that usage was stored in review_metadata
        assert result["success"] is True
        assert "usage" in result["review"]["review_metadata"]
        usage = result["review"]["review_metadata"]["usage"]
        assert usage["prompt_tokens"] == 5200
        assert usage["completion_tokens"] == 1800
        assert usage["reasoning_tokens"] == 600
        assert usage["total_tokens"] == 7000
        assert usage["cost_usd"] == 0.0117


def test_openrouter_cost_logging_no_usage():
    """
    Test that we handle missing usage field gracefully.
    """
    from stage_5_gemini_grounded_review import run_openrouter_review
    import openai.types.chat
    
    # Create ChatCompletion without usage field
    completion_dict = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "test/model",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"score": 7.5, "verdict": "ACCEPTED", "summary": "Good paper", "review_metadata": {"reviewer": "test-model"}}'
            },
            "finish_reason": "stop"
        }]
    }
    mock_response = openai.types.chat.ChatCompletion.model_validate(completion_dict)
    
    with patch('openai.OpenAI') as mock_openai_class:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        review_json = {
            "score": 7.5,
            "verdict": "ACCEPTED",
            "summary": "Good paper",
            "review_metadata": {
                "reviewer": "test-model"
            }
        }
        mock_response.choices[0].message.parsed = review_json
        
        # Should succeed without crashing
        result = run_openrouter_review(
            review_prompt="Test prompt",
            openrouter_api_key="fake-key",
            model_name="test/model"
        )
        
        # Usage should not be in review_metadata
        assert result["success"] is True
        assert "usage" not in result["review"]["review_metadata"]


def test_openrouter_cost_logging_usage_without_cost():
    """
    Test that usage without cost field still captures tokens.
    """
    from stage_5_gemini_grounded_review import run_openrouter_review
    import openai.types.chat
    
    # Create ChatCompletion with usage but no cost
    completion_dict = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "test/model",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"score": 7.5, "verdict": "ACCEPTED", "summary": "Good paper", "review_metadata": {"reviewer": "test-model"}}'
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
    }
    mock_response = openai.types.chat.ChatCompletion.model_validate(completion_dict)
    
    with patch('openai.OpenAI') as mock_openai_class:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        review_json = {
            "score": 7.5,
            "verdict": "ACCEPTED",
            "summary": "Good paper",
            "review_metadata": {
                "reviewer": "test-model"
            }
        }
        mock_response.choices[0].message.parsed = review_json
        
        result = run_openrouter_review(
            review_prompt="Test prompt",
            openrouter_api_key="fake-key",
            model_name="test/model"
        )
        
        # Should have usage info but cost_usd is None
        assert result["success"] is True
        assert "usage" in result["review"]["review_metadata"]
        usage = result["review"]["review_metadata"]["usage"]
        assert usage["prompt_tokens"] == 1000
        assert usage["completion_tokens"] == 500
        assert usage["total_tokens"] == 1500
        assert usage["cost_usd"] is None


# ============================================================================
# ITEM 7: Reviewer name derived from PUBROOT_MODEL
# ============================================================================

def test_reviewer_name_from_env():
    """
    Test that the reviewer name in the prompt is derived from PUBROOT_MODEL env var.
    """
    from stage_4_build_review_prompt import build_review_prompt
    
    # Set PUBROOT_MODEL
    with patch.dict(os.environ, {"PUBROOT_MODEL": "anthropic/claude-3-sonnet"}):
        prompt = build_review_prompt(
            parsed_submission={
                "title": "Test Paper",
                "abstract": "Test abstract",
                "body": "Test body",
                "category": "ai/test",
                "author": "testuser"
            },
            novelty_results={"similar_papers": []},
            repo_data={"badge_type": "text_only"},
            repo_root="/tmp/test",
            paper_id="2026-999"
        )
        
        # Check that the prompt contains the model name from env
        assert "anthropic/claude-3-sonnet" in prompt
        
        # Check that it's in the review_metadata section
        assert '"reviewer": "anthropic/claude-3-sonnet"' in prompt


def test_reviewer_name_default():
    """
    Test that the reviewer name defaults to google/gemini-3.8-flash when PUBROOT_MODEL is unset.
    """
    from stage_4_build_review_prompt import build_review_prompt
    
    # Unset PUBROOT_MODEL
    with patch.dict(os.environ, {}, clear=False):
        if "PUBROOT_MODEL" in os.environ:
            del os.environ["PUBROOT_MODEL"]
        
        prompt = build_review_prompt(
            parsed_submission={
                "title": "Test Paper",
                "abstract": "Test abstract",
                "body": "Test body",
                "category": "ai/test",
                "author": "testuser"
            },
            novelty_results={"similar_papers": []},
            repo_data={"badge_type": "text_only"},
            repo_root="/tmp/test",
            paper_id="2026-999"
        )
        
        # Check that the prompt contains the default model
        assert "google/gemini-3.8-flash" in prompt


# ============================================================================
# ITEM 8: Single atomic commit via Git Data API
# ============================================================================

def test_atomic_commit_git_data_api():
    """
    Test that _commit_files_atomically uses Git Data API correctly.
    
    This tests that:
    1. All files are committed in ONE commit
    2. force=false on update_ref (fail on conflict)
    3. Retries on non-fast-forward with backoff
    """
    from stage_6_post_review_and_decide import _commit_files_atomically, GitHubAPI
    
    gh = Mock(spec=GitHubAPI)
    
    # Mock Git Data API methods
    gh.get_ref_sha.return_value = "parent-sha-123"
    gh.get_commit.return_value = {"tree": {"sha": "tree-sha-456"}}
    gh.create_blob.side_effect = ["blob1", "blob2", "blob3", "blob4", "blob5"]
    gh.create_tree.return_value = "new-tree-789"
    gh.create_commit.return_value = "new-commit-abc"
    gh.update_ref.return_value = None
    
    files = {
        "papers/ai/test/test-paper/index.md": "# Test",
        "papers/ai/test/test-paper/manifest.json": "{}",
        "reviews/2026-999/review.json": "{}",
        "agent-index.json": "{}",
        "priorroot-index.json": "{}",
    }
    
    _commit_files_atomically(
        gh=gh,
        branch="main",
        files=files,
        commit_message="Publish: Test Paper (2026-999)",
        paper_id="2026-999"
    )
    
    # Check that we created 5 blobs (one per file)
    assert gh.create_blob.call_count == 5
    
    # Check that we created 1 tree with all 5 files
    assert gh.create_tree.call_count == 1
    tree_items = gh.create_tree.call_args[0][1]
    assert len(tree_items) == 5
    
    # Check that we created 1 commit
    assert gh.create_commit.call_count == 1
    
    # Check that update_ref was called with force=False
    assert gh.update_ref.call_count == 1
    assert gh.update_ref.call_args[1]["force"] is False


def test_atomic_commit_retries_on_conflict():
    """
    Test that _commit_files_atomically retries on non-fast-forward (409/422).
    """
    from stage_6_post_review_and_decide import _commit_files_atomically, GitHubAPI
    import requests
    
    gh = Mock(spec=GitHubAPI)
    
    # Mock conflict on first attempt, success on second
    conflict_response = Mock()
    conflict_response.status_code = 409
    
    gh.get_ref_sha.return_value = "parent-sha"
    gh.get_commit.return_value = {"tree": {"sha": "tree-sha"}}
    gh.create_blob.return_value = "blob-sha"
    gh.create_tree.return_value = "tree-sha"
    gh.create_commit.return_value = "commit-sha"
    
    # First update_ref fails with 409, second succeeds
    gh.update_ref.side_effect = [
        requests.HTTPError(response=conflict_response),
        None
    ]
    
    with patch('time.sleep'):  # Don't actually sleep
        _commit_files_atomically(
            gh=gh,
            branch="main",
            files={"test.txt": "content"},
            commit_message="Test",
            paper_id="2026-999"
        )
    
    # Should have retried once (2 total update_ref calls)
    assert gh.update_ref.call_count == 2



# ============================================================================
# ITEM 9: Cron retry repair
# ============================================================================

def test_cron_retry_repair():
    """
    Test that when article exists (idempotent retry), we re-run index update
    and verification instead of returning early.
    
    This tests the behavior of the idempotent retry code path. When the article
    already exists with matching paper_id, we should:
    1. Re-run _update_indexes (not skip it)
    2. Re-run _verify_publish_succeeded_with_retry
    
    This ensures a half-failed publish (article committed but indexes not updated)
    heals itself on cron retry.
    """
    from stage_6_post_review_and_decide import _handle_acceptance, GitHubAPI
    import json
    
    gh = Mock(spec=GitHubAPI)
    
    # Simulate article exists with matching paper_id
    gh.path_exists.return_value = True
    
    # Mock get_file_content to return different content depending on the path
    # The key is that agent-index.json contains the paper AFTER the update
    def mock_get_file_content(path, branch="main"):
        if "index.md" in path or "article.md" in path:
            return ("---\npaper_id: 2026-999\ntitle: Test\ndate: \"2026-10-30T15:02:23Z\"\n---\nContent", "file-sha")
        elif "agent-index.json" in path:
            # After update, the paper should be in the index
            return (json.dumps({
                "papers": [{
                    "id": "2026-999",
                    "title": "Test Paper",
                    "category": "ai/test",
                    "article_path": "papers/ai/test/test-paper/index.md"
                }],
                "last_updated": "2026-10-30T00:00:00Z"
            }), "agent-index-sha")
        elif "priorroot-index.json" in path:
            return (json.dumps({"papers": [], "last_updated": "2026-10-30T00:00:00Z"}), "priorroot-index-sha")
        else:
            raise FileNotFoundError(f"Mock: file {path} not found")
    
    gh.get_file_content.side_effect = mock_get_file_content
    
    # Mock other required methods
    gh.get_ref_sha.return_value = "ref-sha"
    gh.get_commit.return_value = {"tree": {"sha": "tree-sha"}}
    gh.create_blob.return_value = "blob-sha"
    gh.create_tree.return_value = "tree-sha"
    gh.create_commit.return_value = "commit-sha"
    gh.update_ref.return_value = None
    gh.get_issue_comments.return_value = []  # No retry attempts yet
    
    # Call _handle_acceptance
    result = _handle_acceptance(
        gh=gh,
        review={"score": 7.0, "verdict": "ACCEPTED"},
        grounding={},
        parsed_submission={
            "title": "Test Paper",
            "category": "ai/test",
            "author": "testuser",
            "abstract": "Test",
            "body": "Test"
        },
        novelty_results={},
        repo_data={"badge_type": "text_only"},
        paper_id="2026-999",
        issue_number=123,
        repo_root="/tmp/test"
    )
    
    # Should return None (idempotent)
    assert result is None
    
    # The key test: We should have called get_file_content for indexes
    # (means we attempted index update, NOT early return)
    # get_file_content is called for: article (1), agent-index (1), priorroot-index (1), verification (2)
    # Total should be at least 3 (the update path)
    assert gh.get_file_content.call_count >= 3, (
        f"Expected at least 3 get_file_content calls (article + both indexes), "
        f"got {gh.get_file_content.call_count}. This suggests early return."
    )


# ============================================================================
# ITEM 10: Test nits
# ============================================================================


# ============================================================================
# B23 round 2: behavioural tests (each one fails if its fix is reverted)
# ============================================================================

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]


def _bot(body):
    return {"user": {"login": "github-actions[bot]"}, "body": body}


def _picker_script():
    import yaml
    wf = yaml.safe_load((REPO_ROOT / ".github/workflows/review.yml").read_text())
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            if step.get("name") == "Determine issue number":
                assert "shell" not in step, "test assumes the default `bash -e` shell"
                return step["run"]
    raise AssertionError("picker step not found")


def _run_picker(tmp_path, issues, comments, fail_api=()):
    """Run the real picker step under `bash -e` (Actions' default) with a fake gh."""
    import tempfile
    if shutil.which("jq") is None:
        pytest.fail("jq is required for the picker test (it is on GitHub's runners)")
    tmp_path = Path(tempfile.mkdtemp(dir=tmp_path))  # one sandbox per simulated cron run
    bindir = tmp_path / "bin"; bindir.mkdir()
    (tmp_path / "state.json").write_text(json.dumps({"issues": issues, "comments": comments}))
    (bindir / "gh").write_text(f"""#!{sys.executable}
import json, os, subprocess, sys
a = sys.argv[1:]; st = json.load(open({str(tmp_path / 'state.json')!r}))
if a[:2] == ["issue", "list"]:
    lbl = a[a.index("--label") + 1] if "--label" in a else None
    data = [i for i in st["issues"] if lbl is None or lbl in [l["name"] for l in i["labels"]]]
elif a[0] == "api":
    n = a[1].split("/")[-2]
    if n in {list(map(str, fail_api))!r}:
        sys.stderr.write("HTTP 502: Bad Gateway\\n"); sys.exit(1)
    data = st["comments"].get(n, [])
else:
    sys.exit(2)
r = subprocess.run(["jq", "-r", a[a.index("--jq") + 1]], input=json.dumps(data), capture_output=True, text=True)
sys.stdout.write(r.stdout); sys.exit(r.returncode)
""")
    (bindir / "python").write_text("#!/bin/sh\nexit 0\n")  # author_gating: everyone approved
    for f in bindir.iterdir():
        f.chmod(0o755)
    script = tmp_path / "step.sh"; script.write_text(_picker_script())
    out = tmp_path / "out.txt"; out.write_text("")
    env = {"PATH": f"{bindir}:{os.environ['PATH']}", "GITHUB_OUTPUT": str(out),
           "GITHUB_REPOSITORY": "o/r", "EVENT_NAME": "schedule"}
    r = subprocess.run(["bash", "-e", str(script)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    picked = [l.split("=", 1)[1] for l in out.read_text().splitlines() if l.startswith("issue_number=")]
    return (picked[-1] if picked else ""), r.stdout


def _labels(*names):
    return [{"name": n} for n in names]


def test_picker_fails_closed_when_gh_api_fails(tmp_path):
    issues = [{"number": 7, "labels": _labels("submission")}]
    picked, log = _run_picker(tmp_path, issues, {}, fail_api=[7])
    assert picked == "", log
    assert "#7 skipped (API call failed)" in log
    # control: same issue with a working API and no bot comments is picked
    picked, log = _run_picker(tmp_path, issues, {})
    assert picked == "7", log


def _cap_comments():
    rev = _bot("# AI Peer Review — ACCEPTED")
    fail = _bot("# Publication step failed (review was ACCEPTED)")
    out = []
    for i in (1, 2, 3):
        out += [rev, _bot(f"<!-- pubroot:publish-retry-attempt-{i} -->\nPublication attempt {i} of 3..."), fail]
    return out


def _accepted_review():
    return {"success": True, "review": {"score": 8.0, "verdict": "ACCEPTED", "summary": "ok"},
            "grounding_metadata": {}}


def _run_post_review(gh):
    from stage_6_post_review_and_decide import post_review_and_decide
    with patch("stage_6_post_review_and_decide.GitHubAPI", return_value=gh):
        return post_review_and_decide(
            review_result=_accepted_review(),
            parsed_submission={"title": "T", "category": "ai/test", "author": "a", "abstract": "x", "body": "y"},
            novelty_results={}, repo_data={"badge_type": "text_only"}, paper_id="2026-999",
            issue_number=5, repo_owner="o", repo_name="r", github_token="t", repo_root="/nonexistent")


def test_retry_cap_parks_issue_and_later_cron_runs_skip_it(tmp_path):
    from stage_6_post_review_and_decide import GitHubAPI
    comments = _cap_comments()
    labels = {"submission", "publish-failed"}
    # cron run 1: picker selects the publish-failed issue
    picked, log = _run_picker(tmp_path, [{"number": 5, "labels": _labels(*sorted(labels))}], {"5": comments})
    assert picked == "5", log
    # ... stage 6 hits the cap
    gh = Mock(spec=GitHubAPI)
    gh.get_issue_comments.return_value = comments
    gh.add_labels.side_effect = lambda n, ls: labels.update(ls)
    gh.remove_label.side_effect = lambda n, l: labels.discard(l)
    posted = []
    gh.post_comment.side_effect = lambda n, body: posted.append(body)
    result = _run_post_review(gh)
    assert result["success"] is False
    assert "editorial-hold" in labels
    assert "publish-failed" in labels, "keep publish-failed so releasing the hold re-enters tier 1"
    assert not any("# Publication step failed" in b for b in posted)
    assert any("pubroot:publish-retry-cap" in b for b in posted)
    comments = comments + [_bot(b) for b in posted]
    # cron runs 2 and 3: nothing is picked, so no LLM call
    for _cron_run in (2, 3):
        picked, log = _run_picker(tmp_path, [{"number": 5, "labels": _labels(*sorted(labels))}], {"5": comments})
        assert picked == "", log
    # maintainer removes editorial-hold: tier 1 picks it again with a fresh count
    labels.discard("editorial-hold")
    picked, log = _run_picker(tmp_path, [{"number": 5, "labels": _labels(*sorted(labels))}], {"5": comments})
    assert picked == "5", log
    from stage_6_post_review_and_decide import _get_publish_retry_attempt
    gh.get_issue_comments.return_value = comments
    assert _get_publish_retry_attempt(gh, 5) == 0


def test_get_issue_comments_paginates():
    from stage_6_post_review_and_decide import GitHubAPI, _get_publish_retry_attempt
    pages = {1: [{"user": {"login": "someone"}, "body": "hi"}] * 100,
             2: [_bot(f"<!-- pubroot:publish-retry-attempt-{i} -->") for i in (1, 2, 3)]}

    def fake_get(url, params=None, **kwargs):
        resp = Mock()
        resp.json.return_value = pages.get(params["page"], [])
        return resp

    with patch("requests.get", side_effect=fake_get):
        assert _get_publish_retry_attempt(GitHubAPI("o", "r", "t"), 5) == 3


def test_close_failure_is_logged_not_failed():
    """Item 3 decision: close keeps failing after its 3 tries -> log only, stay success."""
    from stage_6_post_review_and_decide import GitHubAPI
    gh = Mock(spec=GitHubAPI)
    gh.path_exists.return_value = False
    gh.close_issue.side_effect = Exception("Failed to close issue #5 after 3 attempts: 502")
    with patch("stage_6_post_review_and_decide._handle_acceptance", return_value=None):
        result = _run_post_review(gh)
    assert result["success"] is True and result["action_taken"] == "accepted"
    added = [l for call in gh.add_labels.call_args_list for l in call[0][1]]
    assert "publish-failed" not in added
    gh.close_issue.assert_called_once()


def test_atomic_commit_recomputes_indexes_after_conflict():
    """Item 8 race: after a non-fast-forward, indexes are rebuilt from the NEW parent."""
    from stage_6_post_review_and_decide import _commit_files_atomically, GitHubAPI
    gh = Mock(spec=GitHubAPI)
    gh.get_ref_sha.side_effect = ["parent-1", "parent-2"]
    gh.get_commit.return_value = {"tree": {"sha": "base"}}
    blobs = {}

    def create_blob(content):
        key = f"b{len(blobs)}"; blobs[key] = content; return key

    gh.create_blob.side_effect = create_blob
    gh.create_tree.return_value = "tree"
    gh.create_commit.return_value = "commit"
    gh.update_ref.side_effect = [requests.HTTPError(response=Mock(status_code=422)), None]
    seen = []

    def compute(parent_sha):
        seen.append(parent_sha)
        return f"agent@{parent_sha}", f"prior@{parent_sha}"

    with patch("time.sleep"):
        _commit_files_atomically(gh=gh, branch="main", files={"a/index.md": "x"},
                                 commit_message="m", paper_id="2026-999", compute_indexes=compute)
    assert seen == ["parent-1", "parent-2"]
    committed = {i["path"]: blobs[i["sha"]] for i in gh.create_tree.call_args_list[-1][0][1]}
    assert committed["agent-index.json"] == "agent@parent-2"
    assert committed["priorroot-index.json"] == "prior@parent-2"


def test_heal_uses_article_date_not_retry_clock():
    """Item 9: a cron retry that heals the index stamps the article's own date."""
    from stage_6_post_review_and_decide import _handle_acceptance, GitHubAPI
    gh = Mock(spec=GitHubAPI)
    gh.get_issue_comments.return_value = []
    gh.path_exists.return_value = True
    gh.get_file_content.return_value = ('---\npaper_id: "2026-999"\ndate: "2026-10-30T15:02:23Z"\n---\nbody', "sha")
    with patch("stage_6_post_review_and_decide._update_indexes") as upd, \
         patch("stage_6_post_review_and_decide._verify_publish_succeeded_with_retry"):
        _handle_acceptance(gh=gh, review={"score": 7.0}, grounding={},
                           parsed_submission={"title": "T", "category": "ai/test", "author": "a"},
                           novelty_results={}, repo_data={}, paper_id="2026-999", issue_number=5,
                           repo_root="/nonexistent")
    assert upd.call_args.kwargs["now"] == datetime(2026, 10, 30, 15, 2, 23, tzinfo=timezone.utc)


def _git_data_fake(live_files):
    """Mock GitHubAPI whose contents/Git Data calls read and write `live_files`."""
    from stage_6_post_review_and_decide import GitHubAPI
    gh = Mock(spec=GitHubAPI)
    blobs, committed = {}, {}

    def get_file_content(path, branch="main"):
        if path not in live_files:
            raise requests.HTTPError(response=Mock(status_code=404))
        return live_files[path], "sha"

    def create_blob(content):
        key = f"b{len(blobs)}"; blobs[key] = content; return key

    def create_tree(base, items):
        committed.clear(); committed.update({i["path"]: blobs[i["sha"]] for i in items}); return "tree"

    gh.get_file_content.side_effect = get_file_content
    gh.get_ref_sha.return_value = "parent"
    gh.get_commit.return_value = {"tree": {"sha": "base"}}
    gh.create_blob.side_effect = create_blob
    gh.create_tree.side_effect = create_tree
    gh.create_commit.return_value = "commit"
    gh.update_ref.return_value = None
    return gh, committed


def _replay_inputs(paper_id):
    import yaml
    art = next(p for p in (REPO_ROOT / "papers").rglob("index.md") if f'paper_id: "{paper_id}"' in p.read_text())
    _, fm_txt, body = art.read_text().split("---\n", 2)
    fm = yaml.safe_load(fm_txt)
    man = json.loads((art.parent / "manifest.json").read_text())
    review = json.loads((REPO_ROOT / "reviews" / paper_id / "review.json").read_text())
    parsed = {"title": fm["title"], "category": fm["category"], "abstract": fm["abstract"],
              "body": body.lstrip("\n"), "author": fm["author"], "supporting_repo": man["supporting_repo"],
              "commit_sha": man["commit_sha"], "submission_type": "original-research",
              "word_count_body": man["word_count"], "ai_tooling_attribution": fm["ai_tooling_attribution"]}
    now = datetime.strptime(fm["date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return art, parsed, review, now


def _regen(root):
    import index_builder as IB
    return (IB.serialize_index(IB.build_agent_index(root / "papers", root, "https://pubroot.com")),
            IB.serialize_index(IB.build_priorroot_index(root / "papers", root, "https://pubroot.com")))


def _tree_without(tmp_path, paper_dir, paper_id):
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "papers", root / "papers", ignore=lambda d, n: [x for x in n if Path(d, x) == paper_dir])
    shutil.copytree(REPO_ROOT / "reviews", root / "reviews", ignore=lambda d, n: [paper_id] if Path(d) == REPO_ROOT / "reviews" else [])
    return root


def test_git_data_publish_replays_2026_274_byte_identical(tmp_path):
    """API-only replay of 2026-274 onto main-minus-274: committed indexes == regenerator."""
    from stage_6_post_review_and_decide import _upload_publication_files_to_branch
    art, parsed, review, now = _replay_inputs("2026-274")
    root = _tree_without(tmp_path, art.parent, "2026-274")
    a0, p0 = _regen(root)
    gh, committed = _git_data_fake({"agent-index.json": a0, "priorroot-index.json": p0})
    _upload_publication_files_to_branch(gh=gh, branch="main", review=review, grounding=review.get("grounding_metadata", {}),
                                        parsed_submission=parsed, novelty_results={}, repo_data={"badge_type": "text_only"},
                                        paper_id="2026-274", issue_number=1, repo_root=str(root), now=now)
    article_path = str(art.relative_to(REPO_ROOT))
    assert article_path in committed, sorted(committed)
    for path, content in committed.items():
        if not path.endswith("-index.json"):
            (root / path).parent.mkdir(parents=True, exist_ok=True); (root / path).write_text(content)
    ra, rp = _regen(root)
    assert committed["agent-index.json"] == ra
    assert committed["priorroot-index.json"] == rp
    assert '"2026-024"' not in committed["agent-index.json"]  # archived duplicate stays out


def test_git_data_publish_survives_stale_checkout(tmp_path):
    """The live index has 2026-274 but the local checkout does not: it must be kept."""
    from stage_6_post_review_and_decide import _upload_publication_files_to_branch
    art, parsed, review, now = _replay_inputs("2026-274")
    stale = _tree_without(tmp_path, art.parent, "2026-274")
    live = {"agent-index.json": (REPO_ROOT / "agent-index.json").read_text(),
            "priorroot-index.json": (REPO_ROOT / "priorroot-index.json").read_text()}
    gh, committed = _git_data_fake(live)
    new = dict(parsed, title="A brand new paper on stale checkouts", abstract="New.")
    _upload_publication_files_to_branch(gh=gh, branch="main", review=review, grounding={},
                                        parsed_submission=new, novelty_results={}, repo_data={"badge_type": "text_only"},
                                        paper_id="2026-901", issue_number=1, repo_root=str(stale), now=now)
    ids = {p["id"] for p in json.loads(committed["agent-index.json"])["papers"]}
    assert {"2026-274", "2026-901"} <= ids
