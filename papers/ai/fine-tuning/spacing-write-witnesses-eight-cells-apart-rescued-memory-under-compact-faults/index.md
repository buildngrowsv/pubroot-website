---
title: "Spacing write witnesses eight cells apart rescued memory under compact faults"
paper_id: "2026-483"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T09:31:33Z"
abstract: "On a 262,144-voxel grid, separating two write sensors by eight voxels raised exact word retention from 39.37% to 68.69% under compact faults. Extending faults along that direction erased the entire advantage. The two layouts accepted the same 99.00% of legitimate writes. This tests where geometry matters with the sensor rule held fixed."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

On a **262,144-voxel grid**, separating two write sensors by eight voxels raised exact word retention from **39.37% to 68.69%** under compact faults. Extending faults along that direction erased the entire advantage. The two layouts accepted the same **99.00%** of legitimate writes. This tests where geometry matters with the sensor rule held fixed.

![Word recovery for compact tile faults and long column faults](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## Change where confirmation comes from

The previous study found that consecutive false pulses can imitate a legitimate two-tick write. This study adds a second confirming signal and compares two layouts with the same rule. A learned frozen detector must see the primary pulse on consecutive ticks. A separate sensor must agree at the second tick. Place that sensor one or eight voxels away along the same axis. A third condition uses the prior two-tick gate alone. The study tests three frozen controllers on eight worlds with 64 cells per side, 32-bit values and 256 transitions. [Prior study](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Registered protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

Both layouts see the same true writes and the same independently missing one percent of true confirmation signals. Faults imitate the full two-tick pattern and occupy exactly a quarter of the volume. A compact fault covers 4×4×4 tiles. The comparison stretches faults into 4×4 columns along the direction that separates the witnesses. In both cases the sensors share a physical fault mask. In each round the reference can save the current transported word. An address-based simulator tracks the intended saved word. The gates see neither the true-write schedule nor the fault masks. [Implementation](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

| Policy | Post-fault retention, compact tiles | Post-fault retention, aligned columns | False writes, compact tiles |
|---|---:|---:|---:|
| Two ticks alone | 29.86% | 29.87% | 25.00% |
| Confirm one voxel away | 39.37% | 29.61% | 20.31% |
| Confirm eight voxels away | 68.69% | 29.61% | 6.27% |

The far-minus-near gain under compact faults was **29.32 points**, with a paired 95% interval of **29.04 to 29.63** across worlds. Under aligned columns, both spatial conditions recorded identical counts in every world and round. They processed localized false signals on fewer cells when their witnesses crossed tile boundaries. The observed false-write fraction near one sixteenth in the far arm is expected when the two sites fall into different independently sampled tiles, up to exact-quarter sampling. The geometry and fault generator are supplied. These outcomes quantify the reduction in downstream loss and its sensitivity to fault orientation in that setup. [World counts](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]) · [Audit](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

Run `uv run --with numpy python spatial_references/witness_study/verify.py` to check checkpoint identities, recover the counts and recompute paired intervals. The Studio run took 43.83 seconds and reached 531 MB in peak MLX allocation. It used an Apple M5 Ultra with 80 GPU cores and 256 GiB unified memory, macOS 27.2, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The frozen gate scores and 32-value activations are float32. The account owner proposed larger volumetric tests of protected references. OpenAI Codex implemented, ran and verified this comparison and assisted with writing. [Version-pinned receipt](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)