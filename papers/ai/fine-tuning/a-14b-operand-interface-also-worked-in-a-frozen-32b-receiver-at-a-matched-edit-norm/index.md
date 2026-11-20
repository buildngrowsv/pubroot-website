---
title: "A 14B operand interface also worked in a frozen 32B receiver at a matched edit norm"
paper_id: "2026-470"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:49:09Z"
abstract: "A 7B donor's one-pass edit reversed 420 of 507 initially correct pairs in Qwen2.5-32B with a fitted receiver interface. Reusing the 14B interface's edit direction, scaled to the fitted 32B edit's norm, reversed 414 of 507. Equal-norm random directions reversed zero. The full 32B assignment-state exchange reversed 426. The fitted interface cleared the registered transfer gate. The gain over the borrowed direction was below the registered 20-point margin."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A 7B donor's one-pass edit reversed **420 of 507** initially correct pairs in Qwen2.5-32B with a fitted receiver interface. Reusing the 14B interface's edit direction, scaled to the fitted 32B edit's norm, reversed **414 of 507**. Equal-norm random directions reversed zero. The full 32B assignment-state exchange reversed 426. The fitted interface cleared the registered transfer gate. The gain over the borrowed direction was below the registered 20-point margin.

![Original 14B and fitted or borrowed 32B edits on the same clean arithmetic groups](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Same donor and arithmetic, two receiver sizes

Generated Python functions assign a single-digit variable and return its value plus or minus a constant. Each pair changes the earlier assignment while leaving the assertion prefix and the rest of the program unchanged. Its two possible result digits differ from both operands. Separate donor functions return the operand directly and have different identifier stems. CPython verifies the expected completion. We use the same 512 fresh host pairs at indices 117000–117511 and donor functions at indices 118000–118511 for both receiver sizes. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Executable prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The donor is frozen Qwen2.5-Coder-7B base at revision `0396a76181e127dfc13e5c5ec48a8cee09938b02`. The smaller receiver is Qwen2.5-14B base at `97e1e76335b7017d8f67c08a19d103c0504298c9` and the larger receiver is Qwen2.5-32B base at `1818d35814b8319459f4bd55ed1ac8709630f003`. Neither receiver is quantized. The 14B receiver uses its saved seven-coordinate affine map after block 10 of 48. For the 32B model, fit seven directions and an affine map after block 13 of 64 using the original 512 direct-return calibration pairs. The donor site is after block 6. The layer cuts approximately match relative depth. [Original one-pass interface](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Official 32B checkpoint](https://huggingface.co/Qwen/Qwen2.5-32B)

The borrowed arm projects the 32B assignment onto the archived 14B basis, computes the 14B interface's suggested replacement, and scales that edit to the norm of the fitted 32B edit on the same prompt. Its direction uses the old interface and its norm uses the newly fitted one. Both widths are 5,120, so the vectors fit directly in the same coordinate dimension. The norm-matched random control uses seven orthogonal directions from the fitted recipient. The paired-donor and full host assignment exchanges are additional controls. [Inference and norm checks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Intervention implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Full-vocabulary reversal and shared cohorts

A pair qualifies when both native output digits are unique maxima over the entire vocabulary. Reversal requires the two counterfactual digits to be unique maxima after the edit. Pair counts below use each recipient's eligible cohort.

| Recipient | Native pairs | Fitted one-pass | Paired donor | Equal-norm random | Full host state | Borrowed direction |
|---|---:|---:|---:|---:|---:|---:|
| 14B | 506 | 505 | 505 | 0 | 505 | — |
| 32B | 507 | 420 | 421 | 0 | 426 | 414 |

There were 502 pairs both recipients solved natively. On those, the 14B fitted and full-state arms reversed 501 each. The 32B fitted arm reversed 415, full-state exchange 421, and the borrowed direction 409. Under the full 32B cohort the fitted-minus-borrowed difference was +1.18 points, with a paired 95% interval of −0.39 to +2.76. The 32B full-state comparison also reversed fewer pairs than the 14B comparison. The outcome measures sensitivity to the chosen intervention and layer, with native task accuracy reported separately. [Saved ranks, norms and map](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Recomputed effects](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

As an exploratory diagnostic, the seven singular values of the two fitted host bases' overlap matrix range from 0.74 to 0.84. Their mean square was 0.633, versus 0.00049 for the old basis against the 32B orthogonal control. The fitted subspaces overlap in ambient coordinates in this family. The study uses fitted edit magnitudes, known sites, and one-step arithmetic. [Exploratory overlap calculation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

Run `uv run --with numpy python nested_surgery/numeric_scale_study/verify.py` to check every prompt, rank, norm and comparison. The run took six minutes and 59 seconds on the owner's Apple M5 Ultra. The owner proposed expert transplantation and larger-scale tests. OpenAI Codex designed and operated the comparison, verified its outputs and assisted with writing. [Version-pinned receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)