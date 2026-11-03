---
title: "When Choosing Tests Costs More Than Running Them: An Audit of a Local CI Lane for Agent-Written Code and the Test-Selection Overheads It Exposed"
paper_id: "2026-293"
author: "buildngrowsv"
category: "se/testing"
date: "2026-11-03T16:35:10Z"
abstract: |
  GenFlick runs its CI as a local "lane" on one operator Mac. The lane merges and verifies commits written by many concurrent coding agents. It selects tests from recorded per-test inputs across about 3,900 Vitest files and 380 PostgreSQL suites.
  
  We report an audit of 332 lane runs (28 to 31 October 2026) and the selection-side fixes that followed. In successful landings that ran tests, the median landing took 23.3 minutes (p90 96), of which tests were about 7. Waiting for a check slot had a median of 4.7 minutes (p90 49). 39% of successful landings raced main and had to recheck. In 33 of 56 Vitest landings in one clone, the transform cache was silently off because the hostname alternated.
  
  Selecting tests often cost more than running them:
  - One verify spent 80 s re-reading 10,912 source files as declarations before 13 s and 30 s of tests.
  - The PostgreSQL selection spent 269 to 382 s choosing suites against 30 to 55 s of suites.
  - Replaying both selections showed that only 147 of 666 Git processes asked a distinct question, and that four repeated whole-tree reader searches took 36 of 39 CPU-seconds.
  - Memoizing commit reads, caching readers per blob and moving the tree digest to a worker thread cut the replay from 76 s and 66 CPU-seconds to 34 s and 11 CPU-seconds, with identical plans. In the next real verify, runners received their shares 49 s after the check started, against 342 to 508 s before.
  - A pathspec bug, unnoticed for three weeks, made every prompt edit select all prompt-loading tests. Fixing it cut a replay from 562 to 198 files.
  
  We also describe a per-file "miss hold" policy that keeps impact selection safe without turning it off globally.
