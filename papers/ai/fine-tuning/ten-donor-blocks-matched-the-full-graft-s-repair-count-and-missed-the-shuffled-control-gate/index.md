---
title: "Ten donor blocks matched the full graft\u2019s repair count and missed the shuffled-control gate"
paper_id: "2026-564"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T15:46:02Z"
abstract: "A ridge map predicting the frozen graft's 32 donor features from block 10 of a 28-block specialist solved 166 of 512 held-out Python repair groups in the 14B recipient. The full late features also solved 166. The matched map fit on shuffled target rows solved 143. The 23-group early-map advantage was 4.49 percentage points (95% paired interval \u22120.20 to +8.79), missing the prespecified five-point and positive-lower-bound requirements. Matching the full feature route's total did not qualify the early exit."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A ridge map predicting the frozen graft's 32 donor features from block 10 of a 28-block specialist solved **166 of 512** held-out Python repair groups in the 14B recipient. The full late features also solved **166**. The matched map fit on shuffled target rows solved **143**. The 23-group early-map advantage was **4.49 percentage points** (95% paired interval −0.20 to +8.79), missing the prespecified five-point and positive-lower-bound requirements. Matching the full feature route's total did not qualify the early exit.

![Complete held-out repair groups for the early source and controls](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-exit.png)

## Distill the features of a frozen specialist

Use the previously learned 32-coordinate bridge from Qwen2.5-Coder-7B to Qwen2.5-14B. The bridge reads from the 7B's last feed-forward module and adds an update to the 14B's stream after block 27. Extract the 7B block-10 residual at the prediction token and fit a ridge map from its 3,584 coordinates to the same normalized late features. Use 192 fresh bracket-decoy triplets and no answer labels. Fit an equal-size control with the same features and a row permutation of the targets, preserving the calibration target mean. Hold both pretrained checkpoints and both recipient bridges fixed. FitNets provides a precedent for regressing internal teacher features. This experiment tests replacement of a precise pretrained interface used by an unchanged recipient. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Frozen transplant](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [FitNets](https://arxiv.org/abs/1412.6550)

Score 512 held-out triplets with misleading brackets in inert Python string and comment text. Each group has three versions of one program, where one different opener determines the unique valid closer. Each arm scores the same four candidate tokens. Require all three predictions to be correct. Calibration and held-out IDs are disjoint. The full-bridge and early-bridge arms target the same site. The full 7B still runs in this diagnostic to provide a paired reference. [Archived programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Pinned source](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Feature source or reference | Complete groups / 512 |
|---|---:|
| Intact 7B specialist | 298 |
| Full teacher features in the recipient | 166 |
| Block-10 map in the recipient | 166 |
| Block-10 map with shuffled target rows | 143 |
| Matched bridge from host features | 68 |
| Zero donor feature | 0 |

The early and full feature arms solved 119 of the same groups. Each solved 47 that the other missed. The early map solved 49 groups that the full teacher also solved and all three host, shuffled and ablated controls missed. Its gain over the host bridge was 19.14 points (+14.45 to +23.83). The early map's feature mean-square error was 42.65% of a constant calibration-target mean predictor's error, while the shuffled fit was 151.23%. This separates representation fidelity from recipient behavior. The early map predicted those features substantially better, and the strong shuffled result still prevented the registered behavioral decision. The table compares one early cut and one affine fitting rule on a single constructed task. [Fitted matrices](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Held-out scores and feature predictions](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Reproduction

The original BF16 checkpoints and 168,960-parameter output bridge remained frozen on an arm64 Apple M5 Ultra with 256 GiB unified memory. The Studio used macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The run took 129.91 seconds at 45.64 GB peak MLX allocation. To check the programs, feature errors, completion outcomes and registered decision from the saved data, run `uv run --with numpy python [REDACTED_SECRET].py`. Replay the benchmark on Apple Silicon using the pinned source with `STUDIO_JOB_DIR` set to a new output directory. The owner proposed the specialist transplant. OpenAI Codex implemented, ran, audited and documented this comparison. [Receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)