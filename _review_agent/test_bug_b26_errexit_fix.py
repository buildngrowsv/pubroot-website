"""
Test suite for Bug B26: errexit handling in check-approval workflow step

BUG CONTEXT:
    GitHub Actions runs `run:` steps with `bash -e {0}` by default. The check-approval
    step in review.yml originally ran:
        python _review_agent/author_gating.py check "$ISSUE_NUM" > /tmp/approval.txt 2>&1
        EXIT_CODE=$?
    
    When author_gating.py exits 1 (author not approved), bash -e caused the step to die
    on that line before capturing $? and setting the output variables. This broke all
    gated submissions - they got "Process completed with exit code 1" instead of posting
    "Review Pending Approval" and adding awaiting-approval/submission labels.

FIX:
    Changed to:
        if python _review_agent/author_gating.py check "$ISSUE_NUM" > /tmp/approval.txt 2>&1; then
          EXIT_CODE=0
        else
          EXIT_CODE=$?
        fi
    
    This prevents the non-zero exit from being fatal under bash -e.

TEST APPROACH:
    1. Parse review.yml and extract the check-approval step's run script
    2. Create stub scripts that mimic author_gating.py's behavior (exit 0 for approved,
       exit 1 with Kind/Reason output for gated)
    3. Run the extracted step script with bash -e against each stub
    4. Assert the script exits 0 in both cases and writes correct outputs to GITHUB_OUTPUT

EVIDENCE:
    Failed runs on this bug: 41678625437, 41678629786, 41678634863
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest
import yaml


def extract_check_approval_step_script():
    """
    Extract the check-approval step's run script from review.yml.
    
    This validates that we're testing the actual workflow script, not a mock.
    """
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "review.yml"
    
    with open(workflow_path, 'r') as f:
        workflow = yaml.safe_load(f)
    
    # Find the check-approval step in the analyze-submission job
    job = workflow['jobs']['analyze-submission']
    step = None
    for s in job['steps']:
        if s.get('id') == 'check-approval':
            step = s
            break
    
    assert step is not None, "check-approval step not found in review.yml"
    assert 'run' in step, "check-approval step has no run script"
    
    return step['run']


def prepare_test_script(script, stub_script, approval_txt, issue_num):
    """
    Prepare a test script by replacing paths and issue numbers.
    
    Args:
        script: The original workflow step script
        stub_script: Path to the stub author_gating.py
        approval_txt: Path to the temp approval.txt file
        issue_num: Issue number to use in the test
    
    Returns:
        The modified script ready for testing
    """
    # Replace the python call with our stub and fix all /tmp/approval.txt paths
    test_script = script.replace(
        'python _review_agent/author_gating.py check "$ISSUE_NUM"',
        f'python3 {stub_script} check "$ISSUE_NUM"'
    ).replace(
        '/tmp/approval.txt',
        str(approval_txt)
    )
    
    # Prepend shebang and set -e to mimic GitHub Actions runner
    full_script = f"""#!/bin/bash
set -e
{test_script}
"""
    
    # Replace GitHub Actions template variables
    full_script = full_script.replace('${{ steps.get-issue.outputs.issue_number }}', str(issue_num))
    
    return full_script


def test_check_approval_step_with_approved_author(tmp_path):
    """
    Test that the check-approval step script handles exit 0 (approved) correctly.
    
    The stub exits 0 and outputs:
        Issue #42
        Author: trusted-user
        Approved: True
        Kind: approved
        Reason: repo owner
    
    The step script should:
    - Exit 0
    - Write approved=true to GITHUB_OUTPUT
    - NOT write gate_kind or gate_reason
    """
    script = extract_check_approval_step_script()
    
    # Create a stub script that mimics author_gating.py for an approved author
    stub_script = tmp_path / "author_gating_stub.py"
    stub_script.write_text("""#!/usr/bin/env python3
