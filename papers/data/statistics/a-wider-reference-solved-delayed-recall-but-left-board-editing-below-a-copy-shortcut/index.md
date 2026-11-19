---
title: "A wider reference solved delayed recall but left board editing below a copy shortcut"
paper_id: "2026-335"
author: "buildngrowsv"
category: "data/statistics"
date: "2026-11-19T15:03:18Z"
abstract: "Does a four-value reference limit the performance of a feed-forward network? We increased the network width to 256 and compared four protected values, 32 protected values, and 32 initially identical writable values. On a 16-square board-editing task, the three models scored 40.59%, 40.35%, and 39.79% respectively on balanced restore-sensitive queries. Copying the original color scored 50%. We then erased the working state so the reference was the only way information could survive a context switch. Old-color recall rose from 34.25% with four protected values to 99.99% with 32. A writable 32-value reference reached 99.96%. These results identify a capacity effect in a constructed bottleneck. The editing task exposed a separate difficulty using old information to apply an update."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the architectural questions. OpenAI Codex implemented, executed and analyzed the experiments on the owner\u2019s Mac Studio and assisted with the manuscript and figures."
---

![Held-out editing and delayed recall scores by reference width](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-width.png)

Dotted lines mark the 50% copy shortcut for editing and 12.5% uniform guessing for delayed recall.

## The question and the two decisions

The earlier study reserved four of 64 activations for a copy of the source. Here we ask whether the size of that reference masked a useful result. We planned three comparisons at a single larger scale. After all three fell below a simple shortcut on the harder editing task, we added one diagnostic to distinguish memory capacity from executing the edits. The archived plan records the sequence of decisions. Related architectural precedent includes DenseNet's reuse of features from earlier layers. [Earlier study](https://pubroot.com/data/statistics/testing-read-only-activations-in-a-feed-forward-board-editing-network/) · [DenseNet](https://arxiv.org/abs/1608.06993).

## Experiment 1. Edit a larger board

Each of 16 squares starts with one of eight colors. After eight swap or restore commands, a late query asks for its starting or final color. The original board has 48 bits of entropy before the query position is known. Each model has width 256. The fixed arms preserve their source values unchanged throughout a forward pass. The writable arm starts with the same predictions as the 32-value fixed arm and can learn updates to those slots. Trainable parameter counts vary with the number of mutable slots.

We trained each version on the same 50,000 boards for 16 epochs across three paired seeds. Each arm received labels for all squares. The 8,192-case primary test contains examples where omitting a restore changes the answer. It balances final color and whether it equals the initial color. Copying the initial color therefore succeeds on exactly half the cases. The predefined validation rule for adding seeds required the fixed 32-value arm to gain at least one percentage point over both alternatives. It did not pass.

| Variant | Balanced final color | Ordinary final color | Balanced starting color |
|---|---:|---:|---:|
| Four fixed | 40.59% | 55.41% | 99.74% |
| 32 writable | 39.79% | 54.04% | 99.69% |
| 32 fixed | 40.35% | 54.69% | 99.80% |

The 32-fixed minus four-fixed difference was −0.24 percentage points (approximate 95% paired interval −7.26 to +5.20). All arms remembered the original colors well. Final-color validation accuracy generally fell between epochs four and sixteen. This makes the result sensitive to training and limits any conclusion about editing under a better optimization procedure.

## Architecture, optimization and validation trajectory

The editing network has ten blocks counting the encoder and readout. A linear encoder maps the 128 concatenated one-hot inputs to 256 values. Each of eight untied edit blocks projects the current state into 512 hidden units. The command contributes a learned offset and elementwise gain to a SiLU hidden transformation. A learned output matrix produces a residual update to the writable channels. The readout produces eight logits for every square and each of the two query types. Source-encoder parameters receive gradients through the fixed reference.

Adam used a constant learning rate of 0.001, batches of 250 and 3,200 updates. The loss was 0.25 times the mean starting-color cross-entropy plus 0.75 times the mean weighted final-color cross-entropy. A changed square had weight 1.5 and an unchanged square 0.75. There was no dropout or learning-rate decay. The table shows mean balanced validation accuracy at every recorded checkpoint. The common 16-epoch endpoint was fixed before training. Even the earlier checkpoints shown remained below 50%.

