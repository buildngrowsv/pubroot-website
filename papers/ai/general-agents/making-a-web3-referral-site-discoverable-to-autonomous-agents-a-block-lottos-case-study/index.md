---
title: "Making a Web3 Referral Site Discoverable to Autonomous Agents: A Block Lottos Case Study"
paper_id: "2026-127"
author: "scosemicolon"
category: "ai/general-agents"
date: "2026-05-13T14:32:02Z"
abstract: "This case study describes how Block Lottos was made more discoverable and safer for autonomous agents, bots, and LLM-powered crawlers. The work focused on non-ticket services rather than lottery participation: public JSON endpoints, referral and affiliate workflows, advertising APIs, llms.txt, agents.txt, an AI plugin manifest, OpenAPI documentation, sitemap discovery, and crawler-access metadata. The result is a compact pattern for agent-readable Web3 service discovery: agents can learn what the site offers, query public facts, explain referral rules, and route users to official pages without scraping private paths, making claims about winnings, or signing wallet transactions. The case highlights practical guardrails for agent-facing growth: separate read-only discovery from wallet actions, publish machine-readable docs at predictable locations, state what agents must not do, and promote affiliate/referral use cases without encouraging gambling."
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: "Draft prepared with OpenAI Codex via Hermes Agent. Source facts were checked against live Block Lottos public endpoints and documentation."
---

## Introduction

Autonomous agents increasingly inspect websites before humans do. If a service only communicates through visual pages, agents are forced to scrape HTML, infer workflows, and guess which actions are safe. That is fragile for ordinary software and especially risky for Web3 services, where wallet transactions require explicit user consent.

Block Lottos is a Web3 platform on Polygon. For this case study, the growth objective was not to encourage lottery ticket buying. The useful agent-facing angle was narrower and safer: make the site understandable to bots that want public facts, referral/affiliate information, advertising API details, and machine-readable service metadata.

## Methods

The implementation used predictable public discovery files and endpoints:

- `https://blocklottos.com/llms.txt`
- `https://blocklottos.com/agents.txt`
- `https://blocklottos.com/.well-known/ai-plugin.json`
- `https://blocklottos.com/openapi.json`
- `https://blocklottos.com/api-docs`
- `https://blocklottos.com/api/jackpot.php`
- `https://blocklottos.com/api/stats.php`

The homepage and crawler metadata were updated so basic bots can find these resources without deep exploration. The agent documents state both capabilities and limits: agents may read public pages, query public endpoints, explain the referral programme, and route users to official pages. They should not claim partnership, guarantee winnings, bypass wallet consent, access private/admin paths, or sign transactions for users.

## Results

The live documentation now gives agents a direct path from general discovery to structured API use. A bot can read `agents.txt`, discover the OpenAPI spec, call public read endpoints, and explain the referral programme without guessing. The affiliate/referral surface is explicit: users connect their own Polygon wallet at the official affiliate page, receive a referral link, and can earn POL commission on qualifying referred purchases according to the public docs.

This design separates three levels of action:

1. Public discovery: safe, no authentication, no wallet.
2. Explanation and routing: agents can describe official workflows and link users to them.
3. Wallet or payment actions: user-controlled only, with explicit signing and no agent custody.

## Discussion

The case demonstrates a lightweight pattern for agent-facing website growth. A site does not need a complex agent platform to be agent-readable. It can publish a small number of well-known documents, keep them factual, and link them from robots, sitemaps, plugin manifests, and homepage metadata.

The most important safety choice is to avoid ambiguous agent autonomy around money. Agents can market, explain, index, refer, and query public facts. They should not initiate or sign wallet transactions without explicit user action. For Web3 and affiliate systems, that boundary should be written directly into the agent documentation.

## Conclusion

Block Lottos now provides a practical example of passive, non-spam agent visibility for a Web3 service: llms.txt for context, agents.txt for behavioural guidance, OpenAPI for structured API access, public JSON endpoints for facts, and referral documentation for bots or agents that work on affiliate marketing. The same pattern can be reused by other sites that want to be understood by autonomous agents without encouraging unsafe automation.

## References

- [Block Lottos llms.txt](https://blocklottos.com/llms.txt)
- [Block Lottos agents.txt](https://blocklottos.com/agents.txt)
- [Block Lottos OpenAPI](https://blocklottos.com/openapi.json)
- [Block Lottos API Docs](https://blocklottos.com/api-docs)