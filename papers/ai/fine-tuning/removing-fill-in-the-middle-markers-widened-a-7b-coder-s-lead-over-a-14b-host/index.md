---
title: "Removing fill-in-the-middle markers widened a 7B coder\u2019s lead over a 14B host"
paper_id: "2026-431"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:22:56Z"
abstract: "Qwen2.5-Coder-7B completed all three delimiter repairs in 171 of 256 Python groups from a plain prefix. Qwen2.5-14B completed 82 of 256, a difference of 34.77 percentage points. The general model's tendency to pick a colon disappeared in plain Python. The specialist's advantage grew after both models stopped choosing colons."
score: 7.2
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Qwen2.5-Coder-7B completed all three delimiter repairs in **171 of 256** Python groups from a plain prefix. Qwen2.5-14B completed **82 of 256**, a difference of 34.77 percentage points. The general model's tendency to pick a colon disappeared in plain Python. The specialist's advantage grew after both models stopped choosing colons.

![All three repairs correct across the three formats for each frozen model](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

We generated the same 256 executable triplets for all formats (indices 80000–80255). In each triplet only the opening character changes. A completion from the four allowed tokens, right parenthesis, right bracket, right brace or colon, is correct if it closes the opener and produces a valid program. We tested the original fill-in-the-middle prompt, the same markers with an empty suffix, and the raw incomplete Python prefix. The generator checks unique syntax and execution. The verifier repeats those checks independently on the saved programs. Scoring uses Qwen2.5-Coder-7B base at revision `0396a76181e127dfc13e5c5ec48a8cee09938b02` and Qwen2.5-14B base at revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. Both models are frozen. [Registered protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Generator](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Format scoring](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

| Prompt format | 7B complete groups | 14B complete groups | 7B colon choices | 14B colon choices |
|---|---:|---:|---:|---:|
| Markers and suffix | 55 / 256 | 0 / 256 | 194 / 768 | 763 / 768 |
| Markers, empty suffix | 49 / 256 | 12 / 256 | 205 / 768 | 424 / 768 |
| Raw Python prefix | 171 / 256 | 82 / 256 | 0 / 768 | 0 / 768 |

On the raw prefix, the paired 95% bootstrap interval for the 7B advantage was +28.52 to +41.02 points. The advantage increased by +13.28 points relative to full fill-in-the-middle (+4.69 to +21.48). The resampling unit is a full program triplet across all three formats. The primary comparison passed the registered 10-point gate. The experiment concerns constrained next-token choices in one Python generator and two checkpoints. The raw prefix removes both the suffix and markers. The intermediate arm measures the consequence of removing just the suffix while keeping the markers. [Raw scores, prompts and decisions](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Fill-in-the-middle training](https://arxiv.org/abs/2207.14255)

Run `uv run --with numpy python nested_surgery/opener_format_study/verify.py` from the repository root. Frozen inference ran for 72 seconds on the owner's Apple M5 Ultra using Python 3.12, MLX 0.32.4, MLX-LM 0.32.2, NumPy 2.5.5 and Tokenizers 0.23.3. The owner proposed qualifying a smaller coding expert before grafting. OpenAI Codex implemented and ran the format comparison, verified the data and assisted with writing. [Pinned Studio receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)