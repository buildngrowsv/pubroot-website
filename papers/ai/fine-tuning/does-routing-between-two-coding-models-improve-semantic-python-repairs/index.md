---
title: "Does routing between two coding models improve semantic Python repairs?"
paper_id: "2026-341"
author: "buildngrowsv"
category: "ai/fine-tuning"
date: "2026-11-19T20:33:23Z"
abstract: "Four Python repairs compiled and ran for every problem in this study. On a held-out set of 512 repairs the larger host solved 136 and the smaller coding donor solved 134. An oracle picking the right model answer when either was correct could solve 268. A confidence rule fitted on validation solved only 131 and called a second model for 467 problems. On a new panel, checking one ambiguous execution example and reranking the cheaper donor's candidates solved 248. Adding the larger model reduced that to 243. These results identify a large gap between complementary errors and the ability to choose the correct expert."
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the architectural research program. OpenAI Codex designed and implemented the comparisons, ran them over SSH on the owner's Apple M5 Ultra, analyzed the saved results and assisted with the writing."
---

Four Python repairs compiled and ran for every problem in this study. On a held-out set of 512 repairs the larger host solved **136** and the smaller coding donor solved **134**. An oracle picking the right model answer when either was correct could solve **268**. A confidence rule fitted on validation solved only **131** and called a second model for **467** problems. On a new panel, checking one ambiguous execution example and reranking the cheaper donor's candidates solved **248**. Adding the larger model reduced that to **243**. These results identify a large gap between complementary errors and the ability to choose the correct expert.

[Standalone models, routing, oracle and partial verification controls](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].png)

#### A semantic test for an expert transplant

The preceding surgery study reached a perfect-score ceiling on punctuation repairs: Python's parser could find the only compiling patch. Here all four candidate identifiers are valid. A generated function binds four inputs to variables, exchanges variables zero to three times, and returns one variable plus an integer offset. We leave the returned identifier blank. A contract in the suffix specifies which input field to return, and a public example gives a concrete result. The model fills the gap using Qwen's native infill markers. An independently computed reference grades every candidate on twelve hidden input vectors. Each vector has four distinct values, so exactly one identifier succeeds. Counterfactual pairs share a procedure but request different fields. This isolates whether the prediction changes with the requested output. The complete public example on this first panel also allows exhaustive checking of four candidates. [Earlier surgery](https://pubroot.com/ai/fine-tuning/do-newly-learned-python-repairs-depend-on-a-transplanted-coding-expert/) · [Decision plan](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

We compared the original pinned Qwen2.5-1.5B base host and Qwen2.5-Coder-0.5B base donor. The donor led 73 to 59 on 256 discovery problems and 114 to 84 on 384 validation problems. The validation advantage was 7.81 percentage points, paired interval [2.08, 13.54]. For a harder qualification control we trained only the native host's complete block 28, with the same 1,536-problem, 96-update Adam budget as the preceding study. Seed 101 selected the minimum validation loss among updates 0, 8, 32 and 96, using batch 16 and learning rate 0.00002. This host solved 96 validation problems. The donor's lead of 18/384 was 4.69 percentage points, below the five-point threshold set in advance. We stopped before fitting six transplant arms. On final test the standalone donor's lead over the original host reversed to −0.39 points [−5.27, 4.49]. The task-trained host solved 124. [Qualification record](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Selection history](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json)

#### Which model should answer?

On validation, the models' errors left enough room to try one routing policy. We took the host's margin between its two highest candidate scores. Below or at a validation-selected threshold of 0.9375, the cascade used the coding donor instead. Ties in validation accuracy favored fewer second calls. The held-out solve counts were 131 for the route, 134 for the donor and 136 for the host. Despite the large either-model oracle, this cascade was more expensive in forward-pass count and less accurate than either endpoint on this sample. The oracle uses hidden outcomes and cannot serve as a deployable router. Both members of a counterfactual pair were correct for 0/256 host pairs, 2/256 donor pairs and 3/256 routed pairs. These frozen models seldom produced two correct answers when the requested field changed. [Full scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].json) · [Training and routing implementation](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].py)

A second experiment asked whether execution could supply a better routing signal. We generated 256 fresh pairs, deliberately making two fields equal in the public case and keeping all concealed test values distinct. Exactly two candidates pass the visible check. We first ran the smaller model. If its preferred patch failed the public example, the cascade requested the larger host and used its highest-scoring example-consistent patch. We compared with choosing the cheaper donor's own highest-scoring consistent patch. The visible example is available at inference; no hidden tests were consulted to choose answers. [Follow-up plan](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET].md)

| Policy on the ambiguous-example panel | Solved out of 512 |
|---|---:|
| Unfiltered coding donor | 117 |
| Unfiltered native host | 135 |
| First identifier passing the visible example | 254 |
| Highest-scoring passing donor identifier | 248 |
| Highest-scoring passing host identifier | 259 |
| Donor first, host on a failed check | 243 |

The cascade requested 268 host forwards. Relative to reranking the donor alone, it gained 72 solves and lost 77. Its difference was −0.98 percentage points [−5.27, 3.32]. Filtering candidates using an incomplete example helped substantially. The learned rankings on the two survivors did not show a gain over the cheap first-consistent baseline. A full interpreter of these generated assignments and the explicit contract can solve the task exactly. This benchmark measures conditional model use under constrained decoding. It does not measure general program synthesis or internal mixture-of-experts routing. [Partial-test scores](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET]-test.json)

#### Research context, scope and reproduction

Infill pretraining supplies the two-sided code interface. Functional tests and the strength of test suites are established concerns in language-model code evaluation. The policy tested here routes between complete models, so forward-call counts are a simple resource proxy. Timing was not used to infer a latency improvement. All contrasts resample the base program and its two coupled repairs together using 5,000 bootstrap draws. Task qualification and the threshold use discovery and validation only. The second panel and its decision rule were specified after the first test was reported, using fresh program seeds. [Fill-in-the-middle pretraining](https://arxiv.org/abs/2207.14255) · [Qwen2.5-Coder technical report](https://arxiv.org/abs/2409.12186) · [EvalPlus](https://arxiv.org/abs/2305.01210)

Begin with the original repository's pinned checkpoints and preceding penultimate interfaces. On Apple Silicon run semantic/experiment.py followed by semantic/verifier.py from the repository root. The inexpensive independent check is `uv run --with numpy python semantic/verify.py`. It re-executes every candidate on twelve hidden cases for all 1,024 held-out programs and reproduces both routing decisions and solve counts. The release includes the source prompts, expected outputs, candidate logits and the selected native checkpoint's validation curve. The account owner proposed studying donor transplantation and expert routing. OpenAI Codex designed this follow-up, ran it over SSH on the owner's Mac Studio, verified the predictions and assisted with writing. [Pinned public evidence](https://github.com/buildngrowsv/routed-expert-[REDACTED_SECRET])