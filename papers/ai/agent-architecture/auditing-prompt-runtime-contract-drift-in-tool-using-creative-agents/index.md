---
title: "Auditing Prompt Runtime Contract Drift in Tool-Using Creative Agents"
paper_id: "2026-148"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-05-15T09:27:11Z"
abstract: "This case study documents a prompt-runtime contract audit pattern from GenFlick, a tool-using creative agent whose system prompt described actions that had to survive parser, dispatcher, and state-store layers. The audit compared four independent sources of truth: TypeScript action unions, dispatcher switch cases, parser valid-type filters, and the prompt action list shown to the model. It found that two documented actions, reorder_scenes and move_clip, were wired in the type and dispatcher layers but omitted from the parser allow-list, causing silent drops. It also found vocabulary drift, dead actions, aspirational claims, and costly prompt sections that no longer mapped cleanly to runtime behavior. Live evals and a real user export then exposed deeper issues, including an action that could mark a clip image-ready using a copied still rather than a generated image. The lesson is that agent prompts should be audited as runtime contracts, not just text."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted by a Codex agent from GenFlick prompt/action audit notes, especially docs/CHAT-AGENT-PROMPT-VS-AVAILABLE-ACTIONS-AUDIT-2026-04-20.md."
---

## Problem

Tool-using agents live or die by the contract between the instructions given to the model and the runtime that interprets model output. If the prompt says an action exists but the parser drops it, the user may see confident assistant text while nothing happens. If the prompt gives one vocabulary and the state model uses another, the model spends reasoning budget translating mismatched concepts. If the prompt claims a capability that is only aspirational, downstream behavior becomes unpredictable.

GenFlick's chat agent is a useful case because its prompt is not merely a style guide. It documents actions that create scenes, add clips, update characters, use frames for continuity, set acts, generate media, and alter project state. The runtime then parses a `json:actions` block, validates action types, dispatches changes, and updates a client-side project store.

The audit asked a simple question: does the model-facing prompt describe what the runtime actually permits?

## Method

The audit compared action definitions across four surfaces.

First, it inspected the TypeScript discriminated union that defines the available chat actions. Second, it inspected the dispatcher switch cases that apply those actions to project state. Third, it inspected the parser's valid action-type set. Fourth, it inspected the prompt action list shown to the model.

The key was not to assume that any one layer was authoritative. In a growing tool-using agent, separate lists often drift. A new action can be added to the type union and dispatcher but forgotten in the parser. A deprecated action can remain in the prompt. A prompt example can omit a required field that the type layer now expects.

After the static audit, live model evals were run against real model calls without relying solely on code inspection. This matters because a drift bug is only operationally severe if the model is likely to emit the affected action. The evals confirmed that it did.

## Findings

The highest severity bug was a silent action drop. `reorder_scenes` and `move_clip` were present in the TypeScript action union, implemented in the dispatcher, and documented in the prompt. They were missing from the parser's valid-type set. A model could say it had reordered scenes or moved a clip, emit the intended action, and have the parser skip it.

The second finding was vocabulary drift. Several actions used the word "scene" even though they operated on clips. Another action operated on true scene groups. The prompt had to spend substantial space explaining the difference. This is a tax on the model and a source of mistakes. Better action naming or a clearer `target_kind` model would let the prompt shrink and become less ambiguous.

The third finding was aspirational capability language. The prompt said the system defaulted to cinematic widescreen unless told otherwise, but at the time there was no chat action to change aspect ratio. It described title-card behavior, but title cards were just text flowing into an image prompt rather than a special rendering path. It described lip-sync guidance in a way that varied by provider. These were not necessarily lies, but they blurred the line between model intent and runtime capability.

The fourth finding was dead or redundant actions. Some media-generation actions were listed even though the prompt simultaneously told the model it usually did not need them because other actions auto-queued media. Keeping such actions in the prompt increased cognitive load and risked unwanted side effects.

The fifth finding was prompt bulk. A large prompt can be justified if it maps cleanly to runtime behavior, but long examples and repeated pedagogy become harder to maintain when the action contract is moving. The audit argued for separating stable playbook material from the minimal action contract that every turn needs.

## Empirical Confirmation

The static audit predicted that the parser would drop `reorder_scenes` and `move_clip`. Live evals confirmed that the model would emit those actions in relevant scenarios. This moved the bug from theoretical to operational.

Another eval surfaced a worse pattern. When the model lacked a proper aspect-ratio action, it tried to substitute by recreating scenes with a destructive clear-existing flag. That showed a subtle danger: when the action contract lacks an obvious capability, the model may use a nearby capability in a way the product did not intend.

A later real-user export exposed a separate issue around frame reuse. A `use_scene_frame` action with starting-image semantics could copy a source clip's still preview onto a target clip and mark the target image-ready even when the source clip had no rendered video. The visible result was duplicate thumbnails and an apparently ready clip without a genuine generated image behind it. Synthetic evals missed this because they did not simulate the same in-flight image/no-video state.

## Remediation Principles

The first remediation principle is to derive parser allow-lists from the action type source of truth where possible. Manual valid-type sets are drift traps.

The second principle is to test the contract end to end. A unit test that confirms an action parses is useful, but the stronger test is model output through parser, dispatcher, project state, and user-facing receipt.

The third principle is to treat action names as prompt design. Names like `update_scene` that mean "update clip" are not harmless implementation details. They become part of the model's language environment.

The fourth principle is to remove or hide dead actions. If an action should not normally be used, the cleanest prompt is often one that does not list it.

The fifth principle is to feed dispatch feedback back to the model. In the frame-reuse fix, coercing an invalid starting-image request to safer reference semantics was not enough. The runtime also needed to report the coercion so subsequent model turns could reason from what actually happened.

## Limitations

This case study is based on a private production repository, so the full code path cannot be independently verified from the public article. The method, however, is general and can be reproduced in any tool-using agent: list the model-facing actions, list every runtime gate, compare them, then run model-output evals that exercise the mismatches.

## Conclusion

A tool-using agent prompt is a runtime contract. It should be audited with the same seriousness as an API schema. GenFlick's audit found silent parser drops, vocabulary drift, aspirational claims, redundant actions, and state-dependent failures that only appeared in real user exports. The practical pattern is straightforward: maintain one action source of truth, keep prompt language aligned to runtime capabilities, run live model evals on likely edge cases, and verify that dispatch receipts tell both users and future model turns what actually happened.