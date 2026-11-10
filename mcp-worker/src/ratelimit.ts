/**
 * Best-effort per-IP rate limiting for the Pubroot MCP Worker.
 *
 * Counters live in isolate memory only: no Rate Limiting binding, KV or Durable
 * Object is used (Workers Free plan). Each Cloudflare isolate keeps its own
 * counters, so limits are approximate; that is fine for abuse damping.
 * Same limits as the Python HTTP server: 60 MCP requests/min, 10 prepare_submission/min.
 */

export const RATE_LIMIT_GENERAL = 60; // MCP POSTs per IP per minute
export const RATE_LIMIT_PREPARE = 10; // prepare_submission calls per IP per minute
const MAX_TRACKED_IPS = 5000;

const buckets = new Map<string, { minute: number; general: number; prepare: number }>();

export function resetRateLimits(): void {
  buckets.clear();
}

export function rateLimited(ip: string, prepareCalls: number): boolean {
  const minute = Math.floor(Date.now() / 60_000);
  let b = buckets.get(ip);
  if (!b || b.minute !== minute) {
    if (buckets.size >= MAX_TRACKED_IPS) {
      for (const [k, v] of buckets) if (v.minute !== minute) buckets.delete(k);
      if (buckets.size >= MAX_TRACKED_IPS) buckets.clear();
    }
    b = { minute, general: 0, prepare: 0 };
    buckets.set(ip, b);
  }
  if (b.general + 1 > RATE_LIMIT_GENERAL || b.prepare + prepareCalls > RATE_LIMIT_PREPARE) {
    return true;
  }
  b.general += 1;
  b.prepare += prepareCalls;
  return false;
}

export function countPrepareCalls(body: unknown): number {
  const msgs = Array.isArray(body) ? body : [body];
  let n = 0;
  for (const m of msgs) {
    if (
      m && typeof m === "object" &&
      (m as { method?: unknown }).method === "tools/call" &&
      (m as { params?: { name?: unknown } }).params?.name === "prepare_submission"
    ) {
      n++;
    }
  }
  return n;
}

