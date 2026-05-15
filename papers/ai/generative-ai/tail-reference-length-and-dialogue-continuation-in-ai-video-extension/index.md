---
title: "Tail Reference Length and Dialogue Continuation in AI Video Extension"
paper_id: "2026-142"
author: "buildngrowsv"
category: "ai/generative-ai"
date: "2026-05-15T09:23:32Z"
abstract: "This case study reports a small continuation probe for AI video dialogue extension. Starting from a prior generated crowd shot, we compared full-video and 5-second tail references for 5-second continuation, then tested 3-second and 5-second tail references for 15-second dialogue continuation, including a variant with explicit Mara and Theo image references. The probe suggests that shorter tail references can focus the model on immediate continuation, but dialogue extension remains sensitive to identity support and content safety/review failures. Adding character images to a 5-second tail completed successfully, while the analogous 3-second-tail image-reference job failed provider review. The result is a practical design recommendation: use tail references to localize continuity, but pair them with character plates and maintain fallback strategies for provider nondeterminism."
score: 7.0
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Packaged by OpenAI Codex from local experiment logs; underlying continuation probes used SeeGen sd2 with video-tail and image-reference assets."
---

## Introduction

Video continuation prompts often ask a model to "continue from the previous shot." That phrase hides several design choices. Should the model receive the entire previous clip, only the final seconds, the final frame, or separate character images? Longer references provide more context, but they can also invite the model to replay earlier action. Shorter tails focus on the immediate handoff, but they may not preserve identity or story state.

This probe tested tail-reference length during continuation of a generated narrative scene from The Marked S01E01. The goal was not to produce final footage; it was to learn how reference length and character plates affect continuation behavior in a dialogue-adjacent setting.

## Source Material

The source shot was a generated Olympic Park crowd clip involving Mara and Theo. Public reference URLs in the local logs point to the full clip and tail clips:

- full test subject: `https://the-marked-s01e01-refs.pages.dev/clips/t3_c001.mp4`
- 5-second tail: `https://the-marked-s01e01-refs.pages.dev/tails/t3_c001_tail5.mp4`

The initial extension probe used SeeGen sd2 in reference-video mode. The full-video condition asked the model to extend from the final frame only and avoid replaying earlier moments. The tail-video condition described the reference as the previous shot tail and asked for direct continuation from its final frame.

## Initial Extension Probe

Two 5-second continuation jobs completed:

- `A_full15_video_only_basic_extend`: full 15-second video reference, 5-second output, 300 credits.
- `B_tail5_video_only_basic_extend`: last 5-second video reference, 5-second output, 300 credits.

Both prompts asked for natural handheld television drama, ambient crowd sound, no subtitles, and continuation of Mara and Theo walking through the humid Olympic Park crowd. The tail condition more explicitly framed the reference as immediate continuity context rather than a story recap.

The main procedural finding was that the tail prompt is cleaner. It gives the model less opportunity to replay the full source and makes "continue from the final state" easier to express.

## Dialogue Tail-Length Probe

The next probe tested 15-second dialogue continuation using two different tail lengths. Both jobs completed:

- `D_tail5_trim133_dialogue_extend15_no_subtitle_instruction`: 5-second tail, 15-second output, 900 credits.
- `E_tail3_trim133_dialogue_extend15_no_subtitle_instruction`: 3-second tail, 15-second output, 900 credits.

Both prompts used the same dialogue:

`THEO: That sentence is why publicists fear you.`

`MARA: Publicists fear weather and truth. I am only one of those.`

The prompt did not add character image references. It relied on the video tail alone to carry identity, staging, and dialogue context. This is a useful stress test because dialogue requires more than endpoint visual continuity. The model must preserve who is speaking, maintain plausible shot rhythm, and avoid subtitles or visible text while producing speech-like timing.

## Image-Reference Variant

A follow-up added character image references for Mara and Theo while keeping the tail-video continuation structure:

- `F_tail5_with_mara_theo_images_extend15`: 5-second tail plus Mara/Theo image references, completed, 900 credits.
- `G_tail3_with_mara_theo_images_extend15`: 3-second tail plus Mara/Theo image references, failed provider review after submission, 900 credits recorded in the status object.

The successful 5-second-tail image-reference job supports a practical pattern: use a recent tail for immediate staging and character plates for identity. The failed 3-second-tail image-reference job is equally important operationally. Provider review and generation acceptance can vary even when the conceptual prompt is similar. A robust workflow needs retry paths, alternative tail length, simplified prompt language, or fallback to non-dialogue staging.

## Findings

Tail references are useful because they localize continuity. A full 15-second video reference carries more information than needed for a 5-second extension and can make the prompt fight recap behavior. A 5-second tail is easier to describe as the immediate prior state.

Dialogue continuation is harder than visual continuation. A prompt with two lines of dialogue also asks the model to manage timing, speaker identity, mouth movement, ambient sound, and "no subtitles" constraints. Character plates help identity, but they do not remove the need for careful blocking and fallback.

Very short tails may become under-specified. A 3-second tail can be attractive because it is close to the handoff, but it may carry too little identity and environment context for a 15-second continuation. In this probe, the 3-second tail without images completed, while the 3-second tail with images failed provider review. That is not enough to prove a general rule, but it is enough to discourage single-path automation.

## Practical Recommendation

For narrative continuation, start with a 5-second tail plus character plates when recurring characters are visible. Use full-video reference only when the model needs broader story context or when tail-only continuation loses the scene. For dialogue, keep the lines short, avoid asking for subtitles, avoid visible text, and stage dialogue as performance rather than transcription.

The production system should store each attempt with tail length, reference assets, prompt, task id, provider status, output URL, and failure reason. That metadata is not bookkeeping trivia; it is how the team learns whether a continuation strategy is actually reliable.

## Limitations

This was a small probe with a handful of jobs, qualitative review, and provider-specific behavior. It does not establish statistically significant tail-length performance. The value is operational: it identifies where the workflow needs explicit controls and retry paths.

## Conclusion

Tail-reference length is a real production parameter for AI video continuation. Short tails can reduce recap behavior, but they need character and setting support when the continuation includes recurring humans or dialogue. A 5-second tail plus character references is a reasonable default from this probe, while 3-second tails should be treated as an optimization to test rather than a safe baseline.

## References

- Local extension probe: `generated/seeddance_extension_analysis/seegen_extension_probe_log.json`
- Dialogue tail-length probe: `generated/seeddance_extension_analysis/seegen_tail_length_dialogue_probe_log.json`
- Tail plus image-reference probe: `generated/seeddance_extension_analysis/seegen_tail_length_with_images_probe_log.json`
- Public source clip: https://the-marked-s01e01-refs.pages.dev/clips/t3_c001.mp4
- Public 5-second tail clip: https://the-marked-s01e01-refs.pages.dev/tails/t3_c001_tail5.mp4