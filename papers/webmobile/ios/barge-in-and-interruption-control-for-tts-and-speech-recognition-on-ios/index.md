---
title: "Barge-In and Interruption Control for TTS and Speech Recognition on iOS"
paper_id: "2026-075"
author: "buildngrowsv"
category: "webmobile/ios"
date: "2026-04-05T14:25:14Z"
abstract: "This case study describes how we stop assistant playback and return to listening when the user interrupts. We combine a dedicated UI action that posts a NotificationCenter event, guards in the speech-recognition pipeline keyed off isSpeaking, and teardown of AVAudioPlayer-based playback so barge-in does not leave half-running engines. The design prioritizes deterministic state over implicit voice-activity detection alone."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Article drafted from repository inspection; commit messages reference interruption milestones."
---

## Motivation

When the assistant speaks, the microphone path must not send user audio to the LLM in a way that duplicates or collides with TTS. Yet users expect **barge-in**: they should be able to cut off playback and speak immediately. On iOS, that tension spans `AVAudioPlayer`, `AVSpeechSynthesizer`, `AVAudioEngine`, and optional WebRTC injectors, so a single boolean is not enough without a consistent event story.

## Mechanisms we used

**Explicit interrupt control.** The call UI exposes an interrupt control that posts a notification when tapped. The call manager observes that notification: if the audio engine is not in a conflicting state, it stops the current player, clears the speaking flag, and schedules speech recognition restart after a short delay so hardware and session settle.

**Speaking gates.** Speech recognition callbacks bail out while `isSpeaking` is true so partial transcripts do not race with assistant output. When playback ends normally, we clear speaking and restart recognition on a delay symmetric to the interrupt path.

**WebRTC-aware stops.** Historical commits reference stopping both TTS and WebRTC-backed audio when the user interrupts. That matters because injection paths can bypass a single player object; interruption logic must reach every active output.

## What we learned

Pure automatic barge-in from the mic is tempting but brittle when assistant audio leaks into the same capture path. Combining **explicit interrupt** with **output-aware stop lists** reduced nondeterministic failures during long sessions.

## Operational notes

Debounce delays after stop are not cosmetic—they reduce `AVAudioSession` transition glitches when flipping between play and record. Tune them per device class if you support older phones.

## Scope

This article covers application-level coordination, not third-party wake-word SDKs. If you add on-device VAD, wire it to the same state machine instead of parallel ad hoc flags.