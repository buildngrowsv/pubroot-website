---
title: "\"File Ownership and Message Passing: A Practical Coordination Protocol for LLM Agent Swarms\""
paper_id: "2026-024"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-03-24T05:12:07Z"
abstract: "\"Multi-agent LLM systems face a fundamental coordination problem: how do you let 10-20 autonomous agents edit the same codebase simultaneously without merge conflicts, lost work, or incoherent output? This article presents a practical coordination protocol developed through production use in a 20-agent swarm that ships software across multiple repositories. The protocol rests on three mechanisms: a shared coordination board with strict file ownership, an asynchronous message-passing system, and a persistent task management layer. Tested across 8 concurrent builders with zero file conflicts.\""
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "\"Article drafted by Claude Opus 4.6 (Anthropic). Human operator reviewed before submission.\""
aliases:
  - "/2026-024/article/"
  - "/2026-024/"
---

## Abstract

Multi-agent LLM systems face a fundamental coordination problem: how do you let 10–20 autonomous agents edit the same codebase simultaneously without merge conflicts, lost work, or incoherent output? This article presents a practical coordination protocol developed through production use in a 20-agent swarm that ships software across multiple repositories. The protocol rests on three mechanisms: (1) a shared coordination board with strict file ownership that prevents write conflicts at the filesystem level, (2) an asynchronous message-passing system for inter-agent communication, and (3) a persistent task management layer that survives agent restarts. We describe each mechanism's design, the failure modes it prevents, and the tradeoffs involved. The protocol has been tested across 8 concurrent builder agents working on 8 different projects, with zero file conflicts and successful parallel commits to 6+ repositories in a single session.

## 1. The Coordination Problem in Multi-Agent Systems

When a single LLM agent works on a codebase, coordination is trivial — there is one writer, one context, one plan. But production workloads often benefit from parallelism: auditing security across five repos, shipping payment integrations for three products, or running test suites while another agent writes code. The moment you scale to multiple agents, three problems emerge:

**Write conflicts.** Two agents editing the same file produce inconsistent state. Git merge conflicts are the mild version — the severe version is Agent A overwriting Agent B's work entirely because neither knew the other was active. Unlike human developers who can shout across the room, LLM agents have no ambient awareness of each other's actions.

**Stale context.** Each agent operates within its own context window. Agent A may spend 20 minutes researching the current state of a file, only to discover that Agent B rewrote it during that time. The agent has no way to know its mental model is outdated unless something actively notifies it.

**Lost handoffs.** LLM agent sessions are ephemeral. When an agent's context window fills up, it compacts or restarts. Any in-progress work that was not persisted — plans, discoveries, partial implementations — vanishes. The next agent starts from scratch, repeating research and potentially making different (conflicting) decisions.

These are not theoretical problems. In early swarm sessions without coordination, we observed: agents overwriting each other's commits, duplicate work where two agents independently wrote the same test file, and agents going idle because they did not know work was available.

## 2. The Coordination Board: Static File Ownership

The core mechanism is a shared markdown file (`SWARM_BOARD.md`) that acts as a coordination hub. Every agent reads it before starting work and updates it as they progress. The critical section is the **Task Breakdown table**:

```
| ID | Task | Owner | Owned Files | Depends On | Status |
|----|------|-------|-------------|------------|--------|
| T1 | Payment integration | Builder 3 | PaymentManager.swift, SubscriptionView.swift | — | BUILDING |
| T2 | Test suite | Builder 4 | _review_agent/test_*.py | — | DONE |
| T3 | Security audit | Builder 5 | Accountabilityv6/** | — | BUILDING |
```

The **Owned Files** column is the enforcement mechanism. The rule is absolute: you may only write to files listed in your row. If you need to modify a file owned by another agent, you escalate to the coordinator. This eliminates write conflicts entirely at the protocol level — not through locks or transactions, but through static partitioning.

### Why Static Partitioning Over Dynamic Locking

An alternative approach would be file-level locks: agents acquire a lock before editing and release it after. We rejected this for three reasons:

1. **LLM agents cannot reliably manage locks.** An agent that crashes, compacts, or times out will not release its lock. Implementing lock timeouts adds complexity and introduces a window where two agents believe they hold the same lock.

2. **Static ownership enables planning.** When the coordinator assigns tasks, it must think about file boundaries upfront. This forces decomposition into naturally independent units of work — which is good software engineering practice regardless of whether agents or humans do the work.

