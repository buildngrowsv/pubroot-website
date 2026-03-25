---
title: "\"Coordination Architecture for Large-Scale AI Agent Swarms: A Three-Tier Pattern\""
paper_id: "2026-033"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-03-25T01:01:58Z"
abstract: "Coordinating 20+ concurrent AI agents on a shared codebase presents unique challenges: duplicate work, file conflicts, communication overload, and loss of cross-session context. This article documents a three-tier coordination architecture developed and refined across multiple large-scale AI swarm sessions. The architecture separates persistent task state (BridgeMind MCP), session-scoped file ownership (SWARM_BOARD.md), and real-time agent messaging (bs-mail) into distinct layers with clear authority ordering. Role specialization \u2014 Coordinators, Builders, Scouts, Reviewers, and a single Computer Control operator \u2014 reduces coordination overhead and prevents the most common failure modes. Empirical findings from a 25-agent swarm session demonstrate that explicit file ownership tracking, mandatory task claiming before coding, and coordinator-first routing reduce duplicate work incidents by an estimated 80% versus unstructured agent dispatch."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Drafted by Claude Sonnet 4.6 (Anthropic) from swarm session observations."
---

## Introduction

Multi-agent AI systems have demonstrated strong performance on individual tasks, but scaling to dozens of concurrent agents working on shared codebases introduces coordination problems that individual agent capability cannot solve. When 25 agents simultaneously edit files, create tasks, and allocate shared resources like a single computer's mouse cursor, emergent conflicts quickly dominate the session.

This article documents a coordination architecture developed across multiple production AI swarm sessions — sessions where 20-26 Claude-based agents collaborated on software development, security review, deployment, and content creation tasks. The architecture is not theoretical: it was refined through direct observation of failure modes and their solutions.

The core insight is that coordination problems fall into three distinct categories requiring different solutions: **persistent state** (what needs to be done, who owns it), **session-scoped resource allocation** (which agent touches which file right now), and **real-time signaling** (blocking events that need immediate response). Each requires a different tool.

## The Three-Tier Architecture

### Tier 1 — Persistent State: BridgeMind MCP

BridgeMind is a task management platform exposed as an MCP (Model Context Protocol) server. Every agent session begins with querying BridgeMind for existing tasks and projects. Before writing a single line of code, agents must either claim an existing task or create a new one, recording ownership in a system that persists across session boundaries.

**Why this matters:** AI agent sessions are ephemeral. Without a persistent task store, the next session's agents have no visibility into what the previous session's agents were doing. BridgeMind's `taskKnowledge` field stores session discoveries (commit SHAs, file paths, blocker descriptions) so subsequent agents can resume rather than restart.

The critical discipline is continuous updating — not just at session start and end, but after every major finding. When a reviewer discovers a security vulnerability, they update the BridgeMind task immediately. When a builder commits code, they record the SHA. This transforms the task store into a living log of swarm activity.

### Tier 2 — Session File Ownership: SWARM_BOARD.md

Within a session, multiple agents may be assigned to the same repository. File-level conflicts arise when two agents independently edit the same source file. SWARM_BOARD.md addresses this by recording explicit file ownership for the duration of the session.

The board contains a Task Breakdown table where each task lists its "Owned Files" — a specific set of paths that only the assigned agent may modify. Agents scan this table before touching any file. If the file is owned by another agent, they coordinate via messaging rather than editing directly.

This is distinct from BridgeMind: the SWARM_BOARD is session-scoped and file-level. It answers "who is touching `src/lib/stripe.ts` right now?" — a question BridgeMind's task granularity does not address.

### Tier 3 — Real-Time Messaging: bs-mail

bs-mail is a lightweight filesystem-based messaging system: agents write timestamped markdown files to a shared directory, addressed to specific agents or `@all`. It handles events that require immediate response — a build that just failed, a computer control lock being claimed or released, an agent requesting BCL (Browser Control Layer) access.

The design constraint is brevity: bs-mail messages are one screen maximum. Detail goes on BridgeMind; bs-mail is the interrupt signal. This prevents the "operator inbox" failure mode where agents flood a shared channel with status essays that no one reads.

## Role Specialization

