---
title: "A moving reference left the seven-block transplant penalty intact in 32B"
paper_id: "2026-494"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T10:01:22Z"
abstract: "Holding only the donor's initial displacement while allowing the unedited reference to evolve gave 332 complete carry groups out of 512. Freezing the seven absolute values gave 333, and a single early splice gave 358. Both seven-block policies preserved all 512 native groups. The native-relative hold kept the same length-change asymmetry as the absolute hold."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Holding only the donor's initial displacement while allowing the unedited reference to evolve gave **332 complete carry groups out of 512**. Freezing the seven absolute values gave 333, and a single early splice gave 358. Both seven-block policies preserved all 512 native groups. The native-relative hold kept the same length-change asymmetry as the absolute hold.

![Complete carry groups for the one-shot, absolute and native-relative edits](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-reference.png)

## Reference and controls

We used the same two independently encoded operands, 512 four-variant arithmetic groups, seven-coordinate mapping and scalar gain of 2.624717 as the prior registered comparison. The donor is frozen BF16 Qwen2.5-Coder-7B ([0396a761](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/tree/0396a76181e127dfc13e5c5ec48a8cee09938b02), width 3,584, read after block six). The original seven axes were fitted in Qwen2.5-14B ([97e1e763](https://huggingface.co/Qwen/Qwen2.5-14B/tree/97e1e76335b7017d8f67c08a19d103c0504298c9), width 5,120, block ten). The frozen BF16 recipient is Qwen2.5-32B ([1818d358](https://huggingface.co/Qwen/Qwen2.5-32B/tree/1818d35814b8319459f4bd55ed1ac8709630f003), width 5,120, 64 blocks). The early transplant is performed at both assignment positions after block 13. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [One-shot reference](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Absolute hold](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Let `B` be the original 5,120×7 basis. For each assignment, define the fixed displacement `u = (h₁₃ᵉᵈⁱᵗ − h₁₃ⁿᵃᵗⁱᵛᵉ)B`. At blocks 14 through 20, compute the unedited model's projection plus that same displacement. If the edited activation is `hₖ`, add `(hₖⁿᵃᵗⁱᵛᵉ B + u − hₖ B)Bᵀ` at that token. All other positions and directions continue with normal model weights. Projection is float32 before casting back to BF16. The orthogonal arm uses the same procedure with the matched pre-cast edit norm at the early splice and its own seven-dimensional basis. The native arm applies a zero displacement. An answer qualifies when each expected digit uniquely wins over the full vocabulary and a valid terminator follows. A group requires all four answers. [Implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Prompt archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Results

| Intervention | Complete groups, out of 512 | One to two digits, out of 747 | Two to one digit, out of 747 |
|---|---:|---:|---:|
| One-shot edit | 358 | 689 | 669 |
| Absolute seven-block hold | 333 | 705 | 632 |
| Native-relative seven-block hold | 332 | 700 | 632 |
| Native-relative orthogonal control | 0 | 0 | 0 |

The relative hold gained nine complete groups and lost ten versus the absolute hold. Its difference was **−0.20 percentage points**, paired 95% interval **−1.76 to +1.56**. It lost 26 groups net versus one-shot editing, **−5.08 points**, paired interval **−8.20 to −1.95**. Neither predeclared condition for recovery was met. The data bound improvement from letting the native coordinates move under this specific seven-block schedule. The main penalty persisted when we preserved only the donor displacement. This comparison uses two known sites on one carry panel. It requires seven extra native blocks and measures outcome quality, with no efficiency claim. [World and token counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

Run `uv run --with numpy python nested_surgery/numeric_relative_32b_study/verify.py` to execute and verify the Python programs, reconcile all archive digests, count token-level outcomes and recreate the paired intervals. The 454-second Studio run used 67.0 GB peak MLX allocation on an Apple M5 Ultra with 80 GPU cores, 256 GiB unified memory, Metal 4, macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed fixed activation references. OpenAI Codex implemented, ran and audited the comparisons and assisted with writing. [Version-pinned execution](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)