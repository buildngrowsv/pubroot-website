---
title: "Two 238M Python models adapted to new projects with similar retention"
paper_id: "2026-425"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:09:30Z"
abstract: "After learning from NumPy, SciPy and Matplotlib, two 238M byte predictors improved on all six held-out third-party projects. The model carrying 192 sealed early values improved from 1.70943 to 1.30505 external bits per byte. Its equal-size late-copy control improved from 1.71825 to 1.30641. Original CPython scores changed by +0.01327 and +0.01132 bits per byte, respectively. The difference between these changes was +0.00195 (95% package-paired interval \u22120.00228 to +0.00710), which missed the prespecified retention advantage for the early copy."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

After learning from NumPy, SciPy and Matplotlib, two 238M byte predictors improved on all six held-out third-party projects. The model carrying 192 sealed early values improved from **1.70943 to 1.30505** external bits per byte. Its equal-size late-copy control improved from **1.71825 to 1.30641**. Original CPython scores changed by **+0.01327** and **+0.01132** bits per byte, respectively. The difference between these changes was +0.00195 (95% package-paired interval −0.00228 to +0.00710), which missed the prespecified retention advantage for the early copy.

![Original and external Python prediction before and after updating the two models](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What both models received

The two ten-block predictors store 238,269,312 weights each and use 1,344 coordinates in their seven middle blocks. Both enter the last block at width 1,536. One restores 192 values copied from block 2 and preserved across the narrow middle. The other duplicates its last 192 working coordinates from block 9 to occupy the same exit slots. Each starts from a distinct trained checkpoint at 16,384 steps on package-disjoint CPython. We reset AdamW, warmed up for 128 steps to 0.0004 / 3, and used weight decay 0.03 and a gradient-norm cap of one. Both fit exactly the same 2,048 batches of 8,192 target bytes, with no original CPython replay. The sampling stream matches the first 2,048 steps of the original ecosystem study. [Architecture and checkpoints](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Adaptation code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Before and after training, score 512 fixed windows from each of pandas, NetworkX, xarray, seaborn, mpmath and joblib. Give each project equal weight. Pin archives and exclude exact file duplicates with original data and other projects. On CPython, reuse the same 2,048 windows from 49 package groups. Calculate paired intervals over CPython packages and over files within each of the six fixed external projects. Lower bits per byte means the model assigned more probability to the actual next byte. [Pinned project archives](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Per-window scores, file manifest and run receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-sealed-retention)

| Predictor | CPython before | CPython after | External before | External after |
|---|---:|---:|---:|---:|
| Early sealed copy | 1.07455 | 1.08781 | 1.70943 | 1.30505 |
| Same-size late copy | 1.07655 | 1.08786 | 1.71825 | 1.30641 |

Both post-adaptation external results were close. The sealed-minus-late mean was −0.00136 bits per byte (file-paired interval −0.00377 to +0.00075), passing the +0.02 external margin. The registered retention claim additionally required at least 0.03 bits per byte less CPython deterioration in the sealed model and a negative upper confidence bound. The point estimate was slightly in the other direction, and the interval crossed zero. The CPython changes for each arm individually also had intervals that crossed zero. Under this budget, further training fit the new domains while the measured original-domain losses stayed close to their starting values. [Independent score and window reconstruction](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Recomputed effects](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The earlier 26.83M models saw longer adaptation and a different learning rate. Their original-domain loss increased more substantially. This wide run estimates the two architectures’ difference at one matched budget and one training draw. It leaves open whether a copy matters under stronger forgetting. The owner proposed the fixed reference and the scale revisits. OpenAI Codex implemented and ran the matched fits on the owner’s Apple M5 Ultra, verified the evidence and assisted with writing. [Earlier compact comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Recorded runtime](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)