# Contributing to Pubroot

Thank you for your interest in contributing to Pubroot! This guide explains how to submit papers, propose changes to the review pipeline, and run the project locally.

## Table of Contents

- [How to Submit a Paper](#how-to-submit-a-paper)
- [How to Submit a Priorroot Disclosure](#how-to-submit-a-priorroot-disclosure)
- [How to Propose Rubric or Review Pipeline Changes](#how-to-propose-rubric-or-review-pipeline-changes)
- [Local Development Setup](#local-development-setup)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Code of Conduct](#code-of-conduct)

---

## Types of Contributions

Pubroot welcomes several types of contributions:

1. **Paper submissions** — Use the [submission template](https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml), or `pubroot submit` from the CLI. These go through the 6-stage AI review pipeline (first-time outside authors wait for maintainer approval).

2. **Bug reports, feature requests, and questions** — Open a regular [GitHub issue](https://github.com/buildngrowsv/pubroot-website/issues/new). These are not reviewed as papers.

3. **Code contributions** — Fork the repo, make changes, and open a pull request. See [Pull Request Guidelines](#pull-request-guidelines) below.

**Note**: The review pipeline only treats an issue as a submission if it has the `submission` label (the template and CLI add it) or its body contains the form's `### Article Title` and `### Category` headers. Don't paste those headers into a bug report.

---

## How to Submit a Paper

Pubroot accepts articles through a structured GitHub Issue form. The submission is automatically reviewed by a 6-stage AI pipeline.

### Submission Process

1. **Open the submission form**: [Submit Article](https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml)

2. **Fill out the form** (required unless marked optional):
   - **Article Title** — Clear and descriptive
   - **Category** — Select from the dropdown (format: `journal/topic`, e.g., `ai/llm-benchmarks`)
   - **Submission Type** — Choose from: `original-research`, `case-study`, `benchmark`, `review-survey`, `tutorial`, or `dataset`
   - **AI / Tooling Attribution** — Optional; name the tools/models you used
   - **Abstract** — Up to 300 words, self-contained summary
   - **Article Body** — 200+ words in Markdown (`##` sections and `###` subsections are both fine; the parser only splits on the form's own field labels)
   - **Supporting Repository URL** — Optional but strongly recommended (earns 🟢 **Verified Open** badge)
   - **Commit SHA** — Optional; pin to a specific commit in your repo
   - **Repository Visibility** — `public`, `private`, or `no-repo`
   - **Payment Code** — Optional
   - **Submission Agreement** — Required checkboxes

3. **Submit** — The review pipeline starts automatically for maintainers, collaborators and allowlisted authors (`.github/REVIEW_ALLOWLIST.txt`). Other first-time authors get a comment saying the submission is waiting for maintainer approval.

### The 6-Stage Review Pipeline

Every submission passes through these stages sequentially:

| Stage | File | What It Does |
|-------|------|-------------|
| **1. Parse & Filter** | `_review_agent/stage_1_parse_and_filter.py` | Extract fields, validate format, check word counts, validate category against `journals.json` |
| **2. Novelty Check** | `_review_agent/stage_2_novelty_check.py` | Search arXiv and Semantic Scholar for related work, check internal index for supersession |
| **3. Repo Analysis** | `_review_agent/stage_3_read_linked_repo.py` | If a repo is linked, read file tree and key source files |
| **4. Build Prompt** | `_review_agent/stage_4_build_review_prompt.py` | Assemble complete review prompt with calibration examples, novelty context, and type-specific criteria |
| **5. AI Review** | `_review_agent/stage_5_gemini_grounded_review.py` | Send to an LLM via OpenRouter (default `google/gemini-3.8-flash`, override with `PUBROOT_MODEL`) with the `openrouter:web_search` tool. Model scores and verifies claims |
| **6. Post & Decide** | `_review_agent/stage_6_post_review_and_decide.py` | Post review as GitHub comment. If accepted (≥6.0/10): create PR, auto-merge, update index. If rejected: close issue with feedback |

### Scoring Rubric

Articles get an overall score of 0.0–10.0, plus six dimension scores (each 0.0–1.0; code quality and reproducibility may be null). How much each dimension counts depends on the submission type (see `_build_type_specific_criteria` in stage 4):

- **Methodology** — Rigor of approach, experimental design
- **Factual Accuracy** — Claims checked with web search
- **Novelty** — Contribution beyond existing work
- **Code Quality** — Repository structure, docs, tests, claim alignment
- **Writing Quality** — Clarity, structure, grammar
- **Reproducibility** — Steps documented, dependencies pinned, data available

**Acceptance threshold: 6.0/10.0**

### Review Time by Reputation

These are the targets published in the submission form and README. They are not guarantees:

- **New Contributor**: ~24 hours
- **Established** (2+ accepted): ~6 hours
- **Trusted** (5+ accepted, avg > 7.0): ~1 hour
- **Authority** (10+ accepted, avg > 8.0): Minutes

### Handling Revisions

**If rejected**, open a **new submission issue** with your updated article:

1. Read the review comment on your closed issue
2. Revise your Markdown article and supporting repo
3. Open a [new submission](https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml)
4. Fill in all fields with your full updated content
5. The entire 6-stage review runs again

**Do not** reply to the old issue expecting a re-review — automation does not treat comments on the old issue as a new draft.

**If already published**:
- **Small fixes** (typos, broken links): Open a PR editing `papers/{journal}/{topic}/{slug}/index.md`
- **Substantive changes** (new claims, results): Submit as a new article (may use `supersedes` field in review metadata)

### Figures and Images

The pipeline stores **Markdown text only** — it does not upload binary files from the issue.

- Embed images: `![description](https://...)` using **stable HTTPS URLs you control**
- **Recommended**: Commit images to your supporting repository and link via `raw.githubusercontent.com` or `?raw=1` URLs
- Also valid: self-hosted HTTPS, CDN, or object storage

See [Editorial Guidelines — Figures](https://pubroot.com/editorial-guidelines/#figures-hosting) for details.

---

## How to Submit a Priorroot Disclosure

**Priorroot** is Pubroot's defensive disclosure section. It publishes structured, dated, enabling disclosures intended to serve as public prior art that patent examiners and courts can reference.

> **Not legal advice.** As the [Priorroot page](https://pubroot.com/priorroot/) says, defensive disclosure is a structured publication practice, not a guarantee of patent outcomes, and Pubroot does not provide legal counsel. Ask a qualified patent professional if you are relying on a disclosure for legal purposes.

### What is Priorroot?

Priorroot aims to keep known compounds, devices, and software methods in the public domain. Every published disclosure is:
- AI-reviewed for completeness and enabling detail
- Date-stamped when published
- Placed in the public domain under CC0
- Indexed separately in `priorroot-index.json`

### How to Submit

Priorroot uses the **same submission template** as regular Pubroot papers. The key difference is the **category** you select:

1. Go to [Submit Article](https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml)

2. In the **Category** dropdown, select a **Defensive Disclosures & Prior Art** topic:
   - `prior-art/therapeutic-use` — Known compounds for specific medical uses
   - `prior-art/device-method` — Device operation methods and configurations
   - `prior-art/software-method` — Software algorithms, architectures, and protocols
   - `prior-art/materials-process` — Materials synthesis and processing methods
   - `prior-art/general-disclosure` — Other enabling disclosures

3. Fill out the form as you would for any Pubroot submission:
   - **Submission Type**: Usually `original-research` or `case-study`
   - **Abstract**: What is being disclosed and why it's already known
   - **Article Body**: Enabling technical detail (enough for someone skilled in the art to reproduce)
   - **Supporting Repo**: Code, data, or documentation proving prior knowledge

4. Submit — The same 6-stage review runs, but:
   - Published disclosures go to `papers/prior-art/{topic}/{slug}/`
   - Indexed in `priorroot-index.json` (separate from general Pubroot index)
   - Featured on [pubroot.com/priorroot](https://pubroot.com/priorroot/)

### Review Criteria for Disclosures

Today there is **no Priorroot-specific rubric**. Disclosures go through the same pipeline and are scored with the rubric for the **submission type** you choose. The acceptance threshold is the same (6.0/10). To be useful as a disclosure, write it so that:
- **Enabling detail** — someone skilled in the art could reproduce the method, device, or composition (the [Priorroot page](https://pubroot.com/priorroot/) sets this standard)
- **Sources** — the citations, dates, or documentation behind each claim are given
- **Completeness** — the relevant parameters, conditions, and context are documented

### Future Development

Priorroot submissions currently follow the standard pipeline. [`ROADMAP.md`](ROADMAP.md) tracks a proposed `disclosure` submission type, with criteria focused on completeness and public availability rather than novelty. It is not built yet.

For questions about Priorroot, open an issue in this repository.

---

## How to Propose Rubric or Review Pipeline Changes

The review pipeline is modular and open to community improvements. Changes to scoring criteria, stage logic, or calibration examples are welcome.

### Where Things Live

- **Scoring rubric**: Defined in `_review_agent/stage_4_build_review_prompt.py` (type-specific criteria) and documented in [Editorial Guidelines](https://pubroot.com/editorial-guidelines/)
- **Review prompts**: `_review_agent/stage_4_build_review_prompt.py` and `_review_agent/stage_5_gemini_grounded_review.py`
- **Calibration examples**: `_calibration/gold-01-excellent.json`, `gold-02-average.json`, `gold-03-poor.json`
- **Category definitions**: `journals.json` (journal/topic taxonomy)
- **Workflows**: `.github/workflows/review.yml` and `publish.yml`

### Proposal Process

1. **Open an Issue First**
   - Describe the problem: What's broken, unclear, or missing?
   - Propose your solution: What would you change and why?
   - Ask for the `enhancement` label (contributors without triage rights can't set labels)
   - Get feedback from maintainers before implementing

2. **If Approved, Open a Pull Request**
   - Create a branch: `git checkout -b your-feature-name`
   - Make your changes
   - **Write or update tests** (see [Running Tests](#running-tests) below)
   - Run the test suite: `python3 -m pytest _review_agent/` (from repo root)
   - Open a PR with a clear description linking to the original issue

3. **Code Review**
   - Maintainers will review your PR
   - Run the tests locally; no CI workflow runs pytest on PRs today
   - Small, focused PRs are preferred over large rewrites

### Running Tests

Tests live in `_review_agent/test_*.py`. Run them locally before submitting a PR:

```bash
# From repository root
python3 -m pytest _review_agent/

# Run a specific test file
python3 -m pytest _review_agent/test_stage_1_parse_and_filter.py

# From _review_agent directory
cd _review_agent
python3 -m pytest

# Whole repo (also runs scripts/ and _mcp_server/ tests)
python3 -m pytest
```

**Install test dependencies** (if pytest is not installed):

```bash
pip install pytest
pip install -r _review_agent/requirements.txt
```

Tests include:
- Stage-by-stage unit tests (`test_stage_*.py`)
- Integration tests (`test_end_to_end_integration.py`)
- Bug regression tests (`test_bug_b20_fixes.py`, `test_bug_b23_fixes.py`)
- URL/slug path helper tests (`test_pubroot_site_paths.py`)
- Index golden tests (`scripts/test_index_golden.py`)

### What to Test

When making changes:
- **Changing stage logic**: Update corresponding `test_stage_N_*.py`
- **Changing index building**: Run `python3 -m pytest scripts/test_index_golden.py` and `python3 scripts/validate_index_integrity.py`
- **Changing calibration**: Update the calibration tests in `test_stage_4_build_review_prompt.py` (stage 4 loads the `_calibration/` examples)
- **Adding a new journal/topic**: Update `journals.json` and test with stage 1 validation

---

## Local Development Setup

### Prerequisites

- **Python 3.12** (the version CI uses; no older version is tested)
- **Git**
- **Hugo Extended** (for site builds, optional)
- **API Keys** (for running the review pipeline):
  - `OPENROUTER_API_KEY` — Required for AI review (get from [openrouter.ai](https://openrouter.ai))
  - `GITHUB_TOKEN` — Required for GitHub API (create a [personal access token](https://github.com/settings/tokens))
  - `S2_API_KEY` — Optional, for Semantic Scholar higher rate limits

### Clone the Repository

```bash
git clone https://github.com/buildngrowsv/pubroot-website.git
cd pubroot-website
```

### Install Python Dependencies

```bash
pip install -r _review_agent/requirements.txt
```

This installs:
- `openai` (for OpenRouter API)
- `arxiv` (for arXiv search)
- `requests` (for GitHub and Semantic Scholar APIs)
- `PyYAML` (for config parsing)

### Running the MCP server locally

The read-only stdio MCP server is `_mcp_server/mcp_peer_review_server.py`.
Install its separate dependencies, then start it from the repository root:

```bash
python3 -m pip install -r _mcp_server/requirements.txt
python3 _mcp_server/mcp_peer_review_server.py
```

A stdio MCP client manages this process and sends requests on stdin; this is not
an HTTP server and does not open a dashboard. Configure the Python interpreter
from the environment where you installed the dependencies. For example, replace
both placeholder paths in this generic client configuration:

```json
{
  "mcpServers": {
    "pubroot": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/pubroot-website/_mcp_server/mcp_peer_review_server.py"],
      "env": {
        "REPO_MODE": "local",
        "LOCAL_REPO_PATH": "/path/to/pubroot-website"
      }
    }
  }
}
```

Configuration is read when the server starts:

| Variable | Default | Meaning |
|----------|---------|---------|
| `REPO_MODE` | `local` | `local` reads this clone's JSON files and reviews; `remote` fetches public data from GitHub. |
| `LOCAL_REPO_PATH` | Repository root, resolved from the server file's location | Root directory for local-mode data. It does not depend on the client's working directory. |
| `GITHUB_REPO` | `buildngrowsv/pubroot-website` | `owner/repo` for remote mode; data is read from its `main` branch through `raw.githubusercontent.com`. |
| `CACHE_TTL_SECONDS` | `300` | Integer lifetime of cached JSON responses, in seconds. Restart the server after changing configuration. |
| `LOG_LEVEL` | `INFO` | Python logging level; operational logs go to stderr. |

For remote mode, set `REPO_MODE` to `remote` and `GITHUB_REPO` to the public
repository to read. `LOCAL_REPO_PATH` is only used for local-mode data. Remote
reads require network access; local mode is useful for working with a clone.

The six registered tool names are `search_papers`, `verify_claim`, `get_review`,
`get_contributor_reputation`, `get_related_work`, and `get_submission_guide`.

Run the isolated MCP tests from the repository root:

```bash
python3 -m pytest _mcp_server/test_mcp_peer_review_server.py -q
```

These tests mock the MCP SDK and network requests. They check tool behavior and
data loading; a passing result does not establish a client's stdio interoperability.

### Running the Review Pipeline Locally

**Set environment variables**:

```bash
export OPENROUTER_API_KEY="your-key-here"
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPOSITORY="buildngrowsv/pubroot-website"
export S2_API_KEY="your-semantic-scholar-key"  # Optional
```

**Run the pipeline on an issue**:

Point `GITHUB_REPOSITORY` at **your own fork** and a test issue there. The pipeline posts comments, adds labels, closes issues, and on acceptance opens and merges a PR in whatever repo it targets. Run it from the **repository root**, because it reads `journals.json` from `GITHUB_WORKSPACE`, or from the current directory when that is unset:

```bash
python3 _review_agent/review_pipeline_main.py <issue_number>
```

**Run without API keys** (for testing parse/validate stages only):

You can test stages 1-4 without API keys:

```bash
# Stage 1: parse a saved issue body (no API calls; run from repo root)
python3 -c "import sys; sys.path.insert(0, '_review_agent'); \
from stage_1_parse_and_filter import parse_and_filter_submission; \
print(parse_and_filter_submission(open('issue_body.md').read(), '.', 'your-github-handle'))"
```

`parse_and_filter_submission(issue_body, repo_root, issue_author, paper_id=None)` takes the raw issue Markdown, not an issue number.

### Running Tests

```bash
# All tests from repository root
python3 -m pytest _review_agent/

# Specific test file
python3 -m pytest _review_agent/test_stage_1_parse_and_filter.py -v

# With coverage
python3 -m pytest _review_agent/ --cov=_review_agent --cov-report=html
```

**Install pytest** if needed:

```bash
pip install pytest pytest-cov
```

### Building the Hugo Site Locally

The static site is built with Hugo and deployed to GitHub Pages.

1. **Install Hugo Extended**:
   - macOS: `brew install hugo`
   - Linux: Download from [gohugo.io](https://gohugo.io/installation/)
   - Verify: `hugo version` (must be Extended edition)

2. **Build the site**:

   From the repository root (same as `publish.yml`):

   ```bash
   hugo --source _site_theme --destination ../public --minify
   ```

3. **Serve locally**:

   ```bash
   hugo server --source _site_theme --buildDrafts
   ```

   Visit `http://localhost:1313`

### Running Pagefind (Client-Side Search)

Pagefind generates the client-side search index:

```bash
hugo --source _site_theme --destination ../public --minify
npx pagefind --site public --output-subdir _pagefind
```

Then serve with a local HTTP server:

```bash
python3 -m http.server -d public 8000
```

### Linting and Code Style

**No automated linters are configured in CI** as of November 2026, but clean Python code is expected:

- Follow PEP 8 style guidelines
- Use descriptive variable names
- Add docstrings to functions
- Keep functions focused and small
- Use type hints where helpful

To lint manually:

```bash
# Install linters
pip install flake8 black

# Check formatting
black --check _review_agent/

# Lint
flake8 _review_agent/ --max-line-length=120
```

---

## Pull Request Guidelines

### Before Opening a PR

1. **Create a branch** from `main`:
   ```bash
   git checkout -b your-feature-name
   ```

2. **Make focused changes**:
   - Small, single-purpose PRs are easier to review
   - Don't mix feature work with unrelated refactors

3. **Write or update tests**:
   - New features need test coverage
   - Bug fixes should include a regression test
   - Run `pytest _review_agent/` before committing

4. **Update documentation**:
   - If you change behavior, update relevant docs (README.md, this file, Editorial Guidelines)
   - Add comments explaining non-obvious code

5. **Test locally**:
   - Run the full test suite: `python3 -m pytest _review_agent/`
   - If you changed the site, build it with Hugo
   - Check that your changes don't break existing papers

### Opening the PR

1. **Push your branch**:
   ```bash
   git add .
   git commit -m "Clear description of what changed and why"
   git push -u origin your-feature-name
   ```

2. **Open a PR on GitHub**:
   - Use a clear title (e.g., "Fix stage 2 novelty check rate limiting")
   - Reference related issues (e.g., "Fixes #123")
   - Describe what you changed and why
   - Explain any non-obvious implementation choices
   - Note any breaking changes

3. **Checks**:
   - No CI workflow runs the test suite on PRs today, so paste your local `pytest` result in the PR description

### PR Review Process

- Maintainers will review your code
- Address feedback by pushing new commits
- Once approved, a maintainer will merge
- Small fixes (typos, docs) may be merged quickly
- Larger changes may need discussion or testing

### After Merge

- Maintainers handle deployment (`publish.yml` rebuilds and deploys GitHub Pages when a merge to `main` touches `papers/`, `reviews/`, `_site_theme/`, the index/journal JSON files, or `publish.yml` itself)
- Your contribution will appear in the site build within minutes
- Thank you for contributing!

---

## Code of Conduct

Pubroot does not currently have a formal Code of Conduct, but we expect all contributors to:

- Be respectful and constructive in discussions
- Focus on the work, not personal attacks
- Welcome newcomers and help them learn the codebase
- Assume good intent in others' contributions
- Follow GitHub's [Community Guidelines](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines)

Violations can be reported to the repository maintainers.

---

## Questions?

- **For general questions**: Open an [Issue](https://github.com/buildngrowsv/pubroot-website/issues) (Discussions are not enabled)
- **For bugs or feature requests**: Open an [Issue](https://github.com/buildngrowsv/pubroot-website/issues)
- **For sensitive matters**: Contact the repository owner via their GitHub profile; don't post security issues publicly

**Note**: Only submissions (the [submission template](https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml), `pubroot submit`, or an issue body with the form's `### Article Title` and `### Category` headers) are reviewed. Other issues are normal project issues.

Thank you for contributing to Pubroot! 🚀
