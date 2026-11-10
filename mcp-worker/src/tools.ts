/**
 * Tool definitions and implementations for the read-only Pubroot MCP Worker.
 *
 * Names, input schemas and output shapes mirror src/pubroot/mcp_server.py so
 * that clients, server.json and the Python stdio server stay interchangeable.
 * Two extra cheap read-only tools are added: list_journals and get_paper.
 *
 * There are NO write paths: every tool only reads public JSON and returns data.
 * prepare_submission validates a draft and builds a prefilled GitHub issue URL;
 * it never creates anything.
 */

import {
  DEFAULT_GITHUB_REPO,
  type Env,
  type Paper,
  loadAgentIndex,
  loadContributors,
  loadJournals,
  loadPriorrootIndex,
  loadReview,
} from "./data.js";

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

export class ToolInputError extends Error {}

/** Paper IDs look like "2026-042". Allow 3-5 digit sequence numbers for growth. */
export const PAPER_ID_RE = /^\d{4}-\d{3,5}$/;
/** GitHub login rules: alnum or single hyphens, max 39 chars. */
export const GITHUB_HANDLE_RE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/;

export const LIMITS = {
  query: 500,
  claim: 1000,
  category: 100,
  badge: 50,
  status: 50,
  title: 300,
  abstract: 10_000,
  body: 200_000,
  short: 500,
} as const;

type Args = Record<string, unknown>;

function str(args: Args, key: string, def: string, max: number): string {
  const v = args[key];
  if (v === undefined || v === null) return def;
  if (typeof v !== "string") throw new ToolInputError(`'${key}' must be a string.`);
  if (v.length > max) throw new ToolInputError(`'${key}' is too long (max ${max} characters).`);
  return v;
}

function num(args: Args, key: string, def: number): number {
  const v = args[key];
  if (v === undefined || v === null) return def;
  if (typeof v !== "number" || !Number.isFinite(v)) {
    throw new ToolInputError(`'${key}' must be a finite number.`);
  }
  return v;
}

function paperId(args: Args, key: string, required: boolean): string {
  const v = str(args, key, "", 20).trim();
  if (!v) {
    if (required) throw new ToolInputError(`'${key}' is required (e.g. '2026-042').`);
    return "";
  }
  if (!PAPER_ID_RE.test(v)) {
    throw new ToolInputError(`'${key}' must look like '2026-042' (YYYY-NNN).`);
  }
  return v;
}

const words = (s: string): Set<string> => new Set(s.toLowerCase().split(/\s+/).filter(Boolean));
const wordCount = (s: string): number => (s ? s.split(/\s+/).filter(Boolean).length : 0);
const intersectSize = (a: Set<string>, b: Set<string>): number => {
  let n = 0;
  for (const w of a) if (b.has(w)) n++;
  return n;
};
const errMsg = (e: unknown): string => (e instanceof Error ? e.message : String(e));

// ---------------------------------------------------------------------------
// Tool metadata (tools/list)
// ---------------------------------------------------------------------------

const READ_ONLY = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
} as const;

