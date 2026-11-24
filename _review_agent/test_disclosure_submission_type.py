"""
Tests for the Priorroot `disclosure` submission type (Nov 2026).

Covers:
    - Stage 1 parse of the disclosure.yml form layout (Disclosure Title,
      Detailed Description, Prior Art Cited, Public Domain Dedication (CC0))
      and of disclosures filed with the article layout (submission.yml).
    - Stage 1 validation of the disclosure-only required fields.
    - Stage 4 rubric routing: disclosures get the disclosure rubric, not the
      Original Research rubric; Original Research still routes as before.
    - Stage 6: the 7.0 floor (D-21) and the promotional_intent force-reject
      (D-26) still apply to disclosures; disclosure metadata reaches the
      frontmatter, manifest and index entry, and nothing changes for other types.

WHY: Priorroot issues #95-#116 were filed as prior-art/* disclosures but were
scored with the Original Research rubric (unknown types defaulted to
original-research), and 8 of 9 were rejected for having no novel data.
"""

import json
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from stage_1_parse_and_filter import parse_and_filter_submission, VALID_SUBMISSION_TYPES
from stage_4_build_review_prompt import build_review_prompt, _build_type_specific_criteria
from stage_6_post_review_and_decide import (
    GitHubAPI,
    post_review_and_decide,
    _build_article_md,
    _build_manifest,
)
from index_builder import build_index_entry_from_data, build_priorroot_index

REPO_ROOT = Path(__file__).resolve().parents[1]

LONG_TEXT = " ".join(["The compound is given orally at 500 mg twice daily with meals."] * 25)
PRIOR_ART = (
    "- Yin J, Xing H, Ye J (2008). Efficacy of berberine in patients with type 2 diabetes. "
    "Metabolism 57(5):712-717. https://doi.org/10.1016/j.metabol.2008.01.013\n"
    "- US 8,524,191 B2 (example patent)"
)
CHECKED = "- [X] I dedicate this disclosure to the public domain under CC0 1.0"
UNCHECKED = "- [ ] I dedicate this disclosure to the public domain under CC0 1.0"


def _disclosure_form_body(
    title="Berberine for AMPK-Mediated Glycemic Control - Defensive Therapeutic-Use Disclosure",
    category="prior-art/therapeutic-use",
    submission_type="disclosure",
    abstract="This defensive disclosure places berberine for glycemic control in the public domain under CC0 1.0.",
    description=None,
    prior_art=PRIOR_ART,
    cc0=CHECKED,
) -> str:
    """Mimic the issue body GitHub renders from .github/ISSUE_TEMPLATE/disclosure.yml."""
    if description is None:
        description = "## Subject Matter Disclosed\n\n" + LONG_TEXT
    return f"""### Disclosure Title

{title}

### Category

{category}

### Submission Type

{submission_type}

### AI / Tooling Attribution (optional)

_No response_

### Abstract

{abstract}

### Detailed Description

{description}

### Prior Art Cited

{prior_art}

### Supporting Repository URL

_No response_

### Commit SHA

_No response_

### Repository Visibility

no-repo

### Public Domain Dedication (CC0)

{cc0}

### Submission Agreement

- [X] I confirm this is original work or properly attributed, and contains no personal or patient data"""


def _article_layout_body(category="prior-art/therapeutic-use", submission_type="disclosure",
                         abstract="A disclosure dedicated to the public domain under CC0 1.0.",
                         body=None) -> str:
    """Mimic submission.yml (the layout Priorroot issues #95-#116 used)."""
    if body is None:
        body = "## Protocol\n\n" + LONG_TEXT + "\n\n## References\n\n" + PRIOR_ART
    return f"""### Article Title

Test Disclosure Title For Validation

### Category

{category}

### Submission Type

{submission_type}

### AI / Tooling Attribution (optional)

_No response_

### Abstract

{abstract}

### Article Body

{body}

### Supporting Repository URL

_No response_

### Commit SHA

_No response_

### Repository Visibility

no-repo

### Payment Code (Optional)

_No response_

### Submission Agreement

- [X] I confirm this is original work or properly attributed"""


