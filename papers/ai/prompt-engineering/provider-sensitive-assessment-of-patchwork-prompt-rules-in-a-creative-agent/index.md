---
title: "Provider-Sensitive Assessment of Patchwork Prompt Rules in a Creative Agent"
paper_id: "2026-171"
author: "buildngrowsv"
category: "ai/prompt-engineering"
date: "2026-05-15T09:37:20Z"
abstract: "GenFlick assessed whether patchwork prompt rules were still needed by comparing less-patched and current-patched prompt bundles on edge cases that appeared to motivate those rules. With GPT-5.5, the less-patched bundle handled several targeted cases better than expected: product/app promo grounding, product UI as screen props rather than mascots, and scoped episode openings without unwanted documents or posters. The current patched bundle did not clearly improve those cases and sometimes changed phase selection in undesirable ways. Re-running related less-patched cases through Gemini 3.1 Pro Preview exposed a different conclusion: Gemini averaged 83.6 versus GPT-5.5's low-90s scores, with more unwanted docs/posters, thinner asset plans, and weaker intent alignment. The result argues for provider-sensitive prompt policy: shorter first-principles prompts for stronger models and explicit guardrails for weaker or more drift-prone models."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from docs/PATCHWORK-PROMPT-EDGE-CASE-AUDIT-2026-04-29.md and docs/GEMINI-LESS-PATCHED-AGENT-FLOW-AUDIT-2026-04-29.md."
---

## Benchmark Question

Production prompts often accumulate patches because users discover edge cases. A product promo becomes a sci-fi hologram. A SaaS UI becomes a mascot. "First few scenes" turns into a whole episode package. A narrow prompt rule can prevent each failure.

But patches have a cost. They lengthen the prompt, create conflicting priors, and may no longer be needed as models improve. GenFlick tested whether less-patched prompts still handled patch-motivated cases, and whether the answer changed by provider.

## GPT-5.5 Patchwork Audit

The first audit compared a less-patched prompt bundle against a current patched bundle using live GPT-5.5 through the no-media agent-flow harness. Media generation was skipped.

The cases were chosen because each seemed to justify a specific patch.

The first case was a GenFlick launch promo. The patch motive was to prevent "creative magic" and "make money with AI" from turning into portals, holograms, neon sci-fi, or abstract light worlds. The less-patched bundle scored 90.0 A watch and produced grounded creator-loft, laptop, tablet, phone, and projection surfaces. The current patched bundle scored 91.5 A watch and also grounded the result, but introduced a compact mini-soundstage and a five-segment warning. The patch helped slightly on score but did not decisively improve behavior.

The second case was a SaaS product demo where the UI was the star. The prompt explicitly said not to create a mascot or avatar and to show real screens in an office. The less-patched bundle scored 95.5 A+ pass, with one human character and dashboard/laptop/wall-monitor props. The current patched bundle scored 91.7 A watch. It also avoided mascots, but dropped a helpful staging phase. This suggested the ontology rule was already held, while phase selection got worse.

The third case was a scoped episode opening: only the first few scenes, not the full episode, and no companion docs or posters. Both bundles obeyed scope and avoided docs/posters. The current patched bundle did not clearly improve the output.

The initial conclusion was that these tests did not support adding more patchwork for GPT-5.5. The less-patched prompt already handled targeted edge cases better than expected.

## Gemini Sensitivity Check

A second audit asked whether that conclusion was mostly a GPT-5.5 effect. The same style of patch-motivated cases was run through Gemini 3.1 Pro Preview using the less-patched prompt-source state.

The answer was yes: the difference became more obvious with Gemini.

On the product/app promo case, Gemini scored 83.1 B watch. It drifted into extra documents and posters and produced a weaker asset plan.

On the product UI/interface trap, Gemini scored 79.8 C watch. It did preserve the core "UI as prop" idea and did not create a mascot, but the plan was thinner, less render-ready, and again produced unwanted documents.

On the scoped episode opening, Gemini scored 88.0 B+ watch. It mostly obeyed no-docs/no-posters and the limited scope, but intent alignment was much weaker.

The average score for Gemini less-patched was 83.6, compared with GPT-5.5 less-patched at 93.2 and GPT-5.5 current-patched at 92.1 in the earlier slice. The model difference was larger than the prompt-variant difference for these cases.

## Interpretation

Patchwork prompt rules are doing at least two jobs.

For stronger models, some patches may be redundant. GPT-5.5 inferred practical product-grounding and scope constraints from the prompt and user intent without needing the full bespoke wording. In that setting, extra patchwork can become noise or conflict with phase-selection priorities.

For weaker or more drift-prone models, patches act as guardrails. Gemini benefited more visibly from explicit boundaries around documents/posters, product UI as grounded screen surfaces, and "first few scenes" scope.

This means prompt policy should not be treated as provider-neutral by default. A single shared prompt can work, but it may be too long for one provider and too vague for another.

## Assessment Lessons

The first lesson is to test patch value directly. If a patch exists because of an edge case, build that edge case into the harness and compare with and without the patch.

The second lesson is to compare providers. A patch that looks unnecessary under the strongest model may still be necessary for a cheaper, faster, or product-supported model.

The third lesson is to inspect phase selection. In the GPT-5.5 audit, some regressions were not about final prose or schema validity. They were about planner phases: staging disappeared, casting appeared when not helpful, or act-structure remained despite flow-rethink guidance.

The fourth lesson is to separate ontology rules from narrative patches. "Product UI is usually a prop or screen surface" is a compact principle. A long product-promo block with many special cases may not be needed if the compact principle plus regression cases holds.

## Recommended Prompt Policy

For GPT-5.5-like models, the safer direction is a shorter first-principles prompt with small ontology and render-path rules. Keep a few regression-backed patches, but prune blocks that no longer show measurable value.

For Gemini-like models, retain more explicit guardrails around costly boundary mistakes: do not create documents or posters unless asked, product UI should be represented as real screens or props, and "first few scenes" is not a full episode package.

Across providers, preserve deterministic runtime gates. Prompt policy should reduce mistakes, but the dispatcher and planner should still reject disallowed or costly behavior.

## Limitations

The benchmark used a small set of targeted cases and private run artifacts. The score numbers are internal rubric outputs. The conclusion should be read as a provider-sensitivity signal rather than a universal ranking of models.

## Conclusion

Patchwork prompt rules should be assessed, not worshiped or deleted wholesale. GenFlick's tests showed that GPT-5.5 could handle several patch-motivated cases with less bespoke wording, while Gemini exposed why explicit guardrails may still matter. The practical strategy is provider-sensitive prompting: compact first-principles instructions where model judgment is strong, explicit regression-backed boundaries where it is not.