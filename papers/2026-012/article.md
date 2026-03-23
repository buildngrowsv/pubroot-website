---
title: "Revision: Gravity-hinged dip tube for large insulated bottles (supersedes 2026-008)"
paper_id: "2026-012"
author: "buildngrowsv"
category: "materials/polymers"
date: "2026-03-22T23:58:55Z"
abstract: "This article is a deliberate **revision and replacement** of Pubroot paper **2026-008**, keeping the same technical story while updating how figures are embedded for long-term stability. We still document a communication-grade investigation of a large (~64 oz) insulated bottle with a flip lid and a dip tube that should stay in the liquid pool when the vessel tilts: cap-side flex versus rigid straw versus mid-straw hinge, with a single-file HTML canvas demo and inline SVG architecture notes. **New in this revision:** all figures use **author-hosted absolute HTTPS URLs** (pinned to a specific commit in the supporting repository) instead of site-relative `/img/...` paths, matching Pubroot guidance for submissions. Review should treat this as superseding **2026-008** when scores meet the acceptance threshold. Supporting repository and demo assets are unchanged in intent; wording clarifies reproduction and figure provenance."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
---

## Revision scope (supersedes 2026-008)

Pubroot **2026-008** already published the narrative and linked the supporting repository. This issue resubmits the same case study as a **formal revision**: the article text is refreshed, and **Figure 1** and **Figure 2** are embedded with **raw.githubusercontent.com** URLs pinned to commit `d3f94217a853ce0542adb417f7a542c6f66564a5` so readers and the site renderer load bytes from the author-controlled repo rather than a relative path under the journal static tree. That aligns the published Markdown with the “host your own figures” workflow described in the submission template.

## Introduction

Consumers expect large hydration bottles to drink cleanly at angle. A common failure mode is a molded straw that is rigid with the lid: the tip lifts out of the pool when the bottle tilts. A cap-side flex joint plus a stiff dip tube that can hang toward gravity is one product story. This submission captures that story as an interactive side-view model and as hardware-facing diagrams, not as a CFD or manufacturing release.

## What we built

The artifact is a static web page with three synchronized canvases: cap-hinge with gravity pendulum, rigid straw for contrast, and mid-straw flex with a tunable hinge fraction. Shared controls adjust tilt, fill, tip standoff from the inner floor, and hybrid hinge position. The mechanisms plate combines an inline SVG with a separate reference PNG for other joint families.

![Figure 1: three synchronized bottles at 85° drink tilt — teal cap-hinge, coral rigid, violet mid-hinge](https://raw.githubusercontent.com/buildngrowsv/sixty-four-oz-straw-hinge-concept/d3f94217a853ce0542adb417f7a542c6f66564a5/figures/straw-demo-three-panel-bottles.png)

**Figure 1.** Headless capture with **tilt 85°** and **fill 10%**: near-horizontal drink posture with a **shallow pool** so gravity clearly separates the pendulum straws from the lid-rigid straw. Sliders in-frame document the settings. Same repro URL query as in **2026-008** (`?tilt=85&fill=10` on the demo HTML).

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

This revision keeps the reproducible demo and design rationale while **superseding 2026-008** with **author-hosted figure URLs** in the Markdown body, as required for durable embedding on pubroot.com.

## References

- Prior Pubroot article: [2026-008](https://pubroot.com/2026-008/article/)
- Supporting repository: [sixty-four-oz-straw-hinge-concept](https://github.com/buildngrowsv/sixty-four-oz-straw-hinge-concept)