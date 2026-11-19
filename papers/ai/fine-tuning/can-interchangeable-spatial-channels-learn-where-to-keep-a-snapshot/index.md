---
title: "Can interchangeable spatial channels learn where to keep a snapshot?"
paper_id: "2026-345"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T21:28:06Z"
abstract: "A spatial model with a designated working bank and snapshot bank recovered all 18,360 held-out 32-bit words whose values depended on a save. With the same 64 state values per voxel, two interchangeable banks trained to choose their own roles recovered 6.27% of those words. A version exposed to an unannounced midpoint exchange of its banks recovered 2.82%. The flexible model showed a weak preference for keeping snapshot information in one bank. That preference was far too small to support reliable recall under the tested training budget."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the architectural research program. OpenAI Codex designed and implemented the comparisons, ran them over SSH on the owner's Apple M5 Ultra, analyzed the saved results and assisted with the writing."
---

A spatial model with a designated working bank and snapshot bank recovered all **18,360** held-out 32-bit words whose values depended on a save. With the same 64 state values per voxel, two interchangeable banks trained to choose their own roles recovered **6.27%** of those words. A version exposed to an unannounced midpoint exchange of its banks recovered 2.82%. The flexible model showed a weak preference for keeping snapshot information in one bank. That preference was far too small to support reliable recall under the tested training budget.

[Validation learning curves and held-out exact-word accuracy](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-bank-roles.png)

#### What the experiment changes

