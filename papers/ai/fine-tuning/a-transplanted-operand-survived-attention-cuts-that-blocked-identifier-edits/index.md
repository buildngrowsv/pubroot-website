---
title: "A transplanted operand survived attention cuts that blocked identifier edits"
paper_id: "2026-472"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:05:07Z"
abstract: "Blocking the final token's direct read of the edited assignment still allowed the desired computed digit to win in 384 of 456 native-correct pairs. Closing the eight blocks previously selected on identifier edits left all 456 numeric reversals. Opening only the weaker time-matched eight supported 434. In the earlier identifier experiment, closing the direct edge gave zero reversals, and closing the stronger eight left 21 of 359."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Blocking the final token's direct read of the edited assignment still allowed the desired computed digit to win in **384 of 456** native-correct pairs. Closing the eight blocks previously selected on identifier edits left **all 456** numeric reversals. Opening only the weaker time-matched eight supported 434. In the earlier identifier experiment, closing the direct edge gave zero reversals, and closing the stronger eight left 21 of 359.

![Native retention and counterfactual outcomes under the five frozen attention masks](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-attention.png)

## Reusing the masks in a different computation

Use the 512 new Python pairs at indices 119000–119511. Each program assigns a digit, then adds or subtracts a constant before the final incomplete assertion. Both possible answers differ from either operand. Separate 7B donor functions at indices 120000–120511 return the target operand. The host edits its earlier assignment after block 10 using the exact saved seven-coordinate affine map from the one-pass study. The donor needs only the target activation for each host pass. The source and the edit are identical across all edited masks for that prompt. The frozen checkpoints are Qwen2.5-Coder-7B base revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. [Original map and fit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered cross-task protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Reuse the previous identifier masks without choosing any new layers. The stronger set is blocks 20, 21, 26, 33, 37, 38, 44 and 45. The weaker set is 22, 24, 27, 32, 34, 35, 42 and 48. The two sets have equal counts in each of four depth bins. A mask varies only the availability of a direct read from the assignment to the final prediction token. Other positions can receive the edit and pass information onward. Each mask has its own clean baseline. [Identifier calibration and result](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Mask and scoring code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

A pair qualifies if both correct unedited digits are unique maxima across the whole vocabulary under every mask. Reversal requires both counterfactual digits to be unique maxima. CPython verifies all candidate outcomes. The native counts use each mask's own full panel. All reversal counts use the same 456-pair intersection.

| Direct-read availability | Native pairs correct out of 512 | Shared pairs reversed out of 456 |
|---|---:|---:|
| All blocks | 510 | 456 |
| Closed throughout | 458 | 384 |
| Strong eight only | 501 | 456 |
| Weaker eight only | 481 | 434 |
| All except the strong eight | 506 | 456 |

The stronger set exceeded the weaker set by 4.82 points, with a paired 95% interval of +2.85 to +7.02. This fell below the registered 20-point margin. Removal of the stronger set changed none of the paired outcomes. With the direct read closed, 84.21% of the shared pairs still flipped, exceeding the registered 15% ceiling for the identifier-style pattern. The clean baseline also lost pairs under that mask, so the 384 reversals describe the matched native-correct cohort. The intervention starts at the assignment and the final token cannot read it directly, which establishes an indirect route for these cases. This comparison changes the task and source edit together. It identifies a difference in propagation under the tested protocols, with the specific relay tokens left to the following experiment. [Saved ranks, prompts and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [First-relay protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/numeric_attention_study/verify.py` to re-execute all programs and recompute every result. The Studio run took three minutes and 33 seconds under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed testing model components separated by attention walls. OpenAI Codex designed, operated and verified the comparison and assisted with writing.

## Follow-up qualification of a single first-hop span

A separate 512-pair panel tested two equally long spans near the return expression. One span was the operand's identifier and the other immediately preceded it. We restricted the edited assignment to sending only to one span at a time, while its self-read remained available. Both restricted clean arms solved zero complete native pairs. Unrestricted attention solved 508, and leaving all relays available solved 441. Blocking the final direct edge and the variable-use span, while leaving other relays available, solved 435. The shared native-correct cohort for the five-arm analysis was empty. That leaves the first-hop hypothesis unidentified under these restrictions. [Registered follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Saved ranks and spans](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-results) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Qualification counts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-audit.json)