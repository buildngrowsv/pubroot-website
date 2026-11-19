---
title: "Does specializing a coding model\u2019s final feed-forward block create a useful donor?"
paper_id: "2026-355"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T23:01:41Z"
abstract: "Training only the smaller coding model's final feed-forward block made 99 previously missed Python repairs correct in one run. Restoring the original block erased every one of those gains. The same training also broke 93 earlier solves. Across three training orders the specialized donor solved 96\u2013102 of 384 previously unseen repairs, compared with 137\u2013141 for the larger host given the same labeled examples and optimizer steps. Swapping the learned contribution between different requested repairs of the same program changed average accuracy by 0.06 percentage points. The donor failed the predeclared qualification for transplantation."
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Training only the smaller coding model's final feed-forward block made 99 previously missed Python repairs correct in one run. Restoring the original block erased every one of those gains. The same training also broke 93 earlier solves. Across three training orders the specialized donor solved **96–102 of 384** previously unseen repairs, compared with **137–141** for the larger host given the same labeled examples and optimizer steps. Swapping the learned contribution between different requested repairs of the same program changed average accuracy by **0.06 percentage points**. The donor failed the predeclared qualification for transplantation.

![Correct repairs, newly gained repairs and previously correct repairs lost through specialization](https://raw.githubusercontent.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

## Why qualify an expert before inserting it?

We want to know whether an independently trained part can contribute a skill to a larger network. Earlier experiments replaced a host feed-forward module in block 27 and trained block 28 around it. A delimiter task saturated across all controls. A later indentation screen found that the unadapted donor and host often selected different repairs but were almost tied on solves. Here we tried to teach the *part intended for transfer* a skill in its native model before running another transplant. Model stitching motivates asking which representations an interface can connect. This experiment addresses the preceding empirical question of whether the donor contains an advantage worth transferring. [Earlier donor screen](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Bansal, Nakkiran and Barak](https://arxiv.org/abs/2106.07682) · [Qwen2.5-Coder](https://arxiv.org/abs/2409.12186)

Each Python program contains three nested conditions or loops. Inserting four, eight, twelve or sixteen spaces before an addition produces four valid programs with distinct behavior. We create four requests per program, changing only the outputs required by four public assertions. The chosen patch must pass twelve hidden input/output examples. Executing all legal choices against the public assertions uniquely identifies the answer on every released problem. This cheap interpreter sets the performance ceiling. The models use Qwen's native fill-in-the-middle format, with identical tokens for the host and donor. Multiple-choice selection and the small family of programs limit the generality of the result. [Generator and original controls](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py) · [Fill-in-the-middle training](https://arxiv.org/abs/2207.14255)

## The comparison

We fine-tuned Qwen2.5-Coder-0.5B's last feed-forward module, in block 24, leaving all other parameters fixed. Its 13,074,432 trainable weights are precisely the module proposed for transfer. We trained Qwen2.5-1.5B's complete final transformer block as the native control, updating 46,797,824 weights. Both used the same 1,536 labeled examples, identical example order within each seed, 96 Adam steps, batch size 16 and learning rate 0.00002. Calibration loss selected among steps 0, 8, 32 and 96. All six fits selected step 96. The comparison matches data and optimizer steps; the larger control can change its attention as well as its feed-forward weights, and requires more computation. The measured fitting sections took 1.10–1.12 seconds for the donor and 2.88–3.25 seconds for the host on this M5 Ultra. The complete qualification and test script took 42.2 seconds, including generation, tokenization, training, interventions and evaluation, before the independent replay. [Protocol committed before scoring](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md) · [Training, scores and checkpoint selection](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Runtime](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

The split unit was the ordered triple of control-flow forms. The previously explored eight discovery families were excluded. New draws covered 32 training families, four checkpoint-selection families with 128 examples, eight qualification families with 256 examples, and twelve final families with 384 examples. The four requests for a program stayed together. Only the qualification families decided whether to transplant. Every order had to clear a five-point lead over the adapted host with a positive lower family-bootstrap bound, a five-point gain over the original donor with at least one verified new solve lost on reversion, and at least ten points of headroom above the adapted host. [Decision and per-order intervals](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

## Which new solves actually depended on the donor weights?

| Training order | Qualification donor / host, out of 256 | Final donor / host, out of 384 | New final solves lost on reversion | Former solves lost through training | Net new solves |
|---|---:|---:|---:|---:|---:|
| 101 | 63 / 92 | 96 / 137 | 90 | 88 | +2 |
| 211 | 67 / 88 | 100 / 139 | 99 | 93 | +6 |
| 307 | 67 / 84 | 102 / 141 | 28 | 20 | +8 |

The frozen donor solved 65 qualification repairs and 94 final repairs. The frozen host solved 64 and 96. On final families the specialized donor's mean improvement over its frozen state was +1.39 percentage points, paired 95% interval [+0.26, +3.04]. Its difference from the adapted host was −10.33 points [−13.28, −7.29]. These intervals resample whole families and matched training orders over 5,000 draws. There are only twelve final families and three orders. Only **three** new repairs were gained by all three orders. Fifteen original solves were lost by every order. None of the adapted hosts or donors solved all four versions of a final program. [Results by family and order](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Exact identities of gained and lost solves](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-ledger.json)

Reverting the only trained component must recover the frozen model, and the live forward pass reproduced its scores exactly. A more discriminating intervention asks whether the change in that component is specific to the requested behavior. Let the learned change at the scored token be the trained module's output minus the pretrained module's output on the same recipient. We retain the original branch, attention residual, normalization and output head of that recipient. We exchange only this learned change among the four different requests for the same program. Every request receives each of the three other requests' changes once. An identity exchange checks the implementation.

The intact donor averaged 99.33 final solves out of 384. The three nonidentity exchanges averaged 99.11. The intact-minus-exchanged difference was +0.06 percentage points [−1.50, +1.88]. The interval includes small gains and losses. The individual final donor fits chose the same indentation for all four requests in 79, 87 and 86 of the 96 quartets. These results support an interpretation in which much of the apparent gain is a change in indentation preference. The intervention specifically exchanges within-program changes, so it preserves components common to the program and cannot locate all information used by the network. [Full-path exchange scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-live-exchange.npz) · [Paired counterfactual prompts](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-problems.json)

## Reproduction and decision

We restored each selected checkpoint in a second Studio run, verified its SHA-256, reproduced the native and adapted logits, executed all visible and hidden cases on the released qualification and test prompts, and performed the exchanges inside the live model. No identity-exchange selection differed from its intact counterpart. All live exchange selections also agreed with the separately computed cached-feature implementation. The public release includes all six checkpoint files in two model-specific archives, with upstream attribution and licenses. [Model checkpoints](https://github.com/buildngrowsv/routed-expert-splice/releases/tag/specialist-indent-v1) · [Archive checksums](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-archives.json) · [Numerical replay](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

On Apple Silicon use the repository's pinned checkpoints and MLX environment. Run the commands below from the repository root. To replay the published fits without training, place the six safetensors files into cache/specialist-v1 and start with the replay script. The figure needs Matplotlib.

```sh
python specialist/experiment.py
python specialist/replay.py
python specialist/report.py
python specialist/figure.py
```

The measured result concerns specialization inside the smaller coding model. No host transplant ran after qualification failed. The contrast leaves one concrete ambiguity: changing the donor's feed-forward module alone may be insufficient to select the right evidence across the prompt. A matched full-final-block donor and selective restoration of its attention and feed-forward weights can distinguish where any improved skill resides before another transplant is warranted.