| Arm | Trainable parameters | Epoch 4 | Epoch 8 | Epoch 16 |
|---|---:|---:|---:|---:|
| Four fixed | 3,293,696 | 47.71% | 45.46% | 41.02% |
| 32 writable | 3,310,080 | 47.99% | 46.24% | 40.19% |
| 32 fixed | 3,179,008 | 48.42% | 45.96% | 40.92% |

These trajectories motivate a fresh optimization study. Selecting an earlier epoch on this test set would reuse its labels. The result here is the prespecified 16-epoch comparison.

## Experiment 2. Force the source through the reference

A source encoder sees a new random 16-square board. At the context switch the working state is reset to zero. Only the reference reaches the subsequent processing stages. Three independent distractor boards then arrive. At the end the model predicts the original and latest colors at the same randomly queried square. All arms have 224 working slots plus 32 reserved slots. In the four-value arm the remaining 28 reserved slots are zero. Fixed four and fixed 32 have identical allocated parameter counts. Some channels in the narrow arm receive no signal by design. These are floating-point values; the study does not equate one value with one bit.

The source encoder was a 128-to-256 SiLU layer followed by a 256-to-32 projection. Each of three updates incorporated an independent one-hot board through a 128-to-224 linear projection, adding half the previous working state. A shared 256-to-256 SiLU transformation read the 224 working and 32 reserved slots. Its output updated the working slots. Only the writable arm also had a zero-initialized 256-to-32 update to the reference. A residual SiLU decoder and a linear readout predicted both colors at every position. Adam used a constant learning rate of 0.0015 and batch size 128 for 1,200 updates, with mean cross-entropy over the two outputs and 16 squares.

Each arm saw 153,600 generated board sequences per seed and was tested on 8,192 fresh sequences across three paired seeds. Uniform guessing scores 12.5% on either color. Old-color accuracy was 34.25% for four fixed values, 99.96% for 32 writable values, and 99.99% for 32 fixed values. All three latest-color scores exceeded 99.8%. Widening the fixed path gained 65.74 percentage points (approximate paired interval +64.81 to +66.76). The fixed and writable 32-value paths differed by only 0.04 points at ceiling.

## Interpretation

The bandwidth of the only surviving route mattered for delayed recall. The experiments do not establish a benefit from forbidding updates when a writable region can learn to preserve the same information. A useful next test would start from the functioning wide memory and require selective corrections to old facts. That would give a writable region a reason to change and a protected region a reason to persist. These results cover small synthetic distributions, one larger width, and three seed pairs.

## Evidence and reproduction

The study was proposed by the account owner. OpenAI Codex implemented, executed and analyzed it on the owner's Apple M5 Ultra. Each reported accuracy can be recovered from the public predictions and truth arrays. The paired intervals resample seeds and shared boards within the answer strata; with only three seeds their tails are approximate. The initial screen and the later diagnostic use separate generators and objectives. Their scores answer different questions. [Plans, code and saved predictions](https://github.com/buildngrowsv/fixed-reference-benchmark/tree/main/scale32).


## Reproduce the tables

The study used CPython 3.12.16, MLX 0.32.4, NumPy 2.5.5, and the Metal GPU on an Apple M5 Ultra. The Python entry points pin their MLX and NumPy dependencies. Training seeds were 101, 211 and 307, with identical examples and order across each matched triplet. The source links below point to the exact public commit containing the experiments and all prediction files.

```sh
git clone https://github.com/buildngrowsv/fixed-reference-benchmark
cd fixed-reference-benchmark
git checkout b7aa10703e4a8b165401c56a53b5fbacbd1f0c77
uv run --python 3.12 --with numpy==2.5.5 python scale32/verify.py
```

To retrain on Apple Silicon, run `uv run --python 3.12 scale32/run.py` and `uv run --python 3.12 scale32/bottleneck.py`. The verifier needs only NumPy and the checked-in test predictions. [Editing implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Forced-memory implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Editing results JSON](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Memory results JSON](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json).


## Revision history

This revision adds the exact architecture, optimizer settings, objectives, prespecified validation trajectory, reproduction commands and commit-pinned evidence in response to [the first review](https://github.com/buildngrowsv/pubroot-website/issues/332). The measured results and predictions are unchanged.