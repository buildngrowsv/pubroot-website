"""
Stage 6: Post Review & Decide — Pubroot

PURPOSE:
    This is the final stage of the review pipeline. It takes the structured review
    from Stage 5 and acts on it:
    
    IF ACCEPTED (score >= 6.0):
      1. Post the formatted review as a GitHub Issue comment
      2. Create a branch paper/{paper-id}
      3. Commit index.md + manifest.json to papers/{journal}/{topic}/{slug}/
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
from urllib.parse import quote

import requests

from pubroot_site_paths import (
    article_index_rel,
    manifest_rel,
    parse_journal_topic,
    reader_url as build_reader_url,
    slugify_title,
)
from secret_scrubber import scrub_all
from index_builder import (
    build_index_entry_from_data,
    merge_entry_into_index,
    apply_selection_and_sort,
    serialize_index,
)

# Canonical site origin for agent-index.json reader_url (override in CI if needed).
PUBROOT_SITE_BASE = os.environ.get("PUBROOT_SITE_BASE", "https://pubroot.com")


def _resolve_publication_paths(gh, parsed: dict, paper_id: str) -> dict:
    """
    Compute journal/topic/slug and repo-relative paths for the SEO layout:
    papers/{journal}/{topic}/{slug}/index.md

    Slug is derived from the title (see slugify_title). Idempotent re-runs rely on
    path_exists on this path in _handle_acceptance — if the path already exists,
    the publish step is skipped (same paper), so we do not disambiguate here.
    Rare title collisions in the same journal/topic would require a manual slug
    fix in a follow-up PR.
    """
    journal, topic = parse_journal_topic(parsed.get("category", ""))
    slug = slugify_title(parsed.get("title", "Untitled"), paper_id)
    idx_rel = article_index_rel(journal, topic, slug)
    return {
        "journal": journal,
        "topic": topic,
        "slug": slug,
        "article_index_path": idx_rel,
        "manifest_path": manifest_rel(journal, topic, slug),
        "reader_url": build_reader_url(PUBROOT_SITE_BASE, journal, topic, slug),
    }


def _hugo_date_string_utc(now: datetime) -> str:
    """
    Format publication time for Hugo front matter `.Date` / `.Params` date handling.

    We emit a single-line RFC3339-style UTC timestamp **without** microseconds.
    That keeps YAML as a normal quoted or plain scalar.

    HISTORY (Mar 2026): `_build_article_md` used `now.isoformat()` for `date` and
    treated **any** string containing `:` as needing the YAML pipe (`|`) block
    for multi-line content. ISO-8601 times contain colons in `T12:34:56`, so
    `date` was incorrectly written as:

        date: |
          2026-03-22T17:15:26.693897+00:00

    Hugo then failed: `the "date" front matter field is not a parsable date`.
    Only **actual** multi-line strings (embedded newlines) should use `|`.
    """
    if now.tzinfo is None:
        dt = now.replace(tzinfo=timezone.utc)
    else:
        dt = now.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


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
    # CASE 2: ACCEPTED — Publish to repo (PR with merge, or direct-to-main fallback)
    # -----------------------------------------------------------------------
    # Contributor stats for accepted papers are updated inside _handle_acceptance
    # only after we know we can write files, so a failed publish does not bump
    # acceptance counts twice on retry.
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
            _remove_labels_if_present(gh, issue_number, ["review-error", "publish-failed", "pending-review"])
            
            # Close accepted issues with a link to the published paper.
            # This keeps the issue list clean and makes it clear the submission is complete.
            #
            # CORRECT URL PATTERN: https://pubroot.com/{journal}/{topic}/{slug}/
            # Hugo's contentDir is "papers/", so papers/ is not part of the URL path.
            # pubroot_site_paths.reader_url() already builds this correctly.
            # 
            # For legacy papers (papers/{paper_id}/article.md), use the Hugo alias
            # at https://pubroot.com/{paper_id}/ which redirects to the canonical URL.
            try:
                # Resolve publication paths to get the reader_url
                paths = _resolve_publication_paths(gh, parsed_submission, paper_id)
                
                # Check if this is a legacy paper (flat layout)
                if gh.path_exists(f"papers/{paper_id}/article.md", "main"):
                    # Use the legacy Hugo alias
                    paper_url = f"{PUBROOT_SITE_BASE.rstrip('/')}/{paper_id}/"
                else:
                    # Use the reader_url from the SEO layout
                    paper_url = paths["reader_url"]
                
                close_comment = (
                    f"✅ **Accepted and Published**\n\n"
                    f"Your submission has been published as paper **{paper_id}**.\n\n"
                    f"View it at: {paper_url} (live within a few minutes)\n\n"
                    f"Thank you for contributing to Pubroot!"
                )
                gh.post_comment(issue_number, close_comment)
                gh.close_issue(issue_number)
            except Exception as close_err:
                # Don't fail the whole pipeline if closing fails
                print(f"WARNING: Failed to close accepted issue: {close_err}")

            return {
                "success": True,
                "action_taken": "accepted",
                "pr_number": pr_number,
                "errors": errors,
            }
        except Exception as e:
            err_txt = str(e)
            errors.append(f"Publication failed after review acceptance: {err_txt}")
            try:
                gh.post_comment(
                    issue_number,
                    _format_publish_failure_comment(paper_id, err_txt),
                )
            except Exception as c_err:
                errors.append(f"Also failed to post failure comment: {c_err}")

            gh.add_labels(issue_number, ["publish-failed"])
            return {
                "success": False,
                "action_taken": "error",
                "pr_number": None,
                "errors": errors,
            }

    # -----------------------------------------------------------------------
    # CASE 3: REJECTED — Contributor bump, label, close
    # -----------------------------------------------------------------------

    try:
        _update_contributors(
            gh=gh,
            branch="main",  # Rejection updates go straight to main
            repo_root=repo_root,
            author=parsed_submission.get("author", "unknown"),
            score=score,
            accepted=False,
            category=parsed_submission.get("category", "general-technical"),
        )
    except Exception as e:
        errors.append(f"Failed to update contributors.json: {str(e)}")

    gh.add_labels(issue_number, ["rejected"])
    _remove_labels_if_present(gh, issue_number, ["pending-review"])
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

    def _git_ref_heads_url(self, branch_name: str) -> str:
        """
        Build the URL for a branch ref. Branch names may contain slashes
        (e.g. paper/2026-003); they must be URL-encoded in the path or
        GitHub parses them as multiple path segments and returns 404.
        """
        return f"{self.base_url}/git/ref/heads/{quote(branch_name, safe='')}"

    def delete_branch_if_exists(self, branch_name: str) -> None:
        """Delete refs/heads/branch_name if it exists. Ignores 404."""
        url = f"{self.base_url}/git/refs/heads/{quote(branch_name, safe='')}"
        resp = requests.delete(url, headers=self.headers, timeout=30)
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    def create_branch(self, branch_name: str, sha: str):
        """
        Create a new branch from the given SHA.

        If the branch already exists (e.g., from a previous failed pipeline run
        that created the branch but failed at the PR step), we delete it first
        and recreate from the latest main SHA. Without this, retries fail with
        422 Unprocessable Entity because the ref already exists.
        """
        ref = f"refs/heads/{branch_name}"
        url_create = f"{self.base_url}/git/refs"
        url_existing = self._git_ref_heads_url(branch_name)

        check = requests.get(url_existing, headers=self.headers, timeout=30)
        if check.status_code == 200:
            self.delete_branch_if_exists(branch_name)

        data = {"ref": ref, "sha": sha}
        resp = requests.post(url_create, headers=self.headers, json=data, timeout=30)
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

    def create_or_update_file_with_sha(self, path: str, content: str, message: str, branch: str, sha: Optional[str]):
        """
        Create or update a file with an explicit SHA for optimistic locking.
        
        FIX (Root Cause B residual): This method uses the SHA from a previous read
        to prevent lost updates. If the file changed between the read and the PUT,
        GitHub returns 409/422 and the pipeline fails (cron will retry with fresh state).
        
        Args:
            path: File path in the repo
            content: File content (will be base64-encoded)
            message: Commit message
            branch: Target branch
            sha: Blob SHA from a previous read, or None if creating a new file
        """
        url = f"{self.base_url}/contents/{path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        
        data = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if sha:
            data["sha"] = sha
        
        resp = requests.put(url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_file_content(self, path: str, branch: str = "main") -> tuple[str, str]:
        """
        Fetch the current content and SHA of a file from the given branch via GitHub API.
        
        This is used to fetch fresh state before updating index files, preventing
        lost-update races when multiple pipeline runs execute concurrently.
        
        Returns:
            tuple[str, str]: (decoded_content, blob_sha)
        
        Raises:
            requests.HTTPError: if the file doesn't exist or the request fails
        """
        url = f"{self.base_url}/contents/{path}"
        resp = requests.get(url, headers=self.headers, params={"ref": branch}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content_b64 = data.get("content", "")
        decoded = base64.b64decode(content_b64).decode("utf-8")
        return decoded, data.get("sha")
    
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

    def path_exists(self, path: str, ref: str = "main") -> bool:
        """
        Return True if a file exists at path on the given ref (branch or SHA).
        
        Returns:
            True if the file exists (HTTP 200)
            False if the file does not exist (HTTP 404)
        
        Raises:
            requests.HTTPError: If the API returns any other status code (5xx, rate limit, etc.)
                                to prevent silently skipping collision checks.
        """
        url = f"{self.base_url}/contents/{path}"
        resp = requests.get(url, headers=self.headers, params={"ref": ref}, timeout=30)
        
        if resp.status_code == 200:
            return True
        elif resp.status_code == 404:
            return False
        else:
            # FIX (Bug B20 part 4): Raise on 5xx, rate limits, etc. instead of returning False
            # Returning False on 5xx would skip the collision check and allow an overwrite
            resp.raise_for_status()

    def remove_label(self, issue_number: int, label_name: str) -> None:
        """Remove a label from an issue (404 if label not on issue is OK)."""
        enc = quote(label_name, safe="")
        url = f"{self.base_url}/issues/{issue_number}/labels/{enc}"
        resp = requests.delete(url, headers=self.headers, timeout=30)
        if resp.status_code not in (204, 404):
            resp.raise_for_status()


# ---------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _remove_labels_if_present(gh: GitHubAPI, issue_number: int, labels: list) -> None:
    for lab in labels:
        try:
            gh.remove_label(issue_number, lab)
        except Exception:
            pass


def _format_publish_failure_comment(paper_id: str, error_detail: str) -> str:
    return (
        f"# Publication step failed (review was ACCEPTED)\n\n"
        f"**Paper ID:** `{paper_id}`\n\n"
        f"The AI review succeeded, but committing files to the repository failed:\n\n"
        f"```\n{error_detail[:4000]}\n```\n\n"
        f"The workflow will retry issues labeled `publish-failed` on the next "
        f"scheduled run, or a maintainer can re-run the **AI Peer Review Pipeline** "
        f"workflow manually for this issue number. "
        f"Re-runs are safe: if the article file already exists on `main` (legacy "
        f"`papers/{paper_id}/article.md` or the SEO path under "
        f"`papers/{{journal}}/{{topic}}/{{slug}}/index.md`), the publisher skips "
        f"duplicate work.\n\n"
        f"---\n*Automated message from Pubroot.*"
    )


def _upload_publication_files_to_branch(
    gh: GitHubAPI,
    branch: str,
    review: dict,
    grounding: dict,
    parsed_submission: dict,
    novelty_results: dict,
    repo_data: dict,
    paper_id: str,
    issue_number: int,
    repo_root: str,
    now: datetime,
) -> None:
    """
    Create or update all publication files on the given branch (feature branch
    or main). Idempotent: safe to call again after a failed PR step when
    retrying onto main.

    LAYOUT (Apr 2026): articles live under papers/{journal}/{topic}/{slug}/index.md
    for SEO-friendly URLs; legacy_aliases is only used by one-off migrations.
    """
    paths = _resolve_publication_paths(gh, parsed_submission, paper_id)
    article_content = _build_article_md(
        parsed_submission,
        review,
        repo_data,
        paper_id,
        now,
        legacy_aliases=None,
    )
    
    # SECURITY (B1 second pass): Scrub the article content before publishing.
    # The article includes LLM-generated fields (review summary, strengths, weaknesses)
    # which could theoretically contain secrets if the LLM was compromised.
    article_content = scrub_all(article_content)
    
    gh.create_or_update_file(
        path=paths["article_index_path"],
        content=article_content,
        message=f"Publish article: {parsed_submission.get('title', paper_id)}",
        branch=branch,
    )

    manifest = _build_manifest(
        parsed_submission, review, repo_data, paper_id, now, novelty_results
    )
    
    # SECURITY (B1 second pass): Scrub the manifest JSON before committing.
    # The manifest contains LLM-generated review metadata which could contain secrets.
    manifest_json_str = json.dumps(manifest, indent=2)
    manifest_json_str = scrub_all(manifest_json_str)
    
    gh.create_or_update_file(
        path=paths["manifest_path"],
        content=manifest_json_str,
        message=f"Add manifest for {paper_id}",
        branch=branch,
    )

    review_with_grounding = {**review, "grounding_metadata": grounding}
    
    # SECURITY (B1 second pass): Scrub the review JSON before committing it publicly.
    # The LLM generates all fields in the review dict, so any of them could contain
    # secrets if the LLM was tricked via prompt injection. Scrub the entire JSON.
    review_json_str = json.dumps(review_with_grounding, indent=2)
    review_json_str = scrub_all(review_json_str)
    
    gh.create_or_update_file(
        path=f"reviews/{paper_id}/review.json",
        content=review_json_str,
        message=f"Add review for {paper_id}",
        branch=branch,
    )

    # Update both agent-index.json and priorroot-index.json by merging the new paper entry.
    # This ensures byte-identical output with the regenerator (Bug B22 fix).
    _update_indexes(gh, branch, paper_id, parsed_submission, review, repo_data, now, paths)

    # Note: contributors.json is no longer committed here because it's now
    # committed directly to main by _update_contributors() before the branch
    # is created. This prevents race conditions and ensures rejection stats
    # are also persisted (Bug B13 fix).


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
) -> Optional[int]:
    """
    Publish accepted work: bump contributor stats locally, upload files, then
    merge via PR. If the PR path fails (403, merge rules, etc.), fall back to
    committing the same files directly to main so the site still updates.
    
    FIX (Bug B20 part b): This function now verifies that files were actually
    written and the index was updated. If the publish is a no-op (existing path,
    slug collision, any silent failure), it raises an exception so stage 6 fails
    loudly with a publish-failed label and a non-zero exit code.

    Returns:
        PR number if merged via PR, or None if published via direct commits to main
        or if the article was already on main (idempotent retry).
    
    Raises:
        Exception: If the publish step completes but no files were written or the
                   index was not updated (indicates a silent collision or skip).
    """
    now = datetime.now(timezone.utc)
    branch_name = f"paper/{paper_id}"

    #  FIX (Bug B20 root cause): Check if a file exists at the target path.
    # If it does, read its frontmatter to extract the paper_id. If the paper_id
    # matches this issue's paper_id, it's an idempotent retry (safe no-op).
    # If the paper_id DIFFERS, it's a duplicate submission that resolved to the
    # FIX (Bug B20 part 4): Check if target path exists AND extract its paper_id.
    # If the file exists and has a DIFFERENT paper_id, this is a path collision
    # (e.g., issue #60 vs 2026-067). RAISE directly to trigger publish-failed.
    # The caller (post_review_and_decide) will post ONE comment and add the label.
    # Don't post a comment here - that causes double failure comments.
    # -------------------------------------------------------------------------------
    _paths_probe = _resolve_publication_paths(gh, parsed_submission, paper_id)
    article_path = _paths_probe["article_index_path"]
    
    # Check for idempotent retry or path collision
    if gh.path_exists(article_path, "main"):
        # File exists — try to read it to check paper_id
        print(f"WARNING: Target path exists: {article_path}. Checking paper_id...")
        
        try:
            content_result = gh.get_file_content(article_path, "main")
            # Handle case where get_file_content returns empty or malformed result
            if not content_result or len(content_result) != 2:
                # Cannot verify — treat as collision for safety
                raise ValueError(f"get_file_content returned malformed result: {content_result}")
            
            article_content, _ = content_result
            existing_paper_id = _extract_paper_id_from_frontmatter(article_content)
            
            if existing_paper_id == paper_id:
                # Same paper_id: idempotent retry after successful publish
                print(f"Idempotent retry detected: existing paper_id {existing_paper_id} matches.")
                return None
            elif existing_paper_id:
                # Different paper_id: duplicate submission, same slug (Bug B20)
                raise Exception(
                    f"PUBLISH COLLISION: This submission resolves to the same path as "
                    f"existing paper **{existing_paper_id}**, but has a different paper ID "
                    f"({paper_id}). This indicates a duplicate or near-duplicate submission "
                    f"that was not caught by the deduplication check. "
                    f"Path: `{article_path}`"
                )
            else:
                # existing_paper_id is None (can't extract) — fail safe, treat as collision
                raise Exception(
                    f"Path collision: {article_path} exists but paper_id cannot be extracted. "
                    f"This issue is {paper_id}. Cannot safely overwrite."
                )
        except Exception as e:
            # If we can't read the file or extract paper_id, fail safe
            if "PUBLISH COLLISION" in str(e) or "Path collision" in str(e):
                raise  # Re-raise our own collision exception
            # Other errors (API failures, etc.) - fail safe, treat as collision
            raise Exception(
                f"Path collision: {article_path} exists but verification failed: {e}. "
                f"Cannot safely overwrite."
            )
    
    # Also check legacy flat path for idempotent retries
    if gh.path_exists(f"papers/{paper_id}/article.md", "main"):
        return None

    # Contributor stats must be reflected in contributors.json before upload.
    # We update on the paper branch (which will be merged to main via PR or direct commit)
    _update_contributors(
        gh=gh,
        branch="main",  # Update on main so it's available immediately, branch will be created from latest main
        repo_root=repo_root,
        author=parsed_submission.get("author", "unknown"),
        score=float(review.get("score", 0)),
        accepted=True,
        category=parsed_submission.get("category", "general-technical"),
    )

    def _try_pr_path() -> int:
        main_sha = gh.get_default_branch_sha()
        gh.create_branch(branch_name, main_sha)
        _upload_publication_files_to_branch(
            gh,
            branch_name,
            review,
            grounding,
            parsed_submission,
            novelty_results,
            repo_data,
            paper_id,
            issue_number,
            repo_root,
            now,
        )
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
        gh.merge_pull_request(pr_number, merge_method="squash")
        return pr_number

    def _direct_main_path() -> None:
        """
        Same files, straight to main. GITHUB_TOKEN always has contents:write;
        PR creation can fail in some org settings even when file writes succeed.
        """
        _upload_publication_files_to_branch(
            gh,
            "main",
            review,
            grounding,
            parsed_submission,
            novelty_results,
            repo_data,
            paper_id,
            issue_number,
            repo_root,
            now,
        )
    
    try:
        pr_number = _try_pr_path()
    except Exception:
        gh.delete_branch_if_exists(branch_name)
        _direct_main_path()
        pr_number = None
    
    # FIX (Bug B20): Verify publish succeeded AFTER the final publish path,
    # with retry for eventual consistency. Never write twice.
    _verify_publish_succeeded_with_retry(gh, _paths_probe, paper_id, "after publish")
    
    return pr_number


def _build_article_md(
    parsed: dict,
    review: dict,
    repo_data: dict,
    paper_id: str,
    now: datetime,
    legacy_aliases: Optional[list] = None,
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
        legacy_aliases: Optional list of paths (e.g. "/2026-042/article/") for Hugo
            redirects after migrating from the old papers/{paper_id}/article.md layout.
    """
    frontmatter = {
        "title": parsed.get("title", "Untitled"),
        "paper_id": paper_id,
        "author": parsed.get("author", "unknown"),
        "category": parsed.get("category", ""),
        "date": _hugo_date_string_utc(now),
        "abstract": parsed.get("abstract", ""),
        "score": review.get("score", 0),
        "verdict": review.get("verdict", "ACCEPTED"),
        "badge": repo_data.get("badge_type", "text_only"),
    }
    _ai_attr = parsed.get("ai_tooling_attribution")
    if _ai_attr:
        frontmatter["ai_tooling_attribution"] = _ai_attr

    # Build YAML frontmatter manually. We use json.dumps for safe quoting
    # of strings that might contain colons, newlines, or special YAML chars.
    # Multi-line strings (like abstracts) use the YAML pipe (|) syntax.
    #
    # IMPORTANT: Only use `|` when the value contains an actual newline.
    # Do NOT key off ":" — ISO-8601 dates and many titles contain colons; treating
    # those as block literals breaks Hugo's date parsing (see _hugo_date_string_utc).
    content = "---\n"
    for key, value in frontmatter.items():
        if isinstance(value, str) and "\n" in value:
            content += f'{key}: |\n'
            for line in value.split("\n"):
                content += f"  {line}\n"
        elif isinstance(value, (int, float)):
            # Numbers should NOT be quoted so Hugo reads them as numbers
            content += f"{key}: {value}\n"
        else:
            content += f"{key}: {json.dumps(value)}\n"
    if legacy_aliases:
        content += "aliases:\n"
        for alias in legacy_aliases:
            content += f"  - {json.dumps(alias)}\n"
    content += "---\n\n"
    content += parsed.get("body", "")

    return content


