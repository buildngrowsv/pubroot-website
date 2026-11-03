---
title: "Splitting a 24,000-Page Static Site Build Across Home-Network Macs: Hash-Range Page Shares, Cross-Machine Byte Identity, and Copy-on-Write Assembly"
paper_id: "2026-294"
author: "buildngrowsv"
category: "se/performance"
date: "2026-11-03T16:33:48Z"
abstract: |
  GenFlick's public marketing site is a statically rendered React Server Components site of 24,084 pages (24,744 output files) in many languages. It is built by Vite with an RSC plugin. When the build machine is idle, the build takes about 90 s: 26 s bundling and 61 s rendering. But the build runs inside a local release lane on an operator Mac that many coding agents keep heavily loaded, and there a single site build was recorded at 547 s.
  
  We describe how the build was split across other Apple-silicon Macs on the same home network:
  - Each share re-runs the cheap bundle step and renders only the pages whose 32-bit address hash falls in its range.
  - Share sizes come from a closed-form split that accounts for the work every share repeats.
  - A strict completeness check makes the controller fall back to a whole local build if the shares disagree.
  - The result is assembled from one APFS copy-on-write clone of the previous build plus the files that changed.
  
  Two engineering problems mattered more than the scheduling:
  - **Byte identity across machines.** The RSC plugin named client references by a path that included each machine's linked dependency directory, so a build on another Mac rewrote 24,205 of 24,744 files. One Vite option fixed it.
  - **Assembly cost.** Cloning the 24,744-file directory with one `clonefile(2)` call took 2.5 s, against 50 s for per-file copy-on-write copies.
  
  In the one real run reported, a comment-only change, two runners rendered 13,216 and 10,868 pages in 80 s and 87 s. Only 36 changed files (1.6 MB) crossed the network, assembly took 5.4 s, and the unit build took 98 s. A single-runner build took 210 s, and the earlier local build 547 s.
score: 7.8
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: |
  - **Author:** Adam King, who owns GenFlick (https://genflick.com) and directed the work.
  - **Who built the system:** AI coding agents (Claude and Codex sessions) working under Adam King's direction, 2 and 3 November 2026.
  - **Who wrote this paper:** Grok Bot, an AI agent, drafted it at Adam King's request on 3 November 2026. It is based on the private repository's code, tracker records and runbook. Every number comes from those records. The drafting agent did not rerun any build.
  - **Security edits:** machine names, network details, user accounts, internal paths and commit identifiers have been removed or generalized. Code excerpts are lightly edited for length.
  - **Repository:** private, so it is not linked.
---

## 1. Problem

GenFlick runs builds, tests and deploys on an operator Mac (a 16-core M4 Max) rather than on hosted CI. Many AI coding agents share that machine. On 3 November 2026 its load averages ranged from about 180 to 280. A deploy builds several "units": the static marketing site, an app bundle and five API Workers. Each unit is cached by an input hash, so a unit is rebuilt only when its inputs change.

The site is the largest unit: 24,084 rendered pages and 24,744 output files. Measured on an idle controller, a site build is about 90 s, with 26 s of bundling and 61 s of rendering (plus 16 s of read-only checks before the split work described here). Under the lane's real load, a site build took 169 s on the morning of 2 November and 547 s in the last recorded build before the split (the tracker does not record that run's load). The same lane already shared tests with other Macs on the home network (an M1 Max, an M2 Max and two MacBook Airs; see the companion paper on test sharding). The question was whether a build, which produces one artifact rather than many independent verdicts, could be shared the same way, safely and with output identical to a local build.

Constraints:
- No credentials or private environment files may reach a runner.
- Publication stays on the controller.
- Any failure falls back to a normal local build.

## 2. Design

### 2.1 What a share does

The site generator lists every page address. A share is a half-open range `{from, to}` of a 32-bit hash space (`0 ≤ from < to ≤ 2^32`). A share renders only the pages whose address hash falls in its range, into its own pages directory. Every share repeats the bundle step, because it is cheap compared with rendering and repeating it avoids shipping the bundle between machines. Only the share that starts at 0 also writes what a build writes once: the browser asset files, the 404 page and the policy documents. Each share writes a small report of what all shares must agree on: the browser files, their content keys and the full address list.

```js
// Lightly edited from the shared artifact module.
export const SHARE_SPACE = 2 ** 32;
export const validShare = (share) => share === undefined || (
  share !== null && typeof share === "object" && Object.keys(share).join() === "from,to" &&
  Number.isSafeInteger(share.from) && Number.isSafeInteger(share.to) &&
  share.from >= 0 && share.from < share.to && share.to <= SHARE_SPACE);
```

Hashing addresses, rather than splitting the list by index, spreads heavy page families (one language, one tool directory) across shares. It also keeps a page's share stable when unrelated pages are added.

### 2.2 How big each share is

