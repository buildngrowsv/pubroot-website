"""
Unit tests for the drain decision logic (B25 fix)

Tests all safety requirements:
1. No dispatch when the picker finds nothing (including picker errors)
2. No double review (issues already reviewed/published/rejected are filtered out)
3. Don't make the drop worse (don't dispatch if a run is already queued/pending)
4. No self-triggered loops (drain_depth cap is enforced)
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock, Mock
import pytest

# Add scripts to path to import drain_decision
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import drain_decision


class TestDrainDepthCap:
    """Test that the drain depth cap is enforced."""
    
    def test_at_cap_does_not_dispatch(self):
        """When drain_depth == drain_max, should not dispatch."""
        should_dispatch, reason = drain_decision.should_dispatch_review(
            token="fake-token",
            owner="test-owner",
            repo="test-repo",
            drain_depth=5,
            drain_max=5,
        )
        assert not should_dispatch
        assert "Drain depth 5 >= max 5" in reason
    
    def test_above_cap_does_not_dispatch(self):
        """When drain_depth > drain_max, should not dispatch."""
        should_dispatch, reason = drain_decision.should_dispatch_review(
            token="fake-token",
            owner="test-owner",
            repo="test-repo",
            drain_depth=6,
            drain_max=5,
        )
        assert not should_dispatch
        assert "Drain depth 6 >= max 5" in reason
    
    def test_below_cap_checks_other_conditions(self):
        """When drain_depth < drain_max, should check other conditions."""
        # This will fail on the pending runs check, but that's fine
        # We just need to verify it doesn't short-circuit on the depth check
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            mock_check.return_value = (True, "Found pending run")
            
            should_dispatch, reason = drain_decision.should_dispatch_review(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=3,
                drain_max=5,
            )
            assert not should_dispatch
            assert "Found pending run" in reason


class TestPendingRunsCheck:
    """Test that the drain doesn't dispatch if a run is already queued/pending."""
    
    def test_queued_run_blocks_dispatch(self):
        """If a queued run exists, should not dispatch."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            mock_check.return_value = (True, "Found 1 queued run(s): [12345]")
            
            should_dispatch, reason = drain_decision.should_dispatch_review(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=0,
                drain_max=5,
            )
            assert not should_dispatch
            assert "Found 1 queued run" in reason
    
    def test_in_progress_run_blocks_dispatch(self):
        """If an in_progress run exists, should not dispatch."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            mock_check.return_value = (True, "Found 1 in_progress run(s): [67890]")
            
            should_dispatch, reason = drain_decision.should_dispatch_review(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=0,
                drain_max=5,
            )
            assert not should_dispatch
            assert "Found 1 in_progress run" in reason
    
    def test_api_error_blocks_dispatch(self):
        """If the API call fails, should fail closed (not dispatch)."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            mock_check.return_value = (True, "API error checking queued runs: timeout")
            
            should_dispatch, reason = drain_decision.should_dispatch_review(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=0,
                drain_max=5,
            )
            assert not should_dispatch
            assert "API error" in reason
    
    def test_no_pending_runs_checks_picker(self):
        """If no pending runs, should check the picker."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                mock_check.return_value = (False, "No pending/queued/waiting runs found")
                mock_fetch.return_value = []  # No issues found
                
                should_dispatch, reason = drain_decision.should_dispatch_review(
                    token="fake-token",
                    owner="test-owner",
                    repo="test-repo",
                    drain_depth=0,
                    drain_max=5,
                )
                assert not should_dispatch
                assert "No open submission issues" in reason


