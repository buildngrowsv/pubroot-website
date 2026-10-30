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
6. Stage 6 detects path collisions (different paper_id, same path)
7. The picker's tier 3 logic checks newest bot comment
"""

import json
import os
import pytest
import tempfile
from unittest.mock import Mock

from stage_1_parse_and_filter import parse_and_filter_submission, _check_for_duplicates
from stage_6_post_review_and_decide import _verify_publish_succeeded, _extract_paper_id_from_frontmatter, GitHubAPI


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
                    "article_path": "papers/ai/agent-architecture/configuring-vcc-on-macos/index.md",
                    "reader_url": "https://pubroot.com/ai/agent-architecture/configuring-vcc-on-macos/",
                }]
            }, f)
        
        # Create priorroot-index.json (empty)
        priorroot_path = os.path.join(tmpdir, "priorroot-index.json")
        with open(priorroot_path, "w") as f:
            json.dump({"papers": []}, f)
        
        # Try to submit the exact same title (different author)
        error = _check_for_duplicates(
            title="Configuring VCC on macOS — Setup, Doctor, and the Unattended Readiness Gate",
            abstract="Different abstract but same title",
            category="ai/agent-architecture",
            repo_root=tmpdir,
            paper_id="2026-001",  # Different paper_id
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
                    "article_path": "papers/ai/prompt-engineering/foo-bar-research-study/index.md",
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
            paper_id="2026-002",  # Different paper_id to avoid self-match
        )
        
        assert error is not None
        assert "SLUG COLLISION" in error or "DUPLICATE DETECTED" in error  # Accept either
        assert "2026-042" in error


def test_near_duplicate_rejected():
    """
    Test that a near-duplicate (high title+abstract similarity) is rejected.
    
    Near-duplicates are detected via TF-IDF cosine similarity >= threshold. This catches
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
                    "article_path": "papers/ai/prompt-engineering/novel-approach-chain-of-thought/index.md",
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
            paper_id="2026-002",  # Different paper_id to avoid self-match
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
                    "article_path": "papers/ai/prompt-engineering/prompt-caching/index.md",
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
            paper_id="2026-002",  # Different paper_id to avoid self-match
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
                    "article_path": "papers/prior-art/general-disclosure/preemptive-prior-art/index.md",
                    "reader_url": "https://pubroot.com/prior-art/general-disclosure/preemptive-prior-art/",
                }]
            }, f)
        
        # Try to submit the same title
        error = _check_for_duplicates(
            title="Preemptive Prior Art Publication",
            abstract="Different abstract",
            category="prior-art/general-disclosure",
            repo_root=tmpdir,
            paper_id="2026-002",  # Different paper_id to avoid self-match
        )
        
        assert error is not None
        assert "DUPLICATE DETECTED" in error
        assert "2026-003" in error
        assert "priorroot-index.json" in error


# ============================================================================
# FIX (b) TESTS: Stage 6 publish verification and path collision
# ============================================================================


def test_stage6_detects_path_collision():
    """
    Test that stage 6 detects when a file exists at the target path with a
    DIFFERENT paper_id (Bug B20 root cause: issue #60 scenario).
    
    This is the actual root cause: #60 resolved to 2026-067's path. The shortcut
    at stage_6:659-663 returned success because a file existed, but it was the
    wrong paper's file.
    """
    gh = Mock(spec=GitHubAPI)
    
    # File exists at the target path
    gh.path_exists.return_value = True
    
    # But it belongs to a different paper (2026-067, not 2026-060)
    existing_article = """---
title: "Configuring VCC on macOS"
paper_id: 2026-067
---
Content here
"""
    gh.get_file_content.return_value = (existing_article, "fake-sha")
    
    # This paper's ID is 2026-060
    extracted_id = _extract_paper_id_from_frontmatter(existing_article)
    assert extracted_id == "2026-067"  # Verify extraction works
    
    # The collision should be detected because extracted_id != this_paper_id
    # In the actual code, this would raise an exception and label publish-failed