Each machine *i* has an expected whole-build time *mᵢ*, kept from earlier builds. A fraction *r* of the work is repeated by every share (the bundle step). If machine *i* takes fraction *fᵢ* of the pages, it finishes at:

  *Tᵢ = mᵢ·r + mᵢ·(1 − r)·fᵢ*

Setting every *Tᵢ* equal to a common end time *T* and requiring Σ*fᵢ* = 1 gives a closed form. Any machine whose fraction comes out below 10% is dropped, and the split is solved again:

```js
const MIN_SHARE = 0.1;
export function splitShares(places, repeated) {      // places: [{ name, ms }]
  let chosen = places.filter(p => Number.isFinite(p.ms) && p.ms > 0);
  for (;;) {
    const fixed = p => p.ms * repeated, rest = p => p.ms * (1 - repeated);
    const endMs = (1 + chosen.reduce((s, p) => s + fixed(p) / rest(p), 0))
                / chosen.reduce((s, p) => s + 1 / rest(p), 0);
    const shares = chosen.map(p => ({ name: p.name, fraction: (endMs - fixed(p)) / rest(p) }));
    const smallest = shares.reduce((lo, s) => (s.fraction < lo.fraction ? s : lo), shares[0]);
    if (chosen.length <= 1 || smallest.fraction >= MIN_SHARE) return { shares, endMs };
    chosen = chosen.filter(p => p.name !== smallest.name);
  }
}
```

The controller is counted at half its free cores, so a heavily loaded controller drops out of the split by itself. Whole-build times are stored per machine, and a share's time is stored as the equivalent whole-build time, so later splits keep learning.

### 2.3 Running a share on a runner

A build share takes a build lease and a build checkout of its own on the runner, so it never waits behind a test job. It works like this:
- The commit is pushed as Git objects.
- The runner recomputes the unit's input hash and refuses to build if it does not match.
- It builds with only OS runtime variables and committed public configuration, and rejects private environment files.
- It returns one gzip tar archive, bound to unit, commit, hash and share, as a binary stream over SSH, next to a small control session.
- It sends only files whose content the controller does not already have. The controller sends the content hashes of its previous build of the unit (`have`).

On the controller, the archive's digest, size, identity (including the share) and file list are checked before anything is extracted. Only listed ordinary files are accepted. A share that is given back, because its runner was busy, unready or failed, is built locally.

### 2.4 Putting the shares together safely

Before assembling, the controller requires all of the following:
- every share reports the same browser files, the same content keys and the same address list,
- the shares' pages add up to exactly that address list,
- no file is written by two shares,
- the assembled directory holds every file a complete build writes.

If any check fails, the whole site builds locally. The log records the split, one line per share, and the assembly.

### 2.5 Assembly by copy-on-write directory clone

The new build is usually mostly identical to the previous one. So assembly starts from one copy-on-write clone of the previous build's whole directory, removes the files that changed or disappeared, and extracts or moves in the files the shares produced. Node exposes no directory-level `clonefile(2)`, so the controller calls it through the JavaScript-for-Automation bridge that ships with macOS:

```js
function cloneDirectory(source, destination) {        // destination must not exist
  if (process.platform !== "darwin") return false;
  const r = spawnSync("osascript", ["-l", "JavaScript", "-e",
    'function run(argv){ObjC.bindFunction("clonefile",["int",["char *","char *","int"]]);' +
    'return $.clonefile(argv[0],argv[1],0)}', source, destination],
    { encoding: "utf8", timeout: 120_000 });
  return r.status === 0 && r.stdout.trim() === "0";
}
```

The clone is used only when at least half of the files are unchanged at the same path. When nearly everything changed, deleting the stale files costs more than copying the kept ones. Without a clone, assembly falls back to per-file `copyFileSync(..., COPYFILE_FICLONE)`. Afterwards every file is checked: it must be listed, it must be an ordinary file, and it must either have been written by a share or carry the same content hash as in the base build.

## 3. The problem that had to be solved first: byte identity across Macs

The first remote site build "worked", but it sent 24,205 of 24,744 files against a build made on the controller from the same commit. Almost every page and every browser asset had a different name.

The cause was naming in the React Server Components plugin. It names each client reference by its path from the app folder. On the controller, check trees and runner checkouts link `node_modules` from a dependency install kept elsewhere, and Vite resolved those symlinks. The *install's* location therefore became part of every client-reference name, and every keyed browser file and every page that referenced one changed. Setting `resolve.preserveSymlinks` in the site's Vite configuration makes names depend only on the repository-relative path. After that, a runner's build of an unchanged page is byte-identical to the controller's, which is what makes both the "send only what changed" transfer and the clone-based assembly worthwhile.

This is a general hazard for distributed or cached builds of bundler output. Content-hashed names are only as stable as the inputs to the hash, and an absolute or install-relative path is an input that differs from machine to machine.

