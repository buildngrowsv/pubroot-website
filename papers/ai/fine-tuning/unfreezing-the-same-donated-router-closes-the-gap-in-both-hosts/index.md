---
below_floor: true
quality_floor: 7.0
title: "Unfreezing the same donated router closes the gap in both hosts"
paper_id: "2026-394"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T02:50:18Z"
abstract: "Letting the original router adapt recovered 10.26\u201310.90 percentage points of held-out accuracy after 128 updates. The adapted donor finished 0.20\u20130.38 points ahead of the matched-pretraining native router in both host architectures and both training draws. Every frozen outcome, including the link-edit predictions, reproduced exactly. The adapted graft remained sensitive to the position scores and fell short of 90% on each link-edit check."
score: 6.6
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Letting the original router adapt recovered 10.26–10.90 percentage points of held-out accuracy after 128 updates. The adapted donor finished 0.20–0.38 points ahead of the matched-pretraining native router in both host architectures and both training draws. Every frozen outcome, including the link-edit predictions, reproduced exactly. The adapted graft remained sensitive to the position scores and fell short of 90% on each link-edit check.

## Change one training decision

The frozen comparison reused the same one-hop locator in a convolutional payload host and a gated recurrent payload host. Each model follows two current alias links before choosing an original or latest register write. For this follow-up we reconstructed seed 101 and matched its archived answers and position choices on all 16,384 original one-hop queries. Within each host draw we initialized both arms with identical host and router weights. One arm trained the host while keeping the router frozen. The other allowed the same 2,306 weights to update jointly with the host. Both used the previous 128 updates of 64 programs, the same optimizer and objective, and the same test draws. Every router weight changed in the adapted arms. The shared starting donor and the re-run frozen arms stayed bitwise fixed. [Prespecified plan](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Original study and controls](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

| Host and draw | Frozen | Adapted donor | Pretrained native | Adapted minus frozen | Adapted minus native, paired 95% interval |
|---|---:|---:|---:|---:|---:|
| Convolution, 503 | 58.84% | 69.74% | 69.37% | +10.90 pp | +0.38 pp [+0.27, +0.49] |
| Convolution, 607 | 58.59% | 69.18% | 68.98% | +10.59 pp | +0.20 pp [+0.13, +0.27] |
| GRU, 503 | 63.17% | 73.76% | 73.46% | +10.59 pp | +0.31 pp [+0.22, +0.40] |
| GRU, 607 | 63.26% | 73.52% | 73.30% | +10.26 pp | +0.23 pp [+0.15, +0.31] |

The preregistered closure margin required every adapted-minus-native lower bound to exceed −1 point. All four exceeded zero. The matched source-budget comparator used different one-hop initializations. The effect of unfreezing is estimated by comparing the identical donor with itself under two training conditions. The small advantages over independently pretrained native routers describe these particular seed pairs and one synthetic task. The intervals resample 1,024 held-out programs per fit. [Paired program results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent recomputation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## The exact same link edits

When the current first alias was edited, the adapted models produced the correct new value on 72.8–79.7% of cases that they got right before the edit, versus 63.3–69.6% frozen. Editing the obsolete link preserved 88.3–89.7% of clean correct answers, versus 81.1–83.9% frozen. These denominators are arm-specific. The released unconditional counts use the same 2,048 edited queries per arm. Shifting the adapted router's final read scores reduced clean accuracy to 0.48–0.73%, consistent with the adapted hosts continuing to rely on routing. The original 90% edit criterion remains unmet. [Edit counts and read-score control](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The comparison ran on the Mac Studio CPU in 10.53 seconds, with 155 MB maximum resident memory. The release retains only the new per-query predictions. It reuses the original verified input, control and oracle records. Set `STUDIO_JOB_DIR` to a new writable directory and run `python register_routing/unfreeze_chain.py` from the repository root with MLX and NumPy. To verify the public results without Apple hardware, run `python register_routing/verify_unfreeze_chain.py register_routing/chain_study/adaptation/results register_routing/chain_study/results` with NumPy. The account owner requested the exact-donor comparison. OpenAI Codex ran the experiment over SSH, audited the outputs and assisted with writing. [Studio receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)