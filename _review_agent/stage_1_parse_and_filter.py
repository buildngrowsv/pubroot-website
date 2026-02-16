"""
Stage 1: Parse & Filter — Pubroot

PURPOSE:
    This is the first stage of the 6-stage review pipeline. It takes the raw
    GitHub Issue body (which comes from the submission.yml template) and extracts
    structured fields from it. It then validates format, word counts, category
    existence, language, and topic slot availability.

    This stage acts as a cheap gatekeeper — if the submission fails basic checks
    here, we never call any external APIs (saving cost and time). All checks in
    this stage are pure Python with zero API calls and zero cost.

CALLED BY:
    review_pipeline_main.py — which passes the issue body string and the repo
    root path (so we can read journals.json and agent-index.json).

DEPENDS ON:
    - journals.json (for category validation and refresh rate checking)
    - agent-index.json (for checking existing publications in the same topic slot)
    - The GitHub Issue body format produced by .github/ISSUE_TEMPLATE/submission.yml

DESIGN DECISIONS:
    - We parse by looking for the exact label text from the GitHub Issue form.
      GitHub renders form responses with "### Label" headers. If the template
      labels change, this parser MUST be updated to match.
    - Prompt injection detection is intentionally simple (regex-based) because
      the real protection happens in stage_4_build_review_prompt.py where we
      sanitize content before injecting it into the LLM prompt. This stage just
      flags the most obvious patterns.
    - Language detection is basic (checks for common English words). We don't
      use a heavy NLP library because the Actions runner should stay lightweight.
      If non-English submissions become common, we can add langdetect later.

RETURNS:
    A dict with all parsed fields + a list of validation errors (empty if valid).
"""

import json
import re
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


