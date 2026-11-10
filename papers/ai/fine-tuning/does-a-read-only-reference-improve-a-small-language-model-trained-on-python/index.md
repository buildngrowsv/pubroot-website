---
below_floor: true
quality_floor: 7.0
title: "Does a read-only reference improve a small language model trained on Python?"
paper_id: "2026-363"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T00:46:17Z"
abstract: "Two transformers with 31,992,320 parameters each learned to predict the next byte of CPython source from scratch. On 2,048 held-out windows the model with 64 protected channels scored 1.02012 bits per byte and the writable control scored 1.02210. The fixed-minus-writable difference was \u22120.00197, with a 95% paired package-bootstrap interval of [\u22120.00487, +0.00128]. Exchanging the designated channels between two programs disrupted fewer correct identifier predictions than exchanging an equally wide neighboring group. These data give little evidence for a privileged identifier-memory role at the measured endpoint."
score: 6.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Two transformers with 31,992,320 parameters each learned to predict the next byte of CPython source from scratch. On 2,048 held-out windows the model with 64 protected channels scored 1.02012 bits per byte and the writable control scored 1.02210. The fixed-minus-writable difference was −0.00197, with a 95% paired package-bootstrap interval of [−0.00487, +0.00128]. Exchanging the designated channels between two programs disrupted fewer correct identifier predictions than exchanging an equally wide neighboring group. These data give little evidence for a privileged identifier-memory role at the measured endpoint.

![Paired identifier recalls lost when exchanging designated or adjacent channels](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-outcomes.png)

## Paired training on real code

Each model has ten transformer blocks of width 512 and eight attention heads. At the exit of block 2, the fixed model carries 64 values per token through the next seven blocks. Each intervening block can read those values. In the matched control it can also write new values. Both models use the same initialization, training order, optimizer, and number of stored weights. Initially the projections writing to those coordinates are zero in both. Each arm took 16,384 AdamW updates of 8,192 context bytes, or 134,217,728 training bytes including repeated exposure. [Registered training protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Model and training code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Source files came from a pinned CPython archive with exact-file deduplication and package-based splits. The training partition contained 1,273 files and 26,994,969 bytes. Validation contained 140 files and 3,846,635 bytes. Test contained 70 files and 2,122,472 bytes. Each sample is 512 context bytes from one file and their next-byte targets. Windows can overlap. Similar function bodies, vendored fragments and boilerplate can occur across different packages. Test windows represented 49 package groups. Uncertainty resamples those groups while preserving the pairing of models. [Pinned source and file manifest](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent score audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

| Computation | Validation bits/byte, 4,096 updates | Validation bits/byte, 16,384 updates | Test bits/byte | Test byte accuracy |
|---|---:|---:|---:|---:|
| Fixed reference | 1.03549 | 0.95087 | 1.02012 | 80.90% |
| Writable control | 1.04253 | 0.95167 | 1.02210 | 80.81% |
| Longest matching suffix, with unigram fallback | — | — | 3.24138 | 56.55% |
| Unigram fitted on training bytes | — | — | 4.61996 | — |

The midpoint advantage narrowed at the final checkpoint. Validation fell short of the prespecified 0.02-bit margin and its interval crossed zero, closing the independent-training replication. On the last byte of a repeated identifier-like word, fixed and writable scored 0.07397 and 0.08175 bits per byte. This descriptive subset includes easy completions and cannot identify which channels carry the information. All model contrasts here use one coupled training seed. [Final score record](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Per-window evidence](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

## What happened when the protected values were exchanged?

We generated 1,024 pairs of Python functions. The two members differed only in the last letter of an earlier variable declaration. A later return statement began to repeat that name. Both members had to prefer the correct final byte over the paired alternative. Exchanging hidden coordinates means replacing them at each token with their values from the companion program immediately before the final block. The control exchanges the adjacent 64 coordinates. Exchanging all 512 coordinates had to exchange the predictions exactly. [Registered intervention](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Intervention code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

| Model | Both preferences correct | Correct pairs lost swapping designated 64 | Lost swapping neighboring 64 | Lost swapping all 512 |
|---|---:|---:|---:|---:|
| Fixed | 960 / 1,024 | 16 | 98 | 960 |
| Writable | 922 / 1,024 | 63 | 85 | 922 |

The fixed model recognized more pairs in this generated panel. The designated segment did not meet the prespecified test for selective disruption. Earlier blocks could have already read information into the writable stream. A final-block substitution cannot measure when that earlier transfer occurred. The clean paired measure is a two-candidate preference score. Unrestricted byte top-one accuracy on the fixed model was 1,421/2,048. [Intervention outcomes](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## A lower-parameter comparison

At 4,096 updates two 13,111,808-parameter models processed identical batches. One reused its middle protected block seven times, giving ten block applications. The other used the block once, giving four applications. The deeper computation scored 1.08575 versus 1.08451 validation bits per byte, with paired difference +0.00124 [−0.00261, +0.00452]. Training took 143.2 versus 64.3 seconds on the same Studio in these individual runs. Repeating the block missed its prespecified accuracy threshold and the longer comparison closed. The times include periodic checkpointing. Weight sharing across depth has prior implementations. [Depth-reuse protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Scores](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Universal Transformers](https://arxiv.org/abs/1807.03819)

## Reproduction

The study used an Apple M5 Ultra, macOS 27.2, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The code reads the pinned archive and uses the seeds in the registered plans. The queue manifest records exact git revisions for training, checkpoint continuation and the two post-training experiments. The NumPy verifier reaggregates the saved windows, checks split membership and offsets, reproduces the grouped intervals and individual swap counts, and verifies the complete-state exchange symmetry. Run `python code_reference/verify.py code_reference/results` from the repository root. The release contains per-window and per-pair evidence. Optimizer checkpoints reside on the Studio. [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Versioned run manifest](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The account owner proposed testing a forward-only fixed reference within a neural network. OpenAI Codex implemented the comparisons, ran training over SSH on the owner's Studio, audited the retained evidence and assisted with the manuscript.