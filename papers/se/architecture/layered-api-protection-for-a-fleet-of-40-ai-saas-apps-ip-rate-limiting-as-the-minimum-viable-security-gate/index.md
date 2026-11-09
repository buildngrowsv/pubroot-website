---
title: "\"Layered API Protection for a Fleet of 40+ AI SaaS Apps: IP Rate Limiting as the Minimum Viable Security Gate\""
paper_id: "2026-121"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-10-29T14:14:05Z"
abstract: ">"
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
---

## Introduction

When your AI API key is the product, an unprotected route is a credit card with no spending limit. A single malicious user with curl and a loop can drain a $1000 fal.ai budget in minutes. The economic asymmetry is brutal: each anonymous request costs you $0.01 to $0.50 in vendor fees, and an attacker pays nothing.

This article describes the layered API protection architecture we built for a fleet of 40+ Next.js SaaS applications, all of which proxy user requests to paid AI providers (primarily fal.ai for image and video generation, with some routes hitting Google Gemini and Anthropic). The architecture emerged from a fleet-wide security audit on 2026-03-25 that discovered the majority of the fleet had zero server-side protection on its most expensive routes.

The core insight is that protection should be layered. Authentication plus credit checks is the right target for production, but it requires a database, an auth provider, and a billing system. None of those can be added in five minutes. IP rate limiting can be added in fifty lines of code, requires no external dependencies, and provides an immediate floor against the worst kind of abuse. The two layers complement each other: rate limiting catches sustained abuse from any source, and auth plus credits ensures every legitimate request is paid for.

## The Audit: 39 Routes, 22 Unprotected

The audit was triggered by the discovery that one product (`ai-background-remover`) had a route comment claiming "rate limiting handled by middleware" -- but no such middleware existed in the codebase. Searching the rest of the fleet revealed this was not an isolated mistake.

The methodology was straightforward: list every repository in the `ai-*` namespace, identify the API route that called fal.ai or another paid vendor, and read the route handler to determine what (if anything) ran before the vendor call.

The results, across 39 audited routes:

| Tier | Count | Description |
|------|-------|-------------|
| Tier 1: Fully protected (auth + credits) | 4 routes | Production-ready security |
| Tier 2: IP rate limited only | 12 routes | Mitigated, limited blast radius |
| Tier 3: Misleading comments, no protection | 3 routes | P0 critical |
| Tier 3: Completely unprotected | ~17 routes | P0 critical |

The most alarming category was Tier 3 with misleading comments. Three routes had explicit code comments like "FUTURE: Add auth check (Better Auth session), credit deduction, and IP-based rate limiting." The comments accurately described what was missing, but a casual reader (or a `grep` for "rate limit" in the codebase) would see the comment and assume protection existed. Reviewers had been fooled.

The other 17 unprotected routes had no comment at all -- they were straightforward proxies from the API route to the fal.ai SDK with no intermediate logic.

## The Four Naming Conventions Problem

Before the full audit could complete, an earlier attempt produced false negatives. The earlier audit had used a narrow grep pattern:

```bash
grep -r "ipRateLimitMap\|checkServerSideRateLimit" --include="*.ts"
```

This caught only one of the four naming conventions used across the fleet. The fleet had grown organically, with different builders implementing the same pattern under different identifiers:

| Convention | Variable Name | Function Name | Repos Using |
|-----------|---------------|---------------|-------------|
| A | `ipRateLimitMap` | `checkServerSideRateLimit` | Original template |
| B | `ipRequestTimestampMap` | inline (no function) | Early clones |
| C | `rateLimitMap` | `checkRateLimit` | Mid-batch clones |
| D | `rateLimitMap` | `isRateLimited` | Later clones |

All four conventions implement the same pattern -- an in-memory `Map<string, { count: number; windowStartMs: number }>` keyed by IP -- but the identifier choices diverged. Searching for one variant misses three. The corrected audit used a comprehensive pattern:

```bash
grep -r "rateLimitMap\|ipRateLimitMap\|ipRequestTimestampMap\|checkRateLimit\|isRateLimited\|checkIpRateLimit\|checkServerSideRateLimit" \
  --include="*.ts" --exclude-dir=node_modules --exclude-dir=.next -l
```

The corrected pattern revealed that 25 repositories the earlier audit had flagged as unprotected actually had protection -- just under different names. This is the false negative problem in fleet-wide auditing: when a pattern has organically diverged across products, narrow searches lie. The right approach is to grep broadly and read narrowly.

The lesson generalizes: any fleet-wide audit needs to enumerate the naming variations that exist before drawing conclusions. A single missing pattern in the grep can produce reports that are both technically accurate (the pattern is not present in the named files) and practically wrong (the protection is present, just under a different name).

## In-Memory Rate Limiting on Serverless

The protection pattern that the template now ships with is an in-memory `Map` keyed by IP address, with a fixed-window counter:

```typescript
const ipRequestMap = new Map<string, { count: number; windowStartMs: number }>();

const MAX_REQUESTS_PER_WINDOW = 20;
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 60 seconds

export function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const existing = ipRequestMap.get(ip);

  if (!existing || now - existing.windowStartMs > RATE_LIMIT_WINDOW_MS) {
    ipRequestMap.set(ip, { count: 1, windowStartMs: now });
    return true;
  }

  if (existing.count >= MAX_REQUESTS_PER_WINDOW) {
    return false;
  }

  existing.count += 1;
  return true;
}

export function extractClientIp(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return request.headers.get("x-real-ip") || "unknown";
}
```

The counter increments on each allowed request and resets when the window expires. Over-quota requests return `false`, and the route handler returns HTTP 429 with a `Retry-After: 60` header.

Two design choices are worth examining:

**The Map is module-level, not request-level.** This means it persists across requests within a single serverless instance lifetime. On Vercel, instances are reused for multiple requests until they go cold. The Map naturally accumulates state during warm periods.

**Cold starts reset the Map -- and this is acceptable.** When Vercel spins up a new instance, the Map starts empty. An attacker who knows this could theoretically wait for cold starts and resend their burst. In practice, three things mitigate the concern:

1. Cold starts on Vercel are not reliably triggerable from outside. An attacker cannot force them.
2. Each new instance has its own Map, so the attacker is now distributed across multiple buckets that all need to fill up before the rate limit kicks in. This actually makes the limit harder to circumvent across instances, not easier.
3. The goal is not perfect rate limiting -- it is preventing sustained abuse. A determined attacker who can survive 20 requests per minute per warm instance is paying real time for marginal value.

For perfect cross-instance consistency, the upgrade path is `@upstash/ratelimit` with Redis. The function signatures stay the same; only the storage backend changes.

## Dual-Bucket Design (Anonymous vs Authenticated)

The simple IP-only rate limiter is the floor. The next layer up, used in GenFlix and several other production-tier products, is a dual-bucket rate limiter that distinguishes anonymous users from authenticated ones:

```typescript
const rateLimitMap = new Map<string, { count: number; windowStartMs: number }>();

const WINDOW_MS = 60 * 1000;
const MAX_ANON_PER_MINUTE = 10;
const MAX_AUTH_PER_MINUTE = 30;

export function checkRateLimit(ip: string, userId?: string | null): boolean {
  const key = userId ? `user:${userId}` : `ip:${ip}`;
  const max = userId ? MAX_AUTH_PER_MINUTE : MAX_ANON_PER_MINUTE;
  const now = Date.now();
  const existing = rateLimitMap.get(key);

  if (!existing || now - existing.windowStartMs > WINDOW_MS) {
    rateLimitMap.set(key, { count: 1, windowStartMs: now });
    return true;
  }

  if (existing.count >= max) {
    return false;
  }

  existing.count += 1;
  return true;
}
```

Authenticated users are keyed by `user:${userId}` instead of `ip:${ip}`. This solves two problems:

**Power users behind shared IPs do not throttle each other.** An office or coffee shop with multiple legitimate users behind one NAT would otherwise share a single rate limit bucket. Keying by user ID separates them.

**Authenticated users get a higher limit.** They have an account, they consumed credits to make this request, and they have a higher threshold of trust. Anonymous users (free preview, no account) get the conservative limit.

The bucket key prefix (`user:` vs `ip:`) ensures the two namespaces never collide. An IP that is also a logged-in user gets two buckets, one anonymous and one authenticated.

## Credit Deduction with Optimistic Concurrency

Rate limiting protects against burst abuse. Credit deduction protects against sustained abuse by ensuring every request is paid for from a finite balance. The naive implementation has a race condition: read the user's balance, check it is sufficient, then update it. Two concurrent requests can both pass the check before either updates, allowing a double-spend.

The pattern we use in banananano2pro and several other production products is optimistic concurrency via a SQL `UPDATE ... WHERE` clause:

```typescript
export async function deductCredits(
  userId: string,
  amount: number,
  reason: string
): Promise<boolean> {
  const result = await db
    .update(userProfiles)
    .set({
      credits: sql`${userProfiles.credits} - ${amount}`,
      updatedAt: new Date(),
    })
    .where(
      sql`${userProfiles.userId} = ${userId} AND ${userProfiles.credits} >= ${amount}`
    )
    .returning({ credits: userProfiles.credits });

  if (result.length === 0) return false;

  await db.insert(creditTransactions).values({
    userId,
    amount: -amount,
    reason,
  });

  return true;
}
```

The atomicity comes from the database. The `WHERE credits >= amount` clause ensures the update only succeeds if the user has sufficient balance at the moment the row is locked for update. If two concurrent requests both try to deduct credits, the database serializes the updates: the first one succeeds, the second one finds insufficient credits and the update affects zero rows. The function returns `false`, the route handler returns an error, and the user has not been charged twice.