import sys
print("Issue #42")
print("Author: trusted-user")
print("Approved: True")
print("Kind: approved")
print("Reason: repo owner")
sys.exit(0)
""")
    stub_script.chmod(0o755)
    
    # Create temp files for the test
    github_output = tmp_path / "github_output.txt"
    approval_txt = tmp_path / "approval.txt"
    
    # Prepare the test script
    full_script = prepare_test_script(script, stub_script, approval_txt, issue_num=42)
    
    script_file = tmp_path / "test_script.sh"
    script_file.write_text(full_script)
    script_file.chmod(0o755)
    
    # Run the script with GITHUB_OUTPUT set
    env = os.environ.copy()
    env['GITHUB_OUTPUT'] = str(github_output)
    
    result = subprocess.run(
        [str(script_file)],
        env=env,
        capture_output=True,
        text=True
    )
    
    # Assert the script exited 0 (did not die under bash -e)
    assert result.returncode == 0, f"Script exited {result.returncode}, stderr: {result.stderr}"
    
    # Assert GITHUB_OUTPUT contains approved=true
    output_lines = github_output.read_text().strip().split('\n')
    assert 'approved=true' in output_lines, f"Expected approved=true in {output_lines}"
    
    # Assert gate_kind and gate_reason are NOT set (approved authors don't have those)
    assert not any('gate_kind=' in line for line in output_lines), "gate_kind should not be set for approved authors"
    assert not any('gate_reason=' in line for line in output_lines), "gate_reason should not be set for approved authors"
    
    # Assert approval.txt contains the stub output
    approval_content = approval_txt.read_text()
    assert "Approved: True" in approval_content
    assert "repo owner" in approval_content


def test_check_approval_step_with_gated_author(tmp_path):
    """
    Test that the check-approval step script handles exit 1 (gated) correctly.
    
    This is the critical test for Bug B26. Before the fix, this would die with:
        Process completed with exit code 1
    
    The stub exits 1 and outputs:
        Issue #99
        Author: untrusted-user
        Approved: False
        Kind: needs-approval
        Reason: requires approved-for-review label from maintainer
    
    The step script should:
    - Exit 0 (even though the gating check returned 1)
    - Write approved=false to GITHUB_OUTPUT
    - Write gate_kind=needs-approval to GITHUB_OUTPUT
    - Write gate_reason=requires approved-for-review label from maintainer to GITHUB_OUTPUT
    """
    script = extract_check_approval_step_script()
    
    # Create a stub script that mimics author_gating.py for a gated author
    stub_script = tmp_path / "author_gating_stub.py"
    stub_script.write_text("""#!/usr/bin/env python3
import sys
print("Issue #99")
print("Author: untrusted-user")
print("Approved: False")
print("Kind: needs-approval")
print("Reason: requires approved-for-review label from maintainer")
sys.exit(1)
""")
    stub_script.chmod(0o755)
    
    # Create temp files for the test
    github_output = tmp_path / "github_output.txt"
    approval_txt = tmp_path / "approval.txt"
    
    # Prepare the test script
    full_script = prepare_test_script(script, stub_script, approval_txt, issue_num=99)
    
    script_file = tmp_path / "test_script.sh"
    script_file.write_text(full_script)
    script_file.chmod(0o755)
    
    # Run the script with GITHUB_OUTPUT set
    env = os.environ.copy()
    env['GITHUB_OUTPUT'] = str(github_output)
    
    result = subprocess.run(
        [str(script_file)],
        env=env,
        capture_output=True,
        text=True
    )
    
    # CRITICAL ASSERTION: The script should exit 0 even though author_gating.py exited 1
    # Before the fix, this would fail with exit code 1 due to bash -e killing the step
    assert result.returncode == 0, (
        f"Script died with exit code {result.returncode} under bash -e. "
        f"This means the fix for Bug B26 is broken. "
        f"stderr: {result.stderr}, stdout: {result.stdout}"
    )
    
    # Assert GITHUB_OUTPUT contains all required fields for a gated submission
    output_lines = github_output.read_text().strip().split('\n')
    approval_content = approval_txt.read_text()
    assert 'approved=false' in output_lines, f"Expected approved=false in {output_lines}. approval.txt: {approval_content}"
    assert 'gate_kind=needs-approval' in output_lines, f"Expected gate_kind=needs-approval in {output_lines}. approval.txt: {approval_content}"
    
    # gate_reason should contain the full text (may be split across parsing logic)
    output_text = github_output.read_text()
    assert 'gate_reason=' in output_text, f"Expected gate_reason in output"
    # The actual reason text should be parsed from the Kind: line
    assert 'needs-approval' in output_text or 'approved-for-review' in output_text, \
        f"Expected gate reason keywords in output: {output_text}"
    
    # Assert approval.txt contains the stub output
    approval_content = approval_txt.read_text()
    assert "Approved: False" in approval_content
    assert "Kind: needs-approval" in approval_content
    assert "requires approved-for-review" in approval_content


def test_check_approval_step_with_rate_limited_author(tmp_path):
    """
    Test that the check-approval step script handles rate-limited authors correctly.
    
    The stub exits 1 and outputs:
        Issue #123
        Author: spammy-user
        Approved: False
        Kind: rate-limited
        Reason: rate limit exceeded (5/3 submissions in 24h)
    
    The step script should:
    - Exit 0
    - Write approved=false to GITHUB_OUTPUT
    - Write gate_kind=rate-limited to GITHUB_OUTPUT
    - Write gate_reason with the rate limit message to GITHUB_OUTPUT
    """
    script = extract_check_approval_step_script()
    
    # Create a stub script that mimics author_gating.py for a rate-limited author
    stub_script = tmp_path / "author_gating_stub.py"
    stub_script.write_text("""#!/usr/bin/env python3
