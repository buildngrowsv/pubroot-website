---
title: "Does one frozen router help two different hosts follow a chain of writes?"
paper_id: "2026-392"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T02:45:40Z"
abstract: "The same frozen locator worked in both a convolutional host and a gated recurrent host. Across four fits it answered 58.6\u201363.3% of held-out queries, versus 2.2\u20132.4% for native routers trained from scratch at the same target budget. Independently pretrained native routers, given the same one-hop source exposure as the donor and allowed to adapt on the target, scored 69.0\u201373.5%. All four strong controls beat the frozen transplant. The experiment isolates a benefit of reusing the learned locator under scarce target training, with additional value from a native route that can adapt."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The same frozen locator worked in both a convolutional host and a gated recurrent host. Across four fits it answered 58.6–63.3% of held-out queries, versus 2.2–2.4% for native routers trained from scratch at the same target budget. Independently pretrained native routers, given the same one-hop source exposure as the donor and allowed to adapt on the target, scored 69.0–73.5%. All four strong controls beat the frozen transplant. The experiment isolates a benefit of reusing the learned locator under scarce target training, with additional value from a native route that can adapt.

![Four matched held-out comparisons across two recipient architectures](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-comparison.png)

## From one read to a chain

The source locator had learned to choose among versions of a write. We reconstructed the original seed-101 model and matched its archived top source positions and answers exactly on all 16,384 earlier test queries. We then froze its 2,306 routing weights and used them repeatedly to follow two alias tables and select an initial or latest register write. Alias maps had current and obsolete edges. Every program used independently shuffled record order and distinct random payloads. The router received key symbols and order, and the recipient embedded and decoded its own payloads. Soft composition of the routing rows joined the lookups. Table boundaries and the number of lookups were supplied. No ground-truth address entered model input or loss. An interpreter using the supplied tables solves the task exactly. [Prespecified plan](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Earlier one-hop evidence](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

One host used a two-stage temporal convolution and the other a gated recurrent unit. Each had its own value vocabulary. Within a host draw, all arms used identical host initialization, 128 target updates of batch size 64, and the same train and test programs. The stronger native routers were independently initialized and pretrained on the donor's exact 768 one-hop batches before receiving these same target updates. The frozen donor was identical in all four fits. Groups of 1,024 held-out programs had 40 records in each alias table and 60 final writes, up from 24 and 36 in training. [Pointer Networks](https://arxiv.org/abs/1506.03134) · [Associative recall benchmarks](https://arxiv.org/abs/2312.04927)

| Host and draw | Native from scratch | Frozen graft | Native with matched pretraining | Graft minus pretrained native, 95% interval |
|---|---:|---:|---:|---:|
| Convolution, 503 | 2.45% | 58.84% | 69.37% | −10.52 pp [−11.04, −10.02] |
| Convolution, 607 | 2.37% | 58.59% | 68.98% | −10.39 pp [−10.89, −9.89] |
| GRU, 503 | 2.25% | 63.17% | 73.46% | −10.28 pp [−10.78, −9.80] |
| GRU, 607 | 2.38% | 63.26% | 73.30% | −10.03 pp [−10.50, −9.55] |

The table reports 16,384 query decisions per fit. Intervals resample whole programs within each fit. Differences in source initialization and the ability to adapt jointly both enter the strong comparison. It does not isolate how the exact same transplanted weights would perform if fine-tuned. [Per-arm counts, intervals and familiar-length results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## What the host actually used

Rolling the final read scores with the trained host held fixed reduced accuracy to 0.72–0.98%. Among clean correct answers, edited current links prompted the correct new answer in 63.3–69.6% of evaluated cases. The matched obsolete-link edit preserved 81.1–83.9%. The prespecified gate required both causal fractions to reach 90%, plus an advantage over both native controls in every fit. It closed. The evidence supports cross-host use of a learned route in this structured task, with limited reliability under edits. [Per-program outcomes](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

An input audit caught 29 or 36 obsolete-link control programs per panel where the first generator repeated the existing destination. The corrected run makes one real edit in every control. It reproduced every clean prediction, and only the corrected intervention counts enter this report. The corrected run took 26.60 seconds on the Mac Studio CPU, peaking at 168 MB resident memory. It ran with Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The experiment saves small prediction arrays and no weight checkpoints. Set `STUDIO_JOB_DIR` to a new writable directory and run `python register_routing/chain_transfer.py` from the repo root. Audit with `python register_routing/verify_chain_transfer.py register_routing/chain_study/results register_routing/address_study/results/paired-101.npz`. [Corrected receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Original comparison record](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The account owner proposed comparing the same frozen router across different hosts with matched training budgets. OpenAI Codex implemented and operated the experiment on the owner's Studio, audited the predictions and assisted with writing.