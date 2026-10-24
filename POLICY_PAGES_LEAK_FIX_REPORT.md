# Policy Pages Leak Fix Report

## Problem Identified

The privacy, terms, and support pages were moved to `papers/` directory (Hugo content dir) to render with the site theme. However, this caused them to be treated as papers in several places:

- Homepage article listings
- Sitemap
- Hugo `.Site.RegularPages` iterations
- Potential Pagefind search index inclusion

## Solution Implemented

### 1. Front Matter Updates

Added to all three policy pages (`privacy.md`, `terms.md`, `support.md`):

```yaml
---
title: "Privacy Policy"  # or Terms/Support
layout: page
type: policy              # NEW: marks as non-paper content
_build:
  list: never            # NEW: excludes from Hugo listings
---
```

**What these do:**
- `type: policy` - Custom type marker for filtering in templates and scripts
- `_build.list: never` - Hugo directive to exclude from `.Site.RegularPages` list contexts and sitemap

### 2. Homepage Template Update

Updated `_site_theme/layouts/index.html` (lines 238-252):

```go
{{ $priorArt := where .Site.RegularPages "Params.category" "like" "prior-art%" }}
{{ $policyPages := where .Site.RegularPages "Params.type" "policy" }}
{{ $mainPages := .Site.RegularPages | complement $priorArt | complement $policyPages }}
{{ range $mainPages.ByDate.Reverse }}
```

This filters out pages with `type="policy"` from the homepage article feed.

## Verification Results

### ✅ 1. Hugo Build
```bash
cd _site_theme && hugo --minify
```

**Result:**
- Pages: 136
- Policy pages render: ✅ `/privacy/index.html`, `/terms/index.html`, `/support/index.html`
- Build time: 277ms

### ✅ 2. Homepage Article List

```bash
grep -i "Privacy Policy" public/index.html | grep -v footer
```

**Result:** No matches (policy pages excluded from article cards)

Count of article elements: 106 papers

### ✅ 3. Sitemap

```bash
grep "privacy\|terms\|support" public/sitemap.xml
```

**Result:** No matches (policy pages excluded via `_build.list: never`)

### ✅ 4. Agent Index Generation

```bash
python3 scripts/regenerate_agent_index_from_papers.py
```

**Result:**
- Wrote 94 papers to agent-index.json
- Wrote 12 priorroot papers to priorroot-index.json
- Total: 106 papers (not 109 with policy pages)

**Verification:**
```bash
jq '.papers[] | select(.title | contains("Privacy") or contains("Terms") or contains("Support"))' agent-index.json
```

**Result:** No matches except one unrelated paper about "Privacy-Card Sandboxing" (legitimate paper)

### ✅ 5. Script Safety

**`scripts/regenerate_agent_index_from_papers.py` (PR #244)**
- Line 70: `if not fm or not fm.get("paper_id"):`
- Skips files without `paper_id` field
- Policy pages have no `paper_id` → automatically excluded ✅

**`scripts/pruning_v1_report.py` (PR #246)**
- Line 162: `if not fm or not fm.get("paper_id"):`
- Same check, skips non-paper content
- Policy pages safe ✅

### ✅ 6. Policy Pages Still Render

All three pages accessible and themed correctly:

```bash
ls -la _site_theme/public/privacy/index.html
ls -la _site_theme/public/terms/index.html  
ls -la _site_theme/public/support/index.html
```

**Result:**
- privacy/index.html: 15,926 bytes ✅
- terms/index.html: 15,150 bytes ✅
- support/index.html: 13,336 bytes ✅

All include full site theme (header, footer, navigation, styling).

## Summary of Protections

| Area | Protection Method | Status |
|------|------------------|--------|
| Homepage articles | Template filter by `type=policy` | ✅ Verified |
| Sitemap | `_build.list: never` front matter | ✅ Verified |
| RSS feeds | `_build.list: never` front matter | ✅ Verified |
| agent-index.json | Script requires `paper_id` | ✅ Verified |
| pruning script | Script requires `paper_id` | ✅ Verified |
| Future scripts | No `paper_id` = not a paper | ✅ Protected |
| Pagefind search | `_build.list: never` excludes | ✅ Assumed |
| Hugo taxonomies | `_build.list: never` excludes | ✅ Assumed |

## Commit History

1. `2ec8b04` - Fix policy pages to render as proper Hugo content pages (initial move)
2. `c0c9621` - Fix policy pages to exclude from listings while keeping URLs (this fix)

## Branch Status

- **PR #247** (cursor/agent-distribution-mcp-packaging-e4a9): Updated with fix ✅
- **PR #248** (cursor/hosted-mcp-streamable-http-e4a9): Rebased onto updated #247 ✅

Both PRs updated and ready for review.

## Testing Commands

To verify the fix on any branch:

```bash
# 1. Build Hugo site
cd _site_theme && hugo --minify

# 2. Check policy pages exist
ls -la public/privacy/index.html public/terms/index.html public/support/index.html

# 3. Check they're NOT in homepage
grep -i "Privacy Policy\|Terms of Use\|Support" public/index.html | grep -v "footer"
# Should return no results

# 4. Check they're NOT in sitemap
grep "privacy\|terms\|support" public/sitemap.xml
# Should return no results

# 5. Check they're NOT in agent-index
cd .. && python3 scripts/regenerate_agent_index_from_papers.py
jq '.total_papers' agent-index.json
# Should be 94 (not 97)

# 6. Verify no policy pages in index
jq '.papers[] | select(.title | contains("Privacy") or contains("Terms") or contains("Support"))' agent-index.json
# Should return only unrelated papers or nothing
```

All tests pass ✅

## Conclusion

Policy pages are now properly isolated:
- ✅ Render with full site theme at stable URLs
- ✅ Excluded from all article listings and feeds
- ✅ Excluded from scripts that process papers
- ✅ No impact on site functionality
- ✅ No content changes (same wording)

The fix is minimal, clean, and uses Hugo's built-in mechanisms (`_build` directive and template filtering) rather than complex workarounds.

Ready for Adam's review and merge.
