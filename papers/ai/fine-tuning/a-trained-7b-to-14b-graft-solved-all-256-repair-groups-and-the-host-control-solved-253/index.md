---
title: "A trained 7B-to-14B graft solved all 256 repair groups and the host control solved 253"
paper_id: "2026-544"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T14:44:36Z"
abstract: "A learned 32-feature connection from a frozen Qwen2.5-Coder-7B into frozen Qwen2.5-14B solved 256 of 256 fresh Python repair groups. Setting the donor input to its calibration mean while keeping the trained connection in place erased 226 of those solves. An equal-size connection fed by the host's own activations solved 253 of 256. The trained recipient relied heavily on the donor in that configuration, while the donor missed the registered test for a capability advantage over matched adaptation."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A learned 32-feature connection from a frozen Qwen2.5-Coder-7B into frozen Qwen2.5-14B solved **256 of 256** fresh Python repair groups. Setting the donor input to its calibration mean while keeping the trained connection in place erased **226** of those solves. An equal-size connection fed by the host's own activations solved **253 of 256**. The trained recipient relied heavily on the donor in that configuration, while the donor missed the registered test for a capability advantage over matched adaptation.

![Held-out complete repairs and donor-off control](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Train the connection against the final answer

An earlier splice transplanted the 7B final MLP into the 14B host, used an affine output map trained to reconstruct native 14B activations, and adapted host block 28. The splice solved zero complete repair groups. A subsequent cross-test supplied the exact native expert output. Closing-bracket log odds moved by +2.111 in the 7B model and −0.009 through the old output map into the 14B model. The new intervention keeps the full trained recipient computation and adds a learned residual update at the target prediction position after block 27. The update depends on the intact expert MLP running on the original 7B prefix. Only the bridge sees task gradients, which pass through the frozen 14B tail. This follows prior model stitching and small-interface composition between frozen models. It asks whether the resulting skill relies on the specialist and whether the host can learn the same skill from its own state at the same training and parameter budget. [Earlier splice](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Output-boundary diagnosis](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Model stitching](https://arxiv.org/abs/2106.07682) · [CALM](https://arxiv.org/abs/2401.02412)

Each group contains three executable Python prompts with the same suffix. Changing one opening delimiter changes which closing delimiter completes the code. A complete group must answer all three correctly. We score the same four single-token candidates, including a colon distractor, for both native models and all bridge conditions. Fit the bridges on 64 new triplets with disjoint IDs from the 256 test triplets. For each feature source, compute 32 directions from within-triplet centered activation differences on training examples only, then subtract the training mean and scale each projected coordinate by its training standard deviation. The bridge has `32 × 5,120 + 5,120 = 168,960` trainable FP32 weights. Each arm uses the same zero initialization, batches of four triplets, four passes through the 64 groups and 64 Adam updates at 0.002. In normal inference each bridge receives a single prompt's features. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Pinned runner](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Use of the donor and incremental skill

| Held-out condition | Complete groups out of 256 |
|---|---:|
| Untouched 14B host | 0 |
| Untouched 7B coding donor | 40 |
| Learned host-feature bridge | 253 |
| Learned bridge, randomized donor pairing | 229 |
| Learned bridge, aligned donor | 256 |
| Aligned bridge with mean-input ablation | 30 |
| Aligned bridge with a cyclic donor swap | 77 |

The aligned bridge beat the shuffled condition by 10.55 points (95% paired interval +7.03 to +14.45) and its own ablation by 88.28 points (+84.37 to +92.19). It beat the host-feature bridge by 1.17 points (0.00 to +2.73), below the required five points. The intact donor offered 40 opportunities that the untouched host missed. Zero of those groups qualified as strictly donor-dependent new solves over the matched learned controls. In the cyclic swap, 89 of 256 groups gave all three answers associated with the substituted donor, and 77 retained all three original answers. Both the unchanged-input ablation and the exchanged-input test hold the bridge parameters fixed. [Exact scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Paired ledger](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Reconstructed counts and interventions](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

This establishes donor use for a learned connection inside this 14B host on constrained repairs. The host's own activations nearly saturate this benchmark after matched training, leaving three groups of observed headroom. No evidence supports the registered comparative transplant claim on this panel. The result covers one training order, one partially synthetic program family, and constrained scoring. A parser can solve this exact task and the aligned route requires a separate 7B forward pass. A more discriminating comparison would freeze the learned connections and score under a prespecified formatting or program-family shift on which the host-feature control has headroom.

## Reproduction

The Studio used BF16 frozen base models with the released Qwen checkpoints recorded in the results, on an arm64 Apple M5 Ultra with 256 GiB unified memory. Software was macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The production run took 112.75 seconds and peaked at 46.15 GB MLX allocation. From the repo root, the verifier below executes the candidate repairs, checks the fresh group split, verifies the bridge hash and reconstructs all registered endpoints. The production runner uses the pinned checkpoint loader and the earlier archived output-boundary programs to exclude overlap. The owner proposed the graft experiments and asked for causal ablations. OpenAI Codex wrote, ran, independently audited and documented the test. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Training history](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Trained bridges and projections](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].safetensors) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt)

```sh
uv run --with numpy python nested_surgery/learned_output_port_study/verify.py
```