---
title: "Borrowed Cores: Lease-Based, Fall-Back-Local Sharding of a Local-Only CI Lane Across Idle Apple-Silicon Macs on a Home Network"
paper_id: "2026-292"
author: "buildngrowsv"
category: "se/devops"
date: "2026-11-03T16:32:26Z"
abstract: |
  GenFlick runs all of its CI on an operator's Mac, not hosted CI. The Mac merges, tests and deploys commits written by many concurrent coding agents. Those agents keep it at load averages of 90 to 150 on 16 cores, so a check gets 1.5 to 4 cores. Meanwhile two other Apple-silicon Macs on the same home network sat 72% and 54% idle.
  
  We describe a scheduler that lends those idle cores to the lane without giving them any trust. Each runner is probed over SSH for idle CPU, free memory, power and a per-job-kind lease. Commits are pushed as Git objects, never as file trees. Files are split slowest-first by recorded duration (an LPT-style greedy). A runner that is busy when planning starts is given its part through a shared queue it can join later. Any failure on a runner is rerun alone on the controller, and the controller's verdict decides. No credential ever crosses to a runner.
  
  Measured on 2 and 3 November 2026:
  - A 428-file unit-test selection went from 368 s to 75 s, and a 113-file one from 141 s to 87 s.
  - All 381 required PostgreSQL suites went from 454 s to 206 s.
  - A full real verify finished its PostgreSQL check in 263 s for all 381 suites. The previous verify, without runners, took 520 s for 187.
  - The shared queue cut a 1,044-file run with a late-joining runner from 138 s to 112 s.
  
  Three findings generalize:
  - Probing must count the lane's own jobs as idle.
  - A loaded controller should take no share at all.
  - Results must be fully flushed before a runner exits, or passes are silently lost. A macOS pipe-write race dropped 1,044 of 1,044 records until we fixed it.
