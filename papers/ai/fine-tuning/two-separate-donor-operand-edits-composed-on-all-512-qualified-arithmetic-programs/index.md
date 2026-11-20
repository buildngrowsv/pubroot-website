---
title: "Two separate donor operand edits composed on all 512 qualified arithmetic programs"
paper_id: "2026-452"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:14:36Z"
abstract: "Two changes from separate 7B donor functions composed in a frozen 14B host. Both edits together gave all four expected answers on 512 of 512 generated addition and subtraction groups. The left-only and right-only edits also passed every group. Applying two equal-norm random changes passed zero groups. The untouched host scored all four variants correctly on 128 qualification groups and all 512 held-out groups."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Two changes from separate 7B donor functions composed in a frozen 14B host. Both edits together gave all four expected answers on **512 of 512** generated addition and subtraction groups. The left-only and right-only edits also passed every group. Applying two equal-norm random changes passed zero groups. The untouched host scored all four variants correctly on 128 qualification groups and all 512 held-out groups.

![Intervention outcomes on addition and subtraction](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-operands.png)

## A two-operand task with a competent baseline

The previous expression included multiplication, a constant, and two source variables. The unmodified model solved just eight of 1,024 complete groups. This revision uses direct addition or subtraction of two independent variables. The initial screen must yield at least 20 complete groups out of 128 before any transplant run. It used indices 92000–92127. The 512 evaluated groups use independent indices 93000–93511, 256 each for addition and subtraction. The two source values in each position form a 2-by-2 crossing. All four correct answers are distinct single-digit tokens, and none is one of the four operand digits. In one archived group, the left operands are 1 and 2 and the right operands are 6 and 3. The four sums are 7, 4, 8 and 5. Starting from 1 and 6, a left-only edit targets 8, a right-only edit targets 4, and both edits together target 5. CPython verifies every candidate in every saved program. [Registered native gate and composition protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Earlier benchmark failure](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Saved programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Transferring the two operands

Use Qwen2.5-Coder-7B base revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. Each pair of source variants is read by the donor in its own separate function. The donor function returns the source number directly. Each function uses its own variable and scratch lines. For each operand, project the donor declaration difference after block 6 onto seven fitted directions and map it into seven fitted host directions. The exact same seven-by-seven map from the single-operand study is reused for both positions. Insert each change separately at its corresponding host assignment after block 10. The 14B model evaluates the edited program with its own remaining layers. All checkpoints and the map are frozen. [Saved map and calibration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Inference implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Host condition | Addition groups | Subtraction groups | All groups |
|---|---:|---:|---:|
| Native, original outcomes | 256 / 256 | 256 / 256 | 512 / 512 |
| Left donor edit only | 256 / 256 | 256 / 256 | 512 / 512 |
| Right donor edit only | 256 / 256 | 256 / 256 | 512 / 512 |
| Both independent donor edits | 256 / 256 | 256 / 256 | 512 / 512 |
| Norm-matched random edits at both sites | 0 / 256 | 0 / 256 | 0 / 512 |
| Full host assignment states at both sites | 256 / 256 | 256 / 256 | 512 / 512 |

Every success requires the prespecified answer to win strictly against the other three logits in all four variants. The both-operand arm's mean target margin was +4.07, versus +4.09 for the full host exchange and −4.74 for the random edits. The group bootstrap interval for the difference over random had both endpoints at +100 percentage points, as every group had the same result. These programs span 44 possible operand-pair recipes before order shuffling. The experiment uses known source sites, two counterfactual donor passes per site, and four allowed next-token completions. Its successful composition applies to direct one-step addition and subtraction in these generated programs. [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recomputed results](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Complete scores and doses](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

Run `uv run --with numpy python nested_surgery/numeric_simple_study/verify.py` to execute the programs and derive every target independently. The run took five minutes and seven seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5 on the owner's Apple M5 Ultra. The owner proposed expert transplantation. OpenAI Codex designed and operated the experiment, checked the outcomes and assisted with the writing. [Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)