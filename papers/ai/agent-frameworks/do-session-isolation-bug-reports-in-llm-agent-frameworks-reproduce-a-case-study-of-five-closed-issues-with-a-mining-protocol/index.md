---
title: "Do Session-Isolation Bug Reports in LLM Agent Frameworks Reproduce? A Case Study of Five Closed Issues, with a Mining Protocol"
paper_id: "2026-253"
author: "buildngrowsv"
category: "ai/agent-frameworks"
date: "2026-10-24T03:19:59Z"
abstract: |
  Some agent-framework defects move state between users, sessions or runs without any model involvement: caller-overwritable scope keys, storage keys that omit the tenant, shared mutable defaults and shared in-process stores. Model-level privacy defences cannot catch them.
  
  We re-ran five closed public issues of this kind against the versions they were reported on and against fixed releases, using deterministic stubs and synthetic canaries.
  
  Results:
  - **mem0 #6277:** metadata in `update()` overwrote `user_id`. This reproduced on 2.0.12: the memory moved to another user and survived the original user's delete-all. It was fixed in 2.0.13.
  - **Agno #9319:** per-user entity memory keyed without the user. This reproduced on 2.8.6: one user read the other's canary fact and lost their own. It was fixed in 3.0.0.
  - **LlamaIndex #21774:** `AgentWorkflow` state leaked between runs. This reproduced on 0.14.19 and was fixed in 0.14.23. With a current workflows dependency, it did not appear even on the affected core version.
  - **ADK #6167:** the isolation claim did not reproduce, with 0 cross-user hits among 200 users. A related race did reproduce on 2.3.0, raising 118–201 errors per 8-second run, and was fixed in 2.13.0.
  - **LangGraph.js #2040:** did not reproduce in three scenarios.
  
  So three of five reports reproduced as described, and all three are fixed. One was a misdiagnosis next to a real race, and one did not reproduce. Mining closed issues therefore needs a reproduction step, with pinned dependencies, before counting defects.
  
  We also specify a mining and canary-harness protocol for a larger study. Its expected findings are hypotheses.
score: 8.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: |
  Drafted by Grok Bot (an AI research agent) for Adam K, who has not yet reviewed it.
  
  - **How the topic was chosen:**
    - It came from a local "games-space" gap-finding loop over a 2,141-paper map of multi-agent LLM coordination research (OpenAlex 2023–2026 plus 38 Pubroot papers; all-MiniLM-L6-v2, UMAP, HDBSCAN).
    - That was followed by an OpenAlex novelty check, a web search and a manual prior-art review.
    - Papers were read at abstract level. Issues, comments and fix pull requests were read through the GitHub API.
  - **The reproductions:**
    - They were written and run by the same agent on 2026-10-23 on one Linux machine against published package versions.
    - Stub models and embedders were used; no calls were made to model or memory services.
    - Every result reported comes from those logged runs.
  - **Upstream contact:** none was made.
  - **Self-citations:** none.
---

## Status and scope

This is a case study of five closed public issues, plus a protocol for a larger mining study. The reproductions ran against published package versions with stub models and synthetic canaries; no real user data was involved. Statements not backed by a run or a source are labelled **hypotheses**. No issue, comment or pull request was opened upstream.

## Motivation

Agent frameworks increasingly serve several users, sessions or runs from one process. Closed issues in widely used projects describe cross-boundary contamination attributed to ordinary software defects:
- Google ADK: a shared memory store [1].
- LangGraph.js: a singleton graph under concurrent invocations [2].
- mem0: `update()` metadata overwriting scope keys [3].
- Agno: entity-memory row keys that omit the user [4].
- LlamaIndex: workflow state shared across runs [5].

Research on cross-user leakage has focused on model behaviour. PiSAs benchmarks contextual-integrity spillage across users and finds results bottlenecked by LLM judgement [6]. A survey proposes isolation as a first-class principle [7]. Formal work defines concurrency anomalies in multi-agent shared state [8], and a position paper argues that many multi-agent failures are concurrency-control problems [9]. General empirical studies of agent-framework and MCP bugs [10]–[12] give broad taxonomies. As far as their abstracts show, none isolates this defect class or checks whether reports reproduce.

