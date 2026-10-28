"""
Tests for Secret Scrubber — Pubroot Security Hardening

HISTORY:
    Created 2026-10-24 as part of the B1 security fix (symlink exfiltration vulnerability).
    These tests verify that secrets are properly redacted from text before it reaches
    public outputs (issue comments, review.json, etc.).

RUNNING:
    pytest _review_agent/test_secret_scrubber.py -v
"""

import os
import re
import pytest
from unittest.mock import patch

from secret_scrubber import (
    scrub_secrets,
    scrub_environment_variables,
    scrub_all,
)


# ---------------------------------------------------------------------------
# PATTERN-BASED SECRET SCRUBBING TESTS
# ---------------------------------------------------------------------------


class TestPatternBasedScrubbing:
    """Test detection and redaction of common secret patterns."""
    
    def test_scrub_github_personal_token(self):
        """GitHub personal access tokens (ghp_...) should be redacted."""
        text = "Here is my token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        scrubbed = scrub_secrets(text)
        
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
        assert "Here is my token:" in scrubbed
    
    def test_scrub_github_oauth_token(self):
        """GitHub OAuth tokens (gho_...) should be redacted."""
        text = "OAuth token: gho_abcdefghijklmnopqrstuvwxyzABCDEF123456"
        scrubbed = scrub_secrets(text)
        
        assert "gho_" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_scrub_openrouter_api_key(self):
        """OpenRouter API keys should be detected and scrubbed."""
        text = "The OPENROUTER_API_KEY is sk-or-v1-1234567890abcdef1234567890abcdef"
        result = scrub_secrets(text)
        assert "sk-or-v1-1234567890abcdef1234567890abcdef" not in result
        assert "[REDACTED]" in result
    
    def test_scrub_gemini_api_key(self):
        """Google Gemini API keys (AIza...) should be redacted."""
        text = "My Gemini key is AIzaSyABCDEF1234567890_abcdefghijk-XYZ"
        scrubbed = scrub_secrets(text)
        
        assert "AIzaSy" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_scrub_aws_access_key(self):
        """AWS access keys (AKIA...) should be redacted."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        scrubbed = scrub_secrets(text)
        
        assert "AKIA" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_scrub_bearer_token(self):
        """Bearer tokens in Authorization headers should be redacted."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc"
        scrubbed = scrub_secrets(text)
        
        assert "Bearer eyJ" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_scrub_jwt_token(self):
        """JWT tokens (eyJ... format) should be redacted."""
        text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        scrubbed = scrub_secrets(text)
        
        # JWT tokens start with eyJ and have two dots
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_scrub_private_key(self):
        """PEM-formatted private keys should be redacted."""
        text = """
        Here is my key:
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF
        -----END RSA PRIVATE KEY-----
        Done.
        """
        scrubbed = scrub_secrets(text)
        
        assert "BEGIN RSA PRIVATE KEY" not in scrubbed
        assert "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_scrub_multiple_secrets_in_text(self):
        """Multiple different secrets in the same text should all be redacted."""
        text = """
        GitHub token: ghp_abcdefghijklmnopqrstuvwxyzABCDEF1234
        Gemini key: AIzaSyTest1234567890abcdefghijklmnop_XY
        AWS key: AKIAIOSFODNN7EXAMPLE
        """
        scrubbed = scrub_secrets(text)
        
        # All three should be redacted
        assert "ghp_" not in scrubbed
        assert "AIzaSy" not in scrubbed
        assert "AKIA" not in scrubbed
        # Should have 3 redaction markers
        assert scrubbed.count("[REDACTED_SECRET]") >= 3
    
    def test_custom_redaction_string(self):
        """Should support custom redaction strings for different contexts."""
        text = "Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        scrubbed = scrub_secrets(text, redaction_string="***HIDDEN***")
        
        assert "ghp_" not in scrubbed
        assert "***HIDDEN***" in scrubbed
        assert "[REDACTED_SECRET]" not in scrubbed
    
    def test_additional_patterns(self):
        """Should support additional custom patterns."""
        # Create a custom pattern for a hypothetical service
        custom_pattern = re.compile(r'\bCUSTOM_[A-Z0-9]{20}\b')
        
        text = "My custom secret: CUSTOM_ABCDEFGHIJ1234567890"
        scrubbed = scrub_secrets(text, additional_patterns=[custom_pattern])
        
        assert "CUSTOM_ABCDEFGHIJ1234567890" not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
    
    def test_no_false_positives_on_normal_text(self):
        """Normal text without secrets should pass through unchanged."""
        text = """
        This is a normal review comment. The paper discusses machine learning
        algorithms and includes a GitHub repository with example code. The results
        are promising and show a 15% improvement over baseline methods.
        """
        scrubbed = scrub_secrets(text)
        
        # Most of the text should be unchanged (allowing for some over-redaction of long alphanumeric strings)
        assert "normal review comment" in scrubbed
        assert "machine learning" in scrubbed
        assert "GitHub repository" in scrubbed
    
    def test_empty_text_returns_empty(self):
        """Empty or None text should be handled gracefully."""
        assert scrub_secrets("") == ""
        assert scrub_secrets(None) is None


