---
title: "Swapping both tokens at the dictionary\u2019s alias read changed zero full lookup groups"
paper_id: "2026-572"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T16:00:24Z"
abstract: "At the midpoint of Qwen2.5-72B, swapping the alias token inside the lookup, the closing bracket, or both together changed zero of 143 complete groups under every intervention. The matched relocated-definition control changed 117 of 143. The joint swap changed only one of 572 individual answers in the varying-output contexts. The result extends the earlier null at the copy assignment to the exact downstream lookup tokens tested here."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The owner proposed the research direction. OpenAI Codex registered, implemented, ran and verified the comparisons and assisted with writing."
---

At the midpoint of Qwen2.5-72B, swapping the alias token inside the lookup, the closing bracket, or both together changed **zero of 143** complete groups under every intervention. The matched relocated-definition control changed **117 of 143**. The joint swap changed only **one of 572** individual answers in the varying-output contexts. The result extends the earlier null at the copy assignment to the exact downstream lookup tokens tested here.

![Individual and whole-group switches from the alias, lookup and relocated-definition swaps](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-use.png)

## The computation site

The earlier experiment compared an explicit copy after the dictionary with a numeral declared after it. Swapping the copy's RHS activation changed none of the shared-native groups at block 40. Holding that model, cut and layout fixed, this test targets the step where the program reads the alias again in `table[selected]`. The Qwen tokenizer encodes the alias read and its closing bracket at adjacent positions on every archived prompt. Exchange one or both whole 8,192-value residual vectors with the corresponding vectors from the partner prompt. Those prompts differ at just the initial numeral. The runner verified the exact positions in both variants and reproduced the native top candidates and rank positions on its first batch. [Prior midpoint comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Preregistered follow-up](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Geiger et al., interchange interventions](https://arxiv.org/abs/2301.04709)

The archived panel contains 256 program groups with both original and mirrored dictionary payloads plus a constant-output control. Analyze the same 143 groups solved natively in both layouts. A full group switch requires all four expected counterfactual next tokens to have unique rank one over the complete vocabulary. Each group also has two constant-output prompts. Candidate rank positions, margins and exact winner IDs are archived for every intervention. [Exact Python programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Raw ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-use.npz)

| Block-40 exchange | Individual switches / 572 | Complete switches / 143 | Constants preserved / 143 |
|---|---:|---:|---:|
| Relocated declaration | 546 | 117 | 141 |
| Copy assignment RHS | 4 | 0 | 143 |
| Alias inside lookup | 1 | 0 | 143 |
| Closing bracket | 0 | 0 | 143 |
| Both lookup tokens | 1 | 0 | 143 |

The exact output threshold and the preregistered rescue criteria did not pass for any new swap. The positive control is from the matched alternative arrangement of the same programs. This result establishes that exchanging these token states at the selected cut is insufficient to reliably steer the prediction. It leaves the states' decodable contents, other cut points and wider multi-token exchanges open. [Independent reconstruction](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Registered outcome and paired intervals](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Reproduction

The frozen checkpoint is unquantized BF16 Qwen2.5-72B at revision `efba10c8e54e91e0d9570ab5f7b51a958474d4cb`. The arm64 Apple M5 Ultra Studio has 256 GiB unified memory and used macOS build 26B118, Python 3.12.16, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and tokenizers 0.23.3. Use `uv run --with numpy python [REDACTED_SECRET].py` from the repository root to reconstruct cohorts, exact ranks and contrasts. Reproduce inference using the pinned launcher with a new `STUDIO_JOB_DIR`. The runner reads the prior public dataset and scores from the repository. The owner proposed fixed references. OpenAI Codex registered, implemented, ran and audited the comparison. [Pinned runner](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt)