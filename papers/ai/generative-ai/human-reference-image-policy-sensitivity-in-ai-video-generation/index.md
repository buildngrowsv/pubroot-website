---
title: "Human Reference Image Policy Sensitivity in AI Video Generation"
paper_id: "2026-175"
author: "buildngrowsv"
category: "ai/generative-ai"
date: "2026-05-15T09:39:25Z"
abstract: "A GenFlick production incident showed that a video-generation failure labeled \"Sensitive content\" was caused by photorealistic human reference images sent to Seedance image-to-video and reference-to-video endpoints, not by the written prompt, generated audio, account status, or text-to-video capability. Reconstructed fal.ai Seedance 2.0 tests returned HTTP 422 content-policy failures when human start frames or generated photorealistic character portraits were supplied, while text-only prompts, non-person set references, and stylized avatar references completed. The benchmark suggests that AI video products should classify provider refusals by input modality, surface precise recovery options, and route human-likeness references differently from non-person or stylized references."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from GenFlick Seedance human-reference sensitivity analysis notes. The Pubroot packaging step did not replay provider calls."
---

## Question

When an AI video provider returns a sensitive-content error, the cause is not always the text prompt. It may be the media reference itself.

GenFlick investigated a production failure where a user-visible error implied sensitive content. The underlying question was whether the failure came from the prompt, generated audio, account status, text-to-video unavailability, or reference images.

## Reconstructed Payload

The affected production clip used Seedance 2.0 through fal.ai. The request was reconstructed from persisted project state using the same application helpers used by the generation path:

- generation prompt composition
- labeled video reference construction
- clip lookup
- Seedance provider reference-binding behavior

The reconstructed request used Seedance reference-to-video with a 16:9, 12-second payload, a long production prompt, an approved start frame, and a character portrait reference.

The exact replay reproduced an HTTP 422 failure on image references. Replaying with generated audio disabled failed with the same class of image-reference error, ruling out audio generation as the root cause.

## Sensitivity Matrix

The investigation then varied endpoint, image inputs, and audio.

Requests using human visual references failed:

- exact production replay with start frame plus character portrait
- exact production replay with audio disabled
- start frame only with a generic safe prompt
- individual generated human character portraits as reference images

Requests without photorealistic human references completed:

- the full production prompt as text-to-video with no images
- reference-to-video with a non-person room or set reference
- reference-to-video with a clearly stylized flat avatar reference

The apparent boundary was not "unsafe prompt" or "voiceover." It was photorealistic human-likeness media passed in image reference fields.

## Product Implication

AI video applications often use start frames and character portraits to preserve continuity. That is normally desirable: identity references help keep characters stable across shots. But provider policy can make that path brittle when references contain photorealistic human likenesses.

The failure mode is especially confusing because the written prompt may be safe and the text-to-video endpoint may work. If the application retries the same media payload, it can repeatedly fail without giving the user a useful recovery path.

## Recommended Error Classification

The application should detect this refusal class precisely:

- HTTP 422 or equivalent provider validation failure
- content-policy or safety violation type
- error location includes image URL or image URL list
- message mentions likeness, people, privacy, or private information

The user-facing message should name the failing modality:

```text
Seedance rejected the human reference image, not the written prompt.
```

That distinction matters. It tells the user and the agent what to change.

## Recovery Options

Useful recovery paths include:

- retry the same written prompt without human references
- keep non-person set and prop references while dropping human portraits
- switch to a provider that accepts the desired human-reference workflow
- regenerate character references in a clearly stylized or non-photorealistic look
- ask the user to confirm a provider switch or reference-removal tradeoff

The product should not blindly retry the same media reference payload. A deterministic policy refusal is not transient.

## Routing Policy

A media generation system can avoid some failures by classifying reference assets before provider selection.

For Seedance-like behavior observed here:

- photorealistic human start frames and portraits should be treated as high-risk references
- non-person sets and props can remain useful references
- stylized avatars may be acceptable, but should still be classified conservatively
- text-to-video fallback should remain available when identity continuity is less important than successful generation

The reference router should understand role and content class. A human identity reference, a room reference, and a style board should not be routed as interchangeable images.

## Limitations

This was a provider-specific sensitivity test, not a universal safety benchmark. It does not prove that all Seedance deployments or all providers behave the same way. It also does not determine whether account allowlisting, different image styles, or different vendors would change the boundary.

The supporting repository and production observability exports are private, limiting external reproduction. The methodology remains useful: reconstruct the payload, isolate prompt from media from audio, and vary one modality at a time.

## Conclusion

Sensitive-content errors in AI video generation should be debugged by modality. In this Seedance case, safe text prompts completed, but photorealistic human image references failed consistently. Products that depend on visual continuity should classify human-reference risk, route provider calls accordingly, and offer recovery actions that change the rejected input rather than repeating it.