@pytest.fixture
def repo_root(tmp_path):
    """Temp repo root with the real journals.json and empty indexes."""
    shutil.copy(REPO_ROOT / "journals.json", tmp_path / "journals.json")
    empty = {"schema_version": "1.0", "total_papers": 0, "last_updated": "2026-01-01T00:00:00Z", "papers": []}
    for name in ("agent-index.json", "priorroot-index.json"):
        (tmp_path / name).write_text(json.dumps(empty))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# STAGE 1: parse
# ---------------------------------------------------------------------------


class TestDisclosureParse:
    def test_disclosure_is_a_valid_type(self):
        assert "disclosure" in VALID_SUBMISSION_TYPES

    def test_form_layout_parses_and_validates(self, repo_root):
        result = parse_and_filter_submission(_disclosure_form_body(), repo_root, "author")
        assert result["valid"] is True, result["errors"]
        p = result["parsed"]
        assert p["submission_type"] == "disclosure"
        assert p["title"].startswith("Berberine for AMPK")
        assert p["category"] == "prior-art/therapeutic-use"
        assert p["journal"] == "prior-art"
        assert p["license"] == "CC0-1.0"
        assert p["prior_art_cited"].startswith("- Yin J")
        # Detailed Description + Prior Art Cited are joined into one body
        assert p["body"].startswith("## Subject Matter Disclosed")
        assert "## Prior Art Cited" in p["body"]
        assert "doi.org/10.1016/j.metabol.2008.01.013" in p["body"]
        assert p["word_count_body"] >= 200

    def test_defensive_disclosure_alias(self, repo_root):
        """#95 and #102 typed 'defensive-disclosure' by hand; it now maps to disclosure."""
        result = parse_and_filter_submission(
            _article_layout_body(submission_type="defensive-disclosure"), repo_root, "author")
        assert result["valid"] is True, result["errors"]
        assert result["parsed"]["submission_type"] == "disclosure"
        assert not any("Unknown submission type" in w for w in result["warnings"])

    def test_article_layout_disclosure_parses(self, repo_root):
        result = parse_and_filter_submission(_article_layout_body(), repo_root, "author")
        assert result["valid"] is True, result["errors"]
        assert result["parsed"]["submission_type"] == "disclosure"
        assert result["parsed"]["license"] == "CC0-1.0"
        assert result["parsed"]["prior_art_cited"] is None

    def test_title_label_article_title_still_wins(self, repo_root):
        body = _disclosure_form_body().replace("### Disclosure Title", "### Article Title")
        result = parse_and_filter_submission(body, repo_root, "author")
        assert result["parsed"]["title"].startswith("Berberine for AMPK")


# ---------------------------------------------------------------------------
# STAGE 1: validation
# ---------------------------------------------------------------------------