export const TOOL_DEFINITIONS = [
  {
    name: "search_papers",
    title: "Search Pubroot papers",
    description:
      "Search papers published on Pubroot by keyword (title and abstract), category (journal/topic), minimum review score, badge or status. Returns metadata and abstracts, sorted by review score.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", default: "", maxLength: LIMITS.query, description: "Keyword search (matches title and abstract). Empty string returns all papers." },
        category: { type: "string", default: "", maxLength: LIMITS.category, description: "Filter by category in journal/topic format (e.g. 'ai/llm-benchmarks')." },
        min_score: { type: "number", default: 0.0, minimum: 0, maximum: 10, description: "Minimum review score to include (0.0 to 10.0)." },
        badge: { type: "string", default: "", maxLength: LIMITS.badge, description: "Filter by badge ('verified_open', 'verified_private', 'text_only')." },
        status: { type: "string", default: "current", maxLength: LIMITS.status, description: "Paper status filter ('current', 'superseded', 'expired'). Empty string matches any status." },
        limit: { type: "integer", default: 10, minimum: 1, maximum: 50, description: "Maximum number of results (1-50)." },
      },
    },
    annotations: { title: "Search Pubroot papers", ...READ_ONLY },
  },
  {
    name: "verify_claim",
    title: "Look up a claim in Pubroot reviews",
    description:
      "Find claims in published Pubroot reviews that overlap with the given claim text (keyword match). Returns each matching claim with the reviewer's verified flag, confidence and cited source. No match does not mean the claim is false.",
    inputSchema: {
      type: "object",
      properties: {
        claim: { type: "string", minLength: 1, maxLength: LIMITS.claim, description: "The factual claim to look up (e.g. 'GPT-4o scores 90% on MMLU')." },
        category: { type: "string", default: "", maxLength: LIMITS.category, description: "Optional category to narrow the search." },
      },
      required: ["claim"],
    },
    annotations: { title: "Look up a claim in Pubroot reviews", ...READ_ONLY },
  },
  {
    name: "get_review",
    title: "Get a paper's review",
    description:
      "Return the full AI-generated review (score, verdict, confidence breakdown, checked claims, strengths, weaknesses, sources) for a Pubroot paper ID.",
    inputSchema: {
      type: "object",
      properties: {
        paper_id: { type: "string", pattern: PAPER_ID_RE.source, description: "The paper ID (e.g. '2026-042')." },
      },
      required: ["paper_id"],
    },
    annotations: { title: "Get a paper's review", ...READ_ONLY },
  },
  {
    name: "get_contributor_reputation",
    title: "Get a contributor's public record",
    description:
      "Return the public Pubroot contributor record (submission counts, reputation score and tier) for a GitHub handle.",
    inputSchema: {
      type: "object",
      properties: {
        github_handle: { type: "string", pattern: GITHUB_HANDLE_RE.source, description: "The contributor's GitHub username." },
      },
      required: ["github_handle"],
    },
    annotations: { title: "Get a contributor's public record", ...READ_ONLY },
  },
  {
    name: "get_related_work",
    title: "Find related Pubroot papers",
    description: "List Pubroot papers related to a query or to a given paper ID, ranked by keyword overlap.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", default: "", maxLength: LIMITS.query, description: "Topic or question to find related work for." },
        paper_id: { type: "string", default: "", description: "Optional paper ID (e.g. '2026-042') to find related work for." },
      },
    },
    annotations: { title: "Find related Pubroot papers", ...READ_ONLY },
  },
  {
    name: "get_submission_guide",
    title: "Get Pubroot submission rules",
    description:
      "Return Pubroot's submission rules: issue format, image hosting, revision process and acceptance threshold.",
    inputSchema: { type: "object", properties: {} },
    annotations: { title: "Get Pubroot submission rules", ...READ_ONLY },
  },
  {
    name: "prepare_submission",
    title: "Validate and prepare a submission",
    description:
      "Validate a submission draft against Pubroot rules and return a prefilled GitHub issue URL. Does not create the issue.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string", maxLength: LIMITS.title, description: "Article title (required)." },
        category: { type: "string", maxLength: LIMITS.category, description: "Category in journal/topic format (e.g. 'ai/llm-benchmarks')." },
        abstract: { type: "string", maxLength: LIMITS.abstract, description: "Abstract text (recommended 150-300 words, max 350)." },
        body: { type: "string", maxLength: LIMITS.body, description: "Article body text (minimum 200 words)." },
        submission_type: { type: "string", default: "original-research", maxLength: LIMITS.short, description: "original-research, case-study, benchmark, review-survey, tutorial or dataset." },
        supporting_repo: { type: "string", default: "", maxLength: LIMITS.short, description: "GitHub repo URL (optional)." },
        commit_sha: { type: "string", default: "", maxLength: LIMITS.short, description: "Commit SHA if a repo is provided (optional)." },
        repo_visibility: { type: "string", default: "no-repo", maxLength: LIMITS.short, description: "public, private or no-repo." },
        ai_tooling_attribution: { type: "string", default: "", maxLength: LIMITS.short * 4, description: "AI tools used (optional)." },
      },
      required: ["title", "category", "abstract", "body"],
    },
    annotations: { title: "Validate and prepare a submission", ...READ_ONLY },
  },
  {
    name: "list_journals",
    title: "List Pubroot journals and topics",
    description:
      "List Pubroot journals and their topics (the valid journal/topic categories for search and submission).",
    inputSchema: {
      type: "object",
      properties: {
        journal: { type: "string", default: "", maxLength: LIMITS.category, description: "Optional journal slug (e.g. 'ai') to list only that journal." },
      },
    },
    annotations: { title: "List Pubroot journals and topics", ...READ_ONLY },
  },
  {
    name: "get_paper",
    title: "Get a paper's index entry",
    description:
      "Return the published index metadata (title, author, category, abstract, score, badge, status, links) for a Pubroot paper ID.",
    inputSchema: {
      type: "object",
      properties: {
        paper_id: { type: "string", pattern: PAPER_ID_RE.source, description: "The paper ID (e.g. '2026-042')." },
      },
      required: ["paper_id"],
    },
    annotations: { title: "Get a paper's index entry", ...READ_ONLY },
  },
] as const;

