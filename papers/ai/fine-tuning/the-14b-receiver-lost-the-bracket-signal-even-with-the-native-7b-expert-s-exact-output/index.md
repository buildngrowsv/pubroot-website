---
title: "The 14B receiver lost the bracket signal even with the native 7B expert\u2019s exact output"
paper_id: "2026-426"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:10:45Z"
abstract: "The native Qwen2.5-Coder-7B expert produced a +2.111 matching-bracket log-odds effect on 256 fresh Python repair groups. Feeding its exact output through the original output map into the trained Qwen2.5-14B receiver at the prediction position produced \u22120.009. Giving the same receiver the expert output generated from refitted host input produced \u22120.010. Exact native input to the expert and leaving the preceding host positions intact were insufficient to recover the signal through this output map and receiver."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The native Qwen2.5-Coder-7B expert produced a **+2.111** matching-bracket log-odds effect on 256 fresh Python repair groups. Feeding its exact output through the original output map into the trained Qwen2.5-14B receiver at the prediction position produced **−0.009**. Giving the same receiver the expert output generated from refitted host input produced **−0.010**. Exact native input to the expert and leaving the preceding host positions intact were insufficient to recover the signal through this output map and receiver.

![Bracket-specific log odds in the donor and three receiving interventions](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-boundary.png)

## The intervention starts after the expert

The donor is Qwen/Qwen2.5-Coder-7B base revision 0396a76181e127dfc13e5c5ec48a8cee09938b02, and its expert is the last block’s feed-forward module at width 3,584. The receiver is Qwen/Qwen2.5-14B base revision 97e1e76335b7017d8f67c08a19d103c0504298c9. The earlier transplant replaced its block-27 feed-forward module at width 5,120. Its frozen affine output map was fitted by trace-regularized ridge regression to approximate native host module outputs on 6,144 training-only CPython states. The earlier graft updated only block 28 for eight Adam steps at 0.00002 on 16 examples. We restore those exact adapted block-28 weights, verify the archived input and output map digests, and fit no additional weights. [Original output fit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Failed all-position graft and training details](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered output intervention](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Keep the host’s native block-27 contribution at every token except the final prediction position. Cross all three destination prompts in each group against each of the three source prompts. Feed the 14B recipient either its own block-27 contribution, the mapped output of the donor module driven by its exact original 7B input, or the mapped output of the donor module driven by refitted 14B input. The two donor-output conditions share the same affine output transform and receiving path. A fourth condition uses the exact same 7B donor contribution with its native 7B residual and readout. The native host diagonal reproduces the standard scoring path on a preflight batch. [Inference code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Matched opener effects

The fresh panel uses generator indices 70000–70255, with one differing opening character per triplet and the same suffix. We independently parsed all candidate completions. Average the within-destination change in A-versus-B closing-token log odds when switching the source opener from B to A. Pool the three pairs and three destinations with equal weight and resample whole groups for 95% intervals. This contrast cancels a fixed preference toward one candidate for a given destination.

| Contribution and receiver | Matching-bracket log-odds effect | Paired 95% interval | Complete matching-source groups |
|---|---:|---:|---:|
| Native 7B output and 7B readout | +2.1109 | +2.0401 to +2.1802 | 44 / 256 |
| Native host output and 14B receiver | −0.0229 | −0.0282 to −0.0176 | 0 / 256 |
| Exact 7B output through original map and 14B receiver | −0.0090 | −0.0117 to −0.0060 | 0 / 256 |
| Refitted input, then same map and 14B receiver | −0.0096 | −0.0122 to −0.0070 | 0 / 256 |

The exact-output condition minus half the native donor effect was −1.0644 (−1.0994 to −1.0288), with an upper bound below zero. This met the registered conclusion that the tested output map and receiver failed to retain half the native signal. The comparison localizes the limit to those components jointly. It does not identify how the affine map and later 14B computation contribute individually. The host receiver used this one trained checkpoint and intervention position. [Raw crossed scores and interface hashes](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent verification](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audited effects](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The owner proposed the expert transplant and matched controls. OpenAI Codex implemented and ran the experiment on the owner’s Apple M5 Ultra, audited the evidence and assisted with writing. The model inference used Python 3.12, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and Tokenizers 0.23.3. The verification script runs with Python and NumPy using only the public scores and prompt archive.