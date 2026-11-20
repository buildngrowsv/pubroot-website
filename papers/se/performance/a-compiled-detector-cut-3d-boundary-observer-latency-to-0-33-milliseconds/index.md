---
title: "A compiled detector cut 3D boundary-observer latency to 0.33 milliseconds"
paper_id: "2026-540"
author: "buildngrowsv"
category: "se/performance"
date: "2026-11-20T14:38:27Z"
abstract: "A compiled MLX observer returned the same 11 decisions on all 48 detector frames of a 192\u00b3-cell field as two equivalent NumPy implementations. Median latency was 0.331 ms for the compiled observer, 1.619 ms for direct device gathers and NumPy reductions, and 6.765 ms when materializing the entire detector field first. The median world-paired speed ratio against direct gathers was 4.97\u00d7 (95% interval 4.35\u20135.16\u00d7)."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A compiled MLX observer returned the same 11 decisions on all 48 detector frames of a **192³-cell** field as two equivalent NumPy implementations. Median latency was **0.331 ms** for the compiled observer, **1.619 ms** for direct device gathers and NumPy reductions, and **6.765 ms** when materializing the entire detector field first. The median world-paired speed ratio against direct gathers was **4.97×** (95% interval 4.35–5.16×).

![Median detector observation latency for three implementations](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

All three methods choose three axis-aligned boundary offsets and eight regional witness directions using the same sample coordinates and tie rules. The direct-gather baseline hands two batches of indices to MLX and uses NumPy to determine the boundaries and routes. The compiled function performs both gathers and their intermediate index and reduction operations on the device, materializing only the 11 decision values in NumPy. It still reads up to 69,632 detector entries. An earlier recurrent evaluation on eight grids of the same size and one checkpoint reproduced all 4,608 archived tallies and all 1,536 stored coordinates. [Registered timing protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Timing code](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Independent recurrent parity evidence](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The timed panel used aligned and shifted frames from eight worlds, each with three frozen detector checkpoints. Frame creation, index setup and one per-method warm-up occur before timing. Each warmed frame ran 12 repetitions with cyclic order and output materialization included. The 0.331 ms median pools frame repetitions. The paired gain pools frame-wise median timing ratios within a world, then uses the median across worlds. This gives 20.70× against the full-materialization baseline (95% world bootstrap interval 17.88–21.52×). The measurement covers the observer on one Studio and leaves full recurrent simulation throughput open. [Raw timings and decisions](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Numeric report](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Independent verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

The Apple M5 Ultra job took 7.20 seconds and peaked at 0.93 GB of MLX allocation. Recompute the timing comparisons with NumPy using `python [REDACTED_SECRET].py` from the repo root. [Receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Environment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt)