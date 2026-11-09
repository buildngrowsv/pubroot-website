"""
Stages 1-3 Analyzer — Pubroot Security Hardening

PURPOSE:
    This script runs ONLY stages 1-3 of the review pipeline (parse, novelty, repo reading)
    with NO sensitive secrets in scope. It is called by the analyze-submission job in
    review.yml, which has read-only permissions and does not have access to GEMINI_API_KEY.
    
    This architecture ensures that even if a malicious submitter exploits a vulnerability
    in the repo cloning or file reading logic (e.g., the B1 symlink attack), they cannot
    exfiltrate API keys or gain write access because those secrets are not present.

SECURITY ARCHITECTURE:
    - Input: Issue number (from untrusted submission)
    - Environment: GITHUB_TOKEN (read-only), S2_API_KEY (optional, low-risk), GITHUB_REPOSITORY
    - NO ACCESS TO: GEMINI_API_KEY (kept out of scope until stage 4)
    - Output: JSON file with parsed data, novelty results, and repo context
    - This output is passed to stages 4-6 via GitHub Actions artifacts

CALLED BY:
    .github/workflows/review.yml (analyze-submission job)

USAGE:
    python stages_1_to_3_analyzer.py <issue_number> <output_json_path>
"""

import json
import os
import sys
from datetime import datetime, timezone

# Import only the stages we need (1-3, plus priority calculation)
from stage_1_parse_and_filter import parse_and_filter_submission
from stage_2_novelty_check import check_novelty
from stage_3_read_linked_repo import read_linked_repository
from priority_score_calculator import calculate_priority
from verify_payment_code import verify_payment_code


def fetch_issue_data(issue_number: int, github_token: str, github_repo: str) -> dict:
    """
    Fetch the issue body and author from GitHub API.
    
    This is the ONLY external data we read that comes from an untrusted source
    (the submitter). Everything else in stages 1-3 either comes from our own
    config files or from APIs we control (arXiv, Semantic Scholar).
    """
    import requests
    
    url = f"https://api.github.com/repos/{github_repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue: {response.status_code} {response.text}")
    
    issue = response.json()
    return {
        "body": issue.get("body", ""),
        "author": issue.get("user", {}).get("login", "unknown"),
    }


def run_stages_1_to_3(issue_number: int) -> dict:
    """
    Run stages 1-3 with minimal secrets in scope.
    
    Returns:
        dict with all data needed for stages 4-6:
            - issue_number
            - paper_id
            - parsed (stage 1 output)
            - novelty (stage 2 output)
            - repo_data (stage 3 output)
            - priority_info (stage 0 output)
            - payment_verification (stage 0)
            - success (bool)
            - action (str: 'continue', 'filtered', 'error')
            - errors (list)
    """
    
    # Read environment (read-only token, no GEMINI_API_KEY)
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    s2_api_key = os.environ.get("S2_API_KEY", "")
    
    if not github_token:
        return {
            "success": False,
            "action": "error",
            "errors": ["GITHUB_TOKEN not set"],
        }
    
    if not github_repo:
        return {
            "success": False,
            "action": "error",
            "errors": ["GITHUB_REPOSITORY not set"],
        }
    
    errors = []
    
    # Generate paper ID
    now = datetime.now(timezone.utc)
    paper_id = f"{now.year}-{issue_number:03d}"
    
    print(f"[Stage 0] Processing issue #{issue_number} → Paper ID: {paper_id}")
    
    # Fetch issue data
    try:
        issue_data = fetch_issue_data(issue_number, github_token, github_repo)
    except Exception as e:
        return {
            "success": False,
            "action": "error",
            "errors": [f"Failed to fetch issue: {str(e)}"],
        }
    
    # Get repo root for file operations
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    
    # Stage 0: Calculate priority (before stage 1 so we can label early)
    # Note: We don't have category or payment code yet, so initial priority is minimal
    priority_info = calculate_priority(
        author=issue_data["author"],
        category="",  # Will be filled in by stage 1
        payment_code=None,  # Will be updated after stage 1 extracts it
        repo_root=repo_root,
    )
    
    # Stage 1: Parse and filter
    print(f"[Stage 1] Parsing submission...")
    parsed = parse_and_filter_submission(
        issue_body=issue_data["body"],
        repo_root=repo_root,
        issue_author=issue_data["author"],
        paper_id=paper_id,  # Pass paper_id for self-match detection in dedup
    )
    
    if not parsed.get("valid", False):
        return {
            "success": True,
            "action": "filtered",
            "paper_id": paper_id,
            "issue_number": issue_number,  # FIX: include for stages_4_to_6_reviewer.py
            "parsed": parsed,
            "errors": parsed.get("errors", []),
        }
    
    # Update priority with actual category
    priority_info = calculate_priority(
        author=issue_data["author"],
        category=parsed.get("category", ""),
        payment_code=parsed.get("payment_code"),
        repo_root=repo_root,
    )
    
    # Payment verification (stage 0 continuation)
    payment_verification = verify_payment_code(
        payment_code=parsed.get("payment_code"),
        repo_root=repo_root,
    )
    
    # Update priority with verified payment code if valid
    if payment_verification.get("valid", False):
        priority_info = calculate_priority(
            author=issue_data["author"],
            category=parsed.get("category", ""),
            payment_code=parsed.get("payment_code"),
            repo_root=repo_root,
        )
    
    # Stage 2: Novelty check
    print(f"[Stage 2] Checking novelty...")
    novelty = check_novelty(
        title=parsed.get("title", ""),
        abstract=parsed.get("abstract", ""),
        category=parsed.get("category", ""),
        repo_root=repo_root,
        s2_api_key=s2_api_key,
    )
    
    if novelty.get("errors"):
        errors.extend(novelty["errors"])
        print(f"  ⚠ Novelty check had errors: {novelty['errors']}")
    
    # Stage 3: Read linked repository
    print(f"[Stage 3] Reading linked repository...")
    repo_data = read_linked_repository(
        repo_url=parsed.get("supporting_repo"),
        commit_sha=parsed.get("commit_sha"),
        repo_visibility=parsed.get("repo_visibility", "no-repo"),
    )
    
    if repo_data.get("errors"):
        errors.extend(repo_data["errors"])
        print(f"  ⚠ Repo reading had errors: {repo_data['errors']}")
    
    print(f"[Stage 3] ✓ Stages 1-3 complete. Repo available: {repo_data.get('available', False)}")
    
    return {
        "success": True,
        "action": "continue",
        "issue_number": issue_number,
        "paper_id": paper_id,
        "parsed": parsed,
        "novelty": novelty,
        "repo_data": repo_data,
        "priority_info": priority_info,
        "payment_verification": payment_verification,
        "errors": errors,
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python stages_1_to_3_analyzer.py <issue_number> <output_json_path>")
        sys.exit(1)
    
    issue_number = int(sys.argv[1])
    output_path = sys.argv[2]
    
    print(f"=== Stages 1-3 Analyzer (Security Isolation) ===")
    print(f"Issue: #{issue_number}")
    print(f"Output: {output_path}")
    print(f"Environment: GITHUB_TOKEN (read-only), NO GEMINI_API_KEY")
    print()
    
    result = run_stages_1_to_3(issue_number)
    
    # Write output JSON
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print()
    print(f"✓ Analysis complete. Output written to {output_path}")
    print(f"  Action: {result['action']}")
    print(f"  Success: {result['success']}")
    
    # Exit with appropriate code
    if result["action"] == "error":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
