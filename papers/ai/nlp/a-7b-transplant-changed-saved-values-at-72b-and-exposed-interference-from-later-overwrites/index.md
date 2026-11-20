---
title: "A 7B transplant changed saved values at 72B and exposed interference from later overwrites"
paper_id: "2026-508"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T11:06:24Z"
abstract: "A seven-dimensional transplant into frozen Qwen2.5-72B switched all four correct answers in 193 of 206 paired groups involving a saved Python value and a later overwrite. A full-state exchange at the relevant assignment switched 192, and an equal-norm orthogonal edit switched zero. Editing the irrelevant assignment preserved 195 of 206 groups (94.66%), one group short of the registered 95% floor. All 14 incorrect replies under the irrelevant-site edit gave the edited overwrite plus the offset. That error pattern was identified after the run."
score: 8.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A seven-dimensional transplant into frozen Qwen2.5-72B switched all four correct answers in **193 of 206** paired groups involving a saved Python value and a later overwrite. A full-state exchange at the relevant assignment switched **192**, and an equal-norm orthogonal edit switched **zero**. Editing the irrelevant assignment preserved **195 of 206** groups (94.66%), one group short of the registered 95% floor. All 14 incorrect replies under the irrelevant-site edit gave the edited overwrite plus the offset. That error pattern was identified after the run.

![Whole-vocabulary outcomes in the saved-value and current-value contexts](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Save a value, overwrite the source, then choose what to return

Each Python function assigns an integer to a variable, copies it to a saved variable, executes three to five unrelated assignments, and overwrites the original variable. In one context the return statement reads the saved value and adds a fixed signed offset. In the other context it reads the current value and adds the same offset. A group combines two variants of the assigned digits with the two read contexts. The expected answers are distinct from all four assignment digits. The donor programs are independently generated single-variable functions. Python execution verifies both host and donor answers. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Exact programs and edit sites](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Reuse the fitted interface

The frozen donor is Qwen2.5-Coder-7B, and the frozen recipient is Qwen2.5-72B, both BF16. The donor state after six blocks supplies seven translated coordinates through the existing affine map. The recipient edit occurs after 17 blocks at one assignment token. For recipient state `h` and translated donor coordinates `c`, the edit is `h' = h + (c − ((h − μ)R + ν)) Wᵀ`. The archived 72B matrices `R` and `W` read and write that coordinate system, with centers `μ` and `ν`. The narrow and orthogonal edits share the same pre-cast Euclidean norm at each compared site. A full-state control exchanges all 8,192 coordinates at the read assignment only. The experiment trains neither model and fits no new directions. [Pinned source](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Frozen map](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Frozen alignment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

## Score both counterfactuals and both read contexts

The native model solved all four prompts in 51 of 64 qualification groups and 206 of 256 disjoint test groups. The table conditions on those 206 test groups. Each predicted answer must rank uniquely first over the full vocabulary. Both prompts in a context must yield the exact switched or preserved answer shown below.

| Intervention | Target behavior | Reads the saved value | Reads the current value | Both contexts |
|---|---|---:|---:|---:|
| Donor at relevant assignment | Switch | 193/206 | 206/206 | 193/206 |
| Donor at irrelevant assignment | Preserve | 195/206 | 206/206 | 195/206 |
| Orthogonal at relevant assignment | Switch | 0/206 | 0/206 | 0/206 |
| Full state at relevant assignment | Switch | 192/206 | 206/206 | 192/206 |

The donor exceeded the orthogonal control by 93.69 points, with a 95% paired interval of 90.29 to 96.60 points from 5,000 group bootstrap draws. All criteria except the irrelevant-site preservation floor passed. Under the earlier two-variable task with independent assignments, the same intervention preserved 246 of 250 paired groups. The panel and prompts differ, so that contrast is descriptive. [Earlier independent-assignment result](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Scored ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Computed endpoints](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The 11 preserved-value group failures were confined to edits of the later assignment while the program read the saved value. Within those groups, the top token in all 14 individual misses was the answer obtained from the edited overwrite rather than the saved assignment. This is consistent with a later-value intrusion in this prompt format. The experiment does not identify whether a context-matched whole-state exchange at the overwrite would cause the same errors, since the whole-state control was applied only at the relevant assignment. It assesses arithmetic on saved bindings at known token locations, with no claims about general code generation or training new fixed-reference architectures. [Causal abstraction precedents](https://proceedings.neurips.[REDACTED_SECRET]-Abstract.html)

Run `uv run --with numpy python nested_surgery/numeric_snapshot_72b_study/verify.py` from the repository root to execute and inspect the archived prompts, verify artifact hashes, check the perturbation size control and recompute the rank scores. The run took 732 seconds and reached 147.24 GB peak MLX allocation on an Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory. It used macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed exploring fixed references at larger scales. OpenAI Codex designed and ran this comparison, verified the evidence and assisted with the writing. [Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)