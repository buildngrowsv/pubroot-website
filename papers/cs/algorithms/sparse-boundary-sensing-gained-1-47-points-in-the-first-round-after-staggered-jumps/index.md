---
title: "Sparse boundary sensing gained 1.47 points in the first round after staggered jumps"
paper_id: "2026-542"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-11-20T14:42:46Z"
abstract: "On a simulated lattice of 7,077,888 cells, a controller that consulted at most 0.984% of the detector field retained 72.90% of complete words in the first round following each of 24 staggered boundary jumps. Holding calibration fixed retained 71.44%, and supplying the new positions retained 74.48%. The gain over stale calibration was 1.47 percentage points (95% paired interval +0.72 to +2.25), below the registered four-point target. The lower confidence bound against supplied positions just crossed the two-point margin."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On a simulated lattice of **7,077,888 cells**, a controller that consulted at most **0.984%** of the detector field retained **72.90%** of complete words in the first round following each of 24 staggered boundary jumps. Holding calibration fixed retained **71.44%**, and supplying the new positions retained **74.48%**. The gain over stale calibration was 1.47 percentage points (95% paired interval +0.72 to +2.25), below the registered four-point target. The lower confidence bound against supplied positions just crossed the two-point margin.

![First-round recovery by jump number for the three paired policies](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What the simulation stores and measures

A periodic 192×192×192 lattice carries one working 32-bit word and one saved 32-bit word per cell. Each bit is represented by a float32 value. A previously trained local controller with an 8×8 read table, eight write-detector coefficients and one bias is shared by all cells and reused at all transitions. The seven movement commands choose the current cell or one of six neighbors. Each saved word should equal the working word at the last legitimate write to that cell. An independent integer index tracks the source word for comparison. At the end of a round, a cell scores one only if the model's readout matches all 32 signs of the expected word. [Recorded update and measurement code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Frozen checkpoint 101](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-full-101.json)

Each world has 16 rounds of 16 transitions. Legitimate writes are offered at 12.5% of sites at ticks 3 and 4, and the confirmation signal is withheld from 1% of those offered sites. At ticks 9 and 10, correlated false writes cover one quarter of the lattice. The wraparound field has eight equal regions. Each region's fault columns share one axis, with axes drawn from a balanced randomized assignment. The detector tests a learned linear function of the local binary input and seven neighboring values. A write needs detector activation on two consecutive ticks plus a witness. During a false pulse, the controller chooses a witness eight cells away along the direction whose data shows the least co-activation within its region. All arms share the same motion, initial words, write offers and faults. [World generator and comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Detector weights and sampling scheme](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

## Matched boundary policies

The stale control keeps the initial true partition. The supplied control gets the current true partition. Both use dense co-activation counts to select witness directions. The sampled policy estimates each partition offset from 64 stratified lines along each axis and estimates witness directions using 1,024 dedicated base points and their three axial neighbors in each of the eight inferred regions. That gives an upper bound of 69,632 detector entries per decision, counting duplicates. This is a bound on what informs the estimator. The archived simulation stages a complete detector field for comparison. [Sampling code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Separately timed observer implementations](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

In the earlier synchronized test, all three offsets jumped together at round nine in eight worlds. Over rounds 9–16, retention was 63.25% stale, 68.91% sampled and 70.46% supplied. The 5.66-point gain describes average post-jump retention. The new benchmark uses eight disjoint worlds, changes one axis at each of three jittered rounds near 5, 9 and 13, and scores the first affected round. Translation sizes are 28, 36, 44, 52, 60 or 68 cells modulo 96. Each world changes all three axes in independently assigned order. [Earlier synchronized-shift experiment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered staggered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

| Staggered endpoint | Stale calibration | Sparse inference | Supplied boundaries |
|---|---:|---:|---:|
| First affected round, all 24 jumps | 71.44% | 72.90% | 74.48% |
| First jump | 79.70% | 78.24% | 79.89% |
| Second jump | 70.73% | 71.65% | 73.31% |
| Third jump | 63.89% | 68.83% | 70.25% |
| All shifted rounds in the latter half | 64.63% | 69.07% | 70.62% |

Paired bootstrap draws resample all eight worlds, keeping the three matched events in each world. At the primary endpoint, the sampled-minus-supplied difference was −1.58 points (95% interval −2.012 to −1.238). The lower bound missed the −2-point tolerance. Legitimate writes were accepted at 99.003% across all arms. The shifted first-round false-write fraction was 7.98% stale, 6.08% sparse and 5.74% supplied. The sparse estimate matched 75% of the archived boundary coordinates exactly at the jump rounds. [Raw tallies and coordinates](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Summary](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent reconstruction](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

Later rounds include state accumulated from earlier writes, so the larger third-jump gap describes full trajectories. The experiment does not isolate how much of that gap arose on the marked round. The two schedules also differed in world samples and evaluation windows. The registered primary result remains unresolved and applies to this single frozen detector and axis-aligned fault family.

## Reproduction

The public repository includes the frozen weights, deterministic generator, source code, exact tallies and execution receipts. The Studio used an arm64 Apple M5 Ultra with 256 GiB unified memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4 in float32 and NumPy 2.5.5. The production run took 599.27 s and peaked at 14.33 GB of MLX allocation. On Apple Silicon, install the listed package versions in Python 3.12, create a fresh output directory and run the command below from the repo root. The verifier reads the released output and works anywhere with NumPy. The owner proposed testing spatial boundaries and recovery at scale. OpenAI Codex registered and implemented the comparison, ran it over SSH, verified the outcomes and assisted with the writing. [Pinned Studio source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Recorded environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt)

```sh
python -m pip install mlx==0.32.4 numpy==2.5.5
STUDIO_JOB_DIR="$(mktemp -d)" python spatial_references/witness_staggered_jumps.py
python [REDACTED_SECRET].py
```