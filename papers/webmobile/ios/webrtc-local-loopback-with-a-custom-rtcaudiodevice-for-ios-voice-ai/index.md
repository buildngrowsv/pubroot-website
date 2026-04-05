---
title: "WebRTC Local Loopback with a Custom RTCAudioDevice for iOS Voice AI"
paper_id: "2026-073"
author: "buildngrowsv"
category: "webmobile/ios"
date: "2026-04-05T14:24:35Z"
abstract: "This case study documents how we route synthesized and streamed voice through a local WebRTC loopback on iOS. We use two RTCPeerConnection instances on the same device with empty ICE servers, inject TTS or streamed audio via a custom RTCAudioDevice backed by AVAudioEngine, and disable WebRTC default DSP on the injected track so assistant audio stays clean for testing and tuning. The pattern lets CallKit and the system treat the session like a telephony-quality voice pipe without a remote server."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Article drafted from repository inspection and git history; implementation predates this write-up."
---

## Context and naming

Readers searching for “WebMCP loopback” may land here from adjacent work on browser-side MCP tooling. In our iOS voice stack, the relevant mechanism is **WebRTC** loopback: two local peer connections and a custom audio device, not the WebMCP protocol. Keeping that distinction explicit avoids copying the wrong integration into a mobile codebase.

## What we built

We construct a sender `RTCPeerConnection` and a receiver `RTCPeerConnection` with `RTCConfiguration` ICE servers set to an empty list because all media stays on device. The sender adds an `RTCAudioTrack` sourced from a factory `RTCAudioSource` whose constraints turn off echo cancellation, automatic gain control, noise suppression, high-pass filtering, and typing-noise heuristics. That choice is deliberate: we are injecting assistant speech we already control, and we do not want the stack to fight that signal the way it would fight unpredictable room noise.

Signaling follows the usual offer or answer flow on both peers so the loopback is a real SDP negotiation, not a fake audio tap. When injection is requested and the path is not yet up, we lazily call the loopback setup routine, then push PCM or compressed audio through the custom device so it becomes the track the receiver hears.

## Why it mattered

Native iOS voice products often juggle `AVAudioSession`, CallKit, and playback APIs separately. Feeding audio through WebRTC unifies capture, playout, and buffer timing assumptions with what realtime APIs expect. Git history on our branch shows iterative work from “inject audio file” through full CallManager integration, including interruption handling layered on top.

## Boundaries and risks

Local loopback does not replace security review for real network peers. Empty ICE servers are correct only for on-device testing and production paths that intentionally keep media local. DSP-off constraints are a trade-off: they help TTS fidelity and isolation experiments but are wrong if you need aggressive noise suppression on the same track.

## Reproducibility

Pin a public commit on the supporting repository when you cite behavior. Audio regressions often come from OS session category changes or WebRTC version bumps, so treat the custom device and session configuration as one coupled unit when upgrading dependencies.