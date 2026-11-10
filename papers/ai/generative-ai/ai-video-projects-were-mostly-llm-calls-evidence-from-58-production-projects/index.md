---
title: "AI Video Projects Were Mostly LLM Calls: Evidence from 58 Production Projects"
paper_id: "2026-314"
author: "buildngrowsv"
category: "ai/generative-ai"
date: "2026-11-10T20:45:28Z"
abstract: "What does an AI video project actually ask its providers to do? A fixed-window study of 58 Genflick Film Studio projects recorded 1,808 native provider submission attempts: 1,304 LLM, 364 image, 106 video and 34 audio-related attempts. LLM work represented 72.1% of this recorded count, with agent model steps contributing 1,070 calls. Among 21 creator projects created within the window, the mean was 28.14 attempts and the median 13; nineteen submitted no video. The two that submitted video averaged 131 attempts, an inadequate sample for a completed-film forecast. Carefully anonymized clip-count and duration examples show why authored size, generated targets and delivered films are different denominators. We release the 58-row numeric extract and arithmetic needed to reproduce the descriptive statistics, while keeping private operational records unavailable. Counts describe recorded attempts, including uncertain acceptance, rather than a complete HTTP census, spend shares or final-export demand."
score: 8.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Primary drafting and publication preparation by GPT-6.1 Sol in Codex through T3 Code. Evidence comes from the completed Genflick read-only production study, its SQL aggregates and Python analysis; publication preparation recomputed arithmetic locally and made no generation calls. No image model or new media generation was used. The submitter operates Genflick, the system studied."
---

## The question: what work surrounds the video?

An AI video product can spend many requests deciding, authoring and checking before it submits a video. We measured that surrounding work in Genflick Film Studio rather than estimating it from an ideal production recipe.

In this sample, **72.1% of recorded provider submission attempts were LLM work**. That describes request composition in one system and period. It does not establish that LLMs dominate money, latency or useful creative output.

This is a descriptive production case study, not a comparison of models or platforms. Its contribution is an observed request mix and a demonstration of how incomplete projects change the meaning of an average.

## One study, three separate questions

This article analyzes request composition and project denominators. Two companion analyses, titled *Why Billing Rows Are Not API Request Counters* and *Count Attempts Without Inventing Success*, use the **same study**, examining financial-record granularity and measurement validity respectively. They are not replications or independent datasets. Shared baseline numbers provide context; the underlying observations must only be counted once in any synthesis.

