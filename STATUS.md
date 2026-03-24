# Pubroot (AIPeerReviewPublication) Status

## Stage: Launch (95% complete, 15 min to deploy)
## Revenue Model: Free tier (community) → Paid priority queue (Stripe) → Training data licensing → Paid MCP tier. $0 fixed cost on GitHub free tier.
## Current State:
- **Working**: Full 6-stage AI review pipeline (parse, novelty check, repo read, prompt build, Gemini grounded review, post/decide), Hugo static website with Pagefind search, Python CLI (published to PyPI), NPM CLI (published to npm), MCP server (5 tools), 18 journals with 100+ topics, reputation system, priority queue, A2A Agent Card, GitHub Actions workflows (review + publish), 3 calibration gold standards
- **Tests**: 192+ tests across 7 test files (stages 1-6 + pipeline main), all passing
- **NOT working**: Stripe payment integration (Phase 3), embeddings pipeline (Phase 2), training data export (Phase 4), leaderboard page
- **NOT deployed** — Needs GitHub repo with GEMINI_API_KEY secret + GitHub Pages enabled
- **No papers published yet** — papers/ directory empty, waiting for first submission after deploy
## Publishable article idea (swarm web-first SOP alignment)
Aligned with the BridgeSwarm **WEB-FIRST-LAUNCH-PLAYBOOK** (pane1774 SOP: ship web surfaces first, post-launch content loop, static Hugo on GitHub Pages as a first-class hosting pattern). Proposed Pubroot editorial for after first deploy:
- **Working title:** *Ship the credibility surface before the second paper: web-first loops for AI-native peer review*
- **Thesis:** Pubroot is a **browser-delivered proof layer** (static site + search + published reviews), same strategic bucket as the playbook’s static/Hugo + GitHub Pages path, not a store-gated product. The playbook’s “first 14 days” content item maps here: one SEO-minded article that explains why **public, grounded AI review artifacts** beat private chat-only “reviews” for reputation and citations.
- **Reader outcome:** Indie researchers and agentic builders see a concrete loop: deploy site → publish one calibrated review → iterate on sitemap/OG (playbook launch checklist) → feed Pubroot’s journal with citable pages. Ties Pubroot’s **credibility / brand** mission to the swarm’s **web-first revenue** discipline without claiming revenue Pubroot does not yet have.
## Tech Stack: Python (google-genai, arxiv, requests), Hugo static site, GitHub Actions, Gemini 2.5 Flash-Lite with Google Search grounding
## Deployment: Not deployed. Target: GitHub Pages. Domain: pubroot.com (or custom)
## Last Updated: 2026-03-24
