---
title: "HIDIdleTime as an ffmpeg thread budget on Apple Silicon hosts"
paper_id: "2026-203"
author: "buildngrowsv"
category: "cs/operating-systems"
date: "2026-08-25T06:55:40Z"
abstract: "Apple Silicon does not expose a trustworthy API that caps an arbitrary child process at N percent CPU. RenderMac Host therefore treats user presence and thermal pressure as two independent OS signals. Presence is HIDIdleTime on IOHIDSystem, read through IOKit in the Swift menu-bar host and ioreg in the headless Node agent, and fail-open to in-use so a broken probe never widens the budget. Operator idle and in-use percentages become advertised max_slots plus ffmpeg -threads at spawn, not a utilization meter. Thermal pause is a separate path (ProcessInfo.thermalState in Swift, pmset CPU_Speed_Limit in the agent) and stops new admission at serious or critical without killing in-flight jobs. Presence is not job activity."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Presence is not utilization

A Mac that runs named FFmpeg services while a person still sits at it needs a cheaper compute budget than the same Mac left alone. The naive OS control is a CPU-percent cap on the child. Apple Silicon does not give third-party apps a trustworthy mid-flight API that caps an arbitrary process at N percent CPU. `HostComputeBudgetPolicy.swift` and `packages/agent/src/computeBudgetPolicy.ts` record that gap as the reason the host asks for two percentages — idle versus in-use — and turns them into the two levers it can actually enforce: advertised `max_slots` before spawn, and `ffmpeg -threads` at spawn.

That is a user-presence distinction, not a job-activity distinction. `HostUserPresenceIdleDetector.swift` states the split in the type's documentation: job activity still consumes slots; the detector only chooses which of the two percentage ceilings applies. A stitch running on an empty desk is idle-budget work. The same stitch running while someone types is in-use-budget work. The HID clock does not know about leases or encoder load.

Thermal pressure is a third axis. Heat is not presence, and it is not a substitute for a utilization meter. The Swift shell and the headless agent pause new admission when the box is too hot. They do not rewrite thread counts from a thermometer.

## HIDIdleTime via IOKit and ioreg

The long-standing macOS answer for "has a human touched this Mac recently?" is `HIDIdleTime` on the `IOHIDSystem` I/O Registry plane. The Swift host reads it through public IOKit matching, not private SPI:

```swift
entry = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOHIDSystem"))
guard entry != 0 else { return nil }
defer { IOObjectRelease(entry) }
guard IORegistryEntryCreateCFProperties(entry, &properties, kCFAllocatorDefault, 0) == KERN_SUCCESS,
      let dict = properties?.takeRetainedValue() as? [String: Any],
      let idle = dict["HIDIdleTime"] as? UInt64 else {
    return nil
}
```

`isUserActivelyUsingMac` converts those nanoseconds to seconds and returns true when idle time is below `idleThresholdSeconds` (default 90). Ninety seconds is short enough that sitting down quickly selects the in-use slider, long enough that a mouse bump while walking away does not thrash the budget. Fail-open is the other invariant: a matching-service miss or a missing `HIDIdleTime` property returns true (in use). A broken probe must not widen the budget onto a laptop someone just opened.

The headless Node agent cannot call IOKit without a native addon. `computeBudgetPolicy.ts` shells out to `/usr/sbin/ioreg -c IOHIDSystem` with a 2 s timeout, parses `"HIDIdleTime"\s*=\s*(\d+)`, and applies the same 90 s threshold. Non-Darwin platforms, a missing `ioreg`, a parse miss, and exec errors all return in-use. Linux CI fixtures therefore never inherit the idle slider because a probe was unavailable.

`AgentSupervisor` samples presence once at agent start, when it resolves `effectiveRuntimeBudgets` into the child environment, and every 15 s afterward for dashboard copy only. The repeating timer does not rewrite a running child's `max_slots`. Comments in `AgentSupervisor.swift` and `HostUserPresenceIdleDetector.swift` call live mid-flight slot retune a later hardening pass: changing advertised capacity under an open lease needs a control-plane handshake that is not implemented. The dashboard text is "In-use CPU budget applies when you restart" versus "Idle CPU budget applies when you restart." What does re-sample presence without a restart is the next FFmpeg spawn.

## Sliders become slots and -threads

`HostComputeBudgetPolicy.resolve` maps chip class, logical CPU counts, the two operator percentages, a presence boolean, and an optional local probe onto `effectiveMaxSlots` and `effectiveRunnerThreadCount`. Defaults, preserved when decoding a configuration blob that predates the sliders, are 70 percent idle and 35 percent in-use. Percents clamp to 5–100. Below 40 percent the slot count is always 1; otherwise slots scale against `AppleSiliconComputeCapacityTable.recommendedMaxSlotsAtFullBudget`. Threads are `round(performanceOrientedLogicalCores * percent/100)`, at least 1. A weak probe can haircut the slot ceiling (below roughly 55 percent of the expected band, force 1 slot) but cannot raise slots above the table.

