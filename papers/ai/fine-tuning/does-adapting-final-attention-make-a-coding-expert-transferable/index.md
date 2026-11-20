---
title: "Does adapting final attention make a coding expert transferable?"
paper_id: "2026-357"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T00:04:22Z"
abstract: "Allowing a smaller coding donor to adapt its entire final block gained an average of 0.13 percentage points over training its feed-forward module alone on 512 fresh Python repairs. The paired 95% interval was \u22121.37 to +1.17 points. The larger host solved 172\u2013181 repairs, compared with 136\u2013142 for the fully adapted donor. Restoring the donor's original feed-forward weights in one run erased 124 correct repairs and rescued 112 others. A simple lookup reading the four required outputs and two numerical constants solved 419/512 without analyzing the program's loops or conditions. The proposed feed-forward graft failed qualification."
score: 7.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Allowing a smaller coding donor to adapt its entire final block gained an average of **0.13 percentage points** over training its feed-forward module alone on 512 fresh Python repairs. The paired 95% interval was **−1.37 to +1.17 points**. The larger host solved 172–181 repairs, compared with 136–142 for the fully adapted donor. Restoring the donor's original feed-forward weights in one run erased 124 correct repairs and rescued 112 others. A simple lookup reading the four required outputs and two numerical constants solved **419/512** without analyzing the program's loops or conditions. The proposed feed-forward graft failed qualification.

![Confirmation solves and changed answers under feed-forward restoration](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-restoration.png)

## What changed in this experiment?

A preceding study trained only the final feed-forward module of Qwen2.5-Coder-0.5B, while the native Qwen2.5-1.5B control could adapt its entire final block. That asymmetry left open whether giving the donor the same access to attention would create a useful expert. Here we trained a single additional condition, the smaller donor's whole block 24, and recombined its original and trained components inside the donor. The question is relevant to model stitching because a component that works in one surrounding representation may depend on that context. These measurements are before any insertion into a larger host. [Preceding study](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Revisiting Model Stitching](https://arxiv.org/abs/2106.07682) · [Qwen2.5-Coder report](https://arxiv.org/abs/2409.12186)

Four indentation tokens produce four executable Python programs. An addition runs at one of four depths in three nested guards or loops. For each program we change the expected outputs in four public assertions to request each possible repair in turn. The four prompts therefore have identical program text, inputs and candidate tokens. Every patch must also pass twelve hidden examples. Each visible and hidden set distinguishes all four candidate behaviors. Executing all four candidates against the public assertions achieves 512/512 on each panel.

Training reused the preceding study's exact 1,536 labeled prompts, 128 calibration prompts, optimizer and data orders 101, 211 and 307. Each fit used 96 Adam steps at 0.00002, batch size 16. Minimum four-choice calibration loss selected among steps 0, 8, 32 and 96. Each selected the final step. The adapted donor block has 14,912,384 parameters, including 13,074,432 feed-forward weights. The archived adapted host block has 46,797,824. We verified the archived model files against their published hashes. The newly recorded fitting sections took 2.12, 1.21 and 1.21 seconds on the M5 Ultra. The full primary script, including data preparation, training and evaluation, took 53.6 seconds before replay. These are measurements of this cached setup. [Prospective protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Selection and parameter counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Runtime](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Two independently generated panels

We registered the check before generating held-out scores. Each of the new ordered triples of control-flow forms contains one previously unused form, an equality-to-zero guard or a loop bounded by the input plus one, together with two original forms. We drew two disjoint sets of sixteen families. Each family supplied eight independent layouts and four requests per layout. This produced 512 qualification repairs and 512 confirmation repairs. The models had not received these families in the experimental training set. Python's language constructs themselves are familiar. The gate was recorded on qualification before scoring confirmation.

