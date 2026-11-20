---
title: "Exchanging 25 learned directions reversed all 512 identifier pairs in two pretrained Qwen models"
paper_id: "2026-428"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:12:04Z"
abstract: "Swapping an arbitrary contiguous slice had reversed zero identifier pairs. A 25-dimensional subspace fitted to paired letter changes reversed 512 of 512 fresh pairs in both Qwen2.5-Coder-7B and Qwen2.5-14B. A random 25-dimensional intervention with the same per-token norm reversed zero. The learned changes control this specific answer on the aligned-token task. The positive result uses fewer than 1% of the dimensions of either residual stream."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Swapping an arbitrary contiguous slice had reversed zero identifier pairs. A 25-dimensional subspace fitted to paired letter changes reversed **512 of 512** fresh pairs in both Qwen2.5-Coder-7B and Qwen2.5-14B. A random 25-dimensional intervention with the same per-token norm reversed **zero**. The learned changes control this specific answer on the aligned-token task. The positive result uses fewer than 1% of the dimensions of either residual stream.

![Matching-norm random and learned subspaces compared with a whole-token exchange](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## How the directions were selected

The frozen checkpoints are Qwen/Qwen2.5-Coder-7B base revision 0396a76181e127dfc13e5c5ec48a8cee09938b02 and Qwen/Qwen2.5-14B base revision 97e1e76335b7017d8f67c08a19d103c0504298c9. We read the declaration token after block 6 of 28 in the 7B model (width 3,584) and after block 10 of 48 in the 14B model (width 5,120). Each pair shows the same program apart from one earlier declaration letter. The ending leaves that letter missing in the return statement. Both tokenizers change precisely one input token and admit the two possible completions as single tokens. [Token-aligned benchmark and earlier arbitrary-slice experiment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered subspace protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

On 512 calibration pairs we measured partner differences in the token state. We regressed those differences on the difference between the two letter indicator vectors, using a ridge penalty of 0.02 times the mean diagonal of the letter-design Gram matrix. We took the first 25 left singular vectors of the resulting hidden-by-letter matrix. Twenty-six class indicators have at most 25 independent contrasts here. The control orthogonalizes 25 Gaussian random directions to the learned subspace. It projects the same donor difference onto those directions, then scales each projected change to the same Euclidean norm as the learned change before casting for inference. Across all evaluated tokens the difference between matched float32 norms was at most 0.000008. The host and donor weights stay frozen. [Fit, vector intervention and evaluation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

For 512 fresh pairs (generator indices 8192–8703), exchange the projected letter change at the single declaration position. Keep all other positions untouched. Continue to the normal vocabulary readout in each model and score the originally correct letter against the partner’s letter. The primary success criterion requires both initially correct preferences to reverse. Swapping the full token state supplies a positive control.

| Intervention | Qwen coder 7B reversals | Qwen general 14B reversals |
|---|---:|---:|
| Learned 25-dimensional subspace | 512 / 512 | 512 / 512 |
| Equal-rank random directions with matching norm | 0 / 512 | 0 / 512 |
| Full vector at the same token | 512 / 512 | 512 / 512 |

The learned changes retained 94.9% and 97.4% of the original partner-difference norm at the median token in the 7B and 14B models. Their mean correct-letter log odds shifted from +12.87 to −12.70 and from +12.14 to −12.03. The equal-norm random controls remained at +12.70 and +12.02. The group-paired bootstrap gives a degenerate +100-point difference on this panel because every sampled pair has the same outcome. It does not describe uncertainty across other tasks or checkpoints. [Public prompts and margins](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recomputed effects and norms](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The fitted change acts on a token that directly contains the selected letter. It uses supervised knowledge of that source position and paired letter identities from calibration. The result establishes the effectiveness of a learned direction on this benchmark and does not yet establish that it can carry new kinds of information, survive a forced copy across layers, or move between models. The owner proposed studying fixed routes and what makes them carry an answer. OpenAI Codex implemented and operated the experiment on the owner’s Apple M5 Ultra, audited the outcomes and assisted with writing. The inference ran under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and Tokenizers 0.23.3. [Run receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)