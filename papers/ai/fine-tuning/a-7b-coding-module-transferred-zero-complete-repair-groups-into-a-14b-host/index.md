---
title: "A 7B coding module transferred zero complete repair groups into a 14B host"
paper_id: "2026-403"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:20:45Z"
abstract: "The intact Qwen2.5-Coder-7B solved 54 of 256 fresh Python repair groups that the general 14B model missed. We replaced the feed-forward module in block 27 of the 14B host with the coder's final feed-forward module, then trained all of host block 28. The graft solved zero complete groups. The equally trained native host solved two, and a shuffled coding module with its own fitted interface solved thirteen. Turning the trained graft off lost zero groups and rescued two. This closes one transplant site, interface and training budget on a task the intact donor could demonstrably perform."
score: 7.6
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The intact Qwen2.5-Coder-7B solved 54 of 256 fresh Python repair groups that the general 14B model missed. We replaced the feed-forward module in block 27 of the 14B host with the coder's final feed-forward module, then trained all of host block 28. The graft solved zero complete groups. The equally trained native host solved two, and a shuffled coding module with its own fitted interface solved thirteen. Turning the trained graft off lost zero groups and rescued two. This closes one transplant site, interface and training budget on a task the intact donor could demonstrably perform.

![Complete repair groups on the fresh panel](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-repairs.png)

## What the controls had to explain

Bansal and colleagues used learned connections between segments of trained networks to test whether their representations were compatible. We asked a narrower question. Can one frozen feed-forward module from a specialist transfer an identified behavior into a larger host, and do any newly solved groups disappear when that module is removed? The smaller 0.5B coding donor had solved just seven of 256 original groups and its 1.5B graft solved zero. On those same original groups the 7B donor solved 49 and the 14B host solved zero, clearing the larger transplant's qualification threshold. For the transplant itself we reserved 256 new groups. [Model stitching](https://arxiv.org/abs/2106.07682) · [Smaller surgery](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Larger qualification](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered graft and attribution protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Each group has three executable Python programs with the same suffix. Changing one opening character changes which closing character must be inserted. We score four candidate tokens per prompt. A group counts only if the model correctly repairs all three. The untouched native host chose a colon in 761 of the fresh 768 prompts, although no target was a colon. An ordinary parser can solve this synthetic task exactly. Requiring performance above the equally trained native host controls for learning how to answer the benchmark.

## What crossed the boundary?

Two fixed affine maps fitted on 6,144 training-only token states translate into the donor's coordinates and back into the host. Block 27 keeps its native attention and residual path. All twenty blocks after block 28 remain frozen. Only the 275,268,608 parameters of block 28 receive task gradients. Every arm receives the same 16 labeled training examples and eight full-batch Adam updates at 0.00002, initialized separately from the same original block-28 weights. The archived scores use the checkpoints' released precision. Full and cached scoring agreed exactly on the eight preflight prompts. [Pinned implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Calibration and training artifacts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

| Module in host block 27 during training | Correct prompts / 768 | Complete groups / 256 |
|---|---:|---:|
| Native host | 299 | 2 |
| Zero output | 265 | 0 |
| Direct affine map | 222 | 1 |
| Shuffled 7B coder | 469 | 13 |
| Intact general 7B donor | 159 | 0 |
| Intact coding 7B donor | 251 | 0 |

The intact coding graft trailed the trained native host by 0.78 percentage points on complete groups (paired 95% bootstrap interval −1.95 to 0.00). It trailed the shuffled coding graft by 5.08 points (−7.81 to −2.73). Shuffling breaks the correspondence of intermediate channels inside the donor MLP. The shuffled arm cannot establish that an intact specialist capability was transplanted. A single training draw also leaves the source of its relative advantage open.

Holding the trained coding receiver fixed, zeroing the donor output rescued groups 30140 and 30240. Restoring the native module solved zero groups. The intact graft had zero new groups relative to the equally trained native host, giving zero strict donor-dependent solves. The prespecified criterion was ten such groups plus five-point advantages over the trained native and shuffled controls with positive lower paired bounds. A standalone rerun reproduced every untouched host choice on the fresh set. [Group IDs, contrasts and intervention results](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent reconstruction](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Raw four-candidate logits](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])

The standalone 7B coder solved 54 groups in this fresh sample. The splice therefore missed 54 opportunities that the intact specialist demonstrably had. The next diagnostic exchanges the selected feed-forward module’s output between related prompts inside the functioning 7B donor itself. That tests whether the module carries the opening character in its original setting before choosing another transplant site. [Donor-site protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Standalone opportunity IDs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-result.json)

These data cover one model family, one splice site, a simple repair generator and one small supervised budget. Candidate scoring measures constrained delimiter repair. Real-world coding tasks, other donor circuits, independent training orders and other interfaces remain open. The owner proposed placing a smaller expert one block earlier and training the next host block. OpenAI Codex implemented the tests, ran them on the owner's Apple M5 Ultra, reconstructed the outcomes and assisted with writing.