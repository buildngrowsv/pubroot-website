---
title: |
  Gravity-hinged dip tube for large insulated bottles: kinematic model, short-span silicone joint, and sip-suction design notes
paper_id: "2026-008"
author: "buildngrowsv"
category: "materials/polymers"
date: 2026-03-22T22:16:59Z
abstract: |
  We document a communication-grade investigation of a large (~64 oz) insulated bottle with a flip lid and a dip tube that should stay in the liquid pool when the vessel tilts. The work separates a flexible joint at the cap from a long rigid tube that behaves as a pendulum in world space, compares a fixed one-piece straw, and adds a mid-straw hinge story. A single-file HTML canvas demo encodes the kinematics (level water surface, cavity clip, angle clamping so the rod does not spuriously shorten at walls). An inline SVG explains an adapter-friendly architecture: two cut rigid stubs inside a generous silicone sock with a modest gap between plastic ends to limit unsupported soft volume under typical sip suction (~1 foot of water head, order of magnitude). A markdown design note lists off-the-shelf prototyping paths. The supporting repository hosts the static demo and assets for reproduction and review.
score: 7.5
verdict: "ACCEPTED"
badge: "verified_open"
---

## Introduction

Consumers expect large hydration bottles to drink cleanly at angle. A common failure mode is a molded straw that is rigid with the lid: the tip lifts out of the pool when the bottle tilts. A cap-side flex joint plus a stiff dip tube that can hang toward gravity is one product story. This submission captures that story as an interactive side-view model and as hardware-facing diagrams, not as a CFD or manufacturing release.

## What we built

The artifact is a static web page with three synchronized canvases: cap-hinge with gravity pendulum, rigid straw for contrast, and mid-straw flex with a tunable hinge fraction. Shared controls adjust tilt, fill, tip standoff from the inner floor, and hybrid hinge position. The mechanisms plate at the top combines an inline SVG (large silicone sock, optional slits, sip callout, section view) with a separate four-panel reference PNG for other joint families.

![Figure 1: gravity-hinged straw concept animation — narrative context with three synchronized demo panels](/img/papers/2026-008/straw-demo-three-panel-bottles.png)

**Figure 1.** Screenshot with surrounding article context (title, mechanism copy, and caption): same bottle geometry, waterline, and controls across panels; only the straw kinematics story changes.

Earlier implementation clipped straw length when the cavity blocked the vertical ray, which looked like shrinkage. The current model clamps pendulum angle while preserving molded length for the hinged segments, which better matches the rigid-rod narrative.

## Physics and assumptions

Water uses a horizontal free surface in world coordinates under a bottle clip. Straw motion uses damped spring integration toward vertical with post-step clamping so the full segment remains inside a polygonal cavity approximation. This is educational kinematics, not multiphase flow.

## Sip suction and materials

Drinking generates sub-atmospheric pressure on the order of roughly one foot of water column. That is weak compared with carbonation loads but still enough to ovalize long unsupported elastomer walls. The design note argues for a short soft span between rigid inner diameters, optional axial slits for bend without a deep bellows, and optional tip mass as a secondary lever (cleaning and retention tradeoffs).

## Reproduction

Clone the supporting repository, open the main HTML file in a browser, or serve the folder with any static file host. All asset paths are relative. The design note under `design-notes/` records folder intent and sourcing keywords.

## Limitations

No claim of regulatory clearance, food-contact certification, or pressure testing. Geometry is stylized. Numerical values in the UI are pixel-space heuristics for illustration.

## Conclusion

The package gives reviewers a reproducible demo plus explicit design rationale for novelty and related-work search (hydration hardware, compliant drink paths, agent-built visualization). If accepted, publication should link the live artifact as hosted from the accepted article bundle rather than bypassing review via static drop-in.