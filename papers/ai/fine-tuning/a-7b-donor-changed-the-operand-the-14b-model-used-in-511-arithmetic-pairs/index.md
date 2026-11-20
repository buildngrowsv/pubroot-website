---
title: "A 7B donor changed the operand the 14B model used in 511 arithmetic pairs"
paper_id: "2026-444"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:45:18Z"
abstract: "An activation change from a separate 7B coding model reversed the 14B host's preferred computed answer on all 511 initially solved Python pairs. The donor saw a function that returned the assigned number directly. The host saw a different function, which added or subtracted a constant. An equal-norm random change reversed zero pairs."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

An activation change from a separate 7B coding model reversed the 14B host's preferred computed answer on **all 511 initially solved Python pairs**. The donor saw a function that returned the assigned number directly. The host saw a different function, which added or subtracted a constant. An equal-norm random change reversed zero pairs.

![Reversal counts for the translated operand, matched random edit and full host state](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## How the edit crosses models

We froze Qwen2.5-Coder-7B base revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. Fit seven dimensions for paired changes among eight possible assignment digits, at block 6 in the donor and block 10 in the host. The 512 calibration functions return their assigned numbers directly. Use paired projected changes from the two models to fit a seven-by-seven ridge map. The regularization is 0.02 times the mean diagonal of the projected donor Gram matrix. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Fit and inference code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

In the fresh evaluation the donor functions have different identifiers and surrounding code. They carry the same two possible source values and omit the host's arithmetic operator. The host adds or subtracts a constant from its corresponding variable. Each of its two candidate answers differs from both source digits. The verifier runs both completions in CPython. To intervene, we translate the difference between the two donor declaration states and add it to one host declaration state. The host finishes with its own blocks and own readout. The equal-norm control injects the coefficients into seven random orthogonal directions at the same site. The full host assignment-token exchange is the positive control. [Saved prompts, weights for the map and margins](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

| Host condition | Addition | Subtraction | Total reversed pairs |
|---|---:|---:|---:|
| Translated donor operand edit | 255 / 255 | 256 / 256 | 511 / 511 |
| Equal-norm random edit | 0 / 255 | 0 / 256 | 0 / 511 |
| Full host state exchange | 255 / 255 | 256 / 256 | 511 / 511 |

The native host solved both completions on 511 of 512 pairs. For those pairs, the original answer margin went from +3.61 to −3.55 with transfer and stayed at +3.61 with the random control. All eligible pairs contributed the same sign to the paired comparison, giving a bootstrap interval of +100 to +100 percentage points for this panel. The models share a family. The experiment uses two donor passes, a known assignment location, and a forced choice between two computed digits. How the host uses multiple independent operands is the next test. [Independent verification](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recomputed effects](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Two-operand protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Related cross-size feature transfer](https://arxiv.org/abs/2506.06609)

Run `uv run --with numpy python nested_surgery/numeric_transfer_study/verify.py` to check every saved program, map dimensions, edit norms and paired results. The run took 98 seconds on the owner's Apple M5 Ultra with MLX 0.32.4, MLX-LM 0.32.2, Python 3.12, NumPy 2.5.5 and Tokenizers 0.23.3. The owner proposed expert transplantation and research on fixed internal references. OpenAI Codex designed and implemented the experiment, ran it, verified the results and assisted with writing.