class TestPickerNoIssues:
    """Test that no dispatch happens when the picker finds nothing."""
    
    def test_no_open_submissions(self):
        """If no open submission issues exist, should not dispatch."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                mock_check.return_value = (False, "No pending runs")
                mock_fetch.return_value = []
                
                should_dispatch, reason = drain_decision.should_dispatch_review(
                    token="fake-token",
                    owner="test-owner",
                    repo="test-repo",
                    drain_depth=0,
                    drain_max=5,
                )
                assert not should_dispatch
                assert "No open submission issues" in reason
    
    def test_all_issues_gated(self):
        """If all issues are gated, should not dispatch."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                with patch("drain_decision.pick_next") as mock_pick:
                    mock_check.return_value = (False, "No pending runs")
                    mock_fetch.return_value = [
                        {"number": 100, "title": "[SUBMISSION] Test", "labels": [], "user": {"login": "author1"}},
                        {"number": 101, "title": "[SUBMISSION] Test 2", "labels": [], "user": {"login": "author2"}},
                    ]
                    # pick_next returns (None, skipped_list) when no issue qualifies
                    mock_pick.return_value = (None, [(100, "gated"), (101, "gated")])
                    
                    should_dispatch, reason = drain_decision.should_dispatch_review(
                        token="fake-token",
                        owner="test-owner",
                        repo="test-repo",
                        drain_depth=0,
                        drain_max=5,
                    )
                    assert not should_dispatch
                    assert "no eligible issues" in reason
                    assert "2 skipped" in reason
    
    def test_picker_error_fails_closed(self):
        """If the picker throws an error, should fail closed (not dispatch)."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                mock_check.return_value = (False, "No pending runs")
                mock_fetch.side_effect = Exception("API timeout")
                
                should_dispatch, reason = drain_decision.should_dispatch_review(
                    token="fake-token",
                    owner="test-owner",
                    repo="test-repo",
                    drain_depth=0,
                    drain_max=5,
                )
                assert not should_dispatch
                assert "Picker error (fail closed)" in reason
                assert "API timeout" in reason


class TestPickerFindsIssue:
    """Test that dispatch happens when the picker finds an eligible issue."""
    
    def test_picker_finds_eligible_issue(self):
        """If the picker finds an eligible issue, should dispatch."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                with patch("drain_decision.pick_next") as mock_pick:
                    mock_check.return_value = (False, "No pending runs")
                    mock_fetch.return_value = [
                        {"number": 200, "title": "[SUBMISSION] Eligible", "labels": [], "user": {"login": "author"}},
                    ]
                    # pick_next returns (issue_number, skipped_list) when it finds one
                    mock_pick.return_value = (200, [])
                    
                    should_dispatch, reason = drain_decision.should_dispatch_review(
                        token="fake-token",
                        owner="test-owner",
                        repo="test-repo",
                        drain_depth=0,
                        drain_max=5,
                    )
                    assert should_dispatch
                    assert "issue #200" in reason
    
    def test_picker_finds_issue_after_skipping_some(self):
        """If the picker finds an issue after skipping some, should dispatch."""
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                with patch("drain_decision.pick_next") as mock_pick:
                    mock_check.return_value = (False, "No pending runs")
                    mock_fetch.return_value = [
                        {"number": 300, "title": "[SUBMISSION] Gated", "labels": [], "user": {"login": "author1"}},
                        {"number": 301, "title": "[SUBMISSION] Eligible", "labels": [], "user": {"login": "author2"}},
                    ]
                    # pick_next returns the second issue after skipping the first
                    mock_pick.return_value = (301, [(300, "gated")])
                    
                    should_dispatch, reason = drain_decision.should_dispatch_review(
                        token="fake-token",
                        owner="test-owner",
                        repo="test-repo",
                        drain_depth=0,
                        drain_max=5,
                    )
                    assert should_dispatch
                    assert "issue #301" in reason


