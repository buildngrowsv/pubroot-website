---
title: "Swapping one attention value exchanges two remembered answers at a displaced address"
paper_id: "2026-372"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T01:23:03Z"
abstract: "A 14.3M-parameter transformer learned to read register memory at a position one event past the original write. Across 1,024 pairs of generated programs differing in one initial value, the model correctly answered both original-value queries in 1,014 pairs. Exchanging a single 64-dimensional attention value at the displaced initialization site made both answers switch to their partner\u2019s correct value in all 1,014 pairs. The same exchange at a later write produced zero such switches. In a separate training run on fresh programs, stable displaced addressing retained an 83.01-percentage-point advantage over equally sparse randomized addressing. The exchange identifies a location through which the specific answer causally influences the final query in the tested model."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A 14.3M-parameter transformer learned to read register memory at a position one event past the original write. Across 1,024 pairs of generated programs differing in one initial value, the model correctly answered both original-value queries in 1,014 pairs. Exchanging a single 64-dimensional attention value at the displaced initialization site made both answers switch to their partner’s correct value in all 1,014 pairs. The same exchange at a later write produced zero such switches. In a separate training run on fresh programs, stable displaced addressing retained an 83.01-percentage-point advantage over equally sparse randomized addressing. The exchange identifies a location through which the specific answer causally influences the final query in the tested model.

![Exchange outcomes and independent training accuracy](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What was changed inside the model

Each program initializes 16 registers, overwrites some of them, then queries an original or current value drawn from 32 possibilities. The earlier study supplied one attention head in block 4 of eight with read positions determined from register identities. Displacing eligible positions by one event throughout training preserved most of the accuracy of exact addressing. The model also had ordinary causal attention through its other heads. The behavioral scores left open whether any particular displaced position supplied the specific answer. Interchange interventions test this by moving an internal value between examples and predicting the resulting output. [Earlier benchmark](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Geiger and colleagues, NeurIPS 2021](https://proceedings.neurips.[REDACTED_SECRET]-Abstract.html)

We froze both trained checkpoints from seed 101. We generated 1,024 new program pairs that differed only in the value used to initialize the register queried at the end. A later write to that register occurred in both programs at event index 40. We exchanged the first head’s 64-value vector between the paired inputs at one allowed position, restricting its effect to the final query. All query vectors, keys, attention weights, other heads and other query computations in block 4 remained intact. Each program supplied its own values at all other positions. A self-exchange reproduced the original logits exactly on the first batch for each intervention. The control exchanged the value at the allowed position associated with the later write. The clean and control inputs differed between partners only at initialization. [Protocol committed before scoring](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## A predicted change of answer

| Frozen checkpoint | Both answers initially correct | Both switched to partner at initialization site | Both switched at later-write site |
|---|---:|---:|---:|
| Trained on displaced addresses | 1,014 / 1,024 | 1,014 | 0 |
| Trained on exact addresses | 1,022 / 1,024 | 1,022 | 0 |

Switch counts require both answers to have been correct before the exchange. Relative to all 1,024 pairs, the displaced initialization exchange gave 99.02 percentage points more double switches than the later-write exchange (paired 95% bootstrap interval 98.34–99.61). The preregistered minimum was 25 points with a positive lower bound. In the two checkpoints, the control preserved both original answers on every initially correct pair. These interventions locate a causal contribution to the final original-value query. The earlier layers that formed the representation and the contributions of other circuits remain open questions. [Raw paired predictions and execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Recomputed counts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Does stable addressing survive another training run?

We independently initialized the stable and random arms with seed 211 and trained them on 512 new matched batches with the original optimizer and update budget. The random arm drew the same number of allowed earlier positions as the displaced arm on every query. We then scored 2,048 fresh programs with 10,835 qualifying original and 10,870 qualifying current queries. Under the preregistered balanced accuracy metric, which gives those two query types equal weight, stable displacement scored 92.62% and random routing 9.61%. The difference was 83.01 points (95% program-paired interval 82.44–83.55), following 83.20 points on the original training draw. The intervals quantify sampling of programs within each training run. The direct exchange was performed on seed 101. [Independent-fit protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Per-program results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-order)

## Reproduction and scope

Both tests use the same synthetic instruction language. Register identities enter the mask explicitly. An interpreter given the same events can solve the task exactly. The scientific question is what a learned model puts at the displaced location and whether that state can change its answer. Variation across larger models and natural code remains unmeasured. The public audit regenerates paired labels from the generator, checks program-level query counts, and reconstructs both bootstrap intervals from the saved predictions. Run `python register_routing/relay_study/verify.py` with NumPy from the repository root. The MLX jobs ran on the owner’s Mac Studio. The owner proposed the research direction and OpenAI Codex implemented the comparisons, operated the experiments, verified the evidence and assisted with writing. [Audit script](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Pinned execution manifest](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)