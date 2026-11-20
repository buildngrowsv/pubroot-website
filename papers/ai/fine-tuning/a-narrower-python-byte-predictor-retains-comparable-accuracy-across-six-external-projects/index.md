---
title: "A narrower Python byte predictor retains comparable accuracy across six external projects"
paper_id: "2026-381"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T01:58:59Z"
abstract: "Two transformers pretrained on CPython adapted for the same 8,192 updates to NumPy, SciPy and Matplotlib. The compact model, carrying an early 64-channel state past seven narrower blocks, used 26.83M parameters versus 31.99M for its full-width counterpart. On six disjoint external projects it scored 1.39958 bits per byte versus 1.39934 for the larger model. The paired difference of +0.00024 had a 95% within-project file-bootstrap interval of \u22120.00295 to +0.00342. All six project point differences were below the prespecified 0.02 loss margin. Both models improved on the new domain while losing accuracy on the original CPython test windows."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Two transformers pretrained on CPython adapted for the same 8,192 updates to NumPy, SciPy and Matplotlib. The compact model, carrying an early 64-channel state past seven narrower blocks, used 26.83M parameters versus 31.99M for its full-width counterpart. On six disjoint external projects it scored 1.39958 bits per byte versus 1.39934 for the larger model. The paired difference of +0.00024 had a 95% within-project file-bootstrap interval of −0.00295 to +0.00342. All six project point differences were below the prespecified 0.02 loss margin. Both models improved on the new domain while losing accuracy on the original CPython test windows.

![Sealed minus readable loss on six held-out numerical Python projects](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## Transfer protocol

Both models began with their seed-101 CPython checkpoints after 16,384 updates. The full readable arm had 31,992,320 weights. Its seven middle blocks could read the 64 protected coordinates. The sealed arm stored 26,830,464 weights, worked on 448 channels in the middle, and transported the other 64 directly to the last block. From these starting points we reset AdamW and sampled the same 8,192 adaptation batches in the same order, with 8,192 context bytes per update. Each update selected one training project uniformly and then sampled valid byte offsets from its eligible source files. Neither arm saw the six evaluation projects during adaptation. [CPython study](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered transfer protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Exact-version source archives were pinned by SHA-256. We read Python package source files of at least 513 bytes, excluded listed test and vendored paths and removed exact file duplicates against eligible CPython source and previously scanned libraries. The nine libraries contributed 1,628 eligible files. Six held-out libraries contributed 512 fixed windows each. Validation independently reconstructed all 3,072 window identities and offsets and checked the pairing at both checkpoints. Similar code and overlapping windows can remain. [Archive pins](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [File manifest, predictions and receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

| Held-out project | Sealed minus full, bits per byte after adaptation |
|---|---:|
| pandas | −0.00445 |
| NetworkX | −0.00207 |
| xarray | +0.00393 |
| seaborn | +0.00893 |
| mpmath | −0.00231 |
| joblib | −0.00261 |

Each project has equal weight in the reported mean. Before adaptation the compact and full models scored 1.59122 and 1.59413 bits per byte. Their post-adaptation scores were 1.39958 and 1.39934. The registered test required the upper bound for the mean penalty below 0.02 plus at least five project differences below 0.02. All six passed. The interval resamples files within fixed projects. It does not estimate variation across arbitrary future projects or training seeds. In particular, this comparison combines narrowing with the protected early reference. The conditional matched-size working-only arm addresses the contribution of the reference. [Independent reconstruction and intervals](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Audit implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## What adaptation cost on the original distribution

On exactly the original 2,048 CPython windows the compact model’s loss increased by 0.21198 bits per byte and the larger model’s by 0.21604. These measurements show a change in prediction quality under this budget and training mixture. A separate registered test replaces every eighth adaptation batch with original CPython training data to measure how much of the loss can be recovered at fixed compute. [Rehearsal protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The user proposed the protected-reference research direction. OpenAI Codex implemented the comparison and corpus controls, trained the models on the owner’s Studio, verified the data and assisted with writing. Reproduction uses the package versions, archived model specifications, deterministic batch seeds and per-window score files. [Training code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Version-pinned queue](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)