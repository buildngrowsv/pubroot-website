# Pruning v1: Report-Only Quality Analysis for Pubroot

**Status:** MVP implementation (2026-10-24)  
**Spec:** See `pruning.md` (attached to this PR)  
**Mode:** REPORT-ONLY - No papers are modified, archived, or deleted

## Overview

This implements the Pubroot pruning v1 system using the hybrid approach described in `pruning.md`. The system generates a report that flags papers with potential quality, integrity, or staleness issues, but makes **no changes** to any papers, reviews, or repository state.

## What It Does

The pruning reporter scans all published papers and checks for:

1. **Near-Duplicates** - Papers with high similarity in title/abstract (e.g., 2026-016 vs 2026-005)
2. **Missing Reviews** - Papers with no review.json file (unreviewed: 2026-017, 2026-035, 2026-036, 2026-037)
3. **Expired Papers** - Papers past their `valid_until` date but still marked as `status: current`
4. **Unverifiable Badges** - Papers claiming `verified_private` (never implemented) or `verified_open` without supporting_repo
5. **Missing Grounding** - Reviews claiming `grounding_used: true` but with no grounding_metadata (affects 32 papers since 2026-08-25, per bugs.md B5)

## Key Files

```
scripts/
├── pruning_v1_report.py              # Main report generation script
├── test_pruning_v1_report.py         # Comprehensive test suite (11 tests)
└── requirements_pruning.txt          # Dependencies (PyYAML required, sentence-transformers optional)

.github/workflows/
└── pruning_report.yml                # Manual workflow to generate and upload reports
```

## Usage

### Command Line

```bash
# Basic usage (from repo root)
python3 scripts/pruning_v1_report.py

# Custom output paths
python3 scripts/pruning_v1_report.py \
  --output-json my_report.json \
  --output-md my_report.md

# With LLM-based checks (not yet implemented)
python3 scripts/pruning_v1_report.py --use-llm
```

### GitHub Actions

The workflow is **manual-trigger only** (workflow_dispatch):

1. Go to Actions → "Pruning v1 Report (Report-Only)"
2. Click "Run workflow"
3. Optionally enable embeddings for better duplicate detection
4. Download the JSON and Markdown artifacts

### Dependencies

**Required:**
- PyYAML >= 6.0

**Optional (for enhanced duplicate detection):**
- sentence-transformers >= 2.2.0

Without sentence-transformers, the script falls back to token-based overlap similarity, which is sufficient for exact or near-exact duplicates but may miss semantic duplicates.

## How It Works

### Duplicate Detection

The system uses two methods:

1. **Embedding-based (preferred):** Computes sentence embeddings for title+abstract using `all-MiniLM-L6-v2` and flags pairs with cosine similarity ≥ 0.85
2. **Token overlap (fallback):** Computes Jaccard similarity of word tokens and flags pairs with overlap ≥ 0.3

