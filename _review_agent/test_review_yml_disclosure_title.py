"""
review.yml accepts disclosure.yml issues (Nov 2026): the analyze-submission
job guard and the tier-4 0-label fallback match `### Disclosure Title` as
well as `### Article Title` (always with `### Category`).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "review.yml"


# ---------------------------------------------------------------------------
# review.yml job guard and tier-4 fallback
# ---------------------------------------------------------------------------

DISCLOSURE_BODY = "### Disclosure Title\n\nX\n\n### Category\n\nprior-art/therapeutic-use"
ARTICLE_BODY = "### Article Title\n\nX\n\n### Category\n\nai/agent-architecture"


def _guard_expr() -> str:
    wf = yaml.safe_load(WORKFLOW.read_text())
    return wf["jobs"]["analyze-submission"]["if"]


def _eval_guard(expr: str, event_name: str, labels: list, body: str) -> bool:
    """Tiny evaluator for the guard's contains()/||/&& expression."""
    def contains(hay, needle):
        return needle in hay
    py = expr.replace("||", " or ").replace("&&", " and ")
    py = py.replace("github.event.issue.labels.*.name", "labels")
    py = py.replace("github.event.issue.body", "body").replace("github.event_name", "event_name")
    return bool(eval(py, {"contains": contains}, {"labels": labels, "body": body, "event_name": event_name}))


@pytest.mark.parametrize("body,expected", [
    (DISCLOSURE_BODY, True),
    (ARTICLE_BODY, True),
    ("### Disclosure Title\n\nX", False),
    ("Steps to reproduce", False),
])
def test_job_guard_matches_disclosure_title(body, expected):
    assert _eval_guard(_guard_expr(), "issues", [], body) is expected


def _tier4_jq() -> str:
    m = re.search(r"--jq '(map\(select\(\(\.labels \| length == 0\).*?)' \\\n", WORKFLOW.read_text())
    assert m, "tier-4 jq filter not found in review.yml"
    return m.group(1)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed")
def test_tier4_fallback_matches_disclosure_title():
    issues = [
        {"number": 1, "labels": [], "body": DISCLOSURE_BODY},
        {"number": 2, "labels": [], "body": ARTICLE_BODY},
        {"number": 3, "labels": [], "body": "Steps to reproduce"},
        {"number": 4, "labels": [{"name": "submission"}], "body": DISCLOSURE_BODY},
        {"number": 5, "labels": [], "body": None},
    ]
    out = subprocess.run(["jq", "-r", _tier4_jq()], input=json.dumps(issues),
                         capture_output=True, text=True, check=True).stdout.split()
    assert out == ["1", "2"]


