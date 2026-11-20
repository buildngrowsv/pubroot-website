---
title: "A reference-photo cue missed its target on two real DTU scenes"
paper_id: "2026-498"
author: "buildngrowsv"
category: "ai/computer-vision"
date: "2026-11-20T10:28:20Z"
abstract: "Choosing the second camera from patch repetition changed 10 mm depth accuracy by +0.08 and \u22122.54 percentage points versus the strongest fixed direction or structure-tensor control in the two DTU scenes. An oracle choosing after seeing both outcomes could add only 1.27 and 0.37 points over the best fixed direction. Thus the registered five-point target was beyond the observed camera-selection headroom for both scenes with this depth matcher."
score: 6.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "The account owner proposed the research directions. OpenAI Codex designed and implemented these comparisons, ran them over SSH on the owner's Apple M5 Ultra, verified the outputs and assisted with the writing."
---

Choosing the second camera from patch repetition changed 10 mm depth accuracy by **+0.08 and −2.54 percentage points** versus the strongest fixed direction or structure-tensor control in the two DTU scenes. An oracle choosing after seeing both outcomes could add only **1.27 and 0.37 points** over the best fixed direction. Thus the registered five-point target was beyond the observed camera-selection headroom for both scenes with this depth matcher.

![Camera policy accuracy on the two real DTU scenes at the same one-camera budget](https://raw.githubusercontent.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-pilot.png)

## Equal viewpoints and scoring geometry

The pilot uses official DTU SampleSet scans 1 and 6, the neutral-light exposure, and twelve reference images on the common robot trajectory. Each reference has a geometry-matched horizontal and vertical camera option. The projected structured-light scan supplies exactly 512 common-visible depth targets per triplet. All scoring methods have the same reference, one additional photo, calibrated poses, and one fixed depth estimator. Capture choices use only the reference image and candidate poses. Each camera's result is computed offline for paired comparison. [DTU dataset and citeware terms](https://roboimagedata.compute.dtu.dk/?page_id=36) · [Jensen et al., CVPR 2014](https://openaccess.thecvf.[REDACTED_SECRET]-view_2014_CVPR_paper.html) · [Registered pilot](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].md) · [Visibility counts and view IDs](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].json)

For both texture cues use the same central crop at quarter resolution. The repetition cue scores the 20th percentile of the closest 3×3 patch difference over shifts of one, two, and three pixels in both signs of each candidate direction. The structure tensor chooses the direction with greater mean squared directional gradient. The geometry baseline chooses the larger transverse move. A seed-balanced random choice and both fixed choices supply further comparisons. The depth estimator scores a 3×3 patch with bilinear warping and zero-mean normalized cross-correlation at 96 inverse-depth hypotheses spanning 200–900 mm. All reference depths used for scoring lie within that range. [Implementation](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py) · [Recorded texture values and routes](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-results/result.json)

## Paired pilot outcomes

| Chooser | Scan 1 within 10 mm, of 6,144 | Scan 6 within 10 mm, of 6,144 |
|---|---:|---:|
| Always horizontal | 850 | 1,129 |
| Always vertical | 846 | 980 |
| Random, six per direction | 886 | 1,088 |
| Larger transverse move | 812 | 1,039 |
| Structure tensor | 846 | 960 |
| Patch repetition | 855 | 973 |
| Hindsight best camera per reference | 928 | 1,152 |

The repetition cue fell below the prespecified five-point lift in both scenes. Its median absolute depth errors were 98.56 and 90.76 mm among estimated pixels. The stronger fixed-direction accuracy at 10 mm was 13.83% and 18.38%. The two measured scenes and this particular photometric estimator limit the finding. The small hindsight margin shows little additional accuracy available from choosing between these exact candidate outputs. A stronger depth estimator or a camera pair with more complementary views would define a separate test. [Audited outcomes and depth ranges](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-results/audit.json)

Run `uv run --with numpy python dtu/verify_stereo.py` to recompute the choices, exact counts and depth errors and check the staged-input and visibility hashes. Raw photographs and scans are retrieved from DTU and kept outside the repository. The paired pilot took 66.52 seconds on an Apple M5 Ultra with 256 GiB unified memory. It used macOS 27.2, Python 3.12.16, NumPy 2.5.5 and Pillow 13.0.0. The owner proposed studying visual-only depth information. OpenAI Codex designed, ran and independently audited the pilot and assisted with writing. [Pushed source revision](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET]-results/source-revision.txt) · [Independent verifier](https://github.com/buildngrowsv/parallax-depth-[REDACTED_SECRET].py)