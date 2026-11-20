---
title: "A borrowed 14B interface changed complete 32B sums in 358 of 512 groups"
paper_id: "2026-482"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:29:54Z"
abstract: "Two independently supplied 7B activations changed all four answers in 358 of 512 arithmetic groups in a frozen 32B model. Equal-norm orthogonal edits succeeded in zero groups. Exchanging both complete native states succeeded in 454. The borrowed method cleared the causal contrast and fell short of the registered 80% complete-group target. The same examples previously yielded 512 complete reversals with the original paired intervention in the 14B model."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Two independently supplied 7B activations changed all four answers in **358 of 512 arithmetic groups** in a frozen 32B model. Equal-norm orthogonal edits succeeded in zero groups. Exchanging both complete native states succeeded in 454. The borrowed method cleared the causal contrast and fell short of the registered 80% complete-group target. The same examples previously yielded 512 complete reversals with the original paired intervention in the 14B model.

![Complete-group outcomes and the one-digit to two-digit transitions](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-32b.png)

## One donor input per operand

We used the same 512 four-variant Python assignment and addition groups as the prior 14B experiment. Each group has four distinct answers. At least one crosses the decimal threshold of ten, and each candidate differs from both operands. A frozen 7B coder supplied a separate declaration for each operand. The archived 14B affine map converts the source states into target coordinates for the two assignment tokens in the frozen 32B recipient. Reuse the same gain of 2.624717 previously estimated from separate single-operand input contrasts. The 32B model and gain remain frozen. The 32B recipient passed all 128 qualification groups. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Original prompt archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Gain calibration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

The models were three pinned Qwen2.5 base checkpoints in BF16.

| Role | Checkpoint | Revision | Hidden width | Cut |
|---|---|---|---:|---:|
| Donor | Qwen2.5-Coder-7B | [0396a761](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/tree/0396a76181e127dfc13e5c5ec48a8cee09938b02) | 3,584 | 6 |
| Interface training | Qwen2.5-14B | [97e1e763](https://huggingface.co/Qwen/Qwen2.5-14B/tree/97e1e76335b7017d8f67c08a19d103c0504298c9) | 5,120 | 10 |
| Frozen receiver | Qwen2.5-32B | [1818d358](https://huggingface.co/Qwen/Qwen2.5-32B/tree/1818d35814b8319459f4bd55ed1ac8709630f003) | 5,120 | 13 |

The cut is the number of complete transformer blocks applied before reading or writing. For a partner donor activation `d`, form target coordinates `c = d A W + b` using the archived donor basis `A` (3584×7), affine weight `W` (7×7) and bias `b` (7). For the current 32B assignment activation `h`, the actual update is `h' = h + g (c − h B) Bᵀ`, where `g = 2.624717` and `B` is the archived 14B basis (5120×7). For each operand, the alternate donor activation comes from the input whose value should be supplied for that operand. The independent orthogonal basis replaces `Bᵀ` at the write and is explicitly rescaled to the same per-site norm. Projection and edit arithmetic use float32. The modified assignment states are cast back to BF16 before block 14. Every other token keeps its original boundary activation. [Archived affine factors](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

An outcome requires the uniquely highest-scoring token for each digit and a valid terminator on the subsequent step. The targeted prefix is extended with the expected digit at each step to measure the exact greedy branch. An incorrect earlier argmax invalidates the answer, regardless of the later scores. A group passes only if all four variants pass. An orthogonal edit matches the transplanted edit's pre-cast norm independently for each assignment position. Replacing both full native assignment states uses the partner permutation as a positive control. [Scoring implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [32B interface](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Frozen 32B intervention | Complete groups of 512 | One to two digits of 747 | Two to one digit of 747 |
|---|---:|---:|---:|
| Borrowed two-operand edit | 358 | 689 | 669 |
| Equal-norm orthogonal edit | 0 | 0 | 0 |
| Swap both full native states | 454 | 711 | 737 |

The borrowed-minus-random difference was 69.92 percentage points, with a paired 95% interval of 66.02 to 73.83 points. Both interventions succeeded in 339 groups. The borrowed edit alone succeeded in 19, the full swap alone in 115 and neither in 39. The full swap is an intervention on the model state and does not provide a guaranteed upper bound on each group. The clean variants were all natively solved. This comparison reuses the earlier prompt panel and calibration. The comparison with 14B changes both the recipient and the interface rule, so it cannot isolate a causal effect of model size. [Portable audit and scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Comparison at 14B](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/numeric_carry_32b_study/verify.py` to execute the candidate Python completions, validate the norms and provenance, and independently recalculate the token-path outcomes. The Studio run took 9 minutes and 24 seconds on an Apple M5 Ultra with 80 GPU cores, 256 GiB unified memory and Metal 4, running macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The run loaded models sequentially. The owner proposed expert transplantation at larger scale. OpenAI Codex designed and ran the test, verified its results and assisted with writing. [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)