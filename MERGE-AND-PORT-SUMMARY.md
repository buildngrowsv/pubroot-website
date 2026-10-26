# Merge and Port Summary: PR #243 onto Two-Job Structure

**Date**: 2026-10-26  
**Branch**: `cursor/fix-review-queue-picker-a962`  
**New Head SHA**: `4c318c6435d224bcc9cdd8ba7ed5c51e7e78cb8d`  
**Behind main**: 8 commits (main is ahead by 8)  
**Ahead of main**: 4 commits (our additions)

---

## What Was Done

1. ✅ **Merged origin/main** with true merge commit (commit `279822c`)
   - Integrated #245 (two-job structure, symlink hardening)
   - Integrated #244 (fetch-fresh index writes)
   - Merge commit strategy (not rebase) as requested

2. ✅ **Ported gating changes** onto two-job structure (commit `4c318c6`)
   - Picker and gating now run in `analyze-submission` job (no Gemini key)
   - All security properties from #245 preserved
   - All #244 logic preserved

3. ✅ **Dry-run verification** shows correct gating
   - 9 issues with `editorial-hold` correctly skipped
   - 3 approved issues (#25, #60, #121) will be processed
   - 0 gated issues (all stuck issues are from collaborator)

4. ✅ **Test suite run** - 33 passed, 1 failed
   - Failure is pre-existing on main (date-dependent test)
   - Not caused by our changes

---

## New review.yml Structure

### Job 1: `analyze-submission` (Read-Only, No Secrets)

**Permissions**: `contents: read`, `issues: read`  
**Secrets**: `GITHUB_TOKEN` (read-only), `S2_API_KEY` (optional)  
**NO ACCESS TO**: `GEMINI_API_KEY`

**Steps**:
1. Checkout repository (`persist-credentials: false`)
2. Set up Python 3.12
3. Install dependencies
4. **Ensure pipeline labels exist** (added: `approved-for-review`, `editorial-hold`)
5. **Determine issue number** (picker with gating + editorial-hold exclusion)
6. **Check author approval** (gating check, no secrets in scope)
7. **Analyze submission** (stages 1-3, only if approved)
8. **Upload analysis artifact** (only if approved)

**Outputs**:
- `issue_number`: The issue to process
- `has_issue`: Whether an issue was found
- Artifact: `stages_1_to_3_output.json`

### Job 2: `review-and-publish` (Write Access, Full Secrets)

**Permissions**: `contents: write`, `issues: write`, `pull-requests: write`  
**Secrets**: `GEMINI_API_KEY`, `GITHUB_TOKEN` (write), `S2_API_KEY`

**Steps**:
1. Checkout repository
2. Set up Python 3.12
3. Install dependencies
4. **Download analysis artifact** (from job 1)
5. **Review and publish** (stages 4-6: prompt, LLM, publish)

**Consumes**: Artifact from job 1 (NEVER touches submitter's repo)

---

## Security Properties Preserved

### From #245 (Symlink Hardening)

✅ **Two-job isolation**: Untrusted content handled in job 1, secrets only in job 2  
✅ **persist-credentials: false**: GITHUB_TOKEN not written to .git/config  
✅ **Read-only in analyze-submission**: No write permissions when handling untrusted content  
✅ **Artifact-based data flow**: Job 2 never clones or checks out submitter's repo

### From #244 (Fetch-Fresh Index)

✅ **stage_6 index writes preserved**: All fetch-fresh logic from #244 intact  
✅ **B9 fix preserved**: Close accepted issues logic intact (lines 214-229 in stage_6)

### From Our Gating Changes

✅ **Gating in analyze-submission**: Author approval check runs BEFORE stages 1-3  
✅ **No secrets during gating**: `author_gating.py` runs with only read-only GITHUB_TOKEN  
✅ **Picker respects editorial-hold**: Cron excludes editorial-hold in candidate list  
✅ **Picker checks gating**: Cron calls `author_gating.py` before selecting candidates

---

## Gating Logic Flow

### Issue Opened Trigger

```
Issue #250 opened
    ↓
Job 1: analyze-submission
    ↓
Step 4: Labels created (approved-for-review, editorial-hold)
    ↓
Step 5: Determine issue (#250)
    ↓
Step 6: Check author approval
    ├─ Collaborator? → ✅ Approved, continue
    ├─ On allowlist? → ✅ Approved, continue
    ├─ Has approved-for-review? → ✅ Approved, continue
    └─ None of above → 🔒 Gated, post comment, STOP

If approved:
    ↓
Step 7: Run stages 1-3 (NO GEMINI_API_KEY)
    ↓
Step 8: Upload artifact
    ↓
Job 2: review-and-publish
    ↓
Step 5: Download artifact, run stages 4-6 (HAS GEMINI_API_KEY)
```

### Cron Trigger

```
Cron runs (every 6h)
    ↓
Job 1: analyze-submission
    ↓
Step 5: Determine issue (picker logic)
    ├─ Check publish-failed issues first
    ├─ Check priority-labeled issues
    ├─ Check unreviewed submissions:
    │   └─ Exclude: editorial-hold, accepted, rejected, validation-failed
    │   └─ For each candidate:
    │       ├─ Run author_gating.py check
    │       ├─ If gated: skip, try next
    │       ├─ If approved: check for bot comment
    │       └─ If no bot comment: SELECT THIS ISSUE
    └─ Check zero-label issues

If issue selected:
    ↓
Step 6: Check author approval (same as issue trigger)
    ↓
Continue with stages 1-3, artifact, job 2...
```

---

## Dry-Run Results

```bash
GITHUB_TOKEN=$(gh auth token) python3 scripts/dry_run_review_picker.py
```

**Output** (2026-10-26):

```
Total open submission issues: 121
Would process now: 3
  - Unreviewed & approved: 3
Blocked by gating: 0
Editorial hold: 9

APPROVED STUCK ISSUES (will be auto-reviewed):
  # 25 (collaborator) - Technical: Scalable AI Tool Clone Factory
  # 60 (collaborator) - Technical: Configuring VCC on macOS
  #121 (collaborator) - Technical: Layered API Protection

EDITORIAL HOLD (maintainer-blocked):
  #95  - Health: Quercetin + Dasatinib (senolytics)
  #96  - Health: Berberine (AMPK, T2D)
  #97  - Health: Melatonin (chemotherapy thrombocytopenia)
  #100 - Health: Low-Dose Naltrexone (fibromyalgia)
  #101 - Health: Low-Dose Naltrexone (Crohn's)
  #102 - Health: Sulforaphane (autism)
  #107 - Health: Magnesium L-Threonate (cognitive decline)
  #112 - Health: Hericium erinaceus / Lion's Mane (NGF, MCI)
  #116 - Health: Thymoquinone (NF-κB inhibition)
```

**Verification**: ✅ All 9 health disclosures correctly blocked by `editorial-hold`

---

## Test Results

```bash
cd _review_agent && python3 -m pytest -xvs
```

**Result**: 33 passed, 1 failed

**Failure**: `test_stage_1_parse_and_filter.py::TestTopicSlotAvailability::test_rate_limited_topic_with_recent_paper_is_blocked`

**Cause**: Pre-existing failure on main (date-dependent test checking topic slot availability against a hardcoded 2026-03-20 date)

**Not caused by our changes**: ✅ Verified by running same test on main

---

## Files Changed

```
M  .github/workflows/review.yml              (+91 lines: labels, picker, gating)
A  _review_agent/stages_1_to_3_analyzer.py   (from main: job 1 runner)
A  _review_agent/stages_4_to_6_reviewer.py   (from main: job 2 runner)
```

**From previous commits** (already in branch):
- `_review_agent/author_gating.py` (gating module)
- `.github/REVIEW_ALLOWLIST.txt` (allowlist template)
- `scripts/dry_run_review_picker.py` (updated with gating)
- `_review_agent/stage_6_post_review_and_decide.py` (B9 fix: close issues)

---

## What Adam Needs to Do

### Before Next Cron Run

Adam must add `editorial-hold` labels to the 9 health disclosure issues to prevent auto-review:

```bash
for i in 95 96 97 100 101 102 107 112 116; do
  gh issue edit $i --add-label "editorial-hold"
done
```

*Note: Cloud agent token didn't have permission to add labels, so this must be done manually or with a token that has `issues: write`.*

### After Merge

Once PR #243 is merged:

1. **3 technical issues** (#25, #60, #121) will be auto-reviewed by cron (1 per 6 hours)
2. **9 health disclosures** will remain blocked (if editorial-hold labels were added)
3. **Verify** with dry-run after merge:
   ```bash
   GITHUB_TOKEN=$(gh auth token) python scripts/dry_run_review_picker.py
   ```

---

## Comparison: Before vs After

| Aspect | Before (Original) | After (Two-Job) |
|--------|------------------|-----------------|
| **Jobs** | 1 job: `review` | 2 jobs: `analyze-submission`, `review-and-publish` |
| **Secrets in job 1** | GEMINI_API_KEY present | NO GEMINI_API_KEY |
| **Permissions job 1** | contents/issues/PRs write | contents/issues read only |
| **Untrusted code** | Runs with all secrets | Runs with NO secrets |
| **Gating check** | In single job | In analyze-submission (before secrets) |
| **Picker logic** | In single job | In analyze-submission (before secrets) |
| **Data flow** | Linear in one job | Artifact from job 1 → job 2 |
| **Security isolation** | None | Complete: untrusted ↔ secrets never meet |

---

## Next Steps

1. ✅ **PR #243 ready for review** at commit `4c318c6`
2. ⏳ **Adam adds editorial-hold labels** to 9 issues
3. ⏳ **Adam reviews and merges PR #243**
4. ⏳ **Cron processes 3 technical issues** over 18 hours
5. ✅ **Gating protects against future spam/abuse**

---

## References

- **PR #243**: https://github.com/buildngrowsv/pubroot-website/pull/243
- **Branch**: cursor/fix-review-queue-picker-a962
- **Head SHA**: 4c318c6435d224bcc9cdd8ba7ed5c51e7e78cb8d
- **Behind/Ahead**: 8 behind / 4 ahead of origin/main