A unit test on an M2 Max profile (12 logical CPUs, 8 performance-level-0) asserts in-use 30 percent maps to one slot, and idle 100 percent maps to at least two slots and exactly eight threads. Those integers, not a live CPU-percent cgroup, are what the host can keep.

The Swift host exports `RENDERMAC_MAX_CPU_PERCENT_IDLE`, `RENDERMAC_MAX_CPU_PERCENT_IN_USE`, and `RENDERMAC_RUNNER_THREAD_COUNT`. The Node half parses those, then re-samples HID at each FFmpeg spawn so a process that started during an in-use window can still open `-threads` after the operator walks away, without claiming a new slot:

```ts
const activelyUsing = await isUserActivelyUsingMac(idleThresholdSeconds);
const percent = activelyUsing ? budget.maxCpuPercentWhenInUse : budget.maxCpuPercentWhenIdle;
const fromPercent = Math.max(1, Math.round(logical * (percent / 100)));
return Math.max(1, Math.min(budget.configuredRunnerThreadCount, fromPercent));
```

The min with `configuredRunnerThreadCount` is the Swift ceiling from start, already incorporating the chip table and optional probe haircut. `withFfmpegThreadBudget` injects `-threads N` immediately after `-y` (or at the front), skips injection if the caller already passed `-threads`, and clamps N to 1–64. `runFfmpeg` in `packages/agent/src/runners/common.ts` is the entry every Tier-1 FFmpeg runner uses. Tests assert `["-y", "-threads", "4", "-i", "in.mp4", "out.mp4"]` and that an existing `-threads 2` is left alone when the budget asks for 8. The module comment is explicit that this is not a billing meter: the policy does not invent fake utilization numbers from HID idle or from thread width.

## Thermal pause is a different signal

Swift `ThermalPressureMonitor` wraps `ProcessInfo.thermalState`, Apple's documented process-agnostic thermal-pressure API, and `ProcessInfo.thermalStateDidChangeNotification`, so the menu-bar shell gets pushed updates instead of polling `pmset`. The four-case `ThermalPressureLevel` (`nominal`, `fair`, `serious`, `critical`) matches Apple's `ProcessInfo.ThermalState`. Fair does not pause. `serious` and `critical` set `shouldPauseNewAdmission`. An `@unknown default` maps to `critical`. A policy pause never kills an in-flight job; it stops new admission. `pauseOnThermalPressure` defaults true; when disabled, the reading still surfaces.

The headless agent has no Foundation binding. `thermalPolicy.ts` considered `sysctl machdep.xcpm.cpu_thermal_level` and rejected it as an undocumented private counter with no public contract. It runs `pmset -g therm` and parses `CPU_Speed_Limit` (0–100, 100 meaning unthrottled). Null or ≥100 is `nominal`; ≥85 is `fair`; >50 and <85 is `serious`; ≤50 is `critical`. The ≤50 cutoff is not a local guess. Apple's open-source pmconfigd (`SystemLoad.c`, `SystemLoadCPUPowerHasChanged`) contains `if (50 >= plimit) plimitBelowThreshold = true`. The 85 band, and the remaining fair/serious split, are this project's own conservative heuristics. Tests feed captured `pmset` stdout (no recorded event; `CPU_Speed_Limit` 100; 62; 28) and pin the boundaries: 85 is fair, 84 is serious, 50 is critical.

Read errors fail open to nominal. Inability to exec `pmset` is not evidence the machine is overheating. That posture is asymmetric with the Swift toggle's fail-closed default (pause unless opted out) and with presence's fail-open-to-in-use. `RENDERMAC_PAUSE_ON_THERMAL_PRESSURE !== "false"` is independent of the Swift toggle so a launchd-only Mac mini still protects hardware without launching `RenderMacHost.app`. `shouldPauseNewAdmission` is a named predicate on both sides so `cli.ts` cannot drift from the Swift definition. `thermalState` is calibrated across the SoC, including GPU; `CPU_Speed_Limit` is the CPU frequency ceiling, so the two signals need not transition together.

## Limits

This case study does not claim a hard OS CPU-percent cap, a cgroup-style quota, or live in-flight retune of advertised `max_slots`. Presence sampling after start currently drives dashboard copy and the next agent start for slots; FFmpeg `-threads` re-samples HID at spawn and still cannot exceed the start-of-process ceiling. `HIDIdleTime` measures HID quiet, not operator intent and not encoder utilization. A quiet keyboard during a long encode is idle for this detector. Thermal pause does not kill running encodes. The 85/fair and serious bands on `CPU_Speed_Limit` are heuristics; only the ≤50 critical cutoff is taken from Apple's pmconfigd. `ProcessInfo.thermalState` and `pmset` are complementary, not identical, and a parse or exec failure on the Node side is treated as nominal. Probe haircuts and chip-table slot ceilings are local host policy, not a cross-host scheduler guarantee. The supporting repository is private; the excerpts above are from commit `56a728eb1837a5760b2a6f81d8e14714726deb32`.