---
below_floor: true
quality_floor: 7.0
title: "Replacing a Qwen feed-forward block with a smaller pretrained expert"
paper_id: "2026-333"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T15:00:16Z"
abstract: "Can a larger language model use a frozen block from a smaller coding model? We transplanted the final feed-forward network of Qwen2.5-Coder-0.5B into Qwen2.5-1.5B. An optional soft route selected its pre-adaptation checkpoint for every seed. When the host\u2019s original block was removed, an aligned donor recovered 40.3% of the increase in next-token loss on Python code and 26.3% on documentation. The intact donor improved code loss by 0.070 nats/token over a neuron-shuffled control and 0.025 over a cheaper affine replacement. Most recovery came from fitting the bridges between models. Additional host-side adaptation had a small, uncertain effect, and the intact host retained the best loss. On new windows, the code donor\u2019s advantage over a matched general-purpose 0.5B donor was 0.010 nats/token, with a paired interval spanning zero. The result supports partial transfer of a learned block in a damaged host; it leaves coding specialization and gains in a healthy host unresolved."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the architectural questions. OpenAI Codex implemented, executed and analyzed the experiments on the owner\u2019s Mac Studio and assisted with the manuscript and figures."
---

![Held-out next-token loss for the native block and four replacement conditions](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-replacement.png)

## Architecture and question

Mixtures of experts use a router to decide how much a specialized subnetwork contributes. Here the imported “expert” was one existing feed-forward network, comprising 13,074,432 weights, from a separately released smaller model. The source was the final block of Qwen2.5-Coder-0.5B. The destination was the final block of the base Qwen2.5-1.5B, after attention and before the output normalization. This keeps the donor computation intact while allowing its surrounding maps to adapt. Model stitching and sparse upcycling provide related precedents for connecting pretrained components and deriving experts from dense checkpoints. [Model stitching](https://arxiv.org/abs/2106.07682) · [Sparse upcycling](https://arxiv.org/abs/2212.05055).

The host has 1,536 channels and the donor 896. We used ridge regression on training-only, token-aligned states to map host inputs to donor inputs and donor outputs back to native host updates. The intact and shuffled controls each received their own fitted output map. Shuffling permuted the rows of the donor up-projection relative to its learned gate and down-projection, preserving the stored tensor values. This is a disruption of one learned correspondence. It does not erase all features learned during pretraining.

## Evaluation and selection

We used source files and reStructuredText documentation from a pinned CPython release. Training, validation and test files were disjoint. Each domain supplied 768 training, 128 validation, and 512 test windows, with four target positions per window and up to 64 preceding tokens. All scored probabilities used the full host vocabulary. Primary measurements are natural-log loss per token (lower is better) and exact top-one accuracy. The later comparisons used fresh, non-overlapping windows from the same test-file pool. Uncertainty resamples files, preserving their token groups, and paired adapter seeds where applicable. Pretraining overlap with public CPython source is possible. These tests measure adaptation on this corpus.

## Optional routing

Three arms trained the same rank-16 host-side adapter with either no graft, an intact graft, or a shuffled graft. Graft arms also trained a token-dependent gate and an output-side correction. A soft gate evaluates both branches. The experiment makes no claim of sparse-inference speedup. The validation rule selected epoch zero in all arms and seeds. After one epoch, the trained router gave very little average weight to either graft. On the held-out code windows, the intact host scored 1.4451 nats/token and the selected intact graft scored 1.4472. Because the selected weights were identical across seeds, those seeds supply one distinct prediction set per arm. Small differences in this screen should be interpreted cautiously: the cached native calculation differed from a direct calculation by up to 0.0473 nats on its four-position spot check.

## Forced replacement

We removed the native feed-forward block. An affine pair of bridges aligned the frozen donor; a rank-32 nonlinear host-side correction was then trained to match the original host’s feed-forward output on training states. Validation selected among zero, one, two, four and eight passes. The unmodified and knockout references, a shuffled donor, and disabling the intact donor after training distinguish recovery from ordinary host behavior. The mandatory graft’s inference path receives the surviving host residual and the donor branch. The removed block’s output is a training target only. A direct live model replacement agreed with the cached path on all 32 top-one predictions checked, with mean absolute loss error below 0.000001 nats.

| Replacement | Python loss | Documentation loss | Python top-one accuracy | Documentation top-one accuracy |
|---|---:|---:|---:|---:|
| Original host | 1.554 | 1.954 | 67.38% | 57.42% |
| Block removed | 1.978 | 2.442 | 63.77% | 53.56% |
| Direct affine map, no donor | 1.832 | 2.328 | 64.01% | 52.34% |
| Shuffled donor plus correction | 1.877 | 2.377 | 64.24% | 53.27% |
| Intact donor, fitted bridges only | 1.810 | 2.314 | 63.67% | 52.39% |
| Intact donor plus correction | 1.807 | 2.314 | 63.80% | 52.49% |

We calculated loss recovery relative to the damage caused by removing the native block. The recovered share was 40.3% on Python and 26.3% on documentation. Against the shuffled donor the intact graft reduced loss by 0.070 nats/token on code (approximate 95% paired interval 0.049 to 0.092) and 0.063 on documentation (0.041 to 0.085). Top-one accuracy did not improve over the shuffled control. Against the intact fit-only graft, the extra host-side training improved code loss by 0.0027, with an interval spanning zero. Fitting the bridges accounted for most of the recovery.

We next tried a cheaper direct host-to-host affine map with 2,360,832 fitted coefficients. The intact trained graft reduced code loss by 0.025 relative to this comparator (0.005 to 0.044). Its 0.014 improvement on documentation was uncertain. The intact graft adds a frozen expert, two fitted maps, and more computation; no latency or utilization advantage was measured.

## Does a coding donor matter?

One last comparison used the final block of the general base Qwen2.5-0.5B under the same ridge-fitting protocol. Both grafts used the same host, matching dimensions and training contexts, with no subsequent gradient updates. On a third set of held-out windows, code loss was 1.746 for the specialist and 1.757 for the general donor. The paired difference was −0.010 nats/token (−0.023 to +0.003). The documentation difference was −0.013 (−0.030 to +0.004). The specialist did not pass the planned 0.02-nat threshold. Differences across the three window sets should be compared only within their corresponding experiment.

## Limits and next decision

The host’s pretrained trunk remained frozen. The trained host-side components were the interfaces and small adapters. This is evidence for recovering some function at one forced insertion site; we did not establish a benefit from optional routing, a clear domain-specialization effect, or an advantage over the undamaged native host. The strongest next control would change the insertion depth once while retaining the intact, general-donor and cheap affine controls. Measure downstream task accuracy and real forward latency before treating a lower loss as a deployment improvement.

The account owner proposed the transplantation question. OpenAI Codex implemented the protocols, ran them on the owner’s Apple M5 Ultra, analyzed the saved outputs, and assisted with writing. [Public repository and protocols](https://github.com/buildngrowsv/routed-expert-splice) · [Qwen host](https://huggingface.co/Qwen/Qwen2.5-1.5B) · [Coding donor](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B) · [General donor](https://huggingface.co/Qwen/Qwen2.5-0.5B) · [CPython release source](https://github.[REDACTED_SECRET]).