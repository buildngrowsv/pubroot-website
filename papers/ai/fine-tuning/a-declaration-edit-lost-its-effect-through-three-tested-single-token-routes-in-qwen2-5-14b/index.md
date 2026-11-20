---
title: "A declaration edit lost its effect through three tested single-token routes in Qwen2.5-14B"
paper_id: "2026-446"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-20T07:47:42Z"
abstract: "A 25-dimensional edit to an earlier declaration reversed the read of its class in 242 of 256 paired Python files on one panel and 246 of 256 on a second panel. When the rest of the hidden states were restored to the untouched run through block 17, neither of two assignment signs nor the final query token carried enough of the change to reverse a pair. The final query token also failed when it was allowed to receive the edit through the intact model before capture at block 17."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

A 25-dimensional edit to an earlier declaration reversed the read of its class in 242 of 256 paired Python files on one panel and 246 of 256 on a second panel. When the rest of the hidden states were restored to the untouched run through block 17, neither of two assignment signs nor the final query token carried enough of the change to reverse a pair. The final query token also failed when it was allowed to receive the edit through the intact model before capture at block 17.

![Mean original-letter margins for the unrestricted edit and both single-token relay panels](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Generated task and metric

Each group has two earlier class definitions and two possible destinations for a final attribute read. Starting from a program like the following, write a second version by replacing the final letter of both attributes with a different letter. Run both files with the query selecting the first class, then run them again with the same query selecting the second class.

```python
class Cedar:
    item_732000m = 19

class Harbor:
    item_732000m = 83

def fetch():
    scratch_0 = 216
    return Cedar.item_732000
```

The final line is a prompt prefix. Appending `m` makes the program return 19, and appending the alternate letter makes the read raise `AttributeError`. In the paired version, those relations reverse. Parsing and executing the programs verifies both the target value and the invalid alternative. The actual generator varies class names, assigned values, suffix letters and intervening scratch lines. The two permitted final-letter completions are single Qwen tokens. There are two declaration token changes between versions. They occur before the class name in the query. The two query versions therefore share the same source activation for either declaration. [Generator and paired source audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [All prompts in both panels](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Second panel prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-results/programs.json)

For a query, the margin is the logit of the original correct final letter minus the logit of the partner letter. A paired reversal requires a strictly negative margin in both letter versions. A group qualifies only when both queries and both letters are correct in unmodified inference. All 256 groups satisfied that rule on each panel. We use the first declaration as the sole edit site. Querying the second class measures the same edit on a different read. The bootstrap samples whole four-prompt groups with 5,000 draws per panel. [Probe definition and archived tests](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Edit estimation and the imposed wall

We froze Qwen2.5-14B base revision `97e1e76335b7017d8f67c08a19d103c0504298c9`. To learn the edit directions, use 512 independent programs with a single declaration and two possible letter endings. Record their paired hidden-state differences at the declaration token after block 10. Regress these differences on their corresponding 26-dimensional letter-indicator differences. The ridge penalty is 0.02 times the mean diagonal of the indicator Gram matrix. The first 25 left singular vectors of the fitted hidden-by-letter matrix form columns of an orthonormal basis U. For each test variant, replace its source state x with x + UUᵀ(x_partner − x). All other states start unchanged. The unrestricted control simply continues running the transformer after this edit. [Calibration details and code](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Underlying interchange method](https://arxiv.org/abs/2303.02536)

The imposed wall runs a clean and an edited copy through blocks 11–17. After each block, it takes all token states from the clean copy except the edited source and the candidate relay. At block 17's exit it restores the source state too. From block 18 until the ordinary readout, the relay at the boundary is the only surviving state difference. The first test uses the assignment sign in each class as its candidate relay, in separate arms. Both assignment signs appear after the source under the usual causal mask. The second test uses the final query token. Its restricted arm uses the same step-by-step restoration rule. Its capture arm allows normal propagation through block 17 and then retains only the query-token difference. [Assignment protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Query protocol](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Assignment implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Query implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

## Results at the block-17 boundary

| Panel and route | First-class reversals | Second-class reversals | Mean original-letter margin, first class | Median relay displacement |
|---|---:|---:|---:|---:|
| Assignment panel, native | — | — | +12.64 | — |
| Assignment panel, unrestricted | 242 / 256 | 0 / 256 | −4.64 | — |
| Assignment sign of edited class | 0 / 256 | 0 / 256 | +12.63 | 11.91 |
| Assignment sign of other class | 0 / 256 | 0 / 256 | +12.64 | 1.13 |
| Query panel, native | — | — | +12.81 | — |
| Query panel, unrestricted | 246 / 256 | 0 / 256 | −4.67 | — |
| Final query token, capture | 0 / 256 | 0 / 256 | +12.80 | 7.90 |
| Final query token, restricted | 0 / 256 | 0 / 256 | +12.77 | 6.39 |

The unrestricted first-versus-second query differences were +94.53 points (95% interval +91.80 to +97.27) and +96.09 points (+93.36 to +98.44). Neither assignment relay nor either query relay reached the 35% qualification threshold. The unrestricted edit also reduced the other class's mean margin from +12.60 to +5.91 on the assignment panel and from +12.79 to +5.88 on the query panel. It changed zero paired winners there. The relay displacements show that hidden states changed along the isolated paths. Releasing those altered states left the mean output margins near their unmodified values.

These tests establish a limit at the tested tokens and block boundary in one checkpoint, on generated two-class Python completions. A useful effect remained available through the unrestricted path. Later layers, other token positions and combinations of relay states remain separate possibilities. [Assignment audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Query audit](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-audit.json)

Run `uv run --with numpy python nested_surgery/identifier_doorway_study/verify.py` from the repository root. Add `--query` for the second panel. The programs, scores, release norms and source revisions are public. Studio inference took 149 seconds for the assignment panel and 140 seconds for the query panel under Python 3.12, MLX 0.32.4, MLX-LM 0.32.2 and NumPy 2.5.5 on the owner's Apple M5 Ultra. The owner proposed testing walls that prevent communication between selected parts of a network. OpenAI Codex implemented the interventions, operated the runs over SSH, verified the results and assisted with writing. [Assignment receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Query receipt](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-results/receipt.json) · [Review of the shorter assignment-only report](https://github.com/buildngrowsv/pubroot-website/issues/439)