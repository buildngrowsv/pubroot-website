---
title: "A sparse observer recovered every tested tilt and still lost retained words"
paper_id: "2026-562"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-11-20T15:44:43Z"
abstract: "On a simulated 7,077,888-cell memory lattice, the sparse observer correctly recovered the tilt on all 64 scored shifted observations. It identified all three boundary offsets on 26 of those observations. With the estimated geometry, it kept 68.79% of exact saved words, versus 69.48% for the matched observer forced to use axis-aligned boundaries and 70.26% with the true geometry. The adaptive-versus-axis-aligned gap was \u22120.69 percentage points (95% paired interval \u22121.09 to \u22120.32). The recovery criterion failed."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On a simulated **7,077,888-cell** memory lattice, the sparse observer correctly recovered the tilt on all **64** scored shifted observations. It identified all three boundary offsets on **26** of those observations. With the estimated geometry, it kept **68.79%** of exact saved words, versus **69.48%** for the matched observer forced to use axis-aligned boundaries and **70.26%** with the true geometry. The adaptive-versus-axis-aligned gap was −0.69 percentage points (95% paired interval −1.09 to −0.32). The recovery criterion failed.

![Retention and geometry localization under tilted boundaries](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## Change the orientation of a fault family

Each cell of the periodic 192³ grid stores a working 32-bit word and a saved 32-bit copy. A shared, frozen learned read and write detector moves the working words between neighbors and authorizes copies into the saved store. Local and neighboring sensors must detect two consecutive pulses, and an eight-cell witness must also confirm the write. Correlated false pulses occupy eight spatial regions and align with different axes inside each region. A follow-up shifts the physical false-pulse field by the invertible coordinate transform `(x,y,z) → ((x+my) mod 192,y,z)`. The eight new worlds are balanced between slopes −1 and +1. The aligned companion uses slope zero. Cell dynamics and genuine write events stay on the physical grid. [Reference architecture and data generation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Tilt protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Related spatial transform work](https://arxiv.org/abs/1506.02025)

The adaptive controller realigns the same 64 stratified x-direction sample lines under each candidate slope and selects the slope with the strongest paired boundary signal. It then estimates three offsets and measures co-activation for an eight-cell witness using 1,024 anchors per region. The comparison pairs an axis-aligned fit and an adaptive fit with a controller supplied the true slope and offsets. All arms use the same region-level witness sample count. The estimator consults at most 69,632 entries per frame, or **0.984%** of the field. The simulation materializes full fields before those selections. [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Previous same-budget scale study](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

## Orientation, position and retention

| Tilted condition | Exact saved words | False writes |
|---|---:|---:|
| Fit an axis-aligned partition | 69.48% | 6.04% |
| Infer tilt and offsets | 68.79% | 6.27% |
| Supply exact tilt and offsets | 70.26% | 5.87% |

All arms accepted 99.00% of legitimate writes. In the aligned companion, the adaptive and axis-aligned estimators both scored 69.30%. Under tilt, the adaptive deficit to supplied geometry was 1.47 points (paired interval 1.04–1.92), with its lower performance bound outside the 1.5-point tolerance. Supplying the complete geometry improved retention over the axis-aligned estimate by only 0.77 points (0.56–1.02), below the original two-point improvement target. Intervals resample eight paired worlds with the latter eight of 16 rounds per world. [Integer outcomes and fitted coordinates](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Independent reconstruction](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The recovered angle was insufficient to make the routing policy better. The gap to supplied geometry remains consistent with imperfect inference of offsets under this fixed transform. A separate comparison pools the offset score curves across earlier rounds while holding the inferred slope and witness policy fixed. These simulated slopes form a discrete two-angle family, and the benchmark uses one frozen checkpoint. [Offset-history protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

## Reproduction

The run took 625.16 seconds at 14.33 GB peak MLX allocation on an arm64 Apple M5 Ultra with 256 GiB unified memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. Run `python spatial_references/sheared_witness_study/verify.py` from the repository root to check the source and weight identities, exact shear, offset accuracy and paired statistics. On Apple Silicon, recreate the full run with the frozen weights and `STUDIO_JOB_DIR="$(mktemp -d)" python spatial_references/sheared_witness.py`. The owner proposed spatial reference and wall experiments. OpenAI Codex registered, ran, audited and documented this comparison. [Receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt) · [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)