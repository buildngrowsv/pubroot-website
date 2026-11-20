---
title: "Changing the opening-bracket signal in a 7B coder\u2019s final module breaks 40 of 54 complete repairs"
paper_id: "2026-408"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T03:48:19Z"
abstract: "A frozen 7B coding model solved 54 of 256 Python repair groups. At its final prediction position we replaced only the last feed-forward module\u2019s output. Borrowing that output from a different program with the same opener preserved all 54 groups and gained one. Borrowing from a nearly identical program with a different opener broke 40 and gained none. The paired difference was 16.02 percentage points (95% interval 11.72\u201320.70). All 36 originally correct individual answers that switched to the substituted member\u2019s target moved from a closing brace to a closing parenthesis. The experiment localizes a behaviorally important contribution in the specialist whose module previously failed to transfer to a larger host."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A frozen 7B coding model solved 54 of 256 Python repair groups. At its final prediction position we replaced only the last feed-forward module’s output. Borrowing that output from a different program with the same opener preserved all 54 groups and gained one. Borrowing from a nearly identical program with a different opener broke 40 and gained none. The paired difference was 16.02 percentage points (95% interval 11.72–20.70). All 36 originally correct individual answers that switched to the substituted member’s target moved from a closing brace to a closing parenthesis. The experiment localizes a behaviorally important contribution in the specialist whose module previously failed to transfer to a larger host.

![Whole repair groups solved by the same 7B model under four final-module interventions](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-exchange.png)

## What moved between prompts?

Each generated Python function has three versions. One earlier opening character changes between a parenthesis, square bracket and brace. The suffix and the four possible completions are identical. Fixing all three versions requires reading that earlier choice. The intact Qwen2.5-Coder-7B base model solved 54 of the 256 fresh groups. Its final feed-forward module had transferred zero groups when inserted into block 27 of Qwen2.5-14B and followed by eight updates to block 28. This prompted a location test inside the functioning specialist. We registered its criterion before examining the adapted coding graft’s outcomes. [Transplant paper and opportunity set](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Location protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

In the last of the coder’s 28 blocks we kept the destination prompt’s state after attention. We changed only the feed-forward output added at the final prediction position. One intervention borrowed that output from a different member of the same group, rotating the three opening characters in one fixed direction. Its control borrowed the output from another program with the same opener, choosing the closest available input length. We also scored the native output and an all-zero replacement. The final normalization and vocabulary readout stayed fixed. Every native candidate choice matched the separately loaded standalone donor. In a final block, later positions have no opportunity to attend to these replacements. [Pinned checkpoint and scoring](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Intervention implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Executable prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The primary contrast is the same-opener minus changed-opener difference in complete-triplet accuracy. We resampled all three versions together for a paired 95% interval. The declared gate required five percentage points, a positive lower interval bound and ten initially correct groups retained under the same-opener control and lost under the changed-opener intervention. The score archive includes four raw candidate logits per prompt, the exact source assigned to every destination and enough information to reproduce all ties and removals. [Raw evidence and receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## What the substitutions changed

| Final feed-forward output at the destination | Correct prompts / 768 | Complete groups / 256 | Originally solved groups lost | New groups solved |
|---|---:|---:|---:|---:|
| Original | 559 | 54 | 0 | 0 |
| Set to zero | 454 | 21 | 33 | 0 |
| From a different program with the same opener | 561 | 55 | 0 | 1 |
| From a matched group member with a changed opener | 497 | 14 | 40 | 0 |

The control matched input length exactly on 758 of 768 substitutions, with 759 distinct source prompts. Forty initially solved groups survived the same-opener substitution and failed under the changed opener, passing the registered localization threshold. The same-opener control also introduced one previously unsolved group, accounting for the 41-group difference between the two interventions. Replacing the output with zero preserved 21 groups. Their answers remained available through the rest of the final state. [Group IDs and independent estimates](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

We checked whether incorrect repairs tracked the actual replacement. Of 559 originally correct answers, 62 became incorrect under the changed opener. Of those, 36 picked the borrowed program’s required token. All 36 arose when a brace prompt received the output from a parenthesis prompt. The chosen rotation never tested the opposite direction for that pair. As a secondary continuous check, the changed-opener condition increased the mean log odds of the borrowed target versus the original target by 2.10 relative to the same-opener control (group-paired 95% interval 2.04–2.16). Nineteen changed-opener prompts had ties for highest score, compared with three under the same-opener control. The continuous result uses the saved scores before the fixed-order tie break. [Predictions and substitution indices](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

## Scope and next discriminating test

The intact 7B model uses this module to solve some groups in its own network. The 14B recipient solved zero groups following the earlier transplant of this same module. That contrast leaves several possibilities, including the input map, the output map and the trained receiver. The present diagnostic cannot distinguish them. It tests one base checkpoint, a reused panel from a single executable generator and a cyclic substitution in one direction. The same-opener control preserves the label across a different program, while the changed-opener control uses the original program structure. The paired intervals describe this panel with the recorded assignments; some control sources are reused. A fresh test in both directions can distinguish opener-specific effects from a general increase in parenthesis predictions. Prior work on activation patching describes the sensitivity of causal estimates to the intervention and scoring rule. [Zhang and Nanda](https://arxiv.org/abs/2309.16042)

Run the verification script with Python and NumPy to reproduce the source choices, original standalone predictions, individual transitions and uncertainty estimates. The owner proposed locating and transplanting a working coding expert. OpenAI Codex implemented and ran the diagnostic on the owner’s Apple M5 Ultra, checked its archived scores and assisted with writing.