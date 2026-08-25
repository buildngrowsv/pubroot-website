---
title: "One resolve verb and a JSONL freeze ledger for agent media"
paper_id: "2026-200"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-08-25T06:52:58Z"
abstract: "Agents that author HTML video otherwise dump search snippets into context and leave assets unbound. The HyperFrames media-use skill implements one CLI verb, resolve, that takes a media type, a natural-language intent, and a project directory. stdout is a single line naming a stable id and a frozen local path. Search noise and provenance stay on disk in an append-only .media/manifest.jsonl plus a regenerated .media/index.md. Freeze copies bytes into .media under a 256 MiB header-and-stream cap, rejects platform pages, and SSRF-guards loopback, RFC1918, link-local, and cloud-metadata hosts. Reuse is two-layer. A deterministic floor auto-reuses only case-and-whitespace-normalized exact prompt matches, first in the project then in the per-user global cache. Semantic reuse is never auto-applied; --candidates lists, the agent picks, and --reuse imports by content sha. Brand and entity assets must match entity exactly so a global cache cannot leak another project's mark. This case study cites the public Apache-2.0 skill pack in heygen-com/hyperframes. It is a tool-use contract, not a media marketplace, and it is distinct from at-most-once vendor generation."
score: 8.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

# One resolve verb and a JSONL freeze ledger for agent media

An agent that authors a HyperFrames HTML composition needs bound files. A music search, an icon catalog, and a TTS call that dump ranked snippets into the chat do not give the renderer a path. The next session cannot tell whether `whoosh` already lives on disk. The `media-use` skill in the public HyperFrames skill pack treats that as a tool-use problem, not a retrieval-quality problem.

The implemented contract is one verb. `resolve` takes a type, a natural-language intent, and a project directory. stdout is one line. Bytes land under `.media/`. Provenance appends to `.media/manifest.jsonl`. A human-readable `.media/index.md` is regenerated. Search lists, candidate scores, and provider chatter stay off the transcript.

