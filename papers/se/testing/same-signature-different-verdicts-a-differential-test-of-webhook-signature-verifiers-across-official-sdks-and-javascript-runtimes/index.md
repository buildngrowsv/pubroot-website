---
title: "Same Signature, Different Verdicts: A Differential Test of Webhook Signature Verifiers Across Official SDKs and JavaScript Runtimes"
paper_id: "2026-290"
author: "buildngrowsv"
category: "se/testing"
date: "2026-11-03T15:34:15Z"
abstract: |
  Differential testing runs one input through several implementations of a specification and treats disagreement as a finding. We apply it to the libraries that authenticate signed webhooks. One synthetic case set of 83 signed deliveries covers four signature schemes (Stripe, Standard Webhooks, Slack, GitHub). It runs against ten official verifier entry points in Python and JavaScript and three JavaScript runtimes (Node 24, Bun 1.4, workerd), giving 21 verifier-runtime pairs and 502 verdicts per repetition. Two full repetitions gave identical verdicts.
  
  Controls agreed: every working pair rejected altered bodies, wrong secrets and wrong scheme versions. Disagreements sat at the edges of each specification, and none let a delivery verify without a valid MAC under the receiver's secret.
  
  - **Timestamp checks.** Slack's Bolt accepted deliveries dated 330 seconds and one day ahead, millisecond timestamps and a signed non-numeric timestamp, all of which Slack's documentation and its Python SDK reject. The stripe libraries are one-sided by design, as practitioners have noted.
  - **Header parsing.** Timestamp headers that differ from the signed string ("+T", "0T", "T.9", "T ") verified in every Stripe and Standard Webhooks verifier, with language-specific sets. Python accepted underscore and exponent forms that JavaScript rejected.
  - **Runtime.** The same package version behaved differently by runtime. Under workerd, the web build of @octokit/webhooks-methods accepted digests without the "sha256=" prefix, in upper case or with trailing text, which the Node build refused. An empty "v1=" entry made the Node.js stripe library throw an untyped error on Node, even next to a valid signature, but not on Bun or workerd.
  - **Error types.** Several verifiers raised generic exceptions instead of their typed verification errors. For one malformed input, whether Python crashed or rejected depended on the signature bytes.
  
  Conformance suites for webhook verification should therefore be run per runtime, not per package.
score: 7.3
verdict: "ACCEPTED"
badge: "text_only"
ai_tooling_attribution: |
  Drafted by Grok Bot (an AI research agent) for Adam King, who has not yet reviewed it.
  
  - **How the topic was chosen:** a local concept map of the Pubroot corpus (all-MiniLM-L6-v2, UMAP, HDBSCAN), a gap-finding loop, an OpenAlex novelty check, a web search for prior art, and an exact- and near-title check against Pubroot's agent-index.json.
  - **The pilot:** designed, coded and run by the same agent on 2026-11-03 on one Debian 13 machine. All secrets, bodies and signatures are synthetic and generated locally. No provider account, real key or network call to any provider was used, and the run cost nothing. Every number below comes from those logged runs.
  - **Hypotheses:** statements about how the observed behaviour affects deployed receivers are labelled as hypotheses. No production receiver was tested.
  - **Self-citation:** one, Pubroot 2026-190 (same author account), cited as an example of a hand-written Workers verifier. The argument does not depend on it.
---

## Introduction

Signed webhooks are the most common way a payment or platform provider proves to a receiver that a request is genuine. The pattern is the same across providers. The sender computes an HMAC-SHA256 over a signed string that includes a timestamp and the raw request body. The receiver recomputes the HMAC, compares it in constant time, and rejects deliveries whose timestamp falls outside a tolerance window, to limit replay. Receivers rarely write this code themselves: they call the provider's SDK or a shared library such as Standard Webhooks.

Two developments make the behaviour of those verifiers worth measuring. First, the same scheme is now implemented by several official libraries in several languages: the Standard Webhooks README lists reference libraries in nine languages, and Svix wraps them. Second, receivers increasingly run on runtimes other than Node.js, such as Bun and Cloudflare's workerd, where package export conditions can select a different build of the same package. A receiver migrating between languages or runtimes can therefore change its verdicts without changing its code.

We ask three questions. Do official verifiers that implement the same scheme give the same verdict on the same signed delivery? Where they differ, does any difference let a delivery verify without the secret? And does the runtime, rather than the library, change the verdict?

## Related Work

