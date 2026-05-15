---
title: "Keyframes-First Continuity Grid for Narrative AI Video Generation"
paper_id: "2026-139"
author: "buildngrowsv"
category: "ai/generative-ai"
date: "2026-05-15T09:22:52Z"
abstract: "This case study documents a keyframes-first workflow for long-form narrative AI video generation. In a 19-minute teaser plus Act One plan for The Marked S01E01, we inverted the earlier video-first path: instead of generating 15-second clips and feeding tail clips forward, we planned 455 still keyframes at an average 2.51-second cadence and treated approved stills as continuity authority. The workflow separates editorial decisions from expensive motion generation, makes identity, geography, wardrobe, and prop continuity reviewable before video spend, and prevents a bad generated segment from contaminating subsequent segments. The result is not a claim of final production quality; it is a reproducible production pattern for using dense still-image planning as the control layer above short video generations."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Packaged by OpenAI Codex from local experiment notes; underlying experiments used GPT Image 2 reference/keyframe planning and SeeGen sd2 video generation."
---

## Introduction

Long-form AI video generation fails in ways that are expensive to discover late. A generated shot may look plausible in isolation while drifting character identity, screen geography, wardrobe, prop state, lighting, or camera axis. The first attempt in this project used a video-first chain: generate a 15-second clip, extract the final tail, use that tail as continuity input, and continue the sequence. That path gave the model useful local context, but it also made failures contagious. If the outgoing tail contained a face drift, wrong blocking, odd camera move, or unwanted tone, the next generation inherited the problem.

The keyframes-first workflow tested here changes the authority layer. Still keyframes are generated, reviewed, and locked before video. Each video segment is then a short span between adjacent approved keyframes. The keyframes carry editorial intent; the video model supplies motion between already-approved states.

## Source Scope

The test was built around The Marked, Season 1 Episode 1, teaser plus Act One. Source materials included the series bible, episode script, visual reference plan, image prompt manifest, public reference URL map, and character, set, prop, tonal, and mark reference plates. Prior generated clips, tail videos, voice bootstrap audio, SeeGen job logs, and review frame sheets were intentionally excluded from the clean keyframe-first path.

This boundary matters because the experiment was testing whether the still-image plan could become its own continuity layer rather than merely reorganizing artifacts from the old video-first run.

## Cadence Rule

The working recommendation was a 2 to 3 second active keyframe grid, with exceptions based on visual risk rather than a fixed metronome.

For normal dialogue, procedural action, walking-and-talking, inserts, and location transitions, 2.5 to 3 seconds was treated as the default. For bites, hand movement, screen inserts, crowd movement, character crosses, close eye-mark reveals, and other continuity risks, the interval tightened toward 2 seconds. For a stable locked-off reaction or interview shot with little blocking change, it could loosen to 8 to 10 seconds.

The current manifest for the 19-minute teaser plus Act One contains 455 planned keyframes across roughly 1,140 seconds, averaging 2.51 seconds per keyframe. A cheaper pilot scope was also identified: the opening Rio material and vector lab sequence, roughly 70 keyframes, enough to test whether the control layer improves continuity before scaling.

## Workflow

The workflow has six stages.

1. Build a beat-to-keyframe manifest from the script.
2. Generate still keyframes using reusable reference plates.
3. Review the stills as contact sheets before any video generation.
4. Lock only approved keyframes.
5. Generate short first-frame/last-frame video spans between adjacent approved stills, usually 4 to 6 seconds each.
6. Stitch the spans, review motion, and regenerate only failed spans.

The practical generation unit becomes one short span between two approved frames. The typical request includes an approved first frame, an approved destination frame about 5 seconds later, one to four character/set/prop references, and a prompt that describes only the motion and performance between those stills.

## Review Gate

The still review gate was deliberately concrete. Before any sequence could move to video, stills had to preserve the same character identity, wardrobe, era, geography, screen direction, and story purpose. They also had to avoid real Olympic rings, real sponsor logos, readable accidental text, supernatural-looking eye marks, accidental horror tone in medical or mosquito material, and incoherent prop continuity.

This is where the method earns its value. Reviewing 455 stills is not free, but it is cheaper and clearer than discovering drift after 455 seconds of generated motion. The still grid turns continuity review into a scannable production task.

## Findings

The main finding is architectural rather than aesthetic: keyframes can serve as a non-destructive continuity authority. In the video-first chain, a bad outgoing tail can poison the next shot. In the keyframes-first chain, a bad generated motion segment does not rewrite the next segment's destination because that destination still comes from an approved still.

The second finding is that a dense grid changes prompting discipline. Prompts no longer need to ask the video model to invent the whole scene and preserve every constraint for 15 seconds. They can ask for motion between two known states: a hand reaches, a character turns, a phone buzzes face-down, a larva dish is examined, a camera pushes in. The shorter unit narrows the model's opportunity to drift.

The third finding is that dialogue should not be solved too early. The first pass should prioritize composition, blocking, continuity, and tone. Lip sync, final dialogue timing, and audio can be layered or regenerated after the visual path is coherent.

## Limitations

The method increases up-front planning. A 455-keyframe manifest is a real workload, and the review process needs tooling: contact sheets, stable identifiers, approval state, regeneration tracking, and clear connection between script beats and generated frames.

The method also does not guarantee good motion. It constrains endpoints; it does not make the video model understand performance, physical causality, or acting nuance. Some spans will still need regeneration, and some scenes may require a softer storyboard approach instead of exact endpoint control.

## Conclusion

For narrative AI video, keyframes-first is best understood as a production control pattern. It moves continuity decisions earlier, makes the edit visible before video spend, and isolates video failures to short spans. The approach is especially useful when identity, geography, props, and tone matter more than speed. It should be tested first on a bounded pilot sequence before scaling to a full act or episode.

## References

- Local source note: `keyframes-first-s01e01/README.md`
- Local workflow note: `keyframes-first-s01e01/notes/keyframe_first_workflow.md`
- Active manifest named in the workspace: `manifests/s01e01_teaser_act1_gpt_image2_medium_keyframes.json`