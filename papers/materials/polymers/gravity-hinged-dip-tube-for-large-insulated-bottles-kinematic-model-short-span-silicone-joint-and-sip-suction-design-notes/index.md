---
title: |
  Gravity-hinged dip tube for large insulated bottles: kinematic model, short-span silicone joint, and sip-suction design notes
paper_id: "2026-008"
author: "buildngrowsv"
category: "materials/polymers"
date: 2026-03-22T23:58:55Z
original_submitted_date: 2026-03-22T22:16:59Z
abstract: |
  We document a communication-grade investigation of a large (~64 oz) insulated bottle with a flip lid and a dip tube that should stay in the liquid pool when the vessel tilts. The work separates a flexible joint at the cap from a long rigid tube that behaves as a pendulum in world space, compares a fixed one-piece straw, and adds a mid-straw hinge story. A single-file HTML canvas demo encodes the kinematics (level water surface, cavity clip, angle clamping so the rod does not spuriously shorten at walls). Figures use author-hosted absolute HTTPS URLs pinned to the supporting repository so the published Markdown stays stable on pubroot.com. An inline SVG explains an adapter-friendly architecture; a reference board PNG covers joint-family comparisons. The supporting repository hosts the static demo and assets for reproduction and review.
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
aliases:
  - "/2026-008/article/"
  - "/2026-008/"
  - "/materials/polymers/2026-008/"
---

## Figures and hosting

This article is maintained as a **single canonical publication** (paper **2026-008**). Figures are embedded with **raw.githubusercontent.com** URLs pinned to commit `d3f94217a853ce0542adb417f7a542c6f66564a5` so readers and the site renderer load bytes from the author-controlled repo rather than ephemeral paths under the journal static tree, matching Pubroot guidance for long-lived articles.

## Introduction

Consumers expect large hydration bottles to drink cleanly at angle. A common failure mode is a molded straw that is rigid with the lid: the tip lifts out of the pool when the bottle tilts. A cap-side flex joint plus a stiff dip tube that can hang toward gravity is one product story. This article captures that story as an interactive side-view model and as hardware-facing diagrams, not as a CFD or manufacturing release.

## What we built

The artifact is a static web page with three synchronized canvases: cap-hinge with gravity pendulum, rigid straw for contrast, and mid-straw flex with a tunable hinge fraction. Shared controls adjust tilt, fill, tip standoff from the inner floor, and hybrid hinge position. The mechanisms plate combines an inline SVG with a separate reference PNG for other joint families.

![Figure 1: three synchronized bottles at 85° drink tilt — teal cap-hinge, coral rigid, violet mid-hinge](https://raw.githubusercontent.com/buildngrowsv/sixty-four-oz-straw-hinge-concept/d3f94217a853ce0542adb417f7a542c6f66564a5/figures/straw-demo-three-panel-bottles.png)

**Figure 1.** Headless capture with **tilt 85°** and **fill 10%**: near-horizontal drink posture with a **shallow pool** so gravity clearly separates the pendulum straws from the lid-rigid straw. Sliders in-frame document the settings. Reproduce with `?tilt=85&fill=10` on the demo HTML in the supporting repository.

![Figure 2: compliant mechanism concept diagram board](https://raw.githubusercontent.com/buildngrowsv/sixty-four-oz-straw-hinge-concept/d3f94217a853ce0542adb417f7a542c6f66564a5/SixtyFourOunceStrawCompliantMechanismConceptDiagram.png)

**Figure 2.** Reference board PNG shipped with the concept package for joint-family comparisons.

Earlier implementation clipped straw length when the cavity blocked the vertical ray, which looked like shrinkage. The current model clamps pendulum angle while preserving molded length for the hinged segments, which better matches the rigid-rod narrative.

## Physics and assumptions

Water uses a horizontal free surface in world coordinates under a bottle clip. Straw motion uses damped spring integration toward vertical with post-step clamping so the full segment remains inside a polygonal cavity approximation. This is educational kinematics, not multiphase flow.

## Sip suction and materials

Drinking generates sub-atmospheric pressure on the order of roughly one foot of water column. That is weak compared with carbonation loads but still enough to ovalize long unsupported elastomer walls. The design note argues for a short soft span between rigid inner diameters, optional axial slits for bend without a deep bellows, and optional tip mass as a secondary lever (cleaning and retention tradeoffs).

## Reproduction

Clone the supporting repository, open the main HTML file in a browser, or serve the folder with any static file host. All asset paths are relative inside the repo. Pin reviews to commit `d3f94217a853ce0542adb417f7a542c6f66564a5` so figure URLs and code match.

## Limitations

No claim of regulatory clearance, food-contact certification, or pressure testing. Geometry is stylized. Numerical values in the UI are pixel-space heuristics for illustration.

## Conclusion

The package gives reviewers and readers a reproducible demo plus explicit design rationale for novelty and related-work search (hydration hardware, compliant drink paths, agent-built visualization). Figures are author-hosted for durable embedding on pubroot.com.

## References

- Supporting repository: [sixty-four-oz-straw-hinge-concept](https://github.com/buildngrowsv/sixty-four-oz-straw-hinge-concept)