import sys
print("Issue #123")
print("Author: spammy-user")
print("Approved: False")
print("Kind: rate-limited")
print("Reason: rate limit exceeded (5/3 submissions in 24h)")
sys.exit(1)
""")
    stub_script.chmod(0o755)
    
    # Create temp files for the test
    github_output = tmp_path / "github_output.txt"
    approval_txt = tmp_path / "approval.txt"
    
    # Prepare the test script
    full_script = prepare_test_script(script, stub_script, approval_txt, issue_num=123)
    
    script_file = tmp_path / "test_script.sh"
    script_file.write_text(full_script)
    script_file.chmod(0o755)
    
    # Run the script with GITHUB_OUTPUT set
    env = os.environ.copy()
    env['GITHUB_OUTPUT'] = str(github_output)
    
    result = subprocess.run(
        [str(script_file)],
        env=env,
        capture_output=True,
        text=True
    )
    
    # Assert the script exited 0
    assert result.returncode == 0, f"Script exited {result.returncode}, stderr: {result.stderr}"
    
    # Assert GITHUB_OUTPUT contains correct fields for a rate-limited author
    output_lines = github_output.read_text().strip().split('\n')
    assert 'approved=false' in output_lines, f"Expected approved=false in {output_lines}"
    assert 'gate_kind=rate-limited' in output_lines, f"Expected gate_kind=rate-limited in {output_lines}"
    
    output_text = github_output.read_text()
    assert 'gate_reason=' in output_text, f"Expected gate_reason in output"
    assert 'rate limit' in output_text or 'rate-limited' in output_text, \
        f"Expected rate limit keywords in output: {output_text}"


def test_check_approval_step_with_editorial_hold(tmp_path):
    """
    Test that the check-approval step script handles editorial-hold correctly.
    
    The stub exits 1 and outputs:
        Issue #200
        Author: controversial-author
        Approved: False
        Kind: editorial-hold
        Reason: editorial-hold label present
    
    The step script should handle this the same as any other gated case.
    """
    script = extract_check_approval_step_script()
    
    # Create a stub script that mimics author_gating.py for an editorial-hold issue
    stub_script = tmp_path / "author_gating_stub.py"
    stub_script.write_text("""#!/usr/bin/env python3
import sys
print("Issue #200")
print("Author: controversial-author")
print("Approved: False")
print("Kind: editorial-hold")
print("Reason: editorial-hold label present")
sys.exit(1)
""")
    stub_script.chmod(0o755)
    
    # Create temp files for the test
    github_output = tmp_path / "github_output.txt"
    approval_txt = tmp_path / "approval.txt"
    
    # Prepare the test script
    full_script = prepare_test_script(script, stub_script, approval_txt, issue_num=200)
    
    script_file = tmp_path / "test_script.sh"
    script_file.write_text(full_script)
    script_file.chmod(0o755)
    
    # Run the script with GITHUB_OUTPUT set
    env = os.environ.copy()
    env['GITHUB_OUTPUT'] = str(github_output)
    
    result = subprocess.run(
        [str(script_file)],
        env=env,
        capture_output=True,
        text=True
    )
    
    # Assert the script exited 0
    assert result.returncode == 0, f"Script exited {result.returncode}, stderr: {result.stderr}"
    
    # Assert GITHUB_OUTPUT contains correct fields
    output_lines = github_output.read_text().strip().split('\n')
    assert 'approved=false' in output_lines, f"Expected approved=false in {output_lines}"
    assert 'gate_kind=editorial-hold' in output_lines, f"Expected gate_kind=editorial-hold in {output_lines}"


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v"])
