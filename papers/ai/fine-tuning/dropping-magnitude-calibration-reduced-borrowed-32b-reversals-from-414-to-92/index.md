---
title: "Dropping magnitude calibration reduced borrowed 32B reversals from 414 to 92"
paper_id: "2026-473"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:07:00Z"
abstract: "The 14B affine interface reversed 92 of 507 initially correct pairs when its edit magnitude was used directly in the 32B host. The same edit direction, previously matched to the magnitude of a fitted 32B intervention, reversed 414 of 507 on those identical pairs. The new equal-norm random edit reversed zero. The raw interface missed both the registered transfer threshold and the margin for matching the scaled arm."
score: 6.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The 14B affine interface reversed **92 of 507** initially correct pairs when its edit magnitude was used directly in the 32B host. The same edit direction, previously matched to the magnitude of a fitted 32B intervention, reversed **414 of 507** on those identical pairs. The new equal-norm random edit reversed zero. The raw interface missed both the registered transfer threshold and the margin for matching the scaled arm.

![Raw and scaled reversal counts on the exact same cohort, with the distribution of raw edit norms](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-32b.png)

## What changed

The source is the same frozen Qwen2.5-Coder-7B model and the target is the frozen Qwen2.5-32B base model. Each 7B program returns an operand directly. Its corresponding 32B program computes addition or subtraction with that operand, and the prompt ends before the result digit. We reuse the exact same 512 held-out host and donor pairs and source positions. The archived 14B interface projects the target donor activation after block 6 into a target seven-coordinate state, which replaces the 32B assignment's projection onto the archived 14B basis after block 13. The raw intervention does this directly. The earlier scaled arm multiplied its direction by a scalar derived from a fitted 32B edit for that prompt. The checkpoints stay frozen in both cases. [Registered raw comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Original cross-size experiment and model revisions](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Inference code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

The new random control uses the archived 14B orthogonal basis and matches the raw edit's norm at each token. This calculation uses the 14B map and existing 32B activation. It needs no fitted 32B mapping or magnitude. Its principal comparison uses the same 507 pairs in which both native digits uniquely topped the vocabulary in both runs.

| Intervention | Both alternative digits unique top predictions |
|---|---:|
| Raw 14B interface in 32B | 92 / 507 |
| Equal-norm random from 14B directions | 0 / 507 |
| Same borrowed direction with fitted 32B magnitude, archived run | 414 / 507 |

The raw-minus-scaled difference was −63.51 percentage points, with paired 95% interval −67.65 to −59.17. The raw advantage over random was +18.15 points (+14.99 to +21.50). The raw norm had a median 64.35% of its matched counterpart, with 10th and 90th percentiles at 53.12% and 71.23%. The trial holds the panel and direction fixed while changing the magnitude rule. A follow-up estimates one gain from native assignment-state differences without arithmetic answer labels. [Saved ranks and norms](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Answer-free gain protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/numeric_raw_32b_study/verify.py` to check the source digests, cohort, edit norms and comparison. The Studio run took two minutes and 38 seconds on the owner's Apple M5 Ultra. The owner proposed testing transplanted interfaces at larger model sizes. OpenAI Codex designed and operated this comparison, checked the evidence and assisted with writing. [Pinned execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)