---
title: "Can a frozen attention router transfer where to read without sending the answer?"
paper_id: "2026-388"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T02:29:19Z"
abstract: "A learned router saw register keys and write order but had no input for the values being stored. We moved its position scores into a separate model with its own value vocabulary and readout. On longer programs with unseen combinations of key symbols, the graft answered 88.61% and 85.91% on two independent fits. Cyclically shifting those same scores dropped accuracy below 0.30% in both. Changing the selected write's value caused the corresponding answer change on roughly 98% of clean correct answers. The native routers matched or beat the graft on that panel. The results establish a payload-independent contribution from learned scores on this benchmark. The experiment missed its prespecified joint threshold and gives no advantage over learning the router locally."
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A learned router saw register keys and write order but had no input for the values being stored. We moved its position scores into a separate model with its own value vocabulary and readout. On longer programs with unseen combinations of key symbols, the graft answered 88.61% and 85.91% on two independent fits. Cyclically shifting those same scores dropped accuracy below 0.30% in both. Changing the selected write's value caused the corresponding answer change on roughly 98% of clean correct answers. The native routers matched or beat the graft on that panel. The results establish a payload-independent contribution from learned scores on this benchmark. The experiment missed its prespecified joint threshold and gives no advantage over learning the router locally.

## Which part of a memory behavior transfers?

A recent working paper reports that transplanting a donor activation injected an already-computed answer in its synthetic task. Our graft sends only a row of scores over preceding write positions. The donor never receives the recipient's values. The recipient applies the scores to its own value embeddings and decodes the resulting vector using its own output weights. The learned router uses distinct query and write-key projections over symbolic key components, plus a request-dependent learned bias over ordinal position. Neither matching addresses nor pointer targets enter training or evaluation inference. The training objective is answer prediction. Learned position selection and explicit memory address/content separation have precedents. This is a small controlled study of reusing a learned position-selection function. [Revised Boucher working paper](https://git.spboucher.ai/wpai0001_uqo) · [Pointer Networks](https://arxiv.org/abs/1506.03134) · [Dynamic Neural Turing Machine](https://arxiv.org/abs/1607.00036) · [Zoology](https://arxiv.org/abs/2312.04927)

We trained two independent donors on programs with 12 composite keys and 36 interleaved write positions. An independent recipient saw the same types of program with values drawn from a disjoint set of 64 IDs. Each recipient got 128 batches. The exact same training stream fit the recipient with the frozen trained router, a same-design native router trained end to end, and a frozen untrained router. Test programs drew 20 keys as unseen combinations of familiar symbols, with 60 write positions. The oracle addresses are computed from program semantics and used in the analysis. Each fit used 1,024 held-out programs, with 16 balanced original/latest queries each. [Design, controls and registered thresholds](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training and evaluation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

| Long held-out programs | Seed 101/503 | Seed 211/607 |
|---|---:|---:|
| Graft finds the exact write | 91.31% | 88.39% |
| Graft outputs the right value | 88.61% | 85.91% |
| Same graft with its position scores shifted | 0.18% | 0.30% |
| Frozen untrained router | 1.56% | 1.76% |
| Same-budget trained native router | 89.11% | 90.27% |
| Native router finds the exact write | 99.66% | 100% |

Graft minus shifted-sham accuracy was +88.43 points [87.84, 88.99] and +85.61 [84.96, 86.25]. Graft minus trained native was −0.50 [−1.19, +0.16] and −4.36 [−5.07, −3.64]. The intervals resample whole programs within each fit. On familiar-length programs with familiar key combinations, the graft scored 98.14% and 97.90%, while the native control scored 90.09% and 90.87%. The direction of that comparison changed under the crossed shift. This design varies key combinations and write count together. [Results and per-arm intervals](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Counterfactuals

For each clean program we selected pairs that changed only the request from original to latest, or changed just one key symbol. Exact address and answer accuracy were required on both sides. Switching the request gave 6,895/8,192 and 6,619/8,192 successes. Switching the key gave 1,594/2,037 and 1,516/2,042. The key-switch fractions missed 80% on both seeds. For the first and second fits, changing only the gold write's value switched the answer correctly in 14,244/14,518 and 13,794/14,076 clean correct cases. The same change at a stale write preserved 14,246/14,518 and 13,799/14,076. Those tests kept the entire position-score row fixed. Among all 16,384 queries per fit, the gold-write replacements produced 14,533 and 14,088 correct answers. The direct classifier result, the source argmax, and the conditional causal result have different denominators. [Saved predictions and recomputed counts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The experiment ran on the CPU of an Apple M5 Ultra while the GPU continued a separate run. The measured runs took 3.59 and 3.34 seconds, with peak resident memory of 99 and 106 MB. The launcher failed to save the first exit receipt after the predictions had been written. An exact rerun reproduced every saved prediction array and every reported accuracy measure. Its temporary files were removed and it wrote no weight checkpoints. The source revision and the rerun's exit are recorded. The independent NumPy audit reconstructs interpreter answers, all paired confidence intervals and conditional counts. [Verification script](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Reproduction receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The account owner proposed testing learned addressing and transferable memory. OpenAI Codex designed and implemented the experiment, ran it over SSH on the owner's Mac Studio, verified the forecasts and assisted with writing.