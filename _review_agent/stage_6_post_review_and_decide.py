"""
Stage 6: Post Review & Decide — Pubroot

PURPOSE:
    This is the final stage of the review pipeline. It takes the structured review
    from Stage 5 and acts on it:
    
    IF ACCEPTED (score >= 6.0):
      1. Post the formatted review as a GitHub Issue comment
      2. Create a branch paper/{paper-id}
      3. Commit article.md + manifest.json to papers/{paper-id}/
      4. Commit review.json to reviews/{paper-id}/
      5. Update contributors.json with the new submission stats
      6. Update agent-index.json with the new paper entry
      7. Create a Pull Request and auto-merge it
      8. Add labels: "accepted", "published"
    
    IF REJECTED (score < 6.0):
      1. Post the formatted review as a GitHub Issue comment
      2. Update contributors.json with the rejection stats
      3. Add label: "rejected"
      4. Close the Issue with an explanation
    
    IF ERROR (review failed):
      1. Post an error comment explaining what went wrong
      2. Add label: "review-error"
      3. Leave the Issue open for retry

CALLED BY:
    review_pipeline_main.py — passes the review result, parsed submission,
    and all context from earlier stages.

DEPENDS ON:
    - GitHub API (via requests library) for all Issue/PR/file operations
    - The GITHUB_TOKEN automatically provided by GitHub Actions
    - contributors.json and agent-index.json in the repo

COST:
    $0 — All operations use the GitHub API with the free GITHUB_TOKEN.
    ~12 API calls for an accepted submission, ~5 for a rejected one.
"""

import json
import os
import base64
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests


