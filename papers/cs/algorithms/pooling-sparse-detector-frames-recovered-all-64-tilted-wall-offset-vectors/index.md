---
title: "Pooling sparse detector frames recovered all 64 tilted-wall offset vectors"
paper_id: "2026-570"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-11-20T15:59:05Z"
abstract: "Across eight 192\u00b3 worlds, pooling earlier offset evidence raised exact offset recovery from 26 of 64 to 64 of 64 in the scored tilted rounds. The pooled controller retained 70.18% of whole words, versus 68.79% for the current-frame estimator and 70.26% with supplied geometry. It gained 1.39 percentage points over the current-frame estimator (95% paired interval +0.96 to +1.87). The deficit to exact geometry was 0.08 points and cleared the prespecified margin."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The owner proposed the research direction. OpenAI Codex registered, implemented, ran and verified the comparisons and assisted with writing."
---

Across eight **192³** worlds, pooling earlier offset evidence raised exact offset recovery from **26 of 64** to **64 of 64** in the scored tilted rounds. The pooled controller retained **70.18%** of whole words, versus **68.79%** for the current-frame estimator and **70.26%** with supplied geometry. It gained **1.39 percentage points** over the current-frame estimator (95% paired interval +0.96 to +1.87). The deficit to exact geometry was **0.08 points** and cleared the prespecified margin.

![Word retention and exact offset recovery on paired tilted worlds](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## Hold the tilt and sensor policy fixed

The periodic 7.08-million-cell lattice holds a working and saved 32-bit word per cell. A frozen local network controls movement and authorized writes. Correlated false write pulses follow axes that differ by region. An invertible shear tilts one family of the region boundaries. The earlier comparison estimated all 64 scored tilts correctly and missed at least one offset in 38 observations. Its retained-word score was lower than the axis-aligned control. The new version uses the same frozen detector, same eight worlds, same tilt estimates and same per-round sampling. The current-frame and supplied controllers reproduced every archived tally. [Original tilted-wall benchmark](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Preregistered intervention](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Only the new arm accumulates the three offset score curves across valid observed fault rounds. It chooses the best offset in each accumulated curve. Accumulation restarts when the fitted tilt changes. Each policy uses 64 sampled lines per axis and 1,024 dedicated witness anchors per region, consulting at most 69,632 detector entries each frame. Both fit-based arms infer their angle from the same current samples. The new estimator retains previous summaries, without using extra samples in a frame. The physical simulated fields still materialize in memory. [Frozen controller](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-full-101.json) · [Pinned source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

| Scored condition | Current-frame offsets | Pooled offsets | Supplied geometry |
|---|---:|---:|---:|
| Aligned retention | 69.30% | 70.16% | 70.26% |
| Tilted retention | 68.79% | 70.18% | 70.26% |
| Complete tilted offset vectors | 26/64 | 64/64 | 64/64 |

The paired tilted deficit versus supplied geometry was −0.076 points (95% interval −0.125 to −0.032), inside the −0.75-point tolerance. The aligned gain was +0.86 points (+0.51 to +1.19). World-level resampling keeps all eight scored rounds from one world together. The result establishes that offset estimates can improve while the observed angles, sampling budget and routing rule stay paired. Offsets were stationary in these tests. A separate comparison checks how to discard stale evidence after a jump. [Raw tallies](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Independent reconstruction](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Moving-wall protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

## Reproduction

The Studio used an arm64 Apple M5 Ultra with 256 GiB unified memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The experiment took 610.20 seconds at 14.33 GB peak MLX allocation. Run `python spatial_references/sheared_history_study/verify.py` with NumPy from the repo root. Model replay uses the pinned code with `STUDIO_JOB_DIR` set to a fresh result directory and the prior public study result linked under `runs/spatial-sheared-witness-7077888` in `STUDIO_QUEUE_ROOT`. The owner proposed spatial reference and wall research. OpenAI Codex registered, implemented, ran, audited and documented the experiment. [Receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt) · [Verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)