We measured all four recombinations of original and adapted expert weights with original or adapted attention-side weights. The attention side includes self-attention and both block normalizations. Every other donor parameter stayed fixed. The gate required the full donor and the jointly trained expert with original attention to each beat the adapted host by five points, and restoring the original expert inside the adapted donor to cost at least five points. Each contrast also needed a positive lower paired family-bootstrap bound in every training order. [Qualification scores and intervals](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-summary.json) · [Gate decision](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

| Method on the fresh confirmation panel | Order 101 | Order 211 | Order 307 |
|---|---:|---:|---:|
| Frozen donor | 126 | 126 | 126 |
| Donor expert trained alone in previous study | 141 | 139 | 133 |
| Adapted attention and norms with original expert | 130 | 130 | 132 |
| Jointly trained expert with original attention and norms | 139 | 137 | 142 |
| Fully adapted donor block | 137 | 142 | 136 |
| Previously adapted host block | 172 | 172 | 181 |
| Training-only lookup using output counts | 419 | 419 | 419 |

The full donor scored 133, 146 and 137 on qualification, against host scores of 182, 190 and 187. All orders missed the gate. On confirmation the full donor trailed the host by 7.16 percentage points, paired interval [−9.70, −4.82]. The jointly trained expert with original attention gained 2.60 points over the frozen donor [1.24, 4.10], yet trailed the adapted host by 6.97 points [−8.92, −5.01]. The full donor's gain over this isolated expert was −0.20 points [−1.76, 1.56]. The factorial interaction on accuracy was −1.11 points [−3.39, 1.17]. These estimates use 5,000 paired resamples of complete control-flow families and training orders. Sixteen confirmation families and three orders limit precision. None of the neural conditions solved all four requests for any confirmation layout. [Confirmation results](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-summary.json)

## The cost and benefit of removing a component

Replacing the adapted expert with its original weights while keeping attention and norms adapted erased 96, 124 and 47 correct confirmation repairs. It also corrected 89, 112 and 43 errors respectively. The mean intact-minus-restored difference was +1.50 points [−0.20, 3.32]. Looking only at the solves lost when the expert is removed would overstate its usefulness. The public ledger identifies each repair that moved in either direction for each component and control. [Per-repair interventions](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-switches.json)

## An output shortcut that outscored every model

The dataset itself supplies a strong cue. Subtract the program's literal initial total from each required output and divide by its fixed bonus. This gives the number of additions that must have executed. Sort the four counts. These four numbers discard the structure of the program, the identities of the assertion inputs and their order. For each sorted pattern, our lookup used the most common indentation among matched training examples. Unseen patterns used votes pooled across all training examples tied at the nearest Manhattan distance. Only the training split supplied votes.

This control solved 402/512 on qualification and 419/512 (81.84%) on confirmation. It solved all four requests together on 62 of 128 confirmation layouts. For the shallowest candidate the bonus executes exactly once on every public input, so the four counts are all ones. On this panel all 128 such patterns required four spaces. The lookup additionally solved 112/128 eight-space, 70/128 twelve-space and 109/128 sixteen-space repairs. It solved 34 of 45 repairs with previously unseen count patterns. These are properties of the benchmark generator and its distinct-answer requirement. They establish an available shortcut; the experiment does not determine whether either language model uses it. [Lookup breakdown](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-analysis.json) · [Visible assertions and hidden inputs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-problems.json)

## Verification and decision

An independent replay composed the attention-side computation from one loaded model and the feed-forward computation from another in activation space. It reproduced every recorded top choice on both panels. The largest absolute logit difference was 0.0625 on confirmation. Native control logits reproduced exactly. A second lookup implementation parsed Python syntax trees and reproduced all lookup votes. We checked all visible and hidden candidate behaviors across the 1,024 repairs and verified both directions of the per-problem intervention ledger. [Replay and numerical differences](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

This closes the proposed feed-forward-only transplant for this task at the tested budget. The intact donor gained little from unfreezing its attention and did not exhibit the required advantage over the host. An implementation using input-dependent gates in a spatial network offers a different kind of donor that can be audited against its full local rule. Any transfer claim there should be made against a fully observed host trained on the same examples.

Use the repository's Apple Silicon environment and the original pinned models. Place the previous donor and host checkpoints into cache/specialist-v1 and the new whole-donor checkpoints into cache/donor-block-v1. The commands below reproduce training, replay, the shortcut breakdown and the standalone figure. The full-model score files and per-item ledgers are included under results. [Prior checkpoints](https://github.com/buildngrowsv/routed-expert-splice/releases/tag/specialist-indent-v1) · [New block-24 checkpoints](https://github.com/buildngrowsv/routed-expert-splice/releases/tag/whole-donor-block-v1) · [Archive checksum](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-archive.json)

```sh
python donor_block/experiment.py
python donor_block/verify.py
python donor_block/shortcut_report.py
python donor_block/figure.py
```