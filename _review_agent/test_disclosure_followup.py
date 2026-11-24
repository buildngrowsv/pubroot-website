"""
Tests for the disclosure follow-up (Nov 2026, after PR #582):

    - Auto-switch: a prior-art/* submission of another type that declares CC0
      becomes `disclosure` (disclosure rubric) with a warning; without CC0 it
      keeps its chosen type and the existing warning.
    - Stage-1 warnings reach the public review comment ("Submission Notes").
    - Stage 6 labels disclosures `disclosure`; disclosure.yml applies it too.
    - The dry-run picker's tier-4 fallback accepts `### Disclosure Title`.
      (review.yml's guard/fallback tests are in test_review_yml_disclosure_title.py.)
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from stage_1_parse_and_filter import parse_and_filter_submission
from stage_4_build_review_prompt import build_review_prompt
from stage_6_post_review_and_decide import GitHubAPI, post_review_and_decide, _format_review_comment
from test_disclosure_submission_type import (
    _article_layout_body, _disclosure_form_body, _review, NOVELTY, REPO, DISCLOSURE_PARSED,
    LONG_TEXT, PRIOR_ART,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SWITCH = "Submission type switched from 'original-research' to 'disclosure'"


@pytest.fixture
def repo_root(tmp_path):
    shutil.copy(REPO_ROOT / "journals.json", tmp_path / "journals.json")
    empty = {"schema_version": "1.0", "total_papers": 0, "last_updated": "2026-01-01T00:00:00Z", "papers": []}
    for name in ("agent-index.json", "priorroot-index.json"):
        (tmp_path / name).write_text(json.dumps(empty))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Auto-switch
# ---------------------------------------------------------------------------


class TestAutoSwitch:
    def test_prior_art_with_cc0_switches_to_disclosure(self, repo_root, tmp_path):
        result = parse_and_filter_submission(
            _article_layout_body(submission_type="original-research"), repo_root, "author")
        assert result["valid"] is True, result["errors"]
        p = result["parsed"]
        assert p["submission_type"] == "disclosure"
        assert p["license"] == "CC0-1.0"
        assert any(SWITCH in w for w in result["warnings"])
        assert any(SWITCH in w for w in p["stage1_warnings"])
        prompt = build_review_prompt(p, NOVELTY, REPO, str(tmp_path), "2026-096")
        assert "Defensive Disclosure (Priorroot)" in prompt
        assert "TYPE-SPECIFIC REVIEW CRITERIA: Original Research" not in prompt

    @pytest.mark.parametrize("chosen", ["case-study", "review-survey", "not-a-type"])
    def test_other_types_switch_too(self, repo_root, chosen):
        result = parse_and_filter_submission(
            _article_layout_body(submission_type=chosen), repo_root, "author")
        assert result["parsed"]["submission_type"] == "disclosure"

    def test_form_with_ticked_cc0_and_other_type_switches(self, repo_root):
        result = parse_and_filter_submission(
            _disclosure_form_body(submission_type="original-research"), repo_root, "author")
        assert result["valid"] is True, result["errors"]
        assert result["parsed"]["submission_type"] == "disclosure"

    def test_prior_art_without_cc0_keeps_type(self, repo_root):
        result = parse_and_filter_submission(
            _article_layout_body(submission_type="original-research",
                                 abstract="A disclosure of a therapeutic use."),
            repo_root, "author")
        assert result["valid"] is True, result["errors"]
        assert result["parsed"]["submission_type"] == "original-research"
        assert "license" not in result["parsed"]
        assert not any("switched" in w for w in result["warnings"])
        assert any("should use submission type 'disclosure'" in w for w in result["warnings"])

    def test_non_prior_art_with_cc0_keeps_type(self, repo_root):
        """Regression: CC0 outside prior-art/* never switches; Original Research routes as before."""
        result = parse_and_filter_submission(
            _article_layout_body(category="ai/agent-architecture", submission_type="original-research"),
            repo_root, "author")
        assert result["valid"] is True, result["errors"]
        assert result["parsed"]["submission_type"] == "original-research"
        assert not any("switched" in w for w in result["warnings"])

    def test_explicit_disclosure_has_no_switch_warning(self, repo_root):
        result = parse_and_filter_submission(_article_layout_body(), repo_root, "author")
        assert result["parsed"]["submission_type"] == "disclosure"
        assert not any("switched" in w for w in result["warnings"])

    def test_switched_submission_must_still_cite_prior_art(self, repo_root):
        body = "## Protocol\n\n" + LONG_TEXT
        result = parse_and_filter_submission(
            _article_layout_body(submission_type="original-research", body=body), repo_root, "author")
        assert result["parsed"]["submission_type"] == "disclosure"
        assert result["valid"] is False
        assert any("must cite prior art" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Warnings reach the review comment; disclosure label
# ---------------------------------------------------------------------------


def test_format_review_comment_includes_notes():
    comment = _format_review_comment(_review(8.0)["review"], {}, "2026-096", 8.0, "ACCEPTED",
                                     notes=[SWITCH + ": test"])
    assert "## Submission Notes" in comment
    assert SWITCH in comment


def test_format_review_comment_without_notes_unchanged():
    review = _review(8.0)["review"]
    assert _format_review_comment(review, {}, "2026-096", 8.0, "ACCEPTED") == \
        _format_review_comment(review, {}, "2026-096", 8.0, "ACCEPTED", notes=[])
    assert "Submission Notes" not in _format_review_comment(review, {}, "2026-096", 8.0, "ACCEPTED")


def _decide(parsed, root, score=8.0):
    with patch.object(GitHubAPI, "post_comment") as post, patch.object(GitHubAPI, "add_labels") as labels, \
            patch.object(GitHubAPI, "close_issue"), \
            patch("stage_6_post_review_and_decide._update_contributors"), \
            patch("stage_6_post_review_and_decide._handle_acceptance", return_value=123), \
            patch("stage_6_post_review_and_decide._remove_labels_if_present"):
        post_review_and_decide(_review(score), parsed, NOVELTY, REPO, "2026-096", 96,
                               "owner", "repo", "token", root)
    return post, labels


def test_stage1_switch_warning_appears_in_posted_comment(repo_root):
    """End to end: stage 1 output -> stage 6 posts the switch notice publicly."""
    parsed = parse_and_filter_submission(
        _article_layout_body(submission_type="original-research"), repo_root, "author")["parsed"]
    post, labels = _decide(parsed, repo_root)
    body = post.call_args[0][1]
    assert "## Submission Notes" in body and SWITCH in body
    assert any(c[0][1] == ["disclosure"] for c in labels.call_args_list)


def test_non_disclosure_not_labelled(repo_root):
    parsed = dict(DISCLOSURE_PARSED, submission_type="original-research")
    _, labels = _decide(parsed, repo_root)
    assert not any(c[0][1] == ["disclosure"] for c in labels.call_args_list)


def test_label_failure_is_non_fatal(repo_root):
    def boom(self, n, names):
        if names == ["disclosure"]:
            raise RuntimeError("label API down")
    with patch.object(GitHubAPI, "post_comment"), patch.object(GitHubAPI, "add_labels", boom), \
            patch.object(GitHubAPI, "close_issue"), \
            patch("stage_6_post_review_and_decide._update_contributors"), \
            patch("stage_6_post_review_and_decide._handle_acceptance", return_value=123) as publish, \
            patch("stage_6_post_review_and_decide._remove_labels_if_present"):
        post_review_and_decide(_review(8.0), DISCLOSURE_PARSED, NOVELTY, REPO, "2026-096", 96,
                               "owner", "repo", "token", repo_root)
    assert publish.called


def test_disclosure_form_applies_label():
    form = yaml.safe_load((REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "disclosure.yml").read_text())
    assert form["labels"] == ["submission", "pending-review", "disclosure"]


DISCLOSURE_BODY = "### Disclosure Title\n\nX\n\n### Category\n\nprior-art/therapeutic-use"


def test_dry_run_picker_tier4_matches_disclosure_title():
    from scripts.dry_run_review_picker import pick_next
    bug = {"number": 400, "labels": [], "body": "Steps to reproduce"}
    sub = {"number": 402, "labels": [], "body": DISCLOSURE_BODY}
    picked, _ = pick_next([bug, sub], lambda i: {"approved": True, "reason": "t"}, token="fake")
    assert picked == 402
