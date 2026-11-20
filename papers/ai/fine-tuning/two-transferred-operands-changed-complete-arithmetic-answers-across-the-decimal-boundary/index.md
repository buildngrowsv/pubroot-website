---
title: "Two transferred operands changed complete arithmetic answers across the decimal boundary"
paper_id: "2026-462"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:35:23Z"
abstract: "Two edits from independent 7B donor functions gave the correct complete number in all four variants of 512 of 512 fresh Python programs in the frozen 14B host. They passed all 747 one-to-two-digit changes and all 747 two-to-one-digit changes. Equal-norm random edits passed zero groups and zero length-changing cases. Scoring checked the full vocabulary at every answer step and the token ending the number."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Two edits from independent 7B donor functions gave the correct complete number in all four variants of **512 of 512** fresh Python programs in the frozen 14B host. They passed all **747 one-to-two-digit changes** and all **747 two-to-one-digit changes**. Equal-norm random edits passed zero groups and zero length-changing cases. Scoring checked the full vocabulary at every answer step and the token ending the number.

![Correct complete predictions by direction of decimal-boundary crossing](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Task and the two-operand intervention

Each generated function assigns two single-digit values and returns their sum. The prompt ends with an incomplete assertion about that sum. Each assignment has two alternatives, giving four distinct outcomes, at least one below ten and one above or equal to ten. None of the four outputs equals an operand. Executing the candidate assertions in CPython verifies the answer in every version. The untouched Qwen2.5-14B base checkpoint solved all 128 groups on the native screen at indices 110000–110127. The main panel used independent indices 111000–111511. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Host and donor prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Separate direct-return functions at indices 112000–112511 and 113000–113511 supply the two operand alternatives to Qwen2.5-Coder-7B. Their identifier stems and surrounding code differ from the host's. Each donor pair supplies a difference at its assignment after block 6. Translate the two differences separately with the same saved seven-by-seven map and add each at its host assignment after block 10. The paired full-state comparison copies both host assignments from the target version. Its counterpart uses two orthogonal random edits, each matched to the corresponding translated edit's norm. The donor base revision is `0396a76181e127dfc13e5c5ec48a8cee09938b02`. The host base revision is `97e1e76335b7017d8f67c08a19d103c0504298c9`. Neither checkpoint nor the saved interface was updated. [Map and calibration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Intervention code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Verifying the complete number

Qwen tokenizes these one- and two-digit answers as one token per digit. We append the expected digit sequence solely to check each causal prefix in parallel. For every digit, the model's unique largest vocabulary logit must identify that digit when conditioned on the prompt and the preceding digits. After the last digit the greedy token must end the sequence, start a newline, or start a comment. A sequence satisfying these checks is the exact number the model would produce by greedy next-token selection. The input at one step never includes the expected token at that step or any later token in its attention. This is verified greedy output on each trajectory. The archived terminators independently decoded to a double newline or the end-of-text token. The study does not compare sampling strategies.

| Intervention | All four expected outputs | One to two digits | Two to one digit |
|---|---:|---:|---:|
| Both translated donor edits | 512 / 512 | 747 / 747 | 747 / 747 |
| Norm-matched random edits | 0 / 512 | 0 / 747 | 0 / 747 |
| Both full host assignment states | 512 / 512 | 747 / 747 | 747 / 747 |

All 512 groups qualified in the unedited host. Expected answers changed length in 1,494 of the 2,048 prompt variants. The group-level advantage over random was +100 points with the same two bootstrap bounds, reflecting uniform outcomes on this panel. The experiment uses short generated addition programs, known activation sites, and two donor runs per operand. [Raw top-token trajectories and edit doses](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Run `uv run --with numpy python nested_surgery/numeric_carry_study/verify.py` to execute the programs and recompute the exact sequence and grouping checks. The Studio run took four minutes and 18 seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed expert transplantation and the study of protected internal references. OpenAI Codex designed and operated the experiment, checked the artifacts and assisted with writing. [Pinned execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)