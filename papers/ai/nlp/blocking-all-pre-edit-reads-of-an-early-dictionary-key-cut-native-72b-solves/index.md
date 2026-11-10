---
below_floor: true
quality_floor: 7.0
title: "Blocking all pre-edit reads of an early dictionary key cut native 72B solves"
paper_id: "2026-533"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T13:58:22Z"
abstract: "Preventing later tokens from attending to the early key during the first 17 blocks reduced fully correct native groups from 173 to 17 of 256 in frozen Qwen2.5-72B. An equal-size mask on the preceding assignment-syntax token retained 173. On the 17 groups solved in all three settings, a whole-state swap switched 17 when key access had been blocked and 16 under either control. The shared cohort missed the registered 100-group requirement, leaving the steering hypothesis unresolved."
score: 6.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Preventing later tokens from attending to the early key during the first 17 blocks reduced fully correct native groups from **173 to 17 of 256** in frozen Qwen2.5-72B. An equal-size mask on the preceding assignment-syntax token retained 173. On the 17 groups solved in all three settings, a whole-state swap switched 17 when key access had been blocked and 16 under either control. The shared cohort missed the registered 100-group requirement, leaving the steering hypothesis unresolved.

![Native coverage and full-state intervention outcomes under the early attention masks](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-key-mask.png)

## Remove access before the normal intervention site

The same six-prompt dictionary groups come from the fresh program panel. Each program assigns a selector before a two-entry dictionary and returns the selected value plus a signed offset. Two dictionaries pair opposite payload orderings and a third maps both keys to the same value. Each case includes both values of the key. Earlier studies found much more reliable whole-state and donor steering when the key assignment followed the table and preserved that gain at a matched token distance. This comparison uses the original early assignment and changes only which attention edges exist before the key state is swapped. [Fresh program panel](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Matched-gap study](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered control](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

During the first 17 blocks, the key mask removes every attention edge from a position after the key to the key numeral. Its matched control removes exactly the same number of edges from those query positions to the preceding assignment-syntax token. All positions through the key itself continue to use causal attention. At the boundary, run either the same masked model with its own key state or with the entire 8,192-coordinate state exchanged with the paired prompt. The paired version differs only at the key numeral. Later layers use ordinary causal attention in both cases. The unrestricted arm uses the exact archived early native and swap scores. The experiment applies no new training or fitting. [Pinned mask and scorer](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Unrestricted scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

| Condition | Native correct, all six | Native correct, original table pair | Native correct, mirrored pair | Native correct, constant table pair | Whole-state switches in shared cohort |
|---|---:|---:|---:|---:|---:|
| Unrestricted | 173/256 | 206/256 | 220/256 | 255/256 | 16/17 |
| Block syntax reads before cut | 173/256 | 206/256 | 222/256 | 255/256 | 16/17 |
| Block original-key reads before cut | 17/256 | 77/256 | 78/256 | 220/256 | 17/17 |

The swap outcome requires the answer token to rank uniquely first over the full vocabulary in both directions and both mirrored tables. All three arms preserved the correct output in the constant table in every shared group. The key mask's paired switching gain over either control in that subset was +5.88 points (95% interval 0.00 to +17.65). The result fails the shared coverage and effect-size gates. The main interpretable finding is large native loss when every later position loses access to the original key through the early blocks. The test leaves open a possible advantage from blocking a narrower set of reads. The next registered test limits the mask to query tokens on the dictionary assignment line. [Masked ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Run `uv run --with numpy python [REDACTED_SECRET].py` to verify the source program and score hashes, execute program assertions, and recompute native coverage and conditional switch comparisons. The Studio run took 491 seconds and reached 146.71 GB peak MLX allocation on Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory. The engine used macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed testing walls and conditional routing. OpenAI Codex implemented, ran, audited and documented the comparison. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)