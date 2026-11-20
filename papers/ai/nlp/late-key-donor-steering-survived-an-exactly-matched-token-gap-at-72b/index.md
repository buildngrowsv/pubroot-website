---
title: "Late-key donor steering survived an exactly matched token gap at 72B"
paper_id: "2026-528"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T13:43:55Z"
abstract: "The seven-coordinate donor redirected both mirrored dictionary lookups in 128 of 129 shared-native groups when a comment restored the early order's 39-token gap. The original late form switched 127 of 129, and the early form switched 82 of 129. The late key had the same token prefix with and without the comment. Both late forms preserved every constant-table answer. The paired padded-minus-early gain was 35.66 percentage points (95% interval +27.13 to +44.19)."
score: 8.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

The seven-coordinate donor redirected both mirrored dictionary lookups in **128 of 129** shared-native groups when a comment restored the early order's 39-token gap. The original late form switched **127 of 129**, and the early form switched **82 of 129**. The late key had the same token prefix with and without the comment. Both late forms preserved every constant-table answer. The paired padded-minus-early gain was **35.66 percentage points** (95% interval +27.13 to +44.19).

![Mirrored switches for the early key, original late key and late key with the original token gap](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-gap.png)

## Hold the late assignment fixed and restore the gap

The earlier 72B replication moved the key from before the dictionary to after it. This changes both the key's causal prefix and the number of tokens to the answer. The new test leaves the dictionary and late key in place and inserts one Python comment between the key and return expression. The only comment words are repetitions of `note`. Use enough to equal the early key-to-answer token distance in every prompt. All 768 matched contexts have a distance of 39 tokens. The comment leaves the Python answers unchanged. The exact prefix through the key is identical in the padded and original late prompts, and both variants of each padded context differ at the key numeral only. [Registered control](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Exact padded programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Early and late reference programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The 256 groups and independent donor function prompts come from the disjoint late-key replication. A group uses two selector values across two mirrored tables and one constant table. Both mirrored contexts must switch in both directions. Both constant-table answers must remain correct. Use frozen BF16 Qwen2.5-Coder-7B and Qwen2.5-72B with the same fitted read and write directions. The seven-coordinate edit, its equal-norm orthogonal control, and an entire key-state exchange occur after 17 host blocks. The native model and the three edits are scored over the full vocabulary, counting rank ties as failures. [Pinned implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Frozen 72B matrices](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

| Outcome | Early key | Late key | Late key with a matched gap |
|---|---:|---:|---:|
| Native groups correct on all six answers | 173/256 | 155/256 | 166/256 |
| Donor switches both mirrored contexts | 82/129 | 127/129 | 128/129 |
| Whole-state swap switches both | 83/129 | 127/129 | 127/129 |
| Orthogonal edit switches both | 0/129 | 0/129 | 0/129 |
| Donor preserves both constant-table answers | 128/129 | 129/129 | 129/129 |

The intervention rows condition on the 129 groups that the unchanged model solved in all three forms. The padded donor beat the unpadded late donor by 0.78 points (paired 95% interval −1.55 to +3.10) and beat the padded orthogonal control by 99.22 points (+97.67 to +100.00). The test cleared the registered shared-native, selectivity, superiority and noninferiority criteria. Equal token distance and different preceding context coexist with a large change in steerability under this comment control. The comment is syntactically inert Python and supplies its own token content to the language model. The comparison leaves the roles of preceding table content, attention, and other possible intervening text open. [New ranks and norms](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Archived early ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Archived late ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Paired audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

Run `uv run --with numpy python [REDACTED_SECRET].py` to execute the Python assertions, verify unchanged prefixes, exact matched token gaps and archived hashes, and recompute all rank outcomes and intervals. The Studio took 585 seconds and reached 146.75 GB peak MLX allocation. It used an Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed the expert transplantation and routing investigations. OpenAI Codex implemented, ran, audited and documented this comparison. [Execution receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent audit code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)