---
title: "Confidence routing gained 61 repairs on bracket decoys at a 23% graft-call budget"
paper_id: "2026-556"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T15:13:27Z"
abstract: "A frozen 7B coding specialist and its 14B graft solved 504 of 768 fresh Python repair groups when their scores were blended only on low-confidence specialist prompts. The intact specialist solved 443. Random blending at the same 22.92% graft-call budget averaged 459.34. The route solved 646 matched neutral groups versus 652 for the intact specialist. Its neutral confidence bound crossed the prespecified two-point tolerance, leaving the full decision unresolved."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A frozen 7B coding specialist and its 14B graft solved **504 of 768** fresh Python repair groups when their scores were blended only on low-confidence specialist prompts. The intact specialist solved **443**. Random blending at the same **22.92%** graft-call budget averaged **459.34**. The route solved **646** matched neutral groups versus **652** for the intact specialist. Its neutral confidence bound crossed the prespecified two-point tolerance, leaving the full decision unresolved.

![Complete groups for standalone, randomized, confidence-gated and always-on fusion](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Freeze the confidence policy before scoring

Previous experiments trained an affine bridge from the 7B coder's final MLP output into the 14B host after block 27. That graft solved some bracket repairs the intact donor missed, though the donor was better overall. A separate 256-group discovery panel supplied the absolute threshold for the standalone model's margin between its top two candidate logits. In the new comparison, if the margin is at or below **0.5625**, use 75% of the 7B logits and 25% of the graft's logits. Otherwise use the standalone answer. Both pretrained checkpoints and the 168,960-parameter bridge remain frozen. The conditioning depends only on the candidates from the 7B forward pass. Model score fusion and post-hoc calibration have established precedents. [Prior graft and discovery evidence](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered routing protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Guo et al.](https://arxiv.org/abs/1706.04599)

Score new triplets with unique executable delimiter completions. The decoy condition adds brackets inside a Python string and comment that the parser ignores. Its neutral companion replaces those bracket characters with matched letters. Each group scores one only if the highest of four candidates is correct for all three alternatives. The exhaustive experiment computed logits for both paths on every prompt to enable paired comparisons. Random routes match the exact number of graft calls within each layout and average 32 independent seeded assignments. A separate sparse-execution check ran only the selected 14B inputs on the first eight batches and matched every candidate winner in 12 neutral and 19 decoy calls. These are call-budget and correctness measurements. End-to-end speed depends on batching and was outside the preregistered endpoint. [Pinned runner](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Exact matched programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

| Rule | Neutral correct / 768 | Decoy correct / 768 |
|---|---:|---:|
| Intact 7B specialist | 652 | 443 |
| Always use the graft | 303 | 224 |
| Hard substitution on the confidence mask | 606 | 455 |
| Random blend at identical call volume | 650.25 | 459.34 |
| Confidence-gated blend | 646 | 504 |
| Always blend | 644 | 509 |

The confidence route gained **7.94 percentage points** on decoys over standalone (95% paired interval +5.47 to +10.55) and **5.81 points** over matched random (+3.88 to +7.84). It recovered 82 groups and lost 21 relative to standalone. The neutral change was **−0.78 points** (−2.60 to +1.04) with calls on 12.33% of prompts. Both call fractions were below one third. The frozen rule preserved most of the gain from constant blending under decoys, and the neutral comparison failed the confidence-bound criterion. A larger confirmation holds the threshold and weights fixed and uses 2,304 additional groups per layout. [Exact scores and selected prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Neutral score archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Paired audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Registered confirmation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

## Reproduction

The frozen Qwen2.5-Coder-7B and Qwen2.5-14B base checkpoints used BF16. The Apple M5 Ultra Studio ran Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3 on macOS build 26B118 with 256 GiB unified memory. Exhaustive scoring took 170.20 seconds. Run `uv run --with numpy python nested_surgery/frozen_graft_route_study/verify.py` from the repository root to check the training artifact hash, exact matching, calls and paired statistics. To rerun with the models, link the original trained bridge's result directory as `runs/large-qwen-learned-output-port` under a temporary queue root; set `STUDIO_QUEUE_ROOT` and `STUDIO_JOB_DIR` and run the pinned inference code. The owner proposed expert surgery and conditional routing. OpenAI Codex implemented, ran and independently audited this experiment. [Receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)