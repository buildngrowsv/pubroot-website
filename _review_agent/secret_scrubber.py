"""
Secret Scrubber — Pubroot Security Hardening

PURPOSE:
    Sanitize text content to prevent accidental exposure of secrets in public
    issue comments, review.json files, and other published artifacts. This is
    a defense-in-depth measure against the symlink exfiltration vulnerability
    (B1) and any future bugs that might expose sensitive data.

APPROACH:
    - Pattern-based detection of common secret formats (API keys, tokens, AWS keys)
    - Environment variable value scrubbing (redact any env var values found in text)
    - Configurable redaction string for clear audit trails
    - Conservative: if something looks like a secret, redact it

CALLED BY:
    stage_6_post_review_and_decide.py — before posting issue comments or committing files
    Any other module that generates user-facing or public content

SECURITY CONTEXT:
    This was added as part of the fix for B1 (Critical): a malicious submitter could
    create a repo with symlinks to /proc/self/environ, .git/config, or other files
    containing secrets (GEMINI_API_KEY, GITHUB_TOKEN). Even with symlink blocking in
    stage 3, this scrubber provides an additional safety layer before any content
    reaches the LLM prompt, issue comments, or the public repository.

COST:
    $0 — pure regex and string operations, no API calls.
"""

import re
import os
from typing import Optional, Set


# Common secret patterns that should never appear in public outputs.
# These patterns match common formats for API keys, tokens, and credentials.
# We prefer false positives (over-redacting) to false negatives (leaking secrets).
SECRET_PATTERNS = [
    # GitHub tokens: ghp_, gho_, ghs_, ghr_ prefixes (Personal, OAuth, Server, Refresh)
    # These are 32+ chars of alphanumeric and underscores after the prefix
    # Real tokens are alphanumeric only, but we include underscore to catch test tokens
    re.compile(r'\bgh[pors]_[A-Za-z0-9_]{32,}\b'),
    
    # Google/Gemini API keys: typically start with AIza, followed by 35+ chars of alphanumeric, underscore, hyphen
    # Example: AIzaSyABCDEF1234567890_abcdefghijk-XYZ
    re.compile(r'\bAIza[A-Za-z0-9_-]{31,}\b'),
    
    # AWS Access Key IDs (AKIA...) and Secret Access Keys
    re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    
    # Bearer tokens in Authorization headers
    re.compile(r'\bBearer\s+[A-Za-z0-9._-]{20,}\b', re.IGNORECASE),
    
    # Basic auth credentials (base64 encoded username:password)
    re.compile(r'\bBasic\s+[A-Za-z0-9+/=]{20,}\b', re.IGNORECASE),
    
    # Private keys (PEM format markers)
    re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----'),
    
    # JWT tokens (three base64 segments separated by dots)
    re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'),
    
    # Semantic Scholar API keys (if they have a known format — this is a placeholder)
    re.compile(r'\bs2_[A-Za-z0-9]{32,}\b', re.IGNORECASE),
    
    # Generic long alphanumeric+special strings that look like secrets
    # This catches many API keys but may have false positives, so we put it last
    # and make it more conservative (40+ chars, not 32+)
    re.compile(r'\b[A-Za-z0-9_/+=]{50,}\b'),
]


def scrub_secrets(
    text: str,
    redaction_string: str = "[REDACTED_SECRET]",
    additional_patterns: Optional[list] = None,
) -> str:
    """
    Scrub known secret patterns from text.
    
    This function applies pattern-based redaction to prevent secrets from appearing
    in public outputs. It's intentionally conservative: better to redact too much
    than to miss a real secret.
    
    Args:
        text: The text to scrub (e.g., LLM output, review comment, file content)
        redaction_string: What to replace secrets with. Defaults to [REDACTED_SECRET].
                         Using a clear marker makes it obvious in audits that redaction occurred.
        additional_patterns: Optional list of extra regex patterns to check (compiled regex objects)
    
    Returns:
        The scrubbed text with all detected secrets replaced by redaction_string.
    
    Example:
        >>> scrub_secrets("Here is my token: ghp_1234567890abcdefghijklmnopqrstuvwxyz")
        "Here is my token: [REDACTED_SECRET]"
    """
    if not text:
        return text
    
    scrubbed = text
    
    # Apply all built-in secret patterns
    for pattern in SECRET_PATTERNS:
        scrubbed = pattern.sub(redaction_string, scrubbed)
    
    # Apply any additional patterns provided by the caller
    if additional_patterns:
        for pattern in additional_patterns:
            scrubbed = pattern.sub(redaction_string, scrubbed)
    
    return scrubbed