class TestDisclosureValidation:
    def test_missing_prior_art_field_is_an_error(self, repo_root):
        result = parse_and_filter_submission(_disclosure_form_body(prior_art="_No response_"), repo_root, "author")
        assert result["valid"] is False
        assert "Missing required field: Prior Art Cited" in result["errors"]

    def test_unticked_cc0_box_is_an_error(self, repo_root):
        result = parse_and_filter_submission(_disclosure_form_body(cc0=UNCHECKED), repo_root, "author")
        assert result["valid"] is False
        assert any("CC0" in e for e in result["errors"])

    def test_missing_abstract_is_an_error(self, repo_root):
        """#97 had a lone '|' as its abstract; that stays a validation failure."""
        result = parse_and_filter_submission(_disclosure_form_body(abstract="|"), repo_root, "author")
        assert result["valid"] is False
        assert "Missing required field: Abstract" in result["errors"]

    def test_missing_description_is_an_error(self, repo_root):
        result = parse_and_filter_submission(
            _disclosure_form_body(description="_No response_", prior_art="- one source"), repo_root, "author")
        assert result["valid"] is False
        assert "Missing required field: Detailed Description" in result["errors"]

    def test_disclosure_outside_prior_art_is_an_error(self, repo_root):
        result = parse_and_filter_submission(
            _article_layout_body(category="ai/agent-architecture"), repo_root, "author")
        assert result["valid"] is False
        assert any("requires a prior-art/* category" in e for e in result["errors"])

    def test_article_layout_without_citations_is_an_error(self, repo_root):
        body = "## Protocol\n\n" + LONG_TEXT
        result = parse_and_filter_submission(_article_layout_body(body=body), repo_root, "author")
        assert result["valid"] is False
        assert any("must cite prior art" in e for e in result["errors"])

    def test_article_layout_with_two_links_passes_citation_check(self, repo_root):
        body = ("## Protocol\n\n" + LONG_TEXT + " See https://pubmed.ncbi.nlm.nih.gov/1/ "
                "and https://doi.org/10.1000/xyz123 .")
        result = parse_and_filter_submission(_article_layout_body(body=body), repo_root, "author")
        assert result["valid"] is True, result["errors"]

    def test_article_layout_without_cc0_is_an_error(self, repo_root):
        result = parse_and_filter_submission(
            _article_layout_body(abstract="A disclosure of a therapeutic use."), repo_root, "author")
        assert result["valid"] is False
        assert any("public-domain dedication" in e for e in result["errors"])

    def test_prior_art_category_with_other_type_warns_but_stays_valid(self, repo_root):
        """Regression: prior-art/* + original-research without CC0 validates as before.
        (With a CC0 declaration it is auto-switched; see test_disclosure_followup.py.)"""
        result = parse_and_filter_submission(
            _article_layout_body(submission_type="original-research",
                                 abstract="A disclosure of a therapeutic use."),
            repo_root, "author")
        assert result["valid"] is True, result["errors"]
        assert result["parsed"]["submission_type"] == "original-research"
        assert "license" not in result["parsed"]
        assert any("should use submission type 'disclosure'" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# STAGE 4: rubric routing
# ---------------------------------------------------------------------------

NOVELTY = {"arxiv_results": [], "s2_results": [], "internal_results": [], "potential_supersession": None}
REPO = {"available": False, "badge_type": "text_only"}


def _prompt(submission_type, tmp_path):
    parsed = {
        "title": "T", "category": "prior-art/therapeutic-use", "abstract": "A", "body": "B",
        "author": "a", "submission_type": submission_type, "word_count_body": 300,
    }
    return build_review_prompt(parsed, NOVELTY, REPO, str(tmp_path), "2026-001")


class TestDisclosureRubricRouting:
    def test_disclosure_gets_disclosure_rubric(self, tmp_path):
        prompt = _prompt("disclosure", tmp_path)
        assert "TYPE-SPECIFIC REVIEW CRITERIA: Defensive Disclosure (Priorroot)" in prompt
        assert "TYPE-SPECIFIC REVIEW CRITERIA: Original Research" not in prompt
        assert "**Enabling Detail** (CRITICAL)" in prompt
        assert "**Prior-Art Citation Accuracy** (CRITICAL)" in prompt
        assert "**Novelty** (LOW)" in prompt
        assert "do not require new experiments, new data or empirical results" in prompt
        assert "For novelty assessment, compare against the existing literature" not in prompt
        assert "Do NOT lower the score because the disclosure reports no new experiments or data." in prompt

    def test_disclosure_keeps_floor_and_promotional_rules(self, tmp_path):
        prompt = _prompt("disclosure", tmp_path)
        assert 'The verdict MUST be "ACCEPTED" if score >= 7.0, "REJECTED" if score < 7.0.' in prompt
        assert "PROMOTIONAL INTENT OVERRIDES RULE 8" in prompt
        assert '"promotional_intent"' in prompt

    def test_original_research_routes_as_before(self, tmp_path):
        """Regression: Original Research keeps its rubric and rule 6 text."""
        prompt = _prompt("original-research", tmp_path)
        assert "TYPE-SPECIFIC REVIEW CRITERIA: Original Research" in prompt
        assert "**Novelty** (CRITICAL)" in prompt
        assert "6. For novelty assessment, compare against the existing literature listed above.\n7." in prompt
        assert "Defensive Disclosure" not in prompt

    def test_unknown_type_still_falls_back_to_original_research(self):
        assert "Original Research" in _build_type_specific_criteria("not-a-type")
        assert _build_type_specific_criteria("disclosure") != _build_type_specific_criteria("original-research")

    def test_end_to_end_parse_then_route(self, repo_root, tmp_path):
        parsed = parse_and_filter_submission(_disclosure_form_body(), repo_root, "author")["parsed"]
        prompt = build_review_prompt(parsed, NOVELTY, REPO, str(tmp_path), "2026-001")
        assert "Defensive Disclosure (Priorroot)" in prompt
        assert "**Submission Type:** disclosure" in prompt


# ---------------------------------------------------------------------------
# STAGE 6: floor, promotional intent, publication metadata
# ---------------------------------------------------------------------------

DISCLOSURE_PARSED = {
    "title": "Berberine Disclosure", "category": "prior-art/therapeutic-use",
    "abstract": "A CC0 disclosure.", "body": "Body text.", "author": "test-user",
    "supporting_repo": None, "commit_sha": None, "submission_type": "disclosure",
    "license": "CC0-1.0", "word_count_body": 900,
}


def _review(score, verdict="ACCEPTED", promotional=False):
    return {
        "success": True,
        "review": {
            "paper_id": "2026-097", "score": score, "verdict": verdict, "badge": "text_only",
            "summary": "s", "strengths": ["a"], "weaknesses": ["b"], "suggestions": ["c"],
            "confidence": {"methodology": 0.8, "factual_accuracy": 0.9, "novelty": 0.3,
                           "code_quality": None, "writing_quality": 0.9, "reproducibility": 0.8},
            "claims": [], "novelty_vs_existing": [], "promotional_intent": promotional,
            "supersedes": None, "superseded_by": None, "valid_until": "2027-05-24",
            "review_metadata": {"reviewer": "test", "review_date": "2026-11-24T00:00:00Z",
                                "grounding_used": True, "calibration_examples_used": 0,
                                "novelty_sources_checked": 0},
        },
        "grounding_metadata": {}, "errors": [],
    }


@pytest.fixture
def stage6_root():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "contributors.json"), "w") as f:
            json.dump({"contributors": {}}, f)
        with open(os.path.join(tmpdir, "agent-index.json"), "w") as f:
            json.dump({"schema_version": "1.0", "total_papers": 0, "last_updated": "2026-01-01T00:00:00Z", "papers": []}, f)
        yield tmpdir