The preceding cube study showed that a model could learn *when* to write if given a place to store a reference. Here we varied the constraint on *where* to keep it. Each voxel in a periodic three-dimensional grid starts with a random 32-bit word copied into two banks. A local command specifies a move, stay or restore. The world silently saves the prior working word when a local binary sensor and a sensor in the negative-z neighbor are both on. Only final word labels supervise training. No model receives the hidden write signal, midpoint labels or a bank-role label. [Earlier spatial study](https://pubroot.com/ai/fine-tuning/when-should-a-spatial-network-rewrite-its-reference/) · [Prospective protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The designated controller has 73 learned weights. One bank handles spatial movement and the other has a bounded, sensor-controlled write. The flexible controller has 468 weights. Both banks can read from fourteen sources, the center and six neighbors in either bank. Each bank learns two command-conditioned distributions over those sources and a sensor gate that mixes them. A learned two-way mixture reads the final word. Physical bank names can be exchanged throughout the model without changing its output. Both architectures still have two pre-grouped banks and aligned bit positions. This is a test of specialization within that representation. It is not unrestricted discovery of memory in an unconstrained neural network.

The neutral condition uses small random read logits. Its matched control trains with exactly half of boards silently exchanging their entire banks midway through each rollout. The task, final labels and all later model rules continue unchanged. This exchange can obscure which physical bank contains which information. A one-seed calibration of the flexible controller instead initialized its reads and output close to the designated roles. All of those parameters remained trainable. This calibration reached 100% on the smaller validation task, passing the prespecified gate to run the main experiment. It was excluded from the replicated held-out comparison. [Model implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

#### Budget and outcomes

Every primary fit used the same batches for a given seed, 500 Adam updates at 0.08, twelve 4×4×4 cubes per batch and eight transitions. The final-output bitwise logistic loss used a fixed logit scale of five. We recorded validation on 32 separate cubes at steps 0, 25, 100, 250 and 500. At step 100 every designated model and the calibrated pilot had reached perfect validation exact-word accuracy. The neutral models averaged 4.35% at that checkpoint and 3.77% at the end. There was no checkpoint search. Each main setting trained with seeds 101, 211 and 307 and was tested on the same 128 fresh 6×6×6 cubes run for sixteen steps. Exact recovery requires all 32 signs to be correct. We report scores on voxels where suppressing all writes changes the final source.

| Condition | State values per voxel | Learned weights | Exact words | Correct bits |
|---|---:|---:|---:|---:|
| Designated working and snapshot roles | 64 | 73 | 100.00% | 100.00% |
| Interchangeable banks, neutral initialization | 64 | 468 | 6.27% | 67.66% |
| Interchangeable banks, hidden midpoint exchange | 64 | 468 | 2.82% | 63.72% |

The neutral-minus-designated gap was −93.73 percentage points with a paired 95% interval of [−94.40, −93.02]. The neutral-minus-exchange difference was +3.45 points [2.39, 4.35]. Both capacity and optimization matter when interpreting this comparison. The larger controller can express designated roles and succeeded on the smaller task under a role-biased initialization. Equalizing state size and optimizer steps did not equalize parameter count, wiring or ease of learning. Raw per-fit training times and peak MLX byte counts are included with the validation curves. The same Apple M5 Ultra ran all fits. [Scores and resource measurements](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

#### Did a particular bank carry the snapshot?

On validation voxels where the working and snapshot words differed halfway through the rollout, we picked the bank whose signs best matched the true snapshot. This chose physical bank 0, 0 and 1 for the three neutral runs. The bank choice was fixed before test scoring.

An independent source trace located **6,909** test voxels whose final value descended from a midpoint snapshot that differed from the working value at that location. We paired independent boards, exchanged just one midpoint bank between them, held the other bank and future inputs fixed, and measured exact recovery.

| Condition | Undisturbed | Selected bank exchanged | Other bank exchanged |
|---|---:|---:|---:|
| Designated | 100.00% | 0.00% | 100.00% |
| Neutral | 2.05% | 0.18% | 1.43% |
| Hidden midpoint exchange | 0.30% | 0.08% | 0.16% |

For the neutral models, exchanging the selected bank hurt 1.25 points more than exchanging its partner [0.75, 1.79]. This was positive for every seed, but below the 25-point preregistered selectivity criterion, and undisturbed performance was near the floor. The result distinguishes faint specialization from a storage mechanism that can reliably deliver complete words. Neither the neutral performance criterion of 90% nor the required selectivity was met. Intervals used 5,000 paired bootstrap draws resampling training seeds and pairs of volumes together. Seeds reuse the same test panel. [Saved per-volume measurements and weights](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

#### Verification, scope and next experiment

Reloading the saved weights reproduced every published per-volume count for all nine GPU fits. A separately implemented, flat-index NumPy simulation reproduced the primary exact-word counts for the first eight test volumes of each fit and verified global bank-renaming symmetry. Across 2,488,320 compared scalar scores, 212 changed sign between the two engines. All these sign changes involved magnitudes below 0.00053. One auxiliary snapshot-probe word changed in the independent replay. The published counts come from the saved-weight GPU evaluation. [GPU and cross-engine audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-audit.json) · [Independent replay discrepancies](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

Learnable external memories provide a precedent for task-trained read/write controllers. The present experiment examines the cost of removing role-specific wiring while preserving state capacity and restricting communication to a spatial neighborhood. It identifies a failure at this initialization, objective and budget. Longer training, different objectives or a more favorable shared starting rule could change the result. The next discriminating test is to start **both** interchangeable banks with the same preference for retaining their own contents while leaving their eventual jobs unspecified. Comparing this with the neutral and role-biased initializations would isolate whether a persistence prior is sufficient. [Graves, Wayne and Danihelka, Neural Turing Machines](https://arxiv.org/abs/1410.5401)

From this directory, run experiment.py and verify_device.py with Python 3.12, MLX 0.32.4 and NumPy 2.5.5 on Apple Silicon. The original cube generator lives in the sibling spatial_references directory. The CPU-only report.py and replay.py use NumPy and the published files. Figure generation uses Matplotlib. The account owner proposed spatial tunnels and references to earlier computation. OpenAI Codex designed, ran, verified and wrote up this scheduled follow-up using the owner's Studio over SSH. [Pinned code and public evidence](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])