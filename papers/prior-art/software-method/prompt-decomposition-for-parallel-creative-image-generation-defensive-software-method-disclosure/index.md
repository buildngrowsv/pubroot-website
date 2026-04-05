---
title: "Prompt Decomposition for Parallel Creative Image Generation \u2014 Defensive Software Method Disclosure"
paper_id: "2026-109"
author: "buildngrowsv"
category: "prior-art/software-method"
date: "2026-04-05T19:38:11Z"
abstract: "This disclosure describes a software method for creative image generation that decomposes a single user prompt into multiple divergent creative directions using a large language model (LLM), then generates images in parallel across one or more image generation APIs. Rather than producing variations on a single visual interpretation, the method yields a diverse gallery of conceptually distinct images from a single natural-language input. The pipeline consists of three stages \u2014 LLM-driven concept descriptor generation with explicit diversity constraints, per-descriptor detailed prompt expansion, and parallel image generation with gallery assembly. A diversity enforcement layer using Jaccard distance and farthest-first traversal ensures maximum creative spread across the output set. This method is placed in the public domain under CC0 1.0 Universal to serve as prior art against method-of-use patent claims on prompt decomposition, divergent creative generation, or LLM-to-image-API pipeline orchestration."
score: 8.5
verdict: "ACCEPTED"
badge: "text_only"
---

## 1. System Overview

This disclosure covers a software method — referred to here as the "brainstorm pipeline" — that transforms a single user prompt into a gallery of visually and conceptually diverse images through a multi-stage decomposition and parallel generation process.

The high-level data flow is:

1. **User Input.** A single natural-language prompt describing a creative intent (e.g., "modern workspace with a digital art station").
2. **Stage 1 — Concept Descriptor Generation.** An LLM (any capable chat-completion model, such as GPT-4o, Claude, Gemini, or open-source equivalents) receives the prompt along with a system instruction to act as a "creative director" assigning work to N independent artists. The LLM produces N short concept descriptors (typically 2–5 word phrases), each representing a divergent visual interpretation of the original prompt. Default N = 16.
3. **Stage 2 — Detailed Prompt Expansion.** Each concept descriptor is individually expanded into a full image-generation prompt (20–40 words) by a second LLM call (or batch of calls). Each expanded prompt specifies subject, composition, color palette, mood, lighting, texture, perspective, artistic style, and medium — all guided by but divergent from the original user intent.
4. **Stage 3 — Parallel Image Generation.** The expanded prompts are dispatched in parallel to one or more image generation APIs (e.g., OpenAI DALL-E, OpenAI gpt-image-1, Stability AI Stable Diffusion, Midjourney API, or any future provider). Images are generated concurrently. Results are collected, associated with their provenance metadata (which descriptor, which prompt, which API, generation parameters), and assembled into a gallery.
5. **Gallery Assembly.** The user sees a grid of N images, each representing a distinct creative direction. The user can select, reject, combine, or refine individual concepts for iterative re-generation.

The method is provider-agnostic at every stage: any LLM can perform decomposition, any image API can generate, and any number of providers can be mixed in a single run.

## 2. Problem Statement

Standard image generation systems (as of early 2026) operate on a one-prompt, one-interpretation model. When a user submits "a modern workspace," the system produces one image (or minor variations via seed changes or slight parameter perturbation). The resulting images cluster around a single aesthetic interpretation — they differ in pixel-level detail but not in creative direction.

Users who want creative diversity must manually write multiple, substantially different prompts. This requires prompt engineering skill and significant cognitive overhead. The user must independently imagine divergent interpretations of their own intent, which defeats the purpose of using generative AI for creative exploration.

Existing multi-generation tools (batch generation, grid generation, prompt matrix tools) vary parameters mechanically — changing style tokens, aspect ratios, or sampler settings — but do not perform semantic decomposition of creative intent. They produce parametric variations, not conceptually divergent creative directions.

No existing publicly documented system, as of the disclosure date, automatically decomposes a single creative prompt into semantically divergent creative directions via LLM and generates images for each direction in parallel across heterogeneous image generation APIs.

## 3. Method Description

The method proceeds through the following steps:

**Step 3.1 — Prompt Analysis and Creative Axis Identification.**

The system prompt instructs the LLM to analyze the user's input along multiple creative axes:

