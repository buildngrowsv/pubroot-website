---
title: "Two 238M Python models matched or beat a wider baseline, with little difference from carrying an early copy"
paper_id: "2026-419"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T06:46:36Z"
abstract: "The sealed model, which holds 192 early values unchanged until its last block, scored 1.07455 bits per byte on held-out CPython. The 285M model that let all blocks read those fixed values scored 1.08992. The narrower model used 16.31% fewer parameters and improved loss by 0.01537 bits per byte (paired 95% interval 0.00853\u20130.02415). Its equal-size late-copy control scored 1.07655. The sealed-minus-late difference was \u22120.00200 bits per byte (\u22120.00706 to +0.00224). The compact architecture met its efficiency criterion. The early copy missed the prespecified advantage over the same-size control."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The sealed model, which holds 192 early values unchanged until its last block, scored **1.07455 bits per byte** on held-out CPython. The 285M model that let all blocks read those fixed values scored **1.08992**. The narrower model used **16.31% fewer parameters** and improved loss by 0.01537 bits per byte (paired 95% interval 0.00853–0.02415). Its equal-size late-copy control scored **1.07655**. The sealed-minus-late difference was −0.00200 bits per byte (−0.00706 to +0.00224). The compact architecture met its efficiency criterion. The early copy missed the prespecified advantage over the same-size control.

![Held-out CPython loss and paired contrasts for the compact model](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-held-out.png)

## A narrower computation with two choices of exit state

All models process bytes in ten transformer blocks. The wider readable model has 284,720,640 weights and width 1,536 in all blocks. The compact models have 238,269,312 weights. Both keep the original width in blocks 1, 2 and 10, and use width 1,344 in blocks 3 through 9. For the sealed model, the other 192 values leave the computation at block 2 and are concatenated unchanged before block 10. In the equal-size late-copy control, that exit instead receives a second copy of the last 192 working values from block 9. Duplicating those values changes the number of independent inputs at the exit. The equality here is in stored weights and the middle-block compute. [Architecture and qualification protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Model implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Both compact models used matching initial tensors and the same seed-101 training batches, 128-step warmup and peak rate of 0.0004 / 3 with AdamW. All models saw 134,217,728 target bytes over 16,384 updates. The sealed model passed a registered +0.02 bits-per-byte margin against the readable model on validation at 4,096 updates. The two compact runs then restored their weight and optimizer checkpoints and continued. The Studio recorded 69 minutes and seven seconds for the paired continuation with scoring. The 285M paired continuation took 79 minutes and 32 seconds. This elapsed-time comparison includes evaluation and checkpoint overhead. [Validation screen](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Wide reference fits](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Final Studio receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-sealed-width-final/receipt.json)

| Model | Stored parameters | Validation bits per byte | Held-out bits per byte | Held-out next-byte accuracy |
|---|---:|---:|---:|---:|
| Wide, readable early reference | 284,720,640 | 1.00280 | 1.08992 | 80.60% |
| Narrow, sealed early copy | 238,269,312 | 0.99795 | 1.07455 | 80.67% |
| Narrow, late working copy | 238,269,312 | 0.99648 | 1.07655 | 80.61% |

The 2,048 reserved windows use 49 held-out CPython package groups. Lower bits per byte means the model assigns more probability to the actual next byte. The paired intervals resample packages. The planned held-out economic criterion required the upper bound of sealed minus readable to fall below +0.02. It was −0.00853. The attribution criterion required an advantage of at least 0.02 with a negative upper bound versus the equally compact late copy. The point difference was an order of magnitude smaller and its interval crossed zero. For context, the 285M writable model from the sibling study scored 1.08005 on these exact windows. The exploratory differences for sealed and late copy minus that writable model were −0.00550 (−0.01413 to +0.00095) and −0.00350 (−0.00935 to +0.00136), respectively. [Per-window scores](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-sealed-width-final) · [Audited planned and exploratory contrasts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent verification](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

This is one training order at a fixed byte budget. It supports a narrower middle on this task and recipe. The result leaves open how much useful information the early copy carries under changes in data distribution. A matched adaptation test will compare retention on CPython while both 238M checkpoints learn from different Python projects. The owner proposed the sealed forward route and larger experiments. OpenAI Codex implemented and ran the studies on the owner’s Apple M5 Ultra, verified the paired archives and assisted with writing. [Runtime](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Adaptation protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)