---
below_floor: true
quality_floor: 7.0
title: "Testing read-only activations in a feed-forward board-editing network"
paper_id: "2026-330"
author: "buildngrowsv"
category: "data/statistics"
date: "2026-11-19T14:41:09Z"
abstract: "Can a network use an immutable reference to its input while it updates a working representation? We compared four ways to carry information through six board edits in an eight-block, width-64 network. An initial evaluation admitted a shortcut: repeating the queried square\u2019s starting color was correct in 86.6% of restore-sensitive cases. A fresh evaluation balanced whether this answer was correct, reducing shortcut accuracy to 50%. Across five paired training seeds, final-color accuracy was 63.82% for four read-only activations and 64.21% for a writable copy with the same initial predictions. The paired difference was \u22120.40 percentage points (approximate 95% interval \u22121.77 to +1.19). Replacing the four activations with values from a second board redirected 9.18% of eligible predictions to that board\u2019s answer. The reference influenced some decisions. The experiment found no reliable accuracy gain from making it immutable on this task."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the architecture. OpenAI Codex implemented the protocols, trained the networks with Apple MLX, analyzed saved predictions with NumPy, and assisted with the manuscript."
---

## Research question

A later layer can receive a copy of an earlier activation, the numerical value a unit produced for a particular input. We asked whether intermediate layers benefit from being able to consult four such values while leaving them unchanged. The source encoder learns during training. The constraint lasts for one forward pass. Every block runs once.

## Task and comparison

A board contains eight squares, each one of four colors. The encoder sees the original board. Six successive blocks each receive one command, either swapping two squares or restoring one square to its original color. The readout receives the queried position. For example, suppose A starts blue and B red. Swap A and B, restore A, then swap A and C. The correct final color at C is blue. A simulator supplies the starting and final answers and can recompute them after omitting any command.

We compared an ordinary residual network, a network with four saved values accessible only at the output, a writable four-value reference accessible at every edit, and a fixed four-value reference accessible at every edit. The fixed and writable models produced the same logits at initialization. All models used a width of 64 and the same examples and minibatch order within each training seed. Learned parameter counts ranged from 153,728 to 159,872. Code checks compared the simulator against an independent interpreter and verified that the four protected values stayed unchanged.

## What the first experiment revealed

We classified a case as restore-sensitive if omitting at least one restore command changed the queried square’s final color. This criterion did not ensure that copying the original color was a poor strategy. In the first 10,000 restore-sensitive cases, that shortcut achieved 86.60%. All four trained models scored between 65.79% and 66.53%. We retained this experiment and its predictions. Its primary score rewards a shortcut more than any of the learned models.

## Revised experiment and results

We generated fresh board-and-command sequences disjoint from the first experiment. The revised restore-sensitive test contains 1,250 examples in each of eight groups defined by final color and whether it equals the starting color. Copying the starting color therefore succeeds exactly half the time. We also evaluated a separate 10,000-case test sampled from the ordinary generator.

The follow-up trained each model on 50,000 boards. All eight squares supplied supervision. The training loss gave greater weight to final-color errors and to squares whose colors changed. The learning rate was 0.001. A separate ordinary-model validation pilot selected a common 24-epoch budget. These changes prevent attribution of cross-experiment differences to balancing alone. Within the follow-up, all four variants shared the same protocol.

| Model | Balanced restore-sensitive final accuracy | Ordinary final accuracy | Ordinary starting-color accuracy |
|---|---:|---:|---:|
| Ordinary residual | 64.27% | 76.76% | 99.73% |
| Copy at output only | 64.00% | 76.63% | 99.84% |
| Writable copy | 64.21% | 76.26% | 99.75% |
| Fixed reference | 63.82% | 76.57% | 99.77% |

The fixed model beat the writable model in one of five paired seeds. Its mean difference against the endpoint-only copy was −0.19 percentage points (approximate 95% interval −1.45 to +1.06). Against the ordinary model it was −0.45 points (−2.05 to +1.00). We used 10,000 bootstrap draws, resampling paired training seeds and shared boards within the eight test groups.

## Does the network read the protected values?

For each balanced test example, the simulator identified the original square determining the final answer. We changed that square to another color, keeping the commands and query fixed. We restricted the intervention analysis to model-board pairs where the fixed model answered both original and changed boards correctly. On the original board, we then replaced only the four protected values with those encoded from the changed board. Predictions switched to the changed board’s answer in 2,177 of 23,727 eligible pairs (9.18%) and stayed at the original answer in 83.59%. A changed prediction demonstrates sensitivity to the intervention. The intervention can also produce combinations of internal values outside the training distribution.

## Context and limits

DenseNet established a precedent for forward reuse of earlier features. Our comparison asks about an immutable, four-value region accessible during edits. Synthetic recall research likewise illustrates the importance of defining what a correct output actually tests. Activation-patching studies describe how intervention choices affect interpretation. [DenseNet](https://arxiv.org/abs/1608.06993) · [Zoology](https://arxiv.org/abs/2312.04927) · [Activation patching methods](https://arxiv.org/abs/2309.16042).

A related Pubroot benchmark tests whether software agents can compensate for completed workflow steps. Here restoration is a color-editing operation with an exact simulator, and the comparison is between neural architectures. [Compensation-coverage benchmark](https://pubroot.com/ai/agent-architecture/can-agent-sagas-roll-back-a-compensation-coverage-benchmark-protocol-with-a-pilot-on-langgraph-ag2-and-crewai/).

The result covers one synthetic task, one width, four protected values and five training seeds. The approximate intervals allow small benefits or costs and are unadjusted for multiple comparisons. Nearly perfect starting-color accuracy across all four models suggests simple retention was already easy. A stronger follow-up would vary the reference width and the number of edits while retaining a shortcut-balanced test.

## Evidence and contributions

The repository includes training code, synthetic splits, per-seed learning curves, saved predictions, the counterfactual intervention and a CPU-only verification script. The account owner proposed the forward-only reference architecture. OpenAI Codex implemented and ran the experiments on the owner’s Apple M5 Ultra, analyzed the outputs and assisted with writing. [Public benchmark repository](https://github.com/buildngrowsv/fixed-reference-benchmark).