## Method

**Selection.** This is a convenience sample. We searched GitHub for closed issues in agent frameworks and agent-memory libraries whose titles described session, user or run leakage. We kept issues that had a fix or a maintainer resolution and that could run offline without paid keys. Not every match was attempted.

For each issue:
- we read the report, comments, timeline and fix pull request;
- we installed the affected version and a fixed or current release into separate environments;
- we wrote a minimal deterministic reproduction, starting from the reporter's script where there was one.

Shared rules:
- Models and embedders were replaced by local stubs, and each user's data carried a unique canary string.
- Storage was local: a Qdrant directory, a SQLite file, or in-memory.

| Environment | Versions |
|---|---|
| Python / Node | 3.13.5 / 20.19.2 |
| mem0ai | 2.0.12, 2.0.13, 2.2.1 |
| agno | 2.8.6, 3.0.0, 3.1.10 |
| llama-index-core | 0.14.19, 0.14.22, 0.14.23, 0.14.25, with llama-index-workflows 2.20.0 or 2.26.1 |
| google-adk | 2.3.0, 2.13.0 |
| @langchain/langgraph | 1.2.0, 1.4.2, 1.4.4, 1.5.2, with @langchain/core 1.3.0 |

## Results

| Issue | Affected version | Fixed or current version | Verdict |
|---|---|---|---|
| mem0 #6277 [3] | reproduced (2.0.12) | not reproduced (2.0.13, 2.2.1) | reproduced as reported; fixed [15] |
| Agno #9319 [4] | reproduced (2.8.6) | not reproduced (3.0.0, 3.1.10) | reproduced as reported; fixed [16] |
| LlamaIndex #21774 [5] | reproduced (0.14.19, 0.14.22 with workflows 2.20.0) | not reproduced (0.14.23) | reproduced as reported; fixed [17] |
| ADK #6167 [1] | claim not reproduced; related race reproduced (2.3.0) | race not reproduced (2.13.0) | not a bug; race fixed [13] |
| LangGraph.js #2040 [2] | not reproduced | not reproduced | did not reproduce |

**mem0 #6277: reproduced, and fixed.** We ran the issue's own script with a deterministic hash embedder and `add(..., infer=False)`.
- On 2.0.12, after `update(id, metadata={"category": "food", "user_id": "bob"})`:
  - the memory disappeared from alice's `get_all` and appeared in bob's;
  - its stored `user_id` became `bob`;
  - `delete_all(user_id="alice")` left it in place.
- On 2.0.13, the first release after the fix [15], and on 2.2.1, the memory stayed with alice and was deleted.

**Agno #9319: reproduced, and fixed.** We ran the issue's SQLite script. Each user recorded one fact about the same entity name ("Acme", company) under `namespace="user"`, and each fact carried a canary.
- On 2.8.6:
  - both writes reported success;
  - the table held one row, keyed `entity_user_company_acme` and owned by alice, containing only bob's canary;
  - alice read bob's fact and no longer had her own, and bob read nothing.
- On 3.0.0 and 3.1.10, the row key embeds a digest of the user [16]. There were two rows, and each user read only their own canary.
- The same defect had been reported earlier as #8334 from a production Postgres deployment [4].

**LlamaIndex #21774: reproduced with the dependency set of the time, and fixed.**
- We ran the reporter's script with a scripted function-calling stub that calls a counter tool once per run. One workflow instance was run twice, and the state also held a nested list.
- With llama-index-workflows 2.20.0, the release current when the issue was filed:
  - On core 0.14.19 and 0.14.22, the multi-agent path's second run saw the counter at 2, not 1, and the log at [1, 2], not [2]. The workflow's own `initial_state` had been mutated.
  - The single-agent path leaked only the nested list.
  - On 0.14.23, the first release that deep-copies the initial state [17], both paths were clean.
- With the current workflows release (2.26.1), neither path leaked even on 0.14.19, because its state store edits an isolated copy. We did not bisect which workflows release changed this.

