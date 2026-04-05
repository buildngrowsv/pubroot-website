---
title: "Staggered Timer Ladder and Firebase Control Panel in the Accountability Voice Pipeline"
paper_id: "2026-083"
author: "buildngrowsv"
category: "webmobile/ios"
date: "2026-04-05T14:34:57Z"
abstract: "This case study documents the three-stage timer system used after speech partials arrive on iOS: defaults for LLM delay, TTS staging, and playout scheduling, with Firestore-backed overrides. We explain how resetSilenceTimer debounces user input, how async LLM completion interacts with isLLMTimerFinished, and why remote thresholds matter for tuning latency without App Store releases. Product rationale is inferred from code structure; no ADR was found in-repo."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Drafted from TimerManager, CallManager.resetSilenceTimer, FirebaseManager.getControlPanel, and ControlPanelModel in the cited commit."
---

## What the code actually does

`TimerManager` owns three optional `Timer` references named for pipeline phases: **llmTime**, **ttsTime**, and **playTime**. Inline comments in that file give default hints—approximately half a second before kicking off LLM work, one and a half seconds before TTS handoff, and two seconds before scheduled playout—while **runtime intervals** come from `ControlPanelModel` when Firebase returns data.

`CallManager.resetSilenceTimer` is invoked when speech recognition produces non-empty partial text. It first invalidates all three timers, then schedules new one-shot timers whose intervals are `timerManager.controlPanel?.llmTime ?? 0.5`, `?.ttsTime ?? 1.5`, and `?.playTime ?? 2` respectively. Each new partial utterance resets the chain, which implements **debounced end-of-utterance** behavior: the user must pause long enough for the LLM timer to fire without fresh partials resetting it.

## Firebase control panel

`FirebaseManager.getControlPanel` reads document `controlpanel/processingThreshold` and maps fields `LLMTime`, `TTSTime`, `PlayTime`, and `ExpirationTime` into `ControlPanelModel`. If the fetch fails or fields are missing, the hard-coded defaults above apply. **Why this matters:** thresholds can be adjusted server-side to shorten perceived latency or reduce premature LLM triggers during field trials, without waiting for Apple review—assuming the team maintains that Firestore document.

## Coordinating async LLM with timers

`startLLMProccess` pushes user text into history and calls `generateNextQuestion`. When the LLM returns, the completion checks `timerManager.isLLMTimerFinished`. If the TTS-stage timer has already fired, it speaks immediately; otherwise it stores the string in `timerManager.LLMResult` so the **ttsTime** callback can call `startSpeaking` when the staged delay elapses. That pattern absorbs variance in network RTT: fast responses wait for the timer boundary; slow responses can still align with the ladder depending on arrival order.

The **playTime** branch stops speech recognition before playout and delays audio slightly—matching the need to tear down the recognition tap before assistant audio plays through the same session.

## Why this design was likely chosen (inference only)

The repository does **not** contain meeting notes or a narrative “we picked staggered timers because …” **Plausible engineering reasons visible from structure** include: (1) **separating concerns**—endpointing heuristics, model latency, and TTS generation are different subsystems; (2) **operational tuning** via Firestore; (3) **avoiding a single monolithic delay** that would feel sluggish on fast networks or trigger early on slow ones. Treat these as hypotheses consistent with the code, not attributed quotes.

## Caveats

Timer ordering assumes `Timer.scheduledTimer` callbacks run on the expected run loop; heavy main-thread work can skew real wall-clock spacing. The `ExpirationTime` field is loaded into the model but its consumer should be verified when extending the pipeline. Document any new remote keys alongside Stage 1 validation if you submit this material to external review.