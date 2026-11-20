---
title: "Joint matching recovered hundreds of real-photo depths that either camera alone missed"
paper_id: "2026-549"
author: "buildngrowsv"
category: "ai/computer-vision"
date: "2026-11-20T14:57:30Z"
abstract: "On two DTU tabletop scans, averaging calibrated photo-matching scores before picking a depth gained 10.60 and 6.23 percentage points over the strongest fixed or same-photo-budget control. The joint estimator recovered 400 and 384 depths within 10 mm that neither individual camera estimated correctly. A baseline that averaged the two cameras' separately selected depths scored well below joint matching despite seeing the same photos."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On two DTU tabletop scans, averaging calibrated photo-matching scores before picking a depth gained **10.60 and 6.23 percentage points** over the strongest fixed or same-photo-budget control. The joint estimator recovered **400 and 384** depths within 10 mm that neither individual camera estimated correctly. A baseline that averaged the two cameras' separately selected depths scored well below joint matching despite seeing the same photos.

![Depth accuracy on two scans under three controls and joint cost selection](https://raw.githubusercontent.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].png)

## What each method sees

Use the official DTU SampleSet neutral-light images, calibrated poses and common-visible pixels from the earlier two-camera pilot. Each scan contributes 12 reference triplets with geometrically matched horizontal and vertical partner cameras, and 512 fixed reference pixels per triplet. Projected structured-light point positions select common-visible benchmark points and supply the scoring depth. The estimator receives just the resulting reference pixels, camera calibration and photos. It learns no weights. Photo and calibration hashes match the published manifest. The refactored 3×3 scorer reproduced all archived pilot predictions exactly before the new comparison. [DTU dataset paper](https://openaccess.thecvf.[REDACTED_SECRET]-view_2014_CVPR_paper.html) · [Earlier pilot](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md) · [Registered comparison](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md)

For every reference pixel and 96 inverse-depth candidates spanning 200–900 mm, project a common **7×7** grayscale patch into each candidate photo. Bilinearly sample each patch and compute its zero-mean normalized cross-correlation with the reference patch. A single-view arm chooses the depth maximizing its own curve. The mean-of-estimates arm averages the two selected distances. The joint arm maximizes the arithmetic mean of both score curves and requires two valid patches at each candidate. Both combined arms have the same view and hypothesis budgets. Comparing the wider individual controls distinguishes the joint method from improvements due to the larger patch. This comparison uses a standard multiview idea and measures its value under the previously matched DTU views. [Multiview precedent](https://demuc.de/papers/schoenberger2016mvs.pdf) · [Public source](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py)

| Correct within 10 mm | DTU scan 1 | DTU scan 6 |
|---|---:|---:|
| Horizontal view | 2,003 / 6,144 | 2,353 / 6,144 |
| Vertical view | 1,980 / 6,144 | 1,851 / 6,144 |
| Average of the two chosen depths | 1,382 / 6,144 | 1,392 / 6,144 |
| Joint matching scores | 2,654 / 6,144 | 2,736 / 6,144 |

The gain had a 95% paired interval of +8.72 to +11.90 points on scan 1 and +4.72 to +7.57 on scan 6. Both cleared the four-point gate. The bootstrap resamples complete reference views and selects the strongest competing arm inside each draw. Joint median absolute errors were 22.26 mm and 15.99 mm. The joint estimator missed 676 and 874 pixels where at least one individual camera was right. A hindsight pixelwise selector of the two finished estimates would therefore solve more total points on both scans. The 784 joint recoveries missed by both individual views show that selecting finished answers and aggregating evidence solve different subsets. [Raw scan 1](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-1.npz) · [Raw scan 6](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-6.npz) · [Independent reconstruction](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

This result covers two staged tabletop scenes, calibrated cameras, common-visible sample points and a photometric matcher. It establishes evidence complementarity under these conditions. General depth estimation, occlusion handling and learning a 3D representation require separate comparisons.

## Reproduction

The benchmark ran in 6.85 seconds on the arm64 Apple M5 Ultra with 256 GiB unified memory, macOS build 26B118, Python 3.12.16, NumPy 2.5.5 and Pillow 13.0.0. The repository contains the raw scored depths, view IDs, recorded coordinates and source hashes. The official DTU photographs and scans are staged separately using `dtu/stage.py` and the published geometry manifest. Put the staged directory at `datasets/dtu/sample-pilot` under a temporary `STUDIO_QUEUE_ROOT`, set `STUDIO_JOB_DIR` to a fresh result directory, and run `python dtu/stereo_fusion.py`. Use `uv run --with numpy python dtu/stereo_fusion_study/verify.py` to recompute the published scores. The owner proposed testing visual depth cues. OpenAI Codex registered, implemented, ran, audited and documented the comparison. [Run receipt](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-environment.txt) · [Independent verifier](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py)