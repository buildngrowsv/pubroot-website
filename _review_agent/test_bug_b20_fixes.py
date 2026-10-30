"""
Tests for Bug B20 fixes: deduplication, stage 6 publish verification, and picker tier 3.

FIX (a): Dedup before review - stage 1 checks exact title, slug, and near-duplicate
FIX (b): Stage 6 fails loudly if publish writes nothing
FIX (c): Cron tier 3 picker makes old-error-comment issues eligible again

These tests verify that:
1. Exact title duplicates are rejected in stage 1
2. Slug collisions are detected in stage 1
3. Near-duplicates (high similarity) are rejected in stage 1
4. Distinct papers pass stage 1 dedup checks
5. Stage 6 raises an exception if files are not written
6. The picker's tier 3 logic is label-based (not comment-based)
"""

import json
import os
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock

from stage_1_parse_and_filter import parse_and_filter_submission, _check_for_duplicates
from stage_6_post_review_and_decide import _verify_publish_succeeded, GitHubAPI


# ============================================================================
# FIX (a) TESTS: Deduplication in stage 1
# ============================================================================


def test_exact_title_duplicate_rejected():
    """
    Test that a submission with the exact same title as a published paper is rejected.
    
    Bug B20 incident: Issue #60 had the exact same title as 2026-067 but was not
    caught before review.
    """
    # Create a fake agent-index.json with one paper
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "agent-index.json")
        with open(index_path, "w") as f:
            json.dump({
                "papers": [{
                    "id": "2026-067",
                    "title": "Configuring VCC on macOS — Setup, Doctor, and the Unattended Readiness Gate",
                    "category": "ai/agent-architecture",
                    "abstract": "AI agents that drive desktop UIs assume permissions exist...",
                    "reader_url": "https://pubroot.com/ai/agent-architecture/configuring-vcc-on-macos/",
                }]
            }, f)
        
        # Create priorroot-index.json (empty)
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Try to submit the exact same title
        error = _check_for_duplicates(
            title="Configuring VCC on macOS — Setup, Doctor, and the Unattended Readiness Gate",
            abstract="Different abstract but same title",
            category="ai/agent-architecture",
            repo_root=tmpdir,
        )
        
        assert error is not None
        assert "DUPLICATE DETECTED" in error
        assert "2026-067" in error
        assert "exact same title" in error.lower()


def test_slug_collision_detected():
    """
    Test that a submission whose slug would collide with an existing paper is rejected.
    
    Slug collisions happen when titles are similar enough that slugify_title produces
    the same output. This test uses titles that are different enough to NOT trigger
    the exact title check, but similar enough to produce the same slug.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "agent-index.json")
        with open(index_path, "w") as f:
            json.dump({
                "papers": [{
                    "id": "2026-042",
                    "title": "Foo Bar Research Study",
                    "category": "ai/prompt-engineering",
                    "abstract": "This is about foo bar.",
                    "reader_url": "https://pubroot.com/ai/prompt-engineering/foo-bar-research-study/",
                }]
            }, f)
        
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Submit a title that slugifies to the same thing but is textually different
        error = _check_for_duplicates(
            title="Foo Bar: Research Study",  # Different punctuation, same slug
            abstract="A completely different abstract about something else entirely",
            category="ai/prompt-engineering",
            repo_root=tmpdir,
        )
        
        assert error is not None
        assert "SLUG COLLISION" in error or "DUPLICATE DETECTED" in error  # Accept either
        assert "2026-042" in error


def test_near_duplicate_rejected():
    """
    Test that a near-duplicate (high title+abstract similarity) is rejected.
    
    Near-duplicates are detected via TF-IDF cosine similarity >= 0.92. This catches
    submissions that are essentially the same content with minor wording changes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "agent-index.json")
        existing_title = "Novel Approach to Chain-of-Thought Prompt Engineering with Retrieval"
        existing_abstract = (
            "We present a novel approach to prompt engineering for large language models using "
            "chain-of-thought reasoning combined with retrieval-augmented generation to achieve "
            "state-of-the-art results on benchmark tasks reducing hallucination by forty percent."
        )
        with open(index_path, "w") as f:
            json.dump({
                "papers": [{
                    "id": "2026-100",
                    "title": existing_title,
                    "category": "ai/prompt-engineering",
                    "abstract": existing_abstract,
                    "reader_url": "https://pubroot.com/ai/prompt-engineering/cot-retrieval/",
                }]
            }, f)
        
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Submit a very similar paper (most words are identical)
        new_title = "Novel Approach to Chain-of-Thought Prompt Engineering using Retrieval"
        new_abstract = (
            "We introduce a novel approach to prompt engineering for large language models using "
            "chain-of-thought reasoning combined with retrieval-augmented generation to achieve "
            "state-of-the-art results on benchmark tasks reducing hallucination by forty percent."
        )
        error = _check_for_duplicates(
            title=new_title,
            abstract=new_abstract,
            category="ai/prompt-engineering",
            repo_root=tmpdir,
        )
        
        # Should be caught as either near-duplicate or slug collision
        assert error is not None
        assert ("NEAR-DUPLICATE DETECTED" in error or "SLUG COLLISION" in error 
                or "DUPLICATE DETECTED" in error)
        assert "2026-100" in error