class TestCheckPendingRuns:
    """Test the check_for_pending_or_queued_runs function directly."""
    
    def test_finds_queued_run(self):
        """Should detect queued runs."""
        with patch("requests.get") as mock_get:
            # Mock response for queued status
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "workflow_runs": [
                    {"id": 12345, "status": "queued"},
                ],
            }
            mock_get.return_value = mock_response
            
            has_pending, reason = drain_decision.check_for_pending_or_queued_runs(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
            )
            assert has_pending
            assert "queued" in reason
            assert "12345" in reason
    
    def test_finds_in_progress_run(self):
        """Should detect in_progress runs."""
        with patch("requests.get") as mock_get:
            # Mock responses: no queued, but has in_progress
            def side_effect(url, headers, params, timeout):
                mock_response = Mock()
                mock_response.status_code = 200
                if params["status"] == "queued":
                    mock_response.json.return_value = {"workflow_runs": []}
                elif params["status"] == "in_progress":
                    mock_response.json.return_value = {
                        "workflow_runs": [{"id": 67890, "status": "in_progress"}],
                    }
                else:
                    mock_response.json.return_value = {"workflow_runs": []}
                return mock_response
            
            mock_get.side_effect = side_effect
            
            has_pending, reason = drain_decision.check_for_pending_or_queued_runs(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
            )
            assert has_pending
            assert "in_progress" in reason
            assert "67890" in reason
    
    def test_no_pending_runs(self):
        """Should return False when no pending runs exist."""
        with patch("requests.get") as mock_get:
            # Mock responses: all empty
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"workflow_runs": []}
            mock_get.return_value = mock_response
            
            has_pending, reason = drain_decision.check_for_pending_or_queued_runs(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
            )
            assert not has_pending
            assert "No pending/queued/waiting runs found" in reason
    
    def test_api_error_fails_closed(self):
        """Should fail closed on API errors."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Network timeout")
            
            has_pending, reason = drain_decision.check_for_pending_or_queued_runs(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
            )
            assert has_pending  # Fail closed
            assert "API error" in reason
            assert "Network timeout" in reason


class TestNoDoubleReview:
    """
    Test that the picker logic (pick_next from dry_run_review_picker) correctly
    filters out issues that have already been reviewed, published, or rejected.
    
    Note: The actual filtering is implemented in dry_run_review_picker.pick_next,
    which excludes terminal labels and checks bot comments. These tests verify
    that the drain_decision.should_dispatch_review uses the same picker.
    """
    
    def test_accepted_issue_not_picked(self):
        """Issues with 'accepted' label should not be picked."""
        # This is handled by pick_next's is_terminal check
        # We verify that pick_next is called with the same logic
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                with patch("drain_decision.pick_next") as mock_pick:
                    mock_check.return_value = (False, "No pending runs")
                    mock_fetch.return_value = [
                        {
                            "number": 400,
                            "title": "[SUBMISSION] Accepted",
                            "labels": [{"name": "accepted"}],
                            "user": {"login": "author"},
                        },
                    ]
                    # pick_next should skip this issue (accepted is terminal)
                    mock_pick.return_value = (None, [(400, "has terminal label")])
                    
                    should_dispatch, reason = drain_decision.should_dispatch_review(
                        token="fake-token",
                        owner="test-owner",
                        repo="test-repo",
                        drain_depth=0,
                        drain_max=5,
                    )
                    assert not should_dispatch
                    assert "no eligible issues" in reason
    
    def test_issue_with_non_error_bot_comment_not_picked(self):
        """Issues with a non-error bot review comment should not be picked again."""
        # This is handled by pick_next's bot comment check
        with patch("drain_decision.check_for_pending_or_queued_runs") as mock_check:
            with patch("drain_decision.fetch_open_submission_issues") as mock_fetch:
                with patch("drain_decision.pick_next") as mock_pick:
                    mock_check.return_value = (False, "No pending runs")
                    mock_fetch.return_value = [
                        {
                            "number": 401,
                            "title": "[SUBMISSION] Reviewed",
                            "labels": [{"name": "submission"}],
                            "user": {"login": "author"},
                        },
                    ]
                    # pick_next should skip this issue (has non-error bot review)
                    mock_pick.return_value = (None, [(401, "has non-error bot review")])
                    
                    should_dispatch, reason = drain_decision.should_dispatch_review(
                        token="fake-token",
                        owner="test-owner",
                        repo="test-repo",
                        drain_depth=0,
                        drain_max=5,
                    )
                    assert not should_dispatch
                    assert "no eligible issues" in reason


class TestDispatchFunction:
    """Test the dispatch_review_workflow function."""
    
    def test_successful_dispatch(self):
        """Should return success when dispatch succeeds (204)."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            success, message = drain_decision.dispatch_review_workflow(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=2,
            )
            assert success
            assert "drain_depth=3" in message
            
            # Verify the POST call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "test-owner/test-repo" in call_args[0][0]
            assert call_args[1]["json"]["inputs"]["drain_depth"] == "3"
    
    def test_dispatch_increments_depth(self):
        """Should increment drain_depth in the dispatch."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            drain_decision.dispatch_review_workflow(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=0,
            )
            
            # Verify drain_depth is incremented
            call_args = mock_post.call_args
            assert call_args[1]["json"]["inputs"]["drain_depth"] == "1"
    
    def test_dispatch_api_error(self):
        """Should return failure on API errors."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            success, message = drain_decision.dispatch_review_workflow(
                token="fake-token",
                owner="test-owner",
                repo="test-repo",
                drain_depth=0,
            )
            assert not success
            assert "Dispatch failed" in message
            assert "Network error" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
