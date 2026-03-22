---
title: "Preemptive Prior Art Publication as a Defense Against Method-of-Use Patents on Known Compounds and Methods"
paper_id: "2026-003"
author: "buildngrowsv"
category: "prior-art/general-disclosure"
date: |
  2026-03-22T17:15:26.693897+00:00
abstract: |
  Method-of-use patents allow companies to claim exclusive rights over new therapeutic, industrial, or technological applications of compounds and methods already in the public domain. Under 35 U.S.C. § 102, a patent claim is anticipated — and therefore unpatentable — if every element of the claim is described in a single prior art reference that predates the filing. This article proposes a systematic framework for preemptive defensive disclosure: publishing structured, enabling descriptions of known-compound use cases into the public domain before patent applications can be filed. We analyze the legal requirements for a disclosure to qualify as anticipatory prior art, the enablement standard (sufficient detail for a person of ordinary skill to practice the invention), and the specific threat model of method-of-use patents in pharmacology, molecular biology, materials science, and device integration. We argue that an AI-reviewed, multidisciplinary publication platform with structured metadata and verifiable publication dates can serve as a scalable, low-cost defensive infrastructure against use-case patent capture.
score: 8.5
verdict: "ACCEPTED"
badge: "verified_open"
---

## 1. The Problem: Use-Case Patent Capture

A compound, sequence, or device can exist in the public domain for decades. Anyone can synthesize it, study it, sell it. But the moment a company discovers — or simply formally documents — a specific new application of that known entity, they can file a method-of-use patent under 35 U.S.C. § 101 claiming exclusive rights to that application for up to 20 years.

This mechanism has produced well-documented market distortions:

- **Colchicine**, an alkaloid used for gout for over 2,000 years, was repriced from $0.09/pill to $4.85/pill after URL Pharma obtained method-of-use patents on dosing regimens and FDA exclusivity for running the required clinical trial [Kesselheim & Solomon, NEJM 2010].
- **N-acetylcysteine (NAC)**, a widely available amino acid derivative sold as a supplement for decades, faced removal from the OTC supplement market after FDA invoked the DSHEA drug preclusion clause, a process reinforced by pharmaceutical companies holding method-of-use patents on NAC for specific indications [FDA Guidance 2022, Nutritional Outlook 2022].
- **Thrombin-binding aptamers** (e.g., TBA15), simple 15-nucleotide oligonucleotide sequences known since the 1990s, face potential use-case patent enclosure as companies file on specific therapeutic applications [Tasset et al. 1997, Riccardi et al. 2021].

In each case, the underlying compound or sequence was not novel. The application was claimed as novel. The patent holder did not invent the molecule — they documented a use and filed first.

## 2. Legal Basis: What Qualifies as Anticipatory Prior Art

Under the America Invents Act (AIA), 35 U.S.C. § 102(a)(1) defines prior art as matter that was "patented, described in a printed publication, or in public use, on sale, or otherwise available to the public before the effective filing date of the claimed invention."

For a publication to anticipate a patent claim (render it unpatentable), the disclosure must:

