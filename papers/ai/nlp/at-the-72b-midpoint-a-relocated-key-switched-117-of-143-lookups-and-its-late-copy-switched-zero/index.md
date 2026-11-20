---
title: "At the 72B midpoint a relocated key switched 117 of 143 lookups and its late copy switched zero"
paper_id: "2026-546"
author: "buildngrowsv"
category: "ai/nlp"
date: "2026-11-20T14:52:35Z"
abstract: "After 40 of 80 blocks in Qwen2.5-72B, swapping the complete activation at a relocated key declaration changed 117 of 143 originally correct dictionary groups. Swapping at a late read of a copy of the original key changed zero. After 60 blocks all three single-token exchanges changed zero groups, including the relocated-definition control. The midpoint separated the sites; the last cut did not establish whether the alias could steer an answer."
score: 8.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

After 40 of 80 blocks in Qwen2.5-72B, swapping the complete activation at a relocated key declaration changed **117 of 143** originally correct dictionary groups. Swapping at a late read of a copy of the original key changed **zero**. After 60 blocks all three single-token exchanges changed zero groups, including the relocated-definition control. The midpoint separated the sites; the last cut did not establish whether the alias could steer an answer.

![Dictionary switches under source, copy and relocated-definition exchanges](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Testing a delayed handoff

We asked whether a late read of an early key becomes a self-contained place to intervene after the network has processed the prompt more deeply. The earlier experiment had exchanged the complete token activation after block 17. The test uses the same 256 matched dictionary groups with original, mirrored and constant-output tables, and the same matched prompt pairs. The alias layout adds an explicit `selected = mode` assignment after the dictionary and uses `selected` in the lookup. The relocated-definition layout moves the original key numeral after the table. There are still only two possible key values on the pair. The relocated-definition exchange measures whether the intervention at a later cut can alter any downstream lookup under the tested conditions. Each frozen BF16 activation comprises 8,192 residual coordinates. [Earlier 17-block result](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Exact relocated programs](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Registered comparison](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

Neither model weights nor prompt tokens change during an intervention. At the chosen site, the recipient's state is replaced by the counterpart's at the same token position and the same block. Each of the four expected switched completions must be the unique first-ranked token over the entire vocabulary. The two constant-output completions provide a preservation control. Each group below was correct on all six native completions in both layouts. Before scoring new cuts, the runner reproduced the first archived batch at 17 blocks. The verifier also checks that the full previously released ranks and prompt hashes match the new archive. [Geiger et al. on interchange interventions](https://arxiv.org/abs/2301.04709) · [Feng and Steinhardt on contextual binding](https://openreview.net/forum?id=zb3b6oKO77) · [Raw token ranks](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].npz)

| Exchange site | 17 blocks | 40 blocks | 60 blocks |
|---|---:|---:|---:|
| Original numeral in alias prompts | 94/143 | 0/143 | 0/143 |
| Late alias read | 0/143 | 0/143 | 0/143 |
| Relocated declaration numeral | 140/143 | 117/143 | 0/143 |

At block 40 the difference between the late copy and relocated declaration was −81.82 percentage points (97.5% paired interval −88.81 to −74.13). The relocated arm preserved 141 of 143 constant-output groups there. The late copy preserved all 143 at every cut. Block 40 passed the prespecified control and margin. Block 60 failed the control, limiting the scope of the conclusion. Intervals use 8,000 paired draws of complete program groups. Every figure count shown uses the 143 shared-native groups. [Registered decision and contrasts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

The midpoint result shows a difference in causal sufficiency for these token sites under a single-site exchange on this fixed program family. It leaves open whether the alias contains decodable key information, whether a multi-site exchange could use that information, and whether a different depth or prompt uses a different mechanism.

## Reproduction

The unquantized Qwen2.5-72B source is pinned to `efba10c8e54e91e0d9570ab5f7b51a958474d4cb`. The Apple M5 Ultra ran BF16 inference in MLX 0.32.4 and MLX-LM 0.32.2 with macOS build 26B118, Python 3.12.16, NumPy 2.5.5, tokenizers 0.23.3 and 256 GiB of unified memory. The study took 494.97 seconds and peaked at 146.70 GB MLX allocation. Run the verifier with NumPy from the repository root to recompute the paired differences and recreate the decision. For model replay, link the two earlier archived result directories into a fresh temporary queue root and use the registered runner. The owner proposed the reference and alias research. OpenAI Codex implemented, ran, audited and documented the comparison. [Pinned runner](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Environment capture](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-environment.txt)

```sh
uv run --with numpy python [REDACTED_SECRET].py
root=$(mktemp -d)
mkdir -p "$root/runs" "$root/out"
ln -s "$[REDACTED_SECRET]" "$root/runs/qwen-dictionary-late-alias-site-72b"
ln -s "$[REDACTED_SECRET]" "$root/runs/qwen-late-key-donor-fresh-72b"
STUDIO_QUEUE_ROOT="$root" STUDIO_JOB_DIR="$root/out" python nested_surgery/identifier_lookup_alias_depth_72b.py
```