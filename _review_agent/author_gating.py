"""
Author Gating and Rate Limiting for Pubroot Review Pipeline

PURPOSE:
    Prevents untrusted submissions from burning Gemini API quota and GitHub Actions
    minutes. Requires maintainer approval for first-time or non-collaborator authors.
    
GATING RULES:
    1. Repo collaborators (write access or higher) are auto-approved
    2. Authors on the allowlist file are auto-approved
    3. All other authors need `approved-for-review` label applied by a maintainer
    4. Issues with `editorial-hold` label are always skipped
    5. Per-author daily submission cap (default: 3 per 24 hours)

USAGE:
    python author_gating.py check <issue_number>
    python author_gating.py check-rate-limit <author>
    
    Returns exit code 0 if approved, 1 if gated.

ENVIRONMENT:
    GITHUB_TOKEN — required for API access
    GITHUB_REPOSITORY — owner/repo format
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import requests


def get_env() -> tuple[str, str, str]:
    """Get required environment variables."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    
    if not token or not repo:
        print("ERROR: GITHUB_TOKEN and GITHUB_REPOSITORY required")
        sys.exit(1)
    
    if "/" not in repo:
        print(f"ERROR: Invalid GITHUB_REPOSITORY format: {repo}")
        sys.exit(1)
    
    owner, repo_name = repo.split("/", 1)
    return token, owner, repo_name


def is_repo_collaborator(token: str, owner: str, repo: str, username: str) -> bool:
    """
    Check if a user is a repo collaborator (has write access or higher).
    
    Collaborators are auto-approved because they already have the ability to
    modify the repository directly.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    # Check collaborator status
    # https://docs.github.com/en/rest/collaborators/collaborators#check-if-a-user-is-a-repository-collaborator
    url = f"https://api.github.com/repos/{owner}/{repo}/collaborators/{username}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        # 204 = is a collaborator, 404 = not a collaborator
        return resp.status_code == 204
    except Exception as e:
        print(f"WARNING: Failed to check collaborator status: {e}")
        return False


def is_on_allowlist(username: str, repo_root: str) -> bool:
    """
    Check if a user is on the pre-approved allowlist.
    
    The allowlist file is .github/REVIEW_ALLOWLIST.txt (one username per line).
    This allows maintainers to pre-approve trusted contributors.
    """
    allowlist_path = os.path.join(repo_root, ".github", "REVIEW_ALLOWLIST.txt")
    
    if not os.path.exists(allowlist_path):
        return False
    
    try:
        with open(allowlist_path, "r") as f:
            allowed = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
        return username.lower() in allowed
    except Exception as e:
        print(f"WARNING: Failed to read allowlist: {e}")
        return False


def has_approval_label(token: str, owner: str, repo: str, issue_number: int) -> bool:
    """
    Check if the issue has the `approved-for-review` label.
    
    This label must be applied by a maintainer to gate untrusted submissions.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        issue = resp.json()
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        return "approved-for-review" in labels
    except Exception as e:
        print(f"ERROR: Failed to fetch issue labels: {e}")
        return False


def has_editorial_hold(token: str, owner: str, repo: str, issue_number: int) -> bool:
    """
    Check if the issue has the `editorial-hold` label.
    
    Issues with this label are always skipped by the picker, regardless of
    approval status. This allows maintainers to temporarily block submissions.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        issue = resp.json()
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        return "editorial-hold" in labels
    except Exception as e:
        print(f"ERROR: Failed to fetch issue labels: {e}")
        return False


def get_issue_author(token: str, owner: str, repo: str, issue_number: int) -> Optional[str]:
    """Get the issue author's username."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        issue = resp.json()
        return issue.get("user", {}).get("login")
    except Exception as e:
        print(f"ERROR: Failed to fetch issue: {e}")
        return None


def check_rate_limit(token: str, owner: str, repo: str, author: str, limit: int = 3) -> tuple[bool, int, int]:
    """
    Check if an author has exceeded their daily submission cap.
    
    Returns:
        (allowed, count_today, limit) where allowed=True if under the cap
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    # Get issues created by this author in the last 24 hours
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
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
        
        # Count only [SUBMISSION] issues
        submission_count = sum(1 for issue in issues if issue.get("title", "").startswith("[SUBMISSION]"))
        
        return submission_count < limit, submission_count, limit
    except Exception as e:
        print(f"WARNING: Failed to check rate limit: {e}")
        # Fail open: allow the submission if we can't check
        return True, 0, limit


def check_approval(issue_number: int, repo_root: str) -> Dict:
    """
    Check if an issue is approved for review.
    
    Returns a dict with:
        - approved (bool): whether the issue can be reviewed
        - reason (str): why it was approved or gated
        - author (str): the issue author
    """
    token, owner, repo = get_env()
    
    # Get issue author
    author = get_issue_author(token, owner, repo, issue_number)
    if not author:
        return {
            "approved": False,
            "reason": "Failed to fetch issue author",
            "author": "unknown",
        }
    
    # Check editorial-hold first (always blocks)
    if has_editorial_hold(token, owner, repo, issue_number):
        return {
            "approved": False,
            "reason": "editorial-hold label present",
            "author": author,
        }
    
    # Check if repo collaborator (auto-approved)
    if is_repo_collaborator(token, owner, repo, author):
        return {
            "approved": True,
            "reason": "repo collaborator",
            "author": author,
        }
    
    # Check if on allowlist (auto-approved)
    if is_on_allowlist(author, repo_root):
        return {
            "approved": True,
            "reason": "on allowlist",
            "author": author,
        }
    
    # Check if has approval label
    if has_approval_label(token, owner, repo, issue_number):
        # Also check rate limit
        allowed, count, limit = check_rate_limit(token, owner, repo, author)
        if not allowed:
            return {
                "approved": False,
                "reason": f"rate limit exceeded ({count}/{limit} submissions in 24h)",
                "author": author,
            }
        
        return {
            "approved": True,
            "reason": "approved-for-review label present",
            "author": author,
        }
    
    # Not approved
    return {
        "approved": False,
        "reason": "requires approved-for-review label from maintainer",
        "author": author,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python author_gating.py check <issue_number>")
        sys.exit(1)
    
    command = sys.argv[1]
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    
    if command == "check":
        if len(sys.argv) < 3:
            print("Usage: python author_gating.py check <issue_number>")
            sys.exit(1)
        
        try:
            issue_number = int(sys.argv[2])
        except ValueError:
            print(f"ERROR: Invalid issue number: {sys.argv[2]}")
            sys.exit(1)
        
        result = check_approval(issue_number, repo_root)
        
        print(f"Issue #{issue_number}")
        print(f"Author: {result['author']}")
        print(f"Approved: {result['approved']}")
        print(f"Reason: {result['reason']}")
        
        sys.exit(0 if result["approved"] else 1)
    
    elif command == "check-rate-limit":
        if len(sys.argv) < 3:
            print("Usage: python author_gating.py check-rate-limit <author>")
            sys.exit(1)
        
        author = sys.argv[2]
        token, owner, repo = get_env()
        allowed, count, limit = check_rate_limit(token, owner, repo, author)
        
        print(f"Author: {author}")
        print(f"Submissions in last 24h: {count}/{limit}")
        print(f"Allowed: {allowed}")
        
        sys.exit(0 if allowed else 1)
    
    else:
        print(f"ERROR: Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
