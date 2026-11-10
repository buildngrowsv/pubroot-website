---
below_floor: true
quality_floor: 7.0
title: "Replaying one CPython batch in eight improved both retention and external Python prediction"
paper_id: "2026-387"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T02:27:55Z"
abstract: "Replacing every eighth adaptation batch with original CPython code removed 87.27% of the forgetting seen under ordinary adaptation in a 26.83M-parameter byte model. It also improved loss on all six external Python projects, by a mean 0.05010 bits per byte (paired 95% interval 0.04656\u20130.05471). Both models began from the same checkpoint and took 8,192 updates. This one-training-order result measures a change in the data mixture. Whether the forward-copy architecture contributes to the effect remains open."
score: 6.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Replacing every eighth adaptation batch with original CPython code removed 87.27% of the forgetting seen under ordinary adaptation in a 26.83M-parameter byte model. It also improved loss on all six external Python projects, by a mean 0.05010 bits per byte (paired 95% interval 0.04656–0.05471). Both models began from the same checkpoint and took 8,192 updates. This one-training-order result measures a change in the data mixture. Whether the forward-copy architecture contributes to the effect remains open.

![Performance on both distributions before adaptation and with the two training mixtures](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## One change to the adaptation stream

The sealed model has 512 coordinates at its entrance and exit. Seven intervening blocks process 448 coordinates while 64 early values travel unchanged to the final block. We used its checkpoint after 16,384 updates on package-disjoint CPython, then reset the optimizer for both adaptation runs. Ordinary adaptation used NumPy, SciPy and Matplotlib. Rehearsal replaced exactly 1,024 of the same 8,192 step IDs with batches from the original CPython training split. The other 7,168 batches match the ordinary arm by file and offset selection. Both arms received 67,108,864 context bytes including repeated exposure. The external test set comprises 512 fixed 512-byte windows from each of pandas, NetworkX, xarray, seaborn, mpmath and joblib. The original-domain test set comprises 2,048 unchanged windows from 49 CPython package groups. Lower loss is better. [Protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Batch scheduler](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Corpus and file manifests](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

| Training state | CPython bits per byte | External bits per byte |
|---|---:|---:|
| Before adaptation | 1.01799 | 1.59122 |
| Ordinary adaptation | 1.22997 | 1.39958 |
| Every eighth batch from CPython | 1.04498 | 1.34948 |

Relative to ordinary adaptation, rehearsal improved CPython loss by 0.18499 and reduced the remaining pretraining-to-adaptation penalty to 0.02699. Both preregistered margins passed. CPython loss was 0.07900 below the threshold for removing half the ordinary penalty (paired 95% interval −0.08614 to −0.07196). External loss was 0.09801 below the threshold for retaining 75% of the ordinary gain (−0.10207 to −0.09367). The direct external improvement over ordinary adaptation ranged from 0.02903 to 0.09177 across projects. The comparisons resample packages for CPython and files within the six fixed projects for the external panel. [Window scores, decision and run receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## What the control establishes

Ibrahim and colleagues reported benefits from old-data replay during continued language-model pretraining. Our contribution is a fixed-budget test on a compact Python model in which both old-domain and external-project losses improved. A common Python distribution, changes in exposure to the adaptation projects, or reduced overfitting could each contribute. These fits share an initialization and task order. Neither dataset-wide independence of code fragments nor training-seed uncertainty follows from the clustered intervals. The same-size late-copy model reached 1.39516 external bits per byte under ordinary adaptation. Its replay run is registered to test whether both gains survive removal of the early copy. [Ibrahim et al., March 2024](https://arxiv.org/abs/2403.08763) · [Equal-size ordinary-adaptation data](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-working) · [Architecture precedent and comparisons](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The run used an Apple M5 Ultra with MLX 0.32.4. Run the NumPy verification script from this directory to reproduce the paired endpoints and intervals. The owner proposed the continuing research program. OpenAI Codex implemented and operated the comparison and assisted with analysis and writing. [Recorded environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Audit results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)