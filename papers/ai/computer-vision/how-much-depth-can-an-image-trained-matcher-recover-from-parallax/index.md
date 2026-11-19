---
title: "How much depth can an image-trained matcher recover from parallax?"
paper_id: "2026-347"
author: "buildngrowsv"
category: "ai/computer-vision"
date: "2026-11-19T22:21:35Z"
abstract: "Four synthetic worlds have exactly the same first image, yet each foreground pixel lies at a different depth in every world. A single-view prediction can therefore be right exactly 25% of the time across a quartet. With a second view and four calibrated candidate shifts, a 641-parameter matcher trained using image agreement recovered 92.51% of depths on held-out shapes and camera displacements. A fixed patch-difference rule recovered 92.99%. On fresh worlds, withdrawing the four-shift shortlist from the frozen matcher reduced accuracy by 6.27 percentage points. The experiment separates information supplied by camera motion, image-based training and the search geometry."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Four synthetic worlds have exactly the same first image, yet each foreground pixel lies at a different depth in every world. A single-view prediction can therefore be right exactly 25% of the time across a quartet. With a second view and four calibrated candidate shifts, a 641-parameter matcher trained using image agreement recovered **92.51%** of depths on held-out shapes and camera displacements. A fixed patch-difference rule recovered **92.99%**. On fresh worlds, withdrawing the four-shift shortlist from the frozen matcher reduced accuracy by **6.27 percentage points**. The experiment separates information supplied by camera motion, image-based training and the search geometry.

![Two views, inferred and true depth, and held-out control scores](https://raw.githubusercontent.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].png)

## A first image that cannot give away the answer

The generator places four flat surfaces on a 56×30 reference canvas, with flat, striped, noisy and wavy textures randomly assigned independently of depth. Each occupied pixel is a 3D ray sample. Translating the camera horizontally by b units projects a sample from column x to x − b·d, where d is the focal length divided by depth and takes values one through four. The nearer surface wins when two samples project to the same pixel. On evaluation we cycle the four depth assignments at fixed appearance to produce a quartet of worlds. This yields an exact 25% bound for any predictor that must use the same first image alone, regardless of its capacity. It holds for the pooled worlds of this experiment. An interactive figure uses the first layout of the shifted test panel. Download and open it locally to change the depth assignment or move the camera. [Interactive figure](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].html) · [Scene generator](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py)