- **Style axis:** Photorealistic, illustration, watercolor, vector, pixel art, oil painting, 3D render, collage, mixed media, etc.
- **Mood axis:** Warm, cold, dramatic, serene, chaotic, minimal, maximalist, nostalgic, futuristic, etc.
- **Composition axis:** Close-up, wide shot, bird's-eye, isometric, split-screen, rule-of-thirds, centered, asymmetric, etc.
- **Subject interpretation axis:** Literal vs. metaphorical, abstract vs. concrete, focused vs. environmental, single-subject vs. ensemble, etc.
- **Medium axis:** Photography, digital art, traditional art, architecture, product design, fashion, editorial, advertising, etc.

The LLM is not given a rigid template. Instead, the system prompt frames the task as creative direction ("you are a creative director with N artists to serve"), which naturally produces divergent outputs because the LLM models creative agency distribution rather than parameter permutation.

**Step 3.2 — Divergent Concept Descriptor Generation.**

The LLM generates N concept descriptors. Each descriptor is a short phrase (2–5 words) representing a distinct visual approach. The system prompt includes explicit diversity constraints:

- Each descriptor must be "visually distinctive"
- The set must "cover diverse visual approaches and styles"
- The LLM must "consider the full range of artistic possibilities"

The output is structured JSON: an array of descriptor objects, each containing a `text` field.

**Step 3.3 — Diversity Enforcement (Optional Algorithmic Layer).**

If the LLM generates more than N descriptors (or if a diversity guarantee is required), a post-processing layer selects the most diverse subset. The implementation uses:

- **Jaccard distance** between tokenized descriptor texts as the dissimilarity metric.
- **Farthest-first traversal** (a greedy algorithm that iteratively selects the point maximally distant from all previously selected points) to choose the final N descriptors from a larger candidate pool.

This ensures that even if the LLM produces some similar descriptors, the final set has maximum pairwise dissimilarity.

**Step 3.4 — Per-Descriptor Prompt Expansion.**

Each selected concept descriptor is expanded into a full image-generation prompt via a separate LLM call. The expansion prompt instructs the LLM to:

- Maintain the essence of the concept descriptor
- Specify concrete visual attributes: subject, composition, color palette, mood, lighting, texture, perspective, style, medium
- Produce a prompt of 20–40 words optimized for image generation
- Incorporate the original user intent as context

Expansion calls can run in parallel (batch or concurrent API calls) since each descriptor is independent.

**Step 3.5 — Parallel Multi-Provider Image Generation.**

The expanded prompts are dispatched to image generation APIs. The dispatch is parallel: all N prompts are sent concurrently. The system supports:

- **Single-provider mode:** All prompts go to one API (e.g., all to gpt-image-1).
- **Multi-provider mode:** Prompts are distributed across multiple APIs (e.g., some to DALL-E 3, some to Stable Diffusion XL, some to gpt-image-1) to increase stylistic diversity through model-level differences.
- **Redundant mode:** Each prompt is sent to multiple providers, producing M × N total images.

Each generated image is tagged with provenance metadata: the original user prompt, the concept descriptor, the expanded prompt, the API provider, model name, generation parameters (quality, size, seed if available), and timestamp.

**Step 3.6 — Gallery Assembly and Iterative Refinement.**

Results are collected into a gallery grid. Each cell shows one image with its concept descriptor as a label. The user can:

- **Select** concepts they like (marking them for refinement or export)
- **Reject** concepts they dislike (removing them from future iterations)
- **Combine** two or more concepts (feeding selected descriptors back into the LLM to synthesize a merged direction)
- **Refine** a single concept (re-running the pipeline with the selected descriptor as additional context, producing variations within that creative direction)
- **Pivot** (re-running the entire pipeline with a modified prompt and the previous descriptors as "avoid" examples, ensuring new directions do not repeat prior explorations)

Each iteration produces a new set of descriptors, prompts, and images, building a tree of creative exploration rooted at the original prompt.

## 4. Architecture

The architecture consists of the following components, all of which are swappable:

**Decomposition Layer (Stage 1 + Stage 2):**
- Any LLM capable of structured JSON output (GPT-4o, GPT-4-turbo, Claude 3/4, Gemini 1.5/2.0, Llama 3, Mistral, or any future model).
- System prompts defining the creative-director framing and diversity constraints.
- JSON parsing of LLM output to extract structured descriptor objects.