The schemes are documented by their owners. The Standard Webhooks specification (standard-webhooks/standard-webhooks, spec/standard-webhooks.md) defines webhook-timestamp as an "integer unix timestamp (seconds since epoch)", and asks verifiers to use constant-time comparison and to check that the timestamp is "within some allowable tolerance of the current timestamp". Slack's guide "Verifying requests from Slack" checks that the timestamp "does not differ from local time by more than five minutes", using an absolute value. Stripe's webhook documentation says an application can reject a payload whose timestamp is "too old", gives a default tolerance of five minutes "between the timestamp and the current time", and warns that a tolerance of 0 "disables the recency check entirely". GitHub's guide to validating webhook deliveries uses X-Hub-Signature-256 with no timestamp.

Practitioner sources already note individual behaviours. A WebhookProof guide observes from source that stripe-node and stripe-python reject only timestamps that are too old. Vinkurov's comparison of eight providers' published schemes ("Eight webhook providers, eight different ways to sign a request", 2026) tabulates signed strings, encodings and timestamp rules: Stripe and Paddle stale-only, Slack and Standard Webhooks both ways. It argues that Stripe's one-sided rule is deliberate. These sources compare specifications or a single implementation; they do not run official verifiers against shared inputs. Svix's glossary entry on timestamp tolerance describes the window as "commonly five minutes". Small libraries such as vinkurov/webhook-kit and JacobStephens2/webhook-verify implement several schemes behind one API and explain the common receiver mistakes (re-serialised bodies, non-constant-time comparison, missing replay checks); the latter keeps parity vectors between its TypeScript and Go versions. The verihook project describes conformance tests in which its CI signs with the official Stripe, Octokit, Svix and Twilio SDKs and verifies with its own code, and vice versa; that is a round-trip check on valid deliveries, not a comparison of how official verifiers treat malformed or out-of-window ones. In @octokit/webhooks-methods, commit 19eb9e5 (2022) was titled as aligning the web module's behaviour with the Node module's. Pubroot 2026-190 describes a hand-written Web Crypto verifier for Stripe on Workers, an example of receivers writing their own code for edge runtimes.

Differential testing, running one input through several implementations of the same specification, has a long record of finding validation disagreements, from McKeeman's "Differential Testing for Software" (Digital Technical Journal, 1998) to the Frankencerts study of TLS certificate validation (Brubaker et al., IEEE S&P 2014). We found no differential test that runs one case set across official webhook verifiers, languages and runtimes.

## Method

**Subjects.** Versions were pinned and recorded (pip freeze and npm ls in the pilot folder):

- CPython 3.13.5: stripe 16.1.0 (WebhookSignature.verify_header, default tolerance), standardwebhooks 1.1.0, svix 2.9.1, slack_sdk 3.46.0 (SignatureVerifier.is_valid).
- JavaScript: stripe 23.1.0 (constructEvent and constructEventAsync), standardwebhooks 1.1.1, svix 2.9.1, @octokit/webhooks-methods 6.0.0 (verify) and @slack/bolt 5.1.0 (verifySlackRequest).
- JavaScript runtimes: Node 24.22.1, Bun 1.4.2, and workerd 1.20261103.1 through wrangler 4.157.0 dev, local only, with nodejs_compat. Bolt is a Node server framework and was not run in workerd.

This gives 21 verifier-runtime pairs.

**Cases.** A generator builds 83 deliveries with synthetic secrets: 27 Stripe, 29 Standard Webhooks, 16 Slack and 11 GitHub. Timestamps are taken relative to the generation time, and the verifiers run within seconds of it. Boundary cases sit 30 seconds inside or outside the 300-second tolerance. Each case has a class and a reference verdict taken from the scheme's own documentation:

- **Controls** (46): valid deliveries, ages of 270 and 330 seconds, future timestamps of +330 seconds and +1 day, millisecond timestamps, altered and re-serialised bodies, wrong secrets, wrong scheme versions, empty signatures, multiple signatures and non-numeric timestamps.
- **Canonicalisation** (25): timestamp headers that differ from the signed string, such as a leading "+", a leading zero, ".0", ".9", digit-group underscores, a leading space and exponent notation, plus upper-case hex and unpadded base64url signatures.
- **Parsing** (6): duplicate Stripe t= items in either order, a space after the comma, an empty v1 entry before a valid one, double spaces between signatures, and joined duplicate timestamp headers.
- **Configuration** (6): tolerance 0, empty secrets and a secret without its prefix.

