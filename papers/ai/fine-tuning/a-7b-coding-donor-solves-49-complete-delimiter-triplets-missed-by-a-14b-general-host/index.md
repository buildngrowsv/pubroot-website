---
below_floor: true
quality_floor: 7.0
title: "A 7B coding donor solves 49 complete delimiter triplets missed by a 14B general host"
paper_id: "2026-398"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:08:11Z"
abstract: "On 256 groups of three executable Python repairs, Qwen2.5-Coder-7B solved all three members of 49 groups. Qwen2.5-14B solved zero complete groups and chose a colon on 762 of the 768 individual prompts. The difference was 19.14 percentage points (95% paired interval 14.45\u201323.83). This qualifies a task for a controlled transplant under the registered rule. The host\u2019s response bias and the coding donor\u2019s specialized pretraining bound what this comparison establishes."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On 256 groups of three executable Python repairs, Qwen2.5-Coder-7B solved all three members of 49 groups. Qwen2.5-14B solved zero complete groups and chose a colon on 762 of the 768 individual prompts. The difference was 19.14 percentage points (95% paired interval 14.45–23.83). This qualifies a task for a controlled transplant under the registered rule. The host’s response bias and the coding donor’s specialized pretraining bound what this comparison establishes.

![Complete triplets and individual scores in both checkpoint pairs](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## A single changed character determines the repair

Each prompt contains a nested expression, with an earlier parenthesis, square bracket or brace left open. Each triplet changes only that opening character. The suffix stays identical across all 768 prompts. The four candidate tokens are a closing parenthesis, square bracket, brace or colon. We compare their native next-token logits at the fill-in-the-middle position. In each program exactly one choice parses and passes the supplied executable check. The count of complete triplets rewards a model for responding appropriately to all three changes. The parser itself solves every example. This measures a narrow neural repair behavior under one input format. [Archived prompts and original checkpoint comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Method of fill-in-the-middle training](https://arxiv.org/abs/2207.14255)

| Frozen checkpoint | Correct individual repairs / 768 | All three correct / 256 |
|---|---:|---:|
| 0.5B coding donor, earlier comparison | 503 | 7 |
| 1.5B general host, earlier comparison | 61 | 0 |
| 7B coding donor | 555 | 49 |
| 14B general host | 6 | 0 |

There were 49 donor-only groups and zero host-only groups for the larger checkpoint pair. The preregistered gate required at least 25 donor-only groups, a ten-point net advantage, and a positive lower confidence bound. The 7B coder chose the four candidates 273, 250, 49 and 196 times in the declared order. The 14B host chose them 5, 0, 1 and 762 times. This strongly motivates a native host trained on the same repair examples as the graft. The qualification set was previously used with smaller checkpoints. There is one model per checkpoint condition, and pretraining, specialization, and size differ between conditions. No alternative prompting format was evaluated. [Preregistered thresholds](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Coding checkpoint](https://huggingface.co/Qwen/Qwen2.5-Coder-7B) · [General checkpoint](https://huggingface.co/Qwen/Qwen2.5-14B)

## What would count as a transplant?

The next experiment replaces the feed-forward module in one-based block 27 of the 14B host with the frozen final feed-forward module from the 7B coder. Only host block 28 receives task updates. It compares six matched controls and a separate 256-group panel, then tests which new complete solves disappear on donor removal and native restoration. The current result establishes the standalone donor advantage needed to justify that experiment. [Surgery and removal protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

The scoring ran on the owner's Apple M5 Ultra in original model precision. Reproduction uses the exact two model revisions in the result, plus the released prompt set and four logits per example. Run the independent Python and NumPy audit to rederive the labels, whole-group scores, intervention locations in the prompts, qualification decision and paired intervals. The owner proposed finding a smaller donor that beats its host on real executable repairs. OpenAI Codex implemented and operated the experiments, audited the outputs and assisted with writing. [Raw logits, gate decision and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recomputed counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)