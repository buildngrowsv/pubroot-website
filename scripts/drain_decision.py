#!/usr/bin/env python3
"""
Drain Decision Logic for Review Pipeline B25 Fix

PURPOSE:
    Implements the read-only, decide-only drain logic that runs after review jobs
    finish. Checks if at least one issue qualifies for review using the same picker
    logic and gates as the cron sweep, and decides whether to dispatch review.yml again.

SAFETY REQUIREMENTS:
    1. No dispatch when the picker finds nothing (including picker errors, which fail closed)
    2. No double review: issues already reviewed, published, or rejected are filtered out
    3. Don't make the drop worse: don't dispatch if a review.yml run is already queued/pending
    4. No self-triggered loops: respect the drain_depth cap (default 5)

USAGE:
    python scripts/drain_decision.py [--drain-depth N] [--drain-max N]
    
    Returns exit code 0 if should dispatch, 1 if should not dispatch.
    Logs the decision reason clearly.

ENVIRONMENT:
    GITHUB_TOKEN — required for API access
    GITHUB_REPOSITORY — owner/repo format
"""

import json
import os
import sys
from typing import Dict, Optional, List, Tuple
import requests

# Add _review_agent to path to import author_gating and dry_run_review_picker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "_review_agent"))
from author_gating import evaluate_issue, get_env

# Add scripts to path to import dry_run_review_picker
sys.path.insert(0, os.path.dirname(__file__))
from dry_run_review_picker import pick_next, fetch_open_submission_issues


