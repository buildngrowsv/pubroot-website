"""
Tests for Verify Payment Code — Pubroot Priority Review Monetization

HISTORY:
    Created 2026-03-24 by Builder 4 (swarm agent) as part of the Phase 1
    monetization implementation (BridgeMind task 5302dc1f). These tests
    validate the payment code verification logic that checks submitted
    codes against the Stripe payments ledger.

APPROACH:
    - We create temporary directories with sample _verified_payments.json
      files to simulate different payment states (valid, used, missing, etc.)
    - Each test targets a specific verification path documented in the
      verify_payment_code.py module docstring.
    - No external API calls — all tests are pure Python with temp files.

RUNNING:
    pytest _review_agent/test_verify_payment_code.py -v
"""

import json
import os
import tempfile
import pytest

from verify_payment_code import verify_payment_code


# ---------------------------------------------------------------------------
# FIXTURES — reusable test data
# ---------------------------------------------------------------------------

SAMPLE_LEDGER = {
    "schema_version": "1.0",
    "description": "Test payment ledger",
    "payments": {
        "PAID-abc12345": {
            "stripe_payment_intent": "pi_3abc12345defghijklmnopqrstuvwxyz",
            "product": "priority_review",
            "amount_cents": 500,
            "currency": "usd",
            "created_at": "2026-03-24T12:00:00Z",
            "used": False,
            "used_on_issue": None,
        },
        "PAID-usedcode": {
            "stripe_payment_intent": "pi_3usedcodedefghijklmnopqrstuvwxyz",
            "product": "priority_review",
            "amount_cents": 500,
            "currency": "usd",
            "created_at": "2026-03-23T10:00:00Z",
            "used": True,
            "used_on_issue": 42,
        },
        "PAID-deposit1": {
            "stripe_payment_intent": "pi_3deposit1defghijklmnopqrstuvwxyz",
            "product": "submission_deposit",
            "amount_cents": 100,
            "currency": "usd",
            "created_at": "2026-03-24T08:00:00Z",
            "used": False,
            "used_on_issue": None,
        },
    },
}


@pytest.fixture
def repo_with_ledger(tmp_path):
    """
    Create a temporary repo root with a populated _verified_payments.json.

    This simulates a repo where the Stripe webhook has already written
    some verified payment records. Tests can then look up codes against
    this ledger.
    """
    payments_dir = tmp_path / "payments"
    payments_dir.mkdir()
    ledger_path = payments_dir / "_verified_payments.json"
    ledger_path.write_text(json.dumps(SAMPLE_LEDGER))
    return str(tmp_path)


@pytest.fixture
def repo_without_ledger(tmp_path):
    """
    Create a temporary repo root WITHOUT a payments ledger file.

    This simulates a fresh repo where no payments have ever been processed
    (before the Stripe webhook handler is deployed).
    """
    return str(tmp_path)


@pytest.fixture
def repo_with_empty_ledger(tmp_path):
    """
    Create a temporary repo root with an empty payments ledger.

    This simulates a repo where the payments directory exists but no
    payments have been recorded yet.
    """
    payments_dir = tmp_path / "payments"
    payments_dir.mkdir()
    ledger_path = payments_dir / "_verified_payments.json"
    ledger_path.write_text(json.dumps({
        "schema_version": "1.0",
        "payments": {},
    }))
    return str(tmp_path)


@pytest.fixture
def repo_with_corrupt_ledger(tmp_path):
    """
    Create a temporary repo root with a corrupt (non-JSON) ledger file.

    This simulates a corrupted payments file — the verification should
    handle this gracefully without crashing.
    """
    payments_dir = tmp_path / "payments"
    payments_dir.mkdir()
    ledger_path = payments_dir / "_verified_payments.json"
    ledger_path.write_text("{this is not valid json!!!")
    return str(tmp_path)


# ---------------------------------------------------------------------------
# HAPPY PATH TESTS — valid payment codes
# ---------------------------------------------------------------------------


class TestValidPaymentCodes:
    """Test that valid, unused payment codes are verified correctly."""

    def test_valid_priority_review_code(self, repo_with_ledger):
        """A valid, unused priority_review code should return valid=True."""
        result = verify_payment_code("PAID-abc12345", repo_with_ledger)

        assert result["valid"] is True
        assert result["product"] == "priority_review"
        assert result["amount_cents"] == 500
        assert result["already_used"] is False
        assert result["error"] is None

    def test_valid_deposit_code(self, repo_with_ledger):
        """A valid submission_deposit code should also return valid=True."""
        result = verify_payment_code("PAID-deposit1", repo_with_ledger)

        assert result["valid"] is True
        assert result["product"] == "submission_deposit"
        assert result["amount_cents"] == 100
        assert result["already_used"] is False


# ---------------------------------------------------------------------------
# NO PAYMENT PROVIDED TESTS — empty or None payment codes
# ---------------------------------------------------------------------------


class TestNoPaymentProvided:
    """Test the common case where no payment code is given (free tier)."""

    def test_none_payment_code(self, repo_with_ledger):
        """None payment code should return valid=False with no error."""
        result = verify_payment_code(None, repo_with_ledger)

        assert result["valid"] is False
        assert result["error"] is None  # No error — just no payment
        assert result["product"] is None

    def test_empty_string_payment_code(self, repo_with_ledger):
        """Empty string payment code should return valid=False with no error."""
        result = verify_payment_code("", repo_with_ledger)

        assert result["valid"] is False
        assert result["error"] is None

    def test_whitespace_only_payment_code(self, repo_with_ledger):
        """Whitespace-only payment code should be treated as no payment."""
        result = verify_payment_code("   ", repo_with_ledger)

        assert result["valid"] is False
        assert result["error"] is None


