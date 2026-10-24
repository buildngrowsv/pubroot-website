#!/usr/bin/env python3
"""
Dry-run script for the review pipeline picker.

PURPOSE:
    Shows which issues the review.yml cron picker would select today, without
    actually triggering any reviews or modifying any issues. This helps verify
    that the picker logic correctly identifies unreviewed [SUBMISSION] issues
    and doesn't double-process already-reviewed ones.

USAGE:
    python scripts/dry_run_review_picker.py
    
    Requires GITHUB_TOKEN environment variable for API access.

OUTPUT:
    Prints candidate issues in priority order, showing:
    - Issue number and title
    - Current labels
    - Whether it has a bot review comment (to detect already-reviewed issues)
    - Recommended action (process / skip / already reviewed)
"""

import os
import sys
import json
import requests
from typing import List, Dict, Optional


def get_github_token() -> str:
    """Get GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    return token


def fetch_open_submission_issues(token: str, repo: str = "buildngrowsv/pubroot-website") -> List[Dict]:
    """
    Fetch all open issues that have [SUBMISSION] in the title OR the submission label.
    
    This matches the intended picker logic: find submission issues regardless of their
    current label state.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    all_issues = []
    page = 1
    
    while True:
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {
            "state": "open",
            "per_page": 100,
            "page": page,
        }
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        
        issues = resp.json()
        if not issues:
            break
        
        # Filter for submissions: title starts with [SUBMISSION] OR has submission label
        for issue in issues:
            title = issue.get("title", "")
            labels = [lbl["name"] for lbl in issue.get("labels", [])]
            
            if title.startswith("[SUBMISSION]") or "submission" in labels:
                all_issues.append(issue)
        
        page += 1
    
    return all_issues


def has_bot_review_comment(token: str, repo: str, issue_number: int) -> bool:
    """
    Check if the issue has any comment from github-actions[bot] that looks like
    a review (contains "# AI Peer Review" or similar markers).
    
    A bot comment with these markers means the issue was already reviewed.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    
    comments = resp.json()
    
    for comment in comments:
        user = comment.get("user", {})
        login = user.get("login", "")
        body = comment.get("body", "")
        
        # Look for review comments from the bot
        # Review comments contain "# AI Peer Review" or "Submission Validation Failed"
        if login == "github-actions[bot]":
            if "# AI Peer Review" in body or "Submission Validation Failed" in body:
                return True
    
    return False


def categorize_issues(token: str, issues: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categorize issues into buckets:
    - unreviewed: No bot comment, should be processed
    - already_reviewed: Has bot comment and accepted/rejected/validation-failed label
    - in_progress: Has priority label, might be queued or in progress
    - publish_failed: Review passed but publish failed, should retry
    """
    buckets = {
        "unreviewed": [],
        "already_reviewed": [],
        "in_progress": [],
        "publish_failed": [],
    }
    
    for issue in issues:
        number = issue["number"]
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        
        # Check for terminal labels
        terminal_labels = {"accepted", "rejected", "validation-failed"}
        has_terminal = any(lbl in labels for lbl in terminal_labels)
        
        # Check for publish-failed (special case: should retry)
        if "publish-failed" in labels:
            buckets["publish_failed"].append(issue)
            continue
        
        # Check for bot comment
        has_comment = has_bot_review_comment(token, "buildngrowsv/pubroot-website", number)
        
        # Categorize
        if has_terminal:
            # Already reviewed and decided
            buckets["already_reviewed"].append(issue)
        elif has_comment:
            # Has a review comment but no terminal label (might be in progress)
            buckets["in_progress"].append(issue)
        elif any(lbl.startswith("priority:") for lbl in labels):
            # Has priority label but no review comment yet (queued or in progress)
            buckets["in_progress"].append(issue)
        else:
            # No comment, no priority label, no terminal label = unreviewed
            buckets["unreviewed"].append(issue)
    
    return buckets


