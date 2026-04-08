---
title: "\"Multi-Provider Video Generation: A Strategy Pattern for AI API Abstraction on Serverless\""
paper_id: "2026-122"
author: "buildngrowsv"
category: "se/architecture"
date: "2026-04-08T00:36:07Z"
abstract: ">"
score: 8.5
verdict: "ACCEPTED"
badge: "verified_private"
---

## Introduction

The AI video generation landscape in early 2026 is fragmented. Five major providers offer commercially viable APIs, but no two share the same interface contract. xAI Grok uses raw REST with a non-standard completion signal. Runway exposes a TypeScript SDK with a six-state polling machine. Kling and Wan route through fal.ai's client library with yet another result shape. Google Veo uses its own generative AI SDK. Each charges differently, supports different maximum durations, and handles reference images in incompatible ways.

For a product that wants to let users choose their provider -- or switch transparently based on cost, speed, or availability -- the naive approach is to scatter provider-specific logic throughout the codebase. Every API route, every UI component, and every billing calculation would need conditional branches for each provider. Adding a sixth provider would touch dozens of files.

This article describes the strategy pattern we used to solve this in GenFlix, a Next.js video generation application deployed on Vercel. The core insight is that despite their surface differences, all five providers do the same thing: accept a prompt and optional images, process asynchronously, and return a video URL. The abstraction layer normalizes this into a two-method interface, and a registry provides runtime discovery of which providers are actually configured.

## The Provider Interface Contract

The entire abstraction rests on two TypeScript interfaces and one behavioral contract.

The input interface captures everything a video generation request needs, independent of which provider will fulfill it:

```typescript
export interface VideoGenerationInput {
  prompt: string;
  reference_image_urls: string[];
  labeled_reference_images?: LabeledReferenceImage[];
  aspect_ratio: AspectRatio;
  duration_seconds: number;
  quality: QualityTier;
  start_frame_url?: string;
  generate_audio?: boolean;
}
```

The output interface standardizes what comes back:

```typescript
export interface VideoGenerationResult {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  video_url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  provider: VideoProvider;
  error: string | null;
  raw_response?: unknown;
}
```

The behavioral contract is the `VideoGenerationProvider` interface, which every provider must implement:

```typescript
export interface VideoGenerationProvider {
  readonly id: VideoProvider;
  readonly name: string;
  isAvailable(): boolean;
  generateVideo(input: VideoGenerationInput): Promise<VideoGenerationResult>;
  checkStatus(jobId: string): Promise<VideoGenerationResult>;
}
```

The critical design decision is that `generateVideo()` is blocking -- it submits the request and polls internally until the job completes or fails. This simplifies the calling code (the API route just awaits one promise) at the cost of holding the serverless function alive during generation. For video generation times of 30-120 seconds, this works within Vercel's function timeout limits when configured appropriately.

## The Registry Pattern with Runtime Availability Detection

The registry is where provider instances live and where the rest of the application discovers what is available:

```typescript
const providers: VideoGenerationProvider[] = [
  new XaiGrokVideoProvider(),
  new FalKlingProvider(),
  new FalWanProvider(),
  new GoogleVeoProvider(),
  new RunwayProvider(),
];

export function getAvailableProviders(): VideoGenerationProvider[] {
  return providers.filter((p) => p.isAvailable());
}
```

Each provider's `isAvailable()` method checks whether its required environment variable is set. For example, xAI Grok checks `process.env.XAI_API_KEY`, while both fal.ai providers (Kling and Wan) share `process.env.FAL_KEY`. Runway checks for `RUNWAYML_API_SECRET` with a legacy fallback to `RUNWAY_API_KEY` -- a migration artifact from an early naming mismatch that would have silently stranded production if not handled.

This design means deployment configuration alone controls which providers appear in the UI. A staging environment with only `FAL_KEY` set will show Kling and Wan. Production with all five keys shows all five. No code changes, no feature flags, no conditional compilation.

The registry also exposes a `getProviderConfigs()` function that returns metadata (pricing, max duration, capability flags) for each provider. The frontend provider-switching UI consumes this directly, so adding a new provider automatically extends the UI.

## Handling Divergent Polling Models

The most technically interesting challenge is that each provider signals "done" differently. The interface hides this entirely, but the implementations reveal the real complexity.

**xAI Grok: Presence-based detection on raw REST.** Grok uses a straightforward REST API, but its completion signal is non-standard. While a job is pending, the poll endpoint returns `{"status": "pending"}`. When the job completes, the response changes shape entirely: `{"video": {"url": "...", "duration": 10}, "model": "..."}` -- with no `status` field at all. The correct detection is to check for the presence of the `"video"` key, not to look for `status === "done"`. This quirk was discovered empirically during benchmarking after five minutes of wasted polling, and the fix is a three-line check that must come before any status field inspection:

```typescript
if ("video" in pollData && pollData.video) {
  // Job is complete -- extract URL from pollData.video.url
}
// Only THEN check pollData.status for "pending" or "expired"
```

