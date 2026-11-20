---
title: "Moving a dictionary key raised seven-coordinate donor switching from 71 to 134 groups"
paper_id: "2026-519"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T12:50:38Z"
abstract: "The same 7B donor and fitted seven-coordinate interface redirected a frozen 72B host's dictionary lookup in 134 of 139 shared-native groups when the key was assigned after the dictionary, compared with 71 of 139 when it was assigned first. The late whole-state control redirected 138 groups, and the late equal-norm orthogonal control redirected zero. The late donor preserved all 139 groups where both keys had the same effect. This experiment uses the same panel that established the whole-state result."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The same 7B donor and fitted seven-coordinate interface redirected a frozen 72B host's dictionary lookup in **134 of 139** shared-native groups when the key was assigned after the dictionary, compared with **71 of 139** when it was assigned first. The late whole-state control redirected 138 groups, and the late equal-norm orthogonal control redirected zero. The late donor preserved all 139 groups where both keys had the same effect. This experiment uses the same panel that established the whole-state result.

![Causal dictionary switches for the early donor and the three late edits](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-donor.png)

## Separate donor placement from calibration

In each generated function, the key identifies one of two dictionary entries. The function adds a signed offset to the selected value. A group uses both keys in three contexts. The first two have mirrored dictionary values and require opposite answer changes for the same substituted key. The constant table requires answer preservation. In the late-key version, two assignment lines trade places. Every program has the same expected reply in the two forms. The 139-group cohort solves all six prompts natively in both forms, drawn from the same 256 groups. The unedited model solved 183 groups in the early order and 155 in the late order. [Original dictionary benchmark](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Whole-state order benchmark](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Registered donor test](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Both BF16 checkpoints are frozen. The donor is Qwen2.5-Coder-7B and the recipient is Qwen2.5-72B. The same donor program and fitted affine map produce the seven target coordinates `c` in both orders. At the key token, after 17 host blocks, apply `h' = h + (c − ((h − μ)R + ν))Wᵀ`, using the archived read and write matrices and centers. The equal-norm orthogonal control has the same size in float32 before casting. The late full-state exchange uses the exact alternate prompt's 8,192-value state. The new native and full-state ranks and top-token IDs reproduce the previous late-key run exactly. No calibration uses the dictionary panel. All answer scores require unique top rank over the full vocabulary. [Pinned runner](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Donor map](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Host alignment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

| Edit | Switch both mirrored contexts | Preserve the constant-table answer |
|---|---:|---:|
| Seven-coordinate donor at early key | 71/139 | 138/139 |
| Seven-coordinate donor at late key | 134/139 | 139/139 |
| Equal-norm orthogonal edit at late key | 0/139 | 138/139 |
| Full-state swap at late key | 138/139 | 138/139 |

The paired late-minus-early donor gain was **45.32 points**, with a 95% interval from 36.69 to 54.68. The donor switched 66 groups only in late position and three only in early position. The late gain over orthogonal was 96.40 points (92.81 to 99.28). The late deficit against whole state was 2.88 points (paired deficit 0.72 to 5.76). The prespecified switching, specificity and paired superiority thresholds passed. Declaration order changes both the information reaching the key and the distance to its use. The result measures the two changes jointly. The registered independent replication uses new programs to test whether the effect carries beyond this panel. [Raw ranks and per-token edit norms](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-donor.npz) · [Independent paired metrics](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Fresh-panel replication protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python [REDACTED_SECRET].py` from the repository root to re-execute the program assertions, check artifact hashes, and reproduce the rank outcomes and paired intervals. The run took 406 seconds and reached 146.69 GB peak MLX allocation on an Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory. Software was macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed work on conditional routing and expert transfer. OpenAI Codex implemented, ran, audited and documented the comparison. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)