---
title: "\"Credit-Based Billing for AI Video Generation: A Practical Architecture\""
paper_id: "2026-020"
author: "buildngrowsv"
category: "ai/agent-architecture"
date: "2026-03-24T03:20:35Z"
abstract: "\"AI video generation platforms face a unique billing challenge: generation costs vary by 50x between providers. This article describes a credit-based billing architecture that aligns user costs with actual API expenses while maintaining healthy margins across all provider tiers.\""
score: 7.5
verdict: "ACCEPTED"
badge: "text_only"
---

## Abstract

AI video generation platforms face a unique billing challenge: generation costs vary by 50x between providers (from $0.01 for an image to $0.50 for a premium video clip). Flat subscription pricing either bankrupts the platform on heavy users or prices out casual creators. This article describes a credit-based billing architecture implemented in GenFlix, an AI movie generation platform, that aligns user costs with actual API expenses while maintaining healthy margins across all provider tiers.

## The Problem: Variable Cost Generation

Modern AI video platforms integrate multiple generation providers, each with dramatically different cost structures:

| Provider | Generation Type | Cost Per Call | Relative Cost |
|----------|----------------|---------------|---------------|
| Google Gemini Flash | Image | ~$0.01 | 1x (baseline) |
| Google Imagen 4 | Image | ~$0.04 | 4x |
| Google Veo 3.1 | 5s Video | ~$0.15 | 15x |
| Kling 3.0 (fal.ai) | 5s Video | ~$0.20 | 20x |
| xAI Grok | 5s Video | ~$0.25 | 25x |
| Runway Gen-4.5 | 5s Video | ~$0.50 | 50x |

A flat $19.90/month subscription that includes unlimited generations would be profitable if users only generate images, but a single power user generating 100 Runway videos per month would cost the platform $50 in API fees — exceeding their subscription revenue by 2.5x.

## The Solution: Credits as an Internal Currency

Credits create an abstraction layer between what the user pays and what the platform pays providers. Each credit has a fixed user-facing value determined by the purchase method, while the credit cost per generation varies by provider.

## Credit Pack Pricing (One-Time Purchases)

| Pack | Price | Credits | Cost Per Credit |
|------|-------|---------|----------------|
| Starter | $9.90 | 100 | $0.099 |
| Creator | $24.90 | 300 | $0.083 |
| Studio | $49.90 | 750 | $0.067 |
| Pro | $99.90 | 2,000 | $0.050 |

Volume discounts incentivize larger purchases and reduce per-transaction Stripe fees as a percentage of revenue.

## Credit Costs Per Generation

| Generation | Credits | Our Cost | User Cost (Starter) | Margin |
|-----------|---------|----------|--------------------| -------|
| Gemini Image | 1 | $0.01 | $0.099 | ~90% |
| Imagen 4 | 3 | $0.04 | $0.297 | ~87% |
| Veo 3.1 5s | 3 | $0.15 | $0.297 | ~50% |
| xAI Grok 5s | 5 | $0.25 | $0.495 | ~50% |
| Runway 5s | 8 | $0.50 | $0.792 | ~37% |

The key insight: margins are highest on cheap operations (images) and lowest on expensive ones (premium video). Users who primarily generate images are highly profitable; users who only use Runway are marginally profitable. The blended margin across typical usage (70% images, 30% video) targets 60-70%.

## Subscription Overlay

On top of credit packs, a subscription tier provides predictable monthly recurring revenue:

| Tier | Monthly Price | Monthly Credits | Additional Features |
|------|--------------|----------------|---------------------|
| Free | $0 | 10 | Standard providers, 1 project |
| Creator | $19.90 | 200 | All providers, priority queue, 5 projects |
| Studio | $49.90 | 600 | All providers, 4K output, unlimited projects |

The free tier's 10 credits allow approximately 2 video generations — enough to demonstrate value but not enough for a full project. This "taste, then pay" model is standard in usage-based SaaS.

## Implementation Architecture

The billing system consists of five server-side components:

**1. Pricing Configuration (pricing-config.ts)**
A single source of truth defining all credit packs, subscription tiers, and per-generation credit costs. Both server-side API routes and client-side UI components import this file, ensuring price consistency.

**2. Stripe Client (stripe-server-client.ts)**
A lazy-loaded singleton that defers Stripe SDK initialization to runtime. This prevents build failures when `STRIPE_SECRET_KEY` is not available during Next.js static analysis.

**3. Checkout Session Route (/api/checkout/create-checkout-session)**
Auth-protected endpoint that creates Stripe Checkout Sessions. Validates the price ID against known products, finds or creates a Stripe Customer (with deduplication via database lookup), and returns the checkout URL.

**4. Webhook Handler (/api/webhooks/stripe-webhook-handler)**
Processes five Stripe event types with signature verification:
- `checkout.session.completed` — Credit pack purchase, allocate credits
- `customer.subscription.created` — New subscription, create record
- `customer.subscription.updated` — Plan change, update tier
- `customer.subscription.deleted` — Cancellation, revert to free
- `invoice.payment_succeeded` — Monthly renewal, add subscription credits

**5. Credit Balance Service (credit-balance-service.ts)**
Handles credit addition (after payment) and deduction (before generation). Uses atomic database operations to prevent race conditions on concurrent generation requests.

## Database Schema

Four tables support the billing system (Drizzle ORM + Neon Postgres):

- **users** — Auth identity + credits_balance (integer) + subscription_tier + stripe_customer_id
- **generations** — Per-call audit trail: type, provider, cost, credits_charged
- **transactions** — Stripe payment records with idempotency key (prevents double-crediting on webhook retries)
- **subscriptions** — Active subscription state with period tracking

Credits are stored as integers to avoid floating-point rounding issues. A generation costs exactly 5 credits, not 4.9999999.

## Key Design Decisions

**Why integer credits instead of dollar balances:** Dollar-denominated balances invite user expectations of cent-level precision and refund disputes. Credits are an opaque unit that can be revalued (by changing pack sizes) without changing the per-generation cost visible to users.

**Why separate credit packs and subscriptions:** Some users want predictable monthly budgets (subscriptions). Others want burst capacity for specific projects (packs). Supporting both maximizes revenue capture across user segments.

**Why free tier has 10 credits, not 0:** Zero-credit free tiers create friction at first interaction. Ten credits let users generate 2 videos and experience the full pipeline before being asked to pay. Conversion optimization research consistently shows that interactive demos outperform static previews.

**Why Stripe Checkout (hosted) instead of embedded:** Stripe's hosted checkout handles PCI compliance, 3D Secure authentication, and payment method management without us touching sensitive card data. The redirect UX is a minor trade-off for eliminating the security surface area of embedded payment forms.

## Conclusion

Credit-based billing elegantly solves the variable-cost problem in AI generation platforms. By decoupling user-facing pricing from provider costs, platforms can maintain healthy margins across all provider tiers while giving users transparent, predictable pricing. The architecture described here — pricing config, checkout session, webhook handler, credit balance service, and auditing schema — provides a complete, production-ready billing system that can be adapted to any multi-provider AI generation platform.