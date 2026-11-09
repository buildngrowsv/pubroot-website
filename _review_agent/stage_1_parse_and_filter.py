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
    issue_author: str,
    paper_id: Optional[str] = None,
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
        paper_id: Optional paper ID (e.g., "2026-060") for self-match detection
                  in duplicate checking. If provided, the dedup check will skip
                  index entries with the same paper_id.

    Returns:
        dict with keys:
            - 'valid' (bool): Whether the submission passes all checks
            - 'errors' (list[str]): List of validation error messages (empty if valid)
            - 'warnings' (list[str]): Non-blocking warnings
            - 'parsed' (dict): The extracted fields:
                - 'title' (str)
                - 'category' (str): full "journal/topic" slug (e.g., "ai/llm-benchmarks")
                - 'journal' (str): journal slug extracted from category (e.g., "ai")
                - 'topic' (str): topic slug extracted from category (e.g., "llm-benchmarks")
                - 'submission_type' (str): one of original-research, case-study, benchmark, review-survey, tutorial, dataset
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
    # -----------------------------------------------------------------------
    # SUBMISSION TYPE (added Feb 2026)
    # -----------------------------------------------------------------------
    # submission_type distinguishes how the article is judged. Different types
    # have different review emphasis (e.g., novelty matters more for original
    # research, reproducibility matters more for benchmarks). The valid types
    # are: original-research, case-study, benchmark, review-survey, tutorial,
    # dataset. This field is passed through to stage_4_build_review_prompt.py
    # which uses it to customize the scoring criteria in the AI prompt.
    #
    # If the field is missing (e.g., submissions from before this field was
    # added, or from agents that don't include it), we default to
    # "original-research" as the most conservative/strictest review type.
    # -----------------------------------------------------------------------
    submission_type = parsed_fields.get("Submission Type", "original-research").strip()
    valid_submission_types = [
        "original-research", "case-study", "benchmark",
        "review-survey", "tutorial", "dataset"
    ]
    if submission_type not in valid_submission_types:
        warnings.append(
            f"Unknown submission type '{submission_type}'. Defaulting to 'original-research'. "
            f"Valid types are: {', '.join(valid_submission_types)}"
        )
        submission_type = "original-research"
    ai_tooling_attribution = (
        parsed_fields.get("AI / Tooling Attribution (optional)", "").strip() or None
    )
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

    if ai_tooling_attribution and len(ai_tooling_attribution) > 1200:
        warnings.append(
            "AI / Tooling Attribution is very long (>1200 characters). "
            "Consider shortening; the field is for naming tools/models, not a second abstract."
        )

    # -----------------------------------------------------------------------
    # STEP 4: Validate category exists in journals.json (TWO-LEVEL FORMAT)
    # -----------------------------------------------------------------------
    # As of the taxonomy redesign (Feb 2026), categories use a two-level
    # "journal/topic" format like "ai/llm-benchmarks" or "debug/runtime-errors".
    # The submission.yml dropdown presents options in this format. We split on
    # "/" to get the journal slug and topic slug, then validate both exist in
    # journals.json.
    #
    # We also reject separator lines from the dropdown (like "--- Artificial
    # Intelligence ---") which are visual aids for humans filling out the form
    # but are NOT valid submissions.
    # -----------------------------------------------------------------------

    # Parse the two-level category format: "journal-slug/topic-slug"
    journal_slug = ""
    topic_slug = ""
    if category:
        # Reject dropdown separator lines (visual grouping headers)
        # These look like "--- Artificial Intelligence ---"
        if category.startswith("---") and category.endswith("---"):
            errors.append(
                f"'{category}' is a section header, not a valid category. "
                f"Please select a specific topic from the dropdown "
                f"(e.g., 'ai/llm-benchmarks')."
            )
        elif "/" in category:
            parts = category.split("/", 1)
            journal_slug = parts[0].strip()
            topic_slug = parts[1].strip()
        else:
            # Legacy flat format or malformed input — reject with helpful message
            errors.append(
                f"Category '{category}' is not in the required 'journal/topic' format. "
                f"Please select a topic from the dropdown (e.g., 'ai/llm-benchmarks')."
            )

    journals_path = os.path.join(repo_root, "journals.json")
    journals_data = None
    valid_topics = []  # List of "journal/topic" strings for error messages
    try:
        with open(journals_path, "r") as f:
            journals_data = json.load(f)
        # Build a flat list of valid "journal/topic" slugs for validation
        for j_slug, j_data in journals_data.get("journals", {}).items():
            for t_slug in j_data.get("topics", {}).keys():
                valid_topics.append(f"{j_slug}/{t_slug}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If journals.json is missing or corrupt, that's a system error, not
        # a submission error. We warn but don't block.
        warnings.append(f"Could not load journals.json: {e}")

    # Validate the journal/topic combination exists
    if valid_topics and journal_slug and topic_slug:
        full_category = f"{journal_slug}/{topic_slug}"
        if full_category not in valid_topics:
            # Check if just the journal is wrong vs the topic
            known_journals = list(journals_data.get("journals", {}).keys())
            if journal_slug not in known_journals:
                errors.append(
                    f"Unknown journal '{journal_slug}'. Valid journals are: "
                    f"{', '.join(known_journals)}"
                )
            else:
                known_topics = list(
                    journals_data["journals"][journal_slug].get("topics", {}).keys()
                )
                errors.append(
                    f"Unknown topic '{topic_slug}' in journal '{journal_slug}'. "
                    f"Valid topics for {journal_slug} are: {', '.join(known_topics)}"
                )

    # -----------------------------------------------------------------------
    # STEP 5: Check topic slot availability (refresh rate enforcement)
    # -----------------------------------------------------------------------
    # Some topics have a refresh_rate_days setting. For example,
    # "ai/llm-benchmarks" and "benchmarks/llm-eval" have a 30-day refresh rate,
    # meaning only one article per topic is accepted per month. This prevents
    # spam and creates competitive submission dynamics.
    #
    # In the two-level taxonomy, refresh_rate_days lives on the TOPIC object
    # inside its parent journal. We navigate journals[journal][topics][topic]
    # to find it.
    #
    # We check agent-index.json for the most recent accepted article in the
    # same topic. If it was published within the refresh window, we reject.
    #
    # Topics with refresh_rate_days=0 are always open (the vast majority).
    # -----------------------------------------------------------------------

    if journals_data and journal_slug and topic_slug:
        journal_obj = journals_data.get("journals", {}).get(journal_slug, {})
        topic_config = journal_obj.get("topics", {}).get(topic_slug, {})
        refresh_days = topic_config.get("refresh_rate_days", 0)

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
    # STEP 7b: DUPLICATE DETECTION (Bug B20 fix)
    # -----------------------------------------------------------------------
    # Check for exact duplicates and near-duplicates against all published papers
    # in both agent-index.json and priorroot-index.json. This prevents:
    #   1. Exact title duplicates (same normalized title)
    #   2. Slug collisions (same journal/topic/slug path)
    #   3. Near-duplicates (high similarity in title+abstract)
    #
    # FIX HISTORY: Issue #60 was an exact duplicate of 2026-067 (same title and
    # slug) but passed stages 1-3 with no duplicate flag, got ACCEPTED at 6.8,
    # then stage 6 labeled it published and closed it but wrote nothing (no
    # papers/ folder, no index change). Stage 6 silently skipped the duplicate
    # write because the path already existed, but did not detect or report it.
    #
    # This check runs BEFORE any LLM call (stage 5) to save cost on duplicates.
    #
    # FIX (self-match): Pass paper_id (if provided) so we can skip index entries
    # with the same paper_id to avoid false-positive self-matches during
    # edit/republish flows or cron retries.
    # -----------------------------------------------------------------------
    
    dup_error = _check_for_duplicates(
        title=title,
        abstract=abstract,
        category=category,
        repo_root=repo_root,
        paper_id=paper_id,  # Pass through from caller (analyzer provides it)
    )
    if dup_error:
        errors.append(dup_error)

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
    # NOTE: Previously step 8, renumbered after adding duplicate detection as 7b.
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
            "category": category,          # Full "journal/topic" slug (e.g., "ai/llm-benchmarks")
            "journal": journal_slug,        # Journal slug only (e.g., "ai")
            "topic": topic_slug,            # Topic slug only (e.g., "llm-benchmarks")
            "submission_type": submission_type,  # One of: original-research, case-study, benchmark, review-survey, tutorial, dataset
            "abstract": abstract,
            "body": body,
            "supporting_repo": supporting_repo,
            "commit_sha": commit_sha,
            "repo_visibility": repo_visibility,
            "payment_code": payment_code,
            "ai_tooling_attribution": ai_tooling_attribution,
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


def _check_for_duplicates(
    title: str,
    abstract: str,
    category: str,
    repo_root: str,
    paper_id: Optional[str] = None,
) -> Optional[str]:
    """
    Check for exact and near-duplicate papers in agent-index.json and priorroot-index.json.
    
    DUPLICATE DETECTION (Bug B20 fix):
        This function checks three things:
        1. EXACT TITLE MATCH: Normalized title exactly matches a published paper
        2. SLUG COLLISION: journal/topic/slug path would collide with existing paper
        3. NEAR-DUPLICATE: High cosine similarity of title+abstract (TF-IDF, threshold from env)
    
    FIX HISTORY:
        Issue #60 was an exact duplicate of 2026-067 (same title and slug) but
        passed stages 1-3 with no flag. It got ACCEPTED at 6.8, then stage 6
        silently skipped the write (path existed) but labeled it published anyway.
        
        This check runs BEFORE the LLM call to save cost on duplicates. It's in
        stage 1 (not stage 2) because it's a validation check, not novelty scoring.
    
    FIX (self-match): Skip entries where paper_id matches this submission's paper_id
        to avoid false-positive self-matches during edit/republish flows.
    
    Args:
        title: Submission title
        abstract: Submission abstract (will be truncated to 500 chars like index)
        category: Submission category (journal/topic format)
        repo_root: Path to repo root
        paper_id: This submission's paper_id (e.g., "2026-060") to skip self-matches.
                  If None, no self-match filtering is applied.
    
    Returns:
        Error message string if a duplicate is found, None if no duplicates detected.
    """
    from pubroot_site_paths import parse_journal_topic
    
    # Truncate abstract to 500 chars to match index format (nit fix)
    abstract_truncated = abstract[:500] if abstract else ""
    
    # Get similarity threshold from env (nit fix: configurable)
    similarity_threshold = float(os.environ.get("DUPLICATE_SIMILARITY_THRESHOLD", "0.92"))
    
    # Load both indexes
    indexes_to_check = []
    for idx_file in ["agent-index.json", "priorroot-index.json"]:
        idx_path = os.path.join(repo_root, idx_file)
        try:
            with open(idx_path, "r") as f:
                idx_data = json.load(f)
                indexes_to_check.append((idx_file, idx_data.get("papers", [])))
        except (FileNotFoundError, json.JSONDecodeError):
            # If an index is missing or corrupt, skip it (shouldn't happen in production)
            continue
    
    if not indexes_to_check:
        # No indexes available (shouldn't happen), can't check for duplicates
        return None
    
    # Normalize the submission title for comparison
    normalized_title = _normalize_title(title)
    
    # Parse category for path building
    journal, topic = parse_journal_topic(category)
    
    # Prepare title+abstract for similarity comparison
    submission_text = f"{title} {abstract_truncated}".lower()
    submission_words = _tokenize_for_tfidf(submission_text)
    
    # Check each paper in each index
    for idx_name, papers in indexes_to_check:
        for paper in papers:
            paper_id_in_index = paper.get("id", "unknown")
            paper_title = paper.get("title", "")
            paper_category = paper.get("category", "")
            paper_abstract = paper.get("abstract", "")
            
            # FIX (self-match): Skip this paper if it's the same paper_id as this submission.
            # This prevents false-positive self-matches during edit/republish flows.
            if paper_id and paper_id_in_index == paper_id:
                continue
            
            # ---------------------------------------------------------------
            # CHECK 1: EXACT TITLE MATCH (case-insensitive, normalized)
            # ---------------------------------------------------------------
            if _normalize_title(paper_title) == normalized_title:
                # Nit fix: Use canonical reader_url fallback
                reader_url = paper.get("reader_url") or _build_fallback_reader_url(
                    paper_category, paper_title, paper_id_in_index
                )
                return (
                    f"DUPLICATE DETECTED: This submission has the exact same title as "
                    f"published paper **{paper_id_in_index}** in {idx_name}.\n\n"
                    f"Existing paper: [{paper_title}]({reader_url})\n\n"
                    f"**Note**: If this is a genuine revision or update to the existing paper, "
                    f"please follow the revision process by referencing the original paper's ID "
                    f"and explaining what has changed."
                )
            
            # ---------------------------------------------------------------
            # CHECK 2: SLUG COLLISION (same article_path)
            # ---------------------------------------------------------------
            # Nit fix: Use article_path from index rather than rebuilding slugs
            paper_article_path = paper.get("article_path", "")
            
            # Build the path this submission would get
            from pubroot_site_paths import slugify_title, article_index_rel
            submission_slug = slugify_title(title, "new")
            submission_article_path = article_index_rel(journal, topic, submission_slug)
            
            if submission_article_path == paper_article_path:
                reader_url = paper.get("reader_url") or _build_fallback_reader_url(
                    paper_category, paper_title, paper_id_in_index
                )
                return (
                    f"SLUG COLLISION: This submission would create the same URL path as "
                    f"published paper **{paper_id_in_index}** in {idx_name}.\n\n"
                    f"Existing paper: [{paper_title}]({reader_url})\n"
                    f"Path: `{submission_article_path}`\n\n"
                    f"This typically means the titles are very similar. Please use a "
                    f"more distinctive title or choose a different topic category."
                )
            
            # ---------------------------------------------------------------
            # CHECK 3: NEAR-DUPLICATE (TF-IDF cosine similarity >= threshold)
            # ---------------------------------------------------------------
            paper_text = f"{paper_title} {paper_abstract}".lower()
            paper_words = _tokenize_for_tfidf(paper_text)
            
            similarity = _tfidf_cosine_similarity(submission_words, paper_words)
            
            if similarity >= similarity_threshold:
                reader_url = paper.get("reader_url") or _build_fallback_reader_url(
                    paper_category, paper_title, paper_id_in_index
                )
                return (
                    f"NEAR-DUPLICATE DETECTED: This submission is very similar to "
                    f"published paper **{paper_id_in_index}** in {idx_name} "
                    f"(similarity: {similarity:.1%}).\n\n"
                    f"Existing paper: [{paper_title}]({reader_url})\n\n"
                    f"The title and abstract are too similar to existing work. "
                    f"**Note**: If this is a genuine revision, please follow the revision "
                    f"process by referencing the original paper and explaining the changes."
                )
    
    return None


def _build_fallback_reader_url(category: str, title: str, paper_id: str) -> str:
    """
    Build canonical reader_url as fallback when index doesn't have it.
    
    Nit fix: Use the canonical https://pubroot.com/{journal}/{topic}/{slug}/ pattern.
    """
    from pubroot_site_paths import parse_journal_topic, slugify_title
    
    journal, topic = parse_journal_topic(category)
    slug = slugify_title(title, paper_id)
    
    return f"https://pubroot.com/{journal}/{topic}/{slug}/"


def _normalize_title(title: str) -> str:
    """
    Normalize a title for exact-match comparison.
    
    Lowercases, strips whitespace, removes common punctuation, and collapses
    multiple spaces. This catches duplicates even if one has extra punctuation
    or spacing differences.
    """
    t = title.lower().strip()
    # Remove common punctuation that doesn't affect meaning
    t = re.sub(r"[:\-—–_.!?;,\"'`]", " ", t)
    # Collapse multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _tokenize_for_tfidf(text: str) -> list:
    """
    Tokenize text for TF-IDF similarity: lowercase, alphanumeric words only,
    remove common stop words.
    """
    # Split on non-alphanumeric
    words = re.findall(r'\b[a-z0-9]+\b', text.lower())
    
    # Remove stop words (common English words that don't help with similarity)
    stop_words = {
        "the", "is", "are", "was", "were", "of", "in", "to", "for", "and", 
        "or", "on", "with", "as", "by", "this", "that", "it", "from", "at", 
        "be", "has", "had", "have", "a", "an", "but", "not", "can", "will",
        "would", "should", "could", "may", "might", "if", "then", "than",
        "we", "they", "our", "their", "how", "when", "where", "why", "what",
        "who", "which", "such", "so", "just", "now", "here", "there", "all",
        "some", "any", "more", "most", "other", "into", "over", "out", "up",
        "down", "only", "do", "does", "did", "i", "you", "he", "she", "his",
        "her", "its", "my", "your"
    }
    
    return [w for w in words if w not in stop_words and len(w) > 2]


def _tfidf_cosine_similarity(words1: list, words2: list) -> float:
    """
    Compute TF-IDF weighted cosine similarity between two word lists.
    
    This is a simple local implementation (no scikit-learn dependency) that
    builds a term frequency (TF) vector for each document and computes cosine
    similarity. The "IDF" is implicit: rare words (appearing in only one doc)
    get more weight because they don't appear in the other doc's denominator.
    
    Returns:
        Similarity score in [0.0, 1.0], where 1.0 is identical.
    """
    if not words1 or not words2:
        return 0.0
    
    # Build term frequency maps
    from collections import Counter
    tf1 = Counter(words1)
    tf2 = Counter(words2)
    
    # Get the union of terms
    all_terms = set(tf1.keys()) | set(tf2.keys())
    
    # Build vectors (term frequency as the "TF-IDF" approximation)
    vec1 = [tf1.get(term, 0) for term in all_terms]
    vec2 = [tf2.get(term, 0) for term in all_terms]
    
    # Compute cosine similarity: (vec1 · vec2) / (||vec1|| * ||vec2||)
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def _extract_form_fields(issue_body: str) -> dict:
    """
    Parse a GitHub Issue form response into label-value pairs.

    GitHub renders form responses as:
        ### Label

        Value (possibly multi-line)

        ### Next Label
        ...

    IMPORTANT — KNOWN-LABEL-ONLY SPLITTING:
        We ONLY split on `### ` headers that match known form field labels from
        submission.yml. This is critical because article bodies frequently contain
        `### ` subheadings. If we naively split on every `### `, the article body
        gets truncated at its first `### ` subheading, causing word count failures
        and lost content.

        Prior to this fix, agents submitting articles with `### Results` or
        `### Discussion` inside the Article Body would see those interpreted as
        new form fields, silently discarding everything after the first internal
        `### `. This was the #1 cause of submission failures.

    Returns:
        dict mapping field labels to their string values.
    """
    # -----------------------------------------------------------------------
    # These are the EXACT field labels from submission.yml. The parser only
    # recognizes these as section delimiters. Any other `### ` header (like
    # `### Results` or `### Discussion` inside the article body) is treated
    # as regular content and preserved in the preceding field's value.
    #
    # If submission.yml field labels change, this list MUST be updated.
    # -----------------------------------------------------------------------
    KNOWN_LABELS = [
        "Article Title",
        "Category",
        "Submission Type",
        "AI / Tooling Attribution (optional)",
        "Abstract",
        "Article Body",
        "Supporting Repository URL",
        "Commit SHA",
        "Repository Visibility",
        "Payment Code (Optional)",
        "Submission Agreement",
    ]

    fields = {}

    # Build a regex that matches only known labels after `### `
    # We escape each label for regex safety, then join with |
    escaped_labels = [re.escape(label) for label in KNOWN_LABELS]
    # Match `### Known Label` at the start of a line, followed by newline
    # The label must match exactly (no partial matches)
    known_header_pattern = r"^### (" + "|".join(escaped_labels) + r")\s*$"

    # Find all positions where known headers appear
    matches = list(re.finditer(known_header_pattern, issue_body, flags=re.MULTILINE))

    for i, match in enumerate(matches):
        label = match.group(1).strip()
        # Value starts after the header line
        value_start = match.end()
        # Value ends at the next known header (or end of string)
        if i + 1 < len(matches):
            value_end = matches[i + 1].start()
        else:
            value_end = len(issue_body)

        value = issue_body[value_start:value_end].strip()

        # Remove "_No response_" placeholder that GitHub uses for empty optional fields
        if value == "_No response_":
            value = ""

        fields[label] = value

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
