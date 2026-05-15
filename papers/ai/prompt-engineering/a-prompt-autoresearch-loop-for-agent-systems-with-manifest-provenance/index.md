---
title: "A Prompt Autoresearch Loop for Agent Systems with Manifest Provenance"
paper_id: "2026-163"
author: "buildngrowsv"
category: "ai/prompt-engineering"
date: "2026-05-15T09:33:53Z"
abstract: "This tutorial describes a prompt autoresearch loop for GenFlick-style agent systems: change one prompt or context surface, regenerate provenance, run a fixed eval, score the result, keep improvements, and reset regressions. The pattern adapts Karpathy's autoresearch idea to an agentic application where prompt behavior depends on system prompts, planner prompts, phase addendums, context builders, prompt composers, prompt flatteners, and provider-specific modifiers. The key discipline is separation of mutable target and fixed evaluator. An optimization agent may edit one selected prompt surface, but not the harness that judges it. Each candidate must regenerate the prompt manifest, pass prompt checks, preserve context-engineering version labels when needed, and improve a scalar score without hard failures. The article outlines target selection, scoring, gates, ledgers, and the recommended first run for specialist phase addendums."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from docs/PROMPT-AUTORESEARCH-OPTIMIZATION-RUNBOOK-2026-04-27.md and GenFlick prompt-versioning notes."
---

## Goal

Prompt optimization is tempting to automate. An agent can edit prompt text, run evals, inspect failures, and try again. Without discipline, that loop can also corrupt the evaluator, optimize against a moving target, lose provenance, or create a prompt that scores well locally but breaks production behavior.

GenFlick's prompt autoresearch runbook adapts a simple ratchet pattern: change one prompt surface, regenerate manifest, run fixed eval, score, keep or reset.

The loop is designed for agent systems where behavior is not controlled by one prompt file. GenFlick has system prompts, planner prompts, specialist phase addendums, context builders, prompt composers, prompt flatteners, and provider-specific prompt modifiers. The same method can apply to any tool-using agent with prompt provenance and repeatable evals.

## Core Principle

Separate the mutable target from the evaluator.

An optimization agent may edit the selected prompt or context surface. It may not edit the eval wrapper, scoring rubric, test cases, or manifest rules during that run. If the evaluator changes while the prompt changes, an improved score no longer means the prompt improved.

This sounds obvious, but it is the main failure mode for autonomous prompt optimization. Agents are good at finding paths of least resistance. If the metric is mutable, the loop optimizes the metric.

## Mapping

The pattern maps a general autoresearch loop to GenFlick's repo.

The mutable program is one selected prompt or context file. The prepare step is a fixed eval harness and scoring wrapper. The validation score is a normalized `score_100`. The result ledger records commit, score, hard-failure status, and description. Git stores candidates and makes reset cheap.

The prompt manifest is central. Every candidate must regenerate prompt provenance so the score can be tied to a bundle hash. Otherwise a future reviewer cannot know which prompt was actually assessed.

## Target Selection

Start with one target per run. Good candidates are high-leverage but bounded surfaces, such as planner prompts, specialist base prompts, phase addendums, generation prompt composers, prompt-to-text flatteners, multi-shot compilers, or golden examples.

Avoid broad first runs that edit many prompt surfaces at once. If the score changes after five files changed, attribution is weak. The loop works best when a candidate's effect can be connected to one mutation zone.

For GenFlick, the recommended first target was specialist phase addendums. They are high leverage, already inventoried, and directly affect authoring flow quality.

## Fixed Eval Harness

The eval should produce a stable machine-readable summary. A useful shape is:

```json
{
  "score_100": 87.5,
  "hard_failed": false,
  "errors": [],
  "warnings": [],
  "prompt_bundle_hash": "sha256:...",
  "cases": []
}
```

The exact scoring model can vary by product. GenFlick's suggested default combines routing, action validity, movie craft, prompt quality, continuity, latency penalty, and token penalty. The important part is that the scoring method is chosen before the loop and remains fixed.

## Hard Gates

Some failures should cap or zero the score regardless of subjective quality.

Examples include malformed action JSON, disallowed action types for a planner phase, missing required references or IDs, missing dialogue lines where required, prompt manifest drift, TypeScript or relevant test failure, evaluator crash, unsafe provider behavior, or production-cost violations.

Deterministic gates should run before LLM-as-judge scoring. LLM judges are useful for craft dimensions, but they should not excuse broken contracts.

## Standard Loop

A disciplined loop looks like this:

1. Create a fresh branch or candidate workspace.
2. Create an uncommitted ledger for score rows.
3. Run the unchanged baseline.
4. Edit only the selected mutable target.
5. Regenerate the prompt manifest.
6. Run prompt freshness and hardcoded-prompt checks.
7. Bump context-engineering version labels if non-text behavior changed.
8. Commit the candidate.
9. Run the fixed eval wrapper.
10. Append a ledger row.
11. Keep the candidate only if hard gates pass, score improves, complexity is justified, and generated files are current.
12. Reset to the previous best if the score regresses or the candidate adds brittleness without meaningful gain.

The ledger should record not only score but also why the candidate changed. Prompt optimization without a readable rationale becomes archaeology debt.

## Complexity Budget

The loop should penalize prompt growth unless the gain justifies it. A prompt can improve a narrow score by adding verbose case-specific patches. That may still be a bad trade if it increases cost, conflicts with other cases, or makes future edits harder.

A candidate should be judged on quality and maintainability. Shorter, more general rules that preserve behavior are often better than longer patches that win one case.

## Recommended First Run

For GenFlick, the first recommended run targets the phase addendums and uses the AI-flow eval with warnings treated as failures. The goal is to improve production authoring flow quality without breaking action JSON, planner phase routing, multi-shot prompt quality, reference handling, dialogue preservation, or prompt provenance.

This is a good first target because phase addendums are scoped enough for attribution but broad enough to affect real output. They also sit at the boundary where prompt structure, action permissions, and craft guidance meet.

## Limitations

This approach depends on having a meaningful eval harness. If the eval does not reflect product success, the loop can optimize the wrong behavior. It also depends on enough deterministic validation to catch schema and runtime contract failures.

Autoresearch should not run directly against production prompts without review. It can propose candidates, but humans or higher-level agents should still inspect changes, especially when billing, safety, or user data are involved.

## Conclusion

A prompt autoresearch loop can make agent systems better if it is constrained by provenance and fixed evaluation. The pattern is simple: edit one surface, regenerate manifest, run the same eval, score, keep or reset. The discipline is in what the agent is not allowed to change: the evaluator, the provenance rules, and the hard gates that protect production behavior.