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
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime, timezone, timedelta

# Add _review_agent to path to import author_gating
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "_review_agent"))
from author_gating import evaluate_issue, fetch_issue, get_env


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


def pick_next(
    issues: List[Dict], 
    gate_fn: Callable[[Dict], Dict], 
    repo: str = "buildngrowsv/pubroot-website",
    token: str = "",
) -> Tuple[Optional[int], List[Tuple[int, str]]]:
    """
    Implement the three-tier picker logic from review.yml.
    
    Returns:
        (picked_issue_number, skipped_with_reasons) where skipped_with_reasons
        is a list of (issue_number, reason) tuples for issues that were checked
        but skipped due to gating or other filters.
    
    The picker has three tiers (checked in order):
    1. publish-failed (review passed, publish failed, should retry)
    2. priority-labelled (critical > high > normal > low)
    3. unreviewed submission (no bot review comment)
    """
    skipped = []
    
    def is_terminal(labels: List[str]) -> bool:
        """Check if issue has a terminal label."""
        return any(lbl in labels for lbl in ["accepted", "rejected", "validation-failed"])
    
    def is_excluded(labels: List[str]) -> bool:
        """Check if issue should be excluded from all tiers."""
        return any(lbl in labels for lbl in ["editorial-hold"])
    
    def extract_priority(labels: List[str]) -> Optional[str]:
        """Extract priority label from list."""
        for lbl in labels:
            if lbl.startswith("priority:"):
                return lbl
        return None
    
    def priority_sort_key(lbl: str) -> int:
        """Sort key for priority labels (critical < high < normal < low)."""
        return {"priority:critical": 0, "priority:high": 1, "priority:normal": 2, "priority:low": 3}.get(lbl, 9)
    
    # TIER 1: publish-failed
    tier1_candidates = []
    for issue in issues:
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        if "publish-failed" in labels and not is_excluded(labels):
            tier1_candidates.append(issue)
    
    for candidate in tier1_candidates:
        approval = gate_fn(candidate)
        if approval["approved"]:
            return candidate["number"], skipped
        skipped.append((candidate["number"], f"gated: {approval['reason']}"))
    
    # TIER 2: priority-labelled
    tier2_candidates = []
    for issue in issues:
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        priority = extract_priority(labels)
        if priority and not is_terminal(labels) and not is_excluded(labels) and "publish-failed" not in labels:
            tier2_candidates.append((issue, priority))
    
    # Sort by priority, then by issue number
    tier2_candidates.sort(key=lambda x: (priority_sort_key(x[1]), x[0]["number"]))
    
    for candidate, priority in tier2_candidates:
        approval = gate_fn(candidate)
        if approval["approved"]:
            return candidate["number"], skipped
        skipped.append((candidate["number"], f"gated: {approval['reason']}"))
    
    # TIER 3: unreviewed submissions (newest bot comment missing OR is error)
    # FIX (Bug B20 part 3): Check the NEWEST bot comment. Issue is eligible if:
    #   1. No bot comment at all, OR
    #   2. Newest bot comment is an error (review failed, publish failed, etc.)
    # This prevents repeat OpenRouter reviews after a successful non-error review.
    #
    # Exclude terminal labels: accepted, rejected, validation-failed, published, duplicate
    # Also exclude publish-failed (tier 1), review-error, pending-review, editorial-hold
    tier3_candidates = []
    for issue in issues:
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        terminal_or_excluded = [
            "accepted", "rejected", "validation-failed", "published", "duplicate",
            "publish-failed", "review-error", "pending-review", "editorial-hold"
        ]
        
        if ("submission" in labels 
            and not any(lbl in labels for lbl in terminal_or_excluded)
            and not any(lbl.startswith("priority:") for lbl in labels)):
            tier3_candidates.append(issue)
    
    for candidate in tier3_candidates:
        approval = gate_fn(candidate)
        if not approval["approved"]:
            skipped.append((candidate["number"], f"gated: {approval['reason']}"))
            continue
        
        # Check the newest bot comment
        # FIX (Bug B20 part 6): Paginate comments fetch with per_page=100
        comments_resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues/{candidate['number']}/comments",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"per_page": 100, "page": 1},
            timeout=30
        )
        if comments_resp.status_code == 200:
            comments = comments_resp.json()
            bot_comments = [
                c for c in comments
                if c.get("user", {}).get("login") == "github-actions[bot]"
            ]
            
            if bot_comments:
                # Get the newest bot comment
                newest_comment = bot_comments[-1]
                body = newest_comment.get("body", "")
                
                # Check if it's an error comment
                is_error = (
                    "# AI Peer Review — Error" in body
                    or "Submission Validation Failed" in body
                    or "Publication Failed" in body
                )
                
                if is_error:
                    # Eligible: newest comment is an error
                    return candidate["number"], skipped
                else:
                    # Has non-error review, skip
                    skipped.append((candidate["number"], "has non-error bot review"))
                    continue
            else:
                # No bot comments at all: eligible
                return candidate["number"], skipped
        else:
            # API error: skip this candidate
            skipped.append((candidate["number"], f"API error: {comments_resp.status_code}"))
    
    # TIER 4: 0-label fallback
    tier4_candidates = []
    for issue in issues:
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        if len(labels) == 0:
            tier4_candidates.append(issue)
    
    for candidate in tier4_candidates:
        approval = gate_fn(candidate)
        if approval["approved"]:
            return candidate["number"], skipped
        skipped.append((candidate["number"], f"gated: {approval['reason']}"))
    
    # No eligible issues found
    return None, skipped


def check_approval(token: str, issue: Dict) -> Dict:
    """
    Check if an issue is approved for review.
    
    Now imports the logic from author_gating.py to ensure consistency
    between the workflow and the dry-run script.
    
    Returns:
        - approved (bool): whether the issue can be reviewed
        - reason (str): why it was approved or gated
        - gate_type (str): kind from evaluate_issue
    """
    repo_root = os.getcwd()
    token_env, owner, repo = get_env()
    
    # Use the imported evaluate_issue function
    result = evaluate_issue(issue, repo_root, token, owner, repo)
    
    # Rename 'kind' to 'gate_type' for backward compatibility
    return {
        "approved": result["approved"],
        "reason": result["reason"],
        "gate_type": result.get("kind", "unknown"),
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
    
    # Run the picker to see what the cron would pick
    print("Running three-tier picker (matches review.yml cron logic)...")
    print()
    
    gate_fn = lambda issue: check_approval(token, issue)
    
    picked, skipped = pick_next(issues, gate_fn, repo="buildngrowsv/pubroot-website", token=token)
    
    if picked:
        picked_issue = next((iss for iss in issues if iss["number"] == picked), None)
        if picked_issue:
            print("🎯 NEXT CRON WOULD PICK:")
            print(f"  #{picked} - {picked_issue['title'][:80]}")
            print(f"  Author: @{picked_issue.get('user', {}).get('login', 'unknown')}")
            labels = [lbl["name"] for lbl in picked_issue.get("labels", [])]
            print(f"  Labels: {', '.join(labels) if labels else '(none)'}")
            print()
    else:
        print("🚫 NO ISSUE WOULD BE PICKED (all gated or none eligible)")
        print()
    
    if skipped:
        print(f"Skipped {len(skipped)} issues during picker scan:")
        for num, reason in skipped[:10]:
            print(f"  #{num}: {reason}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")
        print()
    
    print("=" * 80)
    
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