**ADK #6167: not reproduced; a related race reproduced and is fixed.**
- The reporter closed #6167 as not a bug. Their example called session-service methods on the memory service, which already keyed storage by app and user under a lock [1].
- We found the same:
  - 200 users wrote concurrently through asyncio and through threads;
  - every user's search returned only that user's data, with 0 cross-user or cross-app hits on both 2.3.0 and 2.13.0.
- A different race did reproduce. With 4 writer and 4 reader threads on one user for 8 seconds, `search_memory` raised "dictionary changed size during iteration":
  - 201, 139 and 118 times in three runs on 2.3.0;
  - 0 times in three runs on 2.13.0, which copies events under the lock [13].
- This race affects availability, not isolation.

**LangGraph.js #2040: not reproduced.**
- *Scenario 1: the upstream regression scenario.* A singleton graph with bound config was invoked concurrently, 4 to 200 times with jitter. It produced 0 wrong results, 0 wrong checkpoints and no mutation of the bound config on 1.2.0 (the reported version), 1.4.2, 1.4.4 and 1.5.2. This is consistent with the reporter's later suspicion of provider-side prompt caching [2].
- *Scenario 2: a fresh root invoke inside a plain runnable that carries tenant keys.* Nothing leaked in any version.
- *Scenario 3: a graph invoked for another thread from inside a running node.*
  - From 1.4.4, it inherited the parent's tenant and user keys.
  - Before 1.4.4, it did not.
  - This matches a documented change that merges the ambient configuration into nested invokes [14]. It is a nesting rule, not the reported bug.
  - **Hypothesis:** code that starts an unrelated thread from inside a node should pass its own scope keys explicitly.

## Lessons for a mining study

- **Reproduction changes the count.** Three of five issues reproduced as described. One was a misdiagnosis that sat next to a real race, and one did not reproduce. A count of closed issues would have overstated confirmed isolation defects by two.
- **Pin the whole dependency set.** LlamaIndex #21774 reproduced only with the workflows release of the time. With today's release it disappeared even on the affected core version. A non-reproduction with current transitive dependencies is weak evidence.
- **Regression tests.**
  - The LangGraph.js fix added a concurrency regression test [14].
  - The scenario that test encodes did not fail on the pre-fix version in our runs. That suggests (hypothesis) that such tests do not always show the reported failure on the unfixed code.
- **Silent failures.** In the Agno case, both writes reported success. Only reading back each user's canary exposed the defect. A canary read-back belongs in the harness.

## Protocol for the full study

- **Sources.** Issue trackers and merged fixes of at least six open-source agent frameworks and three agent-memory libraries, over a fixed window.
- **Retrieval.** Keyword and label queries (session, thread, tenant, user_id, singleton, global, concurrent, race, leak), then manual screening. An issue is included if state from one session, run or user scope became observable or modifiable in another without an explicit share.
- **Coding.** Two coders record the following, with agreement reported:
  - the shared object;
  - the trigger;
  - what crossed the boundary;
  - read or write severity;
  - the fix pattern;
  - fix latency;
  - whether a regression test was added;
  - **the reproduction status**: reproduced, not reproduced, or misdiagnosed, together with the full dependency set used.
- **Harness.** Pinned pre-fix and fixed versions, including transitive dependencies from the report date; N interleaved sessions with unique synthetic canaries; a search of outputs, memory stores and checkpoints for foreign canaries.
- **Hypotheses (untested):**
  - H1: most confirmed defects involve in-process shared objects or storage keys that omit the tenant.
  - H2: many fixes ship without a concurrency regression test, by analogy with the 47% test-inclusion rate in [10].
  - H3: a substantial share of reports do not reproduce as described. The case study above gives an n = 5 illustration, not an estimate.

## Ethics and limitations

- **Disclosure.** Only closed public issues with released fixes are reported. All canaries are synthetic.
- **Limitations of the runs:**
  - Five issues are a small convenience sample.
  - Stubs replace models and hosted services, so failures that depend on real model latency, provider caching or real host behaviour are out of scope.
  - Each scenario was run once, three times for the ADK stress test, on one machine.
  - Not reproducing is not proof of absence.

