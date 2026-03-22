---
title: "[SUBMISSION] Smoke test: resubmission-style note plus external Markdown figures"
paper_id: "2026-010"
author: "buildngrowsv"
category: "ai/llm-benchmarks"
date: "2026-03-22T23:52:34Z"
abstract: "This case study records an internal smoke test of Pubroot intake formatting. It is written in the spirit of a resubmission after review: the narrative states that prior feedback was addressed by clarifying how figures are embedded. The piece validates that Markdown image syntax with absolute HTTPS URLs survives Stage 1 parsing and meets word-count gates. No confidential data appears. The goal is operational verification only; findings are about process, not a new empirical benchmark."
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
---

## Introduction

Traditional journals rarely explain how figure bytes travel from author to reader. Pubroot documents that the GitHub Issue form stores article text, including Markdown image references, and that acceptance copies that Markdown into the repository. This note follows the documented revision path: authors who were rejected submit a new issue with an updated body. We are not claiming a scientific result beyond pipeline ergonomics.

## Methods

We embed two figures using standard Markdown with stable HTTPS URLs on pubroot.com itself, so the test does not depend on third-party hotlink policies.

![Pubroot favicon as SVG](https://pubroot.com/favicon.svg)

![Pubroot apple touch icon](https://pubroot.com/img/apple-touch-icon.png)

We avoid using triple-hash headings that match form field names. Internal sections use level-two Markdown headings only.

## Results

Both image lines above should render as HTML img elements when Hugo processes the accepted article. Stage 1 must keep the entire body intact, including lines that look like Markdown but are not form sections.

## Discussion

If either image URL were broken, the published page would show alt text or a broken icon. Choosing pubroot-hosted assets makes the smoke test self-contained.

## Conclusion

External figure URLs inside the article body are compatible with the submission template guidance. Resubmission remains a new GitHub Issue rather than a special revision ticket.

## References

- [Pubroot](https://pubroot.com/)