# ---------------------------------------------------------------------------
# INVALID FORMAT TESTS — codes that don't match the expected pattern
# ---------------------------------------------------------------------------


class TestInvalidFormat:
    """Test that malformed payment codes are rejected before ledger lookup."""

    def test_missing_paid_prefix(self, repo_with_ledger):
        """A code without the 'PAID-' prefix should fail format validation."""
        result = verify_payment_code("abc12345", repo_with_ledger)

        assert result["valid"] is False
        assert "format" in result["error"].lower()

    def test_wrong_prefix(self, repo_with_ledger):
        """A code with a wrong prefix should fail format validation."""
        result = verify_payment_code("PAY-abc12345", repo_with_ledger)

        assert result["valid"] is False
        assert "format" in result["error"].lower()

    def test_too_short_suffix(self, repo_with_ledger):
        """A code with fewer than 6 characters after PAID- should fail."""
        result = verify_payment_code("PAID-abc", repo_with_ledger)

        assert result["valid"] is False
        assert "format" in result["error"].lower()

    def test_too_long_suffix(self, repo_with_ledger):
        """A code with more than 12 characters after PAID- should fail."""
        result = verify_payment_code("PAID-abcdefghijklmn", repo_with_ledger)

        assert result["valid"] is False
        assert "format" in result["error"].lower()

    def test_special_characters_in_suffix(self, repo_with_ledger):
        """A code with special characters should fail format validation."""
        result = verify_payment_code("PAID-abc!@#$%", repo_with_ledger)

        assert result["valid"] is False
        assert "format" in result["error"].lower()

    def test_spaces_in_code(self, repo_with_ledger):
        """A code with spaces should fail format validation."""
        result = verify_payment_code("PAID- abc1234", repo_with_ledger)

        assert result["valid"] is False
        assert "format" in result["error"].lower()


# ---------------------------------------------------------------------------
# ALREADY USED TESTS — codes that have been consumed
# ---------------------------------------------------------------------------


class TestAlreadyUsedCodes:
    """Test that previously consumed codes are rejected with clear messaging."""

    def test_used_code_returns_already_used(self, repo_with_ledger):
        """A code marked as used in the ledger should return already_used=True."""
        result = verify_payment_code("PAID-usedcode", repo_with_ledger)

        assert result["valid"] is False
        assert result["already_used"] is True
        assert result["product"] == "priority_review"
        assert result["amount_cents"] == 500
        assert "already been used" in result["error"]
        assert "42" in result["error"]  # Should mention the issue it was used on


# ---------------------------------------------------------------------------
# CODE NOT FOUND TESTS — valid format but not in the ledger
# ---------------------------------------------------------------------------


class TestCodeNotFound:
    """Test that codes not present in the ledger are rejected."""

    def test_unknown_code_with_populated_ledger(self, repo_with_ledger):
        """A correctly formatted code not in the ledger should be rejected."""
        result = verify_payment_code("PAID-unknown1", repo_with_ledger)

        assert result["valid"] is False
        assert result["already_used"] is False
        assert "not found" in result["error"].lower()

    def test_unknown_code_with_empty_ledger(self, repo_with_empty_ledger):
        """A code against an empty ledger should be rejected."""
        result = verify_payment_code("PAID-abc12345", repo_with_empty_ledger)

        assert result["valid"] is False
        assert "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# MISSING/CORRUPT LEDGER TESTS — filesystem edge cases
# ---------------------------------------------------------------------------


class TestLedgerEdgeCases:
    """Test behavior when the payments ledger is missing or corrupt."""

    def test_missing_ledger_file(self, repo_without_ledger):
        """When no ledger file exists, all codes should be rejected gracefully."""
        result = verify_payment_code("PAID-abc12345", repo_without_ledger)

        assert result["valid"] is False
        assert result["error"] is not None
        assert "not yet configured" in result["error"].lower() or "ledger" in result["error"].lower()

    def test_corrupt_ledger_file(self, repo_with_corrupt_ledger):
        """A corrupt (non-JSON) ledger should be handled without crashing."""
        result = verify_payment_code("PAID-abc12345", repo_with_corrupt_ledger)

        assert result["valid"] is False
        assert result["error"] is not None
        assert "could not read" in result["error"].lower()


# ---------------------------------------------------------------------------
# WHITESPACE HANDLING TESTS
# ---------------------------------------------------------------------------


class TestWhitespaceHandling:
    """Test that codes with surrounding whitespace are handled correctly."""

    def test_leading_whitespace_stripped(self, repo_with_ledger):
        """Leading whitespace in a valid code should be stripped before lookup."""
        result = verify_payment_code("  PAID-abc12345", repo_with_ledger)

        assert result["valid"] is True

    def test_trailing_whitespace_stripped(self, repo_with_ledger):
        """Trailing whitespace in a valid code should be stripped before lookup."""
        result = verify_payment_code("PAID-abc12345  ", repo_with_ledger)

        assert result["valid"] is True

    def test_surrounding_whitespace_stripped(self, repo_with_ledger):
        """Both leading and trailing whitespace should be stripped."""
        result = verify_payment_code("  PAID-abc12345  ", repo_with_ledger)

        assert result["valid"] is True