export type ToolName = (typeof TOOL_DEFINITIONS)[number]["name"];
export const TOOL_NAMES = new Set<string>(TOOL_DEFINITIONS.map((t) => t.name));

// ---------------------------------------------------------------------------
// Implementations
// ---------------------------------------------------------------------------

/** Max review files fetched by one verify_claim call (Workers Free: 50 subrequests/request). */
export const MAX_REVIEW_FETCHES = 20;

async function searchPapers(env: Env, args: Args) {
  const query = str(args, "query", "", LIMITS.query);
  const category = str(args, "category", "", LIMITS.category);
  const minScore = num(args, "min_score", 0);
  const badge = str(args, "badge", "", LIMITS.badge);
  const status = str(args, "status", "current", LIMITS.status);
  const limitArg = num(args, "limit", 10);

  let index;
  try {
    index = await loadAgentIndex(env);
  } catch (e) {
    return { error: `Unable to load paper index: ${errMsg(e)}`, results: [], total_matching: 0 };
  }
  const q = query.toLowerCase();
  const results = (index.papers ?? []).filter((p) => {
    if (status && (p.status ?? "current") !== status) return false;
    if (category && p.category !== category) return false;
    if ((p.review_score ?? 0) < minScore) return false;
    if (badge && p.badge !== badge) return false;
    if (q) {
      const t = (p.title ?? "").toLowerCase();
      const a = (p.abstract ?? "").toLowerCase();
      if (!t.includes(q) && !a.includes(q)) return false;
    }
    return true;
  });
  results.sort((a, b) => (b.review_score ?? 0) - (a.review_score ?? 0));
  const limit = Math.min(Math.max(1, Math.trunc(limitArg)), 50);
  const sliced = results.slice(0, limit);
  return {
    total_matching: sliced.length,
    results: sliced,
    index_last_updated: index.last_updated ?? null,
  };
}