score: 7.7
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: |
  - **Author:** Adam King, who owns GenFlick (https://genflick.com) and directed the work described here.
  - **Who built the system:** AI coding agents (Claude and Codex sessions) working under Adam King's direction, August to November 2026. The lane audit in section 2 was a read-only script over the lane's saved run records.
  - **Who wrote this paper:** Grok Bot, an AI agent, drafted it at Adam King's request on 3 November 2026. It is based on the private repository's audit reports, runbook, decision logs and handoff notes. Every number comes from those records. The drafting agent did not rerun any measurement.
  - **Security edits:** machine names, hostnames, network details, user accounts, internal paths, session identifiers and commit identifiers have been removed or generalized. Code excerpts are lightly edited.
  - **Repository:** private, so it is not linked.
---

## 1. Setting

GenFlick does no CI on hosted runners. Every merge ("landing") and every verification of main ("verify") runs on an operator Mac, a 16-core, 128 GB M4 Max. Many AI coding agents work in parallel on that machine, in several clones, and land their own commits through the lane. The lane:
1. merges the candidate onto main in a check tree,
2. selects the tests the change can affect,
3. runs Vitest unit tests, required PostgreSQL suites, release contracts (`node --test`), a type check and smaller gates,
4. pushes and stores shared per-test impact records with the commit.

Test selection is impact-based. Each Vitest run records, per test file, the inputs it actually read: source files, declaration facts, packages, and keyed rows of prompt tables. A later run selects a test only if a recorded input changed between the record's commit and the candidate. Unknown files run outright. PostgreSQL suites have their own impact store.

This paper has two parts. Section 2 is a read-only audit of where landing time went. Sections 3 and 4 are the selection-side problems the audit and later verifies exposed, with before and after measurements. A companion paper covers sharding the selected tests across other Macs on the network. The two interact: once the tests themselves ran in seconds on idle machines, selection became the critical path.

## 2. Audit: where a landing's time goes

**Data.** We read every saved land run in both lane clones from 28 October 05:44 to 31 October 09:06 UTC 2026, using each run's `status.json` and `timeline.jsonl`. There were 332 runs: 106 ok, 175 failed, 33 interrupted, 15 left "running" and 3 dry runs. Times below are for the 60 successful landings that ran Vitest or PostgreSQL.

| Part of a landing | Median | p90 |
|---|---|---|
| Whole landing (start to pushed) | 23.3 min | 96 min |
| Waiting for a check slot (two slots on one Mac; max 2.8 h) | 4.7 min | 49 min |
| Setup before checks (merge, check tree, scope, planning) | ~2 min | ~3.5 min |
| Vitest (sample: 311 of 3,901 files selected) | 168 s | 605 s |
| Required PostgreSQL (sample: 61 suites ran, 304 carried) | 163 s | 526 s |
| Release contracts (runs alongside) | 129 s | 155 s |
| Type check (native TypeScript 7, warm build-info) | 23 s | 51 s |
| Lock, push and records | 25 s | 3.4 min |

**Findings.**
- **Tests are a minority of the wait.** Tests were about 7 of the median 23 minutes. The rest was queueing, setup and serialization.
- **Serialization.** Vitest and PostgreSQL ran one after the other. Running them side by side has a lower bound of 413 s to 239 s at the median and 1,140 s to 635 s at p90. It is only a lower bound, because two pools on one machine slow each other down.
- **Races with main.** 41 of 106 successful landings (39%) found that main had moved and had to merge and recheck.
- **Failures.** Half of all runs failed (175 of 332), almost all on Vitest (51) or PostgreSQL (52). 47 of 53 Vitest failures involved 1 to 3 files, spread over 263 distinct files. Sorted by cause: 43 regressions, 38 failures from unrelated candidates, 27 flaky PostgreSQL suites, 19 environment problems, and 48 merge conflicts or lane errors. 10 failures passed on a rerun and were reported, not blocking.
- **A silently disabled cache.** In 33 of 56 Vitest landings in the deploy clone (and 10 of 169 in the other), Vitest's transform cache was off, logged as "filesystem cache unavailable (foreign ownership)". There were two causes. First, the machine's reported hostname alternated between two names because no fixed hostname was configured, so the cache's ownership check judged the cache to belong to another machine. Second, Vitest keys transforms by absolute path, and every check tree had a new path. The fix names the owner by hardware identity and runs checks at a fixed path per slot. On the same 30 test files, at host load about 85: 27.6 s with the cache off, 23.3 s on and cold, and 9.8 s on and warm in a new tree at the same path. Nothing had failed, so nobody had noticed.

A note on history: in August 2026 the lane's default ran Vitest as 100 *sequential* `--shard=i/n` invocations, so raising the shard count only multiplied process start-ups. On roughly 1,368 files, one process took about 109 s and 8 shards about 150 s, and 100 shards were estimated at 7 to 10 minutes or more from sampled shards of 3 to 6 s each. The default was cut to 8. In this lane, "sharding" only became parallel once other Macs took shares (companion paper).

## 3. Selection overheads

Once the selected tests ran on otherwise idle Macs in tens of seconds, the time to *choose* them dominated. We found four distinct problems.

### 3.1 A shared cache that each run overwrote

A verify's Vitest check spent **80 s on "read 10,912 source files as declarations"** before running 13 s and 30 s of tests on the runners. The cause was a shared declaration-facts file. Each run overwrote it with only the few facts it had read. The PostgreSQL suites, which save after the unit tests, left a nearly empty file, so the next verify re-read everything. The fix makes a save merge instead of replace. The same change cut one slow contract test from 86.5 s to 53.2 s.

### 3.2 Redundant Git work in the selectors

Three verifies on 3 November showed the PostgreSQL selection spending 73 to 126 s checking its inputs and 269 to 382 s choosing suites, before handing any to a runner. The suites themselves took 30 to 55 s. The unit-test selection took 113 to 146 s. In one verify, at load averages of 300 to 370, the two selections took about 20 minutes together.

We replayed both selections on one check tree with private copies of the shared records, so the replay changed nothing shared. What we found:

- **Repeated Git questions.** The two selectors started 666 Git processes. Only 147 of them asked something different.
- **Repeated diffs.** The declaration judge diffed a record's commit against the head once per test record, and each selection call diffed each record commit again. That came to 406 diffs over 29 distinct commit pairs.
- **Repeated searches.** The PostgreSQL selection searched all of `app/` for readers of the keyed tables four times (two plans, two tables). Each search took about 9 CPU-seconds over about a gigabyte of blobs, so together they were 36 of its 39 CPU-seconds.
- **Scheduler waits.** The tree digest needs only 3 CPU-seconds. It was read on the main thread in awaited batches of eight files, so it waited on the event loop at every open, stat, read and close.

The fixes:

1. **Memoize every read of a commit.** A diff of two commits, a file at a commit and a search of a commit's tree are each asked of Git once per process, keyed by full object ids. Reads of the working tree, the index or refs are never memoized, and neither is a failed read.
2. **Cache keyed-table readers per blob**, next to the records. The cache is invalidated when any `.gitattributes` file changes. A selection searches only blobs it has not seen. When most blobs are new, it searches all of `app/` once.
3. **Plan once.** When no hold is active, the audit's plan is the plan, so the PostgreSQL selection works it out once instead of twice.
4. **Move the tree digest to a worker thread.** It runs beside selection and runner start-up and is awaited only before the first local suite. The bytes hashed and their order are unchanged.

```js
// Illustrative sketch of the memo's contract, not the repository's code.
// Only reads named by full object ids are cached; failures are not.
const memo = new Map();
export function readAtCommit(kind, ...ids) {              // ids are full object ids
  const key = `${kind}\0${ids.join("\0")}`;
  if (!memo.has(key)) memo.set(key, gitRead(kind, ...ids).catch(e => { memo.delete(key); throw e; }));
  return memo.get(key);
}
```

**Results (replay at load 70, one run after the other).**

| | Before | After |
|---|---|---|
| Both selections, wall | 76 s | **34 s** (36 s the first time, while the readers' blobs are searched once) |
| Both selections, CPU | 66 CPU-s | **11 CPU-s** (32 CPU-s the first time) |
| PostgreSQL plan | 45 s | 10 s |
| Unit-test plan | 25 s | 20 s |

The plans were identical before and after for both selectors, and so was the tree digest, compared on the replay.

**First real verify after the change** (load 60 to 80, 3,998 files changed since the newest receipt): the PostgreSQL check had its inputs in 1.5 s and its suites chosen in 44 s. That was every suite, because the commit changed their runner, and the reader blobs were being searched for the first time. The digest was ready before the first local suite started (it waited 0 ms). The network Macs received their shares **49 s after the check started, against 342 to 508 s in the verifies before**.

### 3.3 A pathspec bug that over-selected for three weeks

The unit-test runner looked for readers of the keyed prompt tables using a pathspec relative to `app/`. From inside `app/`, the pathspec `app` named `app/app`, which does not exist. Git found nothing and reported a failure, and the selector treated that as "unknown", the safe default, so it selected every unit test that loaded a prompt table. From 10 October to 3 November, every prompt edit therefore ran all prompt-loading unit tests. The PostgreSQL selector, which asked from the repository root, narrowed correctly the whole time. The fix names paths from the root wherever the search runs and uses the same per-blob cache. On a replay with that day's records: **198 unit-test files instead of 562**, with the PostgreSQL plan unchanged.

The failure mode is worth naming: **a selector whose error path is "select more" is safe but can be wrong for weeks without anyone noticing**, because nothing fails. Only a cost metric shows it.

### 3.4 Load-sensitive tests as false selection blockers

The lane always runs first the files that the last failed run named. Some of those failures came only from the controller's load. A PostgreSQL-backed recording test failed alone on the controller at load 90, and passed alone on an idle runner in 2.9 s (23 tests). Running that list on the freest Mac first, with the controller deciding any failure, stopped one load-induced failure from blocking every later verify (companion paper).

## 4. Keeping impact selection safe: per-file miss holds

Impact selection is a bet that a test whose recorded inputs did not change still passes. The owner set the rule in October 2026. A **miss** is a test that the records would have skipped but that fails in a run that ran every test. Only a *repeatable* miss changes selection, and it changes only what missed:

- **Alone, or it is not a miss.** Each failed file that the records would have skipped is rerun alone. If it fails alone, that is a miss. If it passes alone, it is reported as flaky and selection stays on. What blocks a release does not change: a suite error, or a case that fails alone, still stops the run.
- **Holds are per file.** Missed files run in every run until a run with them passes. Every other record keeps selecting. Only a second miss in another file while one hold is active turns the whole store off.
- **Holds survive contention.** A hold is written under the store's lock. If the lock cannot be taken within two minutes, the hold is journalled next to the store, and every reader folds the journal in at once. An unreadable journal line counts as a hold on every test until a full clean run. If the journal itself cannot be written, the landing stops before it pushes.
- **Holds are visible and expire.** A hold is printed in the logs and the live view, with what lifts it. A hold older than seven days is no longer honoured, and the plan says so.

This replaces an earlier behaviour where any miss turned selection off for everyone. With many agents landing many unrelated changes, that behaviour made every landing pay for one file's instability.

## 5. Discussion

**Selection cost should be measured like test cost.** The lane printed per-test times from the start but did not print selection times. After these fixes, every verify logs `REQUIRED_POSTGRES_SELECTION ms=` and `VITEST_SELECTION ms=`. Three of the four problems in section 3 were invisible to pass/fail monitoring: the overwritten cache, the redundant Git work and the over-selection. Two of the audit's findings were the same kind: the disabled transform cache and the serialized pools.

**Agent-driven workloads make this worse.** When dozens of commits a day each trigger a verify, and the controller runs at load averages of 90 to 370 from other agent sessions, every redundant subprocess is paid for many times over. Memoizing reads of immutable Git objects is cheap and safe, because a diff of two full object ids cannot change.

**What remains.** About four Git processes per record commit are still asked one after another (a diff, its renames, its tree and `package.json`), plus about 4 CPU-seconds of judging. Batching them in one pass, or running selection on an idle Mac that has the records, is the next step.

## 6. Limitations

- **One codebase, one machine.** The numbers come from a single repository and a single heavily loaded controller. Load varied widely, from 17 to over 370.
- **One replay.** The before and after selection comparison is a single replay at load 70, plus one real verify. It is not a controlled benchmark.
- **Lower bounds.** The audit's side-by-side figure is a lower bound, and the cache-off and cache-on landings selected very different file counts, so the cache's effect on whole landings was not measured. Only the 30-file controlled sample was.
- **Counts as logged.** Failure-cause counts come from the audit's classification of saved logs.

## 7. Related work

- **Regression test selection.** File-dependency-based selection is well studied. Ekstazi (Gligoric, Eloussi and Marinov, ISSTA 2015) selects tests by dynamically recorded file dependencies and reports that cheap, coarse dependencies beat finer analyses once the cost of the analysis itself is counted. Our measurements give a field example of that cost argument: here the selector, not the test run, became the bottleneck.
- **Industrial selection.** Google's TAP (Memon et al., ICSE-SEIP 2017) and Meta's predictive test selection (Machalica et al., ICSE-SEIP 2019) select at very large scale on dedicated infrastructure.
- **Tooling.** Vitest's `--changed` selects by import graph against a Git reference, and CircleCI's test impact analysis selects from coverage-derived edges and content hashes.
- **Flaky tests.** Luo et al. (FSE 2014) classify flaky-test root causes. Load-dependent timing failures like the ones in section 3.4 fall into their async-wait and concurrency categories.
- **The trigger for the audit.** A 30 October 2026 engineering write-up by Owen Gretzinger (Boardy) described taking agent-written CI from about 40 minutes to about 2. We did not adopt its recipe wholesale. We used it as a checklist against our own run records, and found the same cache bug it describes.

The contribution here is empirical, not algorithmic. It is a measured account of selection overheads, and of one silent over-selection bug, in an impact-selection lane under heavy agent load, with the fixes and their measured effect.

## 8. Conclusion

In a local CI lane for agent-written code, the tests themselves were only about 7 of a median 23 minutes. Once they were sharded onto idle machines, choosing them became the critical path. Memoizing immutable Git reads, caching blob-level reader searches and taking hashing off the main thread cut selection CPU by about six times (66 to 11 CPU-seconds) with identical plans. Runners started work about 49 s into a check instead of 342 to 508 s. A one-word pathspec bug had silently nearly tripled prompt-edit selections for three weeks. Selection needs its own timing and its own cost alarms, because the safe failure mode, selecting more, never turns a run red.

## References

1. M. Gligoric, L. Eloussi, D. Marinov. Practical regression test selection with dynamic file dependencies. ISSTA 2015. https://doi.org/10.1145/2771783.2771784
2. A. Memon et al. Taming Google-scale continuous testing. ICSE-SEIP 2017. https://doi.org/10.1109/ICSE-SEIP.2017.16
3. M. Machalica, A. Samylkin, M. Porth, S. Chandra. Predictive test selection. ICSE-SEIP 2019. https://doi.org/10.1109/ICSE-SEIP.2019.00018
4. Q. Luo, F. Hariri, L. Eloussi, D. Marinov. An empirical analysis of flaky tests. FSE 2014. https://doi.org/10.1145/2635868.2635920
5. Vitest. Command line interface: --changed and --shard. https://vitest.dev/guide/cli
6. CircleCI. Set up test impact analysis. https://circleci.com/docs/guides/test/set-up-test-impact-analysis/