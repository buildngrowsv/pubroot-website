---
title: "One answer-free gain restored the borrowed 32B operand edit on 434 of 507 pairs"
paper_id: "2026-476"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:09:48Z"
abstract: "A scalar of 2.625, measured from native assignment-state differences, raised the borrowed 14B interface from 92 to 434 full-vocabulary reversals in the frozen 32B receiver. The earlier per-prompt norm match using a fitted 32B interface reversed 414. Equal-norm random directions reversed zero. The scalar is measured on separate calibration prompts without arithmetic answers or a fitted 32B mapping."
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A scalar of **2.625**, measured from native assignment-state differences, raised the borrowed 14B interface from **92 to 434** full-vocabulary reversals in the frozen 32B receiver. The earlier per-prompt norm match using a fitted 32B interface reversed 414. Equal-norm random directions reversed zero. The scalar is measured on separate calibration prompts without arithmetic answers or a fitted 32B mapping.

![Full-vocabulary reversal counts for both magnitude rules and the random control](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Estimating the gain

Use 128 direct-return Python pairs at generator indices 123000–123127. In each pair, two otherwise identical functions assign different digits to a variable. Record the entire native 14B assignment state after block 10 and the native 32B assignment state after block 13. Within each model compute the Euclidean distance between the two states. The median of the 128 per-pair ratios, 32B distance divided by 14B distance, is 2.624717. The calibration requires matched input prompts and a known assignment location. It uses no output scores or arithmetic answer labels. [Registered gain rule](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Calibration distances and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

We use the exact 512 held-out arithmetic pairs from the earlier comparison and their separate 7B donor functions. For each host case, read the target donor operand's declaration after block 6. The original 14B affine map supplies a proposed replacement in its seven-coordinate basis. The 32B assignment receives that edit direction multiplied by the single gain. The new random arm assigns an equal-norm edit to the 14B orthogonal basis. The frozen model revisions and original map are identical to the raw test. The verifier checks the digests of the original map and the prompt archive. [Prior map and model identities](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Raw-magnitude comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

## Full-vocabulary outcomes

A shared pair qualifies if both correct unedited digits are uniquely highest-ranked in each run. A reversal requires the alternate computed digit to be uniquely highest-ranked in both edited versions. Each run had the same 507 clean pairs.

| Method in the 32B host | Paired reversals out of 507 |
|---|---:|
| Original 14B magnitude | 92 |
| Single answer-free gain | 434 |
| Equal-norm random direction | 0 |
| Per-prompt magnitude from the fitted 32B interface | 414 |

The gain improved on the raw direction by 67.46 percentage points [63.51, 71.60]. Its advantage over the previous norm match was 3.94 points [2.17, 5.92]. It cleared the preregistered thresholds. The two scaling methods differ geometrically. The scalar gain simply changes the norm of the same direction, and the median resulting norm is larger than the previous per-prompt match. The result supports a single scale estimate on this fixed held-out panel. Its scope includes known assignment locations, paired input contrasts for calibration, and two checkpoints from the same model family. [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Audited differences and norm ratios](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Run `uv run --with numpy python nested_surgery/numeric_scalar_study/verify.py` to recompute the scalar, archives, matched norms and paired comparisons. The Studio run took two minutes and 44 seconds using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5 on the owner's Apple M5 Ultra. The owner proposed larger-scale expert transplantation. OpenAI Codex designed and ran the comparison, verified its outputs and assisted with writing. [Pinned execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)