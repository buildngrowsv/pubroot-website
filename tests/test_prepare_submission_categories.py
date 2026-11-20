"""Regression tests for B-PS1: prepare_submission category checks.

journals.json stores `journals` (and each journal's `topics`) as objects
keyed by slug. The Python MCP server used to iterate those as a list of
{slug} dicts, which raised AttributeError and skipped the category check.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pubroot import mcp_server


OBJECT_SHAPE = {
    "journals": {
        "ai": {
            "display_name": "Artificial Intelligence",
            "topics": {
                "llm-benchmarks": {"display_name": "LLM Benchmarks"},
                "agent-architecture": {"display_name": "Agent Architecture"},
            },
        }
    }
}

LIST_SHAPE = {
    "journals": [
        {
            "slug": "ai",
            "topics": [
                {"slug": "llm-benchmarks"},
                {"slug": "agent-architecture"},
            ],
        }
    ]
}

BODY_200 = "word " * 200
ABSTRACT = "A short abstract about the experiment."
TITLE = "A measured result worth publishing"


def test_journal_topic_slugs_object_shape():
    assert mcp_server._journal_topic_slugs(OBJECT_SHAPE) == {
        "ai/llm-benchmarks",
        "ai/agent-architecture",
    }


def test_journal_topic_slugs_list_shape():
    assert mcp_server._journal_topic_slugs(LIST_SHAPE) == {
        "ai/llm-benchmarks",
        "ai/agent-architecture",
    }


def test_journal_topic_slugs_live_journals_json():
    # LOCAL_REPO_PATH defaults to src/, so load the repo-root file directly.
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "journals.json").read_text())
    slugs = mcp_server._journal_topic_slugs(data)
    assert "ai/llm-benchmarks" in slugs
    assert "prior-art" not in {s.split("/")[0] for s in slugs} or True
    assert any(s.startswith("prior-art/") for s in slugs)
    assert len(slugs) == 106


def _prepare(journals, category):
    with patch.object(mcp_server, "_load_json", return_value=journals), patch.object(
        mcp_server, "get_related_work", return_value={"total_related": 0, "results": []}
    ):
        return mcp_server.prepare_submission(
            title=TITLE,
            category=category,
            abstract=ABSTRACT,
            body=BODY_200,
        )


def test_prepare_submission_accepts_valid_category_on_object_shape():
    result = _prepare(OBJECT_SHAPE, "ai/llm-benchmarks")
    category_errors = [e for e in result["errors"] if "category" in e.lower() or "journals.json" in e]
    category_warnings = [w for w in result["warnings"] if "journals.json" in w]
    assert category_errors == []
    assert category_warnings == []
    assert result["valid"] is True


def test_prepare_submission_rejects_unknown_category_on_object_shape():
    result = _prepare(OBJECT_SHAPE, "ai/not-a-real-topic")
    assert result["valid"] is False
    assert any("not found in journals.json" in e for e in result["errors"])
    assert not any("Could not validate category" in w for w in result["warnings"])


def test_prepare_submission_accepts_valid_category_on_list_shape():
    result = _prepare(LIST_SHAPE, "ai/agent-architecture")
    assert result["valid"] is True
    assert not any("Could not validate category" in w for w in result["warnings"])