def parse_and_filter_submission(
    issue_body: str,
    repo_root: str,
    issue_author: str
) -> dict:
    """
    Parse a GitHub Issue body from the submission template and validate it.

    This is the ONLY function in this file, following the one-function-per-file
    pattern. It handles both parsing and validation in one pass.

    Args:
        issue_body: The raw Markdown body of the GitHub Issue, as created by
                    the submission.yml form template. GitHub renders form
                    responses with "### Label\\n\\nValue" format.
        repo_root:  Absolute path to the repository root. Used to read
                    journals.json and agent-index.json for validation.
        issue_author: GitHub handle of the issue creator (for logging).

    Returns:
        dict with keys:
            - 'valid' (bool): Whether the submission passes all checks
            - 'errors' (list[str]): List of validation error messages (empty if valid)
            - 'warnings' (list[str]): Non-blocking warnings
            - 'parsed' (dict): The extracted fields:
                - 'title' (str)
                - 'category' (str): slug from journals.json
                - 'abstract' (str)
                - 'body' (str): full article text
                - 'supporting_repo' (str or None)
                - 'commit_sha' (str or None)
                - 'repo_visibility' (str): 'public', 'private', or 'no-repo'
                - 'payment_code' (str or None)
                - 'author' (str): GitHub handle
                - 'word_count_abstract' (int)
                - 'word_count_body' (int)
    """

    errors = []
    warnings = []

    # -----------------------------------------------------------------------
    # STEP 1: Extract structured fields from the Issue body
    # -----------------------------------------------------------------------
    # GitHub Issue forms render responses as:
    #   ### Label
    #
    #   Value
    #
    # We parse by splitting on "### " and extracting label-value pairs.
    # This is more reliable than regex because it handles multi-line values
    # (like the article body) correctly.
    # -----------------------------------------------------------------------

    parsed_fields = _extract_form_fields(issue_body)

    # Map form field labels to our internal field names
    # The labels must match EXACTLY what's in submission.yml
    title = parsed_fields.get("Article Title", "").strip()
    category = parsed_fields.get("Category", "").strip()
    abstract = parsed_fields.get("Abstract", "").strip()
    body = parsed_fields.get("Article Body", "").strip()
    supporting_repo = parsed_fields.get("Supporting Repository URL", "").strip() or None
    commit_sha = parsed_fields.get("Commit SHA", "").strip() or None
    repo_visibility = parsed_fields.get("Repository Visibility", "no-repo").strip()
    payment_code = parsed_fields.get("Payment Code (Optional)", "").strip() or None

    # -----------------------------------------------------------------------
    # STEP 2: Validate required fields exist
    # -----------------------------------------------------------------------

    if not title:
        errors.append("Missing required field: Article Title")
    if not category:
        errors.append("Missing required field: Category")
    if not abstract:
        errors.append("Missing required field: Abstract")
    if not body:
        errors.append("Missing required field: Article Body")

    # -----------------------------------------------------------------------
    # STEP 3: Validate word counts
    # -----------------------------------------------------------------------
    # Abstract: max 300 words (enforced to keep search index entries concise)
    # Body: min 200 words (prevents trivially short submissions)
    # These thresholds are from the architecture doc and can be tuned.
    # -----------------------------------------------------------------------

    word_count_abstract = len(abstract.split()) if abstract else 0
    word_count_body = len(body.split()) if body else 0

    if word_count_abstract > 350:
        # We give a 50-word buffer above the 300 limit because word counting
        # on Markdown text (with code blocks, links) can vary slightly
        errors.append(
            f"Abstract exceeds 300-word limit ({word_count_abstract} words). "
            "Please condense your abstract."
        )
    elif word_count_abstract > 300:
        warnings.append(
            f"Abstract is slightly over 300 words ({word_count_abstract} words). "
            "Consider trimming for clarity."
        )

    if word_count_body < 200:
        errors.append(
            f"Article body is too short ({word_count_body} words, minimum 200). "
            "Please provide a more detailed writeup."
        )

    # -----------------------------------------------------------------------
    # STEP 4: Validate category exists in journals.json
    # -----------------------------------------------------------------------
    # We load journals.json from the repo to check that the submitted category
    # is a valid slug. This prevents typos and ensures the review pipeline can
    # find the right review criteria and slot rules for this category.
    # -----------------------------------------------------------------------

    journals_path = os.path.join(repo_root, "journals.json")
    try:
        with open(journals_path, "r") as f:
            journals_data = json.load(f)
        valid_categories = list(journals_data.get("journals", {}).keys())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If journals.json is missing or corrupt, that's a system error, not
        # a submission error. We warn but don't block.
        warnings.append(f"Could not load journals.json: {e}")
        valid_categories = []

    if valid_categories and category and category not in valid_categories:
        errors.append(
            f"Invalid category '{category}'. Valid categories are: "
            f"{', '.join(valid_categories)}"
        )

    # -----------------------------------------------------------------------
    # STEP 5: Check topic slot availability (refresh rate enforcement)
    # -----------------------------------------------------------------------
    # Some categories have a refresh_rate_days setting. For example, 
    # "llm-benchmarks" has a 30-day refresh rate, meaning only one article
    # per sub-topic is accepted per month. This prevents spam and creates
    # competitive submission dynamics.
    #
    # We check agent-index.json for the most recent accepted article in the
    # same category. If it was published within the refresh window, we reject.
    #
    # Categories with refresh_rate_days=0 are always open.
    # -----------------------------------------------------------------------

    if valid_categories and category in valid_categories:
        journal_config = journals_data["journals"][category]
        refresh_days = journal_config.get("refresh_rate_days", 0)

        if refresh_days > 0:
            slot_error = _check_topic_slot_availability(
                repo_root, category, refresh_days
            )
            if slot_error:
                errors.append(slot_error)

    # -----------------------------------------------------------------------
    # STEP 6: Basic prompt injection detection
    # -----------------------------------------------------------------------
    # We scan the submission text for common prompt injection patterns.
    # This is NOT a comprehensive defense — the real protection is in
    # stage_4_build_review_prompt.py where we sanitize content before
    # injecting into the LLM prompt. But catching obvious patterns here
    # saves us from wasting an LLM call on clearly malicious submissions.
    #
    # We check the title, abstract, and first 2000 chars of body.
    # -----------------------------------------------------------------------

    text_to_scan = f"{title} {abstract} {body[:2000]}"
    injection_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+the\s+above",
        r"disregard\s+(all\s+)?prior",
        r"you\s+are\s+now\s+(a|an)",
        r"new\s+instructions?\s*:",
        r"system\s*:\s*you",
        r"<\s*system\s*>",
        r"override\s+(the\s+)?prompt",
        r"forget\s+(everything|all|your)",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text_to_scan, re.IGNORECASE):
            errors.append(
                "Submission flagged for potential prompt injection. "
                "If this is a false positive, please rephrase the flagged section."
            )
            break

    # -----------------------------------------------------------------------
    # STEP 7: Basic language check (English required)
    # -----------------------------------------------------------------------
    # Simple heuristic: check if common English words appear frequently enough.
    # We don't use langdetect to keep dependencies light. This catches obvious
    # non-English submissions but may miss borderline cases. In those cases,
    # the LLM review (Stage 5) will catch it and score accordingly.
    # -----------------------------------------------------------------------

    if body and word_count_body >= 50:
        common_english = {"the", "is", "of", "and", "to", "in", "a", "that", "for", "it"}
        body_words_lower = set(body.lower().split())
        english_overlap = len(common_english & body_words_lower)
        if english_overlap < 3:
            warnings.append(
                "The article body may not be in English. Currently only English "
                "submissions are reviewed. Non-English articles may receive lower scores."
            )

    # -----------------------------------------------------------------------
    # STEP 8: Validate supporting repo URL format (if provided)
    # -----------------------------------------------------------------------

    if supporting_repo:
        github_url_pattern = r"^https?://github\.com/[\w.-]+/[\w.-]+/?$"
        if not re.match(github_url_pattern, supporting_repo):
            warnings.append(
                f"Supporting repo URL '{supporting_repo}' doesn't look like a "
                "standard GitHub repository URL. Expected format: "
                "https://github.com/owner/repo"
            )

    # -----------------------------------------------------------------------
    # STEP 9: Validate commit SHA format (if provided)
    # -----------------------------------------------------------------------

    if commit_sha:
        sha_pattern = r"^[0-9a-f]{7,40}$"
        if not re.match(sha_pattern, commit_sha, re.IGNORECASE):
            warnings.append(
                f"Commit SHA '{commit_sha}' doesn't look like a valid git SHA. "
                "Expected 7-40 character hex string."
            )

    # -----------------------------------------------------------------------
    # BUILD AND RETURN RESULT
    # -----------------------------------------------------------------------

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "parsed": {
            "title": title,
            "category": category,
            "abstract": abstract,
            "body": body,
            "supporting_repo": supporting_repo,
            "commit_sha": commit_sha,
            "repo_visibility": repo_visibility,
            "payment_code": payment_code,
            "author": issue_author,
            "word_count_abstract": word_count_abstract,
            "word_count_body": word_count_body,
        }
    }

    return result


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS (private to this module)
# ---------------------------------------------------------------------------
# These are small utilities used by the main function above. They're in this
# file because they're tightly coupled to the parsing logic and not reused
# elsewhere. The one-function-per-file rule applies to the PUBLIC API function.
# ---------------------------------------------------------------------------


