---
title: "A localized memory head transfers individual answers while most donor skill stays behind"
paper_id: "2026-375"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T01:37:28Z"
abstract: "A 98,304-weight attention-head transplant made a weak transformer solve 831 register-memory queries its matched host missed. Restoring the native head erased 685 of those new solves. The graft also lost 479 queries solved by the matched host. Balanced accuracy increased from 10.45% to 13.68%, below the preregistered five-point transfer threshold and far below the intact donor\u2019s 92.08%. In an independently trained intact donor, exchanging the displaced head\u2019s internal value made 2,016 of 2,020 initially correct program pairs swap answers, versus zero for an equally eligible later-write site. Reliable causal carriage in the donor and partial transfer into a host can coexist on this synthetic benchmark."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A 98,304-weight attention-head transplant made a weak transformer solve 831 register-memory queries its matched host missed. Restoring the native head erased 685 of those new solves. The graft also lost 479 queries solved by the matched host. Balanced accuracy increased from 10.45% to 13.68%, below the preregistered five-point transfer threshold and far below the intact donor’s 92.08%. In an independently trained intact donor, exchanging the displaced head’s internal value made 2,016 of 2,020 initially correct program pairs swap answers, versus zero for an equally eligible later-write site. Reliable causal carriage in the donor and partial transfer into a host can coexist on this synthetic benchmark.

![Memory recall in the host and donor and donor-dependent new answers](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## An independently localized source

In a 16-register synthetic task, one head in block 4 received an attention mask pointing one event beyond earlier initializations and writes to the requested register. The rest of the network learned around that displacement. The original study showed that exchanging one 64-dimensional value between paired programs produced a specific change in the remembered answer. We repeated the intervention in the independently trained seed-211 model on 2,048 fresh pairs. Among all pairs, 2,016 switched both answers to the partner’s value after the initialization-site swap. The later-write swap produced zero double switches and preserved both correct answers in all 2,020 initially correct pairs. The unconditional difference was 98.44 percentage points, with a paired 95% bootstrap interval of 97.90–98.93. The replication localizes the same kind of causal contribution under a second training order. [Original study](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Replication protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Paired raw predictions](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-repeat)

## What crossed into the host

The donor and recipient were eight-block, width-384 transformers descended from the same seed-101 initialization. The donor had trained with the displaced mask, and the weak host had trained with ordinary causal attention. We copied the donor’s first-head query, key, value and output weights into block 4. Both host arms then used the identical displaced mask. Each trained just the following block, 1,770,240 weights, for 1,024 updates on the same fresh program batches. The matched host retained its native head. We evaluated both on 1,024 held-out programs, then replaced the donor head with the native one in the already-adapted graft without retraining. The donor’s upstream blocks stayed outside the host. This experiment tests compatibility of a frozen functional component across models. Model stitching has previously examined compatibility of neural representations using learned connections. [Transplant protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Bansal and colleagues, NeurIPS 2021](https://papers.nips.[REDACTED_SECRET]-Abstract.html)

| Model or intervention | Original value | Current value | Balanced |
|---|---:|---:|---:|
| Full donor | 99.41% | 84.75% | 92.08% |
| Matched adapted host | 14.54% | 6.37% | 10.45% |
| Adapted host with donor head | 22.34% | 5.02% | 13.68% |
| Adapted graft with native head restored | 9.22% | 7.09% | 8.16% |

The 3.23-point balanced improvement over the matched adapted host had a program-paired 95% interval of 2.56–3.94 points. Removing the donor reduced the graft’s score by 5.53 points (4.79–6.28). The rule required at least five points over both controls with positive lower bounds, so the single-head transplant missed its transfer target. The original-value improvement came with lower current-value accuracy. Uncertainty here resamples whole programs for a single transplant training draw. [Per-program results and training receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-surgery)

## Which new answers disappeared?

| Query about an overwritten register | New graft solves versus native host | New solves lost after donor removal | Native-host solves lost with graft | Graft errors fixed by removal |
|---|---:|---:|---:|---:|
| Original value, 5,442 queries | 692 | 583 | 267 | 224 |
| Current value, 5,416 queries | 139 | 102 | 212 | 295 |

The public records identify each query by program and event and give the gold answer and all three predictions. A new solve must be wrong in the independently adapted native host and correct in the graft. A donor-dependent new solve must also become wrong when the native head is restored in that same graft. Restoring it repaired 519 different errors. Both directions matter for interpreting an intervention that changes a model’s predictions. The specific interchange in the intact donor and the transplant are different tests: one changes a computed value inside an otherwise intact model, and the other moves frozen weights into a different network. Whether the host needs the donor’s earlier representations is the next experimental question. [Per-query answers](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npy) · [Recomputed counts and intervals](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Next protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

All fits ran on the owner’s Studio. The account owner proposed testing neural transplants and donor-off controls. OpenAI Codex implemented the experiments and assisted with analysis and writing. The audit regenerates test labels, reconstructs each program’s correct-answer counts from query IDs, recomputes the paired bootstrap and checks the independent interchange against its paired targets. The same-width synthetic setup limits conclusions about transfer between pretrained coding models. [Audit script](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Execution manifest](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)