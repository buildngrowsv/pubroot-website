---
title: "When does a third camera recover depth on an occluded surface?"
paper_id: "2026-359"
author: "buildngrowsv"
category: "ai/computer-vision"
date: "2026-11-20T00:29:17Z"
abstract: "An opposite-side camera raised exact depth accuracy from 36.7% to 92.6% on synthetic pixels hidden from the first translated view and visible to the second. On an independent panel with a smaller camera displacement the gain was 49.4% to 82.2%. Across all foreground pixels, combining the views reduced accuracy on both panels. A round-trip consistency rule applied to two further panels also lost more correct pixels than it rescued."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

An opposite-side camera raised exact depth accuracy from 36.7% to 92.6% on synthetic pixels hidden from the first translated view and visible to the second. On an independent panel with a smaller camera displacement the gain was 49.4% to 82.2%. Across all foreground pixels, combining the views reduced accuracy on both panels. A round-trip consistency rule applied to two further panels also lost more correct pixels than it rescued.

## A controlled change in what the cameras can see

Each layout has four possible depth assignments rendering the same reference image. The matcher evaluates calibrated depth candidates with mean absolute error on 3×3 image patches. The first translated image supplies one error per candidate. With an opposite view available, fusion selects the smaller error for each candidate before choosing its depth. The matcher sees only images and camera geometry. Renderer IDs are used solely to identify newly visible pixels for scoring. Duplicating the first view leaves every prediction unchanged. A wrong opposite view from a different depth assignment of the same layout tests whether a corresponding image is necessary. Classical or learned stereo methods can use richer matching and regularization. This experiment isolates the camera signal in a fixed local matcher. [Preregistered camera study](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md) · [Kendall et al. on stereo matching](https://arxiv.org/abs/1703.04309)

| New layouts, each with four depth assignments | Single correct on newly visible pixels | Matched third view | Mismatched third view | Gains / losses with matched view | Change over all foreground |
|---|---:|---:|---:|---:|---:|
| 512 at the larger displacement | 2,252 / 6,135 | 5,680 / 6,135 | 484 / 6,135 | 3,443 / 15 | −7,958 / 500,140 |
| 512 at the smaller displacement | 719 / 1,456 | 1,197 / 1,456 | 165 / 1,456 | 508 / 30 | −10,170 / 497,880 |

The 95% paired intervals for the gains on newly visible pixels were 53.1 to 58.5 percentage points and 28.8 to 37.3 points. Each bootstrap draw keeps all four depth assignments of a layout together. Neither panel contained reference pixels hidden in both translated views, so that case has no estimate. The synthetic baseline, discrete depths, fixed renderer and local texture limit the inference. These results measure geometric information in paired images. They do not identify what any pretrained generative model learned from its training data. [First panel](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json) · [Confirmation](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

## Can a round-trip check spend the extra view more selectively?

On two fresh 512-layout panels we projected the first match back to the starting image. When it missed the original pixel, the router used the opposite camera's estimate. A matched-budget control substituted the opposite camera at exactly as many randomly chosen pixels per world. The rule used the other camera on 31,353/495,508 and 21,193/497,212 foreground pixels. It recovered 3,427 and 445 newly visible pixels while losing 40 and 23 in the same subsets. Across all pixels the rule lost a net 7,697 and 10,311 correct estimates relative to the single-view baseline. Its overall accuracy fell below the matched random control in both cases. Reverse matching also requires computation, so the fraction routed measures opposite-view use alone. The planned promotion gate closed. [Routing protocol](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md) · [Routing counts and intervals](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

The public evidence includes one count vector for each world and subset. The audit reaggregates 8,192 worlds, checks the duplicate-view identity per world and verifies the gains-minus-losses identities before matching every published total. Run `python occlusion/verify.py occlusion/results` with NumPy. [Audit implementation](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json) · [Source for view matching](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py) · [Routing source](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py)

The account owner proposed investigating what 3D information a model can obtain from its training inputs. OpenAI Codex designed and ran the comparisons over SSH on the owner's Apple M5 Ultra, audited the scores and assisted with this manuscript.