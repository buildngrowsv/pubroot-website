"""
Stages 4-6 Reviewer — Pubroot Security Hardening

PURPOSE:
    This script runs ONLY stages 4-6 of the review pipeline (prompt building, LLM review,
    and publication) with FULL secrets in scope. It is called by the review-and-publish job
    in review.yml, which has OPENROUTER_API_KEY and write permissions.
    
    This script consumes the JSON artifact produced by stages_1_to_3_analyzer.py and
    NEVER checks out, clones, or executes any code from the submitter's repository.

SECURITY ARCHITECTURE:
    - Input: JSON artifact from job 1 (stages 1-3 output)
    - Environment: OPENROUTER_API_KEY, GITHUB_TOKEN (write), GITHUB_REPOSITORY
    - NO ACCESS TO: Submitter's repository (never cloned or checked out)
    - Output: Issue comment, review.json, published paper (all scrubbed by secret_scrubber)
    
    This architecture ensures that even if a malicious submitter corrupted the JSON artifact
    (via a hypothetical bug in stages 1-3), they still cannot access OPENROUTER_API_KEY because
    it was not in scope when they could execute code. The worst they could do is corrupt the
    structured data, and all outputs are scrubbed by secret_scrubber before posting.

CALLED BY:
    .github/workflows/review.yml (review-and-publish job)

USAGE:
    python stages_4_to_6_reviewer.py <analysis_json_path>
"""

import json
import os
import sys
from datetime import datetime, timezone

# Import only the stages we need (4-6)
from stage_4_build_review_prompt import build_review_prompt
from stage_5_gemini_grounded_review import run_openrouter_review
from stage_6_post_review_and_decide import post_review_and_decide, GitHubAPI
from reputation_calculator import update_all_reputations


