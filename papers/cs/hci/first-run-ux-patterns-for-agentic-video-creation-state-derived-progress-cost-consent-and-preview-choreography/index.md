---
title: "First-Run UX Patterns for Agentic Video Creation: State-Derived Progress, Cost Consent, and Preview Choreography"
paper_id: "2026-132"
author: "buildngrowsv"
category: "cs/hci"
date: "2026-05-15T09:14:56Z"
abstract: "Agentic media products can generate useful work while still leaving first-run users confused about what happened, what is still running, what costs credits, and where to preview partial output. This case study reports a GenFlick UX audit after observing a first-time user struggle with an AI movie-generation flow despite the app having the necessary raw features. The product already had chat, screenplay and timeline tabs, media status pills, Story Reel playback, credit estimates, local and cloud storage indicators, and per-clip generation controls. The failure was choreography. The resulting pattern is to compute project progress from state, expose one persistent next-step panel, teach the image-first to video pipeline at the moment it matters, require explicit credit consent before bulk video generation, and provide preview navigation that starts from newly ready work. The article maps the observed confusion points to reusable UX design principles for agentic creation tools."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from docs/FIRST-RUN-UX-AUDIT-AND-ACTION-REPORT-2026-04-26.md and related GenFlick UX implementation notes."
---

## Problem

Agentic creation tools are often evaluated by output quality. First-run experience depends just as much on whether the user understands the system's state. GenFlick's first-run audit showed a familiar pattern: the application could write scenes, create still frames, queue videos, preview clips, and estimate credits, but a new user still did not know what to do next.

The underlying workflow is multi-stage. A prompt becomes a screenplay and movie bible. The agent creates scenes and clips. Still images arrive before videos. Video generation may cost credits and take much longer. Some projects are local-only while others sync to a cloud account. Partial output can be previewed before the full movie is complete. Those facts are obvious to the engineers and agents that built the system, but not to a first-time user watching the interface change.

## Observed Confusion

The audit normalized several observed pain points.

The user thought a previous project was missing. The app had local and cloud storage indicators, but the distinction between "saved in this browser" and "synced to account" was not loud enough before meaningful work was created.

The user did not know generation could take many minutes and require the tab to remain open. Activity indicators existed, but they did not form a bounded progress model.

The user saw still images and was unsure what to do with them. The product intentionally uses an image-first pipeline so creators can inspect still frames before spending video credits, but the UI did not teach that distinction at the first image-ready moment.

The user saw "preview ready" signals but did not know where to preview. Story Reel and timeline playback existed, but the calls to action were scattered across top bars, chat cards, and clip controls.

The user wanted to watch newly generated clips without starting over from the beginning. The product had play-all behavior, but not enough "play from here" or "latest ready" affordances.

The most important observation was positive: once the user found the output, the payoff worked. The first-run problem was not missing capability. It was missing choreography.

## Pattern One: State-Derived Progress

A progress model should be computed from project state, not faked as a percentage. GenFlick's useful counts include acts defined, scenes drafted, clip stills ready, clip stills generating, videos ready, videos generating, missing videos, and exportable clips.

This kind of progress is more legible than "62 percent complete" because it maps to the user's mental model. A user can understand "5 of 12 stills ready, 2 videos ready, 10 videos not started." It also avoids false precision in workflows where LLM and media-provider latency vary.

## Pattern Two: Persistent Next Step

The audit recommended one persistent next-step panel driven by project state. The panel should say what has happened, what is currently happening, and what the likely next action is.

Examples:

- No clips: describe your movie.
- Scenes exist but images are running: writing and making first stills.
- Images ready and no videos: review stills, then generate videos.
- Some videos ready: preview new clips or generate remaining videos.
- All videos ready: watch Story Reel, export, or run a continuity pass.

This panel reduces dependence on users discovering the right tab or remembering prior chat messages. It gives the agent's work a stable home in the UI.

## Pattern Three: Cost Consent Before Bulk Media Work

GenFlick's agent prompt already avoids generating all videos unless the user explicitly asks. The UI should enforce the same discipline. Before bulk video generation, it should show the number of videos to generate, estimated credits, and what will remain pending.

This is not only a billing safeguard. It also clarifies why the agent stopped after still images. From the product's perspective, it is responsibly waiting for consent. From the user's perspective, without an explanation, it may look unfinished.

## Pattern Four: Teach the Pipeline Just in Time

Agentic media tools should avoid front-loading explanations. The better moment to teach is when a state transition occurs.

When the first still frame lands, the UI can say: this is the still frame; if you like it, generate video; if not, regenerate the image. When the first videos are ready, it can promote Story Reel or play-from-latest. When export is attempted with missing clips, it can warn that only rendered videos will be included.

This keeps instruction close to action. It also respects repeat users by making training skippable.

## Pattern Five: Preview Partial Output

A generation pipeline should not make the user wait for perfection before seeing value. GenFlick's Story Reel can play a partial movie using video when available, image when video is missing, and text as fallback. That is a strong first-run affordance, but it needs to be promoted when any previewable media exists.

Preview controls should also match the user's likely task. "Play all" is useful later. During first-run review, "play from selected," "play newly ready," next/previous clip navigation, and incomplete-playback warnings are more useful.

## Storage Clarity

Storage semantics should be explained before they become scary. If a free plan saves in this browser only and paid plans sync to the account, say so before the user creates meaningful work. If upgrading promotes local projects to cloud, say that too. Users should not discover persistence boundaries after closing a tab or switching devices.

## Implementation Notes

The first implementation pass added a shared progress helper, a next-step panel, localStorage-backed quick training, clearer first-screen copy, Stripe trust copy, and playback navigation improvements. It did not solve every issue. Remaining work included cleaning up clip tool density, warning before export with missing clips, browser-close warnings during active jobs, loudness normalization, and broader action buttons in assistant summaries.

The important design decision was to assemble existing features into a coherent journey instead of adding another disconnected surface. The app already had many of the necessary parts. The work was to make state, next action, and user consent obvious.

## Conclusion

First-run UX for agentic video creation should be stateful, not merely conversational. Users need a visible answer to four questions: what did the agent make, what is still running, what costs money next, and where can I preview what exists now? A state-derived progress panel, just-in-time pipeline teaching, explicit credit consent, and partial-output preview form a reusable pattern for creative agent products whose internal workflows are too complex to leave hidden behind chat.