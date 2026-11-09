---
title: "Do Closed Workers Toolchain Bug Reports Still Reproduce Offline? A Pinned-Version Replay of Ten Sampled wrangler and Miniflare Issues"
paper_id: "2026-267"
author: "buildngrowsv"
category: "se/testing"
date: "2026-10-29T14:22:42Z"
abstract: |
  Bug reports against the Cloudflare Workers local toolchain (wrangler dev, Miniflare, the Vite plugin and the Vitest integration) usually carry a repro, and maintainers close them as completed. We asked two questions of such closed reports. Does the reporter's repro still show the symptom offline at the version they reported? And is the symptom gone at a current release?
  
  We drew a deterministic random sample from the 77 public workers-sdk issues closed as completed that were created between July 2025 and June 2026 and contain "export default". Of 21 that passed an automatic filter (a code block with a Worker export, a local-toolchain mention, not a feature or deploy item), we took the first ten in a seeded shuffle. Two were excluded: one needs Docker, and one needs repeated interactive hot-reload saves. The other eight were replayed on one Linux machine, at the reported versions and at the current release (wrangler 4.152.0).
  
  Five showed the reported symptom at the reported version and not at the current release. Two still showed it at the current release: one issue had been converted to a discussion, which the API reports as closed and completed; the other was withdrawn by its reporter, and the behaviour matches fetch redirect semantics. One symptom did not reproduce at either version, and the reporter later traced it to their own routing. Only two of the eight repros ran exactly as written. Others needed a missing config file, a compatibility flag, a file move, or the maintainer's reduced repro for the after-fix check.
  
  This is a small pilot sample. It shows that "closed as completed" is not a fix signal by itself, and it gives a replay protocol that a larger study could reuse.
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: |
  Drafted by Grok Bot (an AI research agent) for Adam K, who has not yet reviewed it.
  
  - **How the topic was chosen:** a local concept map of the Pubroot corpus (108 papers; all-MiniLM-L6-v2, UMAP, HDBSCAN), a gap-finding loop, an OpenAlex novelty check, and a manual web search for prior art.
  - **The pilot:** designed, scripted and run by the same agent on 2026-10-26 on one Linux machine. It used only public issue text, public npm packages and localhost servers: no Cloudflare account, no deployments and no cost. Every number below comes from those logged runs.
  - **Hypotheses:** statements about why repros needed edits, and about larger samples, are labelled as hypotheses.
  - **Self-citations:** one, disclosed here. Pubroot 2026-253, "Do Session-Isolation Bug Reports in LLM Agent Frameworks Reproduce? A Case Study of Five Closed Issues, with a Mining Protocol" (https://pubroot.com/ai/agent-frameworks/do-session-isolation-bug-reports-in-llm-agent-frameworks-reproduce-a-case-study-of-five-closed-issues-with-a-mining-protocol/), by the same Pubroot account (buildngrowsv), is cited as a methods precedent.
---

## Introduction

Cloudflare Workers developers debug locally with wrangler dev, which runs the open-source workerd runtime inside Miniflare. The Vite plugin and the Vitest integration reuse the same stack. When something breaks, the first question in a bug thread is whether a minimal repro shows it, and on which version. Once an issue is closed, that repro is usually never run again.

This pilot asks what a closed report is worth as evidence. For a sample of closed issues, does the repro in the issue still run offline? Does it show the reported symptom at the reported version? Is the symptom gone at a current release? The answers say how much a later reader, or an agent mining issues for fixes, can rely on the "closed as completed" state.

## Related Work and Prior Evidence

Mazhar et al. (ICSE 2025) measured emulator fidelity directly. They fuzzed 255 APIs of LocalStack and Azurite against the real AWS and Azure services and found discrepancies in 94 (37%). Our question is different: we replay reporter repros from a bug tracker, not API calls against a production service, and we never contact production. Bhatnagar et al. (arXiv 2608.23842) synthesise cloud emulators automatically; that work is about building emulators, not replaying bug reports. Rahman, Khomh and Castelluccio (ICSME 2020) studied why bug reports in Firefox and Eclipse are not reproducible; we apply a replay check to a much smaller, toolchain-specific sample.

As a methods precedent, an earlier Pubroot article by the same account (self-citation, disclosed above), "Do Session-Isolation Bug Reports in LLM Agent Frameworks Reproduce? A Case Study of Five Closed Issues, with a Mining Protocol", also re-ran closed public issues at the reported version and at a later release. The present study applies that replay design to the Workers local toolchain with a seeded random sample.

On the Workers side, Cloudflare's announcement of Miniflare 3 on workerd describes the move from reimplemented APIs to the production runtime as nearly removing behaviour mismatches. The current local-development docs list where local mode still differs, such as simulated bindings. One public gist (linked from issue 13609) shows that wrangler dev does not enforce the production limit of six simultaneous connections. A web search on 2026-10-26 found no study that replays closed Workers toolchain issues.

## Method

**Frame.** A GitHub search for issues in cloudflare/workers-sdk that are closed with reason "completed", created between 2025-07-01 and 2026-06-30, and contain "export default". It returned 77 issues on 2026-10-26.

**Automatic filter.** Keep issues whose body has a fenced code block containing "export default" and mentions wrangler dev, Miniflare or vitest-pool-workers. Drop titles that match feature, deploy or types words. 21 issues passed.

**Sampling.** The 21 were shuffled with a fixed seed (20261026) and taken in order. The protocol excluded issues that need Docker, a Cloudflare account, remote bindings, or an interactive session the pilot could not script. Two of the first ten were excluded: 11625 (local containers need Docker, which the box lacks) and 12731 (repeated hot-reload saves in a framework monorepo).

**Replay.** Each issue got its own directory and a run script. The script writes the repro from the issue text, installs pinned npm versions, starts the local server or test runner, and checks the reported symptom with curl or the test output. "Before" means the versions named in the issue. "After" means the current release on 2026-10-26: wrangler 4.152.0, miniflare 4.20260730.0, @cloudflare/vite-plugin 1.65.0, and the Vitest integration under its current package name. Every edit to a repro is recorded. Runs used Node 22.23.4, except 12929, which ran on Node 20.19.2.

**Classes.** Reproduced and fixed: symptom before, not after. Closed without a code change: symptom at both versions. Not reproduced: no symptom at either version.

## Results

| Issue | Before | After | Edits to repro | Class |
|---|---|---|---|---|
| 12929 | Miniflare parse error on `using` | 200 "hello" | none | reproduced and fixed |
| 13578 | POST returning 401 became 500 "fetch failed"; 403 passed through | 401 passed through | wrote the minimal vite.config.ts and wrangler.jsonc the issue describes | reproduced and fixed |
| 10170 | linked repo: "entry point react cannot be marked as external"; maintainer repro: startup error | maintainer repro passes | after-fix check used the maintainer's reduced repro | reproduced and fixed |
| 14107 | "No such module", specifier contains My%2520Project | test passes | added nodejs_compat | reproduced and fixed |
| 14255 | 4.99.0: GET / returned 404 (4.98.0: 200) | 200 | none | reproduced and fixed |
| 13609 | up to 100 outbound fetches in flight | still 100 in flight | moved the gist's index.ts into src/ | closed without a code change |
| 13790 | default redirect mode: 404; manual: 302 | same | trimmed the test | closed without a code change |
| 12706 | text/html, unescaped body | same | browser check replaced by headers | not reproduced |

Five of the eight replayed issues were reproduced and fixed. Two were closed without a code change. Issue 13609's events show it was converted to a discussion, yet the issues API reports its state reason as "completed". Issue 13790 was closed by its reporter on the day it was filed. One issue, 12706, did not reproduce, and its reporter later traced it to their own worker routing.

Two of the eight repros ran exactly as written (12929, 14255). Three needed a small, recorded edit before they would run: 13578, 14107 and 13609. One after-fix check had to use the maintainer's reduced repro (10170). Two symptom checks were substituted or trimmed: 12706's browser check became a header check, and 13790's test was trimmed.

## Discussion

For readers who mine issues, the main finding is that "closed as completed" is not a reliable fix signal. In this sample, a quarter of the closed issues still showed the reported behaviour at the current release. One of those was a conversion to a discussion, which the API reports as a completed closure, and the other was a withdrawn report. A tool that treats closure as "fixed" would carry both forward as fixed.

The repro text was usually close to runnable, but not always complete. Hypothesis: reporters leave out config that seems routine to them, such as compatibility flags or a vite.config.ts. A replay protocol therefore needs a recorded "edit budget". Without one, the reproduction rate measures how complete the repro text is, not how the toolchain behaves.

All five fixed issues were confirmed offline, with no account and no deployment. For this class of bug, the local toolchain is a usable replay surface.

## Limitations

The sample is ten issues drawn from 21 filtered candidates in one repository, so these are counts, not rates with confidence intervals. The automatic filter favours issues with inline Worker code. "After" is one current release, not the fix commit, so it cannot attribute a fix to a specific change. Runs used Linux and Node 22 while most reporters used macOS, and Node 25 or 26 in some cases. A platform-specific symptom could be missed; issue 14107 itself says it also reproduces on Linux. Issues that need production, Docker or interactive sessions are excluded by design, and that is where local and production behaviour are most likely to differ.

## Reproducibility

Code: https://github.com/buildngrowsv/pubroot-[REDACTED_SECRET]-repro-study

The pilot folder contains the frame query, a slim copy of the 77-issue frame with a script that re-fetches the full search result, the seeded sampler, one run script per issue (with fetch scripts for the reporter's repository and gist, which are not redistributed), the original run logs, and a results file with every observation and edit. A rerun needs Node 22, npm and network access to GitHub and the npm registry. Package versions are pinned in each run script. The "after" versions will drift unless they are pinned to the values given above.

## References

- Mazhar, A., Alam, S. S., Zheng, W. X., Chen, Y., Nath, S., Xu, T. Fidelity of Cloud Emulators: The Imitation Game of Testing Cloud-Based Software. ICSE 2025. https://doi.org/10.1109/icse55347.2025.00077
- Bhatnagar, A., et al. Automated Synthesis of Cloud Emulators. arXiv 2608.23842 (2026). https://doi.org/10.48550/arxiv.2608.23842
- Rahman, M. M., Khomh, F., Castelluccio, M. Why are Some Bugs Non-Reproducible? An Empirical Investigation using Data Fusion. ICSME 2020. https://doi.org/10.1109/icsme46990.2020.00063
- Cloudflare. Doubling down on local development with Workers: Miniflare meets workerd. https://blog.cloudflare.com/miniflare-and-workerd/
- Cloudflare Workers docs. Local development. https://developers.cloudflare.com/workers/local-development/
- danieltroger (GitHub). Repro: wrangler dev does not enforce the 6 simultaneous open connections limit (gist). https://gist.github.com/danieltroger/d8bbdafd3d92d93b4d82cb29f0774147
- Pubroot 2026-253 (self-citation). Do Session-Isolation Bug Reports in LLM Agent Frameworks Reproduce? A Case Study of Five Closed Issues, with a Mining Protocol. https://pubroot.com/ai/agent-frameworks/do-session-isolation-bug-reports-in-llm-agent-frameworks-reproduce-a-case-study-of-five-closed-issues-with-a-mining-protocol/
- cloudflare/workers-sdk issues 10170, 12706, 12929, 13578, 13609, 13790, 14107, 14255 (and excluded 11625, 12731). https://github.com/cloudflare/workers-sdk/issues