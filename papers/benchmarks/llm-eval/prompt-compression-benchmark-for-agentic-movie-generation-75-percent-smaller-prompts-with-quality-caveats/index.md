---
title: "Prompt Compression Benchmark for Agentic Movie Generation: 75 Percent Smaller Prompts with Quality Caveats"
paper_id: "2026-137"
author: "buildngrowsv"
category: "benchmarks/llm-eval"
date: "2026-05-15T09:18:54Z"
abstract: "GenFlick benchmarked whether a large prompt stack for agentic movie generation could be compressed without losing core planning quality. The control prompt stack was approximately 145,593 editable prompt tokens. Two compact variants, first-principles-compressed-v1 and flow-overhaul-v1, reduced editable prompt text to about 37,325 and 36,595 approximate tokens respectively, a 74-75 percent reduction. No-media agent-flow runs compared variants across first-shot movie, TV pilot, episode opening, first-frame action, and edit flows. GPT-5.5 carried compressed prompts surprisingly well; the leading flow-overhaul variant reached 95.0 A+ on one first-shot lane and remained close to production on several additional cases with fewer phases. Gemini 3.1 Pro exposed sharper regressions around schema exactness, multi-shot floors, character prompt length, and staging completeness. The benchmark suggests that useful prompt \"patchwork\" often compresses into concise schema and rubric facts rather than long narrative prose."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from docs/PROMPT-VARIANT-COMPRESSION-FLOW-BENCHMARK-2026-04-30.md and GenFlick agent-flow benchmark notes. No media-generation provider calls were made for this Pubroot packaging step."
---

## Benchmark Question

Large prompt stacks are expensive to edit, review, and reason about. GenFlick's production movie-generation agent had accumulated extensive craft guidance, schema reminders, examples, provider constraints, and patches for historical failures. The benchmark question was whether that prompt stack could be compressed substantially while preserving action validity and project quality.

This benchmark did not generate paid image or video media. It used GenFlick's no-media agent-flow harness, which calls the live model path but skips downstream media generation. The inspected artifacts include planner output, phase outputs, parsed actions, dispatch summaries, project state, and rubric scores.

## Variants

The control was the current production prompt stack. The main compressed candidates were `first-principles-compressed-v1` and `flow-overhaul-v1`.

The production stack had about 145,593 approximate editable prompt tokens, estimated by characters divided by four. This is not the full runtime context, because project state and user messages are added later, but it is useful for comparing prompt source size.

The compressed first-principles variant was about 37,325 approximate prompt tokens, a 74.4 percent reduction. The flow-overhaul variant was about 36,595 approximate prompt tokens, a 74.9 percent reduction. Earlier first-principles variants were not true compression experiments; they changed only a few components and stayed near production size.

## Method

The harness ran fixed movie-creation and edit prompts against model and prompt variants. The evaluation emphasized observable project quality rather than prose style. A run could produce fluent assistant text and still fail if parsed actions were malformed, required schema fields were absent, generated clips lacked enough staging detail, or reference-generation inputs were attached incorrectly.

Representative lanes included:

- First-shot movie: "Trailer for aliens vs robots."
- TV pilot first sequence: "Signal House."
- TV episode opening: "The Orchard Static."
- First-frame action matrix.
- Lighthouse color edit.
- Medium continuity edit.
- Major genre pivot.
- Reference-generation character, set, and style inputs.

Scores were reported as letter-grade rubric outputs. The benchmark also tracked phase count because one goal of the flow-overhaul variant was to reduce the number of model phases.

## Results

On the first-shot movie lane, GPT-5.5 performed strongly across variants. The production control scored 99.0 A+ with eight phases. After iteration, `flow-overhaul-v1` scored 95.0 A+ with five phases and passed all gates. The compressed first-principles variant also stayed viable, though some multi-shot floors remained weaker.

Gemini 3.1 Pro was more sensitive. In the same first-shot family, the compact variants initially scored lower, but improved after exact schema and rubric facts were restored. The iterated flow-overhaul result reached 94.1 A on the first-shot movie lane, while earlier compact versions exposed weaknesses around staging, continuity, and character prompt floors.

On the TV pilot lane, GPT-5.5 production remained strongest in one comparison, but the flow-overhaul variant stayed reasonably close while using fewer phases. Gemini results were weaker: the flow-overhaul variant failed one TV pilot comparison at 74.8 C, showing that compression can shift quality differently across providers.

On the TV episode opening lane, production remained strongest for both GPT-5.5 and Gemini. GPT-5.5 still produced acceptable compact results, but Gemini's flow-overhaul result dropped to 78.0 C. This was a useful sensitivity check: the compact prompt could dispatch, but did not preserve enough quality for all model/provider combinations.

An edge-patch sequence produced the most actionable finding. Broad patches that encouraged more aggressive overwrite behavior regressed. Narrow patches that restored exact schema placement for reference-generation media ids worked. A reference-generation lane that initially failed for flow-overhaul improved to 96.7 A+ after a concrete schema/renderability patch.

## What Compression Broke

The compressed prompts initially failed where the old prompt stack had been carrying compact but important contract knowledge.

Some action schemas needed exact field names and nesting. For example, character and set variants required parent names plus variant descriptions and modifiers. Prop assignment required array-shaped prop names and the clip number within the scene. Reference-generation media ids needed to be nested inside character, set, or prop objects rather than floating at the wrong layer.

Some rubric floors were implicit in the long prompt and had to be restated concisely. Multi-shot scene preambles needed enough words, constraints needed a minimum specificity floor, and segment counts needed to be explicit.

Some enum boundaries needed to be named. Gemini sometimes emitted compound genre keys where only one enum value was valid. Adding a compact enum instruction improved dispatch validity.

## Interpretation

The main finding is not that long prompts are unnecessary. It is that some long prompt material is doing different jobs. Narrative explanation can often be shortened. Exact schema facts, enum values, phase ownership, and rubric floors should remain explicit.

GPT-5.5 appeared more tolerant of compression in these runs. It could infer or preserve quality from a smaller first-principles prompt more reliably than Gemini. Gemini served as a useful regression detector because it exposed where compact prompts had removed operational facts the runtime still needed.

The benchmark also supports separating durable contract knowledge from prose. If an instruction is really an action-schema reference, it should probably live as a concise schema fact near the action contract, not as repeated narrative coaching in a large system prompt.

## Limitations

The benchmark used approximate prompt-token estimates rather than provider tokenizer counts. The runs skipped paid media generation, so they evaluated planning and project-state quality rather than final pixels or video motion. The supporting repository is private, which limits external reproducibility unless reviewers have access.

The score labels are internal rubric outputs. They are useful for comparing variants within GenFlick but should not be treated as a universal movie-quality metric.

## Conclusion

GenFlick reduced editable prompt text by roughly 75 percent while preserving viable GPT-5.5 behavior on several agentic movie-generation lanes. The best compact flow was not universally safe: Gemini exposed quality regressions, and some edge cases needed precise schema facts restored. The practical lesson is to compress narrative prompt prose first, preserve exact runtime contracts, and test against a provider that is less forgiving of missing operational detail.