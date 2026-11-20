---
title: "Regional routing preserved more memory when faults disagreed across a 3D grid"
paper_id: "2026-492"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:53:42Z"
abstract: "On a 96\u00b3 grid with 884,736 cells, eight independent confirmation regions recovered 72.32% of stored words when faults pointed in different directions. One global confirmation direction recovered 59.26%. The regional rule used the same inputs, statistic, candidate wires and one-witness limit. All arms accepted 99.00% of legitimate writes. This isolates the benefit of choosing at the scale where the fault direction varied."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On a **96³ grid with 884,736 cells**, eight independent confirmation regions recovered **72.32%** of stored words when faults pointed in different directions. One global confirmation direction recovered **59.26%**. The regional rule used the same inputs, statistic, candidate wires and one-witness limit. All arms accepted **99.00%** of legitimate writes. This isolates the benefit of choosing at the scale where the fault direction varied.

![Exact post-fault retention with shared and regional confirmation directions](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-witness.png)

## Same witness budget, different place to decide

The benchmark uses 32-bit words, 256 transitions, eight independent scene pairs and three frozen local controllers. Divide the 96³ lattice into eight 48³ regions. Each region has three possible witness directions, all eight cells away and wrapping within the region. Movement remains the original learned seven-command rule. A write requires two successive primary detector activations and a confirming reading from one candidate witness. One percent of legitimate witness signals are independently withheld, with identical withholding across arms. [Registered comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Earlier global adaptation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

A spurious write appears as two positive pulses in a set of 4×4 columns. Each region has exactly 25% fault coverage. In the homogeneous world, all fault columns run along one shared axis. In its paired heterogeneous world, the eight regions use three, three and two copies of the three axes in shuffled order. The paired worlds share underlying draws, movement, and intended writes. Each adaptive router uses a running average of the primary detector's spatial co-activation in each candidate direction, with the same decay of 0.92. The global router takes the lowest averaged direction across all regions. The regional router takes a separate minimum in each region using only that region's detector field. Both routers decide from observations through the previous tick. A comparator receives the hidden axis and chooses a predetermined perpendicular direction. [Source addresses and checkpoint digests](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

| Confirmation method | Homogeneous fault directions | Heterogeneous fault directions | False writes, heterogeneous |
|---|---:|---:|---:|
| One global direction | 70.51% | 59.26% | 10.91% |
| A direction per region | 72.33% | 72.32% | 5.32% |
| Fixed perpendicular given orientation | 69.55% | 69.40% | 6.06% |

The regional gain was **13.06 percentage points** under heterogeneous faults, paired 95% interval **12.72 to 13.39**, and **1.82 points** under homogeneous faults, interval **1.50 to 2.11**. The global router's chosen direction coincided with the fault axis in 25% of regions at scored heterogeneous write decisions. The regional router had zero such choices. It also benefited from selecting between the two usable perpendicular directions using observed co-activation. This experiment uses synthetic column faults and fixed boundaries. It measures the cost of pooling evidence across disagreements in this topology. The regional policy is a supplied co-activation rule with frozen learned detectors. It does not learn the partition from end-to-end memory loss. Learned cellular dynamics and conditional selection of computation provide related context. [Growing Neural Cellular Automata](https://distill.pub/2020/growing-ca/) · [Switch Transformers](https://jmlr.org/papers/v23/21-0998.html)

Run `uv run --with numpy python spatial_references/regional_witness_study/verify.py` to check the receipts, checkpoints, routing choices, word counts and paired bootstrap. The full comparison took 152.81 seconds and reached 1.79 GB peak MLX allocation. It ran float32 state updates on an Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory, using macOS 27.2, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The owner proposed exploring much larger structured references. OpenAI Codex designed, ran and independently audited the benchmark and assisted with writing. [Execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)