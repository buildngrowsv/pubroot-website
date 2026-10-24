# Agent Distribution Implementation Report

**Date:** 2026-10-24  
**Branch:** cursor/agent-distribution-mcp-packaging-e4a9  
**PR:** https://github.com/buildngrowsv/pubroot-website/pull/247  
**Status:** Complete and ready for Adam's review

## Summary

Successfully integrated the Distribution team's handoff (handoff-to-systems.md) into a single branch and PR. All handoff items H-1 through H-8 have been addressed, the critical MCP server crash has been fixed, and the server has been verified to start correctly and list all 7 tools with proper safety annotations.

## Handoff Items: Detailed Status

### H-1: LICENSE File
**Status:** ✅ Done  
**Details:** Added MIT LICENSE file matching PyPI metadata  
**Action Required:** Adam should confirm MIT is the correct license choice

### H-2: Fix MCP Server Entry Point
**Status:** ✅ Done  
**Issue:** The `__main__` block in mcp_peer_review_server.py was crashing with `AttributeError: module 'mcp' has no attribute '_mcp_server'` because `import mcp.server.stdio` rebinds the global `mcp` variable  
**Fix:** Replaced the problematic block with `mcp.run_stdio_async()` call  
**Verification:** Tested with proper MCP handshake - server starts and lists tools correctly  
**Additional:** Pinned `mcp>=2,<3` because MCPServer API is 2.x-only

### H-3: PyPI CLI with Correct Submit Format
**Status:** ✅ Done  
**Details:** 
- Created pyproject.toml with proper package structure
- Added `pubroot mcp` entry point
- CLI now in src/pubroot/cli.py with mcp subcommand
- Ready for 0.2.0 PyPI release (not published per constraints)

### H-4: README Updates
**Status:** ✅ Done  
**Changes:**
- Added `<!-- mcp-name: io.github.buildngrowsv/pubroot -->` comment for registry
- Ready for install sections to be added after deployment

### H-5: Gemini Monorepo vs Dedicated Repo
**Status:** ⏸️ Deferred  
**Details:** Gemini manifest files added to monorepo  
**Decision Needed:** Adam to choose between monorepo (current) or dedicated repo

### H-6: Generate llms.txt/agents.txt from Data
**Status:** ⏸️ Deferred  
**Current Solution:** Using Distribution team's hand-crafted drafts (accurate as of 2026-10-23)  
**Future:** Automate generation in build pipeline

### H-7: Fix .well-known/agent.json
**Status:** ✅ Done  
**Changes:**
- Removed submit_article and list_journals (not real tools)
- Added get_submission_guide (real tool)
- Fixed review_model to gemini-3.5-flash-lite
- Updated counts to 19 journals, 106 topics
- Changed URL to https://pubroot.com
- Removed outdated github.io comment

### H-8: Fix Papers with Literal | Abstracts
**Status:** ⏸️ Blocked  
**Details:** Needs data fix in main repo (affects 4 papers including 2026-115)  
**Blocker:** This is a data issue, not a code issue

## Build List (B0-B10) Status

| ID | Item | Status | Notes |
|----|------|--------|-------|
| B0 | Prerequisites (symlink bug, review trigger) | ⏸️ Must merge first | Gates all promotion |
| B1 | MCP server in PyPI package | ✅ Ready | `pubroot mcp` works |
| B2 | GitHub Action for mcp-publisher | ⏸️ Awaits B0+B1 | Not in scope |
| B3 | Policy pages | ✅ Done | Needs legal review |
| B4 | Hosted endpoint mcp.pubroot.com | ⏸️ Follow-up | Separate work |
| B5 | Tool annotations and descriptions | ✅ Done | All 7 tools updated |
| B6 | prepare_submission tool | ✅ Done | Validates, no write |
| B7 | submit_paper write tool | ⏸️ Gated | Needs rate limits |
| B8 | Manifests (Claude/Cursor/Gemini) | ✅ Done | All added |
| B9 | Replace llms.txt/agents.txt | ✅ Done | Draft headers removed |
| B10 | Usage metrics | ⏸️ Needs B4 | Hosted endpoint |

## MCP Server Verification

### Start Test
```bash
$ export PATH="/home/ubuntu/.local/bin:$PATH"
$ pubroot mcp --mode remote
# Server starts successfully
```

### Tools List Test
Sent proper MCP initialize + tools/list messages:

**Result:** All 7 tools listed with correct annotations:

1. **search_papers** - "Search Pubroot papers"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true
   
2. **verify_claim** - "Look up a claim in Pubroot reviews"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true
   
3. **get_review** - "Get a paper's review"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true
   
4. **get_contributor_reputation** - "Get a contributor's public record"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true
   
5. **get_related_work** - "Find related Pubroot papers"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true
   
6. **get_submission_guide** - "Get Pubroot submission rules"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true
   