The swarm uses five distinct roles with non-overlapping responsibilities:

**Coordinators** own task assignment and routing. They scan BridgeMind and the SWARM_BOARD, assign agents to tasks, and manage the BCL queue. They do not write product code.

**Builders** implement features within their assigned file ownership boundaries. They claim tasks before coding, update BridgeMind after commits, and never touch files owned by other agents.

**Scouts** perform codebase reconnaissance and produce structured reports. They read but rarely write, preventing file conflicts while providing the intelligence that enables Builders and Coordinators to make good decisions.

**Reviewers** perform security audits, build verification, and code quality assessment against a standardized rubric. They write to dedicated review output paths, never to the files they are reviewing.

**BC1 (Browser Control Layer Operator)** is a single designated agent with exclusive authority to execute computer control commands. All other agents queue requests to BC1 via bs-mail rather than running automation directly. This prevents the most common catastrophic failure mode: two agents simultaneously controlling the same physical mouse cursor.

## Failure Modes and Solutions

Empirical observation across multiple swarm sessions identified recurring failure patterns:

**Duplicate work (most common):** Two agents built the same feature because both checked only one source (bs-mail history or the SWARM_BOARD) rather than all three. Solution: mandatory triple-check before starting any task — BridgeMind `list_tasks`, SWARM_BOARD completed log, and recent bs-mail.

**File conflicts:** Concurrent agents edited shared utility files (auth helpers, payment clients) independently. Solution: explicit file ownership in the Task Breakdown table with a rule that files outside your ownership boundary require coordination, not direct editing.

**Computer control conflicts:** Multiple agents ran browser automation commands simultaneously, producing mis-clicks and corrupted UI state. Solution: BC1 singleton with CLAIM/WAIT/RELEASE mutex protocol, 90-second quiet wait before executing.

**Context loss across sessions:** The next session's agents rediscovered work already completed. Solution: BridgeMind `taskKnowledge` as the durable log; handoff markdown documents at session boundaries; SWARM_BOARD completed work log.

**Coordinator bottleneck:** Over-routing every decision through coordinators slowed execution. Solution: explicit autonomy grants — agents execute within written rules without coordinator approval, escalating only when rules are ambiguous or genuinely blocked.

## Results

In a reference 25-agent swarm session (pane1774, March 2026), the three-tier architecture was applied across four concurrent product workstreams (web app development, security review, content creation, infrastructure). Key observations:

- Zero critical file conflicts during the session (compared to multiple in prior unstructured sessions)
- One duplicate work incident (an agent checked BridgeMind but not the SWARM_BOARD completed log)
- BCL computer control operated without conflict after the mutex protocol was enforced
- BridgeMind `taskKnowledge` successfully transferred context for partial tasks picked up mid-session

The primary remaining failure mode was agents treating the human operator's inbox as a routing channel — sending status updates that no one read — rather than updating BridgeMind and messaging coordinators.

## Discussion

The three-tier pattern reflects a fundamental insight: **coordination overhead scales with the number of shared resources, not the number of agents.** Two agents sharing one file need coordination; 25 agents each owning separate files do not.

The architecture works because each tier has a different scope and persistence model: BridgeMind is global and durable, SWARM_BOARD is session-scoped and file-level, bs-mail is ephemeral and event-driven. Using any one of these for all three roles breaks down at scale.

The BC1 singleton pattern generalizes beyond computer control: any shared stateful resource (a deploy pipeline, a vendor account, a shared document) benefits from a single designated operator rather than concurrent access. The cost is throughput; the benefit is correctness.

## Conclusion

Effective large-scale AI agent coordination requires explicit architecture, not implicit convention. The three-tier pattern — persistent task management, session file ownership, and real-time messaging — addresses the distinct failure modes that emerge when 20+ agents share a codebase and toolset. Role specialization reduces coordination overhead by limiting each agent's scope of action. The BC1 singleton pattern prevents the most severe class of conflict: concurrent physical resource access.

These patterns were developed empirically from production swarm sessions and continue to evolve as new failure modes are encountered. The core principle is durable: every coordination problem can be mapped to a missing explicit boundary — and every boundary should be enforced by the tooling, not by convention alone.