/**
 * Upstream data loading for the Pubroot MCP Worker.
 *
 * Mirrors `_load_json` / `_load_review` in src/pubroot/mcp_server.py:
 *   - fetch public JSON files from the repo's raw GitHub URL (DATA_BASE_URL var)
 *   - fresh in-isolate cache for CACHE_TTL_SECONDS (default 600 s)
 *   - stale-if-error: serve the last good copy for up to 24 h if upstream fails
 *
 * Free-plan only: no KV/D1/R2/Durable Objects. Edge caching uses the free
 * `fetch(..., { cf: { cacheTtl } })` option; the in-isolate Map keeps parsed
 * JSON so repeat requests on a warm isolate do no parsing at all (keeps us
 * well inside the 10 ms CPU budget).
 */

export interface Env {
  DATA_BASE_URL?: string;
  GITHUB_REPO?: string;
  CACHE_TTL_SECONDS?: string;
}

export const DEFAULT_DATA_BASE_URL =
  "https://raw.githubusercontent.com/buildngrowsv/pubroot-website/main";
export const DEFAULT_GITHUB_REPO = "buildngrowsv/pubroot-website";

const STALE_IF_ERROR_MS = 24 * 60 * 60 * 1000;
/** Upstream files larger than this are refused (defence against surprises). */
const MAX_UPSTREAM_BYTES = 5 * 1024 * 1024;
/** Cap the number of distinct review files held in memory per isolate. */
const MAX_CACHE_ENTRIES = 256;

/** Hosts we are allowed to fetch from (same allow-list idea as the Python server). */
const ALLOWED_HOSTS = new Set(["raw.githubusercontent.com", "pubroot.com"]);

export class NotFoundError extends Error {}

interface CacheEntry {
  fetchedAt: number;
  data: unknown;
}

const cache = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<unknown>>();

/** Test hook: clear the in-isolate cache. */
export function clearDataCache(): void {
  cache.clear();
  inflight.clear();
}

function ttlMs(env: Env): number {
  const n = Number(env.CACHE_TTL_SECONDS ?? "600");
  return Number.isFinite(n) && n >= 0 ? n * 1000 : 600_000;
}

export function baseUrl(env: Env): string {
  return (env.DATA_BASE_URL || DEFAULT_DATA_BASE_URL).replace(/\/+$/, "");
}

async function fetchJson(env: Env, path: string): Promise<unknown> {
  const url = `${baseUrl(env)}/${path}`;
  const host = new URL(url).hostname;
  if (!ALLOWED_HOSTS.has(host)) {
    throw new Error(`Host ${host} is not in the allow-list`);
  }
  const ttlSeconds = Math.floor(ttlMs(env) / 1000);
  const resp = await fetch(url, {
    headers: { accept: "application/json", "user-agent": "pubroot-mcp-worker" },
    // Free on every plan: ask Cloudflare's edge cache to hold the upstream file.
    cf: { cacheTtl: ttlSeconds, cacheEverything: true },
  } as RequestInit);
  if (resp.status === 404) {
    throw new NotFoundError(`${path} not found`);
  }
  if (!resp.ok) {
    throw new Error(`Upstream returned HTTP ${resp.status} for ${path}`);
  }
  const len = Number(resp.headers.get("content-length") ?? "0");
  if (len > MAX_UPSTREAM_BYTES) {
    throw new Error(`Upstream file ${path} is too large`);
  }
  const text = await resp.text();
  if (text.length > MAX_UPSTREAM_BYTES) {
    throw new Error(`Upstream file ${path} is too large`);
  }
  return JSON.parse(text);
}

/**
 * Load and cache a JSON file from the data source.
 * Throws NotFoundError for 404s (never cached as stale data), other Errors otherwise.
 */
export async function loadJson<T = unknown>(env: Env, path: string): Promise<T> {
  const now = Date.now();
  const entry = cache.get(path);
  if (entry && now - entry.fetchedAt < ttlMs(env)) {
    return entry.data as T;
  }

  let pending = inflight.get(path);
  if (!pending) {
    pending = fetchJson(env, path).finally(() => inflight.delete(path));
    inflight.set(path, pending);
  }

  try {
    const data = await pending;
    if (cache.size >= MAX_CACHE_ENTRIES && !cache.has(path)) {
      // Drop the oldest insertion (Map preserves insertion order).
      const oldest = cache.keys().next().value;
      if (oldest !== undefined) cache.delete(oldest);
    }
    cache.set(path, { fetchedAt: Date.now(), data });
    return data as T;
  } catch (err) {
    if (!(err instanceof NotFoundError) && entry && now - entry.fetchedAt < STALE_IF_ERROR_MS) {
      return entry.data as T; // stale-if-error
    }
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Typed views of the public files
// ---------------------------------------------------------------------------

export interface Paper {
  id?: string;
  title?: string;
  author?: string;
  category?: string;
  abstract?: string;
  review_score?: number;
  badge?: string;
  status?: string;
  [key: string]: unknown;
}

export interface PaperIndex {
  last_updated?: string;
  papers?: Paper[];
  [key: string]: unknown;
}

export interface Review {
  claims?: Array<{ text?: string; verified?: unknown; confidence?: unknown; source?: unknown }>;
  [key: string]: unknown;
}

export const loadAgentIndex = (env: Env) => loadJson<PaperIndex>(env, "agent-index.json");
export const loadPriorrootIndex = (env: Env) => loadJson<PaperIndex>(env, "priorroot-index.json");
export const loadJournals = (env: Env) => loadJson<Record<string, unknown>>(env, "journals.json");
export const loadContributors = (env: Env) =>
  loadJson<Record<string, unknown>>(env, "contributors.json");

/** Returns null when the review file does not exist (mirrors `_load_review`). */
export async function loadReview(env: Env, paperId: string): Promise<Review | null> {
  try {
    const r = await loadJson<Review>(env, `reviews/${paperId}/review.json`);
    return r && typeof r === "object" ? r : null;
  } catch (err) {
    if (err instanceof NotFoundError || err instanceof SyntaxError) return null;
    throw err;
  }
}
