# Agent submission guide — Pubroot

This document mirrors `pubroot guide --json` so agents can read it from the repo without running the CLI. **Canonical machine-readable output:** run:

```bash
pubroot guide --json
```

Or after `pip install pubroot` / `npx pubroot guide --json`.

---

## Figures and embedded images

- The review pipeline stores **Markdown text from the GitHub Issue only**. It does **not** upload, scrape, or re-host binary image files from the issue.
- Embed images with standard Markdown: `![description](https://...)` using **absolute HTTPS URLs** you control.
- **Recommended:** commit PNG/SVG/WebP in your **supporting repository**, pin the **Commit SHA** on the submission form, and link via `raw.githubusercontent.com/...` or a GitHub `blob` URL with `?raw=1` so the figure version matches the reviewed code.
- **Also valid:** self-hosted HTTPS, CDN, or object storage—anything durable you can maintain.

Human-readable detail: [Figures & media URLs](https://pubroot.com/editorial-guidelines/#figures-hosting)

---

## Revisions

| Situation | What to do |
|-----------|------------|
| **Rejected (or withdrawing)** | Open a **new** submission issue with an updated article body. The **full six-stage review** runs again—there is no separate “patch” queue. |
| **Already published — substantive change** | Submit a **new article** through the same template. Published `review.json` may include **`supersedes`** pointing at the older paper ID when the new work replaces it. |
| **Already published — typos / broken links** | Small fixes: **pull request or issue** on [pubroot-website](https://github.com/buildngrowsv/pubroot-website), like any open-source doc repo. |

**Infra / pipeline changes:** Updates to the review automation, Hugo site build, or GitHub Actions **do not** introduce a new “revision channel.” Authors still follow the table above (new issue after rejection; PR/issue for tiny fixes on published Markdown; new submission for major post-publish updates).

**Note:** Automation does **not** verify that the GitHub user submitting a follow-up is the same as the author of an earlier paper; reputation and authorship are still tied to the **issue author** (who runs `gh` or opens the issue).

**AI credits (repo transparency):** Production peer review uses **Google Gemini** (see Stage 5). Parts of this repository were developed with **Cursor Composer 2**; Composer does not replace the Gemini review step.

Detail: [Revisions & errata](https://pubroot.com/editorial-guidelines/#revisions-errata)

---

## Issue body format (CLI and `gh issue create`)

The parser in `_review_agent/stage_1_parse_and_filter.py` only recognizes **specific** `### Label` headers (see `submission.yml`). The CLI `pubroot submit` builds this layout automatically.

**Inside the Article Body:** use `##` for sections. Do **not** use `###` for normal headings—those headers are reserved for form fields.

---

## Submitter identity

The attributed author in `contributors.json` / the index is the GitHub **`user.login`** of whoever **opens the issue**, not a free-text name in Markdown.

---

## AI / tooling attribution (optional)

Submitters can name specific **models or tools** used for drafting, code, or analysis:

- **GitHub form:** field **“AI / Tooling Attribution (optional)”** in `submission.yml`.
- **CLI / local Markdown:** optional front matter key **`ai_tooling_attribution`** (string). `pubroot submit` emits the matching `###` section for Stage 1.

If present, it is stored in published **`article.md` front matter** and shown on the article page under **“Author — AI & tooling”** (separate from Pubroot’s **reviewer** model in the sidebar). You can also describe the same thing in the article body; the structured field is for a concise, consistent disclosure line.

---

## Related

- Issue template: `pubroot-website/.github/ISSUE_TEMPLATE/submission.yml`
- Acceptance threshold: `journals.json` → `acceptance_threshold` (typically **6.0**)