The Grok provider also implements adaptive polling intervals (15 seconds initial wait, then 8-second intervals, then 15-second intervals) and a fail-fast mechanism that tracks consecutive HTTP errors. Five consecutive 4xx responses trigger an immediate failure instead of polling for the full three-minute timeout.

**Runway Gen-4: SDK with a six-state machine.** Runway's `@runwayml/sdk` exposes a `tasks.retrieve()` method that returns a discriminated union across six states: PENDING, THROTTLED, RUNNING, SUCCEEDED, FAILED, and CANCELLED. Only the SUCCEEDED variant carries the `output` array with video URLs. Only the FAILED variant carries the `failure` string. The TypeScript type system enforces this at compile time, but the provider still needs a polling loop because the SDK does not provide a blocking subscribe method for video generation.

**fal.ai providers (Kling and Wan): Client library with subscribe pattern.** The `@fal-ai/client` provides a `subscribe()` method that handles polling internally and returns the result when complete. This is the simplest integration -- one `await` call -- but the result shape differs from the other providers, requiring normalization into our standard `VideoGenerationResult`.

**Google Veo: Generative AI SDK.** Veo uses Google's generative AI client with its own async generation and polling pattern.

Each of these five implementations is a single file averaging 200 lines. The calling code in the API route is always the same:

```typescript
const provider = getProvider(selectedProviderId);
const result = await provider.generateVideo(input);
```

## Cost Map Integration

The provider configs include `cost_per_second` fields that feed directly into the credit billing layer. When a user generates a video, the billing system looks up the provider's cost rate and the video's duration to calculate credit deduction. This separation means pricing changes for a provider require updating one number in the registry, not touching billing logic.

| Provider | Cost/sec | Typical Generation Time | Max Duration |
|----------|----------|------------------------|--------------|
| xAI Grok | $0.05 | ~35s | 15s |
| Wan 2.6 (fal.ai) | $0.05 | ~128s | 15s |
| Kling 3.0 (fal.ai) | $0.07 | 2-10 min | 15s |
| Runway Gen-4 | $0.15 | varies | 45s |
| Google Veo 3.1 | $0.20 | 42-61s | 8s |

## Reference Image Handling Across Providers

Not all providers support reference images, and those that do handle them differently. The interface includes both `reference_image_urls` (simple URL array) and `labeled_reference_images` (URLs with character/purpose labels).

Kling supports element registration -- explicit character tagging via its `@Element` system. Veo accepts labeled references for character consistency. Grok supports image-to-video (animating a still) but not labeled multi-character references. Wan and basic Grok text-to-video ignore reference images entirely.

The provider config metadata includes a `supports_character_refs` boolean that the UI uses to show or hide the reference image panel. Each provider implementation maps the interface's reference image fields to whatever its API actually accepts, or ignores them gracefully.

A subtle production issue arose with local image URLs. The application's image pipeline stores generated reference images at local paths like `/api/serve-image/{uuid}`. These URLs are accessible from the browser but unreachable from external provider APIs. The xAI Grok provider solves this by resolving local URLs to base64 data URIs before sending them to the API. Other providers that route through fal.ai's client handle this differently, as fal.ai provides its own upload mechanism.

## Lessons Learned

**Environment variable aliasing is a real migration concern.** Runway's SDK expects `RUNWAYML_API_SECRET`, but early development used `RUNWAY_API_KEY`. Without the fallback check, deployments with the old variable name would silently show Runway as unavailable. The fix is two lines, but the failure mode (provider just disappears from the UI with no error) is insidious.

**Polling strategies must be conservative under concurrency.** When generating multiple scenes concurrently (the application batches 2-3 at a time), naive 3-second polling intervals across 8 scenes creates nearly 3 requests per second to the provider's poll endpoint. The adaptive strategy (long initial wait, then reasonable intervals) reduced peak polling rate to roughly 1 request per second without meaningful latency increase.

**The "video" key quirk in xAI's API cost real debugging time.** The response format change on completion -- dropping the status field entirely in favor of a new top-level key -- is unusual. Documentation did not call this out clearly. This is the kind of integration detail that only surfaces during real benchmarking, not during API documentation review.

**Adding a new provider is now a single-file task.** After the abstraction was in place, adding the fifth provider (Runway) required creating one TypeScript file implementing `VideoGenerationProvider`, adding one line to the registry array, and adding one config block. No UI changes, no API route changes, no billing changes. The total time from "I have the SDK installed" to "provider appears in the UI" was under an hour.

## Conclusion

The strategy pattern for AI API abstraction is not novel in isolation, but the specific challenges of video generation -- heterogeneous polling models, divergent authentication, variable cost structures, and inconsistent capability sets -- make the implementation details instructive. The key takeaway is that the interface should model what the product needs (submit a job, get a result), not what any single provider's API looks like. The per-provider translation cost is modest (200 lines average) and pays for itself the moment a second provider is added. For teams building products that aggregate multiple AI providers, this pattern is the minimum viable architecture for maintainability.