def scrub_environment_variables(
    text: str,
    redaction_string: str = "[REDACTED_SECRET]",
    env_var_names: Optional[Set[str]] = None,
) -> str:
    """
    Scrub the VALUES of environment variables from text.
    
    This function looks for the actual values of environment variables (not their names)
    in the text and redacts them. Useful for catching secrets that were read from
    /proc/self/environ or otherwise leaked into text.
    
    IMPORTANT: This only scrubs the VALUES. The variable names (like "GEMINI_API_KEY")
    are public knowledge and safe to appear in logs/comments. Only the actual key itself
    needs to be redacted.
    
    Args:
        text: The text to scrub
        redaction_string: What to replace secret values with
        env_var_names: Optional set of env var names to check. If None, checks all
                      environment variables that look like they might contain secrets
                      (anything with KEY, TOKEN, SECRET, PASSWORD, CREDENTIAL in the name).
    
    Returns:
        The scrubbed text with environment variable values redacted.
    
    Example:
        # Assuming GEMINI_API_KEY="AIzaSyABC123..."
        >>> scrub_environment_variables("The key is: AIzaSyABC123...")
        "The key is: [REDACTED_SECRET]"
    """
    if not text:
        return text
    
    scrubbed = text
    
    # Determine which env vars to check
    if env_var_names is None:
        # Auto-detect: check env vars that look like they hold secrets
        # This is a security-conscious default: we check anything that might be sensitive
        sensitive_keywords = {"KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH"}
        env_var_names = {
            name for name in os.environ.keys()
            if any(keyword in name.upper() for keyword in sensitive_keywords)
        }
    
    # For each sensitive env var, if it has a non-empty value, redact that value from text
    for var_name in env_var_names:
        value = os.environ.get(var_name)
        if value and len(value) > 8:  # Only redact values that are long enough to be real secrets
            # Escape special regex characters in the value to avoid regex injection
            escaped_value = re.escape(value)
            # Replace all occurrences of this secret value
            scrubbed = re.sub(escaped_value, redaction_string, scrubbed)
    
    return scrubbed


def scrub_all(
    text: str,
    redaction_string: str = "[REDACTED_SECRET]",
    additional_patterns: Optional[list] = None,
    env_var_names: Optional[Set[str]] = None,
) -> str:
    """
    Apply all scrubbing methods: pattern-based and environment variable based.
    
    This is the recommended function to use for maximum protection. It combines
    both pattern-based secret detection and environment variable value scrubbing.
    
    Args:
        text: The text to scrub
        redaction_string: What to replace secrets with
        additional_patterns: Optional extra regex patterns to check
        env_var_names: Optional set of env var names to check (default: auto-detect)
    
    Returns:
        Fully scrubbed text with all detected secrets redacted.
    
    Example:
        >>> scrub_all("Token: ghp_abc123... Key: AIzaSy...")
        "Token: [REDACTED_SECRET] Key: [REDACTED_SECRET]"
    """
    # First pass: pattern-based scrubbing
    scrubbed = scrub_secrets(text, redaction_string, additional_patterns)
    
    # Second pass: environment variable value scrubbing
    scrubbed = scrub_environment_variables(scrubbed, redaction_string, env_var_names)
    
    return scrubbed