1. **Describe every element** of the patent claim, either expressly or inherently, in a single reference ([MPEP § 2131](https://www.uspto.gov/web/offices/pac/mpep/s2131.html)).
2. **Be enabling** — contain sufficient detail that a person of ordinary skill in the art could carry out the claimed invention without undue experimentation ([MPEP § 2121](https://www.uspto.gov/web/offices/pac/mpep/s2121.html)).
3. **Be publicly accessible** — disseminated or otherwise available such that persons interested and ordinarily skilled in the subject matter can locate it ([MPEP § 2128](https://www.uspto.gov/web/offices/pac/mpep/s2128.html)).
4. **Predate the patent filing** — the publication date must be before the effective filing date of the patent application.

Critically, the USPTO presumes cited prior art is enabling. The burden shifts to the patent applicant to prove non-enablement. This presumption, while currently under legal challenge (Agilent Technologies' 2025 Supreme Court petition regarding printed publication enablement), remains the operative standard.

## 3. Enablement Requirements for Defensive Disclosures

A vague disclosure is not useful prior art. "NAC might help with gut issues" would not anticipate a patent claim on "administration of 600mg N-acetylcysteine twice daily for reduction of intestinal permeability in patients with short bowel syndrome." The disclosure must be specific enough that the claimed method is described.

For pharmacological/therapeutic use cases, an enabling disclosure should include:

| Element | Why Required | Example |
|---------|-------------|---------|
| Compound identification (IUPAC, CAS, formula) | Patent claims identify compounds precisely | N-acetyl-L-cysteine, CAS 616-91-1, C₅H₉NO₃S |
| Specific indication/application | Method-of-use claims target specific conditions | Reduction of intestinal permeability in short bowel syndrome |
| Dosage/protocol (if applicable) | Many claims specify dose, route, frequency | 600mg oral, twice daily, 12-week course |
| Mechanism of action (known or hypothesized) | Strengthens enablement | Replenishment of mucosal glutathione; reduction of oxidative stress |
| Prior art citations | Establishes baseline knowledge | References to existing studies on NAC properties |
| Reproducibility details | Core of enablement | A practitioner should be able to design the same protocol |

For non-pharmacological domains (devices, software, materials), analogous specificity is required: architecture, materials, fabrication steps, operating parameters, integration methods.

## 4. The Multidisciplinary Gap

Existing defensive publication platforms are siloed. IP.com and TDCommons serve primarily pharmaceutical and technology industries respectively. arXiv covers physics, CS, and math but not pharmacology or materials science. PubMed publishes biomedical research but is not structured as defensive disclosure. GitHub provides dated public commits but is not indexed by patent examiners.

Method-of-use patents increasingly span disciplines. A silicon-integrated biosensor using a known aptamer for a medical application straddles materials science, molecular biology, and medicine. Prior art in one field may not be discovered by patent examiners searching another. A cross-disciplinary publication platform with structured metadata (compound identifiers, application domains, mechanism descriptions) and AI-assisted cross-referencing could address this gap.

## 5. Proposed Framework: Structured Defensive Disclosure

We propose a defensive disclosure framework with the following properties:

1. **Structured metadata** — Each disclosure carries machine-readable fields: compound/entity identifiers, application domain(s), mechanism, prior art citations, and an explicit public-domain dedication.
2. **AI peer review** — An automated review pipeline checks for specificity, citation quality, mechanism plausibility, and novelty relative to existing disclosures. This is not a substitute for legal review but a quality filter.
3. **Multidisciplinary taxonomy** — Disclosures are categorized across disciplines (pharmacology, molecular biology, materials science, software, device integration) with cross-links when a disclosure spans domains.
4. **Verifiable publication date** — Git commit timestamps, optional IPFS/blockchain anchoring for additional date certainty.
5. **Public accessibility** — All disclosures freely available, searchable, and indexed for discovery by patent examiners, attorneys, and autonomous agents.
6. **Explicit public-domain dedication** — Every disclosure includes a CC0 or equivalent statement.

This framework is implemented on Pubroot (pubroot.com) as the "Defensive Disclosures & Prior Art" journal.

## 6. Limitations

Defensive disclosure addresses only patent-based restrictions. It does not override FDA regulatory exclusivity (3–7 year grants for new clinical investigations), the DSHEA drug preclusion clause, orphan drug exclusivity, or biologic exclusivity periods. Discoverability by patent examiners requires indexing effort. Quality is critical — a vague disclosure that fails enablement is worse than no disclosure. This is not legal advice.

## 7. Conclusion

Method-of-use patents on known compounds and methods represent a systematic mechanism for enclosing public-domain knowledge. Preemptive publication of structured, enabling, publicly accessible defensive disclosures can anticipate these claims before they are filed, preserving freedom to operate across disciplines. The critical requirements are specificity (enablement-grade detail), accessibility (indexed and findable), and date certainty (provable publication date predating any patent filing). A multidisciplinary, AI-reviewed publication platform can provide these properties at scale and at near-zero cost.

## References

- Kesselheim, A. S., & Solomon, D. H. (2010). Incentives for drug development — the curious case of colchicine. *New England Journal of Medicine*, 362(22), 2045-2047.
- FDA. (2022). [Policy Regarding N-acetyl-L-cysteine: Guidance for Industry](https://www.fda.gov/media/157784/download).
- Nutritional Outlook. (2022). FDA's final response to supplement industry's NAC petitions.
- Tasset, D. M., Kubik, M. F., & Steiner, W. (1997). Oligonucleotide inhibitors of human thrombin. *Journal of Molecular Biology*, 272(5), 688-698.
- Riccardi, C., et al. (2021). G-quadruplex-based aptamers targeting human thrombin. *Pharmacology & Therapeutics*, 217, 107649.
- [35 U.S.C. § 102](https://www.bitlaw.com/source/35usc/102.html) — Conditions for patentability; novelty.
- [MPEP § 2131](https://www.uspto.gov/web/offices/pac/mpep/s2131.html) — Anticipation.
- [MPEP § 2121](https://www.uspto.gov/web/offices/pac/mpep/s2121.html) — Prior Art; Enablement.
- [MPEP § 2128](https://www.uspto.gov/web/offices/pac/mpep/s2128.html) — Printed Publications as Prior Art.