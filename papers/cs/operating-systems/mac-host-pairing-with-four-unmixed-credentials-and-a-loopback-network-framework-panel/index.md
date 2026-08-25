---
title: "Mac host pairing with four unmixed credentials and a loopback Network.framework panel"
paper_id: "2026-184"
author: "buildngrowsv"
category: "cs/operating-systems"
date: "2026-08-25T06:37:25Z"
abstract: "A menu-bar macOS host must enroll a machine into a remote control plane without putting a long-lived device credential in the browser, in UserDefaults, or in a LAN-reachable daemon. RenderMac Host keeps four credentials unmixed: an HttpOnly website session cookie, an organization API key, a one-use rm_pair_ enrollment code, and a Keychain rm_device_ token. A first-party provider session mints the pairing code; the Mac claims it at POST /v1/provider/enrollment-claims and receives the device token once. PostgreSQL stores only SHA-256 hashes. The optional browser panel is not a remote admin surface: Network.framework binds to 127.0.0.1, a non-loopback Host is rejected with HTTP 421, mutating Origin must be loopback, and a per-launch 32-byte token travels in the URL fragment then in X-RenderMac-Local-Token. Tests show unauthenticated /api/status is 401, configuration round-trips without writing rm_device_ into UserDefaults, and machine API keys cannot enroll the shared_beta pool."
score: 7.8
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

## Why pairing is an operating-system problem

A Mac that runs named media services for a control plane needs a durable device identity. Storing that identity in a website cookie, a pasted API key, a plist, or a LAN HTTP server mixes lifetimes and attackers. RenderMac Host is a SwiftUI menu-bar app that supervises a bundled agent. Pairing is implemented so the browser never holds the device token and the Mac never holds the website session. The four credentials, documented in `docs/WEB-IDENTITY-HOST-AUTH-AND-DISTRIBUTION.md`, are:

- website session: HttpOnly, Secure, SameSite=Lax, host-only cookie on `provider.rendermac.com`; D1 stores a hash, not the raw cookie.
- organization API key: a machine credential for buyer/provider HTTP APIs, never written into browser storage by the sites Worker.
- enrollment code: one-use, time-limited `rm_pair_…`, hash-only in PostgreSQL.
- device token: `rm_device_…`, plaintext only in that Mac's Keychain; hash-only in PostgreSQL.

Substitution is treated as a bug. A cookie cannot claim a device. An API key cannot pretend to be a paired Mac. A pairing code cannot be reused as a Bearer token on the agent WebSocket.

## Minting a code, claiming it once

A signed-in provider owner with `devices:write` posts `POST /v1/provider/enrollment-codes`. The schema in `packages/shared/src/protocol.ts` caps lifetime at 60–3600 seconds (default 900). `createProviderEnrollmentCode` in `packages/control-plane/src/services/providerEnrollment.ts` inserts `code_prefix` plus `code_hash` and returns plaintext once. The enrollment row stored in the JSON response does not contain that plaintext; an integration test asserts the code is absent from the `enrollment` object.

The Mac, not the browser, spends the code. `ProviderEnrollmentClient` in `native/RenderMacHost/Sources/RenderMacHostCore/ProviderEnrollmentClient.swift` requires prefix `rm_pair_` and length at least 24, then posts hardware facts to `POST /v1/provider/enrollment-claims` with a 30-second timeout. That route is unauthenticated: the pairing code is the proof, rate-limited to 30 claims per minute. Claim lookup is hash equality under a row lock:

```text
SELECT * FROM provider_enrollment_codes
 WHERE code_hash = $1 AND claimed_at IS NULL AND expires_at > now()
 FOR UPDATE
```

A miss is `invalid_enrollment_code` (HTTP 400). A hit mints `rm_device_` plus 32 random bytes (base64url) via `newDeviceToken()`, writes `device_token_hash`, marks `claimed_at`, and returns plaintext once. Replay of the same body is 400. Recovery mints a new code bound to an existing `device_id`; the claim rotates the hash, sets `recovered: true`, and disconnects the previous agent session. The integration test in `packages/control-plane/src/integration/controlPlane.integration.test.ts` checks `device_token_hash !== device_token` and that the old Bearer is `unauthorized`.

Pool membership is not a property of “having any provider credential.” Machine API keys may mint only `org_private` codes. First-party D1 host-beta sessions may choose `org_private` or `shared_beta`. The public provider route encodes that split:

```text
return auth.identitySource === "cloudflare_d1" && auth.betaParticipation === "host"
  ? ["org_private", "shared_beta"] as const
  : ["org_private"] as const;
```

The same integration file posts `pool: "shared_beta"` with a Bearer API key and expects HTTP 409 `pool_forbidden`. Legacy `public` enrollment is rejected for every caller.

## Keychain is the only plaintext store

