"""
seo_gaming_screen.py — screen gated outsider submissions for likely SEO /
reputation gaming (decision D-26, 17 Nov 2026).

POLICY (editorial guidelines):
    Submissions whose likely primary purpose is promotion, backlinks, or
    reputation-building for a product, company or person, rather than a
    research contribution, are rejected. Disclosure of an affiliation does
    not cure this.

ORIGIN:
    Adam King, 17 Nov 2026, on issue #323 (a synthetic pagination "benchmark"
    from an AgentSEO co-founder with a two-minute-old repo who was running a
    same-week directory-listing campaign): "We need a rule against likely seo
    gaming to reject these." Spec: /workspace/pubroot/systems/specs/seo-gaming-rule.md

SIGNALS (each is boolean; deliberately conservative heuristics):
    S1 affiliation   — author states a commercial role (founder, CEO, employee,
                       "our product") or their GitHub profile company is named
                       in the paper.
    S2 thin-account  — supporting repo created < 24h before the submission AND
                       the account is thin (<= 3 public repos or < 30 days old).
                       Without a repo: account < 7 days old with no public repos.
    S3 listing-campaign — in the 30 days before submitting, the author opened
                       >= 3 issues/PRs/comments on other people's repos that are
                       listing / directory / "add X" requests, and those make up
                       at least half of that outside activity.
    S4 low-novelty   — the paper describes its own data as synthetic/constructed
                       (>= 2 distinct terms) AND says no real/live/production
                       system was evaluated.
    S5 brand-links   — links to the affiliated brand's domain, the author's
                       profile site, or 2+ of the author's other repos; or the
                       affiliated brand is named >= 2 times outside the
                       disclosure section.
    S6 cheap-generation — placeholder text, empty/mangled links, or the same
                       source URL listed more than once in the references.

DECISION:
    2+ signals  -> "reject": labels `rejected` + `seo-gaming`, short neutral
                   comment, issue closed as not planned.
    1 signal    -> "flag": label `seo-gaming-flag`; the signal is written to the
                   job summary and passed to the Stage 4 reviewer prompt.
    0 signals   -> "pass".
    Maintainers, collaborators, allowlisted authors, Pubroot's own agents
    (buildngrowsv) and bots are ALWAYS exempt -> "exempt".
    Any API error fails OPEN (decision "error" is treated like "pass").

USAGE:
    python seo_gaming_screen.py screen <issue_number> [--apply] [--json out.json]
        [--ignore-exemptions]   (dry runs only; never combined with --apply)

ENVIRONMENT:
    GITHUB_TOKEN, GITHUB_REPOSITORY, optional GITHUB_OUTPUT / GITHUB_STEP_SUMMARY
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

API = "https://api.github.com"

# Pubroot's own maintainer / agent accounts. These are never auto-rejected,
# whatever their association on a given issue says.
MAINTAINER_LOGINS = {"buildngrowsv"}
TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

REJECT_THRESHOLD = 2

SIGNAL_NAMES = {
    "S1": "affiliated with a commercial product in the topic area",
    "S2": "new or thin account with a freshly created repo",
    "S3": "same-period activity is mainly listing/marketing requests",
    "S4": "synthetic/constructed data with no real-system evaluation",
    "S5": "brand mentions or backlinks to affiliated sites",
    "S6": "signs of cheap generation (placeholders, mangled or duplicate citations)",
}

REJECT_COMMENT = (
    "<!-- pubroot:screen-rejected -->\n"
    "## Submission closed at screening\n\n"
    "Thanks for your interest in Pubroot. This submission was closed before review "
    "under our editorial policy on promotional submissions: submissions whose likely "
    "primary purpose is promotion, backlinks, or reputation-building for a product, "
    "company or person, rather than a research contribution, are not reviewed. "
    "Disclosing an affiliation does not change this.\n\n"
    "Policy: https://pubroot.com/editorial-guidelines/#promotional-submissions\n\n"
    "If you think this was a mistake, reply here and a maintainer will take a look."
)

# --- text heuristics ---------------------------------------------------------

ROLE_RE = re.compile(
    r"\b(co-?founder|founder|ceo|cto|coo|chief [a-z]+ officer|employee of|employed (?:by|at)|"
    r"works? (?:at|for)|head of [a-z]+ at|our (?:company|product|startup|api|platform|tool|service|saas))\b",
    re.I,
)
# "co-founder of AgentSEO" / "CEO at Acme" -> brand
BRAND_RE = re.compile(
    r"\b(?i:co-?founder|founder|ceo|cto|coo|employee|head of [a-z]+)\s+(?i:of|at)\s+([A-Z][\w.\-]{1,40})"
)
ACADEMIC_RE = re.compile(r"\b(university|institute|college|laborator|school of)\b", re.I)

SYNTHETIC_TERMS = ["synthetic", "constructed", "fixture", "simulated", "toy example", "mock data", "hypothetical"]
NO_REAL_EVAL_RE = re.compile(
    r"\bno (?:live|real|production|real-world)\b[^.\n]{0,120}?\b(?:was|were)\s+(?:tested|called|used|evaluated|measured|benchmarked)"
    r"|\bnot (?:a |an )?(?:live|real|production|real-world) (?:comparison|evaluation|benchmark|test)"
    r"|\bno (?:live|real|production|real-world) (?:provider|system|traffic|data|api)",
    re.I,
)
LISTING_RE = re.compile(
    r"\b(add|adding|list|listing|submit|submission|suggest|suggestion|import|vendor|catalog|catalogue|"
    r"directory|registry|awesome|include)\b",
    re.I,
)
PLACEHOLDER_RE = re.compile(
    r"lorem ipsum|\[citation needed\]|\bTODO\b|as an ai language model|\[insert [^\]]+\]|\bxx+\b reference",
    re.I,
)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
URL_RE = re.compile(r"https?://[^\s)>\]]+")

NEUTRAL_DOMAINS = (
    "github.com", "raw.githubusercontent.com", "githubusercontent.com", "arxiv.org", "doi.org",
    "pubroot.com", "creativecommons.org", "wikipedia.org", "rfc-editor.org", "ietf.org",
    "semanticscholar.org", "zenodo.org", "huggingface.co", "pypi.org", "npmjs.com",
)


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _section(body: str, heading_keyword: str) -> str:
    """Return the text of the first markdown section whose heading contains keyword."""
    m = re.search(rf"^#+\s*[^\n]*{heading_keyword}[^\n]*\n(.*?)(?=^#+\s|\Z)", body, re.I | re.M | re.S)
    return m.group(1) if m else ""


def _supporting_repo(body: str) -> Optional[str]:
    sec = _section(body, "Supporting Repository URL")
    m = re.search(r"github\.com/([\w.\-]+/[\w.\-]+)", sec or "")
    if not m:
        return None
    return m.group(1).removesuffix(".git").rstrip("/")


def extract_brands(body: str, profile_company: str = "") -> List[str]:
    brands = []
    for b in BRAND_RE.findall(body or ""):
        b = b.rstrip(".,;:")
        if b and not ACADEMIC_RE.search(b) and b.lower() not in ("the", "a", "an"):
            brands.append(b)
    company = (profile_company or "").strip().lstrip("@").strip()
    if company and not ACADEMIC_RE.search(company):
        brands.append(company)
    seen, out = set(), []
    for b in brands:
        if b.lower() not in seen:
            seen.add(b.lower())
            out.append(b)
    return out


# --- signals -----------------------------------------------------------------

def score_signals(ctx: Dict) -> List[Dict]:
    """
    Pure function: score the six signals from a context dict.

    ctx keys: body, author, issue_created_at, user (GitHub user JSON or {}),
              repo (supporting repo JSON or {}), events (author public events list)
    Returns a list of fired signals: {"id", "name", "evidence"}.
    """
    body = ctx.get("body") or ""
    author = (ctx.get("author") or "").lower()
    user = ctx.get("user") or {}
    repo = ctx.get("repo") or {}
    events = ctx.get("events") or []
    submitted = _parse_time(ctx.get("issue_created_at")) or datetime.now(timezone.utc)
    fired: List[Dict] = []

    def fire(sid, evidence):
        fired.append({"id": sid, "name": SIGNAL_NAMES[sid], "evidence": evidence})

    brands = extract_brands(body, user.get("company") or "")

    # S1 affiliation
    disclosure = _section(body, "disclosure") or _section(body, "conflict") or ""
    role_hits = [m.group(0) for m in ROLE_RE.finditer(body)]
    role_hits = [h for h in role_hits if not ACADEMIC_RE.search(body[max(0, body.find(h) - 0): body.find(h) + 120])]
    company = (user.get("company") or "").strip().lstrip("@").strip()
    if role_hits:
        fire("S1", f"commercial role stated: '{role_hits[0]}'" + (f" ({', '.join(brands)})" if brands else ""))
    elif company and not ACADEMIC_RE.search(company) and company.lower() in body.lower():
        fire("S1", f"profile company '{company}' is named in the paper")

    # S2 new/thin account + fresh repo
    acct_created = _parse_time(user.get("created_at"))
    acct_age_days = (submitted - acct_created).days if acct_created else None
    public_repos = user.get("public_repos")
    followers = user.get("followers")
    # Followers alone are not a thin-account signal (many real authors have few).
    thin = (
        (public_repos is not None and public_repos <= 3)
        or (acct_age_days is not None and acct_age_days < 30)
    )
    repo_created = _parse_time(repo.get("created_at"))
    if repo_created is not None:
        lead = submitted - repo_created
        if timedelta(0) - timedelta(minutes=5) <= lead < timedelta(hours=24) and thin:
            mins = int(lead.total_seconds() // 60)
            fire("S2", f"repo created {mins} min before submission; account has {public_repos} public repos, "
                       f"{followers} followers")
    elif acct_age_days is not None and acct_age_days < 7 and not public_repos:
        fire("S2", f"account {acct_age_days} days old with no public repos")

    # S3 listing campaign (30 days before submission, other people's repos)
    window_start = submitted - timedelta(days=30)
    outside, listing = 0, []
    for ev in events:
        t = _parse_time(ev.get("created_at"))
        if not t or t < window_start or t > submitted + timedelta(hours=1):
            continue
        repo_name = (ev.get("repo") or {}).get("name", "")
        owner = repo_name.split("/")[0].lower() if repo_name else ""
        if owner == author or repo_name.lower() == "buildngrowsv/pubroot-website":
            continue
        etype = ev.get("type")
        payload = ev.get("payload") or {}
        if etype == "IssuesEvent" and payload.get("action") == "opened":
            title = (payload.get("issue") or {}).get("title", "")
        elif etype == "PullRequestEvent" and payload.get("action") == "opened":
            title = (payload.get("pull_request") or {}).get("title", "")
        elif etype == "IssueCommentEvent":
            title = (payload.get("issue") or {}).get("title", "")
        else:
            continue
        outside += 1
        brand_hit = any(b.lower() in title.lower() for b in brands)
        if LISTING_RE.search(title) or brand_hit:
            listing.append(f"{repo_name}: {title[:70]}")
    if len(listing) >= 3 and len(listing) * 2 >= outside:
        fire("S3", f"{len(listing)} of {outside} outside issues/PRs in 30 days are listing requests, e.g. "
                   + "; ".join(listing[:3]))

    # S4 synthetic data + explicit no-real-system evaluation
    low = body.lower()
    syn = [t for t in SYNTHETIC_TERMS if t in low]
    no_real = NO_REAL_EVAL_RE.search(body)
    if len(syn) >= 2 and no_real:
        fire("S4", f"self-described {', '.join(syn)} data; '{no_real.group(0)[:80]}'")

    # S5 brand links / backlinks / repeated brand mentions
    urls = URL_RE.findall(body)
    support = (_supporting_repo(body) or "").lower()
    blog_host = urlparse(user.get("blog") if "://" in (user.get("blog") or "") else
                         "https://" + (user.get("blog") or "")).netloc.lower().removeprefix("www.")
    backlinks = []
    other_author_repos = set()
    for u in urls:
        p = urlparse(u)
        host = p.netloc.lower().removeprefix("www.")
        path = p.path.strip("/").lower()
        if blog_host and host == blog_host:
            backlinks.append(u)
        elif any(b.lower().replace(" ", "") in host.replace("-", "") for b in brands if len(b) >= 4):
            backlinks.append(u)
        elif host == "github.com" and author and path.startswith(author + "/"):
            repo_path = "/".join(path.split("/")[:2])
            if repo_path not in (support, "buildngrowsv/pubroot-website"):
                other_author_repos.add(repo_path)
    # Linking one earlier repo of your own is normal prior work; 2+ looks like backlinking.
    if len(other_author_repos) >= 2:
        backlinks.extend(f"https://github.com/{r}" for r in sorted(other_author_repos))
    outside_disclosure = body.replace(disclosure, "") if disclosure else body
    brand_mentions = {b: len(re.findall(re.escape(b), outside_disclosure, re.I)) for b in brands}
    heavy = {b: n for b, n in brand_mentions.items() if n >= 2}
    if backlinks:
        fire("S5", f"links to affiliated sites: {', '.join(sorted(set(backlinks))[:3])}")
    elif heavy:
        fire("S5", "affiliated brand named outside the disclosure: "
                   + ", ".join(f"{b} x{n}" for b, n in heavy.items()))

    # S6 cheap generation
    reasons = []
    ph = PLACEHOLDER_RE.search(body)
    if ph:
        reasons.append(f"placeholder '{ph.group(0)}'")
    empty = [t for t, u in MD_LINK_RE.findall(body) if not u.strip() or u.strip() in ("#", "http://", "https://")]
    if empty:
        reasons.append(f"{len(empty)} empty link(s)")
    sources = _section(body, "sources") or _section(body, "references") or ""
    src_urls = URL_RE.findall(sources)
    dupes = {u for u in src_urls if src_urls.count(u) > 1}
    if dupes:
        reasons.append(f"duplicate references: {', '.join(sorted(dupes)[:2])}")
    if reasons:
        fire("S6", "; ".join(reasons))

    return fired


def decide(signals: List[Dict]) -> str:
    if len(signals) >= REJECT_THRESHOLD:
        return "reject"
    if len(signals) == 1:
        return "flag"
    return "pass"


# --- GitHub I/O ----------------------------------------------------------------

def _headers(token: str) -> Dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def _get(url: str, token: str, params: Optional[Dict] = None):
    r = requests.get(url, headers=_headers(token), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def is_exempt(issue: Dict, repo_root: str) -> Optional[str]:
    login = ((issue.get("user") or {}).get("login") or "").lower()
    if not login:
        return "unknown author"
    if login in MAINTAINER_LOGINS:
        return f"maintainer/agent account @{login}"
    if (issue.get("user") or {}).get("type") == "Bot" or login.endswith("[bot]"):
        return "bot account"
    if issue.get("author_association") in TRUSTED_ASSOCIATIONS:
        return f"repo {issue.get('author_association', '').lower()}"
    try:
        from author_gating import is_on_allowlist
        if is_on_allowlist(login, repo_root):
            return "on review allowlist"
    except Exception:
        pass
    return None


def gather_context(token: str, full_repo: str, issue: Dict) -> Dict:
    body = issue.get("body") or ""
    author = (issue.get("user") or {}).get("login", "")
    user = _get(f"{API}/users/{author}", token) if author else {}
    repo = {}
    support = _supporting_repo(body)
    if support:
        try:
            repo = _get(f"{API}/repos/{support}", token)
        except requests.HTTPError:
            repo = {}
    events = []
    if author:
        for page in (1, 2, 3):
            batch = _get(f"{API}/users/{author}/events/public", token, {"per_page": 100, "page": page})
            events.extend(batch)
            if len(batch) < 100:
                break
    return {
        "body": body,
        "author": author,
        "issue_created_at": issue.get("created_at"),
        "user": user,
        "repo": repo,
        "events": events,
    }


def screen_issue(issue_number: int, token: str, full_repo: str, repo_root: str,
                 ignore_exemptions: bool = False) -> Dict:
    issue = _get(f"{API}/repos/{full_repo}/issues/{issue_number}", token)
    exempt = None if ignore_exemptions else is_exempt(issue, repo_root)
    result = {
        "issue": issue_number,
        "author": (issue.get("user") or {}).get("login"),
        "state": issue.get("state"),
        "labels": [l.get("name") for l in issue.get("labels", [])],
        "exempt": exempt,
    }
    if exempt:
        result.update({"signals": [], "count": 0, "decision": "exempt"})
        return result
    ctx = gather_context(token, full_repo, issue)
    signals = score_signals(ctx)
    result.update({"signals": signals, "count": len(signals), "decision": decide(signals)})
    return result


def apply_decision(result: Dict, token: str, full_repo: str) -> str:
    """Act on a screening result. Idempotent; never acts on closed issues."""
    n = result["issue"]
    if result["decision"] not in ("reject", "flag"):
        return "no action"
    if result.get("exempt"):
        return "no action (exempt)"
    if result.get("state") != "open":
        return "no action (issue not open)"
    h = _headers(token)
    base = f"{API}/repos/{full_repo}"

    def ensure_label(name, color, desc):
        requests.post(f"{base}/labels", headers=h, json={"name": name, "color": color, "description": desc},
                      timeout=15)  # 422 if it exists; fine

    if result["decision"] == "flag":
        ensure_label("seo-gaming-flag", "fbca04", "One SEO/reputation-gaming signal; reviewer should check (D-26)")
        requests.post(f"{base}/issues/{n}/labels", headers=h, json={"labels": ["seo-gaming-flag"]},
                      timeout=15).raise_for_status()
        return "flagged"

    if "seo-gaming" in (result.get("labels") or []):
        return "no action (already rejected)"
    ensure_label("rejected", "d73a4a", "Submission rejected")
    ensure_label("seo-gaming", "b60205", "Closed at screening: likely SEO/reputation gaming (D-26)")
    requests.post(f"{base}/issues/{n}/labels", headers=h, json={"labels": ["rejected", "seo-gaming"]},
                  timeout=15).raise_for_status()
    for stale in ("pending-review", "awaiting-approval"):
        requests.delete(f"{base}/issues/{n}/labels/{stale}", headers=h, timeout=15)
    requests.post(f"{base}/issues/{n}/comments", headers=h, json={"body": REJECT_COMMENT},
                  timeout=15).raise_for_status()
    requests.patch(f"{base}/issues/{n}", headers=h, json={"state": "closed", "state_reason": "not_planned"},
                   timeout=15).raise_for_status()
    return "rejected and closed"


def _summary_markdown(result: Dict, action: str) -> str:
    lines = [f"### SEO-gaming screen: issue #{result['issue']} (@{result.get('author')})",
             f"Decision: **{result['decision']}** ({result.get('count', 0)} signal(s)). Action: {action}."]
    if result.get("exempt"):
        lines.append(f"Exempt: {result['exempt']}")
    for s in result.get("signals", []):
        lines.append(f"- {s['id']} {s['name']}: {s['evidence']}")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    if len(argv) < 3 or argv[1] != "screen":
        print(__doc__)
        return 2
    issue_number = int(argv[2])
    apply = "--apply" in argv
    ignore = "--ignore-exemptions" in argv
    if apply and ignore:
        print("ERROR: --ignore-exemptions is for dry runs only")
        return 2
    json_out = argv[argv.index("--json") + 1] if "--json" in argv else None
    token = os.environ.get("GITHUB_TOKEN", "")
    full_repo = os.environ.get("GITHUB_REPOSITORY", "")
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    try:
        result = screen_issue(issue_number, token, full_repo, repo_root, ignore_exemptions=ignore)
        action = apply_decision(result, token, full_repo) if apply else "dry run"
    except Exception as e:  # fail open
        result = {"issue": issue_number, "decision": "error", "signals": [], "count": 0, "error": str(e)}
        action = f"none (screen error, failing open: {e})"
    print(json.dumps(result, indent=2))
    print(f"Action: {action}")
    if json_out:
        with open(json_out, "w") as f:
            json.dump(result, f, indent=2)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"decision={result['decision']}\n")
            f.write(f"signal_count={result.get('count', 0)}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(_summary_markdown(result, action))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
