---
title: "Do coding models track indentation when all four repairs are executable?"
paper_id: "2026-353"
author: "buildngrowsv"
category: "ai/llm-benchmarks"
date: "2026-11-19T22:51:56Z"
abstract: "A smaller coding model solved 63 of 256 Python indentation repairs and a larger general-purpose model solved 64. All four candidates compiled. Changing only the expected outputs in four visible assertions changed which indentation was correct. The larger model chose four spaces in every problem, and the coding model kept its choice unchanged in 59 of 64 four-problem sets. The coding donor missed the registered discovery criterion for transplantation. We stopped before opening the validation and final panels or training block 28 on this task."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A smaller coding model solved **63 of 256** Python indentation repairs and a larger general-purpose model solved **64**. All four candidates compiled. Changing only the expected outputs in four visible assertions changed which indentation was correct. The larger model chose four spaces in every problem, and the coding model kept its choice unchanged in 59 of 64 four-problem sets. The coding donor missed the registered discovery criterion for transplantation. We stopped before opening the validation and final panels or training block 28 on this task.

![Model choices at each possible indentation](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Why test indentation?

A previous block-27 transplant in this research series used a smaller Qwen coding donor that clearly outperformed the host on delimiter repairs. The original parser could solve those tasks, and every task-trained control eventually reached 100%. All new solves survived removal of the donor. A later variable-binding task made every option executable but the frozen donor's validation lead over an adapted host was too small to justify surgery. Indentation provides another small, checkable test. A single whitespace token can leave the entire program valid while changing which inputs cause an addition to execute. Fill-in-the-middle pretraining supplies the two-sided code interface. [Earlier transplant and removal study](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Variable-binding study](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Fill-in-the-middle training](https://arxiv.org/abs/2207.14255) · [Qwen2.5-Coder](https://arxiv.org/abs/2409.12186)

Each function has three nested guards or loops and a running total. The omitted token inserts four, eight, twelve or sixteen spaces before an addition. The repaired line may execute once per call, under the first guard, or inside deeper control flow. For a fixed program we generate four versions of the visible assertions, one for each desired scope. Each version uses the same four public input vectors and differs only in expected outputs. The public examples jointly distinguish every pair of candidate programs. Twelve separate input-output cases grade each repair. We selected those inputs independently of the choice of the desired scope but required both the visible and concealed sets to distinguish all four scopes. Program family is the ordered triple of control-flow forms. Families assigned to discovery do not appear in any other split. [Generator](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Prospective design](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

## The discovery result

Both frozen models received identical native infill input tokens. We ranked four eligible single-token continuations without sampling. The token IDs for four, eight, twelve and sixteen spaces were 257, 260, 1797 and 338 in both tokenizers. The base host was Qwen2.5-1.5B and the smaller base donor was Qwen2.5-Coder-0.5B. The same revision-pinned checkpoints and inference interface were used in the preceding studies. One full stop/go screen, including model loading and forward scoring, took 1.38 seconds for the host and 0.56 seconds for the donor on the Apple M5 Ultra. These measurements describe a warm local setup and do not establish a deployment latency difference. [Model pins](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Scoring implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Outcome | General host | Coding donor |
|---|---:|---:|
| Correct out of 256 | 64 | 63 |
| Correct exclusively for this model | 63 | 62 |
| Four scopes all correct out of 64 quartets | 0 | 0 |
| Choice constant across the quartet | 64 | 59 |
| Choices at 4 / 8 / 12 / 16 spaces | 256 / 0 / 0 / 0 | 8 / 24 / 198 / 26 |

The standalone solve-rate difference was −0.39 percentage points in favor of the host when expressed as donor minus host. The paired 95% interval from resampling the eight discovery families was [−1.17, 0.00] points. Confidence about other program families or other infill formats is limited. The discovery gate required a donor lead of at least five points. In seven families both models got eight of 32 correct; the remaining family accounted for the one-solve difference. A balanced answer distribution means that always choosing the same depth produces exactly 25%. An oracle choosing between model outputs could reach 126/256 here. The discordant solves largely reflect different indentation preferences. Their mere existence does not identify a useful specialist. [Disagreement and family counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Per-problem logits](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

An independent AST-based verifier executed all 1,024 supplied candidate programs against the visible assertions and hidden cases, recovered a unique matching patch for all 256 problems, and reproduced both model solve counts from the saved logits. The executable visible-example selector gets 256/256 and requires no model training. The four-way constrained interface measures a narrow ability; it does not score free-form Python generation. The result closes this screen for the chosen pair of frozen models. The other splits and transplant interventions were left untouched, so there is no new causal donor-off result on this task. [Prompts and hidden inputs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verification and choice counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Reproduction

Use the repository's original environment and cached pinned weights. The Studio ran the frozen score over SSH. Only the first script needs model inference. The verifier consumes public data and requires NumPy, and the figure additionally requires Matplotlib.

```sh
python indentation/screen_donor.py
python indentation/verify.py
python indentation/figure.py
```