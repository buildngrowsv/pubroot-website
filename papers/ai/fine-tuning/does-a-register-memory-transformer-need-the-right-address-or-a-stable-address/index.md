---
title: "Does a register-memory transformer need the right address or a stable address?"
paper_id: "2026-368"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T00:54:56Z"
abstract: "A 14.3M-parameter transformer trained with the correct register addresses achieved 93.30% balanced accuracy on held-out overwritten registers. Shifting every eligible address by one event throughout training and testing preserved 92.26%. Redrawing addresses randomly at the same density reduced performance to 9.06%, close to dense attention at 8.85%. The stable-minus-random difference was 83.20 percentage points, with a program-paired 95% bootstrap interval of [82.43, 83.98]. Changing the routing after training also sharply reduced accuracy. The results show that the learner can use a predictable displacement on this generated task."
score: 6.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A 14.3M-parameter transformer trained with the correct register addresses achieved 93.30% balanced accuracy on held-out overwritten registers. Shifting every eligible address by one event throughout training and testing preserved 92.26%. Redrawing addresses randomly at the same density reduced performance to 9.06%, close to dense attention at 8.85%. The stable-minus-random difference was 83.20 percentage points, with a program-paired 95% bootstrap interval of [82.43, 83.98]. Changing the routing after training also sharply reduced accuracy. The results show that the learner can use a predictable displacement on this generated task.

![Register recall under exact, displaced, random and dense attention](https://raw.githubusercontent.com/buildngrowsv/fixed-reference-[REDACTED_SECRET]-recall.png)

## Programs, model and controls

Each 256-token program contains 64 four-token events and 16 registers. Initialization assigns one of 32 values to each register. Later events write new values or query the original or current value. Query answers never appear as query inputs. The primary score equally weights accuracy on original and current queries whose register had changed. A simple interpreter can answer every valid query. This benchmark examines sample-efficient learning of a generated algorithm. Related associative-recall benchmarks also study retrieval of earlier information. [Program generator](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Zoology](https://arxiv.org/abs/2312.04927)

All learned arms use eight blocks, width 384, six heads, shared initialization seed 101, identical program batches, and 512 optimizer updates. Only the first head in block 4 receives the special mask. At a query endpoint, the matched head can read the end markers of earlier writes or initializations to its register and itself. The displaced arm moves each such address forward one event cyclically within the prior events. The random arm draws exactly as many earlier endpoints, uniformly without replacement, independently of the values and answer. Every other head retains standard causal access. The random arm retains the query-dependent count of eligible writes. That count alone was insufficient to reproduce the stable arm's performance. [Original design](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md) · [Random-address follow-up](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

| Training and inference | Original value | Current value | Balanced |
|---|---:|---:|---:|
| Correct addresses | 98.74% | 87.85% | 93.30% |
| Stable one-event shift | 99.25% | 85.27% | 92.26% |
| Newly randomized addresses | 12.04% | 6.08% | 9.06% |
| Dense attention | 11.96% | 5.73% | 8.85% |
| Correctly trained, shifted only at inference | 3.66% | 10.70% | 7.18% |
| Correctly trained, randomized only at inference | 6.82% | 8.30% | 7.56% |

The independent test panel had 1,024 programs containing 5,325 qualifying original and 5,409 qualifying current queries. The validation panel contained 1,024 other programs. Stable displacement beat the random control by 83.02 points on validation [82.23, 83.77], satisfying the prespecified ten-point distinction. Correct addresses exceeded the stable displacement by only 1.30 points on validation and missed the separate five-point replication criterion. These results are consistent with an earlier block learning to relay the value to a neighboring event. Other circuits could also exploit a stable map. The measurements do not localize a relay or establish a unique computation. [Intervention results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Random-control results](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Registered value-swap follow-up](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].md)

## Scope and reproducibility

This is a single training seed and program format. The confidence intervals resample programs, keeping all events of each program together. There is no training-seed uncertainty estimate. The supplied mask directly encodes relationships among register IDs. These scores do not estimate gains on unconstrained real code. The positive finding concerns stable addressing under the stated data and update budget.

The experiments used Apple M5 Ultra, macOS 27.2, Python 3.12.16, MLX 0.32.4 and NumPy 2.5.5. The queue records source revisions, the parent checkpoint and exact execution receipts. The public evidence includes per-program counts for all arms and interventions. From the repository root, run `python register_routing/verify.py register_routing/results` and `python register_routing/verify_random.py register_routing/results/random register_routing/results`. The second audit matches archived predictions at the count level and independently reproduces the paired interval. [Training and fixed routing](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Random control](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].py) · [Audit output](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json) · [Execution manifest](https://github.com/buildngrowsv/fixed-reference-[REDACTED_SECRET].json)

The account owner proposed testing routed, protected pathways in neural networks. OpenAI Codex designed and implemented the comparisons, ran them over SSH on the owner's Studio, verified the public score evidence and assisted with writing.