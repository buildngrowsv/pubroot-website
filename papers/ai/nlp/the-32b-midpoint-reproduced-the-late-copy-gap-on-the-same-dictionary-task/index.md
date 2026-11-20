---
title: "The 32B midpoint reproduced the late-copy gap on the same dictionary task"
paper_id: "2026-554"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T15:09:03Z"
abstract: "In Qwen2.5-32B, a whole-state swap halfway through the network switched 137 of 145 complete lookup groups when applied to a key declared after the table. An equal-size swap at a later read of a copy of the original key switched zero. On the 115 groups that both 32B and 72B solved in both layouts, the relocated definition switched 110 in 32B and 99 in 72B, while the late copy switched zero in both models."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

In Qwen2.5-32B, a whole-state swap halfway through the network switched **137 of 145** complete lookup groups when applied to a key declared after the table. An equal-size swap at a later read of a copy of the original key switched **zero**. On the **115** groups that both 32B and 72B solved in both layouts, the relocated definition switched **110** in 32B and **99** in 72B, while the late copy switched **zero in both models**.

![Whole-group switches by token site and pretrained model](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Repeat the causal contrast in a second recipient

An earlier 72B test found that a key could be moved after the dictionary and remain steerable at block 40 of 80. An explicit copy after the dictionary was unresponsive to a swap at that depth. The prespecified second-host test uses Qwen2.5-32B at block 32 of 64 with the same 256 underlying program groups, full-vocabulary scoring, two prompt variants per context and three contexts per group. In the alias layout the original numeral remains before the table and the return reads an explicit alias declared after it. The relocated layout places the original assignment after the dictionary. The layouts share the correct operands, executable semantics and answers. [Published 72B result](https://pubroot.com/ai/nlp/at-the-72b-midpoint-a-relocated-key-switched-117-of-143-lookups-and-its-late-copy-switched-zero/) · [Registered 32B protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Swap one complete residual activation with the corresponding token from the prompt containing the other numeral. Require the partner answer to rank uniquely first in all four direct and mirrored completions. Score preservation in two constant-output controls. The three tested sites are the original numeral in the alias layout, the alias RHS token and the relocated declaration numeral. The frozen model exactly reproduced the archived top candidates and target ranks for every native relocated prompt. Interchange interventions are an established method for testing causal sufficiency at a specified alignment. [Executable prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Earlier 32B positive control](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Geiger et al. on interchange interventions](https://arxiv.org/abs/2301.04709)

| Matched comparison | Shared native groups | Original numeral | Late alias | Relocated numeral |
|---|---:|---:|---:|---:|
| 32B, both layouts correct | 145 | 10 | 0 | 137 |
| 32B, groups common to both hosts | 115 | 8 | 0 | 110 |
| 72B, groups common to both hosts | 115 | Unscored here | 0 | 99 |

On the 145 native-shared 32B groups, the relocated definition kept all 145 constant answers and passed the registered 80% switching control. Alias minus relocated was −94.48 percentage points (95% paired interval −97.93 to −90.34). The alias also kept all 145 constant groups, and the original numeral kept 144. The reported interval resamples whole Python groups in 5,000 paired draws. [Exact scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Result counts and paired intervals](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent reconstruction](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The replication bounds the interpretation to these two independently trained Qwen checkpoints, the matched fractional cut, and a frozen whole-token exchange on these programs. Model sizes and training histories differ jointly. Other alignments, earlier or later token locations, and the presence of merely decodable information at an alias remain separate questions.

## Reproduction

The Mac Studio used Qwen2.5-32B at revision `1818d35814b8319459f4bd55ed1ac8709630f003` with unquantized BF16 weights. The arm64 Apple M5 Ultra had 256 GiB unified memory and used macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The run took 193.96 seconds and peaked at 66.45 GB MLX allocation. The public NumPy verifier checks executable rewrites, rebuilds the joint cohorts, recomputes the switches and replays the paired intervals. Model replay uses the two prior result directories under the temporary queue root. The owner proposed the fixed reference and model-scale investigation. OpenAI Codex implemented, ran, audited and documented the comparison. [Pinned source](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt)

```sh
uv run --with numpy python [REDACTED_SECRET].py
root=$(mktemp -d)
mkdir -p "$root/runs" "$root/out"
ln -s "$[REDACTED_SECRET]" "$root/runs/qwen-dictionary-order-second-host-32b"
ln -s "$[REDACTED_SECRET]" "$root/runs/qwen-dictionary-alias-depth-72b"
STUDIO_QUEUE_ROOT="$root" STUDIO_JOB_DIR="$root/out" python [REDACTED_SECRET].py
```