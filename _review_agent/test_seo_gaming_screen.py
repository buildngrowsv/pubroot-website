"""
Tests for seo_gaming_screen.py (D-26: reject likely SEO / reputation gaming).

The #323 fixture is the public data from issue #323 (closed as not planned on
17 Nov 2026): body, author profile counts, repo creation time, and the author's
public listing-request events from the week before submitting.
"""

import copy
import json
import os
from unittest.mock import patch

import seo_gaming_screen as s
from stage_4_build_review_prompt import _format_promotion_criterion, build_review_prompt

HERE = os.path.dirname(__file__)
FIXTURE = json.load(open(os.path.join(HERE, "test_fixtures", "seo_screen_issue_323.json")))

CLEAN_BODY = """### Article Title

Measuring cache hit rates in a production CDN

### Category

se/devops

### Article Body

We measured cache hit rates across 14 production edge regions for 30 days of
real traffic. Hit rate rose from 81% to 93% after normalising query strings.

## Sources

- [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111)

### Supporting Repository URL

https://github.com/alice/cdn-cache-study
"""


def clean_ctx():
    return {
        "body": CLEAN_BODY,
        "author": "alice",
        "issue_created_at": "2026-11-16T12:00:00Z",
        "user": {"public_repos": 25, "followers": 2, "created_at": "2019-01-01T00:00:00Z", "company": None, "blog": ""},
        "repo": {"created_at": "2026-06-01T00:00:00Z"},
        "events": [],
    }


def ids(signals):
    return sorted(x["id"] for x in signals)


def test_issue_323_scores_reject():
    sig = s.score_signals(FIXTURE)
    assert ids(sig) == ["S1", "S2", "S3", "S4"]
    assert s.decide(sig) == "reject"


def test_clean_outsider_paper_passes():
    sig = s.score_signals(clean_ctx())
    assert sig == []
    assert s.decide(sig) == "pass"


def test_disclosed_affiliation_alone_is_only_a_flag():
    ctx = clean_ctx()
    ctx["body"] += "\n## Author disclosure\n\nAlice is co-founder of Edgeworks, a CDN vendor.\n"
    sig = s.score_signals(ctx)
    assert ids(sig) == ["S1"]
    assert s.decide(sig) == "flag"


def test_academic_affiliation_is_not_a_signal():
    ctx = clean_ctx()
    ctx["body"] += "\n## Author disclosure\n\nAlice works at the University of Leeds.\n"
    assert s.score_signals(ctx) == []


def test_few_followers_alone_is_not_thin():
    ctx = clean_ctx()
    ctx["repo"] = {"created_at": "2026-11-16T11:40:00Z"}  # fresh repo, but established account
    assert "S2" not in ids(s.score_signals(ctx))


def test_fresh_repo_on_thin_account_fires_s2():
    ctx = clean_ctx()
    ctx["repo"] = {"created_at": "2026-11-16T11:58:00Z"}
    ctx["user"]["public_repos"] = 1
    assert "S2" in ids(s.score_signals(ctx))


def test_listing_campaign_needs_three_and_majority():
    ctx = clean_ctx()
    ev = lambda repo, title: {"type": "IssuesEvent", "repo": {"name": repo}, "created_at": "2026-11-10T00:00:00Z",
                              "payload": {"action": "opened", "issue": {"title": title}}}
    ctx["events"] = [ev("x/awesome-cdn", "Add Edgeworks"), ev("y/catalog", "Add Edgeworks API")]
    assert "S3" not in ids(s.score_signals(ctx))
    ctx["events"].append(ev("z/directory", "Listing request: Edgeworks"))
    assert "S3" in ids(s.score_signals(ctx))
    ctx["events"] += [ev(f"o/r{i}", "Fix crash on startup") for i in range(4)]
    assert "S3" not in ids(s.score_signals(ctx))  # listing requests no longer the majority


def test_backlinks_to_brand_domain_fire_s5():
    ctx = clean_ctx()
    ctx["body"] += "\n## Author disclosure\n\nAlice is CEO of Edgeworks.\n\nTry it at https://edgeworks.io/signup\n"
    assert {"S1", "S5"} <= set(ids(s.score_signals(ctx)))


