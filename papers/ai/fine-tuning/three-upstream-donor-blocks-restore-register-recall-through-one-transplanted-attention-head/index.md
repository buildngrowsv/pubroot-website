---
title: "Three upstream donor blocks restore register recall through one transplanted attention head"
paper_id: "2026-378"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T01:44:32Z"
abstract: "A host transformer with a transplanted memory head scored 13.68% on a synthetic register-recall task. Supplying that same head with the representations produced by its original donor embeddings and first three blocks raised balanced accuracy to 90.32%, close to the intact donor\u2019s 92.08%. Only one 64-dimensional head output per token crossed from the donor branch into the host. With the same added computation and an untrained upstream branch, the recipient scored 10.43%. On 2,048 fresh program pairs, swapping one value inside the donor branch made both recipient answers switch to their partner\u2019s value in 2,015 of 2,017 initially correct pairs. A matched later-write exchange produced zero double switches. The recipient can use a transferred computation when the inputs to that computation are preserved."
score: 7.6
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A host transformer with a transplanted memory head scored 13.68% on a synthetic register-recall task. Supplying that same head with the representations produced by its original donor embeddings and first three blocks raised balanced accuracy to 90.32%, close to the intact donor’s 92.08%. Only one 64-dimensional head output per token crossed from the donor branch into the host. With the same added computation and an untrained upstream branch, the recipient scored 10.43%. On 2,048 fresh program pairs, swapping one value inside the donor branch made both recipient answers switch to their partner’s value in 2,015 of 2,017 initially correct pairs. A matched later-write exchange produced zero double switches. The recipient can use a transferred computation when the inputs to that computation are preserved.

![Balanced recall with the trained upstream computation, three controls and the standalone donor](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-transfer.png)

## What was transplanted?

The original donor and weak host were eight-block transformers with 14.3M parameters, initialized from the same starting weights. One donor head had learned to read a supplied set of register-dependent addresses displaced one event from actual writes. Copying the head’s query, key, value and output weights directly into host block 4 previously gave only a small improvement. That head then received hidden states produced by the host’s first three blocks. Here we asked whether its native upstream inputs would restore the skill. Work on model stitching motivates testing representational compatibility, and interchange interventions give a way to test what information passes through a chosen component. [Head-only study](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Bansal and colleagues, NeurIPS 2021](https://papers.nips.[REDACTED_SECRET]-Abstract.html) · [Geiger and colleagues, NeurIPS 2021](https://proceedings.neurips.[REDACTED_SECRET]-Abstract.html)

A second branch reads the same tokens through the frozen donor’s embeddings and first three blocks. Its block-4 input normalization and first head generate 64 attention outputs per token. The hybrid inserts that vector before the host’s attention output projection, using the transplanted donor columns. All other heads in host block 4 process host states. Host blocks 5–8 produce the answers. We trained only block 5, or 1,770,240 weights, for 1,024 updates. Both experimental arms saw identical programs. The matched-cost control substituted the corresponding embeddings and three upstream blocks from initialization while keeping the trained donor head and its normalization. We verified that reconnecting the extracted branch to the intact donor reproduces the donor’s own logits exactly on the smoke batch. [Preregistered comparisons](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Training code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## Preserving the donor’s upstream computation

| Recipient or comparison | Original value | Current value | Balanced recall |
|---|---:|---:|---:|
| Trained donor branch into adapted host | 99.41% | 81.22% | 90.32% |
| Initial donor branch into separately adapted host | 14.70% | 6.17% | 10.43% |
| Same adapted hybrid switched back to host input | 14.24% | 6.31% | 10.28% |
| Earlier head-only transplant | 22.34% | 5.02% | 13.68% |
| Intact donor | 99.41% | 84.75% | 92.08% |

The 1,024 held-out programs were the same panel used to diagnose the earlier graft. Each score equally weights original and current registers whose values changed. The trained upstream branch exceeded the head-only graft by 76.63 percentage points (paired 95% program-bootstrap interval 75.74–77.44), the matched untrained branch by 79.88 points (79.04–80.67), and the same model with host inputs restored by 80.04 points (79.24–80.81). All three comparisons cleared the prespecified ten-point threshold. These are within-fit program uncertainties on a reused panel. [Per-program counts and training receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET])

## Can changing the donor’s memory change the recipient’s answer?

The accuracy result opened a preregistered test on 2,048 fresh program pairs. Members differed only in the initial value assigned to the register queried at the end, after a later write to it. We exchanged the value vector at the displaced initialization endpoint between partners, only for the final query in the external donor head. All its query vectors, keys, attention weights and other values stayed intact, as did the recipient computation outside this intervention. The active control exchanged the corresponding vector at the displaced later write. Self-exchange reproduced intact logits on both control locations for the first batch. The hybrid initially answered both members correctly in 2,017 pairs. The initialization exchange switched both answers specifically to the other program’s value in 2,015 pairs. The control produced zero such switches. The unconditional source-minus-control difference was 98.39 percentage points (paired 95% interval 97.85–98.93). [Intervention](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Fresh paired predictions](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-interchange) · [Independent audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Limits and reproduction

The experiment concerns a synthetic memory task with a supplied addressing rule, an equal-width donor and recipient, and a shared initialization. The intact eight-block donor still had the highest balanced accuracy, while the hybrid ran the host plus three additional upstream blocks. This establishes causal communication across a specified interface. Other host skills, speed benefits and compatibility across unrelated pretrained models remain unmeasured. The gain attributable specifically to updating block 5 requires comparing against a zero-update recipient using the same donor branch. That fresh comparison is registered. [Receiver-learning protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The NumPy audit links the archival control counts, recalculates paired bootstrap intervals, regenerates the fresh counterfactual gold labels and verifies every reported switch count. Run `python register_routing/prefix_study/verify.py` from the repository root. Model fitting and interventions used MLX on the owner’s Mac Studio. The owner proposed testing frozen expert transplants and training the next host block around them. OpenAI Codex designed these comparisons, ran the experiments, audited the results and assisted with writing. [Verification code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Version-pinned manifest](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)