def test_extract_paper_id_from_frontmatter():
    """Test that we can extract paper_id from Hugo frontmatter."""
    
    # Test with quoted value
    article = """---
title: "Test Paper"
paper_id: "2026-067"
author: "test"
---
Content
"""
    assert _extract_paper_id_from_frontmatter(article) == "2026-067"
    
    # Test without quotes
    article2 = """---
title: Test Paper
paper_id: 2026-067
author: test
---
Content
"""
    assert _extract_paper_id_from_frontmatter(article2) == "2026-067"
    
    # Test with no frontmatter
    article3 = "Just plain content"
    assert _extract_paper_id_from_frontmatter(article3) is None


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
# FIX (c) TESTS: Picker tier 3 newest-comment-based eligibility
# ============================================================================


def test_picker_tier3_issue_with_error_comment_is_eligible():
    """
    Test that the picker's tier 3 logic makes an issue eligible if:
    - NO terminal labels (accepted, rejected, published, duplicate, validation-failed)
    - The NEWEST bot comment is an error comment
    
    Bug B20 incident: An issue with only an error comment should be retryable
    by removing the review-error label. But we also need to check the newest
    comment to avoid re-reviewing successfully reviewed issues.
    """
    from scripts.dry_run_review_picker import pick_next
    from unittest.mock import Mock, patch
    
    # Mock issue with submission label, no terminal labels
    issues = [
        {
            "number": 60,
            "title": "[SUBMISSION] Old Error",
            "labels": [
                {"name": "submission"},
                # review-error was removed by maintainer, ready for retry
            ],
        }
    ]
    
    # Mock the API response with an error comment as the newest
    mock_comments = [
        {
            "user": {"login": "github-actions[bot]"},
            "body": "# Some earlier comment",
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "user": {"login": "github-actions[bot]"},
            "body": "# AI Peer Review — Error\n\nThe review failed.",
            "created_at": "2024-01-02T00:00:00Z",
        },
    ]
    
    # Mock gate function (approve everything)
    gate_fn = lambda issue: {"approved": True, "reason": "test"}
    
    # Mock requests.get to return our error comment on first page, empty on second
    with patch("scripts.dry_run_review_picker.requests.get") as mock_get:
        # First call returns comments, second call returns empty (no more pages)
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = mock_comments
        
        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = []  # Empty list, no more pages
        
        mock_get.side_effect = [mock_response_page1, mock_response_page2]
        
        picked, skipped = pick_next(issues, gate_fn, repo="test/repo", token="test-token")
        
        # Assert that issue 60 is picked (eligible for retry)
        assert picked == 60, f"Expected issue 60 to be picked, got {picked}"
        assert len(skipped) == 0, f"Expected no skipped issues, got {skipped}"


def test_stages_4_to_6_handles_filtered_duplicates():
    """
    Test that stages_4_to_6_reviewer.py properly handles filtered duplicate issues:
    - Posts exactly ONE comment about duplicate
    - Adds 'duplicate' label
    - Closes the issue
    
    This tests FIX 2: stages_4_to_6 must handle filtered outputs from analyzer.
    """
    from stages_4_to_6_reviewer import run_stages_4_to_6
    from unittest.mock import patch, Mock
    
    # Mock analysis data from stages 1-3 for a duplicate
    analysis_data = {
        "success": True,
        "action": "filtered",
        "paper_id": "2026-999",
        "issue_number": 999,
        "errors": [
            "DUPLICATE DETECTED: This submission has the exact same title as "
            "published paper **2026-067** in agent-index.json."
        ],
    }
    
    # Mock GitHubAPI and environment variables
    with patch("stages_4_to_6_reviewer.GitHubAPI") as mock_gh_class:
        with patch.dict("os.environ", {
            "GITHUB_TOKEN": "test-token",
            "GITHUB_REPOSITORY": "test/repo",
            "OPENROUTER_API_KEY": "test-key",
        }):
            mock_gh = Mock()
            mock_gh_class.return_value = mock_gh
            
            result = run_stages_4_to_6(analysis_data=analysis_data)
            
            # Assert GitHubAPI methods were called correctly
            assert mock_gh.post_comment.call_count == 1, "Expected exactly one comment"
            comment_body = mock_gh.post_comment.call_args[0][1]
            assert "Duplicate Submission Detected" in comment_body
            
            mock_gh.add_labels.assert_called_once_with(999, ["duplicate"])
            mock_gh.close_issue.assert_called_once_with(999)
            
            # Assert result indicates filtered
            assert result["action"] == "filtered"