def _decide(review, root):
    with patch.object(GitHubAPI, "post_comment"), patch.object(GitHubAPI, "add_labels"), \
            patch.object(GitHubAPI, "close_issue"), \
            patch("stage_6_post_review_and_decide._update_contributors"), \
            patch("stage_6_post_review_and_decide._handle_acceptance", return_value=123) as publish, \
            patch("stage_6_post_review_and_decide._remove_labels_if_present"):
        result = post_review_and_decide(review, DISCLOSURE_PARSED, NOVELTY, REPO, "2026-097", 97,
                                        "owner", "repo", "token", root)
    return result, publish


@pytest.mark.parametrize("score", [6.9, 7.0])
def test_d21_floor_applies_to_disclosures(score, stage6_root):
    result, publish = _decide(_review(score), stage6_root)
    assert publish.called == (score >= 7.0)
    if score < 7.0:
        assert result["action_taken"] == "rejected"


def test_d26_promotional_intent_rejects_disclosures(stage6_root):
    result, publish = _decide(_review(9.0, promotional=True), stage6_root)
    assert publish.called is False
    assert result["action_taken"] == "rejected"


class TestDisclosurePublicationMetadata:
    NOW = datetime(2026, 11, 24, 15, 0, 0, tzinfo=timezone.utc)

    def test_frontmatter_marks_disclosure_and_cc0(self):
        md = _build_article_md(DISCLOSURE_PARSED, {"score": 8.0, "verdict": "ACCEPTED"},
                               {"badge_type": "text_only"}, "2026-097", self.NOW)
        assert 'submission_type: "disclosure"' in md
        assert 'license: "CC0-1.0"' in md

    def test_manifest_marks_disclosure_and_cc0(self):
        m = _build_manifest(DISCLOSURE_PARSED, {"score": 8.0, "verdict": "ACCEPTED"},
                            {"badge_type": "text_only"}, "2026-097", self.NOW, NOVELTY)
        assert m["submission_type"] == "disclosure"
        assert m["license"] == "CC0-1.0"

    def test_other_types_unchanged(self):
        parsed = dict(DISCLOSURE_PARSED, submission_type="original-research")
        parsed.pop("license")
        md = _build_article_md(parsed, {"score": 8.0, "verdict": "ACCEPTED"},
                               {"badge_type": "text_only"}, "2026-097", self.NOW)
        m = _build_manifest(parsed, {"score": 8.0, "verdict": "ACCEPTED"},
                            {"badge_type": "text_only"}, "2026-097", self.NOW, NOVELTY)
        assert "submission_type" not in md and "license" not in md
        assert "submission_type" not in m and "license" not in m
        entry = build_index_entry_from_data(
            paper_id="2026-097", title="t", author="a", category="ai/x", abstract="a",
            published_date="2026-11-24T15:00:00Z", review_score=8.0, badge="text_only",
            article_path="papers/ai/x/t/index.md", reader_url="https://pubroot.com/ai/x/t/")
        assert "submission_type" not in entry and "license" not in entry

    def test_index_entry_matches_regenerator(self, tmp_path):
        """Stage 6's in-memory entry and the on-disk regenerator agree on the new keys."""
        paper_dir = tmp_path / "papers" / "prior-art" / "therapeutic-use" / "berberine-disclosure"
        paper_dir.mkdir(parents=True)
        md = _build_article_md(DISCLOSURE_PARSED, {"score": 8.0, "verdict": "ACCEPTED"},
                               {"badge_type": "text_only"}, "2026-097", self.NOW)
        (paper_dir / "index.md").write_text(md)
        m = _build_manifest(DISCLOSURE_PARSED, {"score": 8.0, "verdict": "ACCEPTED"},
                            {"badge_type": "text_only"}, "2026-097", self.NOW, NOVELTY)
        (paper_dir / "manifest.json").write_text(json.dumps(m))
        index = build_priorroot_index(tmp_path / "papers", tmp_path)
        disk_entry = index["papers"][0]
        mem_entry = build_index_entry_from_data(
            paper_id="2026-097", title="Berberine Disclosure", author="test-user",
            category="prior-art/therapeutic-use", abstract="A CC0 disclosure.",
            published_date="2026-11-24T15:00:00Z", review_score=8.0, badge="text_only",
            article_path=disk_entry["article_path"], reader_url=disk_entry["reader_url"],
            review_path=disk_entry["review_path"], submission_type="disclosure", license="CC0-1.0")
        assert disk_entry["submission_type"] == mem_entry["submission_type"] == "disclosure"
        assert disk_entry["license"] == mem_entry["license"] == "CC0-1.0"
        assert list(disk_entry)[-2:] == list(mem_entry)[-2:] == ["submission_type", "license"]


def test_issue_templates_match_parser_labels():
    """Every field label on disclosure.yml is one the stage-1 parser splits on."""
    import re
    import stage_1_parse_and_filter as s1
    src = Path(s1.__file__).read_text()
    template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "disclosure.yml").read_text()
    labels = re.findall(r'^\s+label: "([^"]+)"$', template, flags=re.MULTILINE)
    field_labels = [l for l in labels if not l.startswith("I ")]
    for label in field_labels:
        assert f'"{label}"' in src, f"disclosure.yml label {label!r} missing from KNOWN_LABELS"
    assert '- "disclosure"' in template
    assert 'title: "[SUBMISSION] "' in template