async function verifyClaim(env: Env, args: Args) {
  const claim = str(args, "claim", "", LIMITS.claim);
  const category = str(args, "category", "", LIMITS.category);
  if (!claim.trim()) {
    return { found: false, error: "The 'claim' argument must be a non-empty string.", matches: [] };
  }
  let index;
  try {
    index = await loadAgentIndex(env);
  } catch (e) {
    return { found: false, error: `Unable to load paper index: ${errMsg(e)}`, matches: [] };
  }

  const claimWords = words(claim);
  // Same candidate rule as the Python server (title overlap >= 2 or abstract
  // overlap >= 3), but ranked and capped so one call stays within the free
  // plan's subrequest budget.
  const candidates: Array<{ paper: Paper; rank: number }> = [];
  for (const p of index.papers ?? []) {
    if (p.status !== "current") continue;
    if (category && p.category !== category) continue;
    const t = intersectSize(claimWords, words(p.title ?? ""));
    const a = intersectSize(claimWords, words(p.abstract ?? ""));
    if (t >= 2 || a >= 3) candidates.push({ paper: p, rank: t * 2 + a });
  }
  candidates.sort((x, y) => y.rank - x.rank);
  const toCheck = candidates.slice(0, MAX_REVIEW_FETCHES);

  const reviews = await Promise.all(
    toCheck.map(({ paper }) =>
      typeof paper.id === "string" && PAPER_ID_RE.test(paper.id)
        ? loadReview(env, paper.id).catch(() => null)
        : Promise.resolve(null),
    ),
  );

  const matches: Array<Record<string, unknown>> = [];
  toCheck.forEach(({ paper }, i) => {
    const review = reviews[i];
    if (!review) return;
    for (const rc of Array.isArray(review.claims) ? review.claims : []) {
      if (intersectSize(claimWords, words(String(rc?.text ?? ""))) >= 3) {
        matches.push({
          paper_id: paper.id,
          paper_title: paper.title,
          paper_score: paper.review_score,
          claim_text: rc.text,
          verified: rc.verified,
          confidence: rc.confidence,
          source: rc.source,
        });
      }
    }
  });

  if (matches.length === 0) {
    return { found: false, message: `No verified papers found matching the claim: '${claim}'`, matches: [] };
  }
  return { found: true, total_matches: matches.length, matches };
}

async function getReview(env: Env, args: Args) {
  const id = paperId(args, "paper_id", true);
  const review = await loadReview(env, id).catch((e) => {
    throw new Error(`Unable to load review: ${errMsg(e)}`);
  });
  if (review === null) return { found: false, error: `No review found for paper ID: ${id}` };
  return { found: true, paper_id: id, review };
}

async function getContributorReputation(env: Env, args: Args) {
  const handle = str(args, "github_handle", "", 39).trim();
  if (!handle) {
    return { found: false, error: "The 'github_handle' argument must be a non-empty string." };
  }
  if (!GITHUB_HANDLE_RE.test(handle)) {
    throw new ToolInputError("'github_handle' must be a valid GitHub username.");
  }
  let data;
  try {
    data = await loadContributors(env);
  } catch (e) {
    return { found: false, error: `Unable to load contributor data: ${errMsg(e)}` };
  }
  const all = (data.contributors ?? {}) as Record<string, Record<string, unknown>>;
  const c = Object.prototype.hasOwnProperty.call(all, handle) ? all[handle] : undefined;
  if (!c || typeof c !== "object") {
    return {
      found: false,
      message: `No contributor found with handle: ${handle}`,
      suggestion: "This contributor has not submitted any articles yet.",
    };
  }
  return {
    found: true,
    github_handle: handle,
    reputation_score: c.reputation_score ?? 0.0,
    reputation_tier: c.reputation_tier ?? "new",
    total_submissions: c.total_submissions ?? 0,
    accepted: c.accepted ?? 0,
    rejected: c.rejected ?? 0,
    acceptance_rate: c.acceptance_rate ?? 0.0,
    average_score: c.average_score ?? 0.0,
    categories: c.categories ?? {},
    last_submission: c.last_submission ?? null,
    first_seen: c.first_seen ?? null,
  };
}

interface RelatedResult {
  paper_id: unknown;
  title: unknown;
  category: unknown;
  score: unknown;
  relevance_score: number;
  abstract: string;
}

