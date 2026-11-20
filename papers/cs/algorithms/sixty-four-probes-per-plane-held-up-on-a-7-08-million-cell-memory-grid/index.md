---
title: "Sixty-four probes per plane held up on a 7.08-million-cell memory grid"
paper_id: "2026-512"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-11-20T12:09:28Z"
abstract: "An eightfold increase in grid volume still met the registered two-point margin against full observation with only 64 detector probes per plane. After shifted faults, sampled boundary inference recovered 69.58% of complete words. Full observation recovered 70.35%, and fixed boundaries recovered 63.02%. The sampled arm was 0.77 percentage points behind full observation (95% paired interval \u22121.06 to \u22120.50) and used at most 0.521% of the detector field for locating the boundaries."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

An eightfold increase in grid volume still met the registered two-point margin against full observation with only 64 detector probes per plane. After shifted faults, sampled boundary inference recovered **69.58%** of complete words. Full observation recovered **70.35%**, and fixed boundaries recovered **63.02%**. The sampled arm was 0.77 percentage points behind full observation (95% paired interval −1.06 to −0.50) and used at most **0.521%** of the detector field for locating the boundaries.

![Fixed, sparse and fully observed word retention at both sizes, alongside the paired noninferiority margin](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What stayed fixed as volume grew

The periodic lattice holds a working word and a saved word at each cell. A frozen local transport rule advances the working words under seven possible commands. A frozen binary detector reads local and neighboring signals. A write to the saved word requires two successive detector ticks and a confirming witness eight cells away. The controller chooses a witness axis independently in each of eight regions using the lowest prior detector co-activation at that separation. The benchmark scores exact recovery of all 32 intended bits per cell after the disturbance. The earlier study resolved both full observation and 64 stratified probes on an 884,736-cell lattice. [Earlier comparison and methods](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The new lattice has 192 cells per side and eight times the volume. For each axis, the known geometry has two parallel region boundaries 96 cells apart. The unknown translation is inferred by counting disagreements between adjacent slices of the previous detector field. The estimated offset maximizes the sum of the two disagreement rates at that separation. The full arm uses all 36,864 positions in every plane. The sampled arm divides each plane into 8×8 equal tiles and chooses one position per tile, fixed over that world's trials. The upper bound on the three-axis sample fraction is `3 × 64 / 192² = 0.521%`, compared with 2.08% on the smaller lattice. Both arms still use the full previous field for choosing the regional witness axis after the boundaries are estimated. [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Source pinned to the Studio run](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Each of eight new world seeds pairs the initial words, commands, legitimate writes, and fault masks across policy arms. The aligned and shifted cases share the generated faults before the shift. There are three unchanged checkpoints and 16 rounds of 16 transitions per checkpoint-world pair. Score rounds 9–16 and resample complete worlds in the paired bootstrap, keeping all matched rounds and checkpoints together. Compare each boundary estimate to the supplied true translation. Prespecified success requires a lower 95% retention bound at least −2 points versus full observation, at least a four-point retention gain over fixed boundaries with a positive lower bound, and legitimate-write acceptance of at least 98% in both layouts. Both matched fixed and known-boundary controls must have identical counts in the two archives. [Frozen checkpoint example](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-full-101.json) · [Verification code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## Paired results on 7,077,888 cells

| Boundary rule | Retained words, aligned | Retained words, shifted | Exact shifted boundary coordinates | False writes, shifted |
|---|---:|---:|---:|---:|
| Fixed geometry | 70.45% | 63.02% | — | 8.79% |
| Inferred from 64 probes per plane | 69.56% | 69.58% | 77.08% | 6.01% |
| Inferred from full observation | 70.35% | 70.35% | 95.31% | 5.83% |
| True boundaries supplied | 70.45% | 70.45% | — | 5.81% |

Under shifted faults, the sampled policy gained 6.56 points over fixed boundaries, with a paired 95% interval of +5.43 to +7.86. Both layouts retained 99.00% legitimate-write acceptance across all arms. The large run cleared every registered scale criterion. The smaller run had a 1.04-point sampled-minus-full deficit under shifted faults (−1.43 to −0.67). The two volumes use different worlds and ranges of possible shifts. The measured scale result is that the fixed sample count met the same margin at both sizes. [Raw full-field counts and offsets](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Raw stratified counts and offsets](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Independently recomputed metrics](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

Exact boundary-coordinate accuracy remained lower under sampling than under full observation. Word retention was close because it depends on the downstream choice of witness as well as coordinate accuracy. That relationship is descriptive here. The inference code still transfers the full detector field before sampling, and the subsequent regional routing uses full-field information. The sparse budget applies to the boundary-location statistic. The run covers synthetic faults in a fixed periodic planar partition family. It leaves independently moving regions, irregular boundaries, and end-to-end sparse device reads open. [Boundary and verification implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Run `uv run --with numpy python spatial_references/probe_scale_study/verify.py` from the repository root to verify the receipt and frozen checkpoint hashes, compare the two matched controls exactly, and reproduce the word counts, localization metrics and world-paired bootstrap intervals. The paired 192³ run took 3,615 seconds and reached 14.33 GB peak MLX allocation. It ran on an Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory, macOS 27.2, Python 3.12.16, MLX 0.32.4 in float32, and NumPy 2.5.5. The owner proposed testing spatial walls at larger scales. OpenAI Codex implemented and ran the comparison, verified the evidence and assisted with writing. [Execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)