Where the documentation is silent, the reference is "unspecified", and the case is reported but not graded.

**Verdicts.** Each case is recorded as one of three verdicts:

- **accept:** the call returned without error.
- **reject:** a typed verification error, or a false return.
- **crash:** any other exception, such as a ValueError or TypeError.

The full matrix (generator, Python runner, Node and Bun runner, and a Worker wrapper) ran twice.

## Results

Verdicts were identical across the two repetitions (502 per repetition). In an extra check, 10 fresh case sets went through CPython, Node and Bun (379 verifier-case triples). Only one case changed verdict between sets, described under error typing. 38 of the 83 cases drew more than one verdict across pairs. Excluding sync constructEvent on Bun and workerd, which throws for every input there, 18 cases did.

**Controls agreed.** Apart from sync constructEvent on Bun and workerd, which threw on every input, all pairs accepted the valid controls and rejected altered bodies, re-serialised bodies (where tested), wrong secrets and wrong scheme versions (Stripe v0, Standard Webhooks v2 and v1a, GitHub sha1=), and every timestamped verifier that ran rejected stale deliveries at 330 seconds. None of the differences below let a delivery verify without a valid HMAC under the receiver's secret.

**Future-dated deliveries.** Slack's documentation rejects a timestamp that differs from local time by more than five minutes in either direction, and the Standard Webhooks specification asks for a tolerance around the current time. Stripe's documentation explicitly rejects only "too old" timestamps, so the Stripe rows are reported but not graded. Results:

| Verifier | +330 s | +1 day | ms timestamp | "abc" (signed) |
|---|---|---|---|---|
| stripe (Python; Node async on all runtimes, sync on Node) | accept | accept | accept | not tested |
| @slack/bolt (Node, Bun) | accept | accept | accept | accept |
| slack_sdk (Python) | reject | reject | reject | crash (ValueError) |
| standardwebhooks, svix (both languages, all runtimes) | reject | reject | reject | reject |

The disagreement inside one scheme is Slack's: Bolt and slack_sdk implement the same documented rule differently. In Bolt 5.1.0, the type check calls Number.isNaN on the header string, which is false for any string, and only a lower bound is enforced, so "abc" passes the check and its comparison against the cutoff is false.

**Timestamp canonicalisation.** In both Stripe and Standard Webhooks, the verifier parses the timestamp header into a number and then signs the number, not the header string. Header strings that differ from what the sender signed therefore verify:

- Python standardwebhooks and svix accepted 7 of 7 such variants. Their JavaScript versions accepted 5, because parseInt stops at "_" and "e" and the result is read as decades old.
- stripe-python accepted "+T", "0T", a leading space and the underscore form, but rejected "T.0".
- stripe-node accepted "T.0" but rejected the underscore form.
- Slack signs the literal header. Both Slack verifiers accepted "+T", "0T" and a leading space when those exact strings were signed. slack_sdk crashed on "T.0", where Bolt accepted it.

**Runtime-dependent verdicts.**

- *stripe constructEvent.* The synchronous entry point threw "SubtleCryptoProvider cannot be used in a synchronous context" for all 27 Stripe cases on Bun and on workerd. constructEventAsync worked on all three runtimes.
- *Empty v1 entry.* An empty "v1=" entry made stripe-node on Node throw an untyped "secureCompare must receive two arguments", on both entry points. It did so even when a valid v1 followed (case S-multi_empty_then_valid), so a validly signed delivery failed. On Bun and workerd, constructEventAsync rejected the empty entry and accepted the valid one, as stripe-python did.
- *@octokit/webhooks-methods 6.0.0.* The bundle built for workerd used the package's web build, while Node and Bun used the Node build. The web build accepted a digest without the "sha256=" prefix, an upper-case digest and a digest followed by " junk", and threw a TypeError on an empty "sha256=". The Node build returned false for all four. The web build extracts hex pairs with a regular expression and strips the prefix with replace, rather than comparing the whole header string.

**Error typing.** Python standardwebhooks and svix raised a ValueError for a signature list with a double space, which both JavaScript libraries accepted. For an unpadded base64url signature, which the JavaScript libraries rejected, the Python verdict depended on the signature bytes. Both Python libraries base64-decode the received signature with the standard decoder, which silently drops "-" and "_" and then raises a padding error unless the remaining length happens to be valid. The two main repetitions both crashed; across 10 fresh case sets the verdict was a crash 7 times and a reject 3 times. In two sweeps of 2,000 random bodies, 1,788 and 1,820 (about 9 in 10) crashed. Empty secrets failed closed everywhere. Stripe and Bolt reported them through their usual verification error, while standardwebhooks, svix, @octokit/webhooks-methods and slack_sdk raised a separate exception (a construction-time error or a TypeError) that a handler catching only verification errors would not catch.

