---
below_floor: true
quality_floor: 7.0
title: "Inferring shifted fault boundaries rescued memory on an 884,736-cell grid"
paper_id: "2026-499"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T10:29:34Z"
abstract: "The router inferred 89.58% of shifted boundary coordinates exactly from its first detector pulse. After the shifted faults, it recovered 71.78% of stored words, versus 65.24% with fixed regions and 72.55% when the true boundaries were supplied. Every arm accepted 99.00% of legitimate writes. The experiment supplies the partition family and tests whether the router can recover its location from activity."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The router inferred **89.58%** of shifted boundary coordinates exactly from its first detector pulse. After the shifted faults, it recovered **71.78%** of stored words, versus **65.24%** with fixed regions and **72.55%** when the true boundaries were supplied. Every arm accepted **99.00%** of legitimate writes. The experiment supplies the partition family and tests whether the router can recover its location from activity.

![Post-fault memory recovery with fixed, inferred and supplied boundaries](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-regions.png)

## Shift the partition while keeping the task paired

A 96×96×96 grid contains 32-bit data words. The trained primary detector and seven-command transport are frozen at three published checkpoints. Eight 48³ regions have independently generated column faults occupying 25% of the volume. Different regions have different column orientations. Each world is evaluated with the original partition and with the exact same masks translated along three axes. Each hidden offset is a multiple of four from four through 44. The entire grid is periodic. All arms share transport, initial words, true writes, and the one-percent dropout of legitimate witness signals. [Registered comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Earlier fixed regions](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

For each axis, let `D(i)` be the fraction of unequal binary detector readings across the plane between slices `i-1` and `i` in the previous tick's sensor field. Choose the offset `s` maximizing `D(s) + D(s+48)` over the 48 possible offsets. Within each resulting region choose the candidate axis with lowest same-field co-activation over a separation of eight cells. The fixed and supplied-boundary controls use the same regional rule with different boundary positions. A cell can consult one witness eight cells away and wrapping inside its selected region. In the false two-pulse case, the router uses the first pulse to estimate the boundaries before the second pulse can cause a write. It has no fault labels or intended words. [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

| Boundary rule | Retention, original layout | Retention, shifted layout | False writes, shifted layout |
|---|---:|---:|---:|
| Fixed regions | 72.56% | 65.24% | 7.69% |
| Infer boundaries from the detector | 71.78% | 71.78% | 5.50% |
| Supply the true boundaries | 72.56% | 72.55% | 5.27% |

The inferred policy gained **6.54 percentage points** over fixed routing under shifted faults, paired 95% interval **4.95 to 8.27**. Under the original layout it lost **0.77 points**, interval **−1.15 to −0.43**. It met the registered joint decision, including the legitimate-write floor. Boundary accuracy weights each coordinate, round, world, and frozen checkpoint equally. This tests a given family of planar, periodic two-way splits under synthetic column faults. The split shape, candidate direction family and write protocol are supplied. The model infers translations of the split from the previous activity field. It does not learn arbitrary boundaries or partition from end-to-end storage loss. [World counts, routes and intervals](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Related local learned dynamics](https://distill.pub/2020/growing-ca/)

Run `uv run --with numpy python spatial_references/inferred_regions_study/verify.py` to check receipt and checkpoint hashes, translated coordinates, exact word outcomes, and world-paired bootstrap intervals with the checkpoints grouped within each draw. The run took 146.07 seconds and reached 1.79 GB peak MLX allocation. The Apple M5 Ultra had 80 GPU cores, 256 GiB unified memory and Metal 4. The run used float32 MLX 0.32.4, NumPy 2.5.5, Python 3.12.16 and macOS 27.2. The owner proposed research on walls and fixed references. OpenAI Codex designed and ran the paired comparison, audited results and assisted with writing. [Pinned execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)