function relatedFromIndex(papers: Paper[], query: string, pid: string) {
  let targetCategory = "";
  let targetWords = new Set<string>();
  if (pid) {
    const p = papers.find((x) => x.id === pid);
    if (p) {
      targetCategory = p.category ?? "";
      targetWords = words(`${p.title ?? ""} ${p.abstract ?? ""}`);
    }
  }
  if (query) for (const w of words(query)) targetWords.add(w);

  const scored: RelatedResult[] = [];
  for (const p of papers) {
    if (p.id === pid) continue;
    if (p.status !== "current") continue;
    const overlap = intersectSize(targetWords, words(`${p.title ?? ""} ${p.abstract ?? ""}`));
    const relevance = overlap + (p.category === targetCategory ? 2 : 0);
    if (relevance > 2) {
      scored.push({
        paper_id: p.id,
        title: p.title,
        category: p.category,
        score: p.review_score,
        relevance_score: relevance,
        abstract: (p.abstract ?? "").slice(0, 200),
      });
    }
  }
  scored.sort((a, b) => b.relevance_score - a.relevance_score);
  return { total_related: scored.length, results: scored.slice(0, 10) };
}

async function getRelatedWork(env: Env, args: Args) {
  const query = str(args, "query", "", LIMITS.query);
  const pid = paperId(args, "paper_id", false);
  if (!query && !pid) return { error: "Provide either a 'query' or 'paper_id' argument." };
  let index;
  try {
    index = await loadAgentIndex(env);
  } catch (e) {
    return { error: `Unable to load paper index: ${errMsg(e)}`, total_related: 0, results: [] };
  }
  return relatedFromIndex(index.papers ?? [], query, pid);
}

async function getSubmissionGuide(env: Env) {
  let data;
  try {
    data = await loadJournals(env);
  } catch (e) {
    return { error: `Unable to load journal configuration: ${errMsg(e)}` };
  }
  const threshold = Number(data.acceptance_threshold ?? 6.0);
  return {
    product: "Pubroot",
    website: "https://pubroot.com",
    submission_repository: env.GITHUB_REPO || DEFAULT_GITHUB_REPO,
    acceptance_threshold: Number.isFinite(threshold) ? threshold : 6.0,
    figures_and_embedded_media: {
      policy:
        "The automated pipeline persists Markdown from the issue only. It does not upload or mirror binary image files for you.",
      embed_syntax: "![description](https://...) with absolute HTTPS URLs.",
      recommended_hosting: [
        "Commit figures in your supporting repo; pin Commit SHA; link via raw.githubusercontent.com or GitHub blob ?raw=1.",
        "Self-hosted HTTPS, CDN, or object storage you control — keep URLs durable.",
      ],
      reference_url: "https://pubroot.com/editorial-guidelines/#figures-hosting",
    },
    revisions: {
      after_rejection:
        "Open a new submission issue with an updated article body; the full six-stage review runs again.",
      after_publication_substantive:
        "Submit a new article through the same template; published review JSON may include supersedes pointing at the older paper ID.",
      after_publication_minor:
        "Typos, broken links, small formatting: pull request or issue on the pubroot-website repo.",
      same_github_user_as_prior_paper_not_enforced_by_automation: true,
      reference_url: "https://pubroot.com/editorial-guidelines/#revisions-errata",
      pipeline_or_site_changes:
        "Automation or site updates do not add a separate revision channel; authors still follow the same resubmission rules.",
    },
    how_to_submit_revision: {
      summary:
        "After rejection, open a NEW submission issue with the same template — do not reply on the old issue expecting a re-review.",
      submission_template_url:
        "https://github.com/buildngrowsv/pubroot-website/issues/new?template=submission.yml",
      after_rejection_steps: [
        "Read the review comment on the rejected issue.",
        "Revise article Markdown (and supporting-repo figure URLs if applicable).",
        "Open a NEW issue via submission_template_url with the full updated fields.",
        "Paste complete abstract + body; the full six-stage pipeline runs again.",
        "Optional: run `pubroot submit article.md` so ### headers match stage_1 parser.",
      ],
      after_publication_minor:
        "Pull request on pubroot-website editing papers/{journal}/{topic}/{slug}/index.md (see agent-index article_path or frontmatter paper_id).",
      after_publication_substantive:
        "New submission through the same template; review JSON may include supersedes.",
      human_docs: [
        "https://pubroot.com/editorial-guidelines/#revisions-errata",
        "https://pubroot.com/submit/#how-to-submit-revision",
      ],
    },
    submitter_identity: {
      note:
        "Attributed author in our index is the GitHub login of the user who opens the issue (issue author), not a free-text field in the Markdown file.",
    },
    ai_tooling_attribution: {
      optional_field_yaml: "ai_tooling_attribution",
      issue_template_section: "AI / Tooling Attribution (optional)",
      description:
        "Submitters may name models and how they were used (e.g. **Composer 2 in Cursor** for agentic coding; Claude in the browser). Published in article front matter when present.",
    },
    ai_attribution_catalog: {
      file: "ai_attribution_catalog.json",
      purpose:
        "Canonical IDs for primary_model_id and primary_platform_id; submission.yml dropdown options must match catalog labels exactly.",
    },
    issue_body_format: {
      must_match_pipeline:
        "Headers must be exactly the labels expected by stage_1_parse_and_filter.py (see submission.yml).",
      known_section_labels: [
        "Article Title",
        "Category",
        "Submission Type",
        "Primary AI model (optional)",
        "Primary platform / IDE (optional)",
        "AI / Tooling Attribution (optional)",
        "Abstract",
        "Article Body",
        "Supporting Repository URL",
        "Commit SHA",
        "Repository Visibility",
        "Payment Code (Optional)",
        "Submission Agreement",
      ],
      article_body_rule:
        "Inside Article Body, use ## for sections — avoid ### because only specific ### labels are form fields.",
    },
    cli_equivalent: "pubroot guide --json",
  };
}