`KeychainDeviceTokenStore` in `native/RenderMacHost/Sources/RenderMacHostCore/DeviceTokenStore.swift` uses service `com.rendermac.host` and account `provider-device-token`. `save` refuses anything that does not start with `rm_device_`, then writes a generic password with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`:

```swift
guard let data = token.data(using: .utf8), token.hasPrefix("rm_device_") else {
    throw KeychainError.invalidToken
}
let attributes: [String: Any] = [
    kSecValueData as String: data,
    kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
]
```

This-device-only means a Keychain item restored onto another Mac is not a working host credential. After-first-unlock is the availability the agent needs at login without prompting at every heartbeat. Prefix checks are duplicated at claim parse, client decode, Keychain save, and `AgentSupervisor.start`.

Agent configuration still round-trips through UserDefaults (control-plane URL, slot counts, disk reserve). `configurationRoundTripsWithoutADeviceSecret` saves a configuration into a private suite and asserts no value contains `rm_device_`. Host logs run a second pass: `AgentSupervisor` redacts `rm_device_[A-Za-z0-9_-]+` before appending lines the loopback panel can display.

The native app and the loopback panel share the same claim path. `RenderMacHostApp` handles `.pair` by calling `ProviderEnrollmentClient.claim` and then `KeychainDeviceTokenStore.save`. Starting the host refuses if Keychain has no token. After pairing, the agent authenticates to `wss://api.rendermac.com/v1/provider/ws` with `Authorization: Bearer rm_device_…`. `requireDeviceAuth` accepts only that prefix, looks up `device_token_hash`, and rejects disabled devices. Device auth identifies the paired Mac. It does not mint enrollment codes.

A 2026-07-26 public-path canary paired a real Mac through a one-use code from `provider.rendermac.com`, connected the bundled agent to production WSS, and completed `ffmpeg.stitch_export.v1`. The operator how-to is `https://rendermac.com/how-to/pair-host-mac`.

## Loopback panel, not a LAN daemon

Operators sometimes want a browser page instead of the menu extra. `LocalHostControlServer` in `native/RenderMacHost/Sources/RenderMacHostCore/LocalHostControlServer.swift` is an in-process Network.framework listener, created per app launch, not a launchd job and not a second daemon.

The TCP parameters require a local endpoint on `127.0.0.1` with an ephemeral port. When the listener is ready, the app records `http://127.0.0.1:<port>/#token=<accessToken>`. The token is 32 bytes from `SecRandomCopyBytes`, encoded as unpadded base64url. The secret lives in the URL *fragment* so browsers do not send it on HTTP requests. Page JavaScript reads it and then strips the hash:

```text
const token=new URLSearchParams(location.hash.slice(1)).get("token")||"";
history.replaceState({}, "", location.pathname);
```

Every `/api/*` call then sends `X-RenderMac-Local-Token`. The server compares with `constantTimeEqual`. GET `/` is the HTML panel; it does not require the header. GET `/api/status` and all POSTs do. A Swift test, `localBrowserControlIsLoopbackAndTokenAuthenticated`, starts the server, asserts `components.host == "127.0.0.1"`, fetches `/api/status` with no header (401), then fetches with the fragment token in the header (200).

Host and Origin checks are a mitigation for a loopback listener that a browser might still be induced to contact. If `Host` is not `localhost`, `127.0.0.1`, or those names with a port, the server returns HTTP 421 “Loopback Host header required” before looking at the path. Non-GET requests additionally require `Origin` to parse as `http` with host `127.0.0.1` or `localhost`; otherwise the response is 403 `invalid_origin`. Together with the bind address, the panel is a same-machine control surface, not a way to administer the host from another device on the network.

The HTML response sets `Content-Security-Policy` (`default-src 'none'; connect-src 'self'; frame-ancestors 'none'`), `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and `Cache-Control: no-store`. Request bodies are capped at 8192 bytes; reads above 64 KiB return 413. Pairing POSTs decode `{ "code": "…" }` and hand the string to the same Keychain-backed handler the menu bar uses.

## One in-flight status poll

The panel needs a live state label without becoming a hidden-tab timer leak. Inline JavaScript keeps a single `inFlight` flag, a `stopped` flag, and a delay that starts at 3 s, settles at 5 s on success, and doubles on failure to a 60 s cap with ±15% jitter (`0.85 + random * 0.3`). `fetch` uses `AbortController` with a 5 s timeout. `document.hidden` skips both `refresh` and `schedule`. `visibilitychange` restarts at 1 s when the tab is shown; `pagehide` sets `stopped` and clears the timer. The next `setTimeout` is armed only from `finally` after the current attempt settles, matching the repository rule against overlapping `setInterval` work.

That loop talks only to the local listener. Pairing still goes Mac → `https://api.rendermac.com/v1/provider/enrollment-claims`. The browser at `provider.rendermac.com` never receives `rm_device_…`.

## Limits

This is a pairing and local-control design, not a general zero-trust manifesto and not a remote Mac management product.

We do not claim the loopback panel is TLS-authenticated, remotely administrable, or safe against a process already running as the logged-in user who owns the Keychain item. `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` is not Secure Enclave attestation and is not a TPM quote.

Host and Origin checks are implemented mitigations for a `127.0.0.1` Network.framework listener. We do not present them as a complete browser-security proof, and we do not claim they bind every other socket the OS might open.

Device auth identifies the paired host. It does not mint enrollment codes, create buyer jobs, or replace the website session. Machine API keys cannot select `shared_beta` on the public enrollment route; operator/admin routes that exist for other reasons are out of scope here.

The 2026-07-26 canary proved public-path pairing and one production job on `org_private`. It did not measure concurrent recovery races beyond the `FOR UPDATE` claim transaction. No device-token or pairing-code plaintext appears in this article; prefixes are the public contract.