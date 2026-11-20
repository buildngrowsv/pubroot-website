---
title: "The edited declaration changed answers through a direct attention edge in Qwen2.5-14B"
paper_id: "2026-454"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:13:16Z"
abstract: "The earlier declaration edit reversed 508 of 512 paired Python answers when the final prediction token alone could read the edited declaration. Blocking only that direct read and letting other tokens relay the edit produced zero of 512 reversals. With ordinary attention the same edit reversed 496 of 512. All three attention masks preserved the correct answers on every unedited program."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The earlier declaration edit reversed **508 of 512** paired Python answers when the final prediction token alone could read the edited declaration. Blocking only that direct read and letting other tokens relay the edit produced **zero of 512** reversals. With ordinary attention the same edit reversed 496 of 512. All three attention masks preserved the correct answers on every unedited program.

![Paired reversals and answer margins with unrestricted, direct-only and relay-only attention](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-paths.png)

## What the edit and the attention wall change

Each generated file defines two different classes. Both have the same attribute spelling within one version, and the alternate version changes both attributes to a different final letter. Their assigned values differ. The prompt ends in a read from one class, with the last letter left blank. Running the file in CPython verifies that the correct completion gives the selected class's value and the alternative raises an attribute error. There are two queries and two letter variants per group. We intervene only at the first class's attribute declaration token. The two queries come later and share exactly the same edited state for a given variant. [Task and example from the earlier relay study](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Executable prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The only checkpoint is the frozen Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. From 512 independent single-declaration calibrations, regress the hidden-state difference at the declaration after block 10 on the paired 26-letter indicator difference, with a ridge penalty of 0.02 times the mean diagonal of its Gram matrix. The first 25 left singular vectors of the fitted hidden-by-letter matrix form an orthonormal basis U. At the first declaration of each test variant, add UUᵀ times the partner-minus-original hidden-state difference. All other states at block 10 stay at their original values. [Calibration and subspace details](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

Use 512 fresh groups at generator indices 90000–90511. Cross original and edited source state with three Boolean causal masks for blocks 11–48. The unrestricted mask leaves every causal edge open. The direct-only mask allows the edited source to attend to itself and the final token to attend to the source. It blocks every other token from reading the source. The relay-only mask blocks just the final token's direct read. It leaves other tokens able to receive and relay the edit. All other causal edges remain unchanged. [Layer and mask implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## What changed at the readout

A reversal means both variants select the other's letter. We count it only for a group whose four unedited predictions are correct under every mask. All 512 groups met that condition. The score is the original-letter logit minus the partner-letter logit. Metrics use a strict sign, so tied predictions do not count.

| Attention after block 10 | Edited-class pairs reversed | Other-class pairs reversed | Edited-class mean original-letter margin before and after edit |
|---|---:|---:|---:|
| Unrestricted | 496 / 512 | 0 / 512 | +12.70 to −4.71 |
| Direct edge only from source | 508 / 512 | 0 / 512 | +10.95 to −3.25 |
| Indirect paths only from source | 0 / 512 | 0 / 512 | +13.00 to +6.33 |

Allowing the direct path alone increased reversals by 2.34 points over unrestricted attention (95% paired interval +0.78 to +4.10). At the same time, its mean logit margin crossed zero by a smaller amount. The direct-only reversal rate exceeded the relay-only rate by 99.22 points (+98.44 to +99.80). The relay paths reduced confidence despite preserving the winning answers. The same distinction applied to the other class. The unrestricted edit reduced its mean margin from +12.68 to +5.91 without a paired reversal. Intervals resample complete groups. [Saved scores, basis and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Full margins and counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

These interventions identify how this newly injected edit can propagate after block 10. Earlier layers may already have copied native declaration information to other tokens, which can help explain intact answers when the direct edge closes. The studied outputs are two candidate letters in generated programs, and the scope includes this checkpoint, source, and readout. A follow-up splits direct access at block 17. [Timing protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/attention_paths_study/verify.py` to re-execute the prompts and reproduce the statistics. The Studio run lasted six minutes and 52 seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed spatial walls and isolated paths within networks. OpenAI Codex designed and implemented the intervention, ran it on the owner's Apple M5 Ultra, verified the evidence and assisted with writing.