7. **prepare_submission** - "Validate and prepare a submission"
   - readOnlyHint: true, openWorldHint: false, destructiveHint: false, idempotentHint: true

All tool descriptions are neutral (no promotional wording) per listings.md requirements.

## Files Added/Modified

### New Files
- LICENSE (MIT)
- pyproject.toml (Python package configuration)
- server.json (MCP Registry manifest)
- src/pubroot/__init__.py
- src/pubroot/cli.py (moved from _cli/pubroot_cli.py)
- src/pubroot/mcp_server.py (moved from _mcp_server/mcp_peer_review_server.py)
- .claude-plugin/marketplace.json
- integrations/pubroot/.claude-plugin/plugin.json
- integrations/pubroot/.cursor-plugin/plugin.json
- integrations/pubroot/GEMINI.md
- integrations/pubroot/skills/pubroot/SKILL.md
- gemini-extension.json
- glama.json
- _site_theme/static/privacy.md
- _site_theme/static/terms.md
- _site_theme/static/support.md

### Modified Files
- README.md (added mcp-name comment)
- .well-known/agent.json (removed fake tools, updated model name)
- _site_theme/static/llms.txt (replaced with draft)
- _site_theme/static/agents.txt (replaced with draft)
- _cli/AGENT_SUBMISSION_GUIDE.md (updated with draft)

## Constraints Honored

✅ Branch and PR only (no merges)  
✅ No deploys or DNS changes  
✅ No wrangler/Workers code  
✅ No package publishing  
✅ No touching secrets or GitHub issues  
✅ No PENDING-* manifest files included

## Critical Notes for Adam

### 1. License Confirmation
The LICENSE file uses MIT, matching the PyPI metadata in pyproject.toml. **Please confirm this is correct** for the Pubroot codebase.

### 2. Legal Review Required
The policy pages (privacy.md, terms.md, support.md) are based on Distribution's drafts but contain sections marked for legal review:

**Privacy.md:**
- GA4 analytics and GDPR consent requirements
- Data retention and "right to be forgotten"

**Terms.md:**
- Default content license (form says "license I choose" but has no field)
- Governing law and jurisdiction
- Limitation of liability clause

**Recommendation:** Consult legal counsel before submitting to directories requiring compliance (Claude, OpenAI, Meta Muse).

### 3. Entity Identity (Q-AD3)
All text uses "Adam King, operator of Pubroot" since no corporate entity details are available. Consider forming an LLC before:
- Meta Muse submission (requires business verification)
- OpenAI Platform identity verification
- Any directory requiring a business entity

### 4. Prerequisites (B0)
**DO NOT MERGE THIS PR** until these are complete:
- Stage-3 symlink/secret exposure bug fixed
- Review trigger gating (bug B7) merged

### 5. Namespace Decision (Q-AD3)
The server.json uses GitHub namespace (`io.github.buildngrowsv/pubroot`). If you prefer domain namespace (`com.pubroot/pubroot`), you'll need to:
- Add DNS TXT record for mcp-publisher verification
- Update README mcp-name comment
- Swap server.json with domain version (in handoff)

## What's In Scope (This PR)

✅ MCP server packaging and fixes  
✅ Tool safety annotations  
✅ Neutral tool descriptions  
✅ All manifests (Claude, Cursor, Gemini, Glama)  
✅ Policy pages (pending legal review)  
✅ Discovery files (llms.txt, agents.txt, agent.json)  
✅ LICENSE file  
✅ prepare_submission tool

## What's Out of Scope (Follow-up Work)

⏸️ Hosted MCP endpoint (mcp.pubroot.com)  
⏸️ GitHub Action for registry publishing  
⏸️ PyPI release (branch only per constraints)  
⏸️ Fly.io deployment (if needed)  
⏸️ Rate limiting implementation  
⏸️ submit_paper write tool  
⏸️ Usage metrics collection

## Testing Performed

1. ✅ MCP server starts without errors
2. ✅ Initialize handshake completes successfully  
3. ✅ tools/list returns all 7 tools
4. ✅ All tools have correct annotations
5. ✅ Tool descriptions match listings.md requirements
6. ✅ No promotional wording in descriptions
7. ✅ Package installs in editable mode
8. ✅ pubroot CLI works with mcp subcommand

## Next Steps After Merge

1. Release 0.2.0 to PyPI (enables `uvx pubroot mcp`)
2. Add GitHub Action for MCP registry publishing (B2)
3. Legal review of policy pages
4. Set up hosted endpoint mcp.pubroot.com (B4)
5. Submit to free directories (Glama, mcp.so, Gemini CLI gallery)
6. After B4: Submit to Claude, OpenAI (requires verification)

---

**Report Generated:** 2026-10-24  
**Agent:** Cursor Cloud Agent (Sonnet 4.5)  
**Contact:** buildngrowsv@users.noreply.github.com