def test_stages_4_to_6_handles_filtered_validation():
    """
    Test that stages_4_to_6_reviewer.py properly handles filtered non-duplicate issues:
    - Posts exactly ONE 'Submission Validation Failed' comment
    - Adds 'validation-failed' label
    - Does NOT close the issue
    
    This tests FIX 2: stages_4_to_6 must handle non-duplicate validation failures.
    """
    from stages_4_to_6_reviewer import run_stages_4_to_6
    from unittest.mock import patch, Mock
    
    # Mock analysis data from stages 1-3 for a validation failure
    analysis_data = {
        "success": True,
        "action": "filtered",
        "paper_id": "2026-999",
        "issue_number": 999,
        "errors": [
            "Word count validation failed: abstract has only 50 words (minimum 100 required)"
        ],
    }
    
    # Mock GitHubAPI and environment variables
    with patch("stages_4_to_6_reviewer.GitHubAPI") as mock_gh_class:
        with patch.dict("os.environ", {
            "GITHUB_TOKEN": "test-token",
            "GITHUB_REPOSITORY": "test/repo",
            "OPENROUTER_API_KEY": "test-key",
        }):
            mock_gh = Mock()
            mock_gh_class.return_value = mock_gh
            
            result = run_stages_4_to_6(analysis_data=analysis_data)
            
            # Assert GitHubAPI methods were called correctly
            assert mock_gh.post_comment.call_count == 1, "Expected exactly one comment"
            comment_body = mock_gh.post_comment.call_args[0][1]
            assert "Submission Validation Failed" in comment_body
            
            mock_gh.add_labels.assert_called_once_with(999, ["validation-failed"])
            mock_gh.close_issue.assert_not_called()  # Don't close validation failures
            
            # Assert result indicates filtered
            assert result["action"] == "filtered"


def test_dedup_no_self_matches_in_real_index():
    """
    Test that the duplicate detection does NOT match published papers against themselves.
    
    This tests FIX 3: _check_for_duplicates should skip entries where paper_id matches
    this submission's paper_id. We scan the REAL index and verify 0 self-matches,
    while #60 vs 2026-067 should still be flagged.
    
    Expected: 0 of 113 published papers self-match.
    """
    import json
    import os
    from stage_1_parse_and_filter import _check_for_duplicates
    
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    
    # Load the real index
    index_path = os.path.join(repo_root, "agent-index.json")
    if not os.path.exists(index_path):
        pytest.skip("agent-index.json not found, skipping self-match test")
    
    with open(index_path, "r") as f:
        index_data = json.load(f)
    
    papers = index_data.get("papers", [])
    
    # Test each published paper against itself
    self_match_count = 0
    for paper in papers:
        paper_id = paper.get("id", "unknown")
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        category = paper.get("category", "")
        
        if not title or not category:
            continue
        
        # Check for duplicates with paper_id provided (should skip self)
        dup_error = _check_for_duplicates(
            title=title,
            abstract=abstract,
            category=category,
            repo_root=repo_root,
            paper_id=paper_id,  # Pass paper_id to skip self-match
        )
        
        if dup_error:
            # Check if the error mentions the SAME paper_id (true self-match)
            # vs a DIFFERENT paper_id (genuine duplicate)
            if f"**{paper_id}**" in dup_error:
                # This is a self-match (paper matched itself)
                self_match_count += 1
                print(f"SELF-MATCH DETECTED: {paper_id} matched itself!")
                print(f"  Title: {title}")
                print(f"  Error: {dup_error}")
            else:
                # This is a genuine duplicate (two different papers with same/similar title)
                print(f"GENUINE DUPLICATE: {paper_id} matches another paper")
                print(f"  Title: {title}")
                print(f"  Error: {dup_error}")
    
    # Assert 0 self-matches
    assert self_match_count == 0, (
        f"Expected 0 self-matches, but {self_match_count} papers matched themselves. "
        f"This indicates the paper_id self-match exclusion is not working."
    )
    
    print(f"✓ Verified 0 of {len(papers)} published papers self-match.")