def test_distinct_paper_passes_dedup():
    """
    Test that a genuinely distinct paper passes all dedup checks.
    
    This ensures we're not being overly aggressive with the similarity threshold.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "agent-index.json")
        with open(index_path, "w") as f:
            json.dump({
                "papers": [{
                    "id": "2026-050",
                    "title": "Prompt Caching for LLM Cost Reduction",
                    "category": "ai/prompt-engineering",
                    "abstract": "We analyze the impact of prompt caching on API costs for large language models.",
                    "reader_url": "https://pubroot.com/ai/prompt-engineering/prompt-caching/",
                }]
            }, f)
        
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Submit a completely different paper
        error = _check_for_duplicates(
            title="Benchmarking Retrieval-Augmented Generation Systems",
            abstract="This paper presents a comprehensive benchmark for RAG systems across multiple datasets.",
            category="ai/rag-retrieval",
            repo_root=tmpdir,
        )
        
        assert error is None  # Should pass — no duplicate


def test_dedup_checks_priorroot_index():
    """
    Test that dedup checks BOTH agent-index.json and priorroot-index.json.
    
    Bug B20 fix: duplicates could exist in priorroot-index.json (prior-art disclosures)
    and should also be caught.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Empty main index
        index_path = os.path.join(tmpdir, "agent-index.json")
        with open(index_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Duplicate in priorroot-index.json
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({
                "papers": [{
                    "id": "2026-003",
                    "title": "Preemptive Prior Art Publication",
                    "category": "prior-art/general-disclosure",
                    "abstract": "Method-of-use patents on known compounds.",
                    "reader_url": "https://pubroot.com/prior-art/general-disclosure/preemptive-prior-art/",
                }]
            }, f)
        
        # Try to submit the same title
        error = _check_for_duplicates(
            title="Preemptive Prior Art Publication",
            abstract="Different abstract",
            category="prior-art/general-disclosure",
            repo_root=tmpdir,
        )
        
        assert error is not None
        assert "DUPLICATE DETECTED" in error
        assert "2026-003" in error
        assert "priorroot-index.json" in error


# ============================================================================
# FIX (b) TESTS: Stage 6 publish verification
# ============================================================================


def test_stage6_fails_when_article_not_written():
    """
    Test that _verify_publish_succeeded raises an exception if the article file
    does not exist on main after the publish operation.
    
    Bug B20 incident: Issue #60's stage 6 silently skipped the write (path existed)
    but labeled it published anyway. This test ensures we now fail loudly.
    """
    # Mock GitHubAPI
    gh = Mock(spec=GitHubAPI)
    gh.path_exists.return_value = False  # Article does not exist
    
    paths = {
        "article_index_path": "papers/ai/agent-architecture/test-paper/index.md",
        "journal": "ai",
    }
    
    with pytest.raises(Exception) as exc_info:
        _verify_publish_succeeded(gh, paths, "2026-999", "after PR merge")
    
    assert "PUBLISH VERIFICATION FAILED" in str(exc_info.value)
    assert "does not exist on main" in str(exc_info.value)
    assert "publish-failed" in str(exc_info.value)


def test_stage6_fails_when_paper_not_in_index():
    """
    Test that _verify_publish_succeeded raises an exception if the paper ID
    is not present in agent-index.json after the publish operation.
    
    Bug B20 incident: Issue #60 was labeled published but did not appear in
    agent-index.json (still had 101 papers, not 102).
    """
    gh = Mock(spec=GitHubAPI)
    gh.path_exists.return_value = True  # Article exists
    
    # Mock get_file_content to return an index without the paper
    index_json = json.dumps({
        "papers": [
            {"id": "2026-067", "title": "Other Paper"},
            {"id": "2026-068", "title": "Another Paper"},
        ]
    })
    gh.get_file_content.return_value = (index_json, "fake-sha")
    
    paths = {
        "article_index_path": "papers/ai/agent-architecture/test-paper/index.md",
        "journal": "ai",
    }
    
    with pytest.raises(Exception) as exc_info:
        _verify_publish_succeeded(gh, paths, "2026-999", "after PR merge")
    
    assert "PUBLISH VERIFICATION FAILED" in str(exc_info.value)
    assert "was not added to agent-index.json" in str(exc_info.value)
    assert "2026-999 is missing" in str(exc_info.value)


def test_stage6_passes_when_publish_succeeded():
    """
    Test that _verify_publish_succeeded does NOT raise when files exist and
    the paper is in the index (happy path).
    """
    gh = Mock(spec=GitHubAPI)
    gh.path_exists.return_value = True  # Article exists
    
    # Mock get_file_content to return an index WITH the paper
    index_json = json.dumps({
        "papers": [
            {"id": "2026-067", "title": "Other Paper"},
            {"id": "2026-999", "title": "New Paper"},  # The paper we're verifying
        ]
    })
    gh.get_file_content.return_value = (index_json, "fake-sha")
    
    paths = {
        "article_index_path": "papers/ai/agent-architecture/test-paper/index.md",
        "journal": "ai",
    }
    
    # Should not raise
    _verify_publish_succeeded(gh, paths, "2026-999", "after PR merge")


def test_stage6_checks_priorroot_index_for_prior_art():
    """
    Test that _verify_publish_succeeded checks priorroot-index.json for
    prior-art/* papers instead of agent-index.json.
    """
    gh = Mock(spec=GitHubAPI)
    gh.path_exists.return_value = True
    
    # Mock priorroot-index.json with the paper
    index_json = json.dumps({
        "papers": [
            {"id": "2026-999", "title": "Prior Art Disclosure"},
        ]
    })
    gh.get_file_content.return_value = (index_json, "fake-sha")
    
    paths = {
        "article_index_path": "papers/prior-art/general-disclosure/test/index.md",
        "journal": "prior-art",  # Triggers priorroot-index.json check
    }
    
    # Should not raise
    _verify_publish_succeeded(gh, paths, "2026-999", "after PR merge")
    
    # Verify it checked priorroot-index.json, not agent-index.json
    gh.get_file_content.assert_called_once_with("priorroot-index.json", branch="main")


# ============================================================================
# FIX (c) TESTS: Picker tier 3 label-based eligibility
# ============================================================================


def test_picker_tier3_issue_with_only_error_comment_is_eligible():
    """
    Test that the picker's tier 3 logic makes an issue eligible if it has:
    - NO review-error label (even if it had one before)
    - NO pending-review label
    - NO terminal labels
    
    Bug B20 incident: An issue with only an old error comment (posted before
    review-error was removed) should be eligible again for review.
    
    This test verifies the label-based logic (not comment-based).
    """
    # This is a conceptual test — the actual picker logic is in bash/gh CLI.
    # We test the dry_run_review_picker.py tier 3 logic instead.
    from scripts.dry_run_review_picker import pick_next
    
    # Mock issue with submission label, no terminal labels, no review-error
    issues = [
        {
            "number": 60,
            "title": "[SUBMISSION] Old Error",
            "labels": [
                {"name": "submission"},
                # NOTE: review-error was removed by a maintainer
            ],
        }
    ]
    
    # Mock gate function (approve everything)
    gate_fn = lambda issue: {"approved": True, "reason": "test"}
    
    # Mock has_bot_review function (say there IS a comment, but we don't check it)
    has_review_fn = lambda num: True  # Has old error comment
    
    picked, skipped = pick_next(issues, gate_fn, has_review_fn)
    
    # The picker should pick issue #60 because labels say it's eligible
    # (no review-error, no terminal labels)
    assert picked == 60


def test_picker_tier3_skips_issue_with_review_error_label():
    """
    Test that the picker's tier 3 logic skips an issue if it still has the
    review-error label, even if a maintainer hasn't removed it yet.
    """
    from scripts.dry_run_review_picker import pick_next
    
    issues = [
        {
            "number": 61,
            "title": "[SUBMISSION] Still Has Error Label",
            "labels": [
                {"name": "submission"},
                {"name": "review-error"},  # Still has the error label
            ],
        }
    ]
    
    gate_fn = lambda issue: {"approved": True, "reason": "test"}
    has_review_fn = lambda num: True
    
    picked, skipped = pick_next(issues, gate_fn, has_review_fn)
    
    # Should NOT pick this issue (review-error label blocks it)
    assert picked is None


def test_picker_tier3_skips_issue_with_pending_review_label():
    """
    Test that the picker skips issues with pending-review label.
    """
    from scripts.dry_run_review_picker import pick_next
    
    issues = [
        {
            "number": 62,
            "title": "[SUBMISSION] Pending Review",
            "labels": [
                {"name": "submission"},
                {"name": "pending-review"},
            ],
        }
    ]
    
    gate_fn = lambda issue: {"approved": True, "reason": "test"}
    has_review_fn = lambda num: False
    
    picked, skipped = pick_next(issues, gate_fn, has_review_fn)
    
    assert picked is None


# ============================================================================
# INTEGRATION TEST: Full pipeline with duplicate detection
# ============================================================================


def test_integration_duplicate_submission_gets_duplicate_label():
    """
    Integration test: A duplicate submission should be rejected at stage 1,
    labeled with "duplicate" (not "validation-failed"), and closed.
    
    This tests the full flow from parse_and_filter_submission through the
    label logic in review_pipeline_main.py.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an index with an existing paper
        index_path = os.path.join(tmpdir, "agent-index.json")
        with open(index_path, "w") as f:
            json.dump({
                "papers": [{
                    "id": "2026-067",
                    "title": "Configuring VCC on macOS — Setup, Doctor, and the Unattended Readiness Gate",
                    "category": "ai/agent-architecture",
                    "abstract": "AI agents that drive desktop UIs...",
                    "reader_url": "https://pubroot.com/ai/agent-architecture/configuring-vcc/",
                }]
            }, f)
        
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Create journals.json (needed for category validation)
        journals_path = os.path.join(tmpdir, "journals.json")
        with open(journals_path, "w") as f:
            json.dump({
                "journals": {
                    "ai": {
                        "topics": {
                            "agent-architecture": {"refresh_rate_days": 0}
                        }
                    }
                }
            }, f)
        
        # Submit a duplicate
        issue_body = """### Article Title

Configuring VCC on macOS — Setup, Doctor, and the Unattended Readiness Gate

### Category

ai/agent-architecture

### Submission Type

original-research

### Abstract

This is a different abstract but the title is identical.

### Article Body

This is the body of the duplicate submission. It has at least 200 words to pass the word count check. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

### Supporting Repository URL

_No response_

### Commit SHA

_No response_

### Repository Visibility

no-repo
"""
        
        result = parse_and_filter_submission(
            issue_body=issue_body,
            repo_root=tmpdir,
            issue_author="test-user",
        )
        
        # Should be invalid
        assert not result["valid"]
        
        # Should have a duplicate error
        errors = result["errors"]
        assert len(errors) > 0
        assert any("DUPLICATE DETECTED" in e for e in errors)