def _build_manifest(
    parsed: dict, review: dict, repo_data: dict,
    paper_id: str, now: datetime, novelty: dict
) -> dict:
    """
    Build the manifest.json for a published paper.
    
    FIX (Root Cause C): Use second-precision Z format for published_date to match
    the generator and prevent field drift.
    """
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

    # Normalize published_date to second precision Z (match generator)
    published_date = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    valid_until_str = valid_until.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Get supporting_repo, strip quotes
    supporting_repo = parsed.get("supporting_repo")
    if supporting_repo:
        supporting_repo = str(supporting_repo).strip().strip('"').strip("'")
        if not supporting_repo:
            supporting_repo = None
    else:
        supporting_repo = None

    manifest = {
        "paper_id": paper_id,
        "title": parsed.get("title", "Untitled"),
        "author": parsed.get("author", "unknown"),
        "category": parsed.get("category", "general-technical"),
        "published_date": published_date,
        "status": "current",
        "score": review.get("score"),
        "verdict": review.get("verdict"),
        "badge": repo_data.get("badge_type", "text_only"),
        "supporting_repo": supporting_repo,
        "commit_sha": parsed.get("commit_sha"),
        "valid_until": valid_until_str,
        "supersedes": review.get("supersedes"),
        "superseded_by": None,
        "word_count": parsed.get("word_count_body", 0),
    }
    if parsed.get("ai_tooling_attribution"):
        manifest["ai_tooling_attribution"] = parsed["ai_tooling_attribution"]
    return manifest


