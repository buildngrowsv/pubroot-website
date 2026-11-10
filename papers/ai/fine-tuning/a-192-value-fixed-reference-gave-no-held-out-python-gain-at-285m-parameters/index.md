---
below_floor: true
quality_floor: 7.0
title: "A 192-value fixed reference gave no held-out Python gain at 285M parameters"
paper_id: "2026-412"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T05:17:07Z"
abstract: "After equal training exposure, the 285M model that carried a fixed copy through seven blocks scored 1.08992 bits per byte on held-out CPython. The writable control scored 1.08005. A smaller model had shown a 0.00197-bit advantage from the fixed copy, with an interval crossing zero. The wide model\u2019s disadvantage was 0.00987 bits per byte (95% package-paired interval 0.00370\u20130.01614). In an identifier experiment, swapping the wide model\u2019s protected values spoiled two of 935 initially correct pairs. Swapping the adjacent equally wide working slice spoiled 113. A complementary attempt to impose a fixed copy after training also missed its performance and causal criteria."
score: 6.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

After equal training exposure, the 285M model that carried a fixed copy through seven blocks scored 1.08992 bits per byte on held-out CPython. The writable control scored 1.08005. A smaller model had shown a 0.00197-bit advantage from the fixed copy, with an interval crossing zero. The wide model’s disadvantage was 0.00987 bits per byte (95% package-paired interval 0.00370–0.01614). In an identifier experiment, swapping the wide model’s protected values spoiled two of 935 initially correct pairs. Swapping the adjacent equally wide working slice spoiled 113. A complementary attempt to impose a fixed copy after training also missed its performance and causal criteria.

![Held-out fixed-minus-writable losses and paired identifier answers lost after activation exchange](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-held-out.png)

## Training a wide reference

Each model had ten transformer blocks. The fixed model carried its last 192 of 1,536 coordinates forward unchanged from block 2 through seven intervening blocks, where they remained readable. The control could write to those coordinates. Both arms started from matched 284,720,640-parameter initializations and received the same 16,384 AdamW updates and 134,217,728 target bytes per arm. An earlier wide fit failed its 4,096-update learning check at 0.0004. This fit used a peak of 0.0004 / 3 with the same 128-update warmup. It passed validation and then resumed both optimizer states. Its continuation took 79 minutes and 32 seconds on the Studio. [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Learning-rate experiment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Paired scores and receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-width-rate-main)

| Checkpoint size and treatment | Validation bits per byte | Held-out test bits per byte | Held-out next-byte accuracy |
|---|---:|---:|---:|
| 32M fixed | 0.95087 | 1.02012 | 80.90% |
| 32M writable | 0.95167 | 1.02210 | 80.81% |
| 285M fixed | 1.00280 | 1.08992 | 80.60% |
| 285M writable | 1.00486 | 1.08005 | 80.68% |

The 2,048 test windows cover 49 package groups disjoint from training and validation packages. Lower bits per byte means more probability on the observed next byte. The small and large tests share these exact windows. The fixed-minus-writable difference shifted by +0.01184 bits per byte across widths (paired 95% interval +0.00456 to +0.01861). The preregistration required a large-model gain of at least 0.02 bits per byte and a negative upper bound to claim a material improvement. The two widths use different learning rates and one coupled training order. The comparison measures the recorded recipes, with far less data exposure per parameter at the larger width. Its intervals describe variation by package on these trained fits. [Package and score audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Reconstructed results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Did the copy carry a particular answer?

Each of 1,024 pairs contains two executable functions differing at one earlier identifier letter. Each prompt omits the last letter of the same identifier at the return. Both members count as solved only if the model prefers each correct letter to its partner’s letter. Immediately before the final block we exchanged either the designated channels, the adjacent equal-width channels or the whole state. The whole-state exchange reproduced the partner’s logits exactly. In the wide fixed model, the designated exchange caused 111 fewer losses than the neighboring exchange (paired 95% interval 8.89–12.79 percentage points fewer across all pairs). The same contrast in the small fixed model was 82 fewer. Neither partial swap made both members of a correct pair prefer each other’s letter. The whole-state exchange did so for all 935 initially correct pairs in the wide fixed model. This measures sensitivity to an intervention at the last block. The adjacent slice’s larger effect establishes sensitivity, while the whole-state control verifies that this scoring test can detect a complete switch. [Registered exchange](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Raw wide pair scores](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-wide-exchange) · [Independent audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## Add the copy after training

An independent inference-only experiment froze 192 channels in the competent writable model after 4,096 training updates. Calibrating each channel’s movement from block 2 on training data produced one set. We chose a disjoint random set matched in strata of early activation magnitude. On 512 separately sampled validation windows the original model scored 1.02608 bits per byte, the low-drift freeze 1.07488, and the random freeze 1.04572. The low-drift freeze cost 0.04881 bits per byte (95% package-paired interval 0.04377–0.05785) and underperformed the random control by 0.02917. On 482 fresh program pairs solved by both freeze conditions, neither produced any complete switch to the borrowed identifier. This rules out using that drift rule as a selection criterion for a useful fixed reference in this checkpoint. [Registered retrofit protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Independent retrofit audit and raw data](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The owner proposed forward references and their evaluation at larger model sizes. OpenAI Codex implemented the training and causal comparisons, ran the studies on the owner’s Apple M5 Ultra, verified the archives and assisted with writing. The test concerns a particular byte-level model and data budget. The narrower matched-cost test measures a different architectural choice. [Runtime](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Sealed-copy protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)