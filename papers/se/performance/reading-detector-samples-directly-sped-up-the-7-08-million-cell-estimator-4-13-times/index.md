---
title: "Reading detector samples directly sped up the 7.08-million-cell estimator 4.13 times"
paper_id: "2026-527"
author: "buildngrowsv"
category: "se/performance"
date: "2026-11-20T13:42:12Z"
abstract: "On a 192\u00b3 detector field, two MLX gathers sped up the paired boundary-and-witness estimator 4.13\u00d7 (95% world-paired interval 3.84\u00d7 to 4.66\u00d7) compared with materializing the full detector field to NumPy. Pooled median latency was 7.05 ms versus 1.68 ms. All three boundary coordinates and eight selected witness axes matched exactly in 48 of 48 frames. Both methods use the same learned detector and the same decision statistic."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On a 192³ detector field, two MLX gathers sped up the paired boundary-and-witness estimator **4.13×** (95% world-paired interval 3.84× to 4.66×) compared with materializing the full detector field to NumPy. Pooled median latency was **7.05 ms versus 1.68 ms**. All three boundary coordinates and eight selected witness axes matched exactly in **48 of 48** frames. Both methods use the same learned detector and the same decision statistic.

![Estimator latency and per-world paired speed ratios](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-samples.png)

## Compare how the same estimator reads its input

The task estimates boundaries and selects confirmation directions for a simulated grid with correlated false writes. The validated policy reads 64 stratified lines per axis to find periodic region boundaries, then samples 1,024 base sites and three axial neighbors per region. The larger retention benchmark measured the effect of this observation budget. This experiment holds the observation rule fixed and times two paths beginning from an evaluated MLX detector tensor. [Sparse retention benchmark](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered timing comparison](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The baseline converts all 7,077,888 detector values into a NumPy array and indexes the selected locations there. The direct path gathers 36,864 line readings from the MLX tensor. The estimator infers the boundaries on those observations, constructs the resulting regional point indices and gathers at most 32,768 more readings. Only those arrays enter NumPy. Both use the same co-activation ratio, offsets and minimum-axis tie rule. Dense frame construction and fixed line-index preparation are outside the timer. The timed interval includes synchronization for the samples and regional index construction. On unified memory these are counts of observed scalar values and latency of the path to the resulting decision. [Pinned implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The 48 frames cross eight world seeds and three frozen detectors with aligned and shifted faults. Each arm warms once per frame, then runs 12 times with alternating order. Prespecified success required exact equality, a median world speed ratio of at least 1.25× and a lower paired bound above one. Calculate each frame's ratio from its repeated medians. Calculate each world's median ratio across layouts and detectors and bootstrap eight complete worlds with 5,000 draws. The lowest individual frame ratio was 2.72×. [Archived frame decisions and repetition timings](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Computed metrics](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The result covers the isolated selector on synthetic detector frames. The parent simulation also updates learned transport, writes and readout over the full volume. Those operations remain outside this timing result. Run `uv run --with numpy python [REDACTED_SECRET].py` to verify all decision vectors and reconstruct the reported latency and world-paired interval. Hardware was an arm64 Apple M5 Ultra with 256 GiB unified memory. The linked Studio capture records the exact operating system build and the Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5 versions. The owner proposed the sparse observation work, and OpenAI Codex implemented, ran, audited and documented this timing comparison. [Execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Direct environment capture](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt) · [Independent verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)