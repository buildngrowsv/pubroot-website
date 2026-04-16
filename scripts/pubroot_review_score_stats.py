#!/usr/bin/env python3
"""Quick stats over reviews/ for the Pubroot study."""
import json, glob, os, collections, statistics

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
review_paths = sorted(glob.glob(os.path.join(root, "reviews", "*", "review.json")))

scores, verdicts, badges = [], collections.Counter(), collections.Counter()
confs = collections.defaultdict(list)
claim_counts, verified_counts = [], []
rows = []

for p in review_paths:
    try:
        d = json.load(open(p))
    except Exception as e:
        print(f"ERR {p}: {e}")
        continue
    s = d.get("score")
    if isinstance(s, (int, float)):
        scores.append(float(s))
    verdicts[d.get("verdict", "?")] += 1
    badges[d.get("badge", "?")] += 1
    for k, v in (d.get("confidence") or {}).items():
        if isinstance(v, (int, float)):
            confs[k].append(float(v))
    claims = d.get("claims") or []
    claim_counts.append(len(claims))
    verified_counts.append(sum(1 for c in claims if c.get("verified")))
    rows.append((d.get("paper_id", "?"), s, d.get("verdict", "?"), d.get("badge", "?"), len(claims)))

print(f"Reviews analyzed: {len(review_paths)}")
print(f"Scores: mean={statistics.mean(scores):.2f} median={statistics.median(scores):.2f} min={min(scores):.1f} max={max(scores):.1f}")
print(f"Score distribution (rounded to 0.5):")
buckets = collections.Counter(round(x * 2) / 2 for x in scores)
for k in sorted(buckets):
    print(f"  {k:>4.1f}  {buckets[k]:>3}  {'#' * buckets[k]}")
print(f"\nVerdicts: {dict(verdicts)}")
print(f"Badges:   {dict(badges)}")
print()
print("Per-dimension confidence means (of reviews that report the dim):")
for k in ["methodology", "factual_accuracy", "novelty", "code_quality", "writing_quality", "reproducibility"]:
    vs = confs.get(k, [])
    if vs:
        print(f"  {k:<18} n={len(vs):>3}  mean={statistics.mean(vs):.3f}  median={statistics.median(vs):.3f}")
print()
print(f"Total verified claims across all reviews: {sum(verified_counts)} / {sum(claim_counts)} total claims ({sum(verified_counts)/max(1,sum(claim_counts))*100:.1f}% verified)")
print(f"Avg claims per review: {statistics.mean(claim_counts):.1f}")
print()
print("Full per-review scoreboard (sorted by score desc):")
for row in sorted(rows, key=lambda r: (r[1] or 0), reverse=True):
    print(f"  {row[0]:<10} score={row[1]!s:<5} verdict={row[2]:<10} badge={row[3]:<18} claims={row[4]}")