This case study inspects the public Apache-2.0 pack at [`skills/media-use/`](https://github.com/heygen-com/hyperframes/tree/main/skills/media-use) in [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes), pinned to commit `2ca578f9455ca928ab168e7dd08a1a3a9d834788`. The same tree is what `npx skills add heygen-com/hyperframes` installs. There is no dedicated media-use repository. We are not restating at-most-once vendor generation already on Pubroot at [`/se/architecture/at-most-once-media-generation-for-browser-driven-ai-pipelines/`](https://pubroot.com/se/architecture/at-most-once-media-generation-for-browser-driven-ai-pipelines/). That paper is about generation idempotency. This one is about resolution, freeze, and a ledger, including catalog hits and local ingest.

## One verb, one line

`SKILL.md` states the shape:

```bash
node <SKILL_DIR>/scripts/resolve.mjs --type <type> --intent "<description>" --project <dir>
```

stdout is `resolved <id> → <path> (<type>, <metadata>)`. `--json` wraps the same record. `--candidates`, `--doctor`, and `--stats` do not mutate the ledger.

Types that bind files or paste-ready blocks are `bgm`, `sfx`, `image`, `icon`, `logo`, `voice`, `grade`, and `lut`. We do not restate hosted catalog sizes. A `logo` is an official mark — svgl, then simple-icons, then a GitHub org avatar, then a domain favicon — and is never redrawn. `grade` may be an inline preset block rather than a file; `lut` is a validated `.cube`.

`scripts/resolve.mjs` runs a cascade, then freezes:

1. Project `.media/manifest.jsonl` for a normalized exact prompt of the same type.
2. Optional `--entity` match in the project. `icon`, `image`, and `logo` are interchangeable because they share `.media/images/`.
3. Unregistered files under `assets/` that share a meaningful token with the intent, not a substring.
4. Per-user global cache for the same normalized prompt, or the same entity.
5. Provider `search`, then `generate`.
6. Freeze into `.media/<type>/`, append the jsonl line, regenerate `index.md`, and best-effort promote to the global cache.

`--provider` bypasses rungs 1–4 so a forced generator cannot silently return another provider's file. `--local-only` is a hard skip of every `network` provider, including a forced network name.

## Freeze copies bytes, not URLs

A resolve is not done when a URL is known. `scripts/lib/freeze.mjs` copies bytes to a reserved path. `freezeUrl` fails fast if `Content-Length` exceeds `256 * 1024 * 1024` bytes, then streams and aborts if a lying or chunked body crosses the same cap. Empty HTTP bodies are rejected. Local ingest refuses a 0-byte file.

`--from` accepts a local path or a *direct* public media URL. Platform pages are rejected; yt-dlp is deliberately out. The URL must be `http` or `https`, must not be a platform host, must not be a private host, and the path must end in a known media extension.

```javascript
export function isDirectMediaUrl(u) {
  let url;
  try { url = new URL(u); } catch { return false; }
  if (url.protocol !== "http:" && url.protocol !== "https:") return false;
  if (PLATFORM_HOSTS.test(url.hostname)) return false;
  if (PRIVATE_HOST.test(url.hostname)) return false;
  return MEDIA_EXT.test(url.pathname);
}
```

`freeze.test.mjs` blocks loopback, RFC1918, link-local, `.local` / `.internal`, IPv6 ULA and link-local, and `169.254.169.254`. It allows `172.40.0.1`, which is not RFC1918. The guard is a literal hostname check.

## An append-only JSONL ledger

`scripts/lib/manifest.mjs` treats `.media/manifest.jsonl` as append-only. Each record is one JSON object. Malformed lines are skipped. `appendRecord` creates `.media/` and the type subdirectory. Ids are `type_NNN` (`sfx_001`). Concurrent resolves take a per-project `.media/.lock` (`O_EXCL`, 15 s stale-steal) and reserve the destination with `wx` so a slow freeze cannot collide on `sfx_001`. A failed populate deletes the placeholder.

A redacted line looks like:

```json
{"id":"sfx_001","type":"sfx","path":".media/audio/sfx/sfx_001.mp3","source":"search","description":"whoosh","duration":0.6,"provenance":{"provider":"bundled.sfx","prompt":"whoosh"}}
```

Provenance stores provider and the raw prompt. The prompt is not the cache key. `normalizePrompt` trims, lowercases, and collapses internal whitespace so `Calm piano` and `calm  piano` hit. The raw string remains for audit. `manifest.test.mjs` asserts that `Calm Ambient Piano` hits `calm ambient piano` and that `calm ambient guitar` is a miss.

`scripts/lib/index-gen.mjs` rewrites `.media/index.md` as a padded table of id, type, duration, dimensions, path, and description. That is the inventory an agent is told to read.

Fetched and ingested files are promoted to the per-user global cache under `mu-v1-` plus the first 16 hex chars of a SHA-256, with a `.hf-complete` sentinel. Bulk `--adopt` does not auto-promote.

## Two-layer reuse

Semantic match is the agent's job. media-use will not auto-apply a fuzzy match.

The **deterministic floor** auto-reuses only a case- and whitespace-normalized exact prompt, project first, then the global cache. A `--provider` override disables the floor.

The **semantic layer** is `--candidates`. `scripts/lib/candidates.mjs` lists up to eight project records and eight global records, ranked by token overlap, newest first on ties. Zero-overlap rows are still listed; the ranker never filters them out. A project hit is reused by referencing its path. A global hit is imported with `resolve --reuse <sha>`. Explicit import sets `source` to `reused-explicit` and `provenance.reused_by` to `agent`. Ambiguous sha prefixes fail closed.

When the floor misses and a fetch is about to run, a similar-asset count goes to stderr, pointing at `--candidates`. The hint never auto-reuses.

Brand and entity assets must match entity exactly. The global cache aggregates every project on the machine; a `--candidates` list can surface another project's mark and its prompt text. Skill docs: never reuse a cross-project brand asset on a loose match. Trust bias, from `references/resolve.md`: a redundant download is cheap; shipping the wrong asset is not.

## Ingest, adopt, and pluggable providers

`--adopt` walks `assets/`, infers type from extension and path (`bgm/`, `sfx/`, `voice/`), skips 0-byte files, probes duration and dimensions with ffprobe, and registers only new paths. On-the-fly adopt during resolve requires a shared token of length at least 3 after stopwords. Substring includes were too eager: `whoosh` grabbing `who.mp3`.

Providers live in `scripts/lib/registry.mjs` as an ordered list per type. The first non-null `search` or `generate` wins. media-use holds no API keys; each external tool owns its own auth. `--local-only` keeps bundled SFX (19 Pixabay files with `CREDITS.md` in `audio/assets/sfx/`), local Kokoro for voice, local mflux for images, local LTX for video, and the in-process color-grade / cube builder. Network catalog and TTS providers are skipped. We are not ranking those backends and we are not documenting hosted catalog sizes or billing.

`--doctor` checks the bundled SFX library, ffmpeg, ffprobe, and Node >= 18. It is a local gate, not a commercial install requirement. A missing bundled library returns typed JSON with `code: bundled_sfx_assets_missing` and `fix: npx hyperframes skills update media-use`.

## Limits

We did not invent content-addressed media caches or JSONL ledgers. We do not claim catalog coverage, reuse hit rates, or pixel-identical renders. We did not run live hosted searches for this paper; the bundled-SFX path, the freeze URL tests, and the manifest tests are what we cite as executable. The SSRF check is literal-hostname only; `freeze.mjs` notes that a DNS name that later resolves to a private IP still passes. `--adopt` does not promote into the global cache. `grade` records may be inline JSON with no file. This is not a media marketplace, not Studio UI, and not the at-most-once generation paper. The finding is narrower: one verb, frozen bytes, an append-only jsonl ledger, and a reuse rule that refuses to guess.