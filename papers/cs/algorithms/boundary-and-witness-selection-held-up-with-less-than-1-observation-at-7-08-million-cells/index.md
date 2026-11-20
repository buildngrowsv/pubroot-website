---
title: "Boundary and witness selection held up with less than 1% observation at 7.08 million cells"
paper_id: "2026-525"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-11-20T13:39:57Z"
abstract: "With 64 detector lines per axis and 1,024 dedicated detector anchors per region, a 192\u00b3 memory grid recovered 69.27% of whole words after translated faults. Dense witness selection with the exact same inferred boundaries recovered 69.58%, and fixed geometry recovered 63.02%. The sampled policy's deficit to the matched dense witness arm was 0.31 percentage points (95% paired deficit interval 0.22 to 0.41). Its two statistics used at most 0.984% of the field as input. All registered scale criteria passed."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

With 64 detector lines per axis and 1,024 dedicated detector anchors per region, a 192³ memory grid recovered **69.27%** of whole words after translated faults. Dense witness selection with the exact same inferred boundaries recovered **69.58%**, and fixed geometry recovered **63.02%**. The sampled policy's deficit to the matched dense witness arm was **0.31 percentage points** (95% paired deficit interval 0.22 to 0.41). Its two statistics used at most **0.984%** of the field as input. All registered scale criteria passed.

![Shifted retention at two grid sizes and the one-point paired dense-witness margin](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-one-percent.png)

## Scale the same observation count

The periodic lattice has one working 32-bit word and a saved copy at each position. Frozen local weights move working values under seven commands. A learned detector uses local and neighboring binary inputs, and a write needs two consecutive positive detector ticks with an eight-cell witness. Correlated false pulses run along different axes in different regions. The witness policy chooses the least co-active axis in each of the eight regions. The benchmark tests whole-word recovery after these disturbances in a specified simulated family. [Frozen update and readout code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Smaller dedicated-sampling benchmark](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Both matched policies place 64 stratified lines per axis. They locate the translated region boundaries by maximizing disagreement across two parallel candidate slices separated by half the grid. For the sparse witness decision, use 1,024 random base coordinates per inferred region, fixed across rounds in its regional coordinates. Read each base and its three axial neighbors at distance eight, wrapped inside that region. Estimate all three pairwise co-activation rates from the same base positions and choose the minimum. The comparator calculates co-activation over the entire region after inferring the same boundaries from the same lines. At `192³`, the upper bound on scalar readings consulted in the sampled decision is `3 × 64 × 192 + 4 × 8 × 1024 = 69,632` of `7,077,888`. The equivalent upper fraction at 96³ was 5.79%. The simulator stages the full field for both policies. [Preregistered scale protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Pinned simulation source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The three frozen weight files, eight worlds, exact initial words, motion and write streams, and fault geometries are paired with the original 192³ archive. The latter eight of 16 rounds per world contribute to exact 32-bit retention. Each round has 16 updates. The bootstrap resamples whole worlds together with their matched checkpoints and rounds. Every inferred boundary and every fixed and true-boundary summary count matched the corresponding archive exactly. [Dedicated-sample counts and offsets](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Matched dense-witness archive](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz)

| Configuration | Retention, aligned | Retention, shifted | False writes, shifted |
|---|---:|---:|---:|
| Fixed boundaries, dense witness | 70.45% | 63.02% | 8.79% |
| Sampled boundaries and sampled witness | 69.22% | 69.27% | 6.10% |
| Same sampled boundaries, dense witness | 69.56% | 69.58% | 6.01% |
| Fully observed boundary inference and dense witness | 70.35% | 70.35% | 5.83% |
| True boundaries provided, dense witness | 70.45% | 70.45% | 5.81% |

The aligned deficit against the matched dense witness was 0.34 points (0.27 to 0.42). The shifted advantage against fixed geometry was +6.25 points (+5.15 to +7.50). Legitimate-write acceptance was 99.00% in all arms. Both layouts cleared the one-point margin and the shifted comparison cleared the four-point advantage criterion. The difference from the fully observed policy includes boundary sampling as well as witness sampling. That row is context for the matched dense-witness comparison. Practical latency and device materialization are addressed in a separate paired test. [Computed evidence](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Direct-observation timing protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Run `uv run --with numpy python [REDACTED_SECRET].py` from the public repository root. The verifier reproduces the reported statistics from the raw arrays, verifies the three frozen file hashes and checks exact matching of the controls. The run took 1,812 seconds and reached 14.33 GB peak MLX allocation. Environment capture from the Studio records arm64 Apple M5 Ultra and 256 GiB memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4 in float32 and NumPy 2.5.5. The owner proposed larger spatial models and OpenAI Codex implemented, ran, verified and documented this benchmark. [Independent verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Studio environment capture](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt)