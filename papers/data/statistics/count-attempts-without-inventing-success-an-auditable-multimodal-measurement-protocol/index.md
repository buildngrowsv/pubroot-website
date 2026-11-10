---
title: "Count Attempts Without Inventing Success: An Auditable Multimodal Measurement Protocol"
paper_id: "2026-316"
author: "buildngrowsv"
category: "data/statistics"
date: "2026-11-10T20:47:56Z"
abstract: "Multimodal systems expose intents, jobs, submission fences, captures, outputs, selected takes and billing records. Counting any one as another can invent demand or success. We derive a measurement protocol from a fixed-window study of 58 Genflick Film Studio projects. Its 1,808 recorded native attempts comprised 1,740 with a recorded capture, two rejected attempts and 66 with uncertain acceptance; 88 unfenced workflow attempts and one generation without an attempt were excluded. Attempt ordinals never exceeded one, yet additional submission slots on existing jobs exposed repeated work. Separately, sampled telemetry covered only four projects and could not estimate the total. The protocol separates immutable attempt identities from logical targets, reports unresolved acceptance explicitly, checks source-population coverage before applying sampling weights, and distinguishes saved outputs from completed exports. This is a methodological companion to two analyses of the same dataset, not new independent evidence. Public accounting identities reproduce the arithmetic; private source records limit independent empirical verification."
score: 7.9
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Primary drafting and publication preparation by GPT-6.1 Sol in Codex through T3 Code, using the completed Genflick read-only production study, SQL verification and Python analysis. No provider work was replayed. Protocol recommendations are distinguished from measured results. The submitting account operates Genflick; underlying operational records remain private."
---

## The measurement problem

“How many requests did this project make?” has several plausible answers: authoring intentions, durable jobs, provider attempts, HTTP sends, returned results, saved media or charged operations. A single counter cannot safely collapse these units.

This case study develops an auditable reporting protocol from one production measurement exercise. “Auditable” means the reported units, inclusion rules, arithmetic and missing evidence are explicit. It does **not** imply that public readers can inspect the private source records or prove a complete HTTP census.

## Dataset, provenance and overlap

The Genflick Film Studio study selected 58 projects with native provider activity between **2026-10-27 00:00 UTC inclusive and 2026-11-10 20:10 UTC exclusive**. The native clip-metadata snapshot followed at 2026-11-10 20:13:35 UTC. The sample included 23 creator projects, 27 owner/admin projects and eight internal QA-alias projects, spanning 22 owners.

