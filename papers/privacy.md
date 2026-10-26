# DRAFT — needs lawyer review before publishing
<!-- Listing-kit copy, updated 2026-10-25 8:30 PM CT from policy/privacy.draft.md. Changes: the review-provider wording now covers the OpenRouter switch (D-11, PR #250, open); the support address stays a placeholder because the GitHub noreply address used in PR #247 cannot receive mail. PR #247 already carries an earlier version of this text as papers/privacy.md. Replace it with this one before merge. -->

<!-- Pubroot Distribution draft, 2026-10-23 (CT), for Pubroot Lead / Adam King. Target: https://pubroot.com/privacy/ (build-list B3). Owner of final text: Q-AD4.
     Facts checked against the repo at aee2bbc and the live site on 2026-10-23. Bracketed [ ] items need a decision.
     Lawyer flags: (1) GA4 runs with no consent banner, which matters for EU/UK visitors (GDPR/ePrivacy) and California (CCPA/CPRA "sharing").
     (2) Controller identity: an individual (Adam King) vs. an entity (Q-AD3). (3) Retention: public GitHub content is effectively permanent and copied by others.
     (4) If B7 (GitHub OAuth) ever ships, this policy must be rewritten before launch. -->

---
title: "Privacy Policy"
---

**Effective date:** [date of publication] · **Last updated:** [date]

Pubroot ("Pubroot", "we") is an open-access journal at pubroot.com, operated by [Adam King / legal entity name] ("operator"). This policy explains what information Pubroot handles and why. The short version: Pubroot has no user accounts and no sign-in, and we do not sell personal information. Everything you submit is published openly on GitHub.

## 1. Information we handle

**a. Submissions (public by design).** You submit by opening an Issue on our public GitHub repository (github.com/buildngrowsv/pubroot-website), either through the web form or the Pubroot command-line tool. The Issue, everything in it, and your GitHub username are public as soon as you post them. That covers the title, abstract, article body, category, any repository link and commit, and the optional tooling attribution. GitHub, Inc. processes the Issue under its own terms and privacy statement. We don't control GitHub's handling of your account data.

**b. Review and publication (public by design).** Our automated pipeline posts its review as a public comment on your Issue. If your paper is accepted, the pipeline publishes the article, its structured review (review.json) and your GitHub username on pubroot.com and in public JSON files (agent-index.json, contributors.json). contributors.json holds per-username statistics: submission and acceptance counts, average score, categories, and first and last submission dates.

**c. Data sent to service providers during review.** To review a submission, the pipeline sends its text, and the contents of any public repository you link, to an AI model provider: today Google's Gemini API, with Google Search grounding where available. [After PR #250 merges, use instead: "to OpenRouter, which routes it to the selected model (currently Google Gemini) and may run a web search through OpenRouter's search tool."] It also sends search queries derived from the submission (such as title keywords) to arXiv and Semantic Scholar to look for related work. These run on GitHub Actions. Each provider handles the data under its own terms.

**d. Website analytics.** pubroot.com uses Google Analytics 4 to count visits and a few events: clicks on "submit" links, PDF downloads, and outbound clicks to GitHub. Google Analytics sets cookies and receives standard browser data such as IP address (which Google uses to derive approximate location), device and browser type, pages viewed and referrer. [Decide: add a consent banner / IP-truncation note / opt-out link.] You can block it with your browser settings or Google's opt-out add-on (https://tools.google.com/dlpage/gaoptout).

**e. Fonts and hosting.** Pages load fonts from Google Fonts, which receives your IP address and browser data when the font is fetched. The site is hosted on GitHub Pages, which may log requests, including IP addresses, for security and operations. We don't have access to those logs.

**f. Agent and tool access.** The Pubroot MCP server and CLI run on your own computer and read public files from GitHub and pubroot.com. We don't receive the queries you run through them. [If B4 ships: "Our hosted endpoint at mcp.pubroot.com logs request counts per tool and client name, without IP addresses or query text, for [N] days." Update before launch.]

**g. Email.** If you contact us at [support address], we keep the correspondence to answer you.

We do not ask for, and you should not submit, health, genetic, biometric or other sensitive personal data, or anyone else's personal data. Pubroot has no payment processing. The submission form's optional "Payment Code" field is not in use.

## 2. Why we use it

We use it to run the journal: to review and publish submissions, show contributor statistics, detect duplicates and abuse, keep the site working, and understand overall usage. [Legal bases for EEA/UK visitors: legitimate interests (operating the journal; analytics, subject to consent where required); performance of the submission you request.]

## 3. Sharing

Submissions, reviews and published papers are public, so anyone can read, copy, index or archive them, including search engines and AI systems. Apart from that, we share data only with the service providers above (GitHub, Google, [OpenRouter, after PR #250,] arXiv, Semantic Scholar), when required by law, or to protect Pubroot and its users. We do not sell or rent personal information, and we do not share it for cross-context behavioral advertising [lawyer: confirm the GA4 configuration supports this statement].

## 4. Retention and removal

Published papers stay online with permanent links. Pubroot does not delete papers as part of editorial pruning; it archives them with a notice at the same address. You can delete or edit your own GitHub Issue and comments through GitHub. To ask us to remove or anonymize a published paper, a review, or your contributor statistics (for example, because it contains personal data that should not be public), contact [support address]. We will act within [30] days. We can't recall copies that others have already made. Analytics data is kept for [Google Analytics retention setting, e.g. 14 months].

## 5. Your choices and rights

Depending on where you live, you may have rights to access, correct, delete or object to the processing of your personal information, and to complain to a data-protection authority. Contact [support address]. We will not discriminate against you for exercising them.

## 6. Children

Pubroot is not directed to children under 13 [16 in the EEA/UK], and we do not knowingly collect their personal information.

## 7. Security

Pubroot holds no passwords or accounts. We protect the review pipeline's credentials and fix security issues promptly. Report vulnerabilities as described on the Support page.

## 8. Changes

We'll post changes on this page and update the date above. Material changes will be noted on the homepage [for 30 days].

## 9. Contact

[Adam King / entity], [postal address if required], [support address]
