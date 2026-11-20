---
title: "A distilled memory signal switches specific answers in a second trained recipient"
paper_id: "2026-386"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T02:26:14Z"
abstract: "A frozen 261,248-weight memory module replaced a 5,503,872-weight donor branch in a second, independently initialized 14.3M-parameter recipient. The recipient had previously learned to read the full donor. With no further training it achieved 90.38% balanced register recall with the compact module and 90.03% with the full branch. Exchanging one internal value between two programs made their answers switch to each other\u2019s correct answer in 2,018 of 2,022 initially correct pairs. Swapping a value at the later-write control site produced zero such switches. The result establishes portability across two trained recipients with the same interface and supplied addressing rule."
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A frozen 261,248-weight memory module replaced a 5,503,872-weight donor branch in a second, independently initialized 14.3M-parameter recipient. The recipient had previously learned to read the full donor. With no further training it achieved 90.38% balanced register recall with the compact module and 90.03% with the full branch. Exchanging one internal value between two programs made their answers switch to each other’s correct answer in 2,018 of 2,022 initially correct pairs. Swapping a value at the later-write control site produced zero such switches. The result establishes portability across two trained recipients with the same interface and supplied addressing rule.

![Specific answer switches using the compact and full modules in the second recipient](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What changed inside the recipient

The task distinguishes original and current values for registers overwritten within a program. The original teacher used the donor’s first three blocks and the first 64-value attention head in block 4. The student was trained once on that branch’s internal vectors. In an earlier independent initialization, the second recipient learned with the full donor branch by updating block 5 for 1,024 batches. Before that training it scored 9.26%. We froze this recipient and directly substituted the original student. It shares the trained teacher’s output projection and externally supplied displaced address pattern. These features are part of the interface being tested. [Independent-recipient protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Distillation and portability protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Earlier small-model result](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

On 1,024 new programs the compact-minus-full difference was +0.35 points (95% program-paired interval +0.07 to +0.62), meeting the prespecified five-point noninferiority margin. A separate panel of 2,048 program pairs differed in one initial value. For the final original-value query, we exchanged a single internal 64-value vector at the displaced initialization site between the two programs. A matched intervention changed the later-write site instead. Self-exchanges reproduced the original logits on the initial verification batch. This is an interchange intervention, a method with an established causal interpretation for specified counterfactuals. [Paired predictions and receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-portability) · [Geiger et al., 2021](https://proceedings.neurips.[REDACTED_SECRET]-Abstract.html)

| Frozen source | Both answers initially correct | Both switched at initialization site | Both switched at later-write site |
|---|---:|---:|---:|
| Compact student | 2,022 of 2,048 | 2,018 | 0 |
| Full donor branch | 2,027 of 2,048 | 2,017 | 0 |

For the compact student, the source minus later-write double-switch rate across **all** pairs was 98.54 points (95% paired interval 98.00–99.07). The test validates a specific signal in a recipient trained on that interface. It does not establish portability to a host with an unrelated internal representation. In the separately tested 227M recipient that retained its own output projection, only four of 333 new solves disappeared on donor removal. [Independent reconstruction](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Wider recipient](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

## Reordering unrelated events exposes a boundary

A separate evaluation froze the original trained-prefix hybrid and the exact- and displaced-address donors. It used 2,048 fresh programs and preserved every register’s event order and the final event while interleaving different registers. The interpreter confirms the two schedules have the same answers for every query. Reordering alters sequence positions, distances and neighboring events together. Balanced accuracy fell by 13.09 points for the hybrid (95% interval 12.32–13.84), 13.86 for the displaced donor and 13.83 for the exact-address donor. Hybrid minus exact schedule penalty was −0.74 points (−1.63 to +0.16). The observed sensitivity extends to the exact-address control. These are different frozen checkpoints from the compact-student transfer test. [Schedule protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Event permutations and counts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

The two panels use synthetic operations and one trained student. Their paired intervals describe test-program sampling. The owner proposed the transplant research. OpenAI Codex implemented and ran the comparisons, reconstructed the released measurements and assisted with writing. The experiments used MLX 0.32.4 on an Apple M5 Ultra. [Recorded runtime](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Audit output](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)