---
title: "A Hybrid Local-and-Cloud Stack for Agentic Voice on iOS (Accountability Personal AI)"
paper_id: "2026-082"
author: "buildngrowsv"
category: "webmobile/ios"
date: "2026-04-05T14:34:24Z"
abstract: "This case study maps how the Accountability iOS app combines on-device speech capture and session routing with cloud LLMs and multiple TTS backends. We document VoiceType modes (local AVSpeech through OpenAI Realtime), WebRTC loopback with CallKit, and where intelligence lives versus where media is synthesized\u2014without claiming a single named hybrid flag exists in source control."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Drafted from static code review; no separate design memo was found that states product-level naming or roadmap for hybrid voice."
---

## Evidence versus inference

**What we can point to in the repository:** `CallManager` orchestrates calls, Apple `SFSpeechRecognizer` with `AVAudioEngine` for buffering, `VoiceType` encoded in the last character of `voiceId` (local, premium, GPT, Google, custom, real-time), optional WebRTC injection and CallKit reporting, and remote LLM calls through `ConversationManager` / `APIClient` to OpenAI and Anthropic models. TTS paths include `AVSpeechSynthesizer`, `DeepgramService`, and other vendor flows referenced from the speech selector stack. A Firebase-backed control document supplies remote timing thresholds used during turn-taking (covered in the companion article on timers).

**What we did not find:** A dated architecture decision record, RFC, or team chat export in this repo that says “we chose hybrid because …” **Inference below is structural**—it explains how components compose, not a verified quote of product intent.

## Layers of the hybrid

**Local perception and session.** Speech-to-text runs on device via Apple’s framework, with taps on the audio engine and partial results feeding `latestTranscription`. While the assistant is marked as speaking, recognition is gated off to avoid feedback loops. That is classic **local capture + cloud semantics**: the expensive language model is not on the phone, but the microphone path and echo avoidance are.

**Cloud cognition.** User text is appended to `conversationHistory` and sent through `ConversationManager.processStep` to GPT or Claude APIs depending on stored model selection. Agentic behavior (scripted steps, pros/cons mode, summarization) is implemented around that same history object.

**Polyglot output.** Voice mode selects among several backends (including on-device synthesis for `.local` and vendor APIs for neural voices). Real-time voice uses a dedicated branch: when `VoiceType` resolves to `.realTime`, incoming-call reporting and the realtime client dependency indicate a **separate** media and signaling path from the LLM-plus-TTS loop. That split is itself a hybrid: one pipeline for batch-style LLM+TTS steps, another for streaming realtime audio.

**Transport and telephony feel.** WebRTC loopback with a custom `RTCAudioDevice` routes synthesized audio through a peer-to-peer-shaped pipe on device; CallKit can present the session as a call. That is local media plumbing with **no** requirement that the LLM run locally.

## Why “hybrid” is a fair label

No single `isHybrid` boolean appears, but the architecture consistently **splits responsibilities**: Apple handles capture and permissions-sensitive audio; vendors handle generation at scale; Firebase can tune timing without shipping a new binary. That is hybrid agentic voice in the operational sense.

## Boundaries

Vendor APIs, pricing, and privacy commitments change independently of this code snapshot. Realtime mode has different failure modes than REST LLM calls; operators should test both. If you cite this article, pin the commit SHA in the supporting repository.