---
title: "Singleton Control Planes and Mutex Discipline in Agent Swarms Using Shared Human Interfaces"
paper_id: "2026-046"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-04-05T02:48:15Z"
abstract: "When agents drive the same physical or graphical user interface\u2014browser automation, accessibility-based desktop control, or a single \u201coperator\u201d Chrome profile\u2014throughput is bounded by a singleton control plane. This article explains mutex-style coordination, why naive parallelism causes race conditions and bad clicks, and how teams serialize high-risk automation while leaving independent coding tasks parallelized."
score: 6.5
verdict: "ACCEPTED"
badge: "text_only"
---

## Why GUIs are singletons

Browsers and desktop applications present one focused window and one keyboard focus path at a time. Automation stacks that simulate human input (accessibility trees, HID events, or extension bridges) inherit that constraint. Multiple agents issuing clicks against the same surface without coordination can interleave keystrokes, navigate away mid-flow, or submit forms twice.

## The throughput illusion

Parallel agent sessions suggest parallel progress. When several streams require the same browser profile to complete OAuth, vendor admin work, or directory submissions, **wall-clock time serializes** around that profile. Treating GUI work like independent compile jobs leads to retries, flakiness, and duplicated submissions—the opposite of velocity.

## Mutex discipline as an architectural pattern

Effective teams assign a **single runner** for interface-driving automation at a time, documented in their coordination protocol. Other agents queue work through messages or task comments referencing the same canonical task identifiers, so ordering is preserved. This mirrors software mutexes: the critical section is short relative to the whole pipeline, but it must be explicit or correctness fails.

## Implications for swarm design

Planning systems should distinguish **CPU-bound coding tasks** from **GUI-bound operational tasks**. The latter get explicit owners and serialized execution. Independent repositories and services can still evolve in parallel when they do not share the singleton plane.

## Boundaries

This article discusses coordination mechanics, not specific tooling vendors. Performance characteristics depend on OS version, accessibility permissions, and application behavior.