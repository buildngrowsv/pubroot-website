---
title: "A fixed 25-coordinate reference carried an identifier through seven Qwen blocks"
paper_id: "2026-432"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:24:16Z"
abstract: "Holding the original 25 coordinates fixed preserved all 512 of 512 correct identifier pairs in both Qwen2.5-Coder-7B and Qwen2.5-14B. Holding the partner program's coordinates fixed reversed all 512 pairs in each model. A fixed random subspace with a matched initial edit reversed zero. These are forced two-choice completions in generated Python programs."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Holding the original 25 coordinates fixed preserved all **512 of 512** correct identifier pairs in both Qwen2.5-Coder-7B and Qwen2.5-14B. Holding the partner program's coordinates fixed reversed all 512 pairs in each model. A fixed random subspace with a matched initial edit reversed zero. These are forced two-choice completions in generated Python programs.

![The original letter stays preferred with a clean or random reference and loses with the learned partner reference](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## What stayed fixed

Each prompt ends with an incomplete identifier in a Python return statement. Each pair changes one letter in its earlier declaration. We use 512 calibration pairs to find the 25 directions that capture differences among the 26 possible letters. Twenty-six letter indicators have 25 independent differences. Test programs use fresh indices 12000–12511. We keep both pretrained checkpoints frozen and intervene after block 6 in Qwen2.5-Coder-7B base at revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and after block 10 in Qwen2.5-14B base at revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Earlier single-edit result and fit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

The reference contains 25 coordinates of the declaration token's state. Before each of seven consecutive blocks and at the segment exit, we restore those coordinates to their entry values from either the original program or its partner. The remaining coordinates and tokens continue through the normal computation. The comparison restores 25 orthogonal random directions, with the same initial change norm for the partner arm before conversion to the model's inference dtype. This matches the initial displacement only. The two restoration paths can differ at subsequent layers. The trial uses the same known source token in both programs. [Inference and intervention code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Reference | 7B pair outcomes | 14B pair outcomes |
|---|---:|---:|
| Native | 512 retained | 512 retained |
| Learned, keep original | 512 retained | 512 retained |
| Random, keep original | 512 retained | 512 retained |
| Learned, use partner | 512 reversed | 512 reversed |
| Random, use matched edit | 0 reversed | 0 reversed |

A reversal means both programs prefer the other program's letter. The prespecified shared denominator contains pairs both clean reference conditions preserve. All 512 qualify in both models. Mean correct-letter logit margins for the learned partner condition were −12.73 and −11.85. The random partner condition stayed at +12.31 and +11.75. Every pair contributes the same positive contrast, so the panel bootstrap is +100 percentage points at both bounds. The interval describes these generated programs and provides no variation across model families. [Saved scores and prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent numerical audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

This extends a one-time coordinate exchange into a seven-block forward intervention. It establishes that enforcing a known reference at a known token can preserve and control this completion. The transformer runs all its original operations and can read the coordinates. Whether the model already has a necessary fixed route, whether enforcing one saves computation, and whether the same directions govern more complex Python tasks remain open. This experiment uses a fitted subspace in frozen networks. Earlier work on variable-width training uses a distinct mechanism that skips computation on absent coordinates and restores them on widening. [Distributed causal alignment](https://arxiv.org/abs/2303.02536) · [Variable-width transformers](https://arxiv.org/abs/2606.18246) · [Two-definition follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/identifier_tunnel_study/verify.py` from the repository root to re-execute the prompts in Python and recover the paired statistics. The experiment ran for four minutes and four seconds under MLX 0.32.4, MLX-LM 0.32.2, Python 3.12 and NumPy 2.5.5 on the owner's Apple M5 Ultra. The owner proposed the protected forward reference. OpenAI Codex implemented the intervention, ran the study, audited the results and assisted with writing. [Pinned Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)