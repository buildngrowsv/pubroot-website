---
title: "Domain selectivity and room transplantation in walled language models"
paper_id: "2026-578"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-22T18:43:32Z"
abstract: "We trained decoders with hard walls, a wiring-length penalty, learned routing and dense connectivity. Each main run used 400 million tokens. Both hard-wall seeds approached dense validation loss, with an estimated 23% higher compute per token. No main-model room, contiguous arc or expert met the registered domain-selectivity threshold. A transplanted room followed by door refitting recovered 67.0% of the code-loss damage, slightly above 64.3% for door refitting with the room still removed. The registered outcome was a null for the wall hypothesis."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The owner proposed the research direction. OpenAI Codex registered, implemented, ran and verified the comparisons and assisted with writing."
---

We trained decoders with hard walls, a wiring-length penalty, learned routing and dense connectivity. Each main run used 400 million tokens. Both hard-wall seeds approached dense validation loss, with an estimated 23% higher compute per token. No main-model room, contiguous arc or expert met the registered domain-selectivity threshold. A transplanted room followed by door refitting recovered 67.0% of the code-loss damage, slightly above 64.3% for door refitting with the room still removed. The registered outcome was a null for the wall hypothesis.

## Training and removal

All models used RoPE and SwiGLU with an 8,192-entry byte-level BPE tokenizer fit to English prose, Python and Welsh. Each batch contained 40 sequences of 512 tokens from each domain. Five small runs used roughly 200M tokens per arm. The hard-wall and wiring-penalty arms missed the screen threshold. The registered plan continued to the larger comparison to test whether selectivity appeared with more parameters and training.

At the larger size, four rooms in the walled model could exchange information through 32 shared channels. Each room had its own block weights. The topographic comparator used a circular wiring-length penalty. The routed comparator kept dense attention and selected two of four feed-forward experts per token. All five main runs used 399,974,400 tokens. The four configurations at seed 1 shared the batch order. The second walled seed changed initialization and batch order. Reported loss averages English, Python and Welsh equally. [Registered protocol and source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].zip)

| Main arm | Total parameters | Mean loss | Best selectivity | Estimated FLOPs/token |
|---|---:|---:|---:|---:|
| Dense | 97.5M | 2.5437 | 0.075 | 604.0M |
| Hard walls, seed 1 | 117.7M | 2.5504 | 0.280 | 742.4M |
| Hard walls, seed 2 | 117.7M | 2.5681 | 0.091 | 742.4M |
| Wiring penalty | 97.5M | 2.5505 | 0.047 | 604.0M |
| Learned routing | 154.2M | 2.5141 | 0.284 | 604.2M |

The removal tests silenced each walled room and each routed expert, and ablated four contiguous arcs in the other models. A room counted when its removal increased its most affected domain’s loss by at least 1%. A selectivity score of 0.5 required that increase to be at least three times the mean increase on the other two domains. All five main models fell below 0.5. The small routed model reached 0.673, an effect that did not persist in the larger run. The two walled seeds cost 0.26% and 0.96% in mean loss at equal tokens. Wider embeddings, shared doors and different estimated work per token limit comparisons at fixed compute.

## Room transplant and growth

We took the room in seed 1 whose removal hurt code the most relative to other domains. We replaced its block weights and its slices of the embedding, unembedding and final norm with the matching room from seed 2. Both the transplanted and removed-room models got the same 400 updates to door weights alone. Code loss was 1.852 in the intact model, 2.469 after removal and 2.581 after the transplant before refitting. After refitting it was 2.056 with the transplant and 2.072 with the room still removed. The 2.66-point recovery advantage fell below the registered 25-point margin and the transplant fell below the 90% absolute recovery target.

Adding a fifth room almost preserved the initial validation losses, with maximum drift of 0.0000025 nats per token on the three training domains. A separate 500-update comparison adapted to Icelandic, which the original model had never seen.

| Trainable part during Icelandic adaptation | Icelandic gain | English loss rise | Python loss rise | Welsh loss rise |
|---|---:|---:|---:|---:|
| New room only | 2.140 | 0.127 | 0.229 | 0.703 |
| New room and shared door weights | 2.294 | 0.315 | 0.365 | 1.420 |
| Full fine-tuning | 2.486 | 0.449 | 0.511 | 1.909 |

Training the new room alone recovered 86.1% of full fine-tuning’s Icelandic gain with smaller loss increases on each old domain. In that arm, the existing door weights stayed frozen and the new room’s trainable projections could still affect shared channels. It tests selective weight updates within the walled architecture. The three methods used their registered learning rates and training settings.

## Interpretation and evidence

Hard connectivity constraints did not make the resulting rooms replaceable domain specialists at this budget. The shared door refit explains most of the observed transplant recovery. The result concerns this tokenizer, mixture and one donor–recipient seed pair. TopoLM uses a spatial smoothness objective on activations. The circular wiring-length penalty tested here follows a different choice closer to brain-inspired modular training. [TopoLM](https://arxiv.org/abs/2410.11516) · [Brain-inspired modular training](https://arxiv.org/abs/2305.08746)

## Reproduction

One Apple M5 Ultra Mac Studio ran the jobs serially. It has an 80-core GPU, Metal 4 and 256 GB of unified memory. The runs used macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, mlx-lm 0.32.2, NumPy 2.5.5, Transformers 5.23.0, tokenizers 0.23.3, PyArrow 26.0.1 and huggingface-hub 2.4.0. Model parameters and cross-entropy accumulation used float32, and matrix multiplications used bfloat16. The screen took 1.32 hours. The dense, walled seed 1, walled seed 2, wiring-penalty and routed main arms took 1.19, 3.59, 3.77, 1.23 and 1.50 hours. The surgery comparison took 1.51 hours. Its peak MLX allocation was 36.3 GB.

The screen used six layers at reference width 384, and the main models used twelve layers at reference width 768. Training used AdamW with betas 0.9 and 0.95, weight decay 0.1, 2% linear warmup and cosine decay to 10% of peak. Peak rates were `1.5e-3` for the screen and `6e-4` for the main runs. The batch of 120 sequences used two equal gradient-accumulation chunks in the screen and three in the main runs. The routed arm added a load-balancing penalty with coefficient 0.01. The wiring screen tested strengths 0.01 and 0.05 and selected 0.05. The refits shared 400 updates at peak `3e-4` and zero weight decay. The two growth arms used 500 updates at peak `6e-4` with zero weight decay. The full fine-tuning growth control used the same 500 updates at peak `3e-4` with weight decay 0.1.

The Studio executed revision `4982b3395c2cace1c4295be8e0a47d93b099218a`. The repository includes its readable training source and an archive, plus the exact fitted tokenizer and checksummed records for every arm. The independent CPU verifier recalculates main losses, removal indices, the two refit recoveries and Icelandic growth changes. Recreating the training weights requires the listed public data and a full run. [Reproduction commands](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Evidence and receipts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Source archive](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].zip)

[First Pubroot review](https://github.com/buildngrowsv/pubroot-website/issues/577)