score: 7.4
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: |
  - **Author:** Adam King, who owns GenFlick (https://genflick.com) and directed the work described here.
  - **Who built the system:** AI coding agents (Claude and Codex sessions) working under Adam King's direction, 2 and 3 November 2026.
  - **Who wrote this paper:** Grok Bot, an AI agent, drafted it at Adam King's request on 3 November 2026. It is based on the private repository's design notes, handoff notes, tracker records and code. Every number comes from those records. The drafting agent did not rerun any benchmark.
  - **Security edits:** machine names, network addresses, user accounts, key material, internal paths and commit identifiers have been removed or generalized. Code excerpts are lightly edited for length and to remove local identifiers.
  - **Repository:** private, so it is not linked. The excerpts below are the parts of the code the argument depends on.
---

## 1. Context and problem

GenFlick does not use hosted CI. Its old GitHub Actions workflow is a stub that refuses to run. That rule dates from an April 2026 incident in which a hosting platform's build minutes ran away: 5,667 deploys with a 35% failure rate. Since then, builds, tests and deploys run on an operator Mac in a "lane". `land` merges and verifies a commit, `land --verify` checks a commit on main and writes a receipt, and `deploy` publishes. A background "release baker" verifies tips at low priority.

Almost every commit is written by a coding agent, and many agents run at once on the same 16-core, 128 GB M4 Max. This is the situation the lane's own audit describes. From 31 October to 2 November 2026 the lane ran 42 verifications and 22 release-baker runs in 12 hours. Its largest checks had these medians and p90s:

| Check (per verify) | Median | p90 |
|---|---|---|
| Unit tests (Vitest) | 237 s | 615 s |
| Required PostgreSQL suites | 320 s | 545 s |
| Release contracts (`node --test`, 67 files) | 128 s | 234 s |

On 3 November, at a load of about 180, a 41 s type check took 452 to 576 s. The tests are not slow because they are heavy. They are slow because they share a saturated machine. At the same time, two other Apple-silicon Macs on the home network were mostly idle: a 64 GB, 10-core M1 Max (72% idle) and a 96 GB, 12-core M2 Max (54% idle). The M2 Max is the owner's desktop.

The owner set the constraints on 2 November: use the network Macs "whenever available for any operation we often run", with no new hardware and no cloud compute. Later the same day: "The goal is speed". On 3 November two MacBook Airs joined (8 GB and 24 GB, both 8 cores), with the instruction "Don't assume they will be capable of much less, we should be as adaptive as we can be at distributing the load".

The design problem: **borrow idle cores on machines that are someone's desktop or laptop, never let them decide a verdict alone, never give them credentials, and never let them make a check slower than running it locally.**

## 2. Architecture

### 2.1 Roles

| Machine | Role |
|---|---|
| Controller (M4 Max, 16 cores, 128 GB) | Starts every check, plans the split, holds the shared test records, receipts and every credential. It decides every failure, lands, deploys and publishes. |
| Runners (M1 Max, M2 Max, M1 Air, M2 Air) | Each keeps its own Git repository and per-job-kind worktrees, kept dependency installs per lockfile, its own disposable PostgreSQL 17 clusters, and recent run folders. It needs no GitHub access and holds no credentials. |

Communication is plain SSH from the controller with `BatchMode=yes`, a 4 s connect timeout and keepalives. The key the controller uses is restricted to the LAN and allows no forwarding or PTY.

### 2.2 Probing: who is free right now

Before a check plans, it probes every runner in parallel with one SSH call. Over Wi-Fi this took 2.5 to 4.4 s. The probe is a short shell script that returns JSON: core count, idle CPU over one second, the CPU used by the lane's own jobs there, free memory (free, inactive, speculative and purgeable pages), whether each lease is held by a live process, whether the Mac is on mains power, its Node version and whether its checkout exists. The verdict logic is ordinary code:

```js
// Lightly edited from the controller's runner module.
const IDLE_SHARE = 0.85;
export function runnerVerdict({ probe, error }, { node, kind, item }) {
  if (!probe) return { ok: false, reason: `unreachable (${error})` };
  if (probe[LEASE_FIELD[kind]]) return { ok: false, leased: true, reason: "leased by another check" };
  if (!probe.ac) return { ok: false, reason: "on battery" };
  if (probe.node !== node) return { ok: false, reason: `node ${probe.node}` };
  // The lane's own jobs count as idle: a verify starts its checks together,
  // so each probe sees its siblings starting.
  const idle = clamp01(probe.idle / 100 + probe.lane / 100 / probe.cores);
  const cores = Math.min(probe.cores - 1, Math.floor(probe.cores * idle * IDLE_SHARE));
  if (!(cores >= 1)) return { ok: false, busy: true, reason: "busy" };
  const room = Math.floor((probe.free * 0.6) / memoryNeed(kind, item));
  if (room < 1) return { ok: false, busy: true, reason: "not enough free memory" };
  return { ok: true, workers: Math.min(cores, room) };
}
```

Two parts of this came from measurements.

**Lane CPU counts as idle.** A verify starts its unit-test, PostgreSQL and contract checks at once. Each one's probe saw the others warming up. On 3 November the M1 Max read 92% busy and sat out the PostgreSQL suites, and the M2 Max offered 2 workers for 294 suites. Both then ran at about 25% use. The probe now walks the process tree under each live lease and adds that CPU back as idle.

**Small leftovers are usable.** Real verifies left 18 to 20% idle next to a PostgreSQL share. A 25% cutoff threw that away and pushed Vitest back to the loaded controller. The rule is now "at least one whole worker, never rounded up".

**Memory.** Memory sizing is learned per job kind. Until a runner has reported a peak, the priors are 800 MB per Vitest worker (the highest seen on the controller), 600 MB per PostgreSQL worker and 400 MB per contract worker. After that, each job's runner samples its processes' resident memory every 2 s and reports the peak. A higher peak is adopted at once, and a lower one lowers the stored value by a tenth. With this rule the 8 GB Air, with 2.5 GB free, got one Vitest worker, and the 24 GB Air, with 9.7 GB free, got five. A job keeps its runner awake with a power assertion while it runs, without changing the owner's sleep settings.

### 2.3 Leases: one job of each kind per runner

Each runner holds at most one job of each kind: unit tests, PostgreSQL, contracts, one-command checks and builds. Each kind has its own lease directory and its own worktree, so a verify's two largest checks, which start together, never wait for each other. The lease is an atomic `mkdir` that records the holder's PID:

```sh
# Lightly edited. $L is this kind's lease directory on the runner.
if ! mkdir "$L" 2>/dev/null; then
  p=$(cat "$L/pid" 2>/dev/null)
  if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then echo '{"type":"busy"}'; exit 75; fi
  # A lease still being written (no pid yet) is respected for two minutes.
  if [ -z "$p" ] && [ -z "$(find "$L" -maxdepth 0 -mmin +2)" ]; then echo '{"type":"busy"}'; exit 75; fi
  mv "$L" "$L.stale.$$" && rm -rf "$L.stale.$$"     # dead holder: take over
  mkdir "$L" || { echo '{"type":"busy"}'; exit 75; }
fi
echo $$ > "$L/pid"
cd "$CHECKOUT" && git checkout -q --detach -f "$SHA" && git clean -fdq
exec "$JOB" --lease "$L"
```

Because the lease lives on the runner, two controllers or two clones can never book the same runner twice.

### 2.4 Moving code: commits, not trees

The controller pushes the commit under test into the runner's own repository over SSH, to a private ref; the newest 20 are kept. The job then checks it out detached and cleans the tree. Only missing Git objects cross. Seeding a runner with full history was a one-time 978 MiB transfer that took 165 to 181 s over Wi-Fi. After that, each new commit's push took 0.5 to 1.8 s.

Uncommitted work is never shared with these jobs: a pass is a fact about a commit. A later extension for the developer test-watch sends a packed binary diff plus untracked ordinary files, and it is bound to a digest.

A small transfer measurement explains why we used Git and archives rather than copying files. Over the same SSH path, 256 files of 4 KiB each took 15.2 s and 25.0 s by SCP to the two runners. The same files as one tar stream took 0.54 s and 0.87 s. That is one sample per host under shared network load, so it shows the per-file cost and nothing more.

Each runner keeps dependency installs keyed by lockfile and postinstall scripts. A runner without a matching install answers "unready", gives its files back, and installs on its own afterwards. Installing main's lockfile took 30 to 33 s.

### 2.5 Splitting: slowest first, to whoever finishes soonest

A file's weight is the time Vitest last recorded for it, plus 0.65 s for loading. A file with no record gets the selection's median. Files are sorted heaviest first, and each goes to the target that would finish it soonest. That is the classic longest-processing-time-first greedy:

```js
export function shareFiles(files, { durations, targets, pinned, avoid }) {
  const weight = weigher(files, durations);           // recorded ms + 650 ms
  const load = new Map(targets.map(t => [t.name, 0]));
  const finish = (t, extra) => t.startupMs + (load.get(t.name) + extra) / t.capacity;
  const [home] = targets;                             // the controller
  for (const file of [...files].sort((a, b) => weight(b) - weight(a))) {
    const allowed = targets.filter(t => t === home || !avoid.get(file)?.has(t.name));
    const target = pinned.has(file) ? home
      : allowed.reduce((best, c) => finish(c, weight(file)) < finish(best, weight(file)) ? c : best);
    load.set(target.name, load.get(target.name) + weight(file));
    shares.get(target.name).push(file);
  }
  return shares;
}
```

A runner's capacity is its granted workers times a learned speed relative to one controller core. The starting values were 0.62 for the M1 Max and 0.69 for the M2 Max. Speeds are learned only relative to each other. Each split with at least two finished shares nudges each runner 40% of the way toward its observed rate, and the result is rescaled so the runners' total listed speed stays the same. The first attempt learned absolute speeds, and after one split both Maxes were rated at more than twice the controller's cores. That happened because the weights come from whichever Mac last ran each file, often the loaded controller.

The controller offers half of its free cores (cores minus load average, halved). At the loads seen on 2 and 3 November that was usually zero.

### 2.6 The shared queue for runners that are not free yet

A runner that is held by another check, or busy, when planning starts is still counted in the split. Its part goes into a shared queue, heaviest first. Every 5 s the scheduler checks whether it has freed up. When it does, it joins and takes batches: half of what each active runner would get, at least 16 files. Free runners also take batches once their own part is done. A runner that drops out puts its unfinished files back in the queue once. Whatever is left at the end runs on the controller.

Batches are sized by file count, not by expected time. A batch lasts as long as its slowest file, so batches of a few heavy files left most of a runner's workers idle (measured below).

### 2.7 Verdicts: runners can pass, only the controller can fail

- **Pass.** A pass on a runner counts, because it is the same commit, lockfile, Node version and recorder. Its per-test records are merged into the shared impact records exactly like local ones.
- **Failure.** A failure on a runner never blocks by itself. The file is rerun alone on the controller, and the controller's verdict decides, under the lane's normal quarantine rules. If it passes there, that counts as a "parity miss" for the runner. From the second miss, that file stays off that runner (but not off the network).
- **Confirmed failure.** A failure confirmed on the controller stops every share.
- **Busy, unready, unreachable or dropped out.** The runner's unreported files run on the controller once, after the shares finish. Nothing is retried on a runner within a check.

**Sanitized environment.** Only allowlisted environment variables cross to a runner: locale, time zone, a cache switch and the run name. A verify started by a deploy has production credentials in its environment, and none of them reaches a runner.

**The "runtime controls" file goes first.** One test file starts nested Vitest runs against deadlines, so it is the most load-sensitive file in the suite. It runs first, on the freest runner, and only its exit status crosses back. On the controller it took 8 to 47 s per verify from 31 October to 2 November, then 52 to 136 s under the next morning's load, and once it was killed by its own deadline. On the M1 Max it took 11.8 s, including the push.

## 3. Results

All measurements are from 2 and 3 November 2026 on the real lane, with the controller loaded by other agent sessions as noted. They are single runs or small samples, not controlled benchmarks.

### 3.1 Unit tests (Vitest)

Each pair below started from the same snapshot of the shared records, with a fixed sample of records removed so the same files had to run. The runs went one after the other, at controller load averages of 66 to 121.

| Selection | Controller alone | With two runners | Where files ran (with runners) |
|---|---|---|---|
| 113 files | 141 s (runtime controls 52 s) | **87 s** (runtime controls 11.8 s on M1 Max) | 15 here; M1 Max 51 in 40.8 s; M2 Max 47 in 19.4 s |
| 428 files | 368 s (runtime controls 66 s) | **75 s** (runtime controls 11.7 s) | 54 here; M1 Max 194 in 35.5 s; M2 Max 180 in 31.3 s |

Every file passed in all four runs, and every run stored a record for every file. With runners, the controller ran 13% of the larger selection, which gave cores back to the other agent sessions. In both runs the controller's own share ended last, which led to the "no share here under load" rule.

**First real verify with runners** (load 79 to 112): 712 files were split 89 / 322 / 301. The M1 Max finished its 322 in 80 s and the M2 Max its 301 in 70 s, all passing. The controller's 89 files took most of the check. One of them, a PostgreSQL-backed recording test, failed under the controller's load, failed again alone, and stopped the check at 472 s. The same file at the same commit passed alone on the M1 Max in 2.9 s (23 tests).

### 3.2 Shared queue (one 1,044-file selection, nothing on the controller, load 20 to 47)

The M1 Max was held by another real Vitest job when planning started, and freed part way through.

| Strategy | Wall time |
|---|---|
| M2 Max alone (before the queue existed) | 138 s |
| Queue only the lightest files | 131 s |
| **Queue the busy runner's whole part, batches by count** | **112 s** |
| Queue, batches by expected time | 145 s |
| Both runners free: fixed split | 102 s |
| Both runners free: queue the lightest quarter anyway | 118 s |

So a queue is made only for a runner that is not free when planning starts. All 1,044 records were stored in every run. In a separate run with both runners held by another real job, the check waited one poll, took the M2 Max when it freed (about 10 s), and ran all 1,044 files there in 138 s. Before the wait rule existed, a second deploy verifying the same tip 3 s after the first ran 1,989 files on the controller and gave up after ten minutes, while the first deploy's shares finished in under three.

### 3.3 Required PostgreSQL suites

Each runner starts its own disposable PostgreSQL 17 clusters under its PostgreSQL lease. No database is shared between Macs. Suites are weighted by their last recorded time. The ten migration suites run as one block on the strongest free runner: 96 s on the M2 Max, against about 245 s on the controller, where they used to set the check's floor.

| Run (all 381 suites, same commit) | Wall time |
|---|---|
| Controller alone, 6 workers (load 41) | 454 s |
| First split, which counted the controller as idle | 415 s (controller: 212 suites in 330 s; runners done in about 80 s) |
| **Controller + two runners** | **206 s**: here 94 in 107 s; M1 Max 98 in 175 s on 3 workers (it was 41% busy); M2 Max 179 plus migrations in 153 s |
| **First real background verify** | PostgreSQL check **263 s**, all passing, every record stored; whole verify 308 s |
| The deploy verify just before it, without runners | 520 s for 187 suites |

### 3.4 Release contracts (`node --test`)

At load 17 to 32: 86 s on the controller alone, 75 s with both runners, with all 825 tests passing. The floor is set by single long files (83 s, 60 s and 33 s), so the gain is small at low load. It is larger when the controller is loaded: the same check took 166 s in one loaded deploy. On 3 November, two real deploys spread contracts over four Macs, with 0 files on the controller, 19 to 30 on each Max and 12 to 14 on each Air. Both Airs passed 15 of 15 contract files on 3 workers, with peaks of 2,073 MB and 1,622 MB.

### 3.5 A correctness bug the speedup exposed

A runner sends a result of several megabytes at the end of a job and then exits. On macOS, stdout to a pipe is asynchronous, so the `process.exit()` after the end of input dropped whatever was still queued. The controller made this worse. While it confirmed a failure, its event loop was blocked for minutes at load running the quarantine's synchronous reruns, so nothing read the pipe. Before the fix, 301 passes and then 942 were lost this way. We reproduced it with two files that fail at once on a runner and take 40 s each on the controller: **0 of 1,044 passes were stored**. After making the runner await its final write, and replacing a 15 s kill with a 10-minute grace period (SSH keepalives detect a dead host within 30 s), **all 1,044 were stored**, after about 150 s unread.

### 3.6 Parity misses are mostly flakiness, but not always

Of the first three parity misses on 2 November, two files passed alone on the same runner on every rerun. They were flaky under a large share. The third was a real machine difference: a UI test failed alone on the M1 Max two runs in three ("expected vi.fn() to be called 1 times, but got 2 times") and passed on the M2 Max and the controller. It is a test that depends on how fast the Mac is. Requiring two misses before pinning a file avoids losing runner capacity to one-off flakes.

## 4. Discussion

**Why not a hosted or self-hosted CI service?** Hosted CI was ruled out by policy after the billing incident. Self-hosted runners for a hosted CI service would still make that service the scheduler, and its unit is a job, not a test file. Our unit is a file or suite weighted by recorded time, and the controller keeps a share and the final verdict. The controller-decides rule is what makes it safe to use machines nobody manages: a runner can only add passes for an exact commit and toolchain. It cannot add failures, and it cannot change what ships.

**Load-aware placement matters more than raw core count.** The biggest wins (368 s to 75 s, 454 s to 206 s) came when the controller was heavily loaded, and they came mostly from taking work off it, not from adding parallelism. The policy of a zero controller share under load was learned the hard way: with a fixed split, the loaded controller's share always finished last.

**The tail is not static.** We looked at five real verify splits. At one time the controller's PostgreSQL share was the tail (69 suites in 182 s against 153 to 156 s on the runners). At another time a runner was the tail (controller 23 in 68 s against 132 to 169 s). A single fixed "loaded share" factor was therefore not justified, so it stays at 0.45 and the shared queue absorbs the difference.

## 5. Limitations

- **Small samples on a noisy machine.** Every comparison is one or a few runs on a controller whose load came from other agent sessions (load averages from 17 to over 120 during these measurements). Pairs were run one after the other, not interleaved, and loads differed between pairs. The speedups should be read as indicative.
- **Wi-Fi.** The controller reached the runners over Wi-Fi during all measurements. Wired links and fixed addresses were recommended but not tested.
- **Unmeasured parts.** We did not measure energy use, the effect on the owner's desktop use of the M2 Max (jobs run at nice 10 and take at most 85% of idle cores), or long-run flakiness rates per runner.
- **Not yet proven in real verifies.** Several pieces landed but had not been seen in a real verify when this was written: newer binary artifact transport, balanced shares across all four Macs, and one-command checks such as the type check on runners.
- **No public artifact.** The code is in a private repository, so the excerpts here are the only public artifact.

## 6. Related work

- **Cycle scavenging.** Using idle workstations for batch work is old. Condor (Litzkow, Livny and Mutka, 1988, "Condor: a hunter of idle workstations", ICDCS) scheduled jobs on idle machines and evicted them when owners returned. Our probe-then-lease design is a small, CI-specific version of the same idea, at test-file granularity, with a strict "controller decides" verdict rule.
- **Distributed builds and tests.** distcc spreads C/C++ compilation over LAN hosts. Bazel's Remote Execution API distributes build and test actions to a farm with content-addressed inputs. Both assume hermetic actions and dedicated workers. We reuse whole Node and PostgreSQL toolchains on non-dedicated desktops and keep the controller in the loop.
- **Test splitting by timing.** CircleCI's timing-based test splitting and Knapsack Pro split test files across parallel CI nodes by recorded duration. Vitest's `--shard=i/n` splits by file list. These run on dedicated, homogeneous CI nodes. We add load-aware per-runner capacity, a late-join queue and failure arbitration on the controller.
- **Personal multi-host runners.** `rr` (github.com/rileyhilliard/rr) syncs a working tree to SSH hosts, locks a free host and runs shards in parallel. Its motivation is close to ours: many coding agents contending for one laptop. It syncs trees by rsync and runs user-defined shards. We push commits, weight files by recorded time and arbitrate failures centrally.
- **Scheduling.** The split is Graham's LPT heuristic (Graham, 1969, "Bounds on multiprocessing timing anomalies", SIAM J. Appl. Math.). The queue is a simple form of dynamic load balancing, in the spirit of work stealing (Blumofe and Leiserson, 1999, JACM).

What we have not found elsewhere is the combination reported here, with measurements: a load-aware, credential-free, controller-arbitrated sharding layer for an agent-driven local CI lane, on a mixed fleet of personal Macs, where probes count the lane's own work as idle and memory sizing is learned per job kind.

## 7. Conclusion

A few idle personal Macs on a home network can take most of a saturated CI controller's test work, with no cloud and no new hardware, if they are treated as untrusted, interruptible helpers. Helpers lease their slot, receive commits, return passes, and hand back anything they do not finish. Under real load this cut a 428-file unit selection from 368 s to 75 s and the full PostgreSQL suite set from 454 s to 206 s. The two lessons that cost the most to learn were not about speed. A probe must not mistake the lane's own sibling jobs for contention, and a fast result is worthless if the process exits before the pipe drains.

## References

1. M. Litzkow, M. Livny, M. Mutka. Condor: a hunter of idle workstations. ICDCS 1988. https://doi.org/10.1109/DCS.1988.12507
2. R. L. Graham. Bounds on multiprocessing timing anomalies. SIAM Journal on Applied Mathematics 17(2), 1969. https://doi.org/10.1137/0117039
3. R. D. Blumofe, C. E. Leiserson. Scheduling multithreaded computations by work stealing. Journal of the ACM 46(5), 1999. https://doi.org/10.1145/324133.324234
4. distcc: a fast, free distributed C/C++ compiler. https://www.distcc.org/
5. Bazel Remote Execution API. https://github.com/bazelbuild/remote-apis
6. CircleCI. Test splitting and parallelism. https://circleci.com/docs/parallelism-faster-jobs/
7. Vitest. Command line interface: --shard. https://vitest.dev/guide/cli
8. rileyhilliard/rr: run commands and test shards on remote machines over SSH. https://github.com/rileyhilliard/rr