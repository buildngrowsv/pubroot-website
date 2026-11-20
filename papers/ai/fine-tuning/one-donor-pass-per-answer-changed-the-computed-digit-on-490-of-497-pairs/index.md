---
title: "One donor pass per answer changed the computed digit on 490 of 497 pairs"
paper_id: "2026-463"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:38:20Z"
abstract: "A single target activation from the 7B coder was sufficient to change the computed digit in the frozen 14B host on 490 of 497 initially solved Python pairs. The paired-donor interface and full host-state exchange also passed 490. The equal-norm random control passed zero. Each direction of the one-pass intervention consumes only the donor activation for the desired operand."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A single target activation from the 7B coder was sufficient to change the computed digit in the frozen 14B host on **490 of 497** initially solved Python pairs. The paired-donor interface and full host-state exchange also passed 490. The equal-norm random control passed zero. Each direction of the one-pass intervention consumes only the donor activation for the desired operand.

![Full-vocabulary outcomes for the one-pass and paired-donor interfaces and both controls](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-pass.png)

## Fitting an absolute-state interface

Earlier experiments subtracted two donor states to cancel shared context before transferring an operand change. Here we fit an affine transform on absolute activation coordinates. We use the same procedure for fitting seven-dimensional donor and host subspaces on 512 direct-return calibration pairs. Let X and Y contain the donor and host declaration projections after blocks 6 and 10, respectively. Center each matrix across calibration prompts and regress centered Y on centered X with ridge penalty 0.02 times the mean diagonal of the centered donor Gram matrix. The intercept restores the host mean. At inference, take the projected state from the target donor prompt, apply the affine map, and replace the host assignment's original seven-coordinate projection. The host's remaining hidden coordinates stay as they were. [Registration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Affine fit and intervention code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

Use frozen Qwen2.5-Coder-7B base at revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and frozen Qwen2.5-14B base at revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. The 512 new host function pairs at indices 114000–114511 add or subtract a constant from their assigned operand. The two possible result digits differ from both operands. Independent donor functions at indices 115000–115511 return the operand directly. Their code and variable names differ from the host's. The one-pass edit uses only the target donor's declaration state. The paired arm translates the difference of the two donor states. The random control matches the one-pass edit's norm with an orthogonal basis. The full host control exchanges the complete assignment state with the partner. [Prompt and calibration archives](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

## Exact full-vocabulary outcomes

A native pair qualifies if the correct next-token digit is the unique maximum over the entire vocabulary in both versions. A reversal requires the partner digit to be the unique maximum in both edited versions. The two-choice comparison uses the two candidate logits from the same forward passes.

| Intervention | Full vocabulary | Two answer choices |
|---|---:|---:|
| One target donor state | 490 / 497 | 510 / 510 |
| Difference of two donor states | 490 / 497 | 510 / 510 |
| Equal-norm random directions | 0 / 497 | 0 / 510 |
| Complete host source exchange | 490 / 497 | 510 / 510 |

The one-pass and paired arms agree in 495 of 497 eligible full-vocabulary pairs. Each passed one pair the other missed. The one-pass advantage above random was +98.59 percentage points with a paired 95% interval of +97.38 to +99.60. The source location, projection, and output task are supplied. This supports using one target-state read for this numeric variable in these two frozen checkpoints. [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audited counts and map digest](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Run `uv run --with numpy python nested_surgery/numeric_absolute_study/verify.py` to execute the prompts and reconstruct the dose and rank checks. The Studio run took 118 seconds under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed expert transplantation. OpenAI Codex designed and implemented this comparison, ran it, verified its outputs and assisted with writing. [Version-pinned receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)