The study belongs to Genflick, whose operator is the submitting account. The [supporting report at the pinned commit](https://github.com/buildngrowsv/genflix-movie-[REDACTED_SECRET]-studio-production-request-averages-2026-11-10.html) is in a **private repository**. Readers cannot independently inspect its operational source records. The public numeric extract below permits arithmetic reproduction, not independent re-acquisition of production evidence.

## Population, interval and counting unit

The request interval was **2026-10-27 00:00 UTC inclusive to 2026-11-10 20:10 UTC exclusive**. Current native clip metadata was observed at 2026-11-10 20:13:35 UTC.

Discovery selected Film projects with workflow provider-call activity or core-generation activity in that interval. All 58 discovered projects were retained. They belonged to 22 distinct owners: 23 projects on creator accounts, 27 on owner/admin accounts and eight on internal QA aliases. These are **project counts**, not account counts or paid-subscription categories. Seven projects predated the window; 51 were created within it. This is an activity-selected population rather than a random sample of all signups.

The counted unit was one immutable native submission-attempt identity. Workflow attempts required a submission fence in the interval; core attempts required a recorded attempt in the interval. Eighty-eight unfenced workflow attempts and one core generation lacking an attempt were excluded. Jobs, outputs and billing rows were not added as extra requests. The acquisitions used read-only transactions; an independent production SQL aggregation reproduced the key totals.

A fence or attempt record precedes the send. Therefore this unit is weaker than wire-level HTTP evidence. Of 1,808 counted attempts, 1,740 had a recorded capture, two were rejected and 66 had uncertain acceptance. All 66 uncertain attempts were images. Capture metadata was observed; private capture bytes were not independently revalidated. Provider polling, wrapper fallbacks, downloads, uploads, internal rendering and storage traffic are not completely counted.

## Results: the recorded request mix

| Request class | Recorded attempts | Share of all attempts |
| --- | ---: | ---: |
| LLM | 1,304 | 72.1% |
| Image | 364 | 20.1% |
| Video | 106 | 5.9% |
| Voice synthesis | 4 | 0.2% |
| Transcription | 22 | 1.2% |
| Audio separation | 8 | 0.4% |
| Total | 1,808 | 100% before rounding |

The LLM work was itself heterogeneous:

| Native owning purpose | LLM calls |
| --- | ---: |
| Agent model steps | 1,070 |
| Clip-audio comparisons | 96 |
| Reply checks | 62 |
| Tool-owned calls | 38 |
| Workflow calls | 31 |
| Creator-authority checks | 6 |
| Grid critique | 1 |

Stored LLM identities were Muse Spark Contributor 1.3 (1,139 calls), GPT-6.1 Sol (96), GPT-6 Luna (46) and Kimi K3.1 Pro (23). This is an inventory of recorded configurations, not a quality, speed or price ranking.

Only one explicit pencil-guide conversion and one grid-critique call were identified. A previously constructed example of 47 media calls for a 12-clip project was a code-derived scenario, not this study's measured average. An available pipeline stage must not be multiplied across every clip unless execution evidence supports that assumption.

## The mean answers a narrower question than it first appears to

The 21 creator projects created within the window recorded **591 attempts**, for a mean of **28.142857**, median **13**, and P90 **47**. P90 uses linear interpolation at index `(n - 1) * 0.9`.

Nineteen of those 21 projects submitted no video. They recorded 329 attempts, or 17.32 per project. The two that submitted video recorded 262 attempts, or 131 per project. The latter subgroup is too small and too selectively defined to establish a typical completed-film average.

The two video-submitting projects alone contributed 44.3% of attempts in the new-creator cohort. This concentration explains why the mean is more than twice the median. It does not prove why those projects required more work: intent, project maturity, repeated takes and other differences are confounded.

Projects entered at different times and may continue after the cutoff. Others may never finish. These are observed-to-date counts subject to unequal follow-up and unfinished-work bias. Merely excluding projects without video would change the question to a selected subgroup, not repair it into a completed-film study. A completed-film estimate would require an explicit export-completion definition and follow-up of an entry cohort through that endpoint.

## Clip count and authored duration do not fix the denominator

The following are carefully anonymized examples. Labels are local to this public extract. Duration is the sum of current authored clip targets, **not measured final-export runtime**.

| Example | Account class | Current authored plan | Video-submitted targets | LLM | Image | Video | Other audio | Total |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | Creator | 1 clip, 5 seconds | 1 | 113 | 1 | 3 | 3 | 120 |
| B | Creator | 8 clips, 60 seconds | 4 | 124 | 11 | 7 | 0 | 142 |
| C | Creator | 12 clips, 96 seconds | 0 | 25 | 0 | 0 | 0 | 25 |
| D | Creator | 30 clips, 240 seconds | 0 | 31 | 1 | 0 | 0 | 32 |
| E | Owner/admin | 5 clips, 50 seconds | 5 | 81 | 19 | 5 | 0 | 105 |
| F | Owner/admin | 11 clips, 116 seconds | 11 | 75 | 26 | 11 | 0 | 112 |

Examples E and F had selected video takes covering every authored clip at the snapshot. That still does not prove a completed exported film. Example B had only three currently selected video clips. Saved, imported or copied takes also do not establish fresh provider calls on their destination project.

Across the full sample, 106 video attempts addressed 80 distinct project/clip targets: **1.325 attempts per generated target**. This combines new takes and repeated work. It is not an automatic retry rate.

## Public numeric extract and arithmetic reproduction

The CSV below is a fresh allowlisted export of numeric observations. It omits project identifiers and hashes, owner identities, customer names, per-project timestamps, prompts, transcripts, provider receipts and media URLs. Rows have no persistent public identity and are ordered by account class and numeric values. `new` indicates only whether the project was created within the fixed study window. `uncertain` counts attempts with unresolved acceptance; it is included in `total`. `llm_billing` is the count of completed LLM financial rows, included for the companion analysis. No ownership linkage between rows is released.

```csv
account,new,clips,authored_seconds,video_targets,llm,image,video,voice,transcription,separation,total,uncertain,llm_billing
creator,0,4,30.0,4,4,0,4,0,0,0,8,0,4
creator,0,61,610.144,34,46,44,52,0,0,8,150,2,46
creator,1,0,0,0,4,0,0,0,0,0,4,0,1
creator,1,0,0,0,43,4,0,0,0,0,47,0,3
creator,1,1,5.0,1,113,1,3,0,3,0,120,0,13
creator,1,1,8.0,0,0,1,0,0,0,0,1,0,0
creator,1,1,8.0,0,0,1,0,0,0,0,1,1,1
creator,1,1,8.0,0,4,1,0,0,0,0,5,0,1
creator,1,2,10.0,0,0,2,0,0,0,0,2,2,0
creator,1,3,30.0,0,23,1,0,0,0,0,24,1,2
creator,1,3,65.0,0,17,8,0,0,0,0,25,0,1
creator,1,4,8.0,0,33,11,0,0,0,0,44,0,3
creator,1,4,40.0,0,7,0,0,0,0,0,7,0,1
creator,1,5,38.0,0,10,1,0,0,0,0,11,0,1
creator,1,5,40.0,0,0,7,0,0,0,0,7,0,0
creator,1,7,30.0,0,14,20,0,0,0,0,34,2,2
creator,1,8,20.0,0,25,5,0,0,0,0,30,0,3
creator,1,8,60.0,4,124,11,7,0,0,0,142,4,25
creator,1,8,180.0,0,12,0,0,0,0,0,12,0,1
creator,1,12,96.0,0,25,0,0,0,0,0,25,0,3
creator,1,15,270.0,0,13,0,0,0,0,0,13,0,1
creator,1,19,216.0,0,5,0,0,0,0,0,5,0,1
creator,1,30,240.0,0,31,1,0,0,0,0,32,0,6
internal_alias,0,3,10.0,1,4,2,1,0,0,0,7,0,2
internal_alias,1,0,0,0,7,0,0,0,0,0,7,0,2
internal_alias,1,1,4.0,1,10,6,1,0,1,0,18,1,1
internal_alias,1,1,5.0,0,0,2,0,0,0,0,2,1,0
internal_alias,1,1,8.0,0,5,0,0,0,0,0,5,0,1
internal_alias,1,2,16.0,0,9,1,0,0,0,0,10,0,4
internal_alias,1,2,16.0,0,13,3,0,0,0,0,16,1,7
internal_alias,1,13,104.0,0,0,12,0,0,0,0,12,0,0
owner_admin,0,1,5.0,0,82,0,0,0,0,0,82,0,13
owner_admin,0,2,8.0,0,8,0,0,0,0,0,8,0,3
owner_admin,0,3,26.0,0,1,1,0,0,0,0,2,0,1
owner_admin,0,86,685.0,0,27,2,0,0,0,0,29,1,2
owner_admin,1,0,0,0,5,0,0,0,0,0,5,0,1
owner_admin,1,1,6.0,0,12,1,0,0,0,0,13,0,1
owner_admin,1,1,8.0,0,0,1,0,0,0,0,1,0,0
owner_admin,1,1,8.0,0,0,1,0,0,0,0,1,0,0
owner_admin,1,1,8.0,0,0,1,0,0,0,0,1,1,0
owner_admin,1,1,8.0,0,5,1,0,0,0,0,6,0,1
owner_admin,1,2,12.0,0,4,0,0,0,0,0,4,0,1
owner_admin,1,2,12.0,0,6,0,0,0,0,0,6,0,2
owner_admin,1,2,12.0,0,8,0,0,0,0,0,8,0,2
owner_admin,1,2,16.0,0,5,0,0,0,0,0,5,0,1
owner_admin,1,2,16.0,0,15,1,0,0,0,0,16,0,3
owner_admin,1,3,24.0,0,4,0,0,0,0,0,4,0,1
owner_admin,1,5,50.0,5,81,19,5,0,0,0,105,1,14
owner_admin,1,7,45.0,0,33,0,0,0,0,0,33,0,11
owner_admin,1,7,56.0,0,0,8,0,0,0,0,8,8,16
owner_admin,1,8,60.0,0,14,1,0,0,0,0,15,0,4
owner_admin,1,8,64.0,0,29,12,0,0,0,0,41,0,12
owner_admin,1,9,100.0,0,19,21,0,0,0,0,40,10,2
owner_admin,1,11,116.0,11,75,26,11,0,0,0,112,1,22
owner_admin,1,12,180.0,0,67,41,0,4,0,0,112,15,10
owner_admin,1,15,120.0,0,29,7,0,0,0,0,36,1,4
owner_admin,1,20,160.0,18,105,52,21,0,18,0,196,13,29
owner_admin,1,80,480.0,1,69,23,1,0,0,0,93,0,22
```

Save that block as `projects.csv` and run this Python 3 standard-library calculation. It reproduces arithmetic over the supplied extract; it cannot validate the original private acquisitions.

```python
import csv
from statistics import median

with open("projects.csv", newline="") as source:
    rows = [{k: v if k == "account" else float(v)
             for k, v in row.items()} for row in csv.DictReader(source)]
types = ["llm", "image", "video", "voice", "transcription", "separation"]
assert len(rows) == 58
assert all(sum(r[k] for k in types) == r["total"] for r in rows)
assert sum(r["total"] for r in rows) == 1808
assert sum(r["llm"] for r in rows) == 1304
assert sum(r["uncertain"] for r in rows) == 66
recent = [r for r in rows if r["account"] == "creator" and r["new"] == 1]
values = sorted(r["total"] for r in recent)
position = (len(values) - 1) * .9
lo = int(position)
hi = min(lo + 1, len(values) - 1)
p90 = values[lo] + (values[hi] - values[lo]) * (position - lo)
print(len(recent), sum(values), sum(values) / len(values), median(values), p90)
video = [r for r in recent if r["video"] > 0]
print(len(video), sum(r["total"] for r in video) / len(video))
```

Expected outputs are `21 591.0 28.142857142857142 13.0 47.0` and `2 131.0`.

## Related work and limits

[Phased Planner-Executor Architecture](https://pubroot.com/ai/agent-architecture/phased-planner-executor-architecture-for-multimodal-movie-generation-agents/) describes a proposed organization of creative-agent work. This article contributes later production counts, without claiming that the older proposed topology describes every sampled execution. [Grok Imagine Video 5-Second Latency and Cost Benchmark](https://pubroot.com/benchmarks/cost-analysis/grok-imagine-video-5-second-latency-and-cost-benchmark-across-resolutions-and-model-ids/) measures a different question with separate API experiments. Its latency and price observations are not imported into this study. Both are earlier publications from the submitting account.

These observations span historical releases. The live build observed at acquisition is not a stable success baseline for the newer core-generation release. The sample does not measure dollar-cost shares, provider latency, creative quality or completed-film demand. Owner/admin and QA work must remain separate from creator work. The averages weight projects equally; owners with several projects contribute several observations.

The useful operational result is specific: substantial LLM work accompanied a comparatively small number of video submissions, and an average over unfinished projects concealed a strongly uneven workload. Capacity estimates should preserve those stages and denominators before extrapolating beyond this window.