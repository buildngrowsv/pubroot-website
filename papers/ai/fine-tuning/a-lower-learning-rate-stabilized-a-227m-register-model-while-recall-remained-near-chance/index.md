---
title: "A lower learning rate stabilized a 227M register model while recall remained near chance"
paper_id: "2026-400"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:15:32Z"
abstract: "Two 227M-parameter models continued from update 512 to update 4,096 at one quarter of the original learning rate. The model with a routed memory head scored 3.69% balanced recall, versus 3.08% for ordinary attention and 3.125% chance. The advantage was 0.61 percentage points (95% program-paired interval 0.04\u20131.17), below the ten-point recovery criterion. The same routed checkpoint continued at its original rate scored 3.64%. Reducing the learning rate enabled the dense fit to finish after two nonfinite attempts at its original rate. Neither wider model learned the task to a useful level under this continuation."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Two 227M-parameter models continued from update 512 to update 4,096 at one quarter of the original learning rate. The model with a routed memory head scored 3.69% balanced recall, versus 3.08% for ordinary attention and 3.125% chance. The advantage was 0.61 percentage points (95% program-paired interval 0.04–1.17), below the ten-point recovery criterion. The same routed checkpoint continued at its original rate scored 3.64%. Reducing the learning rate enabled the dense fit to finish after two nonfinite attempts at its original rate. Neither wider model learned the task to a useful level under this continuation.

![Recall on a common fresh panel after the training continuations](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-recall.png)

## Why resume the exact checkpoints?

At 14.3M parameters a displaced memory head gave 92.26% recall and ordinary attention gave 8.85% after 512 updates. The 227M models saw the same programs and update count, yet the corresponding scores were 4.05% and 3.03% on the original panel. The route occupies one of six heads in the small model and one of 24 at the larger width. Increasing width also increases compute and decreases training tokens per weight. That earlier submission was rejected in automated review because the wider models were poorly trained. This follow-up measures whether further updates repair these particular checkpoints. It leaves initialization, the first 512 updates and relative head bandwidth unchanged. [Original width comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [First review](https://github.com/buildngrowsv/pubroot-website/issues/384) · [Continuation protocol and chronology](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

We restored all weights and Adam moments from update 512. The two arms received the same new 3,584 batches of 8,192 tokens per update (33,554,432 tokens per arm across both stages). One 64-value attention head in block 4 of eight receives a mask based on matching register writes displaced by one event. The ordinary arm has unrestricted causal attention. The original dense rate of 0.00045 twice produced nonfinite loss after the last successful check at update 624. We chose a common lower rate of 0.0001125 after that failure. Independently, the missing routed arm at the original rate completed. The fresh evaluation panel has 1,024 programs with 5,540 qualifying original-value and 5,390 current-value queries. Balanced recall gives equal weight to the two query types. [Quarter-rate counts and receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-quarter-rate) · [Original-rate routed counts and receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-original-routed) · [Dense failure log](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-budget-failure)

| Continuation | Original-value recall | Current-value recall | Balanced recall |
|---|---:|---:|---:|
| Dense at 0.0001125 | 3.38% | 2.78% | 3.08% |
| Routed at 0.0001125 | 4.26% | 3.12% | 3.69% |
| Routed at 0.00045 | 4.03% | 3.25% | 3.64% |

We also scored both original update-512 checkpoints on these same 1,024 fresh programs. The dense model had 3.08% balanced recall both before and after continuation. Routed recall moved from 3.73% to 3.69%, a paired change of −0.045 percentage points (95% interval −0.090 to −0.009). The small routed advantage was already present before continuation. [Matched starting counts and run receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-budget-baseline)

Changing the continuation rate in the routed model changed balanced recall by +0.05 points (paired 95% interval −0.52 to +0.61). The routed models also missed the preregistered 50% original-value threshold for the targeted swap intervention. Further swaps in checkpoints with chance-level recall would have too few correctly answered pairs to localize a memory signal.

## What remains unresolved

The comparison has one training draw and uses synthetic programs. Paired intervals capture held-out program sampling. A width-aware training recipe from the first update, a more competent comparison model, or a different routed fraction could materially change the result. This study retires these checkpoint continuations. It does not estimate the best achievable 227M performance or whether adding a route would help a well-trained large model. All runs used an Apple M5 Ultra with MLX 0.32.4. The owner proposed revisiting the mechanism at scale. OpenAI Codex implemented and ran the continuations, verified the per-program evidence and assisted with writing. [Independent audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Reconstructed counts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Recorded environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)