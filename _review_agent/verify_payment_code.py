"""
Verify Payment Code — Pubroot Priority Review Monetization

PURPOSE:
    Validate a payment code extracted from a submission's GitHub Issue body
    against the verified payments ledger (payments/_verified_payments.json).

    This is Phase 1 of Pubroot's monetization: a $5 "Priority Review" option
    that lets submitters pay to accelerate their review queue position. The
    flow works like this:

    1. Submitter clicks a Stripe Payment Link (hosted URL, no backend needed)
    2. After payment, Stripe redirects to pubroot.com/priority-review-confirmation/
       which shows the payment code (PAID-{last_8_of_payment_intent_id})
    3. Submitter pastes the code into the "Payment Code (Optional)" field of
       their GitHub Issue submission
    4. This module verifies the code is real, unused, and for the right product
    5. If valid, the priority_score_calculator.py boosts their queue position

    The _verified_payments.json file is populated by a Stripe webhook handler
    (Cloudflare Worker) that listens for checkout.session.completed events.
    This decoupled architecture means the static Hugo site never needs a
    backend — the webhook writes to the repo, and the review pipeline reads.

CALLED BY:
    review_pipeline_main.py — after Stage 1 (parse & filter) succeeds,
    before priority calculation. The payment verification result is passed
    to the priority calculator to determine the queue boost.

DEPENDS ON:
    - payments/_verified_payments.json (the payment ledger)
    - The payment code format: "PAID-{8_alphanumeric_chars}"

DESIGN DECISIONS:
    - We do NOT call Stripe API directly from the pipeline. That would require
      Stripe API keys in GitHub Actions secrets and add latency. Instead, we
      trust the webhook-populated JSON file (which is committed to the repo).
    - Payment codes are one-time-use: once a code is consumed by a submission,
      it cannot be reused. This prevents someone from paying once and submitting
      multiple priority reviews.
    - The "already_used" check happens here, but the actual marking of a code
      as used happens in review_pipeline_main.py AFTER the priority label is
      assigned (so we don't consume the code if the submission fails validation).
    - We validate the code format with a regex before looking it up in the
      ledger, as a cheap first filter against garbage input.
"""

import json
import os
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Payment code format: "PAID-" followed by 6-12 alphanumeric characters.
# The suffix is derived from the last N characters of the Stripe Payment
# Intent ID (pi_...), which is always alphanumeric. We allow 6-12 chars
# to accommodate different truncation lengths if the webhook logic changes.
# ---------------------------------------------------------------------------
PAYMENT_CODE_PATTERN = re.compile(r"^PAID-[A-Za-z0-9]{6,12}$")