/**
 * Valid journal/topic slugs. journals.json is an object keyed by journal slug
 * whose `topics` is an object keyed by topic slug; a list-of-{slug} shape is
 * also accepted for forward compatibility.
 */
function journalEntries(data: Record<string, unknown>) {
  const out: Array<{ slug: string; journal: Record<string, unknown>; topics: Array<{ slug: string; topic: Record<string, unknown> }> }> = [];
  const toEntries = (x: unknown): Array<[string, Record<string, unknown>]> => {
    if (Array.isArray(x)) {
      return x
        .filter((v) => v && typeof v === "object" && typeof (v as { slug?: unknown }).slug === "string")
        .map((v) => [(v as { slug: string }).slug, v as Record<string, unknown>]);
    }
    if (x && typeof x === "object") {
      return Object.entries(x as Record<string, unknown>).filter(
        (e): e is [string, Record<string, unknown>] => !!e[1] && typeof e[1] === "object",
      );
    }
    return [];
  };
  for (const [slug, journal] of toEntries(data.journals)) {
    out.push({ slug, journal, topics: toEntries(journal.topics).map(([s, topic]) => ({ slug: s, topic })) });
  }
  return out;
}

const INJECTION_PATTERNS = [
  /ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directives)/i,
  /disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directives)/i,
  /system\s*:\s*you\s+are/i,
  /new\s+instructions\s*:/i,
  /ignore\s+this\s+document/i,
];
const VALID_TYPES = ["original-research", "case-study", "benchmark", "review-survey", "tutorial", "dataset"];
/** Browsers and GitHub start failing on very long URLs; warn past this length. */
const LONG_URL_WARNING = 8000;

