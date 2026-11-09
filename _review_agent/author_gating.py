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


def is_repo_collaborator_or_member(issue: dict, token: str, owner: str, repo: str, username: str) -> bool:
    """
    Check if a user is a repo collaborator based on author_association.
    
    GitHub provides author_association in issue payloads with values like:
    - OWNER: repo owner
    - MEMBER: organization member
    - COLLABORATOR: repo collaborator with write access
    - CONTRIBUTOR, FIRST_TIME_CONTRIBUTOR, NONE: not a collaborator
    
    The collaborator check (GET /repos/{owner}/{repo}/collaborators/{username})
    requires push access on the token. The analyze-submission job has only
    contents: read and issues: read, so that endpoint returns 403 (fails closed).
    
    Instead, we check author_association in the issue payload, which requires
    only issues: read. On user-owned repos, every collaborator has write access,
    so COLLABORATOR implies trusted.
    
    We keep the collaborator endpoint as an optional secondary check and log
    non-204/404 statuses (e.g., 403 when token lacks push) without failing open.
    """
    # Primary check: author_association from issue payload
    association = issue.get("author_association", "NONE")
    if association in {"OWNER", "MEMBER", "COLLABORATOR"}:
        return True
    
    # Secondary check: collaborator endpoint (optional, may fail with 403)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    # https://docs.github.com/en/rest/collaborators/collaborators#check-if-a-user-is-a-repository-collaborator
    # NOTE: This endpoint requires the authenticated user to have push access.
    # With contents: read only, expect 403.
    url = f"https://api.github.com/repos/{owner}/{repo}/collaborators/{username}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 204:
            return True
        elif resp.status_code == 404:
            return False
        else:
            # Log unexpected statuses (likely 403 when token lacks push)
            print(f"INFO: Collaborator check HTTP {resp.status_code} (token lacks push access), treating as not a collaborator")
            return False
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


def fetch_issue(token: str, owner: str, repo: str, issue_number: int) -> Optional[dict]:
    """
    Fetch a GitHub issue by number.
    
    Returns the full issue dict (includes author, labels, author_association).
    This is called once per issue to avoid redundant API calls.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"ERROR: Failed to fetch issue #{issue_number}: {e}")
        return None


def check_rate_limit(token: str, owner: str, repo: str, author: str, limit: int = 3) -> tuple[bool, int, int]:
    """
    Check if an author has exceeded their daily submission cap.
    
    NOTE: The GitHub API's `since=` parameter filters by *updated_at*, not *created_at*,
    so it can overcount issues that were recently commented on. We fetch issues by creator
    and filter on created_at client-side.
    
    Returns:
        (allowed, count_today, limit) where allowed=True if under the cap
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    
    # Get issues created by this author (no since filter, we'll filter client-side)
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {
        "creator": author,
        "state": "all",
        "per_page": 100,
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        issues = resp.json()
        
        # Filter by created_at in the last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        recent_submissions = [
            issue for issue in issues
            if issue.get("title", "").startswith("[SUBMISSION]")
            and datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")) > cutoff
        ]
        
        submission_count = len(recent_submissions)
        return submission_count < limit, submission_count, limit
    except Exception as e:
        print(f"WARNING: Failed to check rate limit: {e}")
        # Fail open: allow the submission if we can't check
        return True, 0, limit


def evaluate_issue(issue: dict, repo_root: str, token: str, owner: str, repo: str) -> Dict:
    """
    Evaluate whether an issue is approved for review.
    
    This is the core gating function. It checks editorial-hold, author_association,
    allowlist, and approved-for-review label (with rate limit). The result includes
    a stable kind field for use in workflow outputs.
    
    Args:
        issue: Full issue dict from GitHub API (includes author, labels, author_association)
        repo_root: Path to repo root (for reading .github/REVIEW_ALLOWLIST.txt)
        token: GitHub API token
        owner: Repo owner
        repo: Repo name
    
    Returns:
        dict with:
            - approved (bool): whether the issue can be reviewed
            - kind (str): stable gate kind (needs-approval, editorial-hold, rate-limited, error)
            - reason (str): human-readable reason
            - author (str): issue author username
    """
    author = issue.get("user", {}).get("login", "unknown")
    labels = [lbl["name"] for lbl in issue.get("labels", [])]
    
    # Check editorial-hold first (always blocks)
    if "editorial-hold" in labels:
        return {
            "approved": False,
            "kind": "editorial-hold",
            "reason": "editorial-hold label present",
            "author": author,
        }
    
    # Check if repo collaborator/member/owner (auto-approved via author_association)
    if is_repo_collaborator_or_member(issue, token, owner, repo, author):
        return {
            "approved": True,
            "kind": "approved",
            "reason": f"repo {issue.get('author_association', '').lower()}",
            "author": author,
        }
    
    # Check if on allowlist (auto-approved)
    if is_on_allowlist(author, repo_root):
        return {
            "approved": True,
            "kind": "approved",
            "reason": "on allowlist",
            "author": author,
        }
    
    # Check if has approval label
    if "approved-for-review" in labels:
        # Also check rate limit
        allowed, count, limit = check_rate_limit(token, owner, repo, author)
        if not allowed:
            return {
                "approved": False,
                "kind": "rate-limited",
                "reason": f"rate limit exceeded ({count}/{limit} submissions in 24h)",
                "author": author,
            }
        
        return {
            "approved": True,
            "kind": "approved",
            "reason": "approved-for-review label present",
            "author": author,
        }
    
    # Not approved
    return {
        "approved": False,
        "kind": "needs-approval",
        "reason": "requires approved-for-review label from maintainer",
        "author": author,
    }


def check_approval(issue_number: int, repo_root: str) -> Dict:
    """
    Check if an issue is approved for review (legacy wrapper for evaluate_issue).
    
    Fetches the issue and calls evaluate_issue. Used by review.yml for backward
    compatibility with the old check_approval interface.
    
    Returns a dict with:
        - approved (bool): whether the issue can be reviewed
        - kind (str): stable gate kind (needs-approval, editorial-hold, rate-limited, error)
        - reason (str): why it was approved or gated
        - author (str): the issue author
    """
    token, owner, repo = get_env()
    
    # Fetch issue once
    issue = fetch_issue(token, owner, repo, issue_number)
    if not issue:
        return {
            "approved": False,
            "kind": "error",
            "reason": "Failed to fetch issue",
            "author": "unknown",
        }
    
    return evaluate_issue(issue, repo_root, token, owner, repo)


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
        print(f"Kind: {result.get('kind', 'unknown')}")
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
