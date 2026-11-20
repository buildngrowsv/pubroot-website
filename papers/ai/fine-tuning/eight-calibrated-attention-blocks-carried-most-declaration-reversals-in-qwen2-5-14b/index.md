---
title: "Eight calibrated attention blocks carried most declaration reversals in Qwen2.5-14B"
paper_id: "2026-468"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T08:45:46Z"
abstract: "Opening the direct declaration-to-readout edge in eight calibrated blocks reversed 347 of 384 held-out Python pairs. Opening it in eight weaker blocks sampled from the same depth bins reversed zero. Unrestricted access reversed 359 pairs. Closing only the calibrated eight reduced that count to 21. All five schedules preserved every unedited answer."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Opening the direct declaration-to-readout edge in eight calibrated blocks reversed **347 of 384** held-out Python pairs. Opening it in eight weaker blocks sampled from the same depth bins reversed **zero**. Unrestricted access reversed 359 pairs. Closing only the calibrated eight reduced that count to **21**. All five schedules preserved every unedited answer.

![Calibrated blocks, depth-matched alternatives and their held-out reversal counts](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-edges.png)

## How the two sets were chosen

The task supplies two class definitions with the same attribute spelling and a final query for either class. An alternate version changes the suffix letter in both definitions. The final attribute is left one letter short. CPython checks that appending the correct letter reads the selected class's value and the alternative raises AttributeError. We compare both single-token completions. A reversal means both letter variants prefer the alternate letter. Only the first declaration receives the edit, after block 10 of frozen Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. The edit exchanges the partner difference along 25 directions learned from an independent set of 512 single-declaration pairs. [Task, masks and earlier controls](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered sparse comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

We reuse the hidden-state displacement scores for blocks 18–48 from the earlier 64-group calibration. Each score measures how much opening the edge at that block affects the final-token hidden state differently after an edit. Both input states are taken from trajectories where the edge is closed. Divide the resulting displacement by the reference hidden-state norm and average over the selected class's two variants. The strongest single block from that calibration failed on its own. This study uses four prespecified bins, 18–25, 26–33, 34–41 and 42–48. Within each bin take the strongest two scores and the weakest two of the remaining positions, resolving ties by smaller layer index. The sets were locked before the 384 held-out test groups at indices 116000–116383. [Archived single-block calibration](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Sparse mask implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

The stronger blocks are 20, 21, 26, 33, 37, 38, 44 and 45. The weaker blocks are 22, 24, 27, 32, 34, 35, 42 and 48. Each selected position allows the final token's direct read of the source declaration. All other causal edges remain available in all blocks. The clean and edited interventions differ only in the source state under their shared mask.

| Availability after block 10 | Edited-class reversals | Other-class reversals |
|---|---:|---:|
| All blocks | 359 / 384 | 0 / 384 |
| Calibrated eight only | 347 / 384 | 0 / 384 |
| Depth-matched weaker eight only | 0 / 384 | 0 / 384 |
| All except calibrated eight | 21 / 384 | 0 / 384 |
| Closed throughout | 0 / 384 | 0 / 384 |

All 384 groups remained eligible in every clean arm. The 347 stronger-set successes were all among the unrestricted successes. Opening the stronger eight beat the weaker eight by +90.36 percentage points (95% paired interval +87.24 to +93.23). The gap from unrestricted was −3.13 points (−4.95 to −1.56), meeting the 15-point sufficiency margin. Removing the stronger set cost 88.02 points (+84.64 to +91.15). Bootstrap draws resampled complete program groups. These interventions identify a small set of edges that carries most of this edit's two-choice effects in one frozen checkpoint. They leave open which members are needed together and whether the set transfers beyond identifiers. [Raw results and prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audited metrics](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Numeric pathway follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python nested_surgery/attention_sparse_study/verify.py` to reconstruct the calibration selections, execute the saved prompts and audit every comparison. The Studio run took eight minutes and 27 seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5. The owner proposed spatial walls and controlled paths. OpenAI Codex designed and operated the study, verified the outputs and assisted with writing. [Pinned execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)