---
title: "Translating 25 activation coordinates from a 7B coder reversed 512 identifier pairs in a 14B model"
paper_id: "2026-435"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:29:31Z"
abstract: "A fitted linear map carried a declaration edit from Qwen2.5-Coder-7B into Qwen2.5-14B. The translated change reversed 512 of 512 fresh pairs. An equal-norm edit in an orthogonal random subspace reversed zero. The two models remain frozen. The comparison uses a known token position and two candidate letters in generated Python."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A fitted linear map carried a declaration edit from Qwen2.5-Coder-7B into Qwen2.5-14B. The translated change reversed **512 of 512** fresh pairs. An equal-norm edit in an orthogonal random subspace reversed **zero**. The two models remain frozen. The comparison uses a known token position and two candidate letters in generated Python.

## The interface

The coder and general host use widths 3,584 and 5,120. At their source tokens after blocks 6 and 10, respectively, we fit a 25-dimensional basis for changes among 26 letters using 512 paired calibration prompts. Projecting each paired difference into its model's basis gives two 25-number coordinates. We fit a 25 by 25 ridge map from the donor differences to the host differences, with the penalty set to 0.02 times the mean diagonal of the donor Gram matrix. We use Qwen2.5-Coder-7B base revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Fit and inference](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

On fresh indices 16000–16511 the 7B model reads both versions. Its difference passes through the map and expands into the 14B host's hidden space. Add the result at the host declaration and score the host's own completion. The translated edit is independent of the paired host activation at inference. The positive control copies that host activation directly. For the random control, we use the same coefficient vector in a 25-dimensional orthogonal random basis and explicitly match the edit norm before converting to the inference dtype. [Saved map, programs and logits](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

| Host intervention | Paired reversals | Direction 1 | Direction 2 |
|---|---:|---:|---:|
| Translated donor edit | 512 / 512 | 512 / 512 | 512 / 512 |
| Same-norm random control | 0 / 512 | 0 / 512 | 0 / 512 |
| Full host site exchange | 512 / 512 | 512 / 512 | 512 / 512 |

The host solved both unedited completions in all 512 pairs. The paired bootstrap interval of +100 to +100 percentage points reflects identical outcomes on this panel. The first two runs stopped when a Metal norm calculation missed a numerical tolerance. The reported run explicitly rescales the random control and passes the norm check. The earlier attempts produced no benchmark scores. [Successful receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verification](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recomputed results](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

This transfers a fitted counterfactual activation change for a known fact. It uses two donor forward passes, a known declaration position, and calibration examples with shared tasks. The trained donor weights and expert block stay in the donor. Model stitching and cross-size feature transfer supply established precedents for fitted interfaces between frozen networks. The follow-up changes the donor's surrounding program and gives the host two competing source locations. [Model stitching](https://arxiv.org/abs/2106.07682) · [Cross-size feature transfer](https://arxiv.org/abs/2506.06609) · [Cross-context protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/identifier_transfer_study/verify.py` from the repository root. The successful Studio run took two minutes and 24 seconds with Python 3.12, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and Tokenizers 0.23.3. The owner proposed expert transplants and fixed references. OpenAI Codex implemented and ran this comparison, verified the outcomes and assisted with writing.