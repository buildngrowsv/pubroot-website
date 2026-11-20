---
title: "Changing seven activation coordinates changed 511 computed answers in Qwen2.5-14B"
paper_id: "2026-442"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:39:47Z"
abstract: "A learned edit at a Python assignment reversed the model's preferred computed result on all 511 initially solved pairs. The edit reversed every eligible addition and subtraction pair. A random change of the same norm reversed zero. Both possible computed answers used digits different from either source digit, so the task required choosing the consequence of the change."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A learned edit at a Python assignment reversed the model's preferred computed result on **all 511 initially solved pairs**. The edit reversed every eligible addition and subtraction pair. A random change of the same norm reversed zero. Both possible computed answers used digits different from either source digit, so the task required choosing the consequence of the change.

## From a stored number to a computed answer

The generated Python function assigns an integer to a variable and returns its value plus or minus a small constant. The prompt ends at an incomplete assertion about the function's output. In the paired program, only the assignment digit changes. Both available assertion completions are single tokens, and only one executes successfully in each program. For the seven-dimensional basis we use 512 separate pairs whose functions return the assigned integer directly. Eight possible source digits supply seven independent contrasts. The evaluation uses 512 fresh pairs at indices 60000–60511, all with a nonzero offset. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Generator and inference](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

We froze Qwen2.5-14B base at revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. In each evaluation pair we project the activation difference at the assignment digit after block 10 onto the fitted subspace, exchange that change, and run the rest of the model. An equal-norm edit in a random orthogonal subspace provides the matched control. The full assignment state exchange supplies a positive control. [Subspace code and controls](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Intervention | Addition reversals | Subtraction reversals | Total |
|---|---:|---:|---:|
| Learned seven directions | 255 / 255 | 256 / 256 | 511 / 511 |
| Norm-matched random directions | 0 / 255 | 0 / 256 | 0 / 511 |
| Full assignment state | 255 / 255 | 256 / 256 | 511 / 511 |

The untouched model solved both completions in 511 of 512 pairs. One addition pair was ineligible. In the eligible cases, the mean logit margin for the original correct answer moved from +3.53 to −3.44 with the learned edit and stayed at +3.51 with the random edit. Both bootstrap bounds for the reversal contrast were +100 percentage points because every eligible pair had the same outcome. The result concerns generated one-step arithmetic under two candidate completions. The construction fixes the edit location and uses both counterfactual states. More complex computation and cross-model operand transfer are separate tests. [Run receipt, prompts and margins](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recomputed results](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Cross-model follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/computation_study/verify.py` to execute the saved cases and recompute the statistics. The owner proposed testing whether a protected or transplanted state can carry something useful. OpenAI Codex designed and implemented the comparison, ran it on the owner's Apple M5 Ultra, verified the outputs and assisted with writing. The run took 92 seconds under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and Tokenizers 0.23.3.