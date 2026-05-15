---
title: "Phased Planner-Executor Architecture for Multimodal Movie Generation Agents"
paper_id: "2026-135"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-05-15T09:16:58Z"
abstract: "This case study describes the planning architecture GenFlick designed after observing unstable output from single-pass movie generation agents. Early runs showed recurring failures: dialogue decisions vanished, continuity references were named but not wired, and duration choices ignored provider constraints. The proposed architecture separates a low-temperature planner from scoped executor phases. The planner emits a phase plan; each phase receives a narrowed prompt, expected action set, and project context appropriate to its responsibility. Between phases, the server can dispatch actions, emit progress events, and preserve earlier outputs for later phases. The architecture trades one large overburdened generation pass for smaller accountable passes that map to product-visible progress. The article explains the failure observations, phase topology, UI implications, and remaining risks in using LLM planning for multimodal creative production."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from GenFlick internal architecture notes, especially docs/PLANNING-AGENT-ARCHITECTURE-SPEC-2026-04-21.md and related agent-flow audit documents."
---

## Context

GenFlick asks an LLM agent to do an unusually broad job. From one user prompt it may need to infer a genre, choose a visual style, create characters and sets, define acts, write scenes, break scenes into clips, attach dialogue, pick target durations, create continuity references, author image prompts, and schedule media generation. Those choices are connected. A character created in the movie bible must reappear in clips. A match cut described in text must become a concrete continuity reference. A provider duration limit must constrain the clip plan.

Early production audits showed that a single large action block could produce impressive structure while still dropping important details. In one set of runs, dialogue was volatile across model/provider combinations. Continuity references appeared in prose but did not reliably become linked runtime fields. Clip durations clustered around narrow defaults despite explicit capability signals. The agent knew many of the craft rules, but it had to apply too many of them at once.

## Architecture

The planning-agent design splits the work into one planner call and a sequence of scoped executor calls.

The planner reads the user request and active provider capabilities. It writes a plan object, not project state. A typical fresh-project plan may include phases such as movie bible, act structure, scenes for Act I, scenes for Act II, scenes for Act III, and final audit. A smaller edit request may collapse to one phase.

Each executor phase then runs with a narrower system prompt addendum. The phase addendum describes the phase's responsibility, allowed actions, blocked actions, and focus questions. For example, a scenes-for-act phase may be allowed to create scenes and continuity references but blocked from re-registering characters or changing the aspect ratio. An audit phase may be allowed to update scenes and add missing continuity references but not rewrite the entire movie bible.

The server dispatches actions between phases, so later phases can read project state that includes earlier work. It also streams progress events such as plan previews and phase completion summaries. This turns internal agent decomposition into visible user progress.

## Why Phases Help

The main advantage is cognitive load reduction. A single model call no longer has to decide every creative and operational detail simultaneously. The movie bible phase can focus on identity and world-building. The act phase can focus on macro structure. Scene phases can focus on coverage, continuity, and dialogue for a bounded section of the story. The audit phase can inspect the whole assembled project for missing links.

The second advantage is action scoping. When a phase has an expected action set, the runtime can detect unexpected behavior earlier. If a scenes phase emits a billing-sensitive generation action, the dispatcher can reject it as out of scope. If an act-structure phase tries to create clips before scenes are ready, that is a detectable contract violation.

The third advantage is better UI choreography. Users do not only see "the agent is thinking." They can see a checklist of work: establish story bible, define acts, write scenes, polish continuity. This is especially useful for a product where useful work may take minutes and where media generation costs credits.

## Failure Modes Addressed

The design directly targets three observed failure modes.

Dialogue volatility is addressed by giving scene phases explicit responsibility for deciding whether scenes are silent, dialogue, or voiceover. Instead of being one small decision inside a giant movie plan, dialogue coverage becomes a phase-level focus question.

Continuity drift is addressed by moving continuity wiring into the same scoped phase that creates related scenes and clips. If a phase writes match-cut or shot-reverse-shot language, it is also responsible for emitting the continuity reference action.

Provider constraint drift is addressed by passing provider capabilities and pacing priors into phases that choose clip counts and target durations. A later audit phase can check whether the generated plan respects those constraints.

## Product Implications

The planning architecture creates a natural progress model. A chat UI can render the plan as a checklist, then mark phases complete as actions are dispatched. Each phase can produce a compact receipt such as "movie bible locked: four characters and two sets" or "Act II drafted with five scenes and two dialogue beats."

This makes the system more legible to a first-run user. Long-running generation workflows often fail UX-wise because users cannot tell whether the agent is still working, stuck, or done. Phase events make that state explicit.

The same structure also supports retries. If one phase fails, the server can retry that phase with the original user request, the plan, and the project state produced by previous phases. That is a narrower recovery problem than rerunning the entire movie creation request.

## Tradeoffs

The architecture increases the number of LLM calls for complex requests. That adds latency and cost. GenFlick mitigates this by allowing simple requests to collapse to one phase and by using the planner for scoping rather than prose-heavy creativity.

Phases also introduce boundary design work. If the blocked action list is too strict, the agent may be unable to fix problems when it notices them. If it is too loose, the phase boundary stops providing value. The right boundary is domain-specific and must be tuned against evals.

Finally, phase decomposition is not a substitute for robust dispatch validation. The model can still emit malformed or out-of-scope actions. The runtime must remain the authority on what changes are accepted.

## Evaluation Plan

The architecture spec called for a real LLM eval before switching production behavior. The proposed comparison uses fixed user prompts across three conditions: current single-wave or two-wave production, planner-plus-phases, and compressed/alternative prompt variants. Metrics include dispatch validity, scene coverage, dialogue coverage, continuity references, duration distribution, provider constraint compliance, and final project quality rubric scores.

The important evaluation principle is to inspect parsed actions and project state, not only assistant prose. A model may describe continuity beautifully while failing to emit the reference fields that the renderer needs.

## Conclusion

For multimodal creative agents, "think step by step" is not enough. The runtime should own a phase topology that turns creative decomposition into scoped action contracts and user-visible progress. GenFlick's planner-executor design is a practical architecture for that: plan once, execute bounded phases, dispatch between phases, and audit the assembled project before spending media-generation credits.