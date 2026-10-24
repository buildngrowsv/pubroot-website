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
from datetime import datetime, timezone, timedelta


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


def is_repo_collaborator(token: str, username: str) -> bool:
    """Check if a user is a repo collaborator."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/buildngrowsv/pubroot-website/collaborators/{username}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.status_code == 204
    except:
        return False


def is_on_allowlist(username: str) -> bool:
    """Check if a user is on the pre-approved allowlist."""
    allowlist_path = ".github/REVIEW_ALLOWLIST.txt"
    
    if not os.path.exists(allowlist_path):
        return False
    
    try:
        with open(allowlist_path, "r") as f:
            allowed = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
        return username.lower() in allowed
    except:
        return False


def check_rate_limit(token: str, author: str, limit: int = 3) -> tuple[bool, int]:
    """Check if an author has exceeded their daily submission cap."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    
    url = "https://api.github.com/repos/buildngrowsv/pubroot-website/issues"
    params = {
        "creator": author,
        "state": "all",
        "since": since,
        "per_page": 100,
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        issues = resp.json()
        
        submission_count = sum(1 for issue in issues if issue.get("title", "").startswith("[SUBMISSION]"))
        
        return submission_count < limit, submission_count
    except:
        return True, 0


def check_approval(token: str, issue: Dict) -> Dict:
    """
    Check if an issue is approved for review.
    
    Returns:
        - approved (bool): whether the issue can be reviewed
        - reason (str): why it was approved or gated
        - gate_type (str): "collaborator", "allowlist", "approved-label", "gated", "editorial-hold"
    """
    number = issue["number"]
    author = issue.get("user", {}).get("login", "unknown")
    labels = [lbl["name"] for lbl in issue.get("labels", [])]
    
    # Check editorial-hold first (always blocks)
    if "editorial-hold" in labels:
        return {
            "approved": False,
            "reason": "editorial-hold label present",
            "gate_type": "editorial-hold",
        }
    
    # Check if repo collaborator (auto-approved)
    if is_repo_collaborator(token, author):
        return {
            "approved": True,
            "reason": "repo collaborator",
            "gate_type": "collaborator",
        }
    
    # Check if on allowlist (auto-approved)
    if is_on_allowlist(author):
        return {
            "approved": True,
            "reason": "on allowlist",
            "gate_type": "allowlist",
        }
    
    # Check if has approval label
    if "approved-for-review" in labels:
        # Also check rate limit
        allowed, count = check_rate_limit(token, author)
        if not allowed:
            return {
                "approved": False,
                "reason": f"rate limit exceeded ({count}/3 submissions in 24h)",
                "gate_type": "rate-limited",
            }
        
        return {
            "approved": True,
            "reason": "approved-for-review label present",
            "gate_type": "approved-label",
        }
    
    # Not approved
    return {
        "approved": False,
        "reason": "requires approved-for-review label from maintainer",
        "gate_type": "gated",
    }


def categorize_issues(token: str, issues: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categorize issues into buckets:
    - unreviewed_approved: No bot comment, passes approval gate
    - unreviewed_gated: No bot comment, needs approval
    - editorial_hold: Has editorial-hold label
    - already_reviewed: Has bot comment and accepted/rejected/validation-failed label
    - in_progress: Has priority label, might be queued or in progress
    - publish_failed: Review passed but publish failed, should retry
    """
    buckets = {
        "unreviewed_approved": [],
        "unreviewed_gated": [],
        "editorial_hold": [],
        "already_reviewed": [],
        "in_progress": [],
        "publish_failed": [],
    }
    
    for issue in issues:
        number = issue["number"]
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        
        # Check for editorial-hold first
        if "editorial-hold" in labels:
            buckets["editorial_hold"].append((issue, None))
            continue
        
        # Check for terminal labels
        terminal_labels = {"accepted", "rejected", "validation-failed"}
        has_terminal = any(lbl in labels for lbl in terminal_labels)
        
        # Check for publish-failed (special case: should retry)
        if "publish-failed" in labels:
            approval = check_approval(token, issue)
            buckets["publish_failed"].append((issue, approval))
            continue
        
        # Check for bot comment
        has_comment = has_bot_review_comment(token, "buildngrowsv/pubroot-website", number)
        
        # Categorize
        if has_terminal:
            # Already reviewed and decided
            buckets["already_reviewed"].append((issue, None))
        elif has_comment:
            # Has a review comment but no terminal label (might be in progress)
            buckets["in_progress"].append((issue, None))
        elif any(lbl.startswith("priority:") for lbl in labels):
            # Has priority label but no review comment yet (queued or in progress)
            buckets["in_progress"].append((issue, None))
        else:
            # No comment, no priority label, no terminal label = unreviewed
            # Check approval gate
            approval = check_approval(token, issue)
            if approval["approved"]:
                buckets["unreviewed_approved"].append((issue, approval))
            else:
                buckets["unreviewed_gated"].append((issue, approval))
    
    return buckets


def print_issue_summary(issue: Dict, category: str, approval: Optional[Dict] = None):
    """Print a summary of one issue."""
    number = issue["number"]
    title = issue["title"]
    labels = [lbl["name"] for lbl in issue.get("labels", [])]
    created = issue.get("created_at", "")
    author = issue.get("user", {}).get("login", "unknown")
    
    print(f"  #{number:3d} | {created[:10]} | @{author:15s} | {title[:60]}")
    print(f"        Labels: {', '.join(labels) if labels else '(none)'}")
    print(f"        Action: {category}")
    
    if approval:
        gate_emoji = {
            "collaborator": "✅",
            "allowlist": "✅",
            "approved-label": "🔓",
            "gated": "🔒",
            "editorial-hold": "⏸️",
            "rate-limited": "⏱️",
        }.get(approval.get("gate_type", "unknown"), "❓")
        
        print(f"        Gate: {gate_emoji} {approval['reason']}")
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
    print("RESULTS (with gating)")
    print("=" * 80)
    print()
    
    # 1. Publish-failed (highest priority)
    print(f"1. PUBLISH-FAILED (review passed, publish failed, should retry): {len(buckets['publish_failed'])}")
    if buckets["publish_failed"]:
        print()
        approved_count = sum(1 for _, approval in buckets["publish_failed"] if approval and approval["approved"])
        gated_count = len(buckets["publish_failed"]) - approved_count
        print(f"   Approved: {approved_count}, Gated: {gated_count}")
        print()
        for issue, approval in buckets["publish_failed"]:
            print_issue_summary(issue, "RETRY PUBLISH", approval)
    else:
        print("   (none)")
    print()
    
    # 2. Unreviewed and approved (will be processed)
    print(f"2. UNREVIEWED & APPROVED (never processed, passes gate, WILL BE REVIEWED): {len(buckets['unreviewed_approved'])}")
    if buckets["unreviewed_approved"]:
        print()
        for issue, approval in sorted(buckets["unreviewed_approved"], key=lambda x: x[0]["number"]):
            print_issue_summary(issue, "PROCESS NOW", approval)
    else:
        print("   (none)")
    print()
    
    # 3. Unreviewed but gated (needs approval)
    print(f"3. UNREVIEWED & GATED (never processed, needs maintainer approval): {len(buckets['unreviewed_gated'])}")
    if buckets["unreviewed_gated"]:
        print()
        print("   These issues will NOT be reviewed until a maintainer adds the 'approved-for-review' label:")
        print()
        for issue, approval in sorted(buckets["unreviewed_gated"], key=lambda x: x[0]["number"]):
            print_issue_summary(issue, "SKIP (gated)", approval)
    else:
        print("   (none)")
    print()
    
    # 4. Editorial hold
    print(f"4. EDITORIAL HOLD (maintainer-blocked): {len(buckets['editorial_hold'])}")
    if buckets["editorial_hold"]:
        print()
        print("   These issues are on hold pending editorial decision:")
        print()
        for issue, _ in buckets["editorial_hold"][:5]:
            author = issue.get("user", {}).get("login", "unknown")
            print(f"  #{issue['number']:3d} | @{author}")
        if len(buckets["editorial_hold"]) > 5:
            print(f"   ... and {len(buckets['editorial_hold']) - 5} more")
    else:
        print("   (none)")
    print()
    
    # 5. In progress
    print(f"5. IN PROGRESS (has priority label or review comment, not terminal): {len(buckets['in_progress'])}")
    if buckets["in_progress"]:
        print()
        for issue, _ in buckets["in_progress"][:5]:  # Show first 5
            print_issue_summary(issue, "SKIP (in progress)", None)
        if len(buckets["in_progress"]) > 5:
            print(f"   ... and {len(buckets['in_progress']) - 5} more")
    else:
        print("   (none)")
    print()
    
    # 6. Already reviewed
    print(f"6. ALREADY REVIEWED (has terminal label): {len(buckets['already_reviewed'])}")
    if buckets["already_reviewed"]:
        # Count by terminal state
        accepted = sum(1 for issue, _ in buckets["already_reviewed"] if "accepted" in [lbl["name"] for lbl in issue.get("labels", [])])
        rejected = sum(1 for issue, _ in buckets["already_reviewed"] if "rejected" in [lbl["name"] for lbl in issue.get("labels", [])])
        validation_failed = sum(1 for issue, _ in buckets["already_reviewed"] if "validation-failed" in [lbl["name"] for lbl in issue.get("labels", [])])
        
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
    print(f"Would process now: {len(buckets['publish_failed']) + len(buckets['unreviewed_approved'])}")
    print(f"  - Publish-failed retries: {len(buckets['publish_failed'])}")
    print(f"  - Unreviewed & approved: {len(buckets['unreviewed_approved'])}")
    print(f"Blocked by gating: {len(buckets['unreviewed_gated'])}")
    print(f"Editorial hold: {len(buckets['editorial_hold'])}")
    print()
    
    if buckets["unreviewed_approved"]:
        print("APPROVED STUCK ISSUES (will be auto-reviewed):")
        for issue, approval in sorted(buckets["unreviewed_approved"], key=lambda x: x[0]["number"]):
            gate_type = approval.get("gate_type", "unknown")
            print(f"  #{issue['number']:3d} ({gate_type})")
        print()
    
    if buckets["unreviewed_gated"]:
        print("GATED STUCK ISSUES (need maintainer approval):")
        for issue, _ in sorted(buckets["unreviewed_gated"], key=lambda x: x[0]["number"]):
            author = issue.get("user", {}).get("login", "unknown")
            print(f"  #{issue['number']:3d} @{author}")
        print()
        print("ACTION REQUIRED: Add 'approved-for-review' label to gate these through, or")
        print("                 add 'editorial-hold' to explicitly mark them pending decision.")
    
    # Note about accepted issues still open
    accepted_open = sum(1 for issue, _ in buckets["already_reviewed"] if "accepted" in [lbl["name"] for lbl in issue.get("labels", [])])
    if accepted_open > 0:
        print()
        print(f"NOTE: {accepted_open} accepted issues are still OPEN and should be closed.")
        print("      Going forward, stage_6 will close them automatically.")
    print()


if __name__ == "__main__":
    main()
