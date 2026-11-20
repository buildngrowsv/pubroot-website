---
title: "Seven aligned coordinates reversed 502 of 504 answer pairs in a frozen 72B model"
paper_id: "2026-490"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:51:12Z"
abstract: "A frozen 7B coder supplied an operand that changed both arithmetic answers in 502 of 504 qualified pairs in Qwen2.5-72B. A norm-matched orthogonal edit reversed zero, and swapping the entire same-position native activation reversed 501. The seven-coordinate donor interface was originally fitted in a 14B model. We aligned its coordinates to the wider recipient by contrasting matched input states without using the larger model's answer predictions. On 499 shared native-correct pairs, the same method reversed 425 in 32B and 498 in 72B."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A frozen 7B coder supplied an operand that changed both arithmetic answers in **502 of 504** qualified pairs in Qwen2.5-72B. A norm-matched orthogonal edit reversed **zero**, and swapping the entire same-position native activation reversed **501**. The seven-coordinate donor interface was originally fitted in a 14B model. We aligned its coordinates to the wider recipient by contrasting matched input states without using the larger model's answer predictions. On **499 shared native-correct pairs**, the same method reversed **425** in 32B and **498** in 72B.

![Answer reversals on the same native-qualified pairs in the frozen 32B and 72B recipients](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-width.png)

## Cross-model bridge

All four models are frozen Qwen2.5 base checkpoints in BF16. The intervention point is the number of fully applied blocks.

| Role | Model | Revision | Residual width | Block boundary |
|---|---|---|---:|---:|
| Donor | Qwen2.5-Coder-7B | [0396a761](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/tree/0396a76181e127dfc13e5c5ec48a8cee09938b02) | 3,584 | 6 |
| Original interface | Qwen2.5-14B | [97e1e763](https://huggingface.co/Qwen/Qwen2.5-14B/tree/97e1e76335b7017d8f67c08a19d103c0504298c9) | 5,120 | 10 |
| Same-width control | Qwen2.5-32B | [1818d358](https://huggingface.co/Qwen/Qwen2.5-32B/tree/1818d35814b8319459f4bd55ed1ac8709630f003) | 5,120 | 13 |
| Wider recipient | Qwen2.5-72B | [efba10c8](https://huggingface.co/Qwen/Qwen2.5-72B/tree/efba10c8e54e91e0d9570ab5f7b51a958474d4cb) | 8,192 | 17 |

Use 256 separate direct-return Python input pairs with a changed assignment digit. Let `X` stack the differences projected onto the original seven 14B axes. Let `Y` stack the corresponding differences in the recipient's whole assignment state. Fit the write matrix `Wᵀ = (XᵀX + λI)⁻¹XᵀY`, with `λ = 0.02 × mean(diag(XᵀX))`. Compute the seven live coordinates with the pseudoinverse of `W`, centered by the two calibration means. The pre-existing donor affine map converts one separate 7B declaration to the desired seven-coordinate target. Subtract the coordinates of the live assignment, multiply the result by `W` to obtain an edit in the recipient's units, and add it to that assignment alone. This fits a new recipient coordinate map. It uses matched input contrasts and known assignment locations without using recipient answer scores. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Original donor mapping](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

An orthogonal seven-axis random basis gives the control the same per-site, pre-cast Euclidean norm. A full native exchange swaps the entire assignment state between partner inputs. Editing arithmetic is float32 and the replacement enters the remaining blocks in BF16. The unchanged model must uniquely predict the correct digit over the entire vocabulary in both variants to qualify. To reverse a pair, both edited variants must uniquely predict the alternate arithmetic answer. Test prompts and donor programs were identical across recipients. [Archived prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Earlier single-gain result](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

## Results on a shared answer panel

| Recipient | Native-correct pairs | Aligned reversals | Orthogonal reversals | Full-state reversals |
|---|---:|---:|---:|---:|
| 32B | 507 | 426 | 0 | 426 |
| 72B | 504 | 502 | 0 | 501 |
| 32B on the shared subset | 499 | 425 | 0 | 425 |
| 72B on the shared subset | 499 | 498 | 0 | 497 |

In 72B the alignment cleared the registered thresholds and beat the orthogonal arm by **99.60 percentage points**, paired 95% interval **99.01 to 100.00**. On the shared subset, 73 groups reversed only in the 72B alignment and zero reversed only in 32B. The difference was **14.63 points**, paired interval **11.62 to 17.84**, in a separately reported shared-pair comparison. Full native exchanges also reversed substantially more pairs in 72B. These results support portable operand information across residual widths on this task and show that the readout is more responsive to both interventions in this 72B checkpoint. They do not isolate parameter count, width or depth as the cause. The raw matched edit norms were compared within each recipient. Their units and scales differ between models. [Paired evidence](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-paired.json) · [32B audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-32b.json) · [72B audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-72b.json)

The alignment method builds on prior affine model stitching. The paired intervention moves one operand from an independently encoded donor program and checks whether the recipient computes the changed answer. The evidence concerns a known operand site, a fixed same-family model set and a one-digit arithmetic output. [Chen et al., NeurIPS 2025](https://proceedings.nips.[REDACTED_SECRET]-Abstract-Conference.html)

Run `uv run --with numpy python nested_surgery/numeric_width_study/verify.py 32b`, repeat with `72b`, then use `paired` to reproduce the shared count and interval. The 32B and 72B paths ran for 215.5 and 529.4 seconds and reported peaks of 66.9 and 147.1 GB MLX allocation. The Studio used an Apple M5 Ultra with 80 GPU cores, 256 GiB unified memory, Metal 4, macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. Model loads were sequential. The owner proposed larger-scale expert transplant comparisons. OpenAI Codex implemented, ran and verified the study and assisted with writing. [32B artifacts and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [72B artifacts and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])