def print_issue_summary(issue: Dict, category: str):
    """Print a summary of one issue."""
    number = issue["number"]
    title = issue["title"]
    labels = [lbl["name"] for lbl in issue.get("labels", [])]
    created = issue.get("created_at", "")
    
    print(f"  #{number:3d} | {created[:10]} | {title[:80]}")
    print(f"        Labels: {', '.join(labels) if labels else '(none)'}")
    print(f"        Action: {category}")
    print()


def main():
    token = get_github_token()
    
    print("=" * 80)
    print("DRY RUN: Review Pipeline Picker")
    print("=" * 80)
    print()
    print("Fetching open submission issues...")
    
    issues = fetch_open_submission_issues(token)
    print(f"Found {len(issues)} open submission issues")
    print()
    
    print("Categorizing issues...")
    buckets = categorize_issues(token, issues)
    print()
    
    # Print results by category
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    # 1. Publish-failed (highest priority)
    print(f"1. PUBLISH-FAILED (review passed, publish failed, should retry): {len(buckets['publish_failed'])}")
    if buckets["publish_failed"]:
        print()
        for issue in buckets["publish_failed"]:
            print_issue_summary(issue, "RETRY PUBLISH")
    else:
        print("   (none)")
    print()
    
    # 2. Unreviewed (the stuck submissions)
    print(f"2. UNREVIEWED (never processed, should be reviewed): {len(buckets['unreviewed'])}")
    if buckets["unreviewed"]:
        print()
        for issue in sorted(buckets["unreviewed"], key=lambda x: x["number"]):
            print_issue_summary(issue, "PROCESS NOW")
    else:
        print("   (none)")
    print()
    
    # 3. In progress
    print(f"3. IN PROGRESS (has priority label or review comment, not terminal): {len(buckets['in_progress'])}")
    if buckets["in_progress"]:
        print()
        for issue in buckets["in_progress"][:5]:  # Show first 5
            print_issue_summary(issue, "SKIP (in progress)")
        if len(buckets["in_progress"]) > 5:
            print(f"   ... and {len(buckets['in_progress']) - 5} more")
    else:
        print("   (none)")
    print()
    
    # 4. Already reviewed
    print(f"4. ALREADY REVIEWED (has terminal label): {len(buckets['already_reviewed'])}")
    if buckets["already_reviewed"]:
        # Count by terminal state
        accepted = sum(1 for i in buckets["already_reviewed"] if "accepted" in [lbl["name"] for lbl in i.get("labels", [])])
        rejected = sum(1 for i in buckets["already_reviewed"] if "rejected" in [lbl["name"] for lbl in i.get("labels", [])])
        validation_failed = sum(1 for i in buckets["already_reviewed"] if "validation-failed" in [lbl["name"] for lbl in i.get("labels", [])])
        
        print(f"   Accepted: {accepted} (should be CLOSED but are still open)")
        print(f"   Rejected: {rejected}")
        print(f"   Validation failed: {validation_failed}")
    else:
        print("   (none)")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total open submission issues: {len(issues)}")
    print(f"Would process now: {len(buckets['publish_failed']) + len(buckets['unreviewed'])}")
    print(f"  - Publish-failed retries: {len(buckets['publish_failed'])}")
    print(f"  - Unreviewed submissions: {len(buckets['unreviewed'])}")
    print()
    
    if buckets["unreviewed"]:
        print("STUCK ISSUES FOUND:")
        print("The following issues were never reviewed (likely cancelled by concurrency):")
        for issue in sorted(buckets["unreviewed"], key=lambda x: x["number"]):
            print(f"  #{issue['number']}")
        print()
    
    # Note about accepted issues still open
    accepted_open = sum(1 for i in buckets["already_reviewed"] if "accepted" in [lbl["name"] for lbl in i.get("labels", [])])
    if accepted_open > 0:
        print(f"NOTE: {accepted_open} accepted issues are still OPEN and should be closed.")
        print("      This will be fixed by updating stage_6 to close accepted issues.")
    print()


if __name__ == "__main__":
    main()
