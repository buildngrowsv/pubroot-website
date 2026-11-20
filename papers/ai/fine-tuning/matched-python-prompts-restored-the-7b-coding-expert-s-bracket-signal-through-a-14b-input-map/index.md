---
title: "Matched Python prompts restored the 7B coding expert\u2019s bracket signal through a 14B input map"
paper_id: "2026-416"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T05:37:34Z"
abstract: "On 256 fresh repair groups, Qwen2.5-Coder-7B gave a matching-bracket signal of +2.049 log-odds from its own final-layer input. The archived map from Qwen2.5-14B gave \u22120.235. An affine map fitted on matched synthetic Python prompts recovered +2.040. The recovery minus the native effect was \u22120.008 (group-paired 95% interval \u22120.030 to +0.012). With the donor\u2019s own residual and readout held fixed, the new input map gave 58 complete groups, compared with 37 for the archived map and 59 for native input. The tested host state contains information an affine map can deliver to the expert."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On 256 fresh repair groups, Qwen2.5-Coder-7B gave a matching-bracket signal of **+2.049 log-odds** from its own final-layer input. The archived map from Qwen2.5-14B gave **−0.235**. An affine map fitted on matched synthetic Python prompts recovered **+2.040**. The recovery minus the native effect was −0.008 (group-paired 95% interval −0.030 to +0.012). With the donor’s own residual and readout held fixed, the new input map gave 58 complete groups, compared with 37 for the archived map and 59 for native input. The tested host state contains information an affine map can deliver to the expert.

![Matching-bracket signal from the native donor and each fixed input map](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Identical models and a new calibration set

The donor is Qwen/Qwen2.5-Coder-7B base revision 0396a76181e127dfc13e5c5ec48a8cee09938b02. We use its final feed-forward module in block 28 and its native readout. The host is Qwen/Qwen2.5-14B base revision 97e1e76335b7017d8f67c08a19d103c0504298c9. We use its block-27 state after attention and immediately before the feed-forward module. Both checkpoints stay frozen. The original map was fitted on 6,144 positions in CPython implementation and documentation. It failed the earlier crossed opener test. [Original fit and intervention](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Donor checkpoint](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/tree/0396a76181e127dfc13e5c5ec48a8cee09938b02) · [Host checkpoint](https://huggingface.co/Qwen/Qwen2.5-14B/tree/97e1e76335b7017d8f67c08a19d103c0504298c9)

The new fits use corresponding prediction-position vectors for 1,536 calibration prompts in 512 groups (indices 45000–45511). Each group has otherwise identical Python prefixes and suffixes with three distinct opening brackets. Both 5,120-to-3,584 affine maps minimize squared input-state error with a ridge penalty of 0.02 times the mean diagonal of the centered feature Gram matrix. The ordinary map treats each observation equally. The weighted map scales each deviation from its own triplet mean by four before solving, multiplying the loss weight on deviations by 16. Calibration uses paired activations without completion labels or evaluation prompts. Relative to the archived map, the new calibration changes the dataset, sample size and extraction position. Weighting is the only difference between the two new maps. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## The bracket choice follows the translated input

The independent evaluation uses 256 new groups (indices 50000–50255). For each destination we supply the expert with each of three source variants and keep all other 7B state native. We score four candidate tokens for a closing parenthesis, a closing square bracket, a closing brace and a colon. For each candidate pair we subtract the A-versus-B log odds under source B from the same log odds under source A. Holding the destination fixed cancels any constant bias toward either candidate. We average across bracket pairs and destinations and resample whole groups for uncertainty intervals. The native scores reproduce standard forward choices on the eight preflight examples.

| Source for the frozen donor module | Matching-bracket log-odds effect | Paired 95% interval | Fully solved groups with matching source |
|---|---:|---:|---:|
| Native 7B state | +2.0489 | +1.9875 to +2.1096 | 59 / 256 |
| Archived 14B input map | −0.2351 | −0.2619 to −0.2090 | 37 / 256 |
| Refit ordinary map | +2.0404 | +1.9770 to +2.1041 | 58 / 256 |
| Refit weighted map | +2.0427 | +1.9792 to +2.1050 | 58 / 256 |
| Zero module output | No source input | — | 29 / 256 |

The ordinary map exceeded half the native signal by +1.016 (95% interval +0.980 to +1.053), clearing the registered recovery condition. Its complete-group lead over the archived map was 8.20 points (4.69 to 11.72). Weighting changed the log-odds estimate by +0.0023 (−0.0096 to +0.0138). The prespecified rule selected the ordinary fit. Each of the three bracket-pair effects was positive for that map. [Raw crossed scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-scores.npz) · [Evaluation prompts and calibration IDs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Reconstructed paired estimates](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

This is an input-side recovery using one model pair, calibration draw and synthetic generator. A successful transplant into the 14B network additionally depends on its output map and subsequent blocks. The follow-up changes the input map while keeping the output map and block-28 training budget fixed. Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5 produced the study on the owner’s Apple M5 Ultra. The NumPy audit reconstructs candidate labels and arm comparisons without model weights. The owner proposed expert transplantation. OpenAI Codex designed and ran the experiments, audited the results and assisted with writing. [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)