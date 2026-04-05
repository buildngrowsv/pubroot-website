---
title: "Per-Turn Chunk-Keyed RAG with Folder-Backed Memory in a macOS Voice Agent (BubbleVoice)"
paper_id: "2026-090"
author: "buildngrowsv"
category: "ai/rag-retrieval"
date: "2026-04-05T14:55:20Z"
abstract: "This case study describes how we attach retrieval-augmented context on every user message in a voice-oriented macOS assistant: multi-query local embeddings, deduplication by stable chunk_id, filesystem-shaped metadata (life-area paths and document names), and a four-file-per-conversation layout that mirrors a database. We document the 2026 integration that wired context assembly into the websocket message path, unified RAG plus artifact prefixes across LLM providers, and graceful degradation when the vector store is cold. We also disambiguate \u201cindex-matching\u201d from unrelated UI-index automation (Rabbit/BCL)."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_open"
ai_tooling_attribution: "Synthesized from BubbleVoice-Mac source and comments at the cited commit; no separate product memo was found."
---

## What “index-matched chunks” meant in our stack

The phrase collides with **two different “index” ideas** in this workspace:

1. **Memory RAG (this article):** Each retrieved unit is a **vector row** keyed by `chunk_id`, with **folder-like** `area_path` and `document` fields. Prompt formatting labels hits as numbered entries and prints `area_path/document` so the model can cite a stable source. Duplicate hits from multiple queries collapse by `chunk_id`, keeping the highest score.

2. **macOS UI automation (Rabbit / BCL):** “Index” means the **interactive element index** from the last `discover` pass; **not** text-chunk identity. That is a different pipeline (accessibility tree, click-by-index).

This article is about **(1)** only.

## Folder and file system as the user-visible database

Each conversation gets a directory under `conversations/<id>/` with multiple Markdown artifacts—for example a full thread, a **user-inputs-only** file (to bias retrieval toward the user’s words), rotating AI notes, and summaries. The design treats the filesystem as a **human-auditable** backing store while SQLite holds embeddings for fast search.

**Chunking** prefers semantic units: entries parsed from time-stamped sections (not arbitrary token windows), producing chunk IDs that combine area path, document name, and timestamp. That makes `chunk_id` **match** the logical entry in the tree, which is what we mean by “chunk-matched” in prompts: the model sees text that traces back to a specific path and time.

## Every message: assemble, format, inject

On each user message, the backend can call `getContextForTurn`, which aggregates AI notes, a life-areas knowledge tree, **multi-query** vector search over the current transcript, and recent conversation history. The formatted string becomes `conversation.ragContext` before streaming the LLM response.

**Multi-query strategy** runs three embedding searches (recent user text, all user text, full conversation) with weights, merges results, applies recency and optional area boosts, and takes a top-K after deduplication. The intent is to **balance immediate intent** against **longer user history** and **full-dialog drift** without a single naive query.

A later **architecture fix** documented in code moved RAG and artifact context into a **shared prefix** shared by OpenAI, Anthropic, and Gemini builders—previously some providers could miss artifact or RAG context entirely.

## Troubleshooting and operational lessons

**Graceful degradation:** If embeddings or the database are not ready (first launch, dev flags skipping the DB), the server logs a warning and continues **without** RAG so the user still gets a reply.

**Cold start:** First conversations legitimately return empty vectors; that is expected, not a bug.

**Integration gap (fixed in code comments):** Context assembly existed before the websocket handler called it; wiring `getContextForTurn` into `handleUserMessage` was the critical path fix so the feature actually ran in production flows.

## What may be novel

Combining **local Transformers.js embeddings**, **chunk_id-stable dedup across three queries**, **explicit area_path/document provenance in the prompt**, and **provider-agnostic injection** is a coherent pattern for **privacy-sensitive** desktop voice agents. Novelty is relative; the contribution is **end-to-end documentation** of a working integration, not a new embedding model.

## Boundaries

Token budgets and weights are configurable; exact production numbers should be read from `PromptManagementService` / admin config at runtime. Do not conflate this RAG pipeline with iOS Accountability’s timer-based turn-taking—they are separate products in this repo collection.