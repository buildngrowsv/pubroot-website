---
title: "CallKit Incoming Call Simulation for Real-Time Voice Sessions"
paper_id: "2026-074"
author: "buildngrowsv"
category: "webmobile/ios"
date: "2026-04-05T14:26:27Z"
abstract: "This case study explains how we use CXProvider reportNewIncomingCall to surface a Personal AI session as an incoming call when CallKit is enabled, while allowing a non-CallKit path for development. Pairing that UX with the WebRTC audio route gives users the familiar phone-call affordances\u2014lock screen, routing controls, and interruption semantics\u2014while the assistant audio still flows through the loopback and custom device stack described in sibling work."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Article drafted from repository inspection and git history."
---

## Problem

Voice assistants that only use in-app playback can feel unlike a “call,” and iOS may treat audio sessions differently from telephony. For a product positioned as a personal AI phone companion, we wanted the **incoming call** metaphor when it helps adoption, without forcing every build configuration through CallKit during early WebRTC bring-up.

## What we implemented

When the selected voice mode corresponds to the real-time API and CallKit is on, we build a `CXCallUpdate` with a generic handle string and report a new incoming call to the system provider. That triggers the native incoming-call UI the user expects. When CallKit is off, we still mark the session active in app state so engineering builds can iterate without provider plumbing.

The real-time branch short-circuits other conversation bootstrap paths: timers, Firebase logging, and scripted conversation steps behave differently from the standard LLM-plus-TTS loop. Documenting that fork matters because telemetry and QA scenarios diverge.

## Relation to WebRTC loopback

CallKit does not replace audio routing by itself. Our WebRTC loopback and `RTCAudioDevice` implementation carry the actual assistant audio. CallKit primarily shapes **lifecycle and system integration**: what the user sees, how interruptions interleave, and how the session competes with cellular or VoIP peers.

## Git history signal

Repository history shows merges from `webrtc-migration-attempt` branches and commits noting “Call is working with new method,” reflecting incremental validation rather than a single big-bang rewrite. Teams adopting a similar pattern should expect the same phased rollout.

## Caveats

CallKit APIs carry App Store and capability requirements. Test both orientations—CallKit on and off—because QA coverage often clusters on one path. Privacy copy should state clearly when a session is “call-like” UI versus a true PSTN or VoIP peer.

## Takeaway

If your voice product benefits from telephony affordances, reporting an incoming call can be a pragmatic bridge while you still own the entire media plane through WebRTC on device.