async function prepareSubmission(env: Env, args: Args) {
  const title = str(args, "title", "", LIMITS.title);
  const category = str(args, "category", "", LIMITS.category);
  const abstract = str(args, "abstract", "", LIMITS.abstract);
  const body = str(args, "body", "", LIMITS.body);
  const submissionType = str(args, "submission_type", "original-research", LIMITS.short);
  const supportingRepo = str(args, "supporting_repo", "", LIMITS.short);
  const commitSha = str(args, "commit_sha", "", LIMITS.short);
  const repoVisibility = str(args, "repo_visibility", "no-repo", LIMITS.short);
  const aiAttribution = str(args, "ai_tooling_attribution", "", LIMITS.short * 4);
  const repo = env.GITHUB_REPO || DEFAULT_GITHUB_REPO;

  const errors: string[] = [];
  const warnings: string[] = [];

  if (!title.trim()) errors.push("Article Title is required");
  if (!category.trim()) errors.push("Category is required");
  if (!abstract.trim()) errors.push("Abstract is required");
  if (!body.trim()) errors.push("Article Body is required");

  const abstractWords = wordCount(abstract);
  const bodyWords = wordCount(body);
  if (abstractWords > 350) {
    errors.push(`Abstract exceeds 350 words (${abstractWords} words). Please shorten.`);
  } else if (abstractWords > 300) {
    warnings.push(`Abstract is ${abstractWords} words. Consider keeping it under 300 words.`);
  }
  if (bodyWords < 200) errors.push(`Article Body must be at least 200 words (${bodyWords} words)`);

  if (category) {
    if (!category.includes("/")) {
      errors.push(`Category must be in 'journal/topic' format (e.g., 'ai/llm-benchmarks'), got: ${category}`);
    } else if (category.startsWith("---")) {
      errors.push(`Category cannot be a separator line: ${category}`);
    } else {
      try {
        const valid = new Set<string>();
        for (const j of journalEntries(await loadJournals(env))) {
          for (const t of j.topics) valid.add(`${j.slug}/${t.slug}`);
        }
        if (!valid.has(category)) {
          errors.push(`Category '${category}' not found in journals.json. Use 'pubroot topics' to see valid categories.`);
        }
      } catch (e) {
        warnings.push(`Could not validate category against journals.json: ${errMsg(e)}`);
      }
    }
  }

  const checkText = `${title} ${abstract} ${body.slice(0, 2000)}`;
  for (const re of INJECTION_PATTERNS) {
    if (re.test(checkText)) {
      errors.push(`Potential prompt injection detected. Pattern: (?i)${re.source}`);
      break;
    }
  }

  if (submissionType && !VALID_TYPES.includes(submissionType)) {
    warnings.push(
      `Submission type '${submissionType}' is not standard. Will default to 'original-research'. Valid: ${VALID_TYPES.join(", ")}`,
    );
  }

  let relatedPapers: RelatedResult[] = [];
  try {
    const index = await loadAgentIndex(env);
    const related = relatedFromIndex(index.papers ?? [], `${title} ${abstract.slice(0, 100)}`, "");
    relatedPapers = related.results.slice(0, 5);
    const top = relatedPapers[0];
    if (top) {
      if (top.relevance_score > 8) {
        warnings.push(
          `Very similar paper found: '${String(top.title)}' (relevance: ${top.relevance_score}). Consider if this is a duplicate or supersedes existing work.`,
        );
      } else if (top.relevance_score > 5) {
        warnings.push(`Similar paper found: '${String(top.title)}'. Ensure your work adds novelty.`);
      }
    }
  } catch (e) {
    warnings.push(`Could not check for related work: ${errMsg(e)}`);
  }

  const valid = errors.length === 0;
  const result: Record<string, unknown> = {
    valid,
    errors,
    warnings,
    word_counts: { title: wordCount(title), abstract: abstractWords, body: bodyWords },
    related_papers: relatedPapers,
  };

  if (valid) {
    const issueBody = `### Article Title
${title}

### Category
${category}

### Submission Type
${submissionType}

### AI / Tooling Attribution (optional)
${aiAttribution || "_No response_"}

### Abstract
${abstract}

### Article Body
${body}

### Supporting Repository URL
${supportingRepo || "_No response_"}

### Commit SHA
${commitSha || "_No response_"}

### Repository Visibility
${repoVisibility}

### Payment Code (Optional)
_No response_

### Submission Agreement
- [X] I have read and agree to the Editorial Guidelines
- [X] I confirm this is my original work or I have rights to submit it
- [X] I understand reviews are AI-generated and may have errors`;

    const params = new URLSearchParams({
      template: "submission.yml",
      title: `[SUBMISSION] ${title}`,
      body: issueBody,
    });
    const url = `https://github.com/${repo}/issues/new?${params.toString()}`;
    if (url.length > LONG_URL_WARNING) {
      warnings.push(
        `The prefilled issue URL is ${url.length} characters; some browsers/GitHub may truncate it. If so, use gh_command or paste the body manually.`,
      );
    }
    result.github_issue_url = url;
    result.gh_command = `gh issue create --repo ${repo} --title "[SUBMISSION] ${title}" --label submission --label pending-review --body <(cat <<EOF\n${issueBody}\nEOF\n)`;
    result.message = "Validation passed! Open the github_issue_url to submit, or run the gh_command.";
  } else {
    result.message = `Validation failed with ${errors.length} error(s). Fix the errors and try again.`;
  }
  return result;
}