## 4. Results

The tracker records one real split build. It was a comment-only change, built on the two Max runners, with the controller counted at half its free cores and taking no share:

| Measure | Value |
|---|---|
| M2 Max share | 13,216 pages in 80 s |
| M1 Max share | 10,868 pages in 87 s |
| Pages total | 24,084 (all addresses covered) |
| Files sent back | 36 (1.6 MB) |
| Assembly from one APFS directory clone | 5.4 s |
| **Site unit build, two runners** | **98 s** |
| Site unit build, one runner (earlier run) | 210 s |
| Site unit build before the split (load not recorded) | 547 s |

Assembly micro-measurements (controller, 24,744 files):

| Method | Time |
|---|---|
| One `clonefile(2)` of the directory (load 38) | **2.5 s** |
| One `copyFileSync` copy-on-write clone per file | 50 s |
| Per-file clones inside the deploy proof run | 56 s |

A smaller change in the same work also helped. Two read-only checks that used to run before the site build (saved localization and a product-naming guard) now run at the same time as the page generation, in the share that starts at 0. They had taken the first 19 s of a 109 s build.

Earlier in the same program, the app bundle was built on a runner and applied to the controller's unit cache: a 44 MB, 961-file artifact, with 13.4 s on the runner and an 18 s unit build.

## 5. Discussion

**Why split rendering and not bundling?** Rendering was two thirds of an idle build and scales with page count. Bundling is a fixed cost that every share can afford to repeat. The closed-form split accounts for that repeated part directly, rather than assuming perfect scaling.

**Why fall back to a whole build instead of patching?** A site that is mostly right is worse than one built slowly. The agreement checks (browser files, keys, address list, page count, no overlaps, required files) are cheap, and when they fail the result is a normal local build, never a partial site.

**Most of the measured gain is avoided contention.** The controller's 547 s, against about 90 s on an idle machine, is most likely load from other agent sessions, though that run's load was not recorded. Two runners finishing in 80 to 87 s is close to the idle single-machine time divided between them, plus the repeated bundle. The split helps most when the controller is busy, which in this lane is most of the time.

## 6. Limitations

- **One real split.** The two-runner result is a single run of a comment-only change. A change that touches many pages would send more files and gain less from the clone.
- **Unknown baseline load.** The 547 s and 210 s comparisons come from different runs, and the controller's load during them was not recorded in the tracker entry.
- **Cold builds not measured.** We did not measure a cold first build on a runner, or the Air runners for this unit (the memory prior for a site build is 6 GB, which excludes the 8 GB Air).
- **Not yet proven end to end.** Real cache-apply proof of the site through the newest binary transport, and a same-commit local comparison, were deferred when this was written.
- **macOS only.** The clone path depends on macOS and APFS. Elsewhere it falls back to per-file copies.

## 7. Related work

- **Distributed builds.** Distributed build systems such as Bazel's Remote Execution API and distcc distribute compile actions with content-addressed inputs.
- **Static site builds.** Static site generators usually parallelize page rendering across threads on one machine, and incremental deploy tooling often relies on content-hashed asset names and build manifests to upload only changed files.
- **Reproducible builds.** The Reproducible Builds project documents build-path leakage (an absolute or build-directory path ending up in outputs) as a classic source of non-determinism. Section 3 is an instance of it in a JavaScript bundler, caused by symlinked dependency installs rather than by the build directory itself.
- **Copy-on-write.** Apple documents `clonefile(2)` for copy-on-write clones of files and directory hierarchies on APFS.

We found no published account of splitting one static-site render across heterogeneous machines by hashed page address, with a repeated-work-aware split, cross-machine byte-identity checks and copy-on-write assembly. We report it as an engineering case study, not as a general system.

## 8. Conclusion

Sharing a build across home-network Macs is mostly about making the output identical, not about scheduling. Once a single Vite option removed install paths from asset names, page-hash shares from two runners could be checked, merged into a copy-on-write clone in seconds, and published from the controller exactly as a local build would be. In the one real run, the site unit went from 547 s on the loaded controller to 98 s, with 36 changed files crossing the network.

## References

1. Bazel Remote Execution API. https://github.com/bazelbuild/remote-apis
2. distcc: a fast, free distributed C/C++ compiler. https://www.distcc.org/
3. Reproducible Builds: build path. https://reproducible-builds.org/docs/build-path/
4. Apple. clonefile(2), macOS manual page. https://keith.github.io/xcode-man-pages/clonefile.2.html
5. Vite. Shared options: resolve.preserveSymlinks. https://vite.dev/config/shared-options#resolve-preservesymlinks
6. R. L. Graham. Bounds on multiprocessing timing anomalies. SIAM J. Appl. Math. 17(2), 1969. https://doi.org/10.1137/0117039