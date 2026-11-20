---
title: "Moving a dictionary key restored whole-state control in 138 of 139 shared 72B groups"
paper_id: "2026-517"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T12:40:47Z"
abstract: "Moving a numeric key assignment after the dictionary changed whole-state switching from 74 to 138 groups out of 139 with correct native answers in both orders. The relocated key preserved the exact answer in 138 constant-table groups, compared with 137 at the original site. The relocation also reduced native performance across the full panel from 183 to 155 fully correct groups out of 256. The experiment separates the edit's reliability among shared solves from native accuracy."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Moving a numeric key assignment after the dictionary changed whole-state switching from **74 to 138 groups out of 139** with correct native answers in both orders. The relocated key preserved the exact answer in 138 constant-table groups, compared with 137 at the original site. The relocation also reduced native performance across the full panel from 183 to 155 fully correct groups out of 256. The experiment separates the edit's reliability among shared solves from native accuracy.

![Native solves on the full panel and whole-state effects on the shared native cohort](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-order.png)

## Move only the key assignment

Every generated function assigns a one-digit key, defines a two-entry dictionary and returns the selected value plus a signed offset. Each group pairs two key values in three contexts. One uses the original dictionary, one swaps its associated values, and one assigns the same value to both keys. Swapping the key should change the answer in both directions in the first two contexts. The correct answer stays fixed in the constant-table case. The archived 256 groups are the same in both orders. The two assignment lines simply exchange places. Executing every Python program verifies that the order change preserves its expected answer. [Registered key-order test](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Relocated programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Original programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The only tested intervention exchanges the full 8,192-value state at the key token between the two versions of a prompt after 17 blocks in frozen BF16 Qwen2.5-72B. The source and recipient differ at that numeral only. Score each next-token answer over the full vocabulary and count ties as failures. The earlier order uses the pinned full-state and native scores from the first benchmark. The new run computes those same two conditions at the late site. [Pinned implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Original ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz) · [Late-site ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-key.npz)

| Measure | Key before dictionary | Key after dictionary |
|---|---:|---:|
| Native accuracy on all six prompts | 183/256 | 155/256 |
| Native accuracy in only that order | 44/256 | 16/256 |
| Both mirrored contexts switch after exchange | 74/139 | 138/139 |
| Constant table preserves both answers after exchange | 137/139 | 138/139 |
| Both switch and preservation criteria | 73/139 | 137/139 |

The paired switching gain was +46.04 percentage points (95% interval +38.13 to +53.96). Of the 139 shared-native groups, 64 switched only at the late site and zero only at the early site. The comparison cleared the registered 100-group floor, 80% late switching, 95% preservation, and 15-point lift with a positive paired lower bound. The gain measures intervention reliability within the shared cohort. The earlier key is farther from its use and precedes both table entries, while the later key follows both entries and directly precedes its use. This experiment changes those properties together. A separate registered test asks whether the fixed seven-dimensional donor also carries to the new site. [Independent paired audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Donor follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Run `uv run --with numpy python [REDACTED_SECRET].py` to verify program equivalence and recalculate both cohort sizes, the intervention scores and the group bootstrap from exact archives. The Studio run took 249 seconds with 146.70 GB peak MLX allocation on Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory. It used macOS 27.2 (26B118), Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. The owner proposed testing expert transfer and conditional routing. OpenAI Codex implemented, ran, audited and wrote up the comparison. [Receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)