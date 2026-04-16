#!/usr/bin/env python3
"""Summarize issue threads on buildngrowsv/pubroot-website:
- how many issues have comments
- who commented (bot pipeline run vs external humans)
- the actual human / external comments text so we can quote them in the retrospective
Uses `gh` CLI (already authenticated) to avoid hardcoding tokens.
"""
import json, subprocess, collections, sys

OWNER_REPO = "buildngrowsv/pubroot-website"

def gh(args):
    out = subprocess.check_output(["gh"] + args, text=True)
    return out

# 1. list all issues (open + closed). `--json comments` returns the comment
#    array, not a count; we count len() below.
listing = gh([
    "issue", "list", "--repo", OWNER_REPO,
    "--state", "all", "--limit", "300",
    "--json", "number,title,comments,state,author,createdAt,closedAt",
])
issues = json.loads(listing)

def ncomments(i):
    c = i.get("comments", [])
    return len(c) if isinstance(c, list) else int(c or 0)

print(f"Total issues: {len(issues)}")
with_comments = [i for i in issues if ncomments(i) > 0]
print(f"Issues with >=1 comment: {len(with_comments)}")
multi = [i for i in issues if ncomments(i) > 1]
print(f"Issues with >1 comment (plausible discussion): {len(multi)}")
print()
print("Top 20 by comment count:")
for i in sorted(issues, key=ncomments, reverse=True)[:20]:
    a = (i.get("author") or {}).get("login", "?")
    print(f"  #{i['number']:<4} comments={ncomments(i):<2} state={i['state']:<8} author={a:<22} {i['title'][:80]}")

# 2. for issues with comments, pull the actual comments.
#    We want to distinguish the automated review comment (posted by the issue author 'buildngrowsv'
#    or 'github-actions[bot]') from any external commenter.
external_comments = []
all_comments_log = []
for issue in with_comments:
    num = issue["number"]
    body = gh([
        "api",
        f"repos/{OWNER_REPO}/issues/{num}/comments",
        "--jq", "[.[] | {user: .user.login, body: .body, created_at: .created_at}]",
    ])
    try:
        comments = json.loads(body)
    except Exception:
        continue
    for c in comments:
        user = c.get("user", "?")
        all_comments_log.append((num, issue["title"], user, c.get("created_at", "?"), (c.get("body") or "")[:120]))
        if user in {"buildngrowsv", "github-actions[bot]", "github-actions"}:
            continue
        external_comments.append((num, issue["title"], user, c.get("created_at", "?"), c.get("body", "")))

# Who posts comments? (author distribution)
author_counts = collections.Counter(c[2] for c in all_comments_log)
print()
print("=== Comment author distribution (all comments) ===")
for u, n in author_counts.most_common():
    print(f"  {u:<25} {n}")

print()
print(f"=== External / non-pipeline comments: {len(external_comments)} ===")
for num, title, user, when, body in external_comments:
    snippet = (body or "").strip().replace("\n", " ")
    if len(snippet) > 200:
        snippet = snippet[:200] + "…"
    print(f"#{num} [{user} @ {when}] {title[:60]}")
    print(f"  > {snippet}")
    print()