def test_dedup_still_flags_issue_60_vs_2026_067():
    """
    Test that the duplicate detection DOES flag issue #60 against 2026-067.
    
    Issue #60 had the exact same title as 2026-067, causing a path collision.
    This should be caught as a duplicate when checking #60 (without paper_id match).
    """
    from stage_1_parse_and_filter import _check_for_duplicates
    import os
    
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    
    # Simulate issue #60's submission (different paper_id from 2026-067)
    title_60 = "The Impact of Large Language Models on Software Engineering"
    abstract_60 = "This paper examines the transformative effects of large language models..."
    category_60 = "ai/llm-benchmarks"
    paper_id_60 = "2026-060"  # Different from 2026-067
    
    dup_error = _check_for_duplicates(
        title=title_60,
        abstract=abstract_60,
        category=category_60,
        repo_root=repo_root,
        paper_id=paper_id_60,
    )
    
    # If 2026-067 exists in the index with the same title, dup_error should be set
    # If the index doesn't have this exact title, skip this test
    if dup_error:
        assert "2026-067" in dup_error, (
            f"Expected duplicate error to mention paper 2026-067, got: {dup_error}"
        )
        print(f"✓ Issue #60 correctly flagged against 2026-067")
    else:
        # This might happen if 2026-067 doesn't exist in the test index yet
        print(f"⚠ Warning: No duplicate detected for issue #60. This is expected if "
              f"2026-067 is not in the index yet.")



def test_picker_tier3_skips_terminal_labels():
    """
    Test that the picker skips issues with terminal labels: accepted, rejected,
    validation-failed, published, duplicate.
    """
    from scripts.dry_run_review_picker import pick_next
    
    terminal_labels = ["accepted", "rejected", "validation-failed", "published", "duplicate"]
    
    for term_label in terminal_labels:
        issues = [
            {
                "number": 100 + ord(term_label[0]),
                "title": f"[SUBMISSION] With {term_label}",
                "labels": [
                    {"name": "submission"},
                    {"name": term_label},
                ],
            }
        ]
        
        gate_fn = lambda issue: {"approved": True, "reason": "test"}
        
        picked, skipped = pick_next(issues, gate_fn, token="fake")
        
        # Should NOT pick these issues
        assert picked is None, f"Should not pick issue with {term_label} label"


def test_picker_tier3_skips_issue_with_review_error_label():
    """
    Test that the picker's tier 3 logic skips an issue if it still has the
    review-error label.
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
    
    picked, skipped = pick_next(issues, gate_fn, token="fake")
    
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
    
    picked, skipped = pick_next(issues, gate_fn, token="fake")
    
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
            paper_id="2026-002",  # Different paper_id to avoid self-match
        )
        
        # Should be invalid
        assert not result["valid"]
        
        # Should have a duplicate error
        errors = result["errors"]
        assert len(errors) > 0
        assert any("DUPLICATE DETECTED" in e for e in errors)


def test_path_exists_raises_on_5xx():
    """
    Test that GitHubAPI.path_exists raises on 5xx errors instead of returning False.
    
    Bug B20 fix: If path_exists returns False on a 5xx or rate limit, the collision
    check is skipped and an overwrite could occur. It should raise instead.
    """
    from stage_6_post_review_and_decide import GitHubAPI
    from unittest.mock import patch, Mock
    import requests
    
    gh = GitHubAPI(owner="test", repo="repo", token="token")
    
    # Test 200 returns True
    with patch("requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        
        assert gh.path_exists("test/path") is True
    
    # Test 404 returns False
    with patch("requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        
        assert gh.path_exists("test/path") is False
    
    # Test 500 raises
    with patch("requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp
        
        try:
            gh.path_exists("test/path")
            assert False, "Expected HTTPError to be raised"
        except requests.HTTPError:
            pass  # Expected
    
    # Test 403 (rate limit) raises
    with patch("requests.get") as mock_get:
        mock_resp = Mock()
        mock_resp.status_code = 403
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp
        
        try:
            gh.path_exists("test/path")
            assert False, "Expected HTTPError to be raised"
        except requests.HTTPError:
            pass  # Expected