**Diversity Enforcement Layer:**
- Jaccard distance computation over tokenized descriptor texts.
- Farthest-first traversal for subset selection.
- This layer is optional but recommended for guaranteed diversity.

**Prompt Queue:**
- An in-memory queue (or distributed queue for server deployments) holding expanded prompts awaiting image generation.
- Each queue entry carries full provenance metadata.

**Parallel Image Generation Workers:**
- Concurrent workers (async tasks, threads, or serverless functions) that consume prompts from the queue and call image generation APIs.
- Support for multiple API backends: OpenAI Images API (DALL-E 2, DALL-E 3, gpt-image-1), Stability AI API, Midjourney API, Replicate, or any provider exposing a prompt-to-image endpoint.
- Error handling and retry logic per worker.

**Gallery Assembly Layer:**
- Collects generated images and their metadata.
- Organizes results into an iteration structure (a tree of user prompt → descriptors → prompts → images).
- Persists session state for iterative refinement across multiple rounds.

**Session and State Management:**
- Each brainstorm session is a tree of iterations, where each iteration has a parent (except the root).
- Variants (descriptor + prompt + image) are tracked per iteration.
- Prompts are stored in RAM or persistent storage with unique IDs for reference.

## 5. Prior Art

The following prior art is known and distinguished from this disclosure:

- **Standard prompt engineering:** Users manually write image generation prompts. This is a single-prompt, single-interpretation workflow with no automated decomposition.
- **Prompt variation techniques:** Tools that mechanically substitute tokens (e.g., "{style}" → ["oil painting", "watercolor", ...]) produce parametric grids, not semantically divergent creative directions. The variation space is defined by the user, not generated by an LLM.
- **Grid search over image generation parameters:** Varying seed, CFG scale, sampler, or steps produces pixel-level variation within a single interpretation, not conceptual diversity.
- **Multi-generation tools (e.g., Midjourney /imagine with --grid):** Generate multiple images from the same prompt with different seeds. All images share the same creative interpretation.
- **ChatGPT + DALL-E integration (as of 2025–2026):** When a user asks ChatGPT to generate images, the system may internally refine the prompt, but it does not decompose the prompt into multiple divergent creative directions and generate images for each direction in parallel.
- **Prompt enhancement/rewriting tools:** Tools like PromptPerfect or various prompt optimizers take a prompt and produce a single improved prompt. They do not decompose into divergent directions.
- **A/B testing for ad creative:** Some advertising platforms generate multiple ad variations, but these vary copy/layout/color parametrically rather than performing LLM-driven semantic decomposition of creative intent.

## 6. Novel Contribution

The novel combination disclosed here is:

1. **Automated divergent creative decomposition via LLM.** Using an LLM to decompose a single prompt into multiple semantically distinct creative directions — not parametric variations, but genuinely different interpretations of the user's intent along multiple creative axes (style, mood, composition, subject interpretation, medium).

2. **Algorithmic diversity enforcement.** Applying dissimilarity metrics (Jaccard distance) and diversity-maximizing selection algorithms (farthest-first traversal) to the LLM's output to guarantee maximum creative spread in the final descriptor set.

3. **Parallel multi-provider image generation.** Dispatching the divergent prompts in parallel across one or more heterogeneous image generation APIs, with each image tagged with full provenance metadata (original prompt, descriptor, expanded prompt, API, model, parameters).

4. **Gallery assembly as a single pipeline.** Combining decomposition, expansion, parallel generation, and result collection into a single automated pipeline triggered by one user input, producing a diverse gallery rather than a single image or minor variations.

5. **Iterative refinement tree.** Supporting user-driven selection, rejection, combination, and pivot operations that feed back into the pipeline, building a tree of creative exploration.

The novelty is in the combination and orchestration of these steps as an integrated software method, not in any individual component (LLMs, image APIs, diversity algorithms, or gallery UIs are individually known).

## 7. Supporting Implementation

A reference implementation of this method exists in the Bulk Image Generator platform:

