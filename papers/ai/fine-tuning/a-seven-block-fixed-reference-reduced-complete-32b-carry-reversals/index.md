---
title: "A seven-block fixed reference reduced complete 32B carry reversals"
paper_id: "2026-486"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:39:30Z"
abstract: "Keeping the transplanted coordinates fixed for seven additional blocks reduced complete two-operand carry reversals from 358 to 333 of 512 groups. The same protection applied to native values kept all 512 native groups correct. The hold improved individual transitions to two-digit answers from 689 to 705 and reduced transitions back to one digit from 669 to 632. This identifies a cost of preserving this transplanted activation in this recipient."
score: 7.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Keeping the transplanted coordinates fixed for seven additional blocks reduced complete two-operand carry reversals from **358 to 333 of 512 groups**. The same protection applied to native values kept all 512 native groups correct. The hold improved individual transitions to two-digit answers from 689 to 705 and reduced transitions back to one digit from 669 to 632. This identifies a cost of preserving this transplanted activation in this recipient.

![Complete carry groups and the two directions of digit-length changes](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-carry.png)

## Intervention and controls

The same 512 four-variant Python addition groups and donor sources were used as in the one-shot 32B run. Each edited group needs all four greedy answers under a partner assignment of both digits. Each token must win over the full vocabulary, followed by a valid answer terminator. The recipient is Qwen2.5-32B BF16 at revision [1818d358](https://huggingface.co/Qwen/Qwen2.5-32B/tree/1818d35814b8319459f4bd55ed1ac8709630f003), 64 blocks and 5,120 coordinates. The donor is Qwen2.5-Coder-7B at [0396a761](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/tree/0396a76181e127dfc13e5c5ec48a8cee09938b02), read after six blocks. The seven-axis and affine factors were originally estimated at block 10 in Qwen2.5-14B at [97e1e763](https://huggingface.co/Qwen/Qwen2.5-14B/tree/97e1e76335b7017d8f67c08a19d103c0504298c9). The 32B intervention occurs at both assignment tokens after 13 blocks. The scalar gain of 2.624717 and the edit at that boundary stay unchanged. [Registered comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Original protocol and archived one-shot control](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Let `B` be the 5,120×7 orthonormal donor-aligned basis. For each of the two edited assignment tokens, the post-splice seven values are `r = h₁₃ B`. After blocks 14 through 20, step `k` replaces the state `hₖ` with `hₖ + (r − hₖ B) Bᵀ`. This restores the same projection up to the model's BF16 rounding. Other coordinates and positions continue to evolve normally. Projection arithmetic is float32. The no-donor test clamps the original native projection under the same rule. The orthogonal test starts with a per-site norm-matched change and clamps its own seven-coordinate projection. Subsequent corrections arise from the respective trajectories. [Projection implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Token-path scoring](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Prompt and donor archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Outcomes

| Condition | All four edited answers, out of 512 | 1 → 2 digits, out of 747 | 2 → 1 digits, out of 747 |
|---|---:|---:|---:|
| One-shot edit | 358 | 689 | 669 |
| Hold donor projection through seven blocks | 333 | 705 | 632 |
| Hold orthogonal projection through seven blocks | 0 | 0 | 0 |
| Swap both full states once | 454 | 711 | 737 |

The hold improved 27 groups and lost 52, yielding **−4.88 percentage points** versus one-shot editing with a paired 95% interval of **−8.20 to −1.56**. It missed both the prespecified improvement gate and the earlier 80% carry target. The native hold stayed at 512/512. A post hoc token-path audit found that every failed shortening case first failed at the initial digit. Every shortening case that chose the correct first digit also chose an allowed terminator. The asymmetry concerns these observed answer paths. It does not locate the remaining mechanism or predict behavior on other tasks. Related work trains variable-width networks with bypassed coordinates and uses fitted mappings to move features across pretrained models. This experiment keeps the existing networks frozen and reimposes just two token-local projections during an intervention. [Variable-Width Transformers, §2](https://arxiv.org/html/2606.18246v1#S2) · [Transferring Linear Features Across Language Models With Model Stitching](https://proceedings.nips.[REDACTED_SECRET]-Abstract-Conference.html)

Recompute program validity, outcome overlaps and paired intervals with `uv run --with numpy python nested_surgery/numeric_hold_32b_study/verify.py`. The run took 6 minutes 40 seconds and used 67.1 GB peak MLX allocation on an Apple M5 Ultra with 80 GPU cores, 256 GiB unified memory and Metal 4. The environment was macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed the fixed reference and transplanted experts. OpenAI Codex implemented and ran the paired comparison, audited the outputs and assisted with writing. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)