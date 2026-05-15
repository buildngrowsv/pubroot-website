---
title: "Prompt Technique Archaeology After a Prompt Versioning Migration"
paper_id: "2026-151"
author: "buildngrowsv"
category: "ai/prompt-engineering"
date: "2026-05-15T09:28:52Z"
abstract: "After GenFlick migrated prompt text into a versioned prompt bundle, the team ran a prompt technique archaeology pass to determine whether useful older prompting patterns had been lost. The investigation compared current prompt surfaces against historical branches, old prompt-quality experiments, Seedance prompt effectiveness runs, and archived research notes. The migration preserved the most important active rules, including anticipation start frames, arrival-frame timing, dialogue coverage, coverage math, media-reference intent, locked-entity awareness, continuation references, and golden examples. What risked being lost was not the core prompt contract but high-signal example formats and operational runbooks: a master consistency lock for continuations, safe-geometry multi-shot examples, a durable movie-craft rubric, and the finding that focused prompt repair with a concise bible can outperform full production context. The article presents archaeology as a necessary companion to prompt versioning."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from docs/PROMPT-TECHNIQUE-ARCHAEOLOGY-2026-04-27.md and related GenFlick prompt migration notes."
---

## Problem

Prompt versioning can accidentally make a system look cleaner while hiding older craft knowledge in branch history. Moving prompt text into a manifest, bundle, or registry solves provenance, but it does not answer whether the new canonical prompt still contains the best lessons from past experiments.

GenFlick encountered this after a prompt versioning migration. The current prompt bundle had better provenance and loading behavior, but years of agent work had produced scattered examples, branch-specific prompt techniques, eval reports, and runbooks. The question was not "what changed in the diff?" It was "which older techniques still matter, and which ones are stranded outside active prompt surfaces?"

## Method

The archaeology pass compared the current prompt bundle against several historical sources: an old media-library branch, a prompt-quality branch, specific commits for the two-wave chat flow, planning-agent replacement, Seedance golden examples, prompt-quality gates, and multi-shot continuation improvements.

The investigation separated three categories:

- Techniques already preserved in current prompts.
- Techniques worth bringing back into prompt surfaces, docs, tests, or prompt-adjacent utilities.
- Historical implementation details that should remain retired.

That distinction matters. Archaeology should not blindly re-add old text. It should preserve useful technique and discard stale orchestration.

## Preserved Techniques

The migration preserved anticipation start-frame guidance. This rule tells the prompt writer to describe the setup moment before an action, not the peak action. It prevents image prompts from freezing the most dynamic frame, leaving the video model no natural motion to perform.

It also preserved arrival-frame timing. When a clip starts from a previous final frame, the prompt must treat that frame as already arrived. The next prompt should continue from that state, not ask the model to perform the arrival again.

Dialogue coverage rules survived. The current prompts still teach the agent that dialogue scenes need coverage, not just one wide shot: establishing, over-the-shoulder, reaction, insert, two-shot, and final beat. They also preserve the rule that dialogue belongs in animation or multi-shot segment fields rather than being implied only by visual prose.

Coverage math survived. A narrative scene needs establishing, primary coverage, and at least one reaction/detail/cutaway. This avoids the common failure where a "scene" is really a single prompt with no editorial coverage.

Media-reference intent also survived, with a richer model than older branches. Current prompts distinguish canonical identity references, starting frames, derivative image inputs, previous-clip references, and loose inspiration.

Locked-entity caution survived. If an entity is locked, the prompt should not casually redesign it.

## Techniques Worth Reintroducing

The first high-value technique was a master consistency lock for continuation prompts. Older research notes had a compact shape: treat the referenced frame as canonical, preserve identity, wardrobe, environment, lighting direction, screen direction, shadows, reflections, color grade, film grain, and camera style, then continue from the exact final-frame state. Current continuation guidance was good but distributed. The archaeology suggested preserving a compact lock block for direct extension and starting-image workflows.

The second technique was safe-geometry multi-shot examples. Historical Seedance experiments had concrete examples for avoiding unsafe or impossible staging: preserve camera side, do not swap character screen positions, do not cross the 180-degree line, avoid repeated handoffs, and keep location/wardrobe fixed across segments. These examples are particularly useful around trains, roads, rooftops, weapons, crowds, heights, and vehicles.

The third technique was a durable movie-craft rubric. Prompt quality is hard to maintain if the only artifact is the prompt. A rubric that checks coverage, continuity, voicing, staging, prompt renderability, and provider constraints lets future prompt edits be assessed consistently.

The fourth technique was focused prompt repair. A historical prompt-quality comparison found that a focused prompt-writing system plus concise project bible and one scene payload could beat full production context for prompt repair. This is an important structural lesson: more context is not always better. For repair tasks, the right context may be smaller, sharper, and more task-specific.

The fifth technique was an internal prompt-engineering reference page for humans. Not all prompt knowledge belongs in model-facing instructions. Some belongs in docs that help agents and developers understand why the active prompt is shaped the way it is.

## What Not To Reintroduce

Some old techniques were retired for good reasons. The fixed two-wave implementation was superseded by a planner that can emit N phases per turn. The old implementation details should not return. The useful parts were the craft principles: provider-aware durations, dialogue decisions, continuation-chain guidance, and recommendation-not-policy act ratios.

Likewise, old generic quality filler should not be preserved. Phrases such as "high detail" or fixed resolution claims rarely improve modern generation and can clutter prompt surfaces. Archaeology should extract the causal technique, not copy every word from old prompts.

## Why This Matters

Prompt migrations can create a false sense of safety. A manifest tells you what is current. It does not tell you whether the current version lost a hard-won lesson from an experiment three branches ago.

Technique archaeology complements versioning by asking qualitative questions: what did old experiments teach, what survived, what is stranded, and what should become an eval fixture rather than prompt prose?

It also helps prevent prompt bloat. When an older example is useful, the answer is not always to paste it into the system prompt. It may be better as a test case, golden example, human reference, or compiler rule.

## Reusable Process

A practical prompt archaeology pass can follow five steps.

First, choose a migration boundary or major prompt refactor. Second, enumerate historical branches, commits, docs, eval reports, and run artifacts likely to contain prompt knowledge. Third, compare current prompts against those sources. Fourth, classify findings as preserved, reintroduce as prompt text, reintroduce as tests/docs/tooling, or discard. Fifth, create follow-up tasks tied to specific prompt components or eval fixtures.

The output should be a craft inventory, not a merge plan. It tells the next agent where the knowledge is and why it matters.

## Conclusion

Prompt versioning makes active prompt state auditable. Prompt technique archaeology makes prompt memory durable. In GenFlick, the migration preserved many core rules, but the archaeology found valuable example formats and assessment ideas at risk of being stranded. The broader lesson is that prompt engineering systems need both immutable manifests and periodic historical review, especially when the product's best prompt behavior was discovered through messy production experiments.