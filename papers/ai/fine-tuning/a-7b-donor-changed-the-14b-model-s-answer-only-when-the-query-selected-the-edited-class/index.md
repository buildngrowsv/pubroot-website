---
below_floor: true
quality_floor: 7.0
title: "A 7B donor changed the 14B model\u2019s answer only when the query selected the edited class"
paper_id: "2026-440"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:33:56Z"
abstract: "A Qwen2.5-Coder-7B activation change from a separate Python function reversed 504 of 512 paired answers in Qwen2.5-14B when the receiving class was the one read by the query. Applying the identical vector at the other class reversed 0 of 512 pairs. The donor and host used different identifier stems and surrounding code. The host's confidence still fell on the unselected-class arm, despite the winning answer remaining correct."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A Qwen2.5-Coder-7B activation change from a separate Python function reversed **504 of 512** paired answers in Qwen2.5-14B when the receiving class was the one read by the query. Applying the identical vector at the other class reversed **0 of 512** pairs. The donor and host used different identifier stems and surrounding code. The host's confidence still fell on the unselected-class arm, despite the winning answer remaining correct.

![Reversals by receiving class and intervention](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-binding.png)

## What crossed the model boundary

The host defines two classes that share an attribute spelling. A final query chooses a class and leaves the last letter of the attribute off. The donor sees a separate function that uses the same candidate letters with a different stem. It sees no host class, class selector or hidden state. Two donor passes provide the source difference. The exact 25 by 25 map from the earlier single-definition experiment converts that difference into a change in the host's activation space. The same vector is used for either source location and either query. It is applied after block 10 in the host, using the declaration position after block 6 in the donor. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Previous map and calibration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Host intervention | Read first class | Read second class | Total paired reversals |
|---|---:|---:|---:|
| Donor vector applied at the selected class | 248 / 256 | 256 / 256 | 504 / 512 |
| Same vector applied at the other class | 0 / 256 | 0 / 256 | 0 / 512 |
| Full host state exchanged at the selected class | 250 / 256 | 256 / 256 | 506 / 512 |

The unmodified host gave all four correct choices on all 256 fresh groups, so every group qualified. The selected-minus-unselected reversal difference was +98.44 points, with a paired 95% bootstrap interval of +97.27 to +99.41. For queries to the first class, the mean original-letter margin fell from +12.72 native to −4.87 with the selected edit and +5.03 when the edit was applied to the other class. The other-class edit had a comparable effect on confidence for queries to the second class. Selection at the level of winning answers was stronger than isolation at the level of scores. [Raw programs, margins and run receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent verification](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The checkpoints are Qwen2.5-Coder-7B base at `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base at `97e1e76335b7017d8f67c08a19d103c0504298c9`. Neither checkpoint was updated. The letter alternatives, source sites and receiver site are specified. The result shows cross-model transfer of a low-dimensional change that the recipient uses according to the prompt in this generated two-choice test. It leaves open whether learned interfaces can transfer whole skills or support general code generation. Prior work used affine maps for cross-size feature transfer and activation edits for entity–attribute binding. [Cross-size feature transfer](https://arxiv.org/abs/2506.06609) · [Binding in context](https://arxiv.org/abs/2310.17191)

Run `uv run --with numpy python [REDACTED_SECRET].py`. The Studio run took two minutes and 23 seconds under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and Tokenizers 0.23.3. The owner proposed selective internal routing and cross-model expert transfer. OpenAI Codex designed and implemented this comparison, operated it on the owner's Apple M5 Ultra, verified the outputs and assisted with writing.