def test_one_other_own_repo_link_is_fine_but_two_fire_s5():
    ctx = clean_ctx()
    ctx["body"] += "\nPrior work: https://github.com/alice/old-study\n"
    assert "S5" not in ids(s.score_signals(ctx))
    ctx["body"] += "\nSee also https://github.com/alice/product-landing\n"
    assert "S5" in ids(s.score_signals(ctx))


def test_placeholder_and_duplicate_refs_fire_s6():
    ctx = clean_ctx()
    ctx["body"] = ctx["body"].replace(
        "- [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111)",
        "- [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111)\n- [RFC](https://www.rfc-editor.org/rfc/rfc9111)\n- [x]()",
    )
    assert "S6" in ids(s.score_signals(ctx))


def test_maintainer_and_agent_accounts_are_exempt():
    assert s.is_exempt({"user": {"login": "buildngrowsv"}, "author_association": "NONE"}, HERE)
    assert s.is_exempt({"user": {"login": "someone"}, "author_association": "COLLABORATOR"}, HERE)
    assert s.is_exempt({"user": {"login": "dependabot[bot]", "type": "Bot"}}, HERE)
    assert s.is_exempt({"user": {"login": "danielmartinSR"}, "author_association": "NONE"}, HERE) is None


def test_screen_issue_exempt_author_never_rejected():
    issue = {"user": {"login": "buildngrowsv"}, "author_association": "OWNER", "state": "open", "labels": [],
             "body": FIXTURE["body"]}
    with patch.object(s, "_get", return_value=issue):
        r = s.screen_issue(1, "t", "o/r", HERE)
    assert r["decision"] == "exempt" and r["signals"] == []
    assert s.apply_decision(r, "t", "o/r") == "no action"


def test_apply_never_touches_closed_issue():
    r = {"issue": 323, "decision": "reject", "state": "closed", "exempt": None, "labels": []}
    with patch.object(s.requests, "post") as post, patch.object(s.requests, "patch") as p:
        assert "not open" in s.apply_decision(r, "t", "o/r")
        post.assert_not_called(); p.assert_not_called()


def test_apply_reject_labels_comments_and_closes_not_planned():
    r = {"issue": 9, "decision": "reject", "state": "open", "exempt": None, "labels": ["submission"]}
    with patch.object(s.requests, "post") as post, patch.object(s.requests, "patch") as p, \
            patch.object(s.requests, "delete"):
        assert s.apply_decision(r, "t", "o/r") == "rejected and closed"
    label_calls = [c for c in post.call_args_list if c.args[0].endswith("/issues/9/labels")]
    assert label_calls[0].kwargs["json"] == {"labels": ["rejected", "seo-gaming"]}
    comment = [c for c in post.call_args_list if c.args[0].endswith("/comments")][0].kwargs["json"]["body"]
    assert "promotional" in comment and "AgentSEO" not in comment
    assert p.call_args.kwargs["json"] == {"state": "closed", "state_reason": "not_planned"}


def test_screen_error_fails_open(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    with patch.object(s, "screen_issue", side_effect=RuntimeError("boom")):
        assert s.main(["x", "screen", "5", "--apply"]) == 0
    assert "decision=error" in (tmp_path / "out").read_text()


def test_stage4_prompt_has_promotional_intent_criterion_and_signals():
    text = _format_promotion_criterion({"signals": [{"id": "S1", "name": "affil", "evidence": "co-founder"}]})
    assert "PROMOTIONAL INTENT" in text and "Disclosure of an affiliation does not cure this" in text
    assert "S1: affil" in text
    assert "flagged" not in _format_promotion_criterion(None)


def test_stage4_full_prompt_includes_rule_and_field(tmp_path):
    prompt = build_review_prompt(
        parsed_submission={"title": "t", "category": "se/x", "body": "b", "abstract": "a"},
        novelty_results={}, repo_data={}, repo_root=str(tmp_path), paper_id="2026-999",
    )
    assert '"promotional_intent"' in prompt
    assert "PROMOTIONAL INTENT OVERRIDES RULE 8" in prompt
