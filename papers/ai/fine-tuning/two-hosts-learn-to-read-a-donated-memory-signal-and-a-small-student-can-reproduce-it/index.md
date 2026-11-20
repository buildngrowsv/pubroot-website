---
title: "Two hosts learn to read a donated memory signal, and a small student can reproduce it"
paper_id: "2026-380"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T01:56:42Z"
abstract: "A 261,248-weight student replaced a donor branch using 5,503,872 weights in a frozen hybrid transformer. Balanced register recall was 90.29% with the student and 90.12% with the original donor branch. A matched student trained on teacher outputs from unrelated programs scored 6.98%. Training the receiving block had a large effect in its own right. On a fresh panel the same graft scored 29.08% before receiver training and 90.36% afterward. A separately initialized host rose from 9.26% to 89.88% when trained to receive the original branch. These tests separate access to a signal, learning to read it, and reproducing it with a smaller module."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A 261,248-weight student replaced a donor branch using 5,503,872 weights in a frozen hybrid transformer. Balanced register recall was 90.29% with the student and 90.12% with the original donor branch. A matched student trained on teacher outputs from unrelated programs scored 6.98%. Training the receiving block had a large effect in its own right. On a fresh panel the same graft scored 29.08% before receiver training and 90.36% afterward. A separately initialized host rose from 9.26% to 89.88% when trained to receive the original branch. These tests separate access to a signal, learning to read it, and reproducing it with a smaller module.

![Recipient accuracy before and after adaptation, and recall with the compressed module](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What the receiving block learned

The donor had learned to answer original- and current-value queries about overwritten registers. Its first three blocks and one head in block 4 supplied one 64-number vector per token to the recipient. Earlier work traced specific remembered values across this interface by switching them between paired programs. In the present comparison, the only host weights that changed were the 1,770,240 in block 5, updated on 1,024 batches. The two checkpoints and two inputs to the head yielded four frozen readings on 4,096 fresh programs. [Earlier hybrid and causal test](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered receiver test](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

| Input to transplanted head | Original recipient | Adapted recipient |
|---|---:|---:|
| Trained upstream donor signal | 29.08% | 90.36% |
| Host’s own input | 9.77% | 9.95% |

With the donor present, updating block 5 gained 61.28 percentage points (paired 95% program-bootstrap interval 60.75–61.84). The gain specific to the donor input, after subtracting the host-input effect of the same update, was 61.10 points (60.52–61.69). Among 43,305 qualifying queries, 25,141 were correct only under the joint requirement used here: the adapted donor-input recipient answered correctly, while its zero-update donor-input and adapted host-input counterparts both answered incorrectly. The public ledger contains each program and event identifier and all four predictions. [Program counts, query records and execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-learning)

## Transfer to a recipient with a different starting point

A second equal-width host had been initialized with seed 211 and previously trained with randomized addressing. The donor remained fixed at seed 101. Both arms now used the identical displaced-address mask, fresh matched adaptation batches and a new 1,024-program test panel. Balanced recall rose from 9.26% with the donor branch connected before adaptation to 89.88% after updating block 5 (gain 80.63 points, 95% interval 79.85–81.44). An equally costly branch using untrained upstream weights with the trained donor head reached 10.11%. Replacing the donor input with host input after adaptation yielded 6.79%. The intact donor scored 91.62%. This extends the full-branch result across one independently trained recipient. Initialization and earlier addressing history both differed. [Independent-host protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Predictions aggregated per program](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-host)

## A 261,248-weight replacement

Starting from the first adapted recipient, we froze every host weight. Two width-128, one-block students trained on 4,096 batches to predict the donor branch’s intermediate vectors. Both received the same supplied addresses as the donor. Half the mean squared error was measured at query endpoints and half across all tokens. The objective did not use answer labels. The control rotated entire sequences of teacher vectors among programs within each batch. Distillation from intermediate representations has established precedent. This benchmark asks whether the resulting module can directly replace a particular working interface. [Student and control protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Romero and colleagues, FitNets](https://arxiv.org/abs/1412.6550)

On 1,024 fresh programs the aligned student scored 90.29%, the original branch 90.12% and the shuffled-target student 6.98%. The aligned-minus-original difference was +0.17 points (95% interval −0.06 to +0.41), within the five-point loss tolerance. The matched control establishes the importance of pairing the internal signal with the program that produced it. The replacement used 95.25% fewer branch weights. Median end-to-end batch time fell from 7.73 to 5.69 milliseconds over 20 alternating, warmed, synchronized runs per version on one Apple M5 Ultra (32 programs of 256 tokens per batch). These are observed timings for this hardware and implementation. They compare two hybrids and do not establish a speed advantage over the standalone donor. The student substitution used the first recipient only. [Raw counts and per-batch timing samples](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Student implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The three panels come from one synthetic instruction language with a supplied register-dependent address mask. The uncertainty intervals resample programs within each fit. The CPU audit regenerates labels and counts, reconstructs per-program outcomes from the query ledger, checks paired intervals and derives the parameter and timing contrasts. The owner proposed donor transplantation and training the next host block around it. OpenAI Codex implemented the studies, ran them on the owner’s Studio, verified the outputs and assisted with writing. [Audit code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Recomputed metrics](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)