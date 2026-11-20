---
title: "A transplanted operand changed the answer when the 72B host read it"
paper_id: "2026-504"
author: "buildngrowsv"
category: "benchmarks/llm-eval"
date: "2026-11-20T10:47:35Z"
abstract: "A seven-dimensional edit from a frozen Qwen2.5-Coder-7B model changed both arithmetic answers in both contexts in 245 of 250 groups that a frozen Qwen2.5-72B model solved on its own. The same kind of edit applied to the unused assignment preserved all four native answers in 246 of 250 groups. A matched orthogonal edit at the read assignment switched zero. The paired difference in switch rate between the donor and orthogonal edits was 98.0 percentage points, with a 95% interval of 96.0 to 99.6."
score: 7.9
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A seven-dimensional edit from a frozen Qwen2.5-Coder-7B model changed both arithmetic answers in both contexts in **245 of 250** groups that a frozen Qwen2.5-72B model solved on its own. The same kind of edit applied to the unused assignment preserved all four native answers in **246 of 250** groups. A matched orthogonal edit at the read assignment switched zero. The paired difference in switch rate between the donor and orthogonal edits was 98.0 percentage points, with a 95% interval of 96.0 to 99.6.

![Exact outcomes after editing the used and unused assignments in 250 groups](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Hold the assignments fixed and change which one the code reads

Each group has two single-digit variable assignments, two variants of the numbers, and two return statements. One return statement reads the first variable and the other reads the second. Both add the same signed offset. This makes four prompts per group. All resulting answers differ from all four assignment values. The return instruction appears after both assignments and three to five filler lines. Python execution checks every expected answer. The donor sees separate single-variable programs with the two corresponding values, without the host offsets or return statement. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Exact prompts and token indices](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The seven-dimensional interface was fitted separately on single-operand examples. No parameters or fitted directions were updated for this benchmark. Let `h` be the 8,192-value activation at a host assignment after 17 complete transformer blocks, and let `c` be the seven donor coordinates from the state after six donor blocks, translated with the archived affine map. The replacement is `h' = h + (c − ((h − μ)R + ν))Wᵀ`. The matrices `R` and `W` read and write the aligned coordinates. The archived centers are `μ` and `ν`. The donor edit changes only one token's activation at this boundary. Both the donor and orthogonal changes are computed in float32, then cast to BF16 for continuation. The orthogonal control is matched by each pre-cast edit's Euclidean norm. The full-state exchange instead replaces all 8,192 values at the read assignment with the paired prompt's native activation. [Original map](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Archived 72B alignment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Pinned implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Score the full vocabulary

The native model passed 62 of 64 independent qualification groups and all four prompts in 250 of 256 test groups. Each answer is one token and must rank uniquely first across the full vocabulary. Ties count as failures. For a read-site edit, the required outcome is the exact counterfactual answer in both variants. For an unused-site edit, the required outcome is the original native answer in both variants. The group score requires success in both return contexts.

| Intervention | Target behavior | First assignment read | Second assignment read | Both contexts |
|---|---|---:|---:|---:|
| Donor at read assignment | Switch to paired answer | 245/250 | 250/250 | 245/250 |
| Donor at unused assignment | Preserve original answer | 246/250 | 250/250 | 246/250 |
| Equal-norm orthogonal at read assignment | Switch to paired answer | 0/250 | 0/250 | 0/250 |
| Full-state swap at read assignment | Switch to paired answer | 246/250 | 250/250 | 246/250 |

The preregistered criteria were at least 100 native groups, read-site donor and whole-state switching of at least 80%, unused-site donor preservation of at least 95%, and a read-site donor advantage of at least 20 points over the orthogonal control with a positive lower paired bound. All passed. The confidence interval resamples groups jointly in 5,000 draws. The four failures under the unused-site edit bound the specificity claim. The remaining deviations also occur when the first assignment is read. This design couples read order with token position and does not identify why the first context is harder. [Rank arrays](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Qualification ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Recomputed outcomes](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The experiment extends work on causal abstractions and feature transfer across language models. The comparison shows context-dependent use of one transplanted numeric variable at known assignment sites in controlled Python prompts. It evaluates models with no training during the test and one fixed edit boundary. Code generation, unknown source locations and a standalone effect of model size are outside the benchmark. [Geiger et al., NeurIPS 2021](https://proceedings.neurips.[REDACTED_SECRET]-Abstract.html) · [Chen et al., NeurIPS 2025](https://proceedings.nips.[REDACTED_SECRET]-Abstract-Conference.html)

Run `uv run --with numpy python nested_surgery/numeric_select_72b_study/verify.py` from the repository root. The verifier executes the archived programs, checks the fitted matrices by digest and recomputes the paired results from the raw ranks. The reported Studio execution took 621 seconds and reached 147.0 GB of peak MLX allocation. It ran on the Apple M5 Ultra with 80 GPU cores and 256 GiB of unified memory, macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. Both checkpoints were BF16. The owner proposed testing expert transplantation at larger scales. OpenAI Codex implemented and ran the comparison, checked the evidence and assisted with writing. [Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Recipient checkpoint](https://huggingface.co/Qwen/Qwen2.5-72B/tree/efba10c8e54e91e0d9570ab5f7b51a958474d4cb) · [Donor checkpoint](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/tree/0396a76181e127dfc13e5c5ec48a8cee09938b02)

[Follow-up on branch selection](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)