def post_review_and_decide(
    review_result: dict,
    parsed_submission: dict,
    novelty_results: dict,
    repo_data: dict,
    paper_id: str,
    issue_number: int,
    repo_owner: str,
    repo_name: str,
    github_token: str,
    repo_root: str
) -> dict:
    """
    Post the review to GitHub and execute the accept/reject decision.
    
    This is the ONLY public function in this file. It handles the complete
    post-review workflow: commenting, labeling, creating PRs (if accepted),
    updating contributor stats, and updating the paper index.
    
    Args:
        review_result: Output from Stage 5 — the review dict with score/verdict
        parsed_submission: Output from Stage 1 — parsed fields
        novelty_results: Output from Stage 2 — for supersession info
        repo_data: Output from Stage 3 — badge type info
        paper_id: The assigned paper ID (e.g., "2026-042")
        issue_number: The GitHub Issue number
        repo_owner: GitHub repo owner (e.g., "your-username")
        repo_name: GitHub repo name (e.g., "ai-peer-review-journal")
        github_token: GITHUB_TOKEN for API authentication
        repo_root: Path to the local repo checkout (for reading/writing files)
    
    Returns:
        dict with keys:
            - 'success' (bool): Whether the post-review actions completed
            - 'action_taken' (str): 'accepted', 'rejected', or 'error'
            - 'pr_number' (int or None): PR number if created
            - 'errors' (list[str]): Any errors encountered
    """
    
    errors = []
    gh = GitHubAPI(repo_owner, repo_name, github_token)
    
    # -----------------------------------------------------------------------
    # CASE 1: Review failed (Stage 5 returned an error)
    # -----------------------------------------------------------------------
    
    if not review_result.get("success", False):
        error_msg = review_result.get("error", "Unknown review error")
        
        comment = _format_error_comment(error_msg, paper_id)
        gh.post_comment(issue_number, comment)
        gh.add_labels(issue_number, ["review-error"])
        
        return {
            "success": False,
            "action_taken": "error",
            "pr_number": None,
            "errors": [error_msg],
        }
    
    review = review_result.get("review", {})
    grounding = review_result.get("grounding_metadata", {})
    score = float(review.get("score", 0))
    verdict = review.get("verdict", "REJECTED")
    
    # -----------------------------------------------------------------------
    # POST THE REVIEW COMMENT (always, whether accepted or rejected)
    # -----------------------------------------------------------------------
    # We format the review JSON into a readable Markdown comment so the
    # submitter gets human-readable feedback directly on their Issue.
    # -----------------------------------------------------------------------
    
    comment = _format_review_comment(review, grounding, paper_id, score, verdict)
    gh.post_comment(issue_number, comment)
    
    # -----------------------------------------------------------------------
    # UPDATE CONTRIBUTOR STATS (always, for both accepted and rejected)
    # -----------------------------------------------------------------------
    
    try:
        _update_contributors(
            repo_root=repo_root,
            author=parsed_submission.get("author", "unknown"),
            score=score,
            accepted=(verdict == "ACCEPTED"),
            category=parsed_submission.get("category", "general-technical"),
        )
    except Exception as e:
        errors.append(f"Failed to update contributors.json: {str(e)}")
    
    # -----------------------------------------------------------------------
    # CASE 2: ACCEPTED — Create PR with published content
    # -----------------------------------------------------------------------
    
    if verdict == "ACCEPTED" and score >= 6.0:
        try:
            pr_number = _handle_acceptance(
                gh=gh,
                review=review,
                grounding=grounding,
                parsed_submission=parsed_submission,
                novelty_results=novelty_results,
                repo_data=repo_data,
                paper_id=paper_id,
                issue_number=issue_number,
                repo_root=repo_root,
            )
            
            gh.add_labels(issue_number, ["accepted", "published"])
            
            return {
                "success": True,
                "action_taken": "accepted",
                "pr_number": pr_number,
                "errors": errors,
            }
        except Exception as e:
            errors.append(f"Failed to create publication PR: {str(e)}")
            gh.add_labels(issue_number, ["review-error"])
            return {
                "success": False,
                "action_taken": "error",
                "pr_number": None,
                "errors": errors,
            }
    
    # -----------------------------------------------------------------------
    # CASE 3: REJECTED — Label and close
    # -----------------------------------------------------------------------
    
    gh.add_labels(issue_number, ["rejected"])
    gh.close_issue(issue_number)
    
    return {
        "success": True,
        "action_taken": "rejected",
        "pr_number": None,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# GITHUB API HELPER CLASS
# ---------------------------------------------------------------------------
# Wraps the GitHub REST API calls needed by this stage. Uses the GITHUB_TOKEN
# which is auto-generated by GitHub Actions with repo write permissions.
# ---------------------------------------------------------------------------


class GitHubAPI:
    """
    Thin wrapper around GitHub REST API for the operations we need.
    
    All methods use the GITHUB_TOKEN provided by Actions, which has:
    - issues:write (post comments, add labels, close issues)
    - contents:write (create files, commit, push)
    - pull-requests:write (create and merge PRs)
    """
    
    def __init__(self, owner: str, repo: str, token: str):
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    def post_comment(self, issue_number: int, body: str):
        """Post a comment on a GitHub Issue."""
        url = f"{self.base_url}/issues/{issue_number}/comments"
        resp = requests.post(url, headers=self.headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def add_labels(self, issue_number: int, labels: list):
        """Add labels to a GitHub Issue."""
        url = f"{self.base_url}/issues/{issue_number}/labels"
        resp = requests.post(url, headers=self.headers, json={"labels": labels}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def close_issue(self, issue_number: int):
        """Close a GitHub Issue."""
        url = f"{self.base_url}/issues/{issue_number}"
        resp = requests.patch(url, headers=self.headers, json={"state": "closed"}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def get_default_branch_sha(self) -> str:
        """Get the SHA of the HEAD commit on the default branch (main)."""
        url = f"{self.base_url}/git/ref/heads/main"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["object"]["sha"]
    
    def create_branch(self, branch_name: str, sha: str):
        """Create a new branch from the given SHA."""
        url = f"{self.base_url}/git/refs"
        data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
        resp = requests.post(url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def create_or_update_file(self, path: str, content: str, message: str, branch: str):
        """
        Create or update a file in the repo on the given branch.
        Content is automatically base64-encoded.
        """
        url = f"{self.base_url}/contents/{path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        
        # Check if file exists (to get its SHA for updates)
        existing_sha = None
        check = requests.get(url, headers=self.headers, params={"ref": branch}, timeout=30)
        if check.status_code == 200:
            existing_sha = check.json().get("sha")
        
        data = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if existing_sha:
            data["sha"] = existing_sha
        
        resp = requests.put(url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> int:
        """Create a Pull Request. Returns the PR number."""
        url = f"{self.base_url}/pulls"
        data = {"title": title, "body": body, "head": head, "base": base}
        resp = requests.post(url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()["number"]
    
    def merge_pull_request(self, pr_number: int, merge_method: str = "squash"):
        """Merge a Pull Request."""
        url = f"{self.base_url}/pulls/{pr_number}/merge"
        data = {"merge_method": merge_method}
        resp = requests.put(url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _handle_acceptance(
    gh: GitHubAPI,
    review: dict,
    grounding: dict,
    parsed_submission: dict,
    novelty_results: dict,
    repo_data: dict,
    paper_id: str,
    issue_number: int,
    repo_root: str,
) -> int:
    """
    Handle the full acceptance workflow: branch, commit, PR, merge.
    
    Returns the PR number.
    """
    now = datetime.now(timezone.utc)
    branch_name = f"paper/{paper_id}"
    
    # Step 1: Create branch from main HEAD
    main_sha = gh.get_default_branch_sha()
    gh.create_branch(branch_name, main_sha)
    
    # Step 2: Build and commit article.md
    # NOTE: We pass review and repo_data to _build_article_md so it can include
    # score, verdict, and badge in the frontmatter. Without these, the Hugo
    # single page template (single.html) falls back to "?" and "PENDING" defaults.
    # This bug was caught during the Feb 2026 taxonomy redesign audit.
    article_content = _build_article_md(
        parsed_submission, review, repo_data, paper_id, now
    )
    gh.create_or_update_file(
        path=f"papers/{paper_id}/article.md",
        content=article_content,
        message=f"Publish article: {parsed_submission.get('title', paper_id)}",
        branch=branch_name,
    )
    
    # Step 3: Build and commit manifest.json
    manifest = _build_manifest(
        parsed_submission, review, repo_data, paper_id, now, novelty_results
    )
    gh.create_or_update_file(
        path=f"papers/{paper_id}/manifest.json",
        content=json.dumps(manifest, indent=2),
        message=f"Add manifest for {paper_id}",
        branch=branch_name,
    )
    
    # Step 4: Commit review.json (includes grounding metadata)
    review_with_grounding = {**review, "grounding_metadata": grounding}
    gh.create_or_update_file(
        path=f"reviews/{paper_id}/review.json",
        content=json.dumps(review_with_grounding, indent=2),
        message=f"Add review for {paper_id}",
        branch=branch_name,
    )
    
    # Step 5: Update agent-index.json
    index_entry = _build_index_entry(parsed_submission, review, repo_data, paper_id, now)
    _update_agent_index(gh, branch_name, repo_root, index_entry)
    
    # Step 6: Update contributors.json on the branch
    # (Already updated locally in post_review_and_decide, now commit it)
    contributors_path = os.path.join(repo_root, "contributors.json")
    with open(contributors_path, "r") as f:
        contributors_content = f.read()
    gh.create_or_update_file(
        path="contributors.json",
        content=contributors_content,
        message=f"Update contributor stats after {paper_id}",
        branch=branch_name,
    )
    
    # Step 7: Create and merge PR
    pr_title = f"Publish: {parsed_submission.get('title', paper_id)}"
    pr_body = (
        f"## Auto-published by AI Peer Review Pipeline\n\n"
        f"**Paper ID:** {paper_id}\n"
        f"**Score:** {review.get('score', '?')}/10\n"
        f"**Verdict:** {review.get('verdict', '?')}\n"
        f"**Badge:** {review.get('badge', '?')}\n\n"
        f"**Summary:** {review.get('summary', 'No summary available.')}\n\n"
        f"Closes #{issue_number}"
    )
    
    pr_number = gh.create_pull_request(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base="main",
    )
    
    # Auto-merge the PR
    gh.merge_pull_request(pr_number, merge_method="squash")
    
    return pr_number


def _build_article_md(
    parsed: dict,
    review: dict,
    repo_data: dict,
    paper_id: str,
    now: datetime
) -> str:
    """
    Build the published article Markdown file with Hugo-compatible frontmatter.

    This function creates the file that Hugo renders as the article's single page.
    The frontmatter fields map directly to template variables used in single.html:

        .Title           ← title
        .Params.paper_id ← paper_id
        .Params.author   ← author
        .Params.category ← category (now "journal/topic" format, e.g., "ai/llm-benchmarks")
        .Params.abstract ← abstract  (shown in the teal abstract block)
        .Params.score    ← score     (shown in the score circle)
        .Params.verdict  ← verdict   (ACCEPTED/REJECTED badge)
        .Params.badge    ← badge     (verified_open / verified_private / text_only)
        .Date            ← date
        .Content         ← everything below the "---" frontmatter delimiter

    BUG FIX (Feb 2026): Previously this function did NOT include score, verdict,
    or badge in the frontmatter. The single.html template fell back to "?" and
    "PENDING" defaults, making every published article look unscored on the site.
    Fixed by adding review and repo_data as parameters and including their values.

    Args:
        parsed: Parsed submission data from Stage 1 (title, author, category, etc.)
        review: Structured review from Stage 5 (score, verdict, summary, etc.)
        repo_data: Repository analysis from Stage 3 (badge_type, etc.)
        paper_id: The paper ID (e.g., "2026-042")
        now: Publication timestamp
    """
    frontmatter = {
        "title": parsed.get("title", "Untitled"),
        "paper_id": paper_id,
        "author": parsed.get("author", "unknown"),
        "category": parsed.get("category", ""),
        "date": now.isoformat(),
        "abstract": parsed.get("abstract", ""),
        "score": review.get("score", 0),
        "verdict": review.get("verdict", "ACCEPTED"),
        "badge": repo_data.get("badge_type", "text_only"),
    }

    # Build YAML frontmatter manually. We use json.dumps for safe quoting
    # of strings that might contain colons, newlines, or special YAML chars.
    # Multi-line strings (like abstracts) use the YAML pipe (|) syntax.
    content = "---\n"
    for key, value in frontmatter.items():
        if isinstance(value, str) and ("\n" in value or ":" in value):
            content += f'{key}: |\n'
            for line in value.split("\n"):
                content += f"  {line}\n"
        elif isinstance(value, (int, float)):
            # Numbers should NOT be quoted so Hugo reads them as numbers
            content += f"{key}: {value}\n"
        else:
            content += f"{key}: {json.dumps(value)}\n"
    content += "---\n\n"
    content += parsed.get("body", "")

    return content


def _build_manifest(
    parsed: dict, review: dict, repo_data: dict,
    paper_id: str, now: datetime, novelty: dict
) -> dict:
    """Build the manifest.json for a published paper."""
    # Calculate valid_until: 12 months for humanities/philosophy topics,
    # 6 months for everything else. Humanities content has longer shelf life
    # because it deals with ideas that change more slowly than technical content.
    # The old code checked for "intellectual-essays" which no longer exists
    # after the Feb 2026 taxonomy redesign to journal/topic format.
    category = parsed.get("category", "")
    journal_slug = category.split("/")[0] if "/" in category else category
    if journal_slug in ("humanities", "social"):
        valid_until = now + timedelta(days=365)
    else:
        valid_until = now + timedelta(days=180)
    
    return {
        "paper_id": paper_id,
        "title": parsed.get("title", "Untitled"),
        "author": parsed.get("author", "unknown"),
        "category": parsed.get("category", "general-technical"),
        "published_date": now.isoformat(),
        "status": "current",
        "score": review.get("score"),
        "verdict": review.get("verdict"),
        "badge": repo_data.get("badge_type", "text_only"),
        "supporting_repo": parsed.get("supporting_repo"),
        "commit_sha": parsed.get("commit_sha"),
        "valid_until": valid_until.isoformat(),
        "supersedes": review.get("supersedes"),
        "superseded_by": None,
        "word_count": parsed.get("word_count_body", 0),
    }


def _build_index_entry(
    parsed: dict, review: dict, repo_data: dict,
    paper_id: str, now: datetime
) -> dict:
    """Build an entry for agent-index.json."""
    return {
        "id": paper_id,
        "title": parsed.get("title", "Untitled"),
        "author": parsed.get("author", "unknown"),
        "category": parsed.get("category", "general-technical"),
        "abstract": parsed.get("abstract", "")[:500],
        "published_date": now.isoformat(),
        "review_score": review.get("score"),
        "badge": repo_data.get("badge_type", "text_only"),
        "status": "current",
        "article_path": f"papers/{paper_id}/article.md",
        "review_path": f"reviews/{paper_id}/review.json",
        "supporting_repo": parsed.get("supporting_repo"),
    }


def _update_agent_index(
    gh: GitHubAPI, branch: str, repo_root: str, new_entry: dict
):
    """
    Add a new paper entry to agent-index.json and commit it.
    
    We read the current file, append the new entry, update the metadata,
    and commit the updated file to the publication branch.
    """
    index_path = os.path.join(repo_root, "agent-index.json")
    
    with open(index_path, "r") as f:
        index_data = json.load(f)
    
    index_data["papers"].append(new_entry)
    index_data["total_papers"] = len(index_data["papers"])
    index_data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    gh.create_or_update_file(
        path="agent-index.json",
        content=json.dumps(index_data, indent=2),
        message=f"Update paper index: add {new_entry['id']}",
        branch=branch,
    )


def _update_contributors(
    repo_root: str,
    author: str,
    score: float,
    accepted: bool,
    category: str
):
    """
    Update the contributor's stats in contributors.json.
    
    This is called for BOTH accepted and rejected submissions. It updates
    the contributor's submission count, acceptance rate, average score,
    and per-category stats. The reputation score is recalculated by
    reputation_calculator.py (called separately).
    
    We write the updated file locally. Stage 6 then commits it to the branch.
    """
    contributors_path = os.path.join(repo_root, "contributors.json")
    
    with open(contributors_path, "r") as f:
        data = json.load(f)
    
    contributors = data.get("contributors", {})
    
    if author not in contributors:
        contributors[author] = {
            "github_handle": author,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_submission": datetime.now(timezone.utc).isoformat(),
            "total_submissions": 0,
            "accepted": 0,
            "rejected": 0,
            "withdrawn": 0,
            "acceptance_rate": 0.0,
            "average_score": 0.0,
            "score_trend": "insufficient_data",
            "categories": {},
            "reputation_score": 0.0,
            "reputation_tier": "new",
            "flags": {
                "prompt_injection_attempts": 0,
                "spam_submissions": 0,
                "dmca_strikes": 0,
            },
        }
    
    c = contributors[author]
    c["last_submission"] = datetime.now(timezone.utc).isoformat()
    c["total_submissions"] += 1
    
    if accepted:
        c["accepted"] += 1
    else:
        c["rejected"] += 1
    
    # Recalculate acceptance rate
    total = c["total_submissions"]
    c["acceptance_rate"] = round(c["accepted"] / total, 3) if total > 0 else 0.0
    
    # Recalculate running average score
    # Formula: new_avg = old_avg + (new_score - old_avg) / new_count
    old_avg = c["average_score"]
    c["average_score"] = round(old_avg + (score - old_avg) / total, 2)
    
    # Update per-category stats
    if category not in c["categories"]:
        c["categories"][category] = {
            "submissions": 0,
            "accepted": 0,
            "avg_score": 0.0,
        }
    cat = c["categories"][category]
    cat["submissions"] += 1
    if accepted:
        cat["accepted"] += 1
    cat_total = cat["submissions"]
    cat["avg_score"] = round(cat["avg_score"] + (score - cat["avg_score"]) / cat_total, 2)
    
    data["contributors"] = contributors
    
    with open(contributors_path, "w") as f:
        json.dump(data, f, indent=2)


def _format_review_comment(
    review: dict, grounding: dict, paper_id: str, score: float, verdict: str
) -> str:
    """
    Format the review JSON into a readable Markdown comment for the GitHub Issue.
    
    This is what the submitter sees. It needs to be clear, actionable, and
    professional. We show the key metrics prominently, then the detailed
    breakdown, then the full claims verification.
    """
    # Determine emoji for verdict (using standard Unicode, user didn't say no emojis)
    verdict_icon = "ACCEPTED" if verdict == "ACCEPTED" else "REJECTED"
    score_bar = _score_to_bar(score)
    
    badge = review.get("badge", "text_only")
    summary = review.get("summary", "No summary available.")
    
    lines = [
        f"# AI Peer Review — {verdict_icon}",
        f"**Paper ID:** `{paper_id}`",
        f"**Score:** {score}/10 {score_bar}",
        f"**Badge:** `{badge}`",
        "",
        f"## Summary",
        summary,
        "",
    ]
    
    # Confidence breakdown
    confidence = review.get("confidence", {})
    if confidence:
        lines.append("## Confidence Scores")
        lines.append("| Dimension | Score |")
        lines.append("|-----------|-------|")
        for dim, val in confidence.items():
            if val is not None:
                lines.append(f"| {dim.replace('_', ' ').title()} | {val} |")
        lines.append("")
    
    # Strengths
    strengths = review.get("strengths", [])
    if strengths:
        lines.append("## Strengths")
        for s in strengths:
            lines.append(f"- {s}")
        lines.append("")
    
    # Weaknesses
    weaknesses = review.get("weaknesses", [])
    if weaknesses:
        lines.append("## Weaknesses")
        for w in weaknesses:
            lines.append(f"- {w}")
        lines.append("")
    
    # Suggestions
    suggestions = review.get("suggestions", [])
    if suggestions:
        lines.append("## Suggestions for Improvement")
        for s in suggestions:
            lines.append(f"- {s}")
        lines.append("")
    
    # Claims verification
    claims = review.get("claims", [])
    if claims:
        lines.append("## Claim Verification")
        lines.append("| Claim | Verified | Confidence | Source |")
        lines.append("|-------|----------|------------|--------|")
        for claim in claims:
            verified = "Yes" if claim.get("verified") else "No"
            conf = claim.get("confidence", "?")
            source = claim.get("source", "N/A")
            text = claim.get("text", "")[:80]
            lines.append(f"| {text} | {verified} | {conf} | {source} |")
        lines.append("")
    
    # Grounding sources
    sources = grounding.get("sources", []) if isinstance(grounding, dict) else []
    if sources:
        lines.append("## Sources Used for Fact-Checking")
        for src in sources[:10]:
            title = src.get("title", "Untitled")
            uri = src.get("uri", "")
            lines.append(f"- [{title}]({uri})")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append(
        "*This review was generated by the Pubroot pipeline "
        f"using {review.get('review_metadata', {}).get('reviewer', 'Gemini')} "
        "with Google Search grounding.*"
    )
    
    return "\n".join(lines)


def _format_error_comment(error_msg: str, paper_id: str) -> str:
    """Format an error comment when the review pipeline fails."""
    return (
        f"# AI Peer Review — Error\n\n"
        f"**Paper ID:** `{paper_id}`\n\n"
        f"The review pipeline encountered an error:\n\n"
        f"```\n{error_msg}\n```\n\n"
        f"This issue has been labeled `review-error` and will be retried. "
        f"If the problem persists, a maintainer will investigate.\n\n"
        f"---\n"
        f"*This is an automated message from the Pubroot pipeline.*"
    )


def _score_to_bar(score: float) -> str:
    """Convert a 0-10 score to a visual bar for the comment."""
    filled = int(round(score))
    empty = 10 - filled
    return "[" + "|" * filled + "." * empty + "]"
