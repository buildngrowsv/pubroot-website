---
title: "Dedicated detector pairs recovered sparse witness routing within 0.20 retention points"
paper_id: "2026-520"
author: "buildngrowsv"
category: "cs/algorithms"
date: "2026-11-20T12:49:20Z"
abstract: "On an 884,736-cell grid under shifted faults, dedicated detector pairs recovered 70.54% of 32-bit words. Reusing the boundary lines for witness selection recovered 67.72%. Dense witness selection with the same inferred boundaries recovered 70.74%. Dedicated samples recovered 2.82 percentage points over reuse and came within 0.20 points of dense selection, using at most 5.79% of the detector field for both statistics. The paired 95% deficit interval versus dense selection was 0.08 to 0.33 points."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On an 884,736-cell grid under shifted faults, dedicated detector pairs recovered **70.54%** of 32-bit words. Reusing the boundary lines for witness selection recovered **67.72%**. Dense witness selection with the same inferred boundaries recovered **70.74%**. Dedicated samples recovered 2.82 percentage points over reuse and came within 0.20 points of dense selection, using at most **5.79%** of the detector field for both statistics. The paired 95% deficit interval versus dense selection was 0.08 to 0.33 points.

![Three matched witness policies with identical inferred boundaries](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-probes.png)

## Partially observed fault-tolerant memory

The synthetic memory grid gives each cell a working 32-bit word and a saved copy. A frozen local transport rule moves working values. A frozen detector checks its local and neighboring signals. A memory write requires two consecutive detector ticks plus confirmation from a second position eight cells away. Correlated false pulses can fire both detectors if that witness falls along the fault's long axis. The benchmark asks how much observed detector data suffices to choose a witness direction that limits false writes. It models a known family of periodic planar regions in a controlled simulation. [Memory update and detector source](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Boundary inference and shared-line baseline](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Both sparse and dense witness policies estimate the same three boundary translations from 64 stratified detector lines per axis in a periodic 96³ grid. The earlier reuse policy also estimated each direction's joint detector activation from exactly those lines. In the dedicated policy, choose 1,024 uniform random base coordinates with replacement in each inferred region, fixed in regional coordinates per world. Read each base detector and its three axial neighbors at distance eight, wrapping each offset inside the region. Estimate all three co-activation fractions on the same base coordinates and choose the axis with the lowest estimate. The dense witness policy performs the corresponding calculation over every cell in the inferred region. The dedicated arm uses at most 18,432 readings for boundaries and 32,768 more for orientation, or 51,200 of 884,736. [Registered sampling rule](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Runnable source at the experiment revision](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Three frozen checkpoints and eight paired worlds share initialized data, commands, conditions and true writes. Aligned and translated cases share the underlying false pulse patterns. Each world has 16 rounds of 16 updates. The latter eight rounds contribute to the endpoint, the fraction of cells recovering all 32 intended bits. Paired intervals draw complete worlds with their rounds and checkpoints together. The independent audit verifies every inferred boundary, exact fixed and true-boundary control counts, and hashes of the dense and reuse raw archives. [New raw counts and offsets](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Dense control archive](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz) · [Reuse archive](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].npz)

| Witness and boundary policy | Retention, aligned | Retention, shifted | False writes, shifted |
|---|---:|---:|---:|
| Fixed boundaries, dense witness | 72.56% | 65.24% | 7.69% |
| Inferred boundaries, reuse lines | 67.62% | 67.72% | 6.40% |
| Inferred boundaries, dedicated coordinates | 70.50% | 70.54% | 5.76% |
| Inferred boundaries, dense witness | 70.60% | 70.74% | 5.71% |
| Supplied boundaries, dense witness | 72.56% | 72.55% | 5.27% |

The dedicated arm gained +2.82 points over reuse under shifted faults (95% paired interval +2.41 to +3.28) and +5.30 over fixed boundaries (+3.61 to +7.13). Its aligned deficit versus dense routing was 0.11 points (0.04 to 0.17). All arms accepted 99.00% of legitimate writes. Both layouts met the registered one-point dense margin and all other criteria passed. The practical intervention changes observation count and placement together. The staged simulator uses dense detector tensors and measures only the information used by the sparse estimator. It motivates a fixed-budget comparison at 192³ with the same observation count and a combined field fraction below 1%. [Paired statistics and artifact hashes](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

From the public repository root, run `uv run --with numpy python spatial_references/anchored_witness_study/verify.py` to reproduce the claim counts and intervals from the three archived arrays. The verifier is runnable on CPU with NumPy and uses the frozen checkpoint hashes. The pinned simulation runner uses MLX and the queue's two dependency archives. The Studio run took 142 seconds and reached 1.79 GB peak MLX allocation. The linked Studio capture records an arm64 M5 Ultra with 256 GiB unified memory, macOS build 26B118, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. It was obtained directly over SSH after the trial. The owner proposed the spatial-memory experiments and OpenAI Codex implemented, ran, audited and documented them. [Independent verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Execution receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Direct Studio environment capture](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-environment.txt) · [Prior reuse submission and review](https://github.com/buildngrowsv/pubroot-website/issues/516)