3. **Simplicity.** A markdown table is readable by any agent, any human, and any tool. There is no lock server to maintain, no race conditions to handle, no distributed consensus to achieve. The coordination mechanism is a text file.

### The Role Taxonomy

The protocol defines four agent roles:

- **Coordinators** decompose the goal into tasks, assign file ownership, and monitor progress. They are the only agents who write to the Task Breakdown table.
- **Builders** execute implementation tasks. They write code, run tests, and commit. Each builder owns a distinct set of files.
- **Scouts** perform read-only research. They explore codebases, search documentation, and report findings. Scouts own no files and make no edits, which means any number of scouts can operate in parallel without conflict.
- **Reviewers** inspect completed work for bugs, style issues, and integration problems. They read builder output but do not edit it — review feedback flows through the message-passing system.

This taxonomy maps naturally to how human engineering teams operate: tech leads (coordinators), developers (builders), researchers (scouts), and code reviewers (reviewers). The key difference is that role boundaries are enforced by the protocol rather than by social convention.

## 3. Message Passing: Asynchronous Inter-Agent Communication

Agents need to communicate without sharing a context window. The solution is `bs-mail`, a lightweight message-passing system implemented as a CLI tool:

```bash
# Send a message to a specific agent
bs-mail send --to "Builder 5" --body "Security audit found 8 hardcoded API keys"

# Send to all agents
bs-mail send --to @all --body "Merge freeze in 10 minutes"

# Check for new messages
bs-mail check
```

Messages have four types:
- **message**: General communication (research findings, status updates, questions)
- **status**: Concise progress updates for the coordination board
- **escalation**: Request for help — goes to the coordinator or operator
- **worker_done**: Signals task completion, triggering the review phase

### Design Decisions

**Asynchronous, not synchronous.** Agents check mail at their own pace (typically every 30–60 seconds during idle periods). There is no blocking receive. This prevents an agent from stalling its entire context window waiting for a response that may take minutes.

**No guaranteed delivery order.** Messages are appended to a shared store. An agent may see messages out of order if multiple agents send simultaneously. The protocol tolerates this because messages are informational — the coordination board is the source of truth for task state, not messages.

**Pull, not push.** Agents poll for messages rather than being interrupted. This is a deliberate choice: LLM agents cannot handle interrupts mid-reasoning. A push notification arriving while an agent is writing code would corrupt its chain of thought. Polling at natural breakpoints (between tasks, during idle loops) preserves reasoning coherence.

## 4. Persistent Task Management: Surviving Restarts

The coordination board and message system handle intra-session coordination. But swarm sessions end — context windows fill up, terminal sessions close, or the operator explicitly restarts the swarm. The third layer handles cross-session persistence.

We use a combination of:

1. **Handoff documents.** When a session ends, each agent writes a structured handoff to `handoffs/<Agent>-handoff-<date>.md` containing: what was worked on, what was completed, what is in progress, what is blocked, and what should happen next. The next session's agents read these handoffs before starting.

2. **External task management (BridgeMind MCP).** An MCP server provides a persistent kanban board that survives all session boundaries. Agents create tasks, update status, and add knowledge notes. The task state in BridgeMind is the authoritative record of what has been done and what remains — it is not affected by context window compaction or session restarts.

3. **Git as persistence.** Completed work is committed and pushed immediately. This is the strongest form of persistence — even if all coordination infrastructure fails, the code is safe in the remote repository. The protocol mandates atomic commits after each task completion, not batched commits at session end.

### The Handoff Problem

The most fragile moment in multi-session swarm work is the handoff. Agent A spent 45 minutes researching a codebase, found the right approach, wrote half the implementation — and then the session ends. Agent B starts fresh. Without handoff documents, Agent B repeats the research, potentially arrives at a different approach, and may conflict with Agent A's partial work.

Handoff documents solve this by encoding the agent's accumulated knowledge in a structured format that the next agent can consume in seconds rather than minutes. A well-written handoff includes:

- **Files changed** (with paths and a one-sentence description of each change)
- **Key decisions made** (with the reasoning — why this approach and not the alternative)
- **What is blocked** (with the specific blocker, not just "needs human help")
- **What is next** (the specific next action, not a vague goal)

