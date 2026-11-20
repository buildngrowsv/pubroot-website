---
title: "Two independently transferred operands composed without a shortlist on all 512 groups"
paper_id: "2026-458"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:23:03Z"
abstract: "Allowing the 14B host to choose any vocabulary token preserved the two-operand result. Both donor edits made the expected computed digit the unique top prediction on all four variants of 512 of 512 Python programs. Equal-norm random edits passed zero groups. The full host assignment-state exchange passed all 512. The two model checkpoints stayed frozen."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Allowing the 14B host to choose any vocabulary token preserved the two-operand result. Both donor edits made the expected computed digit the unique top prediction on all four variants of **512 of 512** Python programs. Equal-norm random edits passed zero groups. The full host assignment-state exchange passed all 512. The two model checkpoints stayed frozen.

![Both transferred operands, the random edit and full host exchange under both scoring rules](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-open.png)

## What the checkpoint sees and how it is edited

The 512 instances previously passed the four-choice test on an independent panel. Each has two variables and a return expression that adds or subtracts one from the other. Each variable has two possible assigned values. Crossing them gives four versions with four distinct results. Each result is a single token and differs from the operand digits. The prompt ends in an incomplete assertion about the function's result. The two donor functions have independent identifier stems and simply return their assigned integers. The source programs, test prompts and seven-by-seven linear map were reused without any new fitting. Their digests are saved in the result. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Initial composition test and executable example](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Use Qwen2.5-Coder-7B base revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. The two donor activation differences after block 6 are projected and translated independently with the same saved map. Add each translated activation at its corresponding host assignment token after block 10. Continue the host's normal forward pass. The matched control uses an orthogonal random subspace with the same displacement norm at each assignment. The full-state control replaces both host assignment states with those from the corresponding target program. [Map and calibration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Inference and ranking code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## The full-vocabulary endpoint

The original and counterfactual candidate ranks count every score at or above the corresponding token score. Rank 1 therefore requires a unique maximum. A group qualifies if all four original outputs reach rank 1 in the unedited checkpoint. An intervention passes only if all four expected outputs are uniquely first across the model's vocabulary. We also compute the four-choice outcome from the same logits. Neither the donor nor the host receives the four choices as input.

| Intervention | Addition groups, full vocabulary | Subtraction groups, full vocabulary | All groups, full vocabulary | All groups, four choices |
|---|---:|---:|---:|---:|
| Original host | 256 / 256 | 256 / 256 | 512 / 512 | 512 / 512 |
| Both translated edits | 256 / 256 | 256 / 256 | 512 / 512 | 512 / 512 |
| Norm-matched random edits | 0 / 256 | 0 / 256 | 0 / 512 | 0 / 512 |
| Both full host states | 256 / 256 | 256 / 256 | 512 / 512 | 512 / 512 |

Within this panel, the difference from random is +100 points and the paired bootstrap gives +100 at both endpoints. In all four arms, the overall top token was one of the four candidate digits in every prompt, although the scoring did not enforce this. The probes still involve one-step arithmetic, known intervention sites, and one output token. The next planned comparison checks complete numbers that can cross the decimal boundary. [Ranks, logits and dose checks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Run `uv run --with numpy python nested_surgery/numeric_simple_open_study/verify.py` to verify the archive identities, rank invariants, shortlisted winners and group-level metrics. The Studio run took three minutes and 21 seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed donor transplantation and larger controlled tests. OpenAI Codex designed and implemented this comparison, operated the run, verified the results and assisted with writing. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)