def verify_payment_code(
    payment_code: Optional[str],
    repo_root: str
) -> dict:
    """
    Check if a payment code from the submission Issue body is valid.

    This is the ONLY public function in this module, following the
    one-function-per-file pattern used throughout the Pubroot review pipeline.

    Args:
        payment_code: The payment code string extracted from the GitHub Issue
                      body by stage_1_parse_and_filter.py. May be None or empty
                      if the submitter didn't provide one (free tier submission).
        repo_root:    Absolute path to the repository root. Used to locate
                      the payments/_verified_payments.json ledger file.

    Returns:
        dict with keys:
            - 'valid' (bool): Whether the payment code matches a real,
                               unused payment in the ledger
            - 'product' (str or None): The Stripe product slug if valid
                                        (e.g., "priority_review")
            - 'amount_cents' (int): Payment amount in cents (e.g., 500 for $5)
            - 'already_used' (bool): True if this code was already consumed
                                      by a previous submission
            - 'error' (str or None): Human-readable error message if invalid
    """

    # -----------------------------------------------------------------------
    # EARLY EXIT: No payment code provided
    # -----------------------------------------------------------------------
    # Most submissions will be free-tier (no payment code). We return a
    # clean "not paid" result without touching the filesystem at all.
    # This is the hot path — optimized for the common case.
    # -----------------------------------------------------------------------

    if not payment_code or not payment_code.strip():
        return {
            "valid": False,
            "product": None,
            "amount_cents": 0,
            "already_used": False,
            "error": None,  # No error — just no payment provided
        }

    payment_code = payment_code.strip()

    # -----------------------------------------------------------------------
    # FORMAT VALIDATION: Check the code matches the expected pattern
    # -----------------------------------------------------------------------
    # This is a cheap regex check before we hit the filesystem. It catches
    # typos, garbage input, and injection attempts. The pattern is:
    # "PAID-" + 6-12 alphanumeric characters (from Stripe Payment Intent ID).
    # -----------------------------------------------------------------------

    if not PAYMENT_CODE_PATTERN.match(payment_code):
        return {
            "valid": False,
            "product": None,
            "amount_cents": 0,
            "already_used": False,
            "error": (
                f"Payment code '{payment_code}' does not match the expected format. "
                f"Valid codes look like 'PAID-abc12345' (from the Stripe confirmation page)."
            ),
        }

    # -----------------------------------------------------------------------
    # LEDGER LOOKUP: Read the verified payments JSON file
    # -----------------------------------------------------------------------
    # The ledger is populated by the Stripe webhook handler (Cloudflare Worker)
    # and committed to the repo. If the file doesn't exist yet (before any
    # payments have been made), we treat all codes as invalid.
    # -----------------------------------------------------------------------

    payments_file_path = os.path.join(repo_root, "payments", "_verified_payments.json")

    if not os.path.exists(payments_file_path):
        return {
            "valid": False,
            "product": None,
            "amount_cents": 0,
            "already_used": False,
            "error": (
                "Payment verification is not yet configured (no payments ledger found). "
                "If you just paid, your payment may not have been processed yet. "
                "Please wait a few minutes and resubmit, or submit without a payment code."
            ),
        }

    try:
        with open(payments_file_path, "r") as f:
            ledger = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # -----------------------------------------------------------------------
        # If the ledger file is corrupt or unreadable, we don't block the
        # submission — we just treat it as unverified. The priority calculator
        # will give it a normal (non-boosted) score. Better to let a paid
        # submission through at normal priority than to reject it entirely
        # because of a broken JSON file.
        # -----------------------------------------------------------------------
        return {
            "valid": False,
            "product": None,
            "amount_cents": 0,
            "already_used": False,
            "error": f"Could not read payments ledger: {e}",
        }

    # -----------------------------------------------------------------------
    # PAYMENT LOOKUP: Check if the code exists in the ledger
    # -----------------------------------------------------------------------

    payments = ledger.get("payments", {})
    payment_entry = payments.get(payment_code)

    if payment_entry is None:
        return {
            "valid": False,
            "product": None,
            "amount_cents": 0,
            "already_used": False,
            "error": (
                f"Payment code '{payment_code}' was not found in the verified payments ledger. "
                f"This could mean: (1) the code is incorrect, (2) the Stripe webhook hasn't "
                f"processed the payment yet, or (3) the code was already consumed. "
                f"If you just paid, please wait a few minutes and try again."
            ),
        }

    # -----------------------------------------------------------------------
    # USAGE CHECK: Has this code already been consumed by another submission?
    # -----------------------------------------------------------------------
    # Payment codes are single-use. Once a code is tied to a GitHub Issue
    # (via the "used_on_issue" field), it cannot be reused. This prevents
    # a single $5 payment from being applied to multiple submissions.
    # -----------------------------------------------------------------------

    already_used = payment_entry.get("used", False)

    if already_used:
        used_on = payment_entry.get("used_on_issue", "unknown")
        return {
            "valid": False,
            "product": payment_entry.get("product"),
            "amount_cents": payment_entry.get("amount_cents", 0),
            "already_used": True,
            "error": (
                f"Payment code '{payment_code}' has already been used on issue #{used_on}. "
                f"Each payment code can only be used once. Please purchase a new priority "
                f"review if you want to accelerate another submission."
            ),
        }

    # -----------------------------------------------------------------------
    # VALID PAYMENT: Code exists, is unused, and matches a real Stripe payment
    # -----------------------------------------------------------------------

    return {
        "valid": True,
        "product": payment_entry.get("product"),
        "amount_cents": payment_entry.get("amount_cents", 0),
        "already_used": False,
        "error": None,
    }
