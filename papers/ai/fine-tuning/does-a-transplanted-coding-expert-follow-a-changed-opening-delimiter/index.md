---
title: "Does a transplanted coding expert follow a changed opening delimiter?"
paper_id: "2026-369"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T00:56:00Z"
abstract: "A coding expert spliced into block 27 of a larger language model solved zero of 256 three-program counterfactual tests. Each triplet used an identical fill-in-the-middle suffix and changed only one earlier opening delimiter. The transplanted model solved 243 of 768 individual programs, all requiring a closing parenthesis. Disabling the donor erased 47 correct parentheses and rescued 69 braces, increasing the total to 265. The standalone smaller donor solved 503 individual programs and seven complete triplets. Removing a donor can identify particular answers that depend on it even when the graft fails to follow the coding rule across paired changes."
score: 8.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A coding expert spliced into block 27 of a larger language model solved zero of 256 three-program counterfactual tests. Each triplet used an identical fill-in-the-middle suffix and changed only one earlier opening delimiter. The transplanted model solved 243 of 768 individual programs, all requiring a closing parenthesis. Disabling the donor erased 47 correct parentheses and rescued 69 braces, increasing the total to 265. The standalone smaller donor solved 503 individual programs and seven complete triplets. Removing a donor can identify particular answers that depend on it even when the graft fails to follow the coding rule across paired changes.

![Correct repairs grouped by the punctuation they require](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-repairs.png)

## Why repeat the intervention?

In the preceding experiment the donor qualified on 256/256 nested Python repairs against 119/256 for the original larger host. Training block 28 around a frozen block-27 coding graft gave 335/512 correct on a deeper panel. Seven new repairs that the equally trained native host missed disappeared when the donor was disabled. A four-entry lookup of the text after the gap also solved all 512. The present study was registered before collecting its outcomes to test whether the same trained graft could respond appropriately to a change in opening syntax when the suffix no longer supplies the answer. [Preceding paper](https://pubroot.com/ai/fine-tuning/which-new-python-repairs-disappear-when-a-transplanted-coding-expert-is-switched-off/) · [Decision protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

We generated 256 new arithmetic expressions. Each appears three times, following an opening parenthesis, square bracket or brace. Only that one input byte changes. Every suffix is identical across all 768 tasks. Each completed program returns the input variable, so closing the delimiter is required for syntax while execution behavior stays constant. The four candidates include a colon distractor. Python's parser identifies the valid repair in all 768 cases. A constant suffix-only prediction can solve at most one member per triplet. The primary endpoint requires all three. One byte can tokenize differently across variants. [Program construction and scoring](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

We restored the previously fitted final host block and coding donor, and refit the native and general controls on the same 16 original training examples with the same eight updates. All scores use the full installed model. For the donor-off and shuffled substitutions the recipient weights are held fixed. The smaller model is Qwen2.5-Coder-0.5B. The host is Qwen2.5-1.5B. A successful transfer required at least five percentage points of advantage over the adapted native host on complete triplets, a positive lower paired bound, and ten strict donor-dependent triplets. The models received no target-specific retraining on the new format. [Training and weights provenance](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Fill-in-the-middle training](https://arxiv.org/abs/2207.14255)

| Model or intervention | Correct individual repairs / 768 | Correct complete triplets / 256 |
|---|---:|---:|
| Standalone coding donor | 503 | 7 |
| Untouched native host | 61 | 0 |
| Adapted native host | 233 | 0 |
| Adapted general-purpose graft | 280 | 0 |
| Adapted coding graft | 243 | 0 |
| Coding donor disabled | 265 | 0 |
| Substituted shuffled donor | 223 | 0 |

The coding graft solved 243 of 256 parenthesis items and none of the bracket or brace items. The 47 strict donor-dependent individual repairs were all parentheses. Disabling the donor left 196 correct parentheses and 69 correct braces. Even the standalone coding model, which solved 255 parentheses and 241 brackets, solved only seven braces. The failure on complete triplets closes the prespecified syntax-transfer branch. The zero-width empirical paired interval for the graft-minus-native triplet score simply reflects that both had zero successes throughout this sample. It is not a population bound on every possible program or training seed. [Per-item logits and report](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Reproduce the result

The analysis retains the exact programs and full four-candidate logits from the second inference attempt. All model predictions had been saved when a type error stopped the JSON summary writer. The recovery reads the original artifacts by SHA-256 and performs no training or model inference. An independent NumPy/Python audit recompiled every patch, checked one changed byte per triplet, verified the single suffix, and reconstructed the correct-answer ledger and primary interval. From the repository root run `python nested_surgery/verify_opener.py nested_surgery/opener_study/results`. The project used Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5 on Apple M5 Ultra. [Hashed recovery](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Original receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The account owner proposed testing which newly correct answers disappear when an expert is switched off. OpenAI Codex generated the counterfactual panel, ran the study on the owner's Mac Studio, audited the predictions and assisted with the manuscript.