---
title: "A frozen 7B coding graft added 30 attributable repairs among Python bracket decoys"
paper_id: "2026-548"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T14:56:00Z"
abstract: "On 256 new Python repair triplets with misleading brackets inside a string and comment, a frozen 7B-to-14B graft solved 63 complete groups. The matched host-feature bridge solved 33 and the shuffled-donor bridge solved 18. Setting the aligned donor input to its mean erased all 63 solves. Thirty groups met every attribution criterion, including success by the intact coding expert and failure of the native recipient and all matched controls. The intact 7B specialist solved 150 groups and remains the strongest observed endpoint on this task."
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On **256** new Python repair triplets with misleading brackets inside a string and comment, a frozen 7B-to-14B graft solved **63** complete groups. The matched host-feature bridge solved **33** and the shuffled-donor bridge solved **18**. Setting the aligned donor input to its mean erased all 63 solves. **Thirty groups** met every attribution criterion, including success by the intact coding expert and failure of the native recipient and all matched controls. The intact 7B specialist solved **150** groups and remains the strongest observed endpoint on this task.

![Matched control and graft scores in neutral and decoy layouts](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Why change the input?

On the original controlled repair panel, the donor bridge's 256/256 and the host-feature bridge's 253/256 left little headroom to separate effectiveness. Freeze those two bridges and the shuffled control from the released trial. Rewrite 256 fresh program triplets so the correct closing delimiter is preceded by a string and comment containing brackets that the parser must ignore. Compare the same programs with the brackets in the string and comment replaced by corresponding letters. Layouts share the 14B and 7B checkpoints, the frozen bridge weights, target positions defined by the end of each completion prompt and all evaluation logic. Tokenization may differ between the two layouts. The test compares the complete input shift. [Original graft comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Executable archive](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Every triplet differs by one opening delimiter across its three members. Each completion uses four candidate tokens, and the correct closer must be highest-scoring for all three members. The learned bridge adds a rank-32 projection of the final 7B MLP output to the residual stream of the frozen 14B model after block 27. The host control uses a learned bridge of the same size with a rank-32 projection of its own block-27 MLP output. The original adapters saw the same 64 training triplets and 64 Adam updates. The fitted weights and projection statistics for each arm were loaded from the earlier run and verified by SHA-256 before scoring. This experiment fits no parameters. The intervention complements prior frozen model composition by measuring strict per-group reliance under a controlled lexical change. [CALM](https://arxiv.org/abs/2401.02412) · [Source runner](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Held-out configuration | Neutral text | Bracket decoys |
|---|---:|---:|
| Untouched 14B host | 0 | 0 |
| Intact 7B specialist | 221 | 150 |
| Matched host-feature bridge | 104 | 33 |
| Shuffled-donor bridge | 84 | 18 |
| Aligned donor bridge | 86 | 63 |
| Aligned bridge, donor off | 0 | 0 |

The 71-group decline in the host-feature arm exceeded the 26-group headroom requirement. The aligned-minus-host difference was +11.72 percentage points on decoys (95% paired interval +5.47 to +17.97). The gain over the shuffled bridge was +17.58 points (+11.33 to +23.83) and over its own ablation +24.61 (+19.53 to +30.08). All three lower bounds and the ten-group strict criterion passed. In the neutral layout, the aligned-minus-host difference was −7.03 points (−15.63 to +1.56). The effect is conditional on the input shift. A cyclic exchange between triplet members retained 37 correct decoy groups, and no group followed all three substituted answers. Removing the donor reveals causal reliance in the aligned graft. The cyclic test gives no evidence for arbitrary control of the chosen bracket through the bridge. [Both sets of logits](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Neutral logits](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Exact ledger](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The result uses one trained set of bridges, one model family, constrained completions and synthetic but executable Python. It establishes comparative transplant value over the equally sized recipient interfaces in this setting. Running the intact 7B specialist remains more accurate and cheaper than running both models here.

## Reproduction

The pinned BF16 Qwen2.5 models, trained 168,960-parameter bridge, source code and exact panels are public. The Studio ran Apple M5 Ultra arm64, 256 GiB memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, tokenizers 0.23.3 and NumPy 2.5.5. The 137.74-second run used the exact models registered in the prior comparison. Run `uv run --with numpy python [REDACTED_SECRET].py` from the repo root to execute the matched repairs and reconstruct the scores and gates. For model replay, link the public prior result directory at `runs/large-qwen-learned-output-port` under a temporary `STUDIO_QUEUE_ROOT` and use the runner with a fresh `STUDIO_JOB_DIR`. The owner proposed the expert surgery and causal tests. OpenAI Codex implemented, ran, audited and documented the experiment. [Source revision receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt) · [Prior frozen bridges](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].safetensors)