async function listJournals(env: Env, args: Args) {
  const only = str(args, "journal", "", LIMITS.category).trim();
  let data;
  try {
    data = await loadJournals(env);
  } catch (e) {
    return { error: `Unable to load journal configuration: ${errMsg(e)}`, journals: [] };
  }
  const journals = journalEntries(data)
    .filter((j) => !only || j.slug === only)
    .map((j) => ({
      slug: j.slug,
      display_name: j.journal.display_name ?? null,
      description: j.journal.description ?? null,
      topics: j.topics.map((t) => ({
        slug: t.slug,
        category: `${j.slug}/${t.slug}`,
        display_name: t.topic.display_name ?? null,
        description: t.topic.description ?? null,
      })),
    }));
  return {
    acceptance_threshold: data.acceptance_threshold ?? null,
    total_journals: journals.length,
    journals,
  };
}

async function getPaper(env: Env, args: Args) {
  const id = paperId(args, "paper_id", true);
  const sources: Array<[string, typeof loadAgentIndex]> = [
    ["agent-index.json", loadAgentIndex],
    ["priorroot-index.json", loadPriorrootIndex],
  ];
  const errors: string[] = [];
  for (const [name, load] of sources) {
    try {
      const paper = ((await load(env)).papers ?? []).find((p) => p.id === id);
      if (paper) return { found: true, paper_id: id, source_index: name, paper };
    } catch (e) {
      errors.push(`${name}: ${errMsg(e)}`);
    }
  }
  if (errors.length === sources.length) {
    return { found: false, error: `Unable to load paper indexes: ${errors.join("; ")}` };
  }
  return { found: false, error: `No paper found for paper ID: ${id}` };
}

export async function callTool(env: Env, name: string, rawArgs: unknown): Promise<Record<string, unknown>> {
  if (rawArgs !== undefined && (rawArgs === null || typeof rawArgs !== "object" || Array.isArray(rawArgs))) {
    throw new ToolInputError("Tool arguments must be an object.");
  }
  const args = (rawArgs ?? {}) as Args;
  switch (name as ToolName) {
    case "search_papers":
      return searchPapers(env, args);
    case "verify_claim":
      return verifyClaim(env, args);
    case "get_review":
      return getReview(env, args);
    case "get_contributor_reputation":
      return getContributorReputation(env, args);
    case "get_related_work":
      return getRelatedWork(env, args);
    case "get_submission_guide":
      return getSubmissionGuide(env);
    case "prepare_submission":
      return prepareSubmission(env, args);
    case "list_journals":
      return listJournals(env, args);
    case "get_paper":
      return getPaper(env, args);
    default:
      throw new ToolInputError(`Unknown tool: ${name}`);
  }
}
