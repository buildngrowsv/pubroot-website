---
title: "A transferred operand changed the top token in 488 of 491 arithmetic pairs without a shortlist"
paper_id: "2026-448"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:58:48Z"
abstract: "When the 14B host could choose any token in its vocabulary, the edit translated from Qwen2.5-Coder-7B still made the counterfactual computed digit the unique top prediction on 488 of 491 initially solved Python pairs. An equal-norm random change reversed zero pairs, and the full host assignment-state exchange reversed 488. The earlier two-answer score reproduced on the same inference passes."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

When the 14B host could choose any token in its vocabulary, the edit translated from Qwen2.5-Coder-7B still made the counterfactual computed digit the unique top prediction on **488 of 491** initially solved Python pairs. An equal-norm random change reversed **zero pairs**, and the full host assignment-state exchange reversed 488. The earlier two-answer score reproduced on the same inference passes.

![Pair reversals using the complete vocabulary and using two answer tokens](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-vocabulary.png)

## What changed in scoring

We reused the 512 previously evaluated host pairs, separate donor functions, and exact seven-by-seven map. Both models remained frozen. The donor function returns its assigned integer directly. The host function adds or subtracts a small constant, and its two possible outputs differ from both donor operands. The translated edit uses the difference between the donor states of the two prompts at their declaration positions after block 6. The edit acts at the host assignment after block 10. The host continues through its ordinary blocks and vocabulary projection. See the previous study for both pinned model revisions, calibration, candidate programs and saved map. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Operand transfer methods and source archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Full-vocabulary inference](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

For each prompt, the original and alternative digits are assigned a rank equal to the count of all vocabulary logits at or above each digit's logit. A rank of one requires a unique maximum. A native pair qualifies only if both correct digits have rank one, and reversal requires both counterfactual answers to have rank one after intervention. For the two-choice comparison we also compare the two digit logits in the same forward passes. The saved digest confirms the exact previous map and prompt archive. [Saved ranks, top token IDs, margins and edit norms](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

| Scoring rule | Native eligible pairs | Translated reversals | Norm-matched random | Full host state |
|---|---:|---:|---:|---:|
| Complete vocabulary, unique top token | 491 / 512 | 488 / 491 | 0 / 491 | 488 / 491 |
| Two answer tokens | 511 / 512 | 511 / 511 | 0 / 511 | 511 / 511 |

The difference over the randomized directions was +99.39 percentage points under full-vocabulary scoring. The paired 95% interval was +98.57 to +100.00. Across all 1,024 prompts the transferred edit put the alternative digit strictly first 1,004 times. Its top token was outside the two digits in 18 prompts. These are next-token decisions in a generated one-step arithmetic task with two donor passes and an identified source. Multi-token continuations and arithmetic with two independently edited operands require separate tests. [Audit and full-vocabulary counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verification](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

Run `uv run --with numpy python nested_surgery/numeric_open_study/verify.py` to verify the archive identities, ranks, dose matches, and paired counts against the prior scores. Studio inference took 90 seconds on the owner's Apple M5 Ultra under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed expert transplantation. OpenAI Codex implemented this follow-up, ran and verified it, and assisted with writing. [Version-pinned receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)