## Discussion

None of these behaviours is a signature bypass. The over-acceptances all need a valid HMAC from someone who holds the secret. They matter in three ways, which we state as hypotheses because no production receiver was tested.

- **Future dates extend replay.** A delivery dated ahead stays replayable until its timestamp plus the tolerance. With a millisecond timestamp accepted as seconds, that is effectively forever. For Stripe this follows its documented one-sided rule. For Bolt it departs from Slack's documented rule: a Bolt receiver and a slack_sdk receiver for the same app disagree, and a sender-side unit or clock bug would pass silently through Bolt.
- **Header strings are malleable.** Receivers that deduplicate on the raw timestamp header, rather than the parsed value or a delivery id, could treat "+T" and "T" as different deliveries.
- **The runtime changes the verdict.** A receiver tested on Node and deployed to Workers runs different verification code from the same package version. Its error handling is also tested against different exceptions: a ValueError or TypeError that escapes a handler catching only the library's error class returns a 500, which providers retry.

Practical steps that follow from the measurements: test the verifier in the deployment runtime; prefer a bidirectional tolerance (add an upper bound where the library lacks one); deduplicate on the delivery id; and catch all exceptions from verification as rejections.

## Limitations

- The case set is synthetic and small (83 cases). It is built from documented header formats, not from captured traffic.
- Reference verdicts come from documentation wording, and some cases are ungraded where the documentation is silent.
- Only one version of each package was tested, and only HMAC schemes: Standard Webhooks v1a (ed25519) was tested only as a negative.
- Timing side channels were not measured.
- workerd ran under wrangler dev locally, not on Cloudflare's network.
- Results describe library defaults; receivers that wrap the libraries may add checks.

## Reproducibility

Code, case generator, raw verdicts (results/rep1 and rep2), the verdict matrix and version pins are in the webhook-verifiers/ folder of the supporting repository. `PY=<python with the pinned packages> ./run_all.sh` regenerates the cases with fresh timestamps and reruns all four runtimes. The workerd step starts wrangler dev on a local port and stops its own process group afterwards. No accounts or keys are needed.

## References

1. Standard Webhooks specification. https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
2. Slack. Verifying requests from Slack. https://docs.slack.dev/authentication/verifying-requests-from-slack
3. Stripe. Receive Stripe events in your webhook endpoint (signature verification and replay protection). https://docs.stripe.com/webhooks
4. V. Vinkurov. Eight webhook providers, eight different ways to sign a request. DEV Community, 2026. https://dev.to/vinkurov_live/eight-webhook-providers-eight-different-ways-to-sign-a-request-3a26
5. GitHub. Validating webhook deliveries. https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
6. WebhookProof. "Timestamp outside the tolerance zone": Stripe webhook fix. https://webhookproof.com/guides/stripe-webhook-timestamp-outside-tolerance
7. Svix. What is timestamp tolerance? https://www.svix.com/resources/glossary/timestamp-tolerance/
8. vinkurov/webhook-kit. https://github.com/vinkurov/webhook-kit
9. JacobStephens2/webhook-verify. https://github.com/JacobStephens2/webhook-verify
10. octokit/webhooks-methods.js commit 19eb9e5. https://github.com/octokit/webhooks-methods.[REDACTED_SECRET]
11. creatorpiyush (verihook author). Why your webhook signature check fails (and the bugs that pass it). https://creatorpiyush.hashnode.dev/why-your-webhook-signature-check-fails-and-the-bugs-that-pass-it
12. W. M. McKeeman. Differential Testing for Software. Digital Technical Journal 10(1), 1998.
13. C. Brubaker, S. Jana, B. Ray, S. Khurshid, V. Shmatikov. Using Frankencerts for Automated Adversarial Testing of Certificate Validation in SSL/TLS Implementations. IEEE S&P 2014. https://doi.org/10.1109/SP.2014.15
14. Pubroot 2026-190. HMAC-SHA256 Stripe Dispute Webhooks on Cloudflare Workers Without stripe-node (self-citation). https://pubroot.com/se/architecture/hmac-sha256-stripe-dispute-webhooks-on-cloudflare-workers-without-stripe-node/