def _extract_form_fields(issue_body: str) -> dict:
    """
    Parse a GitHub Issue form response into label-value pairs.

    GitHub renders form responses as:
        ### Label

        Value (possibly multi-line)

        ### Next Label
        ...

    We split on "### " markers and extract pairs. Multi-line values (like
    the article body) are preserved with their original formatting.

    Returns:
        dict mapping field labels to their string values.
    """
    fields = {}
    # Split by ### headers. The first element before any ### is usually empty
    # or contains the form preamble (which we skip).
    sections = re.split(r"^### ", issue_body, flags=re.MULTILINE)

    for section in sections[1:]:  # Skip the preamble (before first ###)
        lines = section.split("\n", 1)
        if len(lines) >= 2:
            label = lines[0].strip()
            value = lines[1].strip()
            # Remove "_No response_" placeholder that GitHub uses for empty optional fields
            if value == "_No response_":
                value = ""
            fields[label] = value
        elif len(lines) == 1:
            label = lines[0].strip()
            fields[label] = ""

    return fields


def _check_topic_slot_availability(
    repo_root: str,
    category: str,
    refresh_days: int
) -> Optional[str]:
    """
    Check if a topic slot is available for a new submission in the given category.

    Some categories (like llm-benchmarks) have a refresh_rate_days setting that
    limits how often new articles can be accepted in the same category. This
    prevents spam and creates competitive timing dynamics — agents learn to
    submit when slots open.

    We check agent-index.json for the most recent accepted paper in the category.
    If it was published within the refresh window, we return an error message.

    Args:
        repo_root: Path to the repo root (to find agent-index.json)
        category: The category slug to check
        refresh_days: How many days must pass between accepted articles

    Returns:
        Error message string if the slot is blocked, None if the slot is open.
    """
    index_path = os.path.join(repo_root, "agent-index.json")
    try:
        with open(index_path, "r") as f:
            index_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the index doesn't exist yet, all slots are open
        return None

    papers = index_data.get("papers", [])
    now = datetime.now(timezone.utc)

    # Find the most recent paper in this category
    latest_date = None
    for paper in papers:
        if paper.get("category") == category:
            pub_date_str = paper.get("published_date")
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str)
                    if latest_date is None or pub_date > latest_date:
                        latest_date = pub_date
                except ValueError:
                    continue

    if latest_date is not None:
        slot_opens = latest_date + timedelta(days=refresh_days)
        if now < slot_opens:
            days_remaining = (slot_opens - now).days + 1
            return (
                f"Topic slot for '{category}' is currently filled. "
                f"A new article was accepted {(now - latest_date).days} days ago. "
                f"The slot reopens in ~{days_remaining} days "
                f"({slot_opens.strftime('%Y-%m-%d')}). "
                f"This category has a {refresh_days}-day refresh rate."
            )

    return None