- **Repository:** `github.com/buildngrowsv/Bulk-Image-Generator-Platform`
- **Brainstorm feature module:** `src/features/brainstorm/`
- **Key service files:**
  - `services/brainstormService.ts` — Main orchestrator implementing the three-stage pipeline (descriptor generation → prompt expansion → parallel image generation).
  - `services/conceptDescriptorService.ts` — Stage 1: LLM-driven concept descriptor generation with creative-director framing and structured JSON output.
  - `services/promptCreatorService.ts` — Stage 2: Per-descriptor prompt expansion via LLM.
  - `services/imageGenerationService.ts` — Stage 3: Parallel image generation via OpenAI Images API.
  - `services/diversityAlgorithmService.ts` — Diversity enforcement layer using Jaccard distance and farthest-first traversal.
  - `services/combinationService.ts` — Concept combination for iterative refinement.
- **Type definitions:** `types/brainstormTypes.ts` — Defines `ConceptDescriptor`, `Variant`, `Iteration`, `BrainstormSession`, and `BrainstormProject` data structures.
- **Prompt templates:** `constants/promptTemplates.ts` — System prompts for the creative-director decomposition framing and the detailed prompt expansion step.

The implementation currently uses GPT-4o for decomposition (Stages 1 and 2) and gpt-image-1 for generation (Stage 3), but the architecture is provider-agnostic and the services are designed for substitution.

## 8. Public-Domain Dedication

This disclosure and the method described herein are dedicated to the public domain under the **Creative Commons CC0 1.0 Universal Public Domain Dedication**.

To the extent possible under law, the author has waived all copyright and related or neighboring rights to this work. This work is published from the United States.

This disclosure is intended to serve as prior art under 35 U.S.C. § 102(a)(1) against any patent claims covering the methods described herein, including but not limited to: prompt decomposition for image generation, LLM-driven creative direction generation, divergent prompt expansion, parallel multi-provider image generation, diversity-enforced creative output, and gallery assembly from decomposed prompts.

See: https://creativecommons.org/publicdomain/zero/1.0/

## 9. Limitations and Disclaimer

- This disclosure describes a software method. It does not claim to be the only way to achieve creative diversity in image generation, nor does it claim that the method produces optimal creative output in all cases.
- The quality and diversity of output depends on the capabilities of the LLM used for decomposition and the image generation APIs used for rendering. Weaker models may produce less divergent descriptors; lower-quality image APIs may produce less visually distinct results.
- The Jaccard distance metric for diversity enforcement is a simple token-overlap measure. More sophisticated semantic similarity measures (embedding cosine distance, BERTScore, etc.) could improve diversity guarantees but are not required for the method to function.
- The iterative refinement loop (select, reject, combine, pivot) depends on user interaction and is not fully automated in the current implementation.
- This disclosure is not legal advice. It is a technical description of a software method intended for defensive prior art purposes. Consult a patent attorney for legal guidance on specific patent claims.
- Provider-specific API terms, rate limits, and pricing are outside the scope of this method disclosure.

## References

- OpenAI. (2024–2026). Images API documentation. https://platform.openai.com/docs/guides/images
- OpenAI. (2025). GPT-image-1 model documentation. https://platform.openai.com/docs/models
- Stability AI. (2023–2026). Stable Diffusion API documentation. https://platform.stability.ai/docs/api
- Midjourney. (2023–2026). Midjourney API and documentation. https://docs.midjourney.com/
- Jaccard, P. (1912). "The distribution of the flora in the alpine zone." *New Phytologist*, 11(2), 37–50.
- Gonzalez, T. F. (1985). "Clustering to minimize the maximum intercluster distance." *Theoretical Computer Science*, 38, 293–306. (Farthest-first traversal algorithm.)
- Brown, T. B., et al. (2020). "Language Models are Few-Shot Learners." *Advances in Neural Information Processing Systems*, 33.
- Ramesh, A., et al. (2022). "Hierarchical Text-Conditional Image Generation with CLIP Latents." arXiv:2204.06125.
- 35 U.S.C. § 102 — Conditions for patentability; novelty. https://www.bitlaw.com/source/35usc/102.html
- MPEP § 2131 — Anticipation. https://www.uspto.gov/web/offices/pac/mpep/s2131.html
- MPEP § 2121 — Prior Art; Enablement. https://www.uspto.gov/web/offices/pac/mpep/s2121.html
- Creative Commons. CC0 1.0 Universal Public Domain Dedication. https://creativecommons.org/publicdomain/zero/1.0/