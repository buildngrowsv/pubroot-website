---
title: "Which new Python repairs disappear when a transplanted coding expert is switched off?"
paper_id: "2026-362"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T00:44:45Z"
abstract: "A smaller coding model solved all 256 repairs used to qualify a donor, while the larger host solved 119. We transplanted the donor's final feed-forward module into host block 27 and trained host block 28 on 16 examples. On 512 more deeply nested Python programs the coding graft solved 335 and the equally adapted native host solved 331. Disabling the donor erased 44 of 140 new solves relative to the untouched host. Seven of those 44 had also been missed by the adapted native host. A four-entry suffix-only lookup solved all 512 problems, limiting what the result establishes about syntax."
score: 6.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A smaller coding model solved all 256 repairs used to qualify a donor, while the larger host solved 119. We transplanted the donor's final feed-forward module into host block 27 and trained host block 28 on 16 examples. On 512 more deeply nested Python programs the coding graft solved 335 and the equally adapted native host solved 331. Disabling the donor erased 44 of 140 new solves relative to the untouched host. Seven of those 44 had also been missed by the adapted native host. A four-entry suffix-only lookup solved all 512 problems, limiting what the result establishes about syntax.

![Correct repairs with intact, native, shuffled, general and disabled grafts](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-outcomes.png)

## Donor qualification and surgery

The Qwen2.5-Coder-0.5B donor and Qwen2.5-1.5B host received identical fill-in-the-middle prompts and chose one of four single-token repairs. A qualification win required a five-point donor lead with a positive paired bootstrap lower bound. The donor won 137 programs the host missed and lost zero. Its qualification advantage had a 95% interval of +47.7 to +59.8 percentage points. Qualification used nesting depths two and three. The independent evaluation used depths four through six, with twelve executable cases per program. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Generator](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Qualification evidence](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

The frozen graft used the existing training-only linear bridges. Conditions included native, removed, direct affine, shuffled-neuron, general-purpose donor and intact coding donor paths. Only the final full host block trained. Every condition had the same 16 balanced examples drawn from the previous simpler generator, eight Adam updates, and learning rate 0.00002. A cached scoring check stopped an earlier job before training. We used the full model and full vocabulary to score every choice in the reported study. Native logits reproduced the original model exactly in the scoring audit. Model stitching motivates fitted interfaces, and fill-in-the-middle training provides the task format. [Model stitching](https://arxiv.org/abs/2106.07682) · [Fill-in-the-middle training](https://arxiv.org/abs/2207.14255) · [Qwen2.5-Coder report](https://arxiv.org/abs/2409.12186)

| Block 27 condition | Correct before fitting | Correct after fitting |
|---|---:|---:|
| Native | 237 | 331 |
| Feed-forward output removed | 222 | 247 |
| Direct affine replacement | 238 | 307 |
| Shuffled coding graft | 242 | 306 |
| General-purpose donor | 229 | 360 |
| Intact coding graft | 220 | 335 |

The coding graft gained four net solves over the adapted native control. Its paired advantage was +0.78 points [−2.34, +3.71]. Against the shuffled graft it gained +5.66 points [+3.71, +7.81]. The general-purpose donor had the highest count on this panel. The intervals resample programs from four shared code forms. There was one supervised training draw. [All candidate logits and comparisons](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

## Following individual repairs through the intervention

The 335 correct programs included 140 the untouched host missed. The graft also missed 42 originally correct repairs. Of the 140 new solves, 23 were also missed by the equally trained native host. Disabling the graft with the trained host held fixed lost 44 repairs and rescued four. All 44 losses came from the 140 new solves. Seven losses came from the stricter set of 23. Their IDs were nested-71977-34, -40, -125, -376, -395, -453 and -478, each with the same nested-71977 prefix. Substituting the shuffled expert in the trained recipient left 301 correct. The predefined promotion required ten strict donor-dependent repairs and a five-point advantage over both controls. It closed. [All lost IDs and audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

An exploratory control mapped each post-gap suffix in the qualification panel to its repair. Four distinct suffixes predicted all 512 primary outcomes with no access to the nested code. These data establish a causal contribution to particular model answers under this benchmark. They cannot identify parsing or stack tracking. A follow-up uses one identical suffix and changes only the opening byte in otherwise identical program triplets. [Opener follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

## Reproduction

The release includes all prompts, hidden cases, candidate logits, training IDs, bridge digest, receipts and intervention identities. From the repository root run `python nested_surgery/verify.py nested_surgery/results/qualification nested_surgery/results/fit` with NumPy to recompile the candidate programs and reconstruct the item-level changes. The environment used Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5 on the Apple M5 Ultra. The prior study supplies the pinned public model revisions and training-only interfaces. [Verification code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Surgery code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Bridge construction](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

The account owner proposed moving an expert one block earlier, adapting the following block, and measuring which newly correct answers disappear when the donor is removed. OpenAI Codex implemented the study, ran it over SSH on the owner's Studio, audited the outcomes and assisted with writing.