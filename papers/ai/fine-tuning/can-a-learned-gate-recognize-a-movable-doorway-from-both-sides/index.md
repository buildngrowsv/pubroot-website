---
title: "Can a learned gate recognize a movable doorway from both sides?"
paper_id: "2026-351"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T22:47:41Z"
abstract: "A small network trained on final words learned when to allow a signal across a wall. On larger cubes with a rotated wall and a newly placed door, it produced the correct 32-bit word in both open and sealed conditions at all 681 affected cells, across each of three training seeds. An equally sized network with one endpoint's latch hidden achieved 98.76% ordinary word accuracy and got zero of the 681 open/sealed pairs right. Enumerating the learned gate on all 64 possible local inputs confirmed that each full model had learned the complete decision table."
score: 8.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A small network trained on final words learned when to allow a signal across a wall. On larger cubes with a rotated wall and a newly placed door, it produced the correct 32-bit word in **both** open and sealed conditions at all **681** affected cells, across each of three training seeds. An equally sized network with one endpoint's latch hidden achieved **98.76%** ordinary word accuracy and got **zero** of the 681 open/sealed pairs right. Enumerating the learned gate on all 64 possible local inputs confirmed that each full model had learned the complete decision table.

![Overall and intervention-sensitive word accuracy alongside exhaustive gate scores](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].png)

## What the model has to learn

A wall in a neural network can be implemented by forbidding a read across a boundary. That leaves open whether the network can learn *when* to permit the read. An earlier experiment supplied the blocked edges directly. Here each voxel has a region label, a binary latch and a distractor bit. A movement command identifies the candidate neighbor. If the two region labels match, the read succeeds. Across regions it succeeds only when both latches are on. The graph, choice of candidate neighbor, and stay-or-read operation are built into the experiment. The correct gate decision is hidden. Learned local computations on graph edges have a precedent in neural message passing. [Earlier supplied-wall experiment](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Gilmer et al.](https://arxiv.org/abs/1704.01212) · [Prospective protocol](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

The model receives six endpoint measurements. A 6→16→1 rectified network followed by a sigmoid produces one mixing weight. It applies that same weight to all 32 channels, interpolating between the cell's previous word and the neighbor's previous word. Each cell updates in parallel. The 129 parameters are shared across sites, steps and directions. The control retains the full parameter array and overwrites the neighbor latch input with zero at every step in training and evaluation. We also run unrestricted movement and an interpreter with the exact rule. [Controller](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Generator](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

Each periodic cube contains two regions separated by two seams. We open a single random crossing on the middle seam. Closed crossings can have either endpoint on or neither on. Region labels may be globally reversed. In the final step both endpoints of the candidate door attempt to cross, in both open and closed worlds. This enriches the task with attempted crossings and can cue their location. It leaves the state of the door ambiguous without the sensor readings. Words start as random signs. Each fit used 500 Adam updates at 0.015, ten 4×4×4 boards per step, eight transitions and only a final bitwise loss. Open and sealed training boards were sampled independently. The six fits took between 0.45 and 1.07 seconds each in the recorded training section on an Apple M5 Ultra. [Training histories](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## Why ordinary accuracy missed the failure

The primary endpoint holds the input words, motion commands and nuisance sensors fixed. Closing the door flips exactly one latch at the designated edge. An independent backwards walk traces which initial word reaches each final cell in each world. We score the cells whose correct words change and require all 32 signs to match in both worlds. A second intervention flips the irrelevant sensor on the same endpoint while keeping the door open.

The seed-101 pilot recovered 203/203 affected validation pairs and the blind gate got zero. Changing the latch affected all 203 model outputs; changing the irrelevant bit affected none. This met the prospective gate for two more fits. All three seeds then faced the same 128 fresh open/sealed pairs at twice the side length and twice the rollout depth. Training placed the wall perpendicular to x; test walls were perpendicular to y or z. Sharing the gate across axes is an inductive bias supplied to the model.

| Method | Ordinary exact words, open and sealed | Exact in both settings on 681 affected cells |
|---|---:|---:|
| Reads both endpoint latches | 100% | 681 / 681 in every seed |
| Blinded to the neighboring latch | 98.76% | 0 / 681 in every seed |
| Unrestricted transport | 42.58% | 0 / 681 |
| Interpreter with the known rule | 100% | 681 / 681 |

Ordinary accuracy pools the open and sealed versions of 65,536 sites per condition and averages the three model seeds. Most of those words have the same desired value in both worlds. The one-ended gate got zero affected words right with the door open; with the door sealed it recovered 668, 676 and 670. The full controller changed all 681 affected predictions after the latch edit, and zero after the nuisance edit. A paired bootstrap over whole cubes and seeds gives a ceiling-degenerate full-minus-blind interval of [100, 100] percentage points on the observed pairs. It is an empirical description of this panel. Predictions under other sensor semantics remain an open question. [Counts, checkpoint replay and trace checks](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

## What the weights say beyond the test cubes

After scoring, we enumerated all 64 binary sensor configurations, including the nuisance bits. The full fits assigned more than half the mixture weight to the correct decision on all 64. Each blinded fit did so on 56. With one latch hidden, certain sensor inputs correspond to both an open and a blocked edge, so a deterministic local gate cannot be correct on every row. The exact gate outputs and learned weights are included.

There is also a finite-horizon bound on the original soft model. If the correct branch always has weight at least q, the exact source word contributes at least q to the first update and at least q raised to T after T updates, by following the oracle path through the mixtures. Whenever this exceeds one half, every sign of that source word is preserved even if all other contributions have the opposite sign. The smallest correct-branch weights in seed order were 0.95885, 0.96445 and 0.93959. In real arithmetic these imply conservative guarantees through 16, 19 and 11 steps respectively for any legal binary inputs and any grid size. Seed 307 still recovered every tested word at 16 steps. The bound is sufficient and can be loose. It uses the architecture's nonnegative convex mixtures and unit-magnitude signed inputs. We evaluated the table numerically in float64 using the released weights; this argument does not bound backend roundoff. The 16-step empirical results were reproduced from the saved checkpoints on Metal. [Exhaustive table and verifier](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py)

## Decision and reproduction

The hand-written rule handles this task exactly at zero training cost. The learned result establishes that final-word supervision can recover the rule in this particular representation. It supplies a verifiable donor for a future transplant. A credible transfer test must give the host the same observations and training budget, leave the host room to improve, and score each new solve with the donor enabled and disabled. The blinded control deliberately removes information and is unsuitable as evidence for a transplant benefit.

From the repository root on Apple Silicon with Python 3.12, MLX 0.32.4 and NumPy 2.5.5, run the following. The final chart requires Matplotlib. Replaying with the supplied weights requires only the second command.

```sh
python hidden_door/experiment.py
python hidden_door/verify.py
python hidden_door/figure.py
```