This avoids explicit transactions, advisory locks, and the SELECT-then-UPDATE pattern that requires careful isolation level configuration. The single statement is its own critical section, enforced by the database engine.

## Template Propagation: Fix Once, Inherit Forever

The most leveraged fix in this story was not adding rate limiting to one product -- it was adding it to the `saas-clone-template` repository. This is the source from which all new clones are scaffolded. Every clone created after the template fix inherits the protection automatically.

The template fix was committed on 2026-03-25 as commit `5c8d146`. The template's `src/app/api/generate/route.ts` now ships with `ipRateLimitMap`, `checkIpRateLimit()`, and `extractClientIp()` inline. The rate limit check runs before authentication and before the fal.ai call, so over-limit requests cost zero API credits even if they come from a logged-in user.

The protection is positioned deliberately:

```typescript
export async function POST(request: NextRequest) {
  // Layer 1: IP rate limit (zero cost to enforce, runs first)
  const clientIp = extractClientIp(request);
  if (!checkIpRateLimit(clientIp)) {
    return NextResponse.json(
      { error: "Rate limit exceeded" },
      { status: 429, headers: { "Retry-After": "60" } }
    );
  }

  // Layer 2: Authentication (when wired)
  const session = await getServerSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Layer 3: Credit deduction (atomic)
  const deducted = await deductCredits(session.user.id, COST, "generate");
  if (!deducted) {
    return NextResponse.json({ error: "Insufficient credits" }, { status: 402 });
  }

  // Vendor call (only after all layers pass)
  const result = await falClient.subscribe(...);
  return NextResponse.json(result);
}
```

The order matters: cheap checks first, expensive operations last. The IP check is the cheapest -- a Map lookup. Authentication is next -- a session decode and possibly a database read. Credit deduction is more expensive -- a database write. The vendor call is the most expensive -- a network round-trip and real money spent. By ordering these from cheapest to most expensive, the system rejects bad requests as early as possible and only commits resources to requests that have passed every gate.

## When the Floor Is Enough: Lightweight Clones Without Auth

Not every product in the fleet has authentication wired. Some are intentionally lightweight -- a single-page tool, no signup, just type or upload and get a result. For these, the IP rate limiter is the only layer of protection, and it has to be enough.

The constraint we accepted is that lightweight clones get a tighter rate limit (3 requests per IP per day in the template default) and a clear cost cap. The template's `FREE_GENERATIONS_PER_IP_PER_DAY = 3` is a deliberately conservative number: enough for a curious visitor to try the tool, not enough to cause meaningful vendor cost from any single source.

This is a judgment call that depends on the unit cost of the vendor call. A $0.01 image generation can tolerate a higher per-IP limit than a $0.50 video generation. The template ships with image-tier defaults; video-heavy products override the constants.

## Lessons Learned

**Comments lie, code does not.** Three of the most dangerous routes had comments claiming rate limiting that did not exist. Reviewers had been fooled by the comments. The audit had to read the actual handler logic, not trust the prose. This generalizes: any audit that reads only comments or only documentation will produce false confidence.

**Naming conventions diverge in fleets.** Four different identifiers for the same pattern across one fleet of 40 repositories. A grep with one name misses three. Audits need to enumerate naming variations before searching. Templates need to enforce naming so future divergence is prevented.

**The minimum viable security gate is fifty lines of code.** IP rate limiting requires no external dependencies, no database, no auth provider. It can be added to any Next.js API route in under five minutes. There is no excuse for shipping a paid-API proxy without it.

**Cold-start resets are a feature for in-memory rate limiting.** Each new serverless instance has its own bucket. An attacker cannot force cold starts. The intermittent reset is acceptable noise that prevents the pattern from being a perfect oracle for attackers, while still bounding sustained abuse.

**Optimistic concurrency in SQL is simpler than locks.** A single `UPDATE ... WHERE balance >= amount` statement replaces a SELECT-then-UPDATE transaction with explicit isolation. The database is already a critical section; use it.

**Template-level fixes propagate.** Adding rate limiting to one product fixes one product. Adding it to the template fixes every future product. The leverage ratio is enormous. Audit findings should be triaged by whether they can be fixed at the template level, and template fixes should be prioritized over individual repository fixes.

## Conclusion

Protecting paid AI API routes is not optional, and the minimum viable protection is much cheaper than most teams assume. A fifty-line IP rate limiter prevents the worst class of abuse and requires no external dependencies. A dual-bucket design distinguishes power users from anonymous bursts. A SQL `UPDATE ... WHERE` clause prevents credit double-spends without explicit locking. A template-level commit propagates the protection to every future clone in one change.

The expensive lessons in our fleet were not the technical patterns -- those took an afternoon to write -- but the audit methodology and the cultural changes. Auditing requires enumerating naming variations to avoid false negatives. Reviews must read code, not comments. Templates need to ship with protection by default so individual builders cannot accidentally omit it. For any team operating multiple AI-vendor-backed products, the architecture in this article is the minimum viable starting point. Anything less is a credit card with no spending limit.