def _update_indexes(
    gh: GitHubAPI,
    branch: str,
    paper_id: str,
    parsed_submission: dict,
    review: dict,
    repo_data: dict,
    now: datetime,
    paths: dict,
):
    """
    Update both agent-index.json and priorroot-index.json with a new paper entry.
    
    FIX (Bug B22 - Oct 2026): Stage 6 now merges the new paper entry into live indexes
    fetched from the target branch, ensuring byte-identical output with the regenerator.
    
    KEY INSIGHT:
        Stage 6 runs in CI with an event-time checkout. The new paper's files are uploaded
        via GitHub API, NOT written to disk. Therefore, we can't scan papers/ to build indexes.
        Instead, we:
        1. GET live indexes from target branch with their SHAs
        2. Build new paper's entry from in-memory data (same data we're uploading)
        3. Merge entry into live indexes
        4. Apply shared selection, sort, last_updated logic
        5. Commit with optimistic locking and retry on conflict (max 3 attempts)
    
    OPTIMISTIC LOCKING:
        We fetch each index's content and SHA in the same API call. If another writer
        modified the index between our read and write, GitHub returns 409/422. We retry
        up to 3 times, then fail into publish-failed for cron retry.
        
    Args:
        gh: GitHub API client
        branch: Target branch ("main" or "paper/{paper-id}")
        paper_id: The paper ID being published
        parsed_submission: Parsed submission data from Stage 1
        review: Review data from Stage 5
        repo_data: Repository data from Stage 3
        now: Publication timestamp
        paths: Publication paths dict (article_index_path, reader_url, etc.)
    """
    # Build the new paper's entry from in-memory data
    # This is the same data we're uploading to manifest.json and frontmatter
    published_date = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # SECURITY (Bug B22 secret scrubbing): Build the index entry from the EXACT
    # scrubbed strings that get uploaded to the repo. This ensures the index entry
    # is byte-identical to what the regenerator derives from the committed files.
    # All text fields must be scrubbed before being passed to build_index_entry_from_data.
    scrubbed_title = scrub_all(str(parsed_submission.get("title", "Untitled")))
    scrubbed_author = scrub_all(str(parsed_submission.get("author", "unknown")))
    scrubbed_abstract = scrub_all(str(parsed_submission.get("abstract", "")))
    scrubbed_supporting_repo = None
    if parsed_submission.get("supporting_repo"):
        scrubbed_supporting_repo = scrub_all(str(parsed_submission["supporting_repo"]))
    scrubbed_ai_attr = None
    if parsed_submission.get("ai_tooling_attribution"):
        scrubbed_ai_attr = scrub_all(str(parsed_submission["ai_tooling_attribution"]))
    
    new_entry = build_index_entry_from_data(
        paper_id=paper_id,
        title=scrubbed_title,
        author=scrubbed_author,
        category=parsed_submission.get("category", "general-technical"),
        abstract=scrubbed_abstract,
        published_date=published_date,
        review_score=review.get("score"),
        badge=repo_data.get("badge_type", "text_only"),
        article_path=paths["article_index_path"],
        reader_url=paths["reader_url"],
        review_path=f"reviews/{paper_id}/review.json",
        supporting_repo=scrubbed_supporting_repo,
        ai_tooling_attribution=scrubbed_ai_attr,
    )
    
    # Determine which index to update based on category
    is_priorart = new_entry["category"].startswith("prior-art/")
    target_index_file = "priorroot-index.json" if is_priorart else "agent-index.json"
    other_index_file = "agent-index.json" if is_priorart else "priorroot-index.json"
    
    # Retry loop for optimistic locking conflicts
    # Backoff delays for retries (patchable in tests)
    backoff_delays = [1, 2, 4]  # seconds: 1s, 2s, 4s
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Fetch live indexes with their SHAs (same API call)
            target_index_json, target_sha = gh.get_file_content(target_index_file, branch=branch)
            target_index = json.loads(target_index_json)
            
            other_index_json, other_sha = gh.get_file_content(other_index_file, branch=branch)
            other_index = json.loads(other_index_json)
            
            # Merge new entry into target index
            merge_entry_into_index(target_index, new_entry)
            
            # Apply selection (filter archived) and sort to both indexes.
            # We need ALL entries for last_updated calculation (max published_date
            # across both indexes ensures they stay in sync).
            all_entries = target_index["papers"] + other_index["papers"]
            apply_selection_and_sort(target_index, all_entries)
            apply_selection_and_sort(other_index, all_entries)
            
            # Serialize with canonical formatting
            target_content = serialize_index(target_index)
            other_content = serialize_index(other_index)
            
            # Commit target index (the one with the new paper)
            gh.create_or_update_file_with_sha(
                path=target_index_file,
                content=target_content,
                message=f"Update {target_index_file}: add {paper_id}",
                branch=branch,
                sha=target_sha,
            )
            
            # Only commit other index if it changed (last_updated update)
            # Compare with fetched content to avoid redundant writes
            if other_content != other_index_json:
                gh.create_or_update_file_with_sha(
                    path=other_index_file,
                    content=other_content,
                    message=f"Update {other_index_file}: last_updated after {paper_id}",
                    branch=branch,
                    sha=other_sha,
                )
            
            # Success - exit retry loop
            return
            
        except requests.HTTPError as e:
            # Check for optimistic locking conflict (409 Conflict or 422 Unprocessable Entity)
            if e.response is not None and e.response.status_code in (409, 422):
                if attempt < max_retries - 1:
                    # Retry with fresh state after backoff delay
                    import time
                    delay = backoff_delays[attempt]
                    print(f"Index update conflict on attempt {attempt + 1}, retrying after {delay}s backoff...")
                    time.sleep(delay)
                    continue
                else:
                    # Max retries exhausted - fail into publish-failed
                    raise Exception(
                        f"Index update failed after {max_retries} attempts due to conflicts. "
                        f"Another writer modified the index between read and write. "
                        f"This paper will be retried by the cron job."
                    )
            else:
                # Other HTTP error - propagate immediately
                raise


