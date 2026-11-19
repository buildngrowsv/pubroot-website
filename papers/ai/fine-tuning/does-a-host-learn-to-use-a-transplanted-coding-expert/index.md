---
title: "Does a host learn to use a transplanted coding expert?"
paper_id: "2026-337"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T16:21:20Z"
abstract: "Can one trainable host block learn to use an expert transplanted from a smaller language model? We replaced the penultimate feed-forward network of Qwen2.5-1.5B with the frozen final feed-forward network of Qwen2.5-Coder-0.5B and trained all 46.8 million parameters of the following host block against intact-host hidden states. Six paired conditions, three minibatch-order seeds and a new file-held-out CPython panel separated initial compatibility from acquired reliance. On code, removing the coding expert before training cost 0.05527 nats per token. After adaptation it cost 0.05389, a change of \u22120.00138 with a paired 95% interval of [\u22120.00339, 0.00000]. The coding graft beat a shuffled donor by 0.01565 nats but its advantage over a matched general-purpose donor was unresolved. Training had its largest effect when the feed-forward network was absent. Within this short reconstruction experiment, a usable transplant and increased host reliance were empirically separable."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the surgical intervention. OpenAI Codex implemented and ran the comparison on the owner's Apple M5 Ultra, analyzed outputs, and assisted with the manuscript."
---

A frozen coding expert carried useful information immediately after surgery. On held-out Python code, removing it raised next-token loss by **0.0553 nats per token**. After allowing the next host block to learn, the cost of removal was **0.0539**. The change in reliance was **−0.00138** with a paired 95% interval of **[−0.00339, 0.00000]**. This experiment found no increase in reliance under a short host-reconstruction objective. It did show that an intact donor performed better on code than the same donor with its internal neuron pairing scrambled.

[Study figure](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-use.png)

#### Operation and benchmark

We moved the same 13,074,432-weight feed-forward network from Qwen2.5-Coder-0.5B into block 27 of the 28-block Qwen2.5-1.5B base model. Host attention and its residual connection survived the operation. Affine input and output maps fitted on training activations translated between the host's 1,536 values per token and the donor's 896. The coding network and both maps stayed fixed. Block 28, including its attention, feed-forward network and normalizations, supplied all 46,797,824 gradient-trainable parameters. Each token passed through the same branch. The prior study used the final host block for the graft. The present study estimates effects within the upstream placement. [Prior study](https://pubroot.com/ai/fine-tuning/replacing-a-qwen-feed-forward-block-with-a-smaller-pretrained-expert/)

Six conditions began with identical host checkpoints. Each received 96 Adam updates at a learning rate of 0.00002 over 1,536 CPython windows. The training target was the intact host's final hidden state. Within each seed we held example order constant across conditions. On 256 validation windows, next-token loss selected among steps 0, 8, 32 and 96. We then scored the actual full models on 1,024 new 64-token windows from 92 Python source files and 62 documentation files. Four target positions per window gave 2,048 predictions per domain, shared across all three order seeds. Every test file was held out from both fitting and model selection. All new windows were disjoint from the earlier panels. In the results below, lower loss means the model assigned more probability to the token that actually came next. [Protocol committed before evaluation](https://github.com/buildngrowsv/routed-expert-splice/blob/f5fc1d2/penultimate/PLAN.md) · [Methods and reproduction](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

#### Loss with the next host block frozen or allowed to learn

| Block 27 condition | Python, frozen | Python, after selection | Docs, frozen | Docs, after selection |
|---|---:|---:|---:|---:|
| Native host | 1.57656 | 1.57656 | 1.86673 | 1.86673 |
| Feed-forward network removed | 1.73518 | 1.72232 | 2.01383 | 1.99092 |
| Direct affine reconstruction | 1.68504 | 1.68470 | 1.94727 | 1.94731 |
| Shuffled coding expert | 1.69587 | 1.69511 | 1.94922 | 1.94984 |
| General-purpose expert | 1.68305 | 1.68095 | 1.94439 | 1.94686 |
| Intact coding expert | 1.67991 | 1.67946 | 1.94006 | 1.94039 |

Training with the coding graft improved Python loss by 0.00044 nats, with a 95% interval of [−0.00073, 0.00199]. The target set in advance was 0.02. Top-one accuracy moved from 65.33% to 65.43%, a change of 0.10 percentage points [−0.10, 0.35]. On documentation, the loss increase was 0.00033. The selected coding checkpoints occurred at steps 0, 8 and 8. The removal control selected step 96 for all three seeds and improved by 0.01286 nats on code [0.00133, 0.02431] and 0.02291 on documentation [0.00814, 0.03726]. The untouched host still had the best absolute scores. [Validation history](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [All held-out estimates](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

#### Did the host learn to use this donor?

Removal after training kept the adapted block fixed. The expert's immediate benefit persisted, and the estimated change in that benefit was slightly negative in both domains. On documentation the withdrawal penalty moved from 0.07377 to 0.07074 nats, a change of −0.00303 [−0.00610, 0.00000]. A second check exchanged the blocks trained with the coding and shuffled experts. On code, matching each block back to its own expert improved mean loss by just 0.00001 nats [−0.00078, 0.00086]. Paired intervals resample source files and order seeds, preserving within-file correlations.

The intact graft beat its neuron-shuffled control on code by 0.01565 nats [0.00655, 0.02484]. Its advantage over the same-sized general donor was 0.00149 [−0.00728, 0.01097], and over the direct affine map it was 0.00524 [−0.00493, 0.01581]. These comparisons support a role for intact pretrained structure. They leave the value of code specialization unresolved. The clearest evidence for learning was the host's partial compensation when its feed-forward network was missing.

#### Relation to existing research

Model stitching uses a learned interface to test whether representations from separately trained models can work together. Prior studies of feature transfer also identified disruption of features that were learned together. Those findings motivated testing the neighboring block and using a fitted affine control. Work on language model composition provides another precedent for accessing signals from a smaller model through a learned interface. The present intervention transplants a single mandatory feed-forward module and measures whether subsequent adaptation increases the cost of removing it. [Bansal, Nakkiran and Barak, model stitching](https://arxiv.org/abs/2106.07682) · [Yosinski et al., feature transfer](https://arxiv.org/abs/1411.1792) · [Bansal et al., language model composition](https://arxiv.org/abs/2401.02412)

#### Limits and next experiment

This evaluates local repair under one objective, placement, model family and training budget. Training the host to imitate its old state rewards restoring behavior it already had. It gives little incentive to acquire a capability unique to the donor. The benchmark covers short CPython sequences, uses next-token probabilities, and cannot rule out overlap with model pretraining. A validation check found small BF16 discrepancies between cached and end-to-end inference, so all validation selections and test metrics use the full model. Three order seeds offer limited precision about training variability. [Diagnostic measurements](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-model-check.json)

The most informative next experiment would first verify that the standalone donor beats the intact host on a specific, automatically graded code task. If that advantage exists, fit the same host block on the graded task and repeat the donor-removal test and the general-donor control. That would give the host a reason to acquire a donor-specific skill and a way to count successful transfers.

The account owner proposed moving the graft upstream and adapting the following block. OpenAI Codex implemented the experiment, ran it over SSH on the owner's Apple M5 Ultra, analyzed the results and assisted with writing. The portable verification script checks 18 checkpoint choices, selected weight updates, unique test windows, all domain scores and both donor-use contrasts. [Pinned evidence and implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])