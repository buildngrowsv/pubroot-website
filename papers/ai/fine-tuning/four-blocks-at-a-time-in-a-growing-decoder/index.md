---
title: "Four blocks at a time in a growing decoder"
paper_id: "2026-580"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-22T20:45:56Z"
abstract: "Growing a decoder from four to eight to twelve blocks and freezing each earlier stage finished with 47.92% of the estimated training FLOPs of the full-depth run. Its validation loss was 3.49% worse than the dense model at the same estimated compute, outside the registered 3% margin. Letting earlier blocks keep training used 68.75% of full-depth compute and landed 1.33% above its matched dense reference. At equal tokens, both growth recipes had higher loss than training all twelve blocks from the start."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The owner proposed the research direction. OpenAI Codex registered, implemented, ran and verified the comparisons and assisted with writing."
---

Growing a decoder from four to eight to twelve blocks and freezing each earlier stage finished with 47.92% of the estimated training FLOPs of the full-depth run. Its validation loss was 3.49% worse than the dense model at the same estimated compute, outside the registered 3% margin. Letting earlier blocks keep training used 68.75% of full-depth compute and landed 1.33% above its matched dense reference. At equal tokens, both growth recipes had higher loss than training all twelve blocks from the start.

## Design

All arms used a 97.5M-parameter final decoder with width 768, twelve RoPE and SwiGLU blocks, untied embeddings and the same 8,192-entry tokenizer. Training used the same seed and order of English, Python and Welsh windows, with 40 sequences of length 512 per domain per batch. The dense model trained at full depth from the start for 6,510 updates. The two growing models used three stages of 2,170 updates each, for the same total of 399,974,400 tokens.

The growth operator zero-initialized each new block’s attention and feed-forward output projections so it began as a residual identity. In the frozen arm the embedding and earlier blocks stopped training after each expansion. The final normalization and output projection continued to train. In the unfrozen arm all blocks and the embedding kept training. Each growth stage started a new optimizer schedule. The dense reference used a single schedule across its full run. [Growth implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Results

| Training recipe | Final mean loss | Estimated training FLOPs | Gap to dense at matched FLOPs | Gap to dense at matched tokens |
|---|---:|---:|---:|---:|
| Dense from the start | 2.5437 | 2.416 × 10¹⁷ | — | — |
| Grow and freeze earlier blocks | 2.8350 | 1.158 × 10¹⁷ | +3.49% | +11.45% |
| Grow with all blocks trainable | 2.6640 | 1.661 × 10¹⁷ | +1.33% | +4.73% |

Loss is the mean across English, Python and Welsh validation windows. Each domain used 64 fixed windows. The matched-compute loss comes from linear interpolation of the dense learning curve at each grown model’s final FLOP count. The dense loss at these two points was 2.7393 for the frozen comparison and 2.6289 for the unfrozen comparison. The dense run at both points was still in its learning-rate schedule. The equal-token endpoints compare all three completed schedules.

The estimate counts active block and output-projection parameters plus attention products. It charges two operations per parameter for forward passes and four for backward passes on trainable blocks and the output head. The frozen and unfrozen arms finish at different compute budgets. Their matched-compute gaps each use their own dense reference, while their equal-token gaps share the same dense endpoint.

Training time was about 71 minutes for dense, 32 minutes for frozen growth and 52 minutes for unfrozen growth on the Studio. The three runs used one starting seed. The two nominally identical four-block stages differed by 0.0012 nats per token in validation loss. The frozen arm missed the registered criterion. The unfrozen control was inside the same margin. These results measure this growth operator on this decoder and data mixture. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

## Reproduction

The Studio was a single Apple M5 Ultra Mac Studio with 80 GPU cores, 256 GB unified memory and Metal 4. Runs used macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, mlx-lm 0.32.2, NumPy 2.5.5, Transformers 5.23.0, tokenizers 0.23.3 and PyArrow 26.0.1. Optimizer parameters and cross-entropy used float32 and matrix products used bfloat16. AdamW used betas 0.9 and 0.95, weight decay 0.1, peak learning rate `6e-4`, two-percent warmup and cosine decay to ten percent of peak. Each update accumulated gradients across three equal chunks of the batch.

Run `python3 bottom_up_depth/verify.py` to recompute per-stage FLOPs, both dense interpolations and the result against the registered margin. For model replay, use the pinned parent runtime and tokenizer, prepare the data and train the dense reference, then place `grow.py` at `e5/grow.py` in the extracted runtime. Run `python run.py e5.grow --mode frozen --seed 1` and `python run.py e5.grow --mode unfrozen --seed 1` with distinct `STUDIO_JOB_DIR` paths and the same `STUDIO_QUEUE_ROOT` used for the dense reference. The exact execution revision was `4982b3395c2cace1c4295be8e0a47d93b099218a`. [Evidence and receipts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Pinned data and runtime](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Freezing earlier blocks during progressive growth has precedent in multi-stage BERT training. LLaMA Pro expands an already pretrained decoder, and curriculum-guided layer scaling couples depth growth with a data curriculum. This test compares freezing, continued training and full-depth training from scratch on the same domain-balanced stream. [Progressively Stacking 2.0](https://arxiv.org/abs/2011.13635) · [LLaMA Pro](https://arxiv.org/abs/2401.02415) · [Curriculum-Guided Layer Scaling](https://arxiv.org/abs/2506.11389)