def _update_contributors(
    gh: GitHubAPI,
    branch: str,
    repo_root: str,
    author: str,
    score: float,
    accepted: bool,
    category: str
):
    """
    Update the contributor's stats in contributors.json and commit it.
    
    This is called for BOTH accepted and rejected submissions. It updates
    the contributor's submission count, acceptance rate, average score,
    and per-category stats. The reputation score is recalculated by
    reputation_calculator.py (called separately).
    
    RACE CONDITION FIX (2026-10-24):
        Like agent-index.json, contributors.json previously suffered from lost-update
        races (Bug B13). Now we fetch fresh state from the target branch via GitHub API,
        update it, and commit it back. This ensures rejection stats are persisted and
        acceptance stats don't get overwritten by concurrent runs.
    """
    try:
        # Fetch fresh state from the target branch via GitHub API
        contributors_json_str, _blob_sha = gh.get_file_content("contributors.json", branch=branch)
        data = json.loads(contributors_json_str)
    except requests.HTTPError as e:
        # If contributors.json doesn't exist on the branch yet (shouldn't happen),
        # fall back to the local checkout as a last resort
        if e.response is not None and e.response.status_code == 404:
            contributors_path = os.path.join(repo_root, "contributors.json")
            with open(contributors_path, "r") as f:
                data = json.load(f)
        else:
            raise
    
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
    
    # Commit the updated contributors.json back to the branch
    # This fixes Bug B13: rejection stats are now persisted, and acceptance
    # stats can't be lost due to concurrent pipeline runs
    gh.create_or_update_file(
        path="contributors.json",
        content=json.dumps(data, indent=2),
        message=f"Update contributor stats: {author} ({'accepted' if accepted else 'rejected'})",
        branch=branch,
    )


