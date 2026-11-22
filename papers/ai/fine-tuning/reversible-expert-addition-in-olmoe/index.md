---
title: "Reversible expert addition in OLMoE"
paper_id: "2026-575"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-22T04:33:31Z"
abstract: "Adding one trainable expert to each layer of frozen OLMoE-1B-7B recovered 89.2% of the Icelandic validation-loss gain of full fine-tuning at 20.48 million matched training tokens. After the full plug-in run, removal restored bit-identical logits on two fixed English windows and restored the original validation losses across four domains. While installed, the plug-in raised Python loss by 2.34%, exceeding the registered 1% retention limit. When two independently trained language plug-ins shared the model, both languages improved over the base model and each gained less than it did with its own plug-in alone."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The owner proposed the research direction. OpenAI Codex registered, implemented, ran and verified the comparisons and assisted with writing."
---

Adding one trainable expert to each layer of frozen OLMoE-1B-7B recovered 89.2% of the Icelandic validation-loss gain of full fine-tuning at 20.48 million matched training tokens. After the full plug-in run, removal restored bit-identical logits on two fixed English windows and restored the original validation losses across four domains. While installed, the plug-in raised Python loss by 2.34%, exceeding the registered 1% retention limit. When two independently trained language plug-ins shared the model, both languages improved over the base model and each gained less than it did with its own plug-in alone.

## Method

We used the OLMoE-1B-7B-0924 base checkpoint at revision `6d84c48581ece794365f2b8e9cfb043c68ade9c5`. OLMoE has 16 layers of 64 experts with eight selected per token. We retained the original experts and router rows as frozen modules. Each layer gained one expert and one router row. A census of about one million tokens per domain identified source experts by high language-to-English selection ratios subject to a minimum language-use rate. The primary plug-in copied the source expert’s gate and up projections and its router row, and started its down projection at zero. The original top-eight rule still applied, with softmax over all available rows. This allows a new row to influence routing even while its expert output is zero. We also trained a Welsh plug-in independently using the same procedure. [OLMoE](https://arxiv.org/abs/2409.02060)

The primary plug-in trained 100.7M parameters with AdamW. The controls used a fixed router, trainable copies of all router rows, copied down projections, attention LoRA matched within 0.04% of the primary trainable parameter count, and full fine-tuning of 6.92B parameters. Each recipe used its registered learning rate, one seed and identically ordered windows for its language. Validation used 64 fixed windows per domain. All arms except the time-capped full fine-tuning reached 3,051 steps and 49.99M tokens. The registered decision used 70% gain recovery, 1% maximum loss increases on English and Python, and exact output restoration after removal. [Registered protocol and pinned source](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].zip)

## Comparison at matched tokens

Full fine-tuning ended at 1,450 steps. Its last evaluation shared with the plug-in was step 1,250, at 20.48M tokens. Icelandic loss went from 3.075 to 1.935 with the plug-in and to 1.798 with full fine-tuning. Dividing the two reductions gives 89.2% gain recovery. At the plug-in’s 49.99M-token endpoint, Icelandic loss was 1.758 and English and Python losses rose by 0.34% and 2.34%. Exact removal passed on the tested windows. The registered decision was partial because Python loss exceeded the retention limit.

| Icelandic arm at 49.99M tokens | Icelandic loss | English loss change | Python loss change |
|---|---:|---:|---:|
| New experts and their router rows | 1.758 | +0.34% | +2.34% |
| New experts, fixed router | 1.830 | +0.34% | +1.73% |
| New experts and copies of all router rows | 1.750 | +1.01% | +4.58% |
| Parameter-matched attention LoRA | 1.964 | +7.41% | +16.19% |
| Copied down projections at initialization | 1.834 | +0.62% | +4.01% |

The primary plug-in led LoRA on Icelandic, English and Python at equal tokens. Training every router row improved Icelandic loss by another 0.008 nats per token and added 2.23 percentage points to the Python loss increase. Leaving the router fixed preserved Python better and gave up some Icelandic improvement.

## Two experts in one model

| Installed plug-ins | Icelandic loss | Welsh loss | English loss | Python loss |
|---|---:|---:|---:|---:|
| None | 3.075 | 2.720 | 2.267 | 0.795 |
| Icelandic | 1.758 | 3.889 | 2.275 | 0.813 |
| Welsh | 3.990 | 1.639 | 2.278 | 0.812 |
| Icelandic and Welsh | 2.439 | 1.950 | 2.300 | 0.847 |

Each plug-in raised loss on the other language while installed. Together they preserved 48.3% of the standalone Icelandic gain and 71.2% of the standalone Welsh gain. The original routing census chose the same initialization expert in 13 of 16 layers for Icelandic and Welsh. Shared top-eight selection and normalization allow interference. This experiment measures the combined effect and leaves the contribution of each routing mechanism open.

## Scope and verification

Adding experts for continued learning has precedent in Lifelong-MoE, and Branch-Train-MiX combines independently trained branches and then trains routing. Here the original OLMoE modules remained available for exact restoration, and the study measured both the installed cost and the interaction between two removable expert sets. The evidence covers one base checkpoint, two languages, fixed validation windows and one seed per arm. Bit identity was checked on two windows after removal; the study also logged the restored losses across all four domains. [Lifelong-MoE](https://arxiv.org/abs/2305.12281) · [Branch-Train-MiX](https://arxiv.org/abs/2403.07816)

The Studio executed source revision `4982b3395c2cace1c4295be8e0a47d93b099218a` using MLX 0.32.4 and mlx-lm 0.32.2. Run `python3 olmoe_plugin/verify.py` from the repository root to recompute the matched gain, endpoints and decision from the saved curves and receipts. The verifier checks the recorded removal tests. The source archive contains the registered protocol, runtime and E4 implementation from the exact execution commit. [Evidence](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Source archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].zip)