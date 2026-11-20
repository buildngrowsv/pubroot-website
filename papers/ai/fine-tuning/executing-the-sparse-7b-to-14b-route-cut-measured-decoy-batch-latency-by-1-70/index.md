---
title: "Executing the sparse 7B-to-14B route cut measured decoy-batch latency by 1.70\u00d7"
paper_id: "2026-561"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T15:43:12Z"
abstract: "Running the 14B graft only on low-margin prompts gave a paired median speedup of 1.70\u00d7 versus always blending on bracket-decoy batches (95% interval 1.68\u20131.76\u00d7). The actual sparse route solved 1,482 of 2,304 complete decoy groups versus 1,375 for standalone 7B. It reproduced every call decision from offline scores and differed on one complete-group candidate vector. The route took 235.76 ms median per batch of 12 decoy prompts, while the standalone 7B took 134.72 ms."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Running the 14B graft only on low-margin prompts gave a paired median speedup of **1.70×** versus always blending on bracket-decoy batches (95% interval 1.68–1.76×). The actual sparse route solved **1,482 of 2,304** complete decoy groups versus **1,375** for standalone 7B. It reproduced every call decision from offline scores and differed on one complete-group candidate vector. The route took 235.76 ms median per batch of 12 decoy prompts, while the standalone 7B took 134.72 ms.

![Synchronized latency for three inference paths](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-timing.png)

## Run only the selected 14B rows

Use the exact neutral and decoy triplets, frozen BF16 checkpoints, 32-coordinate interface and fixed rule from the prior confirmation. The 7B specialist scores all prompts. Its top-two logit margin of 0.5625 or lower selects a subset of rows. The 14B runs on that subset only, after the subset has been selected. The rule blends its resulting logits at weights 0.75 for the 7B and 0.25 for the graft. Every triplet comprises three versions with independently checked executable candidate completions. Complete success means returning all three unique language-level answers from four tokens. The neutral layout replaces bracket decoys in the inert string and comment with letters. [Frozen confirmation and matched prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered benchmark](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Time three paths on the same 32 randomly selected batches of 12 prompts per layout, with resident weights, preencoded prompts, one warm-up for each method and three cyclically ordered repetitions. Each timed call produces materialized scores and winners. Timing includes both model passes when used, selecting the rows, the expert projection and blend. Setup and warm-up are outside the timed interval. Per-batch medians form paired ratios. Resample complete timing batches 5,000 times. Separately run true sparse execution for all 6,912 prompts per layout and compare them with the exhaustive offline predictions and masks. [Pinned source](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Choices and nanosecond timings](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-route.npz)

| Workload | Standalone 7B median | Always blend median | Confidence route median | Paired speed ratio |
|---|---:|---:|---:|---:|
| Neutral | 134.71 ms | 419.85 ms | 221.03 ms | 1.90× |
| Bracket decoys | 134.72 ms | 420.11 ms | 235.76 ms | 1.70× |

The neutral speed ratio interval is 1.76–1.98×. The decoy route gained **4.64 percentage points** over standalone (95% paired whole-group interval +3.17 to +6.16). On neutral prompts it solved 1,957 versus 1,960 standalone, a change of −0.13 points (−1.13 to +0.82), inside the two-point loss tolerance. The call counts were exactly the archived 1,593 decoy and 825 neutral calls, out of 6,912 per layout. The per-group vector differed from offline in one decoy and three neutral groups. The actual execution cleared the registered parity, speed, quality and request-fraction gates. [Numeric report](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent reconstruction](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The timed cases use preencoded short synthetic Python repairs, a resident pair of Apple Silicon models and batches of 12. The route remains slower than standalone and yields higher decoy accuracy. Claimed speedup is against evaluating both models on every prompt in this workload. The experiment leaves cold-start time, generation beyond one token and more diverse programming tasks open.

## Reproduction

The owner’s Apple M5 Ultra Studio has 256 GiB unified memory. It ran macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The full live job took 460.89 seconds and peaked at 45.58 GB MLX allocation. From the repo root, `uv run --with numpy python [REDACTED_SECRET].py` verifies the complete-panel predictions, exact call masks, timing batches and paired intervals. To reproduce model execution, use the pinned launcher with `STUDIO_JOB_DIR` set to a fresh directory. It reads the public bridge, prompt and reference logits archives from the repo. The owner proposed expert transplantation and conditional calls. OpenAI Codex implemented, ran, audited and documented the experiment. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)