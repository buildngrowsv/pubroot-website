"""
B26 review follow-ups (pr300-fix.patch).

Runs the real check-approval `run` script from review.yml under both shells
GitHub uses: `bash -e {0}` (no `shell:` key, what review.yml gets today) and
`bash --noprofile --norc -eo pipefail {0}` (`shell: bash`).
"""
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from test_bug_b26_errexit_fix import extract_check_approval_step_script

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "review.yml"
SHELLS = [["bash", "-e"], ["bash", "--noprofile", "--norc", "-eo", "pipefail"]]

STUB_OUTPUTS = {
    "approved": ("Issue #5\nAuthor: a\nApproved: True\nKind: approved\nReason: repo owner", 0),
    "needs-approval": ("Issue #5\nAuthor: m\nApproved: False\nKind: needs-approval\n"
                       "Reason: requires approved-for-review label from maintainer", 1),
    "rate-limited": ("Issue #5\nAuthor: m\nApproved: False\nKind: rate-limited\n"
                     "Reason: rate limit exceeded (3/3 submissions in 24h)", 1),
    "editorial-hold": ("Issue #5\nAuthor: m\nApproved: False\nKind: editorial-hold\n"
                       "Reason: editorial-hold label present", 1),
    "error": ("ERROR: Failed to fetch issue #5: 404 Client Error\nIssue #5\nAuthor: unknown\n"
              "Approved: False\nKind: error\nReason: Failed to fetch issue", 1),
    "crash": ("Traceback (most recent call last):\nRuntimeError: boom", 1),
}


def run_step(tmp_path, case, shell):
    text, code = STUB_OUTPUTS[case]
    stub = tmp_path / "stub.py"
    stub.write_text(f"import sys\nprint({text!r})\nsys.exit({code})\n")
    approval = tmp_path / "approval.txt"
    out = tmp_path / "out.txt"
    out.write_text("")
    script = (extract_check_approval_step_script()
              .replace('python _review_agent/author_gating.py check "$ISSUE_NUM"',
                       f'python3 {stub} check "$ISSUE_NUM"')
              .replace("/tmp/approval.txt", str(approval))
              .replace("${{ steps.get-issue.outputs.issue_number }}", "5"))
    assert f"python3 {stub}" in script  # the real call was substituted
    path = tmp_path / "step.sh"
    path.write_text(script)
    env = {**os.environ, "GITHUB_OUTPUT": str(out)}
    r = subprocess.run(shell + [str(path)], env=env, capture_output=True, text=True)
    outputs = dict(l.split("=", 1) for l in out.read_text().splitlines() if "=" in l)
    return r, outputs


@pytest.mark.parametrize("shell", SHELLS, ids=["bash-e", "bash-eo-pipefail"])
@pytest.mark.parametrize("case", ["needs-approval", "rate-limited", "editorial-hold"])
def test_gated_kinds_write_outputs_and_succeed(tmp_path, shell, case):
    r, outputs = run_step(tmp_path, case, shell)
    assert r.returncode == 0, r.stdout + r.stderr
    assert outputs["approved"] == "false"
    assert outputs["gate_kind"] == case
    assert outputs["gate_reason"]


@pytest.mark.parametrize("shell", SHELLS, ids=["bash-e", "bash-eo-pipefail"])
def test_approved_writes_true(tmp_path, shell):
    r, outputs = run_step(tmp_path, "approved", shell)
    assert r.returncode == 0
    assert outputs == {"approved": "true"}


@pytest.mark.parametrize("shell", SHELLS, ids=["bash-e", "bash-eo-pipefail"])
@pytest.mark.parametrize("case,kind", [("error", "error"), ("crash", "")])
def test_gate_errors_write_outputs_then_fail_visibly(tmp_path, shell, case, kind):
    r, outputs = run_step(tmp_path, case, shell)
    assert r.returncode == 1, "a gate error must fail the run, not end green"
    assert "::error::Gating check failed" in r.stdout
    assert outputs["approved"] == "false"
    assert outputs["gate_kind"] == kind  # written before exiting


def test_notify_gated_can_resolve_repo_and_fails_closed():
    wf = yaml.safe_load(WORKFLOW.read_text())
    job = wf["jobs"]["notify-gated"]
    has_checkout = any("actions/checkout" in (s.get("uses") or "") for s in job["steps"])
    assert has_checkout or job.get("env", {}).get("GH_REPO") == "${{ github.repository }}"
    post = next(s for s in job["steps"] if s.get("name") == "Post gating comment")
    assert "set -o pipefail" in post["run"].split("EXISTING_COUNT=")[0]
    assert "needs.analyze-submission.outputs.gate_kind == 'needs-approval'" in job["if"]
    assert "approved == 'true'" in wf["jobs"]["review-and-publish"]["if"]