def run_stages_4_to_6(analysis_data: dict) -> dict:
    """
    Run stages 4-6 consuming only the JSON artifact from stages 1-3.
    
    This function NEVER touches the submitter's repository. All data about the
    repo comes from the analysis_data dict, which contains sanitized file contents
    that were already read (and symlink-protected) in job 1.
    
    Args:
        analysis_data: The output from stages_1_to_3_analyzer.py, containing:
            - issue_number
            - paper_id
            - parsed (stage 1 output)
            - novelty (stage 2 output)
            - repo_data (stage 3 output)
            - priority_info
            - payment_verification
            - action ('continue', 'filtered', 'error')
            - errors
    
    Returns:
        dict with keys:
            - success (bool)
            - action (str)
            - errors (list)
    """
    
    # Read environment (full secrets for LLM and publication)
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model_name = os.environ.get("PUBROOT_MODEL", "google/gemini-3.5-flash-lite")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    github_workspace = os.environ.get("GITHUB_WORKSPACE", "")
    
    if not openrouter_api_key:
        return {
            "success": False,
            "action": "error",
            "errors": ["OPENROUTER_API_KEY not set. Please add this secret to the repository settings."],
        }
    
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
    
    # Extract data from the analysis
    if not analysis_data.get("success"):
        print(f"[Stage 4-6] Analysis failed or was filtered. Action: {analysis_data.get('action')}")
        return analysis_data
    
    action = analysis_data.get("action", "")
    if action != "continue":
        print(f"[Stage 4-6] Analysis did not continue. Action: {action}")
        return analysis_data
    
    issue_number = analysis_data["issue_number"]
    paper_id = analysis_data["paper_id"]
    parsed = analysis_data["parsed"]
    novelty = analysis_data["novelty"]
    repo_data = analysis_data["repo_data"]
    priority_info = analysis_data["priority_info"]
    
    errors = analysis_data.get("errors", [])
    
    print(f"[Stage 4-6] Processing paper {paper_id} from issue #{issue_number}")
    print(f"[Stage 4-6] Category: {parsed.get('category', 'unknown')}")
    print(f"[Stage 4-6] Repo available: {repo_data.get('available', False)}")
    
    # Stage 4: Build review prompt
    print(f"[Stage 4] Building review prompt...")
    prompt = build_review_prompt(
        parsed_submission=parsed,
        novelty_results=novelty,
        repo_data=repo_data,
        calibration_dir=os.path.join(github_workspace, "_calibration"),
    )
    
    if not prompt:
        return {
            "success": False,
            "action": "error",
            "paper_id": paper_id,
            "errors": ["Failed to build review prompt"],
        }
    
    print(f"[Stage 4] ✓ Prompt built ({len(prompt)} chars)")
    
    # Stage 5: OpenRouter LLM review with web search
    print(f"[Stage 5] Running LLM review via OpenRouter (model: {model_name})...")
    review_result = run_openrouter_review(
        review_prompt=prompt,
        openrouter_api_key=openrouter_api_key,
        model_name=model_name,
    )
    
    if not review_result.get("success", False):
        review_errors = review_result.get("errors", ["Unknown error"])
        print(f"[Stage 5] ✗ Review failed: {review_errors}")
        
        # Post error comment and label
        gh = GitHubAPI(github_token, github_repo)
        post_review_and_decide(
            gh=gh,
            review=None,
            grounding={},
            parsed_submission=parsed,
            novelty_results=novelty,
            repo_data=repo_data,
            paper_id=paper_id,
            issue_number=issue_number,
            repo_root=github_workspace,
            priority_info=priority_info,
        )
        
        return {
            "success": False,
            "action": "review_error",
            "paper_id": paper_id,
            "errors": review_errors,
        }
    
    review = review_result["review"]
    grounding = review_result["grounding"]
    
    print(f"[Stage 5] ✓ Review complete. Score: {review.get('score', '?')}/10, Verdict: {review.get('verdict', '?')}")
    
    # Stage 6: Post review and decide
    print(f"[Stage 6] Posting review and deciding...")
    gh = GitHubAPI(github_token, github_repo)
    
    stage_6_result = post_review_and_decide(
        gh=gh,
        review=review,
        grounding=grounding,
        parsed_submission=parsed,
        novelty_results=novelty,
        repo_data=repo_data,
        paper_id=paper_id,
        issue_number=issue_number,
        repo_root=github_workspace,
        priority_info=priority_info,
    )
    
    if not stage_6_result.get("success", False):
        stage_6_errors = stage_6_result.get("errors", ["Unknown publication error"])
        print(f"[Stage 6] ✗ Publication failed: {stage_6_errors}")
        return {
            "success": False,
            "action": "publish_error",
            "paper_id": paper_id,
            "score": review.get("score"),
            "errors": errors + stage_6_errors,
        }
    
    final_action = stage_6_result.get("action", "unknown")
    print(f"[Stage 6] ✓ {final_action.upper()}")
    
    # Update reputations (runs locally, commits in stage 6 if accepted)
    if final_action == "accepted":
        print(f"[Reputation] Updating contributor reputations...")
        update_all_reputations(github_workspace)
    
    return {
        "success": True,
        "action": final_action,
        "paper_id": paper_id,
        "score": review.get("score"),
        "errors": errors,
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python stages_4_to_6_reviewer.py <analysis_json_path>")
        sys.exit(1)
    
    analysis_json_path = sys.argv[1]
    
    model_name = os.environ.get("PUBROOT_MODEL", "google/gemini-3.5-flash-lite")
    print(f"=== Stages 4-6 Reviewer (LLM + Publication) ===")
    print(f"Input: {analysis_json_path}")
    print(f"Environment: OPENROUTER_API_KEY, GITHUB_TOKEN (write)")
    print(f"Model: {model_name}")
    print(f"SECURITY: This job NEVER touches the submitter's repository.")
    print(f"          All repo data comes from the sanitized JSON artifact.")
    print()
    
    # Load the analysis from job 1
    try:
        with open(analysis_json_path, "r") as f:
            analysis_data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load analysis JSON: {e}")
        sys.exit(1)
    
    result = run_stages_4_to_6(analysis_data)
    
    print()
    print(f"✓ Pipeline complete.")
    print(f"  Action: {result['action']}")
    print(f"  Success: {result['success']}")
    if result.get("score"):
        print(f"  Score: {result['score']}/10")
    
    # Exit with appropriate code
    if result["action"] in ["error", "review_error", "publish_error"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
