---
title: "Turn-Taking with Staggered Timers and Apple Speech Partial Results"
paper_id: "2026-076"
author: "buildngrowsv"
category: "webmobile/ios"
date: "2026-04-05T14:27:05Z"
abstract: "This case study outlines our end-of-utterance and pipeline staging strategy on iOS using SFSpeechRecognizer with partial results plus a small fleet of one-shot timers for LLM invocation, TTS preparation, and playback. Silence resets re-arm the chain so bursty speech does not trigger premature model calls. The pattern is pragmatic for on-device speech where you want control without shipping a separate cloud VAD."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Article drafted from repository inspection; timer defaults may be tuned via remote control panel in app."
---

## Role of partial results

We enable `shouldReportPartialResults` on the speech request so `latestTranscription` updates continuously. That gives responsive UI text but would spam the LLM if we forwarded every delta. Instead, we treat partials as activity that **resets a silence window**, not as direct model input.

## Timer ladder

When transcription content changes, we invalidate prior timers and schedule three staggered one-shot timers with defaults near half a second for LLM start, longer for TTS staging, and a final gate before playout. Remote configuration can adjust those intervals without shipping a new binary—useful when marketing wants snappier replies or engineering needs fewer partial-triggered cancellations.

The ladder effectively approximates **turn detection**: the user’s pause must outlast the LLM timer before we commit text and call upstream. This is not a neural endpointing model; it is honest, tunable heuristics paired with Apple’s recognizer.

## Interaction with speaking state

While the assistant is speaking, recognition is suppressed. Timer logic and interruption handling must agree on when to re-enter listening; mismatches here show up as “double answers” or missed user input in QA.

## Trade-offs

Shorter timers feel faster but increase false triggers on thinking pauses. Longer timers feel sluggish. Expose sane bounds in internal tooling and log timer fires when debugging production clips.

## Relation to WebRTC

When assistant audio routes through WebRTC injection, the same timer and partial-result layer still gates the LLM; only the playback backend changes. Keeping turn-taking above the transport layer preserved our sanity across migrations visible in git history.

## Closing

For teams shipping voice without a dedicated cloud endpointing API, staggered timers plus partial results are a maintainable baseline—provided you document the defaults and test across Bluetooth and speaker routes.