def check_for_pending_or_queued_runs(
    token: str, owner: str, repo: str, workflow_id: str = "review.yml"
) -> Tuple[bool, str]:
    """
    Check if there are any pending, queued, or waiting review.yml runs.
    
    This prevents the drain from dispatching when a run is already queued,
    which would cause the drain's pending run to cancel the queued issue-event run
    (the same B25 drop we're trying to fix).
    
    Args:
        token: GitHub API token
        owner: Repo owner
        repo: Repo name
        workflow_id: Workflow file name (default: review.yml)
    
    Returns:
        (has_pending, reason) where has_pending=True if a run is queued/pending/waiting
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    # Get recent workflow runs for review.yml
    # Filter by status: queued, in_progress, or waiting
    # We check all three to be safe, even though the concurrency group mainly
    # affects queued runs. A run that's in_progress might have jobs still pending.
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
    
    for status in ["queued", "in_progress", "waiting"]:
        params = {
            "status": status,
            "per_page": 10,  # Only need to check if any exist
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            runs = data.get("workflow_runs", [])
            if runs:
                # Found at least one run with this status
                run_ids = [r["id"] for r in runs[:3]]
                return True, f"Found {len(runs)} {status} run(s): {run_ids}"
        except Exception as e:
            # API error: fail closed (don't dispatch)
            return True, f"API error checking {status} runs: {e}"
    
    # No pending/queued/waiting runs found
    return False, "No pending/queued/waiting runs found"


def should_dispatch_review(
    token: str,
    owner: str,
    repo: str,
    drain_depth: int = 0,
    drain_max: int = 5,
) -> Tuple[bool, str]:
    """
    Decide whether to dispatch review.yml again.
    
    This is the core drain decision function. It applies all safety requirements:
    1. Check drain_depth cap (fail closed if exceeded)
    2. Check for pending/queued runs (fail closed if found)
    3. Run picker logic (same as cron sweep)
    4. Fail closed on picker errors
    
    Args:
        token: GitHub API token
        owner: Repo owner
        repo: Repo name
        drain_depth: Current chain counter (incremented on each dispatch)
        drain_max: Hard cap for drain depth (default 5)
    
    Returns:
        (should_dispatch, reason) where should_dispatch=True if review.yml should be dispatched
    """
    # Safety check 1: Drain depth cap (prevent infinite loops)
    if drain_depth >= drain_max:
        return False, f"Drain depth {drain_depth} >= max {drain_max}, stopping chain"
    
    # Safety check 2: Check for pending/queued runs (prevent cancelling issue-event runs)
    has_pending, pending_reason = check_for_pending_or_queued_runs(token, owner, repo)
    if has_pending:
        return False, f"Not dispatching: {pending_reason}"
    
    # Safety check 3: Run picker logic (same as cron sweep)
    try:
        issues = fetch_open_submission_issues(token, repo=f"{owner}/{repo}")
        if not issues:
            return False, "No open submission issues found"
        
        # Use the same gate function as dry_run_review_picker
        repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
        
        def gate_fn(issue: Dict) -> Dict:
            """Check if an issue is approved for review (same as workflow)."""
            result = evaluate_issue(issue, repo_root, token, owner, repo)
            return {
                "approved": result["approved"],
                "reason": result["reason"],
                "gate_type": result.get("kind", "unknown"),
            }
        
        # Run the three-tier picker
        picked, skipped = pick_next(issues, gate_fn, repo=f"{owner}/{repo}", token=token)
        
        if picked:
            return True, f"Picker found issue #{picked}, dispatching review.yml"
        else:
            return False, f"Picker found no eligible issues ({len(skipped)} skipped)"
    
    except Exception as e:
        # Picker error: fail closed (don't dispatch)
        return False, f"Picker error (fail closed): {e}"


def dispatch_review_workflow(
    token: str,
    owner: str,
    repo: str,
    drain_depth: int,
) -> Tuple[bool, str]:
    """
    Dispatch the review.yml workflow with incremented drain_depth.
    
    This uses the GitHub Actions workflow_dispatch API to trigger review.yml
    with the drain_depth input incremented by 1.
    
    Args:
        token: GitHub API token
        owner: Repo owner
        repo: Repo name
        drain_depth: Current drain depth (will be incremented for the dispatch)
    
    Returns:
        (success, message) where success=True if dispatch succeeded
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/review.yml/dispatches"
    
    payload = {
        "ref": "main",  # Always dispatch on main
        "inputs": {
            "drain_depth": str(drain_depth + 1),  # Increment for the next run
        },
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        
        # 204 No Content = success
        if resp.status_code == 204:
            return True, f"Dispatched review.yml with drain_depth={drain_depth + 1}"
        else:
            return False, f"Unexpected status {resp.status_code}: {resp.text}"
    
    except Exception as e:
        return False, f"Dispatch failed: {e}"


def main():
    """
    Main entry point for the drain decision logic.
    
    Reads drain_depth and drain_max from command-line arguments or environment,
    makes the dispatch decision, and optionally dispatches if running in dispatch mode.
    
    Exit codes:
        0: Should dispatch (or did dispatch successfully in dispatch mode)
        1: Should not dispatch (or dispatch failed)
    """
    # Parse arguments
    drain_depth = 0
    drain_max = 5
    dispatch_mode = False
    
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--drain-depth" and i + 1 < len(sys.argv) - 1:
            drain_depth = int(sys.argv[i + 2])
        elif arg == "--drain-max" and i + 1 < len(sys.argv) - 1:
            drain_max = int(sys.argv[i + 2])
        elif arg == "--dispatch":
            dispatch_mode = True
    
    # Get environment
    try:
        token, owner, repo = get_env()
    except SystemExit:
        print("ERROR: GITHUB_TOKEN and GITHUB_REPOSITORY required", file=sys.stderr)
        sys.exit(1)
    
    # Make the decision
    should_dispatch, reason = should_dispatch_review(
        token, owner, repo, drain_depth, drain_max
    )
    
    # Log the decision
    print(f"Drain decision (depth {drain_depth}/{drain_max}): {reason}")
    
    if should_dispatch:
        print("Decision: DISPATCH review.yml")
        
        if dispatch_mode:
            # Actually dispatch the workflow
            success, message = dispatch_review_workflow(token, owner, repo, drain_depth)
            print(f"Dispatch result: {message}")
            sys.exit(0 if success else 1)
        else:
            # Dry-run mode: just indicate we would dispatch
            print("(Dry-run mode: would dispatch review.yml with drain_depth={})".format(drain_depth + 1))
            sys.exit(0)
    else:
        print("Decision: DO NOT DISPATCH")
        sys.exit(1)


if __name__ == "__main__":
    main()