The quality of handoffs directly determines swarm continuity. A vague handoff ("worked on payments, needs more work") forces the next agent to re-derive the entire context. A specific handoff ("integrated Paddle SDK in LicenseManager.swift using PaddleDelegate pattern, verified compile but untested — next: write unit test for license state machine transitions") lets the next agent start immediately.

## 5. Failure Modes and Mitigations

### Agent Goes Idle

Symptom: An agent finishes its task and stops working, even though more work is available.

Cause: The agent does not know to poll for new assignments after completing a task.

Mitigation: The protocol requires agents to poll `bs-mail check` every 30–60 seconds after task completion. The swarm instructions explicitly state: "After completing a task, keep polling for follow-up work. Do NOT go idle."

### Coordinator Bottleneck

Symptom: Multiple builders finish simultaneously and wait for the coordinator to assign new work.

Cause: A single coordinator cannot decompose and assign tasks as fast as builders consume them.

Mitigation: Use multiple coordinators. In our 20-agent configuration, we run 3 coordinators. Coordinators share write access to `SWARM_BOARD.md` — the only file with shared ownership. Contention is rare because coordinators operate on different sections (one assigns tasks, another monitors progress, the third handles escalations).

### Stale Board Reads

Symptom: Agent reads the board, sees a task as OPEN, begins working on it — but another agent already claimed it.

Cause: Two agents read the board in the gap between one agent's read and its subsequent write.

Mitigation: The protocol accepts this as a low-probability event (in practice, we have not observed it with 20 agents) and handles it via escalation. If an agent discovers another agent is already working on "its" task, it stops and escalates. The coordinator reassigns. The cost of occasional duplicate work initiation is lower than the cost of implementing distributed locking.

## 6. Results and Observations

In a production session with 20 agents (3 coordinators, 8 builders, 6 scouts, 3 reviewers) working across 8 projects simultaneously:

- **Zero file conflicts** across all concurrent builders
- **200+ tests committed** to one repository (Pubroot review pipeline)
- **Security remediations** completed for two iOS apps (removing 8+ hardcoded API keys)
- **6+ repositories** received commits in a single swarm session
- **Average task completion time**: 15–25 minutes per builder task
- **Cross-agent communication**: 40+ bs-mail messages exchanged
- **Handoff quality**: All agents produced structured handoffs enabling session continuity

The primary bottleneck was not coordination — it was **human-dependent tasks**. Several tasks required authentication (Cloudflare login, Paddle vendor account creation, API key rotation) that agents could not complete autonomously. A future improvement would be automated credential provisioning for known services.

## 7. Comparison with Existing Approaches

### CrewAI and LangGraph

Frameworks like CrewAI and LangGraph provide multi-agent orchestration at the API level. They manage agent spawning, message routing, and task graphs programmatically. Our protocol is deliberately lower-tech: it uses markdown files and CLI tools rather than a runtime framework. This makes it tool-agnostic (works with any LLM that can read files and run commands), inspectable (humans can read the board and messages directly), and resilient (no framework server to crash).

The tradeoff is that our protocol requires agents to be cooperative — there is no runtime enforcement of file ownership. An agent could theoretically ignore the board and edit any file. In practice, LLM agents follow instructions reliably when the rules are clear and prominently stated.

### Git Branch-Per-Agent

An alternative to file ownership is giving each agent its own git branch. This eliminates write conflicts through git's branching mechanism. We rejected this because: (1) merging N branches back to main introduces integration conflicts that are harder to resolve than preventing them, (2) agents on separate branches cannot see each other's work-in-progress, and (3) branch management adds cognitive load for agents that could be spent on actual work.

## 8. Conclusion

The coordination protocol presented here — static file ownership via a shared board, asynchronous message passing, and persistent task management — enables 20 LLM agents to work on a multi-project codebase simultaneously without conflicts. The key insight is that simplicity beats sophistication: a markdown table enforces file ownership more reliably than a distributed lock manager, and polling-based messaging respects the sequential nature of LLM reasoning better than interrupt-driven architectures.

The protocol is deliberately minimal. It solves the three core problems (write conflicts, stale context, lost handoffs) with the lowest-complexity mechanisms that work in practice. As LLM agent capabilities improve — particularly around long-running sessions and persistent memory — some of these mechanisms may become unnecessary. But for the current generation of context-window-limited agents, this protocol provides a practical foundation for parallel software engineering at scale.