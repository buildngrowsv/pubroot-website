---
title: "VideoToolbox as a Fail-Closed Media API: M2 Max Encode and Remotion Benchmarks against Cloudflare Containers and Apple Container Machine"
paper_id: "2026-182"
author: "buildngrowsv"
category: "se/performance"
date: "2026-08-25T06:35:42Z"
abstract: "Media APIs often treat Apple hardware encode as an FFmpeg encoder string. We report two dated bakeoffs on one Apple M2 Max (96 GB, Mac14,5) and the fail-closed routing RenderMac ships around them. On 2026-07-22, a sequential (concurrency 1) 20-minute 1080p30 re-encode finished in 95.14 s with h264_videotoolbox at 8 Mbps and 102.79 s with libx264 medium CRF23; the same libx264 job inside Docker --cpus=0.5 --memory=4g took 2371.1 s (MEASURED). Linux guests had no VideoToolbox path. On 2026-07-25, Remotion 4.0.381 HeavyMotion (450 frames, 1920\u00d71080@30, concurrency 4, three measured trials after one warm-up) had a native median of 30.753 s versus 95.018 s on Apple Container machine (3.09\u00d7), 97.668 s on Colima VZ, and 98.168 s on Apple container run (MEASURED). Those Linux guests advertised neither VideoToolbox encoders nor /dev/dri. The shipping product claim is not the wall times: ffmpeg.transcode.v1 defaults to h264_videotoolbox, but the agent probe encodes one lavfi frame rather than parsing --encoders, ANE is hardcoded false, and the matcher will not quote or lease a VideoToolbox transcode unless capability_probes.videotoolbox_hw is true. Scope is these hosts, these dates, and one Cloudflare Containers shape\u2014not a claim that Apple Silicon always wins."
score: 7.2
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

A media API that offers `h264_videotoolbox` is making a hardware claim. Listing the encoder in `ffmpeg -encoders` does not prove a Media Engine session can actually produce a frame. RenderMac treats that gap as a routing bug: `ffmpeg.transcode.v1` defaults `video_codec` to `h264_videotoolbox`, so a device that cannot encode must not appear in the quote cell or receive the lease.

This note reports two MEASURED bakeoffs and the fail-closed probe that the shipping agent and matcher use. It does not argue that Apple Silicon always wins, that a Linux guest will never gain hardware encode, or that a single Mac beats a fan-out service we did not run.

## Encoder lists are not a capability

`FfmpegTranscodeInputSchema` in `packages/shared/src/protocol.ts` allows only `h264_videotoolbox` and `libx264`, and defaults to VideoToolbox. The transcode runner then builds argv from that enum (`-c:v` plus either `-b:v 2M` or `-crf 23`). Buyers never pass an encoder name as a free string.

A second, packaging-only check exists in `scripts/build_native_app.sh`: the ad-hoc Apple Silicon DMG refuses to copy FFmpeg unless `ffmpeg -encoders` contains `h264_videotoolbox`. That is a binary-content gate for the bundle. It is not how a live host proves the encoder works. The runtime probe, below, actually encodes.

## The runtime probe encodes one frame

`packages/agent/src/capabilityProbes.ts` returns `{ videotoolbox_hw, metal, ane }`. On non-Darwin it returns false for VideoToolbox. On Darwin it runs FFmpeg against a generated lavfi source and a null muxer, with a 20 s timeout:

```
ffmpeg -v error -f lavfi -i color=c=black:s=64x64:d=0.05
  -frames:v 1 -c:v h264_videotoolbox -f null -
```

Any non-zero exit is `videotoolbox_hw: false`. The agent does not parse `--encoders`. Metal is a separate, conservative parse of `system_profiler SPDisplaysDataType -json`: both `spdisplays_mtlgpufamilysupport` and `spdisplays_metal` must appear in the JSON text, and invalid JSON is false (`packages/agent/src/hostPolicy.test.ts`). ANE is hardcoded false because the agent has no stable public execution probe; unknown is not advertised.

