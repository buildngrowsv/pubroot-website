---
title: "Choosing one write at every hop restores clean and edited recall"
paper_id: "2026-405"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:41:56Z"
abstract: "Direct final-write supervision scored 87\u201388% on every unseen edit type across a convolutional and a recurrent host. It slightly reduced clean accuracy. Changing only how the fitted router followed links gave 100% clean, current-link and obsolete-link accuracy in both hosts on a separate panel. The same inference change worked with the original answer-trained donor and with both independently pretrained native controls. The improvement came from choosing one record at each intermediate step in this structured task."
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Direct final-write supervision scored 87–88% on every unseen edit type across a convolutional and a recurrent host. It slightly reduced clean accuracy. Changing only how the fitted router followed links gave 100% clean, current-link and obsolete-link accuracy in both hosts on a separate panel. The same inference change worked with the original answer-trained donor and with both independently pretrained native controls. The improvement came from choosing one record at each intermediate step in this structured task.

![Accuracy ranges across both hosts and both draws for each training and inference combination](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-comparison.png)

## Train the router to choose the final write

We reused the original convolutional and GRU hosts and the two previously used host draws. All arms used 128 target updates, each with 64 base programs. Within each host draw, the donor and both native initializations each received an original clean-answer fit, a paired-answer fit, and a final-write fit. The final-write objective trains the router to rank the correct final record, while an auxiliary ordinary answer loss keeps the host's payload encoder and decoder involved in training. The same highest-ranked record is read directly at evaluation across conditions. When the trained router produces scores, it sees the structured tables and query, with no answer or target positions. The supervised arm uses additional position labels during training. [Prespecified method](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

On the first fresh panel of 2,048 programs per fit, the supervised donor scored 87.59–87.84% clean, 87.74–88.06% on current edits, and 87.13–87.28% on obsolete edits. It lost 0.42–0.60 percentage points clean relative to the clean-only donor using the same direct readout. Both native controls used the same location supervision in their corresponding arms. The pretrained native placements were within 0.15 points of the donor on the edit endpoints. Every edit query contributes to these rates. The original clean-answer and paired-answer fits exactly reproduced their archived lookup positions and answers on the prior benchmark. [Primary results and all controls](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Primary data audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Select a record before following the next link

The first inference rule combined soft scores along all candidate paths and then chose one final record. The follow-up made a discrete choice after scoring each alias table, carried that record's destination key forward, and selected the final record the same way. Its lookup uses only the router's scores and the table contents. We reconstructed the original fits, verified their saved soft-composed predictions, then evaluated both inference paths on another fresh panel using the same fitted weights. Pointer Networks are an established example of using attention scores to choose positions. Multi-query associative recall provides related measures of memory retrieval. Our comparison isolates composition and readout for this router and task. [Follow-up protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Inference code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Pointer Networks](https://arxiv.org/abs/1506.03134) · [Zoology](https://arxiv.org/abs/2312.04927)

| Training and inference on the second fresh panel | Clean | Current edit | Obsolete edit |
|---|---:|---:|---:|
| Donor, original answer training, soft composition | 88.22–88.37% | 87.45–88.72% | 87.67–88.70% |
| Donor, final-write training, soft composition | 87.79–87.90% | 86.99–88.33% | 87.33–88.18% |
| Donor, original answer training, discrete composition | 100% | 100% | 100% |
| Donor, final-write training, discrete composition | 100% | 100% | 100% |
| Matched pretrained native, either recipe, discrete composition | 100% | 100% | 100% |
| Scratch native, final-write training, discrete composition | 4.84–4.90% | 4.98–5.81% | 4.79–5.05% |

Each fit had 32,768 clean queries and 4,096 queries per edit type. The discrete pretrained models also answered all four edited queries correctly in every program. With zero failures, the empirical program-bootstrap intervals degenerate at 100%; the result is for the sampled programs. Both architectures share the locator interface, and the discrete path returns the visible payload without passing through the trained neural decoder. The benchmark exposes the table boundaries, link destination keys, number of hops and payloads. These results establish a clean-versus-edited retrieval behavior on this structured task. [Follow-up outcomes](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent verification of scores and edited tables](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Reproduction

The Studio ran both fits on CPU, alongside an existing GPU job. Maximum resident memory was 203 MB in the 75-second first comparison and 194 MB in the 50-second follow-up. Each run saves predictions, input witnesses and an exact source receipt. Use Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. Set `STUDIO_JOB_DIR` to a new writable output directory and run `python register_routing/write_supervision.py`, then `python register_routing/discrete_hops.py` after staging the first run's saved test arrays in the documented evidence directory. The standalone NumPy verifiers interpret each released program independently and recalculate the paired scores. [Primary receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Follow-up receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Primary verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Follow-up verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The account owner requested training the router to select the write directly and checking every unseen edit. OpenAI Codex implemented the matched runs, operated the Mac Studio over SSH, checked the evidence and assisted with writing.