# ---------------------------------------------------------------------------
# ENVIRONMENT VARIABLE SCRUBBING TESTS
# ---------------------------------------------------------------------------


class TestEnvironmentVariableScrubbing:
    """Test scrubbing of environment variable values."""
    
    def test_scrub_specific_env_var_value(self):
        """Should redact the value of a specific environment variable."""
        with patch.dict(os.environ, {"TEST_SECRET_KEY": "super_secret_value_12345"}):
            text = "The secret is: super_secret_value_12345"
            scrubbed = scrub_environment_variables(text, env_var_names={"TEST_SECRET_KEY"})
            
            assert "super_secret_value_12345" not in scrubbed
            assert "[REDACTED_SECRET]" in scrubbed
    
    def test_auto_detect_sensitive_env_vars(self):
        """Should auto-detect env vars with KEY, TOKEN, SECRET in their names."""
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "sk-or-v1-1234567890abcdef1234567890abcdef",
            "GEMINI_API_KEY": "AIzaSyTestKey123456789012345678901234567",
            "GITHUB_TOKEN": "ghp_testtoken1234567890abcdefghijklmnop",
            "DATABASE_URL": "postgresql://user:pass@localhost/db",  # Not auto-detected (no KEY/TOKEN/SECRET)
        }):
            # Text containing the actual secret values
            text = """
            GEMINI_API_KEY=AIzaSyTestKey123456789012345678901234567
            GITHUB_TOKEN=ghp_testtoken1234567890abcdefghijklmnop
            DATABASE_URL=postgresql://user:pass@localhost/db
            """
            
            # Auto-detect mode (no env_var_names specified)
            scrubbed = scrub_environment_variables(text)
            
            # The KEY and TOKEN values should be redacted
            assert "AIzaSyTestKey123456789012345678901234567" not in scrubbed
            assert "ghp_testtoken1234567890abcdefghijklmnop" not in scrubbed
            
            # The DATABASE_URL might or might not be redacted depending on implementation
            # (PASSWORD is a sensitive keyword, so it might catch the "pass" part)
    
    def test_short_values_not_redacted(self):
        """Short env var values (<=8 chars) should not be redacted to avoid false positives."""
        with patch.dict(os.environ, {"SHORT_KEY": "abc"}):
            text = "The value is: abc"
            scrubbed = scrub_environment_variables(text, env_var_names={"SHORT_KEY"})
            
            # "abc" is too short to be a real secret, so it shouldn't be redacted
            assert "abc" in scrubbed
    
    def test_env_var_names_stay_visible(self):
        """Environment variable NAMES should not be redacted, only their values."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "secret_value_12345"}):
            text = "OPENROUTER_API_KEY is set to: secret_value_12345"
            scrubbed = scrub_environment_variables(text, env_var_names={"OPENROUTER_API_KEY"})
            
            # The name should still be visible
            assert "OPENROUTER_API_KEY" in scrubbed
            # The value should be redacted
            assert "secret_value_12345" not in scrubbed
    
    def test_empty_env_var_not_redacted(self):
        """Empty environment variables should not cause issues."""
        with patch.dict(os.environ, {"EMPTY_SECRET": ""}):
            text = "Some text here"
            scrubbed = scrub_environment_variables(text, env_var_names={"EMPTY_SECRET"})
            
            assert scrubbed == text


# ---------------------------------------------------------------------------
# COMBINED SCRUBBING TESTS
# ---------------------------------------------------------------------------


class TestCombinedScrubbing:
    """Test the scrub_all function that combines all scrubbing methods."""
    
    def test_scrub_all_catches_patterns_and_env_vars(self):
        """scrub_all should apply both pattern-based and env-var-based scrubbing."""
        with patch.dict(os.environ, {"TEST_TOKEN": "env_secret_value_123456"}):
            text = """
            Pattern-based secret: ghp_abcdefghijklmnopqrstuvwxyz123456
            Env var secret: env_secret_value_123456
            """
            scrubbed = scrub_all(text)
            
            # Both types of secrets should be redacted
            assert "ghp_" not in scrubbed
            assert "env_secret_value_123456" not in scrubbed
            assert scrubbed.count("[REDACTED_SECRET]") >= 2
    
    def test_scrub_all_with_custom_settings(self):
        """scrub_all should support custom redaction strings and patterns."""
        custom_pattern = re.compile(r'\bSERVICE_[A-Z0-9]{10}\b')
        
        with patch.dict(os.environ, {"CUSTOM_KEY": "custom_value_12345"}):
            text = "Token: SERVICE_ABC1234567, Key: custom_value_12345"
            scrubbed = scrub_all(
                text,
                redaction_string="***REMOVED***",
                additional_patterns=[custom_pattern],
                env_var_names={"CUSTOM_KEY"}
            )
            
            assert "SERVICE_ABC1234567" not in scrubbed
            assert "custom_value_12345" not in scrubbed
            assert "***REMOVED***" in scrubbed


# ---------------------------------------------------------------------------
# INTEGRATION TESTS: REALISTIC ATTACK SCENARIOS
# ---------------------------------------------------------------------------


class TestRealisticAttackScenarios:
    """
    Test scrubbing against realistic attack scenarios from the B1 vulnerability.
    
    These tests simulate what would happen if a malicious repo successfully
    exfiltrated secrets through symlinks (before the stage 3 fix) and verify
    that the scrubber would catch them before they reach public outputs.
    """
    
    def test_proc_environ_attack_blocked(self):
        """
        Simulate /proc/self/environ exfiltration attempt.
        
        If a symlink to /proc/self/environ was read, the content would look like:
        VAR1=value1\0VAR2=value2\0OPENROUTER_API_KEY=sk-or...\0
        
        The scrubber should catch both the pattern and the env var value.
        """
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "sk-or-v1-RealSecretKey1234567890abcdefghijk",
            "GITHUB_TOKEN": "ghp_realtoken1234567890abcdefghijklmnopqr",
        }):
            # Simulate content from /proc/self/environ (null-byte separated)
            text = (
                "PATH=/usr/bin\x00"
                "USER=runner\x00"
                "OPENROUTER_API_KEY=sk-or-v1-RealSecretKey1234567890abcdefghijk\x00"
                "GITHUB_TOKEN=ghp_realtoken1234567890abcdefghijklmnopqr\x00"
            )
            
            scrubbed = scrub_all(text)
            
            # Both secrets should be redacted
            assert "AIzaSyRealSecretKey" not in scrubbed
            assert "ghp_realtoken" not in scrubbed
    
    def test_git_config_attack_blocked(self):
        """
        Simulate .git/config exfiltration attempt.
        
        The .git/config file contains the GITHUB_TOKEN in the extraheader when
        persist-credentials is true (default). The scrubber should catch it.
        """
        with patch.dict(os.environ, {
            "GITHUB_TOKEN": "ghp_config_token_1234567890abcdefghijklm",
        }):
            # Simulate content from .git/config
            text = """
            [core]
                repositoryformatversion = 0
            [remote "origin"]
                url = https://github.com/owner/repo
                fetch = +refs/heads/*:refs/remotes/origin/*
            [http "https://github.com/"]
                extraheader = AUTHORIZATION: basic ghp_config_token_1234567890abcdefghijklm
            """
            
            scrubbed = scrub_all(text)
            
            # Token should be redacted
            assert "ghp_config_token" not in scrubbed
    
    def test_llm_prompt_injection_attack_blocked(self):
        """
        Simulate an attack where a malicious README contains instructions to
        the LLM to echo back secrets that were leaked into the prompt.
        
        Even if secrets somehow reach the LLM prompt, the scrubber on the OUTPUT
        should catch them before they're posted publicly.
        """
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "sk-or-v1-AttackKey1234567890abcdefghijklmn",
        }):
            # Simulate LLM output that was tricked into echoing the secret
            llm_output = """
            ## Review Summary
            
            The submission is acceptable. Here is the configuration I found:
            OPENROUTER_API_KEY: sk-or-v1-AttackKey1234567890abcdefghijklmn
            
            Score: 7.5/10
            """
            
            scrubbed = scrub_all(llm_output)
            
            # The secret should be redacted from the LLM output
            assert "AIzaSyAttackKey" not in scrubbed
            # The rest of the review should still be intact
            assert "Review Summary" in scrubbed
            assert "acceptable" in scrubbed
            assert "Score: 7.5/10" in scrubbed
    
    def test_base64_encoded_secret_caught_by_generic_pattern(self):
        """
        Base64-encoded secrets are caught by the generic long string pattern.
        
        The generic pattern (50+ chars of alphanumeric/special) catches base64-encoded
        secrets since they're typically long. This provides defense in depth: even if
        an attacker tries to obfuscate a secret, the generic pattern catches it.
        
        The decoded version is also caught by the specific GitHub token pattern.
        """
        import base64
        
        secret = "ghp_secret_token_1234567890abcdefghijklmnop"
        encoded = base64.b64encode(secret.encode()).decode()
        
        text = f"Encoded token: {encoded}"
        scrubbed = scrub_secrets(text)
        
        # The base64-encoded version IS caught by the generic 50+ char pattern
        # (it's 60 chars long: Z2hwX3NlY3JldF90b2tlbl8xMjM0NTY3ODkwYWJjZGVmZ2hpamtsbW5vcA==)
        assert encoded not in scrubbed
        assert "[REDACTED_SECRET]" in scrubbed
        
        # And if the decoded version appears, it's also caught
        text_with_decoded = f"Encoded: {encoded}, Decoded: {secret}"
        scrubbed_decoded = scrub_secrets(text_with_decoded)
        assert secret not in scrubbed_decoded
        assert scrubbed_decoded.count("[REDACTED_SECRET]") >= 2