Image reconstruction losses and stereo correspondence are established tools for recovering depth from views. Earlier work used view synthesis for training from stereo pairs or monocular video, while learned stereo architectures have aggregated matching costs over candidate disparities. Our contribution here is the controlled ambiguity benchmark and its shortlist intervention. The split exposes precisely what information this small system has been given. [Godard et al.](https://arxiv.org/abs/1609.03677) · [Zhou et al.](https://arxiv.org/abs/1704.07813) · [Kendall et al.](https://arxiv.org/abs/1703.04309)

## Methods and controls

For each reference pixel we concatenate its 3×3 intensity patch with a second-view 3×3 patch at each candidate shift. A shared 18→32→1 network scores candidate pairs; a softmax turns scores into weights. The training loss is the weighted absolute difference between the two center intensities. No per-pixel depth, correspondence, occlusion, mesh or object-ID targets enter optimization. We sample nonblack reference pixels. The training renderer uses explicit 3D geometry, and calibrated candidate projections supply the learner with a strong prior. A fixed stereo rule minimizes the mean absolute difference over the same nine intensities. A second control evaluates the neural matcher at its random initialization.

Each of three seeds received 400 Adam updates at 0.008 using eight fresh scene layouts and 32 sampled reference pixels per layout per update. That is 3,200 training scenes and 102,400 pixel samples per fit. The fits took 1.58, 0.78 and 0.78 seconds for the recorded training section on the Apple M5 Ultra. Training shapes were rectangles and ellipses viewed under signed one-unit motion. Each held-out panel used 96 independently drawn layouts and all four worlds per layout. The shift panel combined new triangle/diamond shapes and twice the displacement. The two changes are coupled. Higher shifted scores therefore cannot be attributed to a particular kind of generalization. [Protocol](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md) · [Training and scoring](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py) · [Device and loss curves](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

| Method | Training-family holdout | Shifted shapes and motion | Shifted novel-view error |
|---|---:|---:|---:|
| One-image constant depth | 25.00% | 25.00% | 0.3032 |
| Neural matcher, trained (three-seed mean) | 81.89% | 92.51% | 0.0468 |
| Fixed patch difference | 82.41% | 92.99% | 0.0439 |
| Renderer depth | 100% | 100% | 0 |

On 92,656 shifted foreground pixels the three trained seeds got 85,710, 85,680 and 85,749 correct. The fixed rule got 86,159. The trained-minus-fixed difference was −0.48 percentage points, paired 95% bootstrap interval [−0.58, −0.38]. Training improved on matched initialization by 71.65 points [54.28, 81.19]. All intervals use 5,000 paired draws over complete layouts and training seeds, preserving the four worlds together. Three seeds provide limited precision about training variability. Novel-view error is the mean absolute intensity error on the union of predicted and target nonblack pixels after rendering to the opposite side at triple unit displacement. The oracle reproduces the entire target frame. [All endpoints, contrasts and intervals](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

Textures matter. The learned matcher recovered 97.78% on textured surfaces and 76.78% on flat surfaces. It recovered only 30.57% of the 1,168 pixels occluded in the second image. The fixed method reached 40.75% on those pixels. The value of the second image is largest where something distinctive remains visible.

## What if we remove the four candidate depths?

Before scoring a fresh 96-layout panel we registered a frozen-weight comparison. Both search rules used the same image pairs. One checked the four offsets implied by camera motion and the allowed depths. The other checked every signed integer offset from −8 to +8; ranking those seventeen patches received no camera displacement. We applied the same change to the fixed rule. Training had still used calibrated projections. On 92,500 foreground pixels, results were as follows. [Follow-up protocol](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md) · [Search implementation](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py)

| Method | Four calibrated shifts | All 17 horizontal shifts |
|---|---:|---:|
| Learned pair scorer, three-seed mean | 92.21% | 85.94% |
| Fixed patch difference | 92.85% | 86.92% |

The learned difference was −6.27 points [−6.88, −5.69]. It selected a physically inadmissible shift 9.43% of the time and recovered 67.36% on flat surfaces in the dense search. Dense ranking defaults to the first best-scoring offset; if tied candidates instead receive uniform fractional credit, the learned mean is 85.08% and the fixed rule reaches 86.06%. Exact numeric tie handling therefore matters, particularly on flat regions.

## What the benchmark establishes

Two related images can provide depth evidence without explicit training depth labels on this renderer. The fixed rule remained more accurate and requires no training. The comparison favors that method as the baseline for new experiments in this setting. The dataset consists of front-facing planar surfaces, horizontal camera motion, idealized brightness and four discrete inverse depths. It does not test how a language or video foundation model acquired a general 3D representation.

An independent sort-based renderer reproduced the second and third images for all 1,152 evaluation worlds. Reloaded Metal weights and a separate patch extractor reproduced all published learned and fixed test counts. Recomputing the network with NumPy on eight layouts per panel changed 44 of 107,268 individual candidate selections across the fits and search settings. [Replay and numerical sensitivity](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

## Reproduce

The Studio ran Python 3.12.16, NumPy 2.5.5 and MLX 0.32.4 on Apple Silicon. Starting from the public code in this directory, run the commands below. The final two commands build the portable Chrome figure and the static plot. Raw per-world counts and all three saved networks are included under results.

```sh
python -m pip install mlx==0.32.4 numpy==2.5.5 matplotlib
python experiment.py
python search.py
python verify.py
python report.py
python demo.py
python figure.py
```