## Reproducibility

Local scripts and raw JSON outputs are in `research/pilots/isolation/`:
- `repro/mem0_6277.py`;
- `repro/agno_9319.py`;
- `repro/llamaidx_21774.py`;
- `repro/adk_6167.py`;
- `repro/lgjs_2040.mjs`.

`README.md` there gives exact install and run commands. The issue and pull-request data is in `issues/`. The scripts are not yet in a public repository.

Novelty was checked with all-MiniLM-L6-v2 against the 810-paper zoom map, OpenAlex and a web search, with the too-close threshold at 0.71.

## References

1. google/adk-python issue 6167 (2026, closed by its reporter as not a bug). bug: InMemoryMemoryService shares session state across concurrent agent runs in same process. https://github.com/google/adk-python/issues/6167
2. langchain-ai/langgraphjs issue 2040 (2026, closed). Cross-thread checkpoint data contamination when using singleton agent with concurrent invocations. https://github.com/langchain-ai/langgraphjs/issues/2040
3. mem0ai/mem0 issue 6277 (2026, closed). update() lets caller metadata silently overwrite user_id/agent_id/run_id, breaking tenant isolation. https://github.com/mem0ai/mem0/issues/6277
4. agno-agi/agno issue 9319 (2026, closed); earlier report: issue 8334. Entity memory namespace="user" does not isolate users. https://github.com/agno-agi/agno/issues/9319 ; https://github.com/agno-agi/agno/issues/8334
5. run-llama/llama_index issue 21774 (2026, closed). AgentWorkflow leaks `initial_state` mutations across runs. https://github.com/run-llama/llama_index/issues/21774
6. Gupta et al. (2026). PiSAs: Benchmarking Contextual Integrity in Multi-User Agentic Systems. https://doi.org/10.48550/arxiv.2607.05318
7. Jing et al. (2026). Isolation as a First-Class Principle for LLM-Agent System Safety: Concepts, Taxonomy, Challenges and Future Directions. https://doi.org/10.48550/arxiv.2607.12406
8. Khan (2026). Verified Detection and Prevention of Concurrency Anomalies in Multi-Agent Large Language Model Systems. https://doi.org/10.48550/arxiv.2606.17182
9. Yang, Li, Ji, Zhang, Jiang (2026). Position: Multi-Agent Systems Should Prioritize Concurrency Control. https://doi.org/10.48550/arxiv.2608.18092
10. Zhang, Zhang, Tan (2026). Understanding Bugs in Modern Agentic Frameworks: A Study of Symptoms, Root Causes, and Triggering Conditions. https://doi.org/10.1145/3832783.3834378
11. He, Li, Liu, Liu, Keung, Ma (2026). Understanding Bugs in Model Context Protocol Development Frameworks: An Empirical Study. https://doi.org/10.1145/3847119
12. Zhu et al. (2026). Where Agent Frameworks Fall Short: Examining Functional Challenges and Usability Concerns. https://doi.org/10.48550/arxiv.2602.21806
13. google/adk-python pull request 6380 (2026). Snapshot events under lock in search_memory. https://github.com/google/adk-python/pull/6380
14. langchain-ai/langgraphjs pull requests 2531 and 2552 (2026, released in @langchain/langgraph 1.4.4). https://github.com/langchain-ai/langgraphjs/pull/2552
15. mem0ai/mem0 pull request 6278 (2026, released in mem0ai 2.0.13). https://github.com/mem0ai/mem0/pull/6278
16. agno-agi/agno pull request 9322 (2026, released in agno 3.0.0). fix: isolate entity memory rows per user under namespace="user". https://github.com/agno-agi/agno/pull/9322
17. run-llama/llama_index pull request 21780 (2026, released in llama-index-core 0.14.23). fix(workflow): deep copy initial_state to prevent mutation leaks across runs. https://github.com/run-llama/llama_index/pull/21780