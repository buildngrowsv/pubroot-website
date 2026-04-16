#!/usr/bin/env python3
"""Pull GA4 (top pages, countries, sources) + GSC (top queries, pages) for
pubroot.com and dump a readable report for the retrospective."""
import json, subprocess, urllib.request, urllib.parse, sys

def shell(cmd):
    return subprocess.check_output(cmd, text=True, shell=True).strip()

GA4_TOKEN = shell("/Users/ak/UserRoot/tmp/google-oauth-get-access-token.sh --surface ga4 2>/dev/null | tail -n 1")
GSC_TOKEN = shell("/Users/ak/UserRoot/tmp/google-oauth-get-access-token.sh --surface search-console 2>/dev/null | tail -n 1")

GA4_PROPERTY = "properties/531004173"
GSC_SITE = "sc-domain:pubroot.com"


def ga4(body):
    req = urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/{GA4_PROPERTY}:runReport",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {GA4_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def gsc(body):
    site_encoded = urllib.parse.quote(GSC_SITE, safe="")
    req = urllib.request.Request(
        f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_encoded}/searchAnalytics/query",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {GSC_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def fmt_ga_rows(resp, dim_names, metric_names):
    rows = resp.get("rows") or []
    out = []
    for r in rows:
        dims = [d["value"] for d in r.get("dimensionValues", [])]
        mets = [m["value"] for m in r.get("metricValues", [])]
        out.append(dict(zip(dim_names, dims)) | dict(zip(metric_names, mets)))
    return out


# --- GA4 reports ---
print("=" * 70)
print("GA4 (property Pubroot, since property creation 2026-04-02)")
print("=" * 70)

# Top pages by pageview (90d window, which really covers creation → now)
resp = ga4({
    "dateRanges": [{"startDate": "90daysAgo", "endDate": "today"}],
    "dimensions": [{"name": "pagePath"}],
    "metrics": [{"name": "screenPageViews"}, {"name": "totalUsers"}, {"name": "averageSessionDuration"}],
    "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": True}],
    "limit": 20,
})
print("\nTOP PAGES (by pageviews):")
for row in fmt_ga_rows(resp, ["pagePath"], ["pageviews", "users", "avg_sess_sec"]):
    path = row["pagePath"][:60]
    print(f"  {row['pageviews']:>4}  users={row['users']:>3}  {path}")

# Countries
resp = ga4({
    "dateRanges": [{"startDate": "90daysAgo", "endDate": "today"}],
    "dimensions": [{"name": "country"}],
    "metrics": [{"name": "totalUsers"}, {"name": "sessions"}],
    "orderBys": [{"metric": {"metricName": "totalUsers"}, "desc": True}],
    "limit": 15,
})
print("\nTOP COUNTRIES:")
for row in fmt_ga_rows(resp, ["country"], ["users", "sessions"]):
    print(f"  users={row['users']:>3} sessions={row['sessions']:>3}  {row['country']}")

# Traffic sources
resp = ga4({
    "dateRanges": [{"startDate": "90daysAgo", "endDate": "today"}],
    "dimensions": [{"name": "sessionSource"}, {"name": "sessionMedium"}],
    "metrics": [{"name": "sessions"}, {"name": "totalUsers"}],
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    "limit": 15,
})
print("\nTOP TRAFFIC SOURCES:")
for row in fmt_ga_rows(resp, ["source", "medium"], ["sessions", "users"]):
    print(f"  sessions={row['sessions']:>3} users={row['users']:>3}  {row['source']} / {row['medium']}")

# Device category
resp = ga4({
    "dateRanges": [{"startDate": "90daysAgo", "endDate": "today"}],
    "dimensions": [{"name": "deviceCategory"}],
    "metrics": [{"name": "sessions"}, {"name": "totalUsers"}],
})
print("\nDEVICE MIX:")
for row in fmt_ga_rows(resp, ["device"], ["sessions", "users"]):
    print(f"  sessions={row['sessions']:>3} users={row['users']:>3}  {row['device']}")

# --- GSC reports ---
print()
print("=" * 70)
print("Search Console (sc-domain:pubroot.com, last 90d)")
print("=" * 70)

try:
    resp = gsc({
        "startDate": "2026-01-16",
        "endDate": "2026-04-16",
        "dimensions": [],
        "rowLimit": 1,
    })
    totals = (resp.get("rows") or [{}])[0]
    print(f"\nTOTALS: clicks={totals.get('clicks',0)}  impressions={totals.get('impressions',0)}  ctr={totals.get('ctr',0):.2%}  avg_position={totals.get('position',0):.1f}")

    for dim, label, limit in [("query", "TOP QUERIES", 25), ("page", "TOP PAGES", 15), ("country", "TOP COUNTRIES", 10), ("device", "DEVICE MIX", 5)]:
        resp = gsc({
            "startDate": "2026-01-16",
            "endDate": "2026-04-16",
            "dimensions": [dim],
            "rowLimit": limit,
        })
        rows = resp.get("rows") or []
        print(f"\n{label}:")
        if not rows:
            print("  (no data)")
            continue
        for r in rows:
            key = r["keys"][0]
            clicks = r.get("clicks", 0)
            impr = r.get("impressions", 0)
            ctr = r.get("ctr", 0)
            pos = r.get("position", 0)
            # shorten page paths
            if dim == "page":
                key = key.replace("https://pubroot.com", "")[:70]
            print(f"  clicks={clicks:>3} impr={impr:>4} ctr={ctr:.1%} pos={pos:4.1f}  {key[:70]}")
except Exception as e:
    print(f"GSC error: {e}")
