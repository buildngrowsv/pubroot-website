"""
conftest.py — Pytest configuration for _review_agent test suite

HISTORY:
    Created 2026-03-23 by Builder 4 to fix the import path issue
    flagged by Reviewer 17. Without this file, tests had to be run
    from within the _review_agent/ directory because the test files
    use bare imports (e.g., `from stage_1_parse_and_filter import ...`).

PURPOSE:
    Adds the _review_agent directory to sys.path so tests can be run
    from the repository root via `pytest _review_agent/` without
    ModuleNotFoundError. This is the standard pytest pattern for
    packages that aren't installed via pip.

RUNNING:
    # From repo root:
    pytest _review_agent/ -v
    # From _review_agent/ directory (still works):
    pytest -v
"""

import sys
import os

# -----------------------------------------------------------------------
# Add the _review_agent directory itself to sys.path so that bare imports
# like `from stage_1_parse_and_filter import ...` resolve correctly
# regardless of which directory pytest is invoked from.
#
# This is necessary because the review pipeline modules are not installed
# as a Python package — they're standalone scripts that import each other
# by filename. The conftest.py approach is the standard pytest solution
# for this pattern, recommended by the pytest docs.
# -----------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
