---
title: "Pulse timing determined whether 32,768 writable references survived false signals"
paper_id: "2026-478"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:14:27Z"
abstract: "On a 32,768-voxel grid, a write gate that required two consecutive confirmations preserved 100% of 32-bit words under separated false pulses. Thresholding each pulse independently preserved 29.75%. A soft two-tick gate preserved 98.79%. When the same false pulses arrived consecutively, all three fell to 29.91%. Every policy accepted all legitimate writes at the immediate readout. The two-tick rule rejects isolated errors and accepts errors that reproduce its entire confirmation pattern."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On a **32,768-voxel grid**, a write gate that required two consecutive confirmations preserved **100%** of 32-bit words under separated false pulses. Thresholding each pulse independently preserved **29.75%**. A soft two-tick gate preserved **98.79%**. When the same false pulses arrived consecutively, **all three fell to 29.91%**. Every policy accepted all legitimate writes at the immediate readout. The two-tick rule rejects isolated errors and accepts errors that reproduce its entire confirmation pattern.

![Exact recovery after short and long waits and after either false pulse timing](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## The original reference after a longer wait

Three frozen local controllers trained on side-four cubes were tested on 64 pairs of side-16 cubes. Each voxel began with a 32-bit word and could conditionally save a transported word at step eight. The paired world used the opposite save signal. After that step the prescribed rule forbids every write. We kept the learned transport and restore weights the same and changed only the final write gate from its sigmoid value to a threshold at zero logit. Recall at transition 16 or 128 counts only positions where the paired tasks have different correct words. Both complete words must be correct. [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Frozen weights](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Execution and scores](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

| Gate | Matched pairs correct at 16 | Matched pairs correct at 128 |
|---|---:|---:|
| Native soft gate | 770,634 / 770,637 | 0 / 770,637 |
| Thresholded gate | 770,637 / 770,637 | 770,637 / 770,637 |

Counts pool checkpoints on the same 64 world pairs. Each checkpoint had 256,879 eligible pairs. A sigmoid assigns positive write weight even to the generator's intended no-write cases. Repeated soft updates can therefore alter the saved state. The thresholded rule can copy that state forward exactly when its score stays negative.

## Reopening the reference for new writes

The next test used 24 shared worlds of side 32 and 256 transitions. Each of 16 rounds contained legitimate two-tick writes on randomly selected voxels. Faults injected the exact same number of positive ticks on the same 4×4×4 tiles either with a gap or consecutively. The model saw the local inputs and, for the two-tick rules, its previous gate value. The provenance simulator followed the source address that should be stored after each true write. It used the actual transport command and the true write mask, which was hidden from the policy. All evaluation used the last eight rounds, with the first eight allowing history to accumulate. [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Execution and scores](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

| Gate | After true writes | After separated faults | After consecutive faults |
|---|---:|---:|---:|
| Threshold every tick | 100% | 29.75% | 29.91% |
| Multiply two soft scores | 100% | 98.79% | 29.91% |
| Require two threshold-positive ticks | 100% | 100% | 29.91% |

Requiring confirmation improved exact recovery on separated pulses by **70.25 percentage points**, with a paired 95% bootstrap interval of **69.91 to 70.57** across worlds. The soft two-tick gate met the registered two-point margin. The post-fault rates pool 18,874,368 word reads per timing and policy, with 24 independent worlds as the resampling unit. Immediate true-write accuracy pools about 2.36 million selected reads per timing and policy. The controller therefore remained writable over many rounds. Time between false pulses mattered more than their count.

## What the comparison establishes

The write grammar and local topology are supplied, and only the original gate and transport weights were trained. The fault test characterizes a controlled synthetic memory, with the same initial words and movement in both timings. A two-tick rule cannot distinguish a valid signal from a fault with the same locally observed two-tick pattern. A further independent signal would change the information available to the gate. The setup connects to gated memory cells and work on matching gates to the time scales of sequences. [Gers, Schmidhuber and Cummins](https://doi.org/10.1162/089976600300015015) · [Tallec and Ollivier](https://arxiv.org/abs/1804.11188)

Run `uv run --with numpy python spatial_references/long_hold_study/verify.py` to verify the receipts and checkpoint digests and reproduce the counts and fault interval independently of MLX. The owner proposed revisiting the protected reference at much larger volume. OpenAI Codex designed and ran the studies over SSH on the owner's M5 Ultra, verified the results and assisted with writing. The long wait and fault runs took 3.95 and 18.86 seconds with 303 MB and 142 MB peak MLX allocation. [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)