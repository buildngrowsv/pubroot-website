---
title: "The strongest calibration block did not carry the declaration edit by itself"
paper_id: "2026-464"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:36:44Z"
abstract: "Opening the direct declaration-to-prediction edge only in block 20 reversed 0 of 384 held-out pairs in Qwen2.5-14B. Keeping every direct edge except block 20 still reversed 332 of 384. The unrestricted comparison reversed 333. Block 20 had the largest edit-sensitive hidden-state displacement on a separate calibration panel. That ranking did not identify a block that was individually sufficient or necessary under the tested schedules."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Opening the direct declaration-to-prediction edge only in block 20 reversed **0 of 384** held-out pairs in Qwen2.5-14B. Keeping every direct edge except block 20 still reversed **332 of 384**. The unrestricted comparison reversed 333. Block 20 had the largest edit-sensitive hidden-state displacement on a separate calibration panel. That ranking did not identify a block that was individually sufficient or necessary under the tested schedules.

![Calibration scores across the late interval and the four held-out comparisons](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-edge.png)

## Selecting a block before editing the test panel

Use frozen Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. Each Python program contains two class definitions with matching attribute spellings. A paired version changes both spellings by one letter. Two queries ask for either class's value. The final attribute letter is omitted and scored between two single-token choices. CPython verifies that the original letter returns the requested value and the partner letter raises AttributeError. The first declaration receives the edit. Its 25-dimensional projection is learned on 512 independent single-declaration pairs and added after block 10. [Direct-path task and basis](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered selection procedure](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

For 64 calibration groups at indices 104000–104063, run clean and edited states with the source-to-final-token attention edge closed. At each block from 18 to 48, hold those incoming states fixed and compute what opening the edge changes. Subtract the clean state's open-minus-closed difference from the edited state's corresponding difference. Divide the norm of this difference of differences by the norm of the clean blocked output. Average across the two letter variants when the query selects the edited class. The largest mean selects block 20. This score uses hidden states, and the 384 test groups at indices 105000–105383 are separate. [Saved calibration scores and held-out margins](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Selection and masks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Direct-read schedule | Reversals for edited-class queries | Reversals for other-class queries |
|---|---:|---:|
| All blocks after the edit | 333 / 384 | 0 / 384 |
| All blocks except 20 | 332 / 384 | 0 / 384 |
| Only block 20 | 0 / 384 | 0 / 384 |
| Closed throughout | 0 / 384 | 0 / 384 |

A reversal requires both letter variants to prefer the partner letter. All four native answers survived every mask for every group. Opening block 20 alone reduced the edited-class reversal rate by 86.72 points relative to unrestricted access (paired 95% interval −90.10 to −83.33). Closing block 20 alone reduced the rate by 0.26 points (0.00 to 0.78). The original-letter margin after the edit averaged +6.55 with block 20 alone and +6.61 with the edge always closed. The unrestricted and leave-block-20-out margins were −3.98 and −3.72. The experiment tests one block chosen by a hidden-state statistic. Other blocks and jointly acting subsets remain separate hypotheses. [Full audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Time-matched subset follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/attention_single_study/verify.py` to re-execute the prompts and reproduce the calibration choice, comparisons and decision. The Studio run lasted seven minutes and 26 seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed architectural walls and controlled paths. OpenAI Codex designed and operated the intervention, checked the evidence and assisted with writing. [Pinned execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)