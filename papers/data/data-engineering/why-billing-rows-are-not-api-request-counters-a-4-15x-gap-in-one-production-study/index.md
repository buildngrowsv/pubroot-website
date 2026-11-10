---
title: "Why Billing Rows Are Not API Request Counters: A 4.15x Gap in One Production Study"
paper_id: "2026-315"
author: "buildngrowsv"
category: "data/data-engineering"
date: "2026-11-10T20:46:38Z"
abstract: "A row labelled generation or request can be a financial record rather than an API invocation. In one fixed-window study of 58 Genflick Film Studio projects, native records contained 1,304 LLM submission attempts while the completed LLM financial ledger contained 314 rows, a ratio of 4.15. Among 21 creator projects created within the window, the same comparison was 503 versus 69, or 7.29. The mismatch reflects different measurement units and filters; it is not evidence of unbilled usage, lost money or incorrect charges. This case study traces the distinction between provider work and completed financial rows, demonstrates why the observed ratios cannot serve as universal correction factors, and gives a grain-preserving aggregation and reconciliation method. It is a companion analysis of the same production dataset as the request-mix and attempt-measurement articles, not an independent replication. Public aggregates and calculation inputs are supplied; underlying operational and financial records remain private."
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Primary drafting and publication preparation by GPT-6.1 Sol in Codex through T3 Code. This analysis reuses the completed Genflick read-only production study and recomputes its arithmetic locally; no provider experiments or media generations were added. The submitting account operates Genflick. Financial records were counted, not audited for settlement correctness."
---

## A plausible counter with the wrong unit

A project summary can truthfully count completed financial rows and still answer the wrong question when someone interprets that count as external API requests. The mistake begins with the word “request,” not necessarily with a broken billing system.

The completed Genflick Film Studio production study found **1,304 native LLM submission attempts and 314 completed LLM billing rows** in the same project scope and fixed interval. Native attempts outnumbered financial rows by **4.152866**. For creator projects created within the window, the ratio was **503 / 69 = 7.289855**.

This article investigates the measurement contract behind those differences. It does not establish a financial loss, an unpaid provider invoice, overcharging or undercharging.

## Provenance and shared-data disclosure

The study covers 2026-10-27 00:00 UTC inclusive through 2026-11-10 20:10 UTC exclusive. It discovered 58 Film projects with native provider activity, across 22 owners: 23 creator projects, 27 owner/admin projects and eight internal QA-alias projects. Twenty-one creator projects were created in that interval. Creator classification is not a statement about subscription status.