When a duplicate is found, the **newer** paper is flagged (per the spec's games-space method), suggesting `superseded_by` for the older paper.

### Badge Verification

Currently flags:
- All `verified_private` badges (verification feature not implemented per bugs.md B4)
- `verified_open` badges without a `supporting_repo` URL

Future enhancement: Check if `git checkout <sha>` succeeded in the review pipeline.

### Grounding Integrity

Checks if `review_metadata.grounding_used` is true but `grounding_metadata.available` is false. This catches the known issue (bugs.md B5) where all reviews since 2026-08-25 claim grounding but have no grounding metadata.

### Expiry Detection

Parses `valid_until` dates and flags papers where:
- `valid_until < now` AND `status == "current"`

The spec says these should transition to `status: expired`, not archived.

## Report Format

### JSON Report (`pruning_report.json`)

Structured data suitable for programmatic analysis:

```json
{
  "report_metadata": {
    "generated_at": "2026-10-24T02:02:26.229952+00:00",
    "total_papers_scanned": 106,
    "total_flagged": 62,
    "embeddings_available": false,
    "thresholds": { ... },
    "spec_version": "pruning_v1_mvp"
  },
  "flagged_candidates": [
    {
      "paper_id": "2026-016",
      "title": "...",
      "flags": ["near_duplicate", "unverifiable_badge"],
      "evidence": {
        "near_duplicate": [...],
        "unverifiable_badge": { ... }
      }
    }
  ],
  "summary_by_flag": {
    "near_duplicate": 1,
    "missing_review": 4,
    "expired": 0,
    "unverifiable_badge": 56,
    "missing_grounding": 32
  }
}
```

### Markdown Report (`pruning_report.md`)

Human-readable report with:
- Executive summary with counts per flag type
- Per-paper details with all evidence
- Explicit REPORT-ONLY disclaimer

## Current Findings (as of 2026-10-24 on main)

From the generated report:

- **106 papers scanned**
- **62 papers flagged** (58% of corpus)

Breakdown:
- **Near-Duplicates:** 1 paper (2026-024 vs 2026-018, 100% title match)
  - Note: 2026-016 vs 2026-005 has 0.295 overlap, just below the 0.3 threshold
- **Missing Reviews:** 4 papers (2026-017, 2026-035, 2026-036, 2026-037) - marked as "unreviewed" per Pubroot Lead guidance
- **Expired Papers:** 0 papers (no papers have expired valid_until dates yet)
- **Unverifiable Badges:** 56 papers
  - 32 with `verified_private` (feature not implemented)
  - 24 with `verified_open` but no `supporting_repo` URL
- **Missing Grounding:** 32 papers (reviews claiming grounding without metadata)

## Testing

The test suite includes 11 tests covering:
- Reporter initialization
- Paper loading from frontmatter
- Token overlap similarity computation
- All detection functions (duplicates, missing reviews, expired, badges, grounding)
- Report generation and formatting
- JSON and Markdown output

Run tests:
```bash
pytest scripts/test_pruning_v1_report.py -v
```

All tests passing as of 2026-10-24.

## Future Enhancements (Not in MVP)

From the spec:

1. **LLM Re-Review (Option 1):** Re-review papers in the bottom slice using the current best model with grounding required
2. **Algorithmic Health Score:** Combine multiple signals (use, citations, claim verification, author reputation) into a single health metric
3. **Two-Reason Rule:** Require two independent signals before archiving (docking requires only one)
4. **Usage Tracking:** Log MCP retrievals, page views, and citations (requires infrastructure beyond GitHub Pages)
5. **Link Checker:** Validate claim sources and repo URLs
6. **Embeddings by Default:** Use sentence-transformers for all deployments

## Constraints Met

Per the task requirements:

✅ **Report-only:** No papers archived, unpublished, deleted, relabeled, or edited  
✅ **No issues touched:** The script only reads data, never writes to GitHub  
✅ **No wrangler/Workers code:** Pure Python, no Cloudflare dependencies  
✅ **No workflow replacement:** New workflow added, existing review.yml and publish.yml untouched  
✅ **No CNAME change:** Per 2026-04-19 operator decision  
✅ **No secrets touched:** The script has no API calls or secret dependencies  
✅ **LLM optional and off by default:** `--use-llm` flag present but not implemented yet  
✅ **No paid API calls during development:** Uses only local computation and file reads  
✅ **Tests added:** 11 comprehensive tests in test_pruning_v1_report.py  
✅ **Branch and PR workflow:** Implemented on `cursor/pruning-v1-report-only-fd51`  

## Decision Points for Adam (Pubroot Lead)

From the spec and implementation:

1. **Threshold Tuning:** Current thresholds are:
   - Duplicate embedding similarity: 0.85
   - Duplicate token overlap: 0.3
   - Should these be adjusted based on the first report?

2. **2026-016 vs 2026-005:** The known near-duplicate case has 0.295 token overlap (just below threshold). Flagged in the spec but not in the token-overlap report. Should we:
   - Lower the token threshold to 0.29?
   - Require embeddings for production?
   - Manually mark this pair?

3. **Unverifiable Badge Policy:** 56 papers flagged for badge issues:
   - What should happen to papers with `verified_private`? (Downgrade to `text_only` or `unverified_private`?)
   - Should `verified_open` require both `supporting_repo` URL and successful SHA checkout?

4. **Missing Grounding (32 papers):** Reviews claim `grounding_used: true` but have no metadata. Should these:
   - Be re-reviewed?
   - Have their `grounding_used` flags corrected in place?
   - Be flagged in the UI but not docked?

5. **Report Cadence:** Should this run:
   - On every PR (as a check)?
   - Weekly via cron?
   - Only manual dispatch?

6. **Next Steps:** After this MVP, which enhancement should be prioritized:
   - Link checker for dead sources?
   - Embeddings for better duplicate detection?
   - Algorithmic health score?
   - LLM re-review of the bottom slice?

## Related Issues

This implementation addresses the following known issues from bugs.md and the Systems audit:

- **B4:** Unverifiable badges (verified_private, verified_open with failed SHA)
- **B5:** Missing grounding metadata (32 papers since 2026-08-25)
- **B11:** Supersession and expiry never applied
- **B14:** Missing review.json for 2026-017, 2026-035, 2026-036, 2026-037

It also implements the detection for the near-duplicate pressure test (2026-016 ≈ 2026-005) mentioned in the spec.

## License

This code follows the same license as the Pubroot repository (CC0 for content, Apache 2.0 for code).