Quote and lease both consume that boolean. `assessCapacity` appends `videotoolbox_hw` to the capacity cell when `ffmpeg.transcode.v1` requests VideoToolbox (the default codec), then filters devices with `NOT $6 OR COALESCE((capability_probes->>'videotoolbox_hw')::boolean, FALSE)`. The matcher applies the same rule when selecting a queued job for a pulling device: a VideoToolbox transcode is ineligible unless `device.capability_probes?.videotoolbox_hw` is true. An integration test in `packages/control-plane/src/integration/controlPlane.integration.test.ts` inserts one probed and one unprobed device; VideoToolbox capacity reports `eligibleDevices === 1` and a cell ending in `videotoolbox_hw`, software x264 sees both devices, and the unprobed host is offered only the `libx264` job.

## MEASURED 20-minute 1080p30 encode, 2026-07-22

Hardware: Apple M2 Max, 96 GB, Mac14,5 (`MBP14M2Max96GB.lan`). Date stamp `2026-07-22T053512Z` for the native encodes and `2026-07-22T054542Z` for the Cloudflare-shaped Docker job. Concurrency: 1 (sequential `/usr/bin/time -p` wraps). Source: 20 minutes of 1920×1080@30 lavfi `testsrc` (36 000 frames). The ultrafast generate step is scaffolding, not the sellable job (MEASURED 147.8 s on the same M2 Max).

Native FFmpeg (Homebrew on PATH) then re-encoded that file:

| Step (concurrency 1, M2 Max, 2026-07-22) | Wall | Label |
|---|---:|---|
| `h264_videotoolbox` `-b:v 8M`, audio copy | 95.14 s | MEASURED |
| `libx264` medium CRF23, audio copy | 102.79 s | MEASURED |

The cloud contrast used the same libx264 command inside Docker `--cpus=0.5 --memory=4g` on that same Mac, chosen to resemble Cloudflare Containers standard-1 (4 GiB, 0.5 vCPU). MEASURED wall was 2371.1 s. There is no VideoToolbox path in that Linux shape. M1 Air ffmpeg rows were blocked: Homebrew/ffmpeg were missing on SSH PATH; earlier silver logs with `real 0.00` were discarded as invalid.

Versus the same-host Mac x264, the CF-shape job was about 23× slower wall (2371.1 / 102.79). Versus VideoToolbox the ratio is larger, but that comparison is not codec-matched: 8 Mbps hardware H.264 versus CRF23 software x264. The honest paired contrast is Mac x264 versus CF-shape x264; VideoToolbox is the Mac-only extra path.

A published Cloudflare Containers rate card times that 2371.1 s wall gives an upper-bound compute estimate of about $0.0474 (`est_cf_compute_usd_upper` in `ffmpeg-20m-cf-shape-2026-07-22T054542Z/ffmpeg-summary.json`, method `published rates × docker wall`). That is a **rate-card estimate, not a Cloudflare invoice**. We did not read a billing export.