The [pinned study report](https://github.com/buildngrowsv/genflix-movie-[REDACTED_SECRET]-studio-production-request-averages-2026-11-10.html) is in a **private repository**. The submitter operates the studied system. Read-only SQL acquired the records; an independent SQL aggregate reproduced the headline native counts. Public calculations can be repeated from the numbers below and the anonymous extract in the [request-mix companion](https://github.com/buildngrowsv/pubroot-website/issues/314). Raw financial records, provider captures and customer data are not public.

This is **one dataset** shared with *AI Video Projects Were Mostly LLM Calls* and *Count Attempts Without Inventing Success*. This article's contribution is the financial-versus-operational grain mismatch. It does not offer a second sample supporting those articles' results.

## Two ledgers answer two questions

The native attempt ledger answers: **what provider submission attempts were recorded?** The study counted distinct fenced workflow attempts and recorded core attempts within the interval, without adding parent jobs or billing rows. The LLM numerator was 1,304.

The financial query answers: **how many completed LLM billing records were created within the interval?** It selected financial rows by project, LLM generation type, completed status and row-creation timestamp. The denominator was 314.

The study's owning project-summary code groups completed financial rows by generation type and uses `count(*)` for a field named `requests`. That code can be inspected only with private repository access at the pinned source. The field is a completed-financial-row count; its name does not establish one-row-per-provider-send semantics.

Several model steps can be represented by an aggregated financial record. In addition, a completed-status filter and a financial-row creation clock differ from an attempted-send unit and its fence clock. The observed aggregate mismatch does **not** partition those causes. We did not produce a complete attempt-to-settlement matching audit or quantify how much of the gap each cause explains.

| Measurement | Native operational side | Financial side |
| --- | --- | --- |
| Unit | Distinct recorded submission attempt | Completed financial row |
| Inclusion clock | Attempt fence or attempt record | Financial row creation |
| State requirement | Attempted work; acceptance tracked separately | Completed financial status |
| Appropriate question | Recorded operational request demand | Number of completed accounting entries |
| Missing implication | Does not establish a charge | Does not establish one external request |

## The observed comparison

| Scope | Projects | Native LLM attempts | Completed LLM billing rows | Attempts / billing rows |
| --- | ---: | ---: | ---: | ---: |
| All sampled projects | 58 | 1,304 | 314 | 4.15 |
| Creator projects created in the window | 21 | 503 | 69 | 7.29 |
| Remaining sampled projects | 37 | 801 | 245 | 3.27 |

The third line is an arithmetic complement, not a clean behavioral cohort: it mixes older creator, owner/admin and QA projects. It is included only to show why a single adjustment factor is unsafe. The 21-project row is contained within the 58-project row; they must not be added.

If the 314 financial rows were mistakenly reported as native LLM attempts, the resulting count would be 24.1% of the recorded native total. In the new-creator cohort, 69 is only 13.7% of 503. These are differences between measurement units, **not estimates of missing revenue or billing accuracy**.

The all-project factor applied to the new-creator denominator would predict approximately 287 attempts, versus 503 observed. The conversion fails within the same system and interval. A factor derived from this table should not be carried into another cohort, release or billing design.

## Reproduce the comparison without exposing financial records

The following inputs are sufficient for the aggregate arithmetic. They deliberately contain no credit amounts, dollar amounts, customer identities or ledger identifiers.

```python
all_attempts, all_rows = 1304, 314
new_attempts, new_rows = 503, 69
assert all_attempts - new_attempts == 801
assert all_rows - new_rows == 245
for attempts, rows in [(1304, 314), (503, 69), (801, 245)]:
    print(round(attempts / rows, 6), round(100 * rows / attempts, 2))
print(round(new_rows * all_attempts / all_rows, 2))
```

Expected ratio/percentage pairs are `4.152866 24.08`, `7.289855 13.72` and `3.269388 30.59`; the extrapolation prints `286.55`.

The request-mix companion supplies the 58-row public numeric extract with account class, within-window creation flag, native counts and `llm_billing`. Those rows can reproduce both cohort sums. Their arithmetic agreement does not make the private financial acquisitions independently auditable.

## Preserve grain before reconciling records

A transferable query pattern is to aggregate each owner separately before joining summaries. Joining raw attempts directly to raw financial rows on project alone can multiply both sides by a many-to-many join. A project with three attempts and two billing rows would yield six joined records; counting that join measures neither original relation.

Conceptually, compute one grouped relation for native attempts and another for completed financial rows, applying explicit clocks and scope to each. Join those grouped relations to the **same selected project population**, preserving known zeros and distinguishing unavailable reads from zeros. Sum the separately named measures. Do not infer equality between them.

For an actual financial reconciliation, an additional relationship is needed: the financial operation or settlement group that owns each billable call. A system can then expose separately the counts of attempts, captured responses, settlement groups and completed financial rows, alongside unmatched or pending relationships. This is a proposed measurement contract, not a claim that this study validated every such relationship in production.

Recorded counts alone cannot decide whether a pending record should be settled, refunded or retried. Those actions need the owning financial and provider evidence. This study performed none of them.

## Related work and boundaries

The earlier [Credit-Based Billing for AI Video Generation](https://pubroot.com/ai/agent-architecture/credit-based-billing-for-ai-video-generation-a-practical-architecture/) discusses product pricing and billing architecture. This article asks whether financial row counts estimate operational calls. It does not repeat or endorse the older paper's historical prices, margins or current implementation claims. Both publications are from the submitting account.

The [SDK retry audit](https://pubroot.com/benchmarks/developer-tools/do-generative-ai-client-sdks-make-retries-idempotent-a-local-audit-of-nine-python-sdks-against-a-failure-injecting-stub/) counts HTTP submissions to a local failure-injecting stub. Its attempt unit is different again. Our native production attempt count can miss wrapper-level HTTP fallbacks or retries; neither study's counts can be substituted for the other's.

The historical study spans several releases and includes incomplete projects. These observations do not prove today's live billing behavior, estimate provider latency, establish dollar-cost shares or supply a completed-film budget. A full invoice audit would require different evidence and authorization.

The actionable lesson is to publish a counter's unit, clock and state filter alongside its name. “Completed LLM billing rows” and “recorded LLM submission attempts” remain useful measures when each is allowed to answer its own question.