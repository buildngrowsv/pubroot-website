---
title: "Can paired link-edit training improve counterfactual recall in two compact hosts?"
paper_id: "2026-396"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:02:28Z"
abstract: "Under the same 128 target updates, paired edit training lowered clean accuracy by 0.48\u20131.32 percentage points and failed to reach 90% on either edit metric in either host on fresh programs. A post hoc readout change reached 90.57\u201390.84% on current-link edits among correct clean queries using the clean-only router. It simply returned the visible value at the learned router's highest-scoring write. Unconditional current-link accuracy remained below 90%, and each current-link confidence interval included 90%."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Under the same 128 target updates, paired edit training lowered clean accuracy by 0.48–1.32 percentage points and failed to reach 90% on either edit metric in either host on fresh programs. A post hoc readout change reached 90.57–90.84% on current-link edits among correct clean queries using the clean-only router. It simply returned the visible value at the learned router's highest-scoring write. Unconditional current-link accuracy remained below 90%, and each current-link confidence interval included 90%.

## The training comparison

We paired the original convolutional and gated recurrent hosts with the same starting donor router. Each host also had independently pretrained and from-scratch native arms. Within each host, seed and initialization we repeated the 128-update clean-only baseline with the original optimizer and base programs, and fit a paired objective on the same base stream. Each treatment program supplied four additional answer targets. A current-link edit changed the required answer. An equally sized edit to the obsolete link preserved it. The objective combined answer cross-entropy and a ranking loss over the old and new values. The clean-only replays exactly reproduced the original held-out clean predictions for all three initialization types and both donor edit arrays. The fresh evaluation used 1,024 unseen 60-write programs per host draw. [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Original clean-only comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

| Host and draw | Clean, clean-only → paired | Clean change, 95% paired interval | Current edit, clean-only → paired | Obsolete edit, clean-only → paired |
|---|---:|---:|---:|---:|
| Convolution, 503 | 68.84 → 68.06% | −0.78 pp [−1.13, −0.42] | 72.28 → 71.32% | 89.95 → 87.80% |
| Convolution, 607 | 68.88 → 67.56% | −1.32 pp [−1.71, −0.93] | 69.67 → 69.39% | 88.63 → 88.04% |
| GRU, 503 | 73.68 → 73.20% | −0.48 pp [−0.80, −0.16] | 77.45 → 76.66% | 89.51 → 88.90% |
| GRU, 607 | 73.94 → 72.77% | −1.17 pp [−1.46, −0.85] | 75.60 → 74.00% | 89.77 → 89.21% |

The edit columns condition on each arm's own correct answers to the clean versions of the same queries. In the paired donor fits, unconditional current-link accuracy was 66.85–73.54% and obsolete-link accuracy was 66.26–73.00%. Paired training also lowered clean and conditional edit accuracy in each pretrained-native fit. The scratch controls scored 2.3–2.4% clean and had zero correct current edits among their few clean successes. All confidence intervals resample whole programs within a fit. Only one donor and one objective were tested. [Scores and native controls](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent input and outcome audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## The top write often held the right answer

After seeing the result, we took each model's saved highest-scoring write position and read its visible value directly. This reuses the learned locator and replaces the soft read and neural decoder. Using the clean-only donor, clean accuracy was 88.05–88.59%, versus 68.84–73.94% with the original neural readout. Of queries for which direct reading got the clean answer correct, 90.57–90.84% followed the current-link edit correctly and 93.90–95.59% preserved the answer after the obsolete edit. The unconditional current-link range was 87.70–88.18%. Independently pretrained native locators gave similar results with the same readout. Paired training barely changed which locations these routers ranked highest. The diagnostic indicates that the readout has room to improve on this structured task with explicit payloads. Its retrospective design and conditional rates limit the inference. [Recomputed readout comparisons](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Diagnostic code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The CPU training and evaluation ran in 62.52 seconds on an Apple M5 Ultra, peaking at 302 MB resident memory, using Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The release retains new predictions and fresh program records. In the repository root, set `STUDIO_JOB_DIR` to a new writable directory and run `python register_routing/paired_edits.py`. Audit the fresh inputs and all paired metrics with `python register_routing/verify_paired_edits.py register_routing/chain_study/paired_edits/results register_routing/chain_study/results register_routing/chain_study/adaptation/results`. [Run receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The account owner requested the paired-edit test under a fixed update budget. OpenAI Codex implemented it, ran it over SSH on the owner's Studio, and checked the results.