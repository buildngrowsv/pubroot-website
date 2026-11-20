---
title: "A threefold reduction in learning rate restores Python prediction in two 285M models"
paper_id: "2026-407"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:46:59Z"
abstract: "At the original learning rate, a 285M-parameter model carrying a fixed 192-value reference scored 5.73704 validation bits per byte, and its equally wide writable control scored 5.07911. Restarting from the same initializations and reducing the peak learning rate from 0.0004 to 0.0004 / 3 moved the scores to 1.02025 and 1.01431 on the same Python. Both passed the 3.24 qualification threshold. The original fixed-minus-writable gap of +0.65793 bits per byte became +0.00594 (paired 95% interval +0.00217 to +0.00790). Optimization had a large influence on the apparent architectural difference in this training draw."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

At the original learning rate, a 285M-parameter model carrying a fixed 192-value reference scored 5.73704 validation bits per byte, and its equally wide writable control scored 5.07911. Restarting from the same initializations and reducing the peak learning rate from 0.0004 to 0.0004 / 3 moved the scores to 1.02025 and 1.01431 on the same Python. Both passed the 3.24 qualification threshold. The original fixed-minus-writable gap of +0.65793 bits per byte became +0.00594 (paired 95% interval +0.00217 to +0.00790). Optimization had a large influence on the apparent architectural difference in this training draw.

![Both wide models recover at one third of the original peak learning rate](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-recovery.png)

## The matched restart

Each model uses ten transformer blocks, width 1,536, and 284,720,640 parameters. In the fixed arm, 192 coordinates produced by block 2 travel unchanged through seven blocks. Those blocks can read the coordinates. In the control they can also overwrite them. Initial weights match between arms, including zero-initialized output rows that write to those coordinates. We restarted both models with seed 101 and retained the exact 4,096 batches of 16 windows, with 512 target bytes per window. That gives 33,554,432 target bytes per fit, including repeated exposure. AdamW, its 128-update warmup, the 0.03 weight decay and the gradient-norm cap of 1 were held fixed. The learning rate was selected after the first wide fixed-arm result became available. We registered the retry before the original writable result and before the recovery fits. [Protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Earlier width comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

| Architecture | Initial rate, bits per byte | Reduced rate, bits per byte | Change and paired 95% interval |
|---|---:|---:|---|
| Fixed reference | 5.73704 | 1.02025 | -4.71679 (-4.90931 to -4.61956) |
| Writable control | 5.07911 | 1.01431 | -4.06480 (-4.19665 to -3.99645) |

Lower bits per byte means higher probability assigned to the observed next byte. All four fits use the same 1,024 held-out validation windows sampled from 42 package groups in CPython. We reconstructed their file identities and offsets from the public corpus manifest and resampled whole package groups for paired intervals. The change in the fixed-minus-writable comparison across rates was -0.65199 bits per byte (95% interval -0.73797 to -0.60814). Under the original rate a single-byte frequency predictor scored 4.54745 and a preceding-byte count model scored 3.36963. [Per-window data and receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-width-rate-mid) · [Original fits and counting baselines](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-original-mid) · [Audit code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Audited numbers](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## What this permits us to test

The 32M pair scored 1.03549 and 1.04253 at the original rate. The two widths now use different learning rates, and each has one training order. The published intervals measure variation over validation packages. They do not estimate variation across independently trained models. Prior work on width-dependent parameterization motivates explicit attention to optimizer transfer when scaling. The threefold decrease here was a targeted empirical choice. These two settings cannot identify an optimal rate. [Yang and colleagues](https://arxiv.org/abs/2203.03466)

The predeclared decision now qualifies a continuation of both checkpoints with their optimizer states to 16,384 updates, followed by comparison on a separate 2,048-window test panel. The 238M sealed- versus late-copy comparison uses the recovered fixed model as its same-rate baseline. A reserved test result and direct interventions measure aggregate prediction and the channels carrying a specific answer, respectively. [Sealed comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Identifier exchange](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The owner proposed revisiting fixed forward references at larger sizes. OpenAI Codex implemented and ran the fits on the owner's Apple M5 Ultra, reconstructed their validation results and assisted with writing. [Recorded environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)