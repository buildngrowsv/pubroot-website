---
title: "Soft Storyboards as a Directing Layer for AI Video Generation"
paper_id: "2026-145"
author: "buildngrowsv"
category: "ai/generative-ai"
date: "2026-05-15T09:25:02Z"
abstract: "This case study reports a pivot from dense keyframe control to soft storyboard prompting for narrative AI video. In The Marked S01E01 Act One, each shot was described by a storyboard brief covering story purpose, geography, characters, wardrobe, props, camera setup, ordered beats, continuity constraints, and reference plates. The method was tested with three six-second SeeGen sd2 clips and then with three fifteen-second dialogue clips. The early result was that soft storyboard briefs handled ordinary human staging better than exact-frame control, while object-specific actions and readable-screen constraints still required physical blocking language. The article proposes a review gate based on whether generated video satisfies the shot brief, not whether it copies exact panels."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Packaged by OpenAI Codex from local experiment notes; underlying experiments used SeeGen sd2 with visual and voice references."
---

## Introduction

Dense keyframes help preserve continuity, but they can also create a brittle workflow. Every keyframe must be separately generated, reviewed, and reconciled with adjacent frames. The resulting image sequence may be orderly in filenames while still drifting in visual logic. A shot can appear to have start and end control, yet the video model may struggle to animate a natural human performance between them.

The soft storyboard workflow tested here treats the storyboard as a directing layer rather than a locked frame sequence. Each shot receives a clear brief: what the shot is about, who is present, where everyone is, what props matter, what must not change, and what ordered action beats should occur. The video model is then asked to perform the shot naturally using that brief and reference plates, without being forced to copy exact panels.

## Method

The test restarted The Marked S01E01 from Act One and intentionally excluded previous generated film clips, stitched cuts, tail continuity videos, review frames, generated keyframes, old video prompts, and audio bootstrap files. Allowed sources were the series bible, episode script, visual reference plan, image prompt manifest, public reference URL map, and root-level reference plates for characters, sets, props, and tone.

Each shot card included a shot id, script span, story purpose, fixed location, screen geography, characters, wardrobe, props, camera setup, beat count, ordered action beats, continuity constraints, and reference plates. Simple inserts or reactions used roughly three beats. Normal action or two-person dialogue used about four beats. Blocking changes, discoveries, confrontations, or crowd movements used five or six beats.

## First Test

The first pilot generated three independent six-second SeeGen sd2 clips from Act One storyboard briefs. There were no keyframes, no previous-tail chaining, and no prior film prompts.

The tested shots were:

- `A1-S01-010`: apartment aftermath, with Mara at a laptop and Theo scratching.
- `A1-S01-040`: mosquito on wall beside laptop glow, slap and miss.
- `A1-S02-020`: Lena receives Bruno's sanitation text and sees the contradiction in the lab.

The apartment aftermath clip was promising. It showed strong room continuity, believable two-person staging, and natural performance. The model handled ordered beats without exact keyframes, which was the strongest early evidence for the soft-storyboard approach.

The mosquito wall clip needed revision. The model understood the laptop, wall, insect, and slap, but over-performed the action. The body staging became awkward and the mosquito business became too visually emphasized. This suggests that tiny object actions should often be staged through human reaction and off-screen attention rather than direct insect visibility.

The lab contradiction clip was mixed. Lena identity and lab atmosphere were strong, and the action sequence read as phone to sample to decision. However, the phone screen showed readable-looking text, violating the constraint. The correction is not merely to say "no readable text"; the prompt should physically block the screen by keeping it face-down, angled away, blown out, or seen only as blurred light.

## Dialogue Redo

A second batch reran the same three soft storyboard tests at fifteen seconds with visual references and voice references. The purpose was to test whether longer duration plus voice references could improve dialogue while preserving continuity behavior from the six-second test.

Apartment clips used Mara, Theo, and Rio rental visual references plus Mara and Theo voice references. The lab clip used Lena, Lena neutral, Bruno, Rio vector lab, and sample-tube references plus Lena and Bruno voice references. The apartment dialogue was mostly direct script material. The lab clip adapted a text-message beat into a brief phone exchange so the dialogue test had enough spoken material while preserving story meaning.

## Findings

Soft storyboards are effective for ordinary human staging. The apartment aftermath test produced coherent human behavior with fewer generated still assets than the keyframe-first path. That matters because narrative scenes are often driven by room geography, attention, and performance rather than by exact endpoint frames.

The method is weaker for object-specific action unless the prompt turns constraints into physical blocking. "No readable text" is too abstract; "phone remains face-down and only its blurred glow is visible" is operational. "Tiny mosquito visible" can cause the model to enlarge or over-center the insect; "Mara notices something just out of focus near the laptop" keeps the human performance in control.

The review standard also changes. The question is not whether a generated clip matched the storyboard panels. The question is whether it satisfies the shot brief: same identities, same wardrobe, stable geography, no unauthorized props, no real sponsor or Olympic marks, no accidental readable text, and clear ordered action.

## Limitations

This is an early three-shot pilot, not a full production benchmark. The outputs were judged qualitatively from contact sheets and clip review, not by a formal perceptual metric. Dialogue and voice consistency remain open questions. The method also depends heavily on shot-card quality; a vague brief will still produce vague video.

## Conclusion

Soft storyboards are a useful middle layer between free-form prompting and dense keyframe control. They preserve directorial intent while giving the video model room to create natural in-between motion, body language, and camera nuance. For this project, the next sensible workflow is to use soft storyboards for ordinary dramatic staging, reserve dense keyframes for risky visual continuity beats, and review each candidate against the shot brief rather than against exact panel imitation.

## References

- Local workflow note: `storyboard-first-s01e01/notes/storyboard_first_workflow.md`
- First test results: `storyboard-first-s01e01/notes/soft_storyboard_test_001_results.md`
- Dialogue redo note: `storyboard-first-s01e01/notes/soft_storyboard_test_002_15s_dialogue_results.md`
- Storyboard outline: `storyboard-first-s01e01/storyboards/act1_storyboard_outline.md`