def _format_review_comment(
    review: dict, grounding: dict, paper_id: str, score: float, verdict: str
) -> str:
    """
    Format the review JSON into a readable Markdown comment for the GitHub Issue.
    
    This is what the submitter sees. It needs to be clear, actionable, and
    professional. We show the key metrics prominently, then the detailed
    breakdown, then the full claims verification.
    
    SECURITY (B1 second pass): The formatted comment is scrubbed for secrets before
    being returned. Even if the LLM was somehow tricked into echoing a secret that
    leaked into the prompt, the scrubber will redact it before it reaches the public
    issue comment.
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
        "## Summary",
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
    
    comment_text = "\n".join(lines)
    
    # SECURITY (B1 second pass): Scrub any secrets that may have leaked into the LLM output.
    # This is defense-in-depth: even if a malicious submitter exploited a bug and got secrets
    # into the prompt, and the LLM echoed them in the review, they will be redacted here
    # before being posted publicly.
    comment_text = scrub_all(comment_text)
    
    return comment_text


def _format_error_comment(error_msg: str, paper_id: str) -> str:
    """
    Format an error comment when the review pipeline fails.
    
    SECURITY (B1 second pass): Error messages could potentially contain secrets if
    they include stack traces, environment details, or API responses. Scrub before posting.
    """
    comment = (
        f"# AI Peer Review — Error\n\n"
        f"**Paper ID:** `{paper_id}`\n\n"
        f"The review pipeline encountered an error:\n\n"
        f"```\n{error_msg}\n```\n\n"
        f"This issue has been labeled `review-error` and will be retried. "
        f"If the problem persists, a maintainer will investigate.\n\n"
        f"---\n"
        f"*This is an automated message from the Pubroot pipeline.*"
    )
    return scrub_all(comment)


def _score_to_bar(score: float) -> str:
    """Convert a 0-10 score to a visual bar for the comment."""
    filled = int(round(score))
    empty = 10 - filled
    return "[" + "|" * filled + "." * empty + "]"


def _extract_paper_id_from_frontmatter(article_content: str) -> Optional[str]:
    """
    Extract the paper_id from Hugo frontmatter.
    
    FIX (Bug B20 root cause): Read the paper_id field from the existing file
    to detect duplicate submissions that resolved to the same slug.
    
    Returns:
        The paper_id string, or None if not found.
    """
    # Frontmatter is between --- delimiters
    if not article_content.startswith("---"):
        return None
    
    # Find the closing ---
    end_pos = article_content.find("\n---\n", 4)
    if end_pos == -1:
        return None
    
    frontmatter = article_content[4:end_pos]
    
    # Look for paper_id: line
    match = re.search(r'^paper_id:\s*["\']?([^"\'\n]+)["\']?', frontmatter, re.MULTILINE)
    if match:
        return match.group(1).strip()
    
    return None


def _verify_publish_succeeded_with_retry(
    gh: GitHubAPI,
    paths: dict,
    paper_id: str,
    context: str,
    max_retries: int = 3,
) -> None:
    """
    Verify publication with retry for eventual consistency.
    
    FIX (Bug B20): GitHub API may have eventual consistency delays after PR merge.
    Retry up to 3 times with exponential backoff before failing.
    
    Args:
        gh: GitHub API wrapper
        paths: Publication paths dict
        paper_id: The paper ID
        context: Description for error messages
        max_retries: Maximum retry attempts (default 3)
    
    Raises:
        Exception: If verification fails after all retries
    """
    import time
    
    for attempt in range(max_retries):
        try:
            _verify_publish_succeeded(gh, paths, paper_id, context)
            return  # Success
        except Exception as e:
            if attempt < max_retries - 1:
                wait_seconds = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Verification attempt {attempt + 1} failed, retrying in {wait_seconds}s: {e}")
                time.sleep(wait_seconds)
            else:
                # Final attempt failed
                raise


def _verify_publish_succeeded(
    gh: GitHubAPI,
    paths: dict,
    paper_id: str,
    context: str,
) -> None:
    """
    Verify that publication actually wrote files and updated the index (Bug B20 fix).
    
    FIX HISTORY:
        Issue #60 was a duplicate of 2026-067. Stage 6 ran _upload_publication_files_to_branch,
        but the article path already existed, so the GitHub API silently skipped the write
        (returning 200 OK with no content change). The PR merged, labels were added, issue
        was closed, but NO new files were created and agent-index.json was NOT updated.
        
        This function detects that failure case by checking that:
        1. The article file exists on main after the publish operation
        2. The paper_id appears in agent-index.json or priorroot-index.json
        
        If either check fails, we raise an exception so the workflow run fails and the
        issue gets labeled publish-failed (not published).
    
    Args:
        gh: GitHub API wrapper
        paths: Publication paths dict from _resolve_publication_paths
        paper_id: The paper ID (e.g., "2026-060")
        context: Description of when this check runs (for error message)
    
    Raises:
        Exception: If verification fails (article path missing or paper not in index)
    """
    article_path = paths["article_index_path"]
    
    # CHECK 1: Article file exists on main
    if not gh.path_exists(article_path, "main"):
        raise Exception(
            f"PUBLISH VERIFICATION FAILED {context}: "
            f"Article file '{article_path}' does not exist on main. "
            f"This indicates a silent collision or no-op write. "
            f"The issue will be labeled publish-failed for retry."
        )
    
    # CHECK 2: Paper appears in agent-index.json or priorroot-index.json
    # Determine which index based on category
    category = paths.get("journal", "")
    is_priorart = category.startswith("prior-art")
    index_name = "priorroot-index.json" if is_priorart else "agent-index.json"
    
    try:
        index_json_str, _ = gh.get_file_content(index_name, branch="main")
        try:
            index_data = json.loads(index_json_str)
        except (json.JSONDecodeError, ValueError) as json_err:
            raise Exception(
                f"PUBLISH VERIFICATION FAILED {context}: "
                f"Could not parse {index_name} as JSON: {json_err}. "
                f"The issue will be labeled publish-failed for retry."
            )
        
        papers = index_data.get("papers", [])
        
        paper_ids = [p.get("id") for p in papers]
        if paper_id not in paper_ids:
            raise Exception(
                f"PUBLISH VERIFICATION FAILED {context}: "
                f"Paper {paper_id} was not added to {index_name}. "
                f"Found {len(paper_ids)} papers, but {paper_id} is missing. "
                f"This indicates the index update was skipped or failed. "
                f"The issue will be labeled publish-failed for retry."
            )
    except requests.HTTPError as e:
        # If we can't fetch the index, that's a real failure too
        raise Exception(
            f"PUBLISH VERIFICATION FAILED {context}: "
            f"Could not fetch {index_name} from main to verify publication. "
            f"HTTP {e.response.status_code if e.response is not None else 'error'}. "
            f"The issue will be labeled publish-failed for retry."
        )