Public table for this bakeoff: [VideoToolbox vs cloud encode](https://rendermac.com/benchmarks/videotoolbox-vs-cloud-encode).

The shipping transcode runner uses `-b:v 2M` for VideoToolbox, not the bench’s 8 Mbps, so product jobs are not claimed to match these 95.14 s.

## MEASURED Remotion native versus four runtimes, 2026-07-25

Hardware: the same Apple M2 Max, 12 logical host CPUs, 96 GB RAM, macOS 26.5.1, Apple `container` CLI 1.1.0. Date: 2026-07-25 (`virtualization-full-2026-07-25`, host `created_utc` 2026-07-25T20:08:50Z). Workload: Remotion 4.0.381, 1920×1080@30, compositions LightMotion (150 frames), MediumMotion (300), HeavyMotion (450). Concurrency: 4 for every runtime. Linux guests: 4 vCPU / 8 GB, one shared ARM64 Debian/Chromium OCI image. Policy: one uncounted LightMotion warm-up, then three measured iterations; medians below. Native used Remotion’s macOS browser; Linux used Chromium in the image, so native-versus-Linux is a combined OS/browser/VM path. The three Linux rows are the cleaner runtime comparison.

![Abstract comparison of one direct native rendering lane with three longer virtualized lanes](https://rendermac.com/assets/benchmarks-virtualization-social.png)

| Runtime (M2 Max, 2026-07-25, concurrency 4) | Light median | Medium median | Heavy median | Heavy vs native |
|---|---:|---:|---:|---:|
| Native macOS | 3.480 s | 7.072 s | 30.753 s | 1.00× |
| Colima Docker / VZ | 11.152 s | 22.303 s | 97.668 s | 3.18× |
| Apple `container run` | 10.864 s | 22.410 s | 98.168 s | 3.19× |
| Apple Container machine | 10.094 s | 21.882 s | 95.018 s | 3.09× |

All 36 measured renders completed with nonempty MP4 outputs (`virtualization-full-2026-07-25/summary.json`). Container machine was the fastest Linux option by a modest margin (HeavyMotion about 2.7% faster than Colima VZ and 3.2% faster than per-container VM) and remained about 3.1× slower than native. Process launch overhead was 0.235 s native, 0.355 s on a warm Container machine, 0.371 s Colima (VM already up), and 1.295 s for Apple per-container VM. Container machine cold-restarted and ran `node --version` in 0.728 s; first local image create-and-boot was 1.179 s. Startup is small next to a 30–100 s render.

The host FFmpeg advertised `h264_videotoolbox`, `hevc_videotoolbox`, and `prores_videotoolbox`. The identical Linux image under Colima, Apple per-container VM, and Container machine advertised no VideoToolbox encoders and had no `/dev/dri`. That is a MEASURED guest-capability result for this configuration, not a prediction about every future Containerization API.

Public table and per-trial listing: [Apple Container machine vs native](https://rendermac.com/benchmarks/apple-container-machine-vs-native).

A separate 2026-07-22 Remotion fleet on the same M2 Max plus two M1 Airs (wall-clock only on the Airs; ffmpeg absent) is not mixed into the 2026-07-25 medians. MEASURED LightMotion there was 3.47 s (M2 Max), 8.78 s and 8.66 s (M1 Airs). Cloudflare Containers live (declared standard → standard-1, 0.5 vCPU / 4 GiB) finished the same LightMotion in 54.12 s and LongKinetic3m (5400 frames / 3:00 output) in 2175.3 s; the M2 Max LongKinetic3m was 111.54 s (concurrency unset in that suite JSON). A 20-minute CF-live LongKinetic row of 14502 s is **PROJECTED** (2175.3 × 20/3), not measured. Remotion Lambda was not run.

## What the numbers change in the scheduler

ADR 0011 keeps launch execution as fixed, signed native services so VideoToolbox remains reachable. ADR 0012 records the 2026-07-25 3.09× HeavyMotion result as evidence for a future host Isolation mode; that mode, the VM supervisor, and a buyer confidential tier are accepted roadmap and are not implemented. `FailClosedMacosVmSupervisor` exists as a typed stub that refuses rather than silently host-sandboxing a job that required a VM, and it is not wired into the agent CLI.

The bakeoff therefore supports a product default, not a universal ranking: keep VideoToolbox transcodes on probed native macOS; do not pretend a 0.5 vCPU x264 container is the same service; do not pay a measured ~3× Remotion penalty for a Linux guest that still lacks the Media Engine in this setup.

## Limits

We do not claim Apple Silicon always wins. Scope is one M2 Max, two M1 Airs for some Remotion walls only, and one Cloudflare Containers shape (live standard-1 and a Docker `--cpus=0.5 --memory=4g` stand-in). We did not run Remotion Lambda, Blender, GPU-cloud H.264, or a temperature-controlled lab. The 2026-07-25 suite used three iterations on an active development Mac; native-versus-Linux mixed browser builds. Apple per-container guests reported five visible processors with a cgroup quota of four CPUs. Encode power was not sampled. Cloudflare dollar figures in the artifacts are rate-card estimates, not invoices; we omit them as costs of record. PROJECTED 20-minute CF Remotion (14502 s) and the incomplete Docker CF-shape LongKinetic3m projection are not used as MEASURED results. Shipping transcode bitrate is 2 Mbps, not the 8 Mbps bench. Packaging still greps `--encoders`; only the live probe encodes a frame. ANE remains false. VM Isolation is not shipping.