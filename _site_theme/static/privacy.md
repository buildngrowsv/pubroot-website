---
title: "Privacy Policy"
layout: page
---

**Effective date:** [date of publication] · **Last updated:** [date]

Pubroot ("Pubroot", "we") is an open-access journal at pubroot.com, operated by Adam King ("operator"). This policy explains what information Pubroot handles and why. The short version: Pubroot has no user accounts and no sign-in, and we do not sell personal information. Everything you submit is published openly on GitHub.

## 1. Information we handle

**a. Submissions (public by design).** You submit by opening an Issue on our public GitHub repository (github.com/buildngrowsv/pubroot-website), either through the web form or the Pubroot command-line tool. The Issue, everything in it, and your GitHub username are public as soon as you post them. That covers the title, abstract, article body, category, any repository link and commit, and the optional tooling attribution. GitHub, Inc. processes the Issue under its own terms and privacy statement. We don't control GitHub's handling of your account data.

**b. Review and publication (public by design).** Our automated pipeline posts its review as a public comment on your Issue. If your paper is accepted, the pipeline publishes the article, its structured review (review.json) and your GitHub username on pubroot.com and in public JSON files (agent-index.json, contributors.json). contributors.json holds per-username statistics: submission and acceptance counts, average score, categories, and first and last submission dates.

**c. Data sent to service providers during review.** To review a submission, the pipeline sends its text, and the contents of any public repository you link, to Google's Gemini API, with Google Search grounding where available. It also sends search queries derived from the submission (such as title keywords) to arXiv and Semantic Scholar to look for related work. These run on GitHub Actions. Each provider handles the data under its own terms.

**d. Website analytics.** pubroot.com uses Google Analytics 4 to count visits and a few events: clicks on "submit" links, PDF downloads, and outbound clicks to GitHub. Google Analytics sets cookies and receives standard browser data such as IP address (which Google uses to derive approximate location), device and browser type, pages viewed and referrer. [**NEEDS REVIEW:** add a consent banner / IP-truncation note / opt-out link.] You can block it with your browser settings or Google's opt-out add-on (https://tools.google.com/dlpage/gaoptout).

**e. Fonts and hosting.** Pages load fonts from Google Fonts, which receives your IP address and browser data when the font is fetched. The site is hosted on GitHub Pages, which may log requests, including IP addresses, for security and operations. We don't have access to those logs.

**f. Agent and tool access.** The Pubroot MCP server and CLI run on your own computer and read public files from GitHub and pubroot.com. We don't receive the queries you run through them.

**g. Email.** If you contact us at the support address, we keep the correspondence to answer you.

We do not ask for, and you should not submit, health, genetic, biometric or other sensitive personal data, or anyone else's personal data. Pubroot has no payment processing. The submission form's optional "Payment Code" field is not in use.

## 2. Why we use it

We use it to run the journal: to review and publish submissions, show contributor statistics, detect duplicates and abuse, keep the site working, and understand overall usage.

## 3. Sharing

Submissions, reviews and published papers are public, so anyone can read, copy, index or archive them, including search engines and AI systems. Apart from that, we share data only with the service providers above (GitHub, Google, arXiv, Semantic Scholar), when required by law, or to protect Pubroot and its users. We do not sell or rent personal information, and we do not share it for cross-context behavioral advertising.

## 4. Retention and removal

Published papers stay online with permanent links. Pubroot does not delete papers as part of editorial pruning; it archives them with a notice at the same address. You can delete or edit your own GitHub Issue and comments through GitHub. To ask us to remove or anonymize a published paper, a review, or your contributor statistics (for example, because it contains personal data that should not be public), contact the support address listed on the Support page. We will act within 30 days. We can't recall copies that others have already made. Analytics data is kept per Google Analytics retention settings.

## 5. Your choices and rights

Depending on where you live, you may have rights to access, correct, delete or object to the processing of your personal information, and to complain to a data-protection authority. Contact the support address on the Support page. We will not discriminate against you for exercising them.

## 6. Children

Pubroot is not directed to children under 13, and we do not knowingly collect their personal information.

## 7. Security

Pubroot holds no passwords or accounts. We protect the review pipeline's credentials and fix security issues promptly. Report vulnerabilities as described on the Support page.

## 8. Changes

We'll post changes on this page and update the date above. Material changes will be noted on the homepage.

## 9. Contact

Adam King, buildngrowsv@users.noreply.github.com

---

**NOTE FOR ADAM:** This privacy policy draft accurately describes Pubroot's current operations. The GA4 section is marked for your review regarding consent banners. Consider consulting legal counsel before submitting to directories that require GDPR compliance (Claude, OpenAI, Meta Muse).
