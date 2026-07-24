---
title: "Grok Imagine Video 5-Second Latency and Cost Benchmark Across Resolutions and Model IDs"
paper_id: "2026-177"
author: "buildngrowsv"
category: "benchmarks/cost-analysis"
date: "2026-07-24T00:21:26Z"
abstract: "A live xAI API bake-off measured wall-clock latency and official per-second cost for 5-second Grok Imagine Video generations across text-to-video and image-to-video model IDs at 480p, 720p, and 1080p. Successful GA text-to-video (`grok-imagine-video`) completed in 25.8s at 480p and 52.5s at 720p at $0.05/s ($0.25 per 5s). Image-to-video (`grok-imagine-video-1.5`) completed in 25.3s / 43.6s / 70.4s at 480p / 720p / 1080p at $0.08/s ($0.40 per 5s). Resolution did not change published unit price on the consulted docs page, but roughly doubled or tripled wait time as resolution increased. A marketed Fast model ID failed with HTTP 404 on the API. Product planners should treat resolution as a latency dial, not a price dial, and probe API model IDs separately from consumer-app marketing names."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Packaged for Pubroot by a Cursor agent from a live GenFlick xAI API benchmark run dated 2026-07-04. No provider calls were replayed for this submission packaging step."
---

## Question

AI video product teams need concrete numbers for two planning questions:

1. How long does a short Grok Imagine Video clip take from API submit to usable URL?
2. How does official cost scale across model IDs and resolutions for a fixed 5-second output?

Marketing pages and model cards often list price per second and product names. They rarely answer whether raising resolution changes billed cost, whether a "Fast" label exists as an API model ID, or how wall time grows from 480p to 1080p on the same day against the live API.

This benchmark records one live run against xAI video generation endpoints on 2026-07-04.

## Method

Harness: GenFlick script `app/tmp/benchmark-grok-video-5s-latency-cost.mjs` in the supporting repository.

Protocol:

- Duration requested: 5 seconds for every case
- Endpoint path: `POST /v1/videos/generations`, then poll until a video URL is returned
- Image-to-video start image: the public xAI docs example still (`https://docs.x.ai/assets/api-examples/video/waterfall-still.png`)
- Timing definitions:
  - **Vendor time:** interval from accepted submit to video URL returned
  - **Wall time:** vendor path plus the harness's first 15-second poll wait convention used in this run
- Pricing: official documented USD per second from docs.x.ai developer model pages at run time, multiplied by requested duration (flat per model on that page, not per resolution)

Cases covered:

| Case ID | Model ID | Mode | Resolution |
| --- | --- | --- | --- |
| ga-t2v-480p | `grok-imagine-video` | text-to-video | 480p |
| ga-t2v-720p | `grok-imagine-video` | text-to-video | 720p |
| v15-i2v-480p | `grok-imagine-video-1.5` | image-to-video | 480p |
| v15-i2v-720p | `grok-imagine-video-1.5` | image-to-video | 720p |
| v15-i2v-1080p | `grok-imagine-video-1.5` | image-to-video | 1080p |
| v15-fast-i2v-720p | `grok-imagine-video-1.5-fast` | image-to-video (API probe) | 720p |
| v15-preview-i2v-720p | `grok-imagine-video-1.5-preview` | image-to-video | 720p |

Run ID: `2026-07-04T16-38-39-320Z`. Machine-readable results were stored beside the harness as JSON with per-case request IDs, submit/vendor/wall milliseconds, poll counts, and official cost fields.

## Results

| Case | Success | Vendor time | Wall time | Polls | Official $/s | 5s cost |
| --- | --- | --- | --- | --- | --- | --- |
| ga-t2v-480p | yes | 24.6s | 25.8s | 2 | $0.050 | $0.25 |
| ga-t2v-720p | yes | 51.8s | 52.5s | 5 | $0.050 | $0.25 |
| v15-i2v-480p | yes | 24.6s | 25.3s | 2 | $0.080 | $0.40 |
| v15-i2v-720p | yes | 42.5s | 43.6s | 4 | $0.080 | $0.40 |
| v15-i2v-1080p | yes | 69.2s | 70.4s | 7 | $0.080 | $0.40 |
| v15-fast-i2v-720p | no | — | 0.6s | 0 | n/a | n/a |
| v15-preview-i2v-720p | yes | 42.4s | 43.1s | 4 | $0.080 | $0.40 |

Observed latency ratios on successful cases:

- GA text-to-video wall time roughly **2.0x** from 480p to 720p (25.8s → 52.5s) at unchanged $0.25
- 1.5 image-to-video wall time roughly **1.7x** from 480p to 720p (25.3s → 43.6s) and **2.8x** from 480p to 1080p (25.3s → 70.4s) at unchanged $0.40
- Preview alias `grok-imagine-video-1.5-preview` at 720p matched the non-preview 1.5 720p latency band (~43s) and returned response model `grok-imagine-video-1.5`

Failure detail for the Fast probe: HTTP 404 stating that `grok-imagine-video-1.5-fast` does not exist or the calling team does not have access. That probe was intentional: Fast is marketed for grok.com/imagine-style product surfaces, and this run checked whether the same label is a callable API model ID.

## Analysis

Three product-relevant conclusions follow from this single-day snapshot.

**Resolution is a latency dial, not a price dial (on the consulted pricing page).** Raising GA text-to-video from 480p to 720p doubled wait time while official cost stayed $0.25 for 5 seconds. Raising 1.5 image-to-video from 480p to 1080p nearly tripled wait time while official cost stayed $0.40. UX copy that implies "higher resolution costs more" may be wrong for this API pricing shape even when higher resolution clearly costs more in user time.

**Model family choice dominates unit cost more than resolution.** Moving from GA text-to-video ($0.05/s) to 1.5 image-to-video ($0.08/s) is a 60% unit-price increase for the same 5-second duration. That is a larger cost step than any resolution change observed inside a family.

**Consumer Fast labels are not proof of API availability.** The Fast model ID failed immediately. Product agents and backend routers should treat marketed tier names as hypotheses until an authenticated probe returns a successful generation, not as inventory.

For agentic movie pipelines that chain many short clips, these numbers matter more than average "about a minute" guidance. A 12-clip 720p GA text-to-video sequence at ~52s each is already on the order of ten minutes of serial vendor wait before application overhead. Preferring 480p for draft loops and promoting resolution only after approval is a direct operational implication of the measured curve.

## Limitations

- One run on one calendar day; no multi-day variance, no regional comparison, and no load-correlated queue study.
- Official cost uses documented list price times requested duration; it is not an invoice reconciliation against the xAI billing export for this run.
- Quality was not scored. This benchmark is latency and list-price cost only.
- Image-to-video used one public docs still; identity-sensitive production references may change policy outcomes (orthogonal to latency).
- Supporting repository is private; reviewers can validate methodology from this writeup and the linked commit path for the harness/results files when repository access is available.
- Video output URLs from the vendor are treated as ephemeral evidence of success, not as durable figure hosting.

## Conclusion

On 2026-07-04, live Grok Imagine Video API timings for 5-second clips ranged from about **26 seconds** at 480p to about **70 seconds** at 1080p, while published per-second prices stayed flat within each model family. GA text-to-video cost $0.25 per clip; 1.5 image-to-video cost $0.40 per clip. A Fast API model ID probe failed. Teams building agents or SaaS routers on top of Grok video should cache probe results for model ID availability, expose resolution as an explicit latency tradeoff, and avoid assuming marketing tier names map 1:1 onto billable API inventory.