Its [source report and SQL methodology](https://github.com/buildngrowsv/genflix-movie-[REDACTED_SECRET]-studio-production-request-averages-2026-11-10.html) are in a **private repository**. Acquisitions were read-only. An independent production SQL aggregate reproduced key totals. Capture metadata was read; the private capture bytes were not downloaded and independently revalidated.

The submitting account operates Genflick. This is the **same dataset** used in the [request-mix companion](https://github.com/buildngrowsv/pubroot-website/issues/314) and [billing-grain companion](https://github.com/buildngrowsv/pubroot-website/issues/315). Their questions are request composition and financial-row granularity. The contribution here is the measurement protocol and its failure checks. These articles do not constitute three replications.

## Separate the units before counting

| Unit | What one item represents | What it does not establish |
| --- | --- | --- |
| Intent or target | Work a creator wants in a logical slot | Any provider submission |
| Job | Durable orchestration work | Exactly one external call |
| Native attempt | Immutable recorded submission attempt | Complete wire-level traffic or provider acceptance |
| HTTP send | One request crossing a specified transport boundary | Successful processing or usable output |
| Capture | A recorded response artifact or response evidence | Saved, selected or exported media |
| Output | A saved result record | Selection into a film or a new call on this project |
| Selected take | Current chosen media for a clip | A completed export |
| Billing row | A financial accounting record | One provider attempt or one successful output |

The units can be related, but the relationships need evidence. One job may make multiple calls. One call may contain a multi-panel image. An imported take may contribute no new provider call on the importing project. A later selection change can alter the current clip state without changing historical provider demand.

The measured unit in this study was **recorded native submission attempts**, not literal HTTP requests. Wrapper fallbacks, polling, media transfers, internal rendering and storage traffic were not completely represented.

## Inclusion rules and uncertainty must travel together

Workflow attempts were counted once per immutable identity when their submission fence fell inside the interval. Eighty-eight workflow attempt rows without that fence were excluded. Core work contributed 14 recorded attempts; one generation row without an attempt was excluded. The two owning relations were disjoint in this study. Financial rows, outputs and parent jobs were not added to the attempt total.

| Included attempt evidence | Count | Interpretation |
| --- | ---: | --- |
| Recorded capture | 1,740 | Capture metadata exists; no general media-success claim |
| Rejected | 2 | Counted attempted work with recorded rejection |
| Uncertain acceptance | 66 | Counted attempted work; acceptance unresolved |
| Total | 1,808 | Sum of the three disjoint evidence classes |

The 66 uncertain attempts were all images: 52 fenced workflow attempts with unresolved or abandoned acceptance and 14 core attempts whose receipt status was unknown. The fence or record precedes the send, so an abrupt failure in between can leave a counted attempt without proof that a provider received it. Removing those records would hide uncertain attempted work; treating them as accepted generations would invent success.

The correct public statement is “1,808 recorded attempts, including 66 with uncertain acceptance.” The study cannot resolve those 66 into actual provider sends, generated images or charges. The 1,740 captured records also must not be described as 1,740 successful media outputs: most measured work was LLM activity, and capture is not apply or export.

## An ordinal is not a repeat-work detector

Across the sample there were **106 video attempts for 80 distinct project/clip targets**, or 1.325 attempts per target. This mixes deliberate new takes and repeated work. A denominator of targets describes work intensity, not an automatic retry probability.

No counted attempt had a recorded ordinal above one. Nevertheless, ten additional submission slots appeared on jobs already counted, eight explicitly marked as media resends. The ledger could represent a new call slot with its own first attempt. Filtering only for `ordinal > 1` would therefore report no repeats while overlooking observed additional submissions.

These are overlapping descriptions of work, not additive counts: resend slots are already represented in attempt totals. The study does not assign every excess video attempt to retry, regeneration or user revision. A causal retry rate would require explicit reason and lineage, plus a clearly defined eligible population.

This illustrates a general review question: **what creates a new identity at each layer?** Inspect that ownership contract before choosing a deduplication key or interpreting an ordinal.

## Weighting stored telemetry cannot repair missing population coverage

The same study queried provider-start telemetry over the fixed interval and project scope. It returned **62 stored rows**, sampling-weighted to **72**, covering only **four of the 58 projects**. Sampling intervals reached two. Start and finish events were not added together.

Those weighted rows were not used to estimate total provider requests. A sampling weight describes the event's sampling process; this study had no evidence that it also corrected absent instrumentation or missing project coverage. Applying weights to an incomplete source population would produce a more precise-looking answer without establishing the intended denominator.

This is a concrete coverage failure in the observed query, not a general evaluation of the telemetry product. Nor can the ratio `72 / 1808` be called a known capture probability: the numerator is sampled event evidence, and the denominator is a different native-attempt unit with its own uncertainty.

A defensible estimator would first require an event-emission contract for every relevant execution path, evidence of population coverage, known inclusion probabilities and transport-unit alignment. These were not established retrospectively. The honest outcome was to decline the HTTP-total estimate.

## Outputs and lifecycle states require separate accounting

Of the 106 video submissions, the study observed 100 completed jobs, three failed jobs and three cancelled jobs. Separately, 100 video-output rows were saved within the interval. The matching number 100 does not prove a one-to-one correspondence: job status and output creation have different owners and clocks, and this report does not assert a bijection.

Current authored target durations were available for all 517 clips. Measured final-export runtimes were not. Some projects had selected video covering all current clips, but that does not establish export completion. Copied or imported media, later edits and changes of selection further separate a current workspace from historical request activity.

The window also spans multiple releases. It cannot serve as a stable success baseline for the newly observed core-generation release. In particular, the 14 counted core image attempts had uncertain acceptance, and the snapshot established no confirmed delivered core images. That is an evidence boundary rather than a measured failure rate for the release.

## Reproduce the accounting checks

These public checks require Python 3 only and contain no operational identifiers. They reproduce accounting arithmetic, not source acquisition or lifecycle matching.

```python
assert 1740 + 2 + 66 == 1808
assert 52 + 14 == 66
assert sum([1304, 364, 106, 4, 22, 8]) == 1808
assert 100 + 3 + 3 == 106
assert 106 / 80 == 1.325
assert 8 <= 10  # resend-labelled slots are part of additional slots
```

The companion public numeric extract supports project-level totals and cohort arithmetic. It does not contain the attempt identities, acceptance proofs or parent/output links needed to independently audit deduplication and attribution. Private read-only SQL verification strengthens the original study's internal consistency but does not eliminate that public reproducibility limit.

## A portable reporting contract

For a comparable measurement, publish the following together:

1. The selected population, fixed interval and metadata snapshot, including older work and incomplete follow-up.
2. The identity counted, its owning record and the timestamp defining inclusion.
3. Excluded prepared work and any uninstrumented paths.
4. Separate capture, rejection and uncertain-acceptance classes without turning them into media-success labels.
5. Logical targets and repeat-work lineage separately from submission totals.
6. Output, selection, export and financial states as separately owned facts.
7. A coverage check before any sampling weights become a population estimate.
8. Reproducible public arithmetic and an explicit statement of inaccessible source evidence.

These are recommendations derived from the exercise. The study did not prove complete instrumentation of every provider HTTP path or a universal measurement standard.

## Related work and difference

[At-Most-Once Media Generation](https://pubroot.com/se/architecture/at-most-once-media-generation-for-browser-driven-ai-pipelines/) discusses preventing duplicate work. [Durable workflows versus a BFF](https://pubroot.com/se/architecture/durable-workflows-versus-a-bff-for-multi-minute-movie-production-on-cloudflare-workers/) discusses execution ownership and recovery. This article measures historical records; it does not claim those older designs eliminate duplicates or guarantee success in the new sample. Both are earlier publications by the submitting account.

The [nine-SDK retry audit](https://pubroot.com/benchmarks/developer-tools/do-generative-ai-client-sdks-make-retries-idempotent-a-local-audit-of-nine-python-sdks-against-a-failure-injecting-stub/) measures transport behavior against a controlled stub. Its wire-visible requests illustrate an evidence level our native ledgers do not provide. We reuse none of its observations in our production totals.

The methodological result is a refusal as well as a count: the study supports 1,808 recorded native attempts with explicit uncertainty, while leaving complete HTTP traffic, successful final-film demand and financial adjudication unresolved.