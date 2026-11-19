---
title: "Does symmetric retention teach two spatial memory banks different jobs?"
paper_id: "2026-348"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T22:23:25Z"
abstract: "Giving two interchangeable banks the same strong preference for retaining their contents yielded 1,071 of 18,544 held-out 32-bit words exactly correct. Without that preference, the same architecture recovered 1,105. A controller initialized with different working and snapshot roles recovered all 18,544, as did a smaller controller whose wiring designated those roles. These are paired results from a single training seed. The preregistered validation screen stopped replication of symmetric retention. The role-biased model's perfect transfer to larger cubes supplies a positive control for what these 468 weights can represent."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Giving two interchangeable banks the same strong preference for retaining their contents yielded **1,071 of 18,544** held-out 32-bit words exactly correct. Without that preference, the same architecture recovered **1,105**. A controller initialized with different working and snapshot roles recovered **all 18,544**, as did a smaller controller whose wiring designated those roles. These are paired results from a single training seed. The preregistered validation screen stopped replication of symmetric retention. The role-biased model's perfect transfer to larger cubes supplies a positive control for what these 468 weights can represent.

![Exact recovery on the common validation and test panels](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What was missing from the earlier comparison?

A model might fail to learn a useful memory address because each update mixes too many inputs before a stable signal can travel through time. Preserving existing contents in both banks gives either bank an opportunity to acquire a distinct function. This change leaves the model symmetry intact at the level of its initialization distribution. The previous three-seed study compared interchangeable and assigned roles. Its role-biased calibration had only been scored on the smaller training-shaped task. Here we bring that checkpoint and the other controls to new, common validation and test panels. Memory architectures with learned addressing supply a broader research context. [Earlier spatial study](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Neural Turing Machines](https://arxiv.org/abs/1410.5401) · [Prospective protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Every cell in a periodic cube has two 32-value banks. A command moves, holds or restores a word. A write occurs when two sensors, one local and one adjacent, are simultaneously active. The network receives final word targets. Its snapshots and write events are hidden during training. The flexible controller has two distributions over fourteen read ports for each destination bank and command. A learned sensor gate interpolates between those distributions. Starting with the previously used random logits, we added log(117) to the entry for the destination bank's own center, on both branches for every command. That corresponds to 90% self-weight before adding random noise. The model can subsequently learn any permitted weights. The neutral and role-biased models have the same 468 trainable weights. The role-biased start favors particular read ports, write branches and output bank together. The assigned controller has 73 weights. [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## Training and results

We fit the symmetric condition with seed 101, 500 Adam updates, batch size twelve, learning rate 0.08 and final-output bitwise logistic loss on 4×4×4 cubes over eight steps. We reused final seed-101 control weights trained on the same stream and budget. On a fresh 64-cube validation panel the symmetric start recovered 4.25% and neutral recovered 4.17%. Their 0.08-point difference fell short of the five-point replication criterion. We therefore retained a one-seed comparison on the new 128-cube test panel. Those cubes were 6×6×6 with sixteen steps. The primary denominator counts cells whose final source changes when writes are suppressed. Each successful word requires all 32 bits. [Gate and validation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Counts, training times and MLX memory](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

| Initialization or architecture | Learned weights | Validation | Held-out exact words |
|---|---:|---:|---:|
| Neutral | 468 | 4.17% | 1,105 / 18,544 (5.96%) |
| Symmetric retention | 468 | 4.25% | 1,071 / 18,544 (5.78%) |
| Initial roles supplied, all weights trainable | 468 | 100% | 18,544 / 18,544 |
| Roles assigned by the architecture | 73 | 100% | 18,544 / 18,544 |

The held-out symmetric-minus-neutral difference was −0.18 percentage points. A 5,000-draw paired bootstrap over 64 pairs of cubes gave a 95% interval of [−0.38, +0.0054] points, conditional on this fit. Different training seeds introduce uncertainty beyond this interval. The symmetric fit took 1.24 seconds within the recorded training section on the M5 Ultra. Timing includes overhead specific to this small task and implementation.

## Which bank is needed to recover a saved word?

An independent source trace identified 6,711 final cells that depended on a distinct midpoint snapshot. We chose each model's candidate snapshot bank on validation, then exchanged that bank between pairs of test cubes, leaving future inputs unchanged. In both successful controllers, exchanging the selected bank erased all 6,711 words. Exchanging the other bank preserved all 6,711. The neutral and symmetric models both had only 121 intact successes on this subset before intervention. Exchanging their selected bank left three and eight successes respectively. Exchanging the other left 89 and 94. This test identifies a storage dependency under the synthetic rule. It does not isolate which component of the role-biased initialization makes learning possible.

Reloading weights on the Studio reproduced every released count. A separate NumPy implementation agreed on denominators and primary whole-word counts for all four conditions on the first eight held-out cubes. A few bit comparisons and two auxiliary exchanged-bank word counts differed across arithmetic implementations. [Audit by arm and endpoint](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Decision and reproduction

Keep the 73-weight controller as the reference for this task. The extra trainable parameters and symmetric retention preference bought no measured improvement under the tested budget. The positive role-initialized control makes a more targeted question possible in future work, such as transferring a learned write decision when a fresh host cannot learn that decision at equal cost. Further sweeps over the retention strength would answer a narrower question.

Run the following in the repository root in the Apple Silicon MLX environment used by the preceding study. The experiment script reuses archived controls and previously completed fits. To fit symmetric retention anew, use a fresh checkout and move the saved symmetric JSON out of the results directory before running. The report and chart need NumPy and Matplotlib.

```sh
python persistence/experiment_persistence.py
python persistence/verify.py
python persistence/report.py
python persistence/figure.py
```