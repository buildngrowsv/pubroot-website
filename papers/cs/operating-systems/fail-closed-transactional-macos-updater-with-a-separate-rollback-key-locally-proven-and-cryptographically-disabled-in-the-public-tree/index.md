---
title: "Fail-closed transactional macOS updater with a separate rollback key, locally proven and cryptographically disabled in the public tree"
paper_id: "2026-194"
author: "buildngrowsv"
category: "cs/operating-systems"
date: "2026-08-25T06:46:04Z"
abstract: "RenderMac Host treats the updater as a remote-code-execution boundary. HTTPS is transport, not release authority, so a compromised feed, DNS path, CDN account, or storage token must not make a host trust an artifact. Schema-v1 Ed25519 signs one canonical UTF-8 sequence covering schema, channel, strict SemVer, HTTPS artifact URL, lowercase SHA-256, exact byte count, and minimum macOS version. The pin is compiled into RenderMacUpdateTrust and is not editable in UserDefaults. Production pins, Developer ID team, designated requirement, and emergency-rollback pin are nil in the public tree, so an ad-hoc development build cannot install. Installation is a two-process journal. The running app stages, the embedded helper swaps, and the newly installed app commits a Keychain version floor the helper cannot write. Durable phases are prepared, backup_created, candidate_installed, health_check_passed, ledger_committed, and committed, each published with fsync and rename. ZIP is preflighted before ditto. Ordinary updates cannot lower the highest-ever version. A downgrade needs a distinct offline Ed25519 statement, at most 24 hours, with a one-time nonce. Local tests inject interruptions at post-swap phases. Production signing and live auto-update remain disabled."
score: 7.5
verdict: "ACCEPTED"
badge: "verified_private"
ai_tooling_attribution: "Drafted with Grok (xAI) from repository inspection; human operator will submit via pubroot CLI."
---

A Mac host that pulls work from a control plane still has to take security fixes. The update path is itself remote code execution. RenderMac Host therefore refuses to treat TLS, a CDN account, or a JSON feed as release authority. ADR 0009 (`docs/adr/0009-native-update-trust-and-install-boundary.md`) records the contract that ships in Swift. Production pins are nil. The implementation is locally proven and cryptographically disabled in the public tree.

The supporting repository is private. The excerpts below are the evidence. This is not a distributable auto-update channel.

## HTTPS is transport, not authority

`SignedUpdateChecker` verifies a schema-v1 manifest before it reports any outcome and before it streams an artifact. The signed bytes are one canonical UTF-8 sequence. Newlines and control characters are forbidden in values so two parsers cannot disagree. The final newline is part of the signature. A semantic change requires a new schema; parsers must not reinterpret v1.

```text
rendermac-update-manifest-v1
schema_version=1
channel=stable
version=0.2.0
download_url=https://…
sha256=<64 lowercase hex>
artifact_size_bytes=<exact count>
minimum_system_version=
```

`scripts/sign_native_update_manifest.mjs` emits that same payload. A Swift test asserts the host verifier and the Node signer agree byte for byte. The download URL must be HTTPS with no embedded credentials. Streaming to an owner-only directory is capped at the signed byte count. The file is retained only after exact size and streaming SHA-256 match again.

None of that makes TLS the authority. A compromised feed, DNS path, CDN token, or object-store account can still serve bytes. Those bytes do not become an installable app unless they carry a 64-byte Ed25519 signature over the canonical payload, match the compiled pin, and later survive Developer ID, hardened runtime, notarization staple, and Gatekeeper assessment of the contained bundle.

## Compiled-in pins, all nil in this tree

The public pin is not a setting. It is compiled into the signed app through `RenderMacUpdateTrust`. Keeping it out of `UserDefaults` prevents a feed or a local preference edit from silently selecting a different release authority.

```swift
public enum RenderMacUpdateTrust {
    public static let releaseEd25519PublicKeyBase64: String? = nil
    public static let releaseTeamIdentifier: String? = nil
    public static let releaseDesignatedRequirement: String? = nil
    public static let emergencyRollbackEd25519PublicKeyBase64: String? = nil
}
```

Those four values are nil in the public tree at `56a728eb1837a5760b2a6f81d8e14714726deb32`. `nativeAppReleaseIdentity` therefore returns nil. `NativeUpdateInstaller.hasConfiguredInstallationTrust` is false. `SignedUpdateChecker.trustedPublicKey()` throws `missingOrInvalidTrustedPublicKey` unless a test injects a 32-byte key. The development UI reports that production trust is not provisioned and cannot stage an installation.

Artifact authentication is necessary but not sufficient. `SystemNativeAppReleaseVerifier` in `NativeUpdateSecurity.swift` requires bundle ID `com.rendermac.host`, one regular main executable plus embedded `RenderMacUpdateHelper`, no links or special files in the app tree, deep/strict `codesign` against the compiled designated requirement, Developer ID Application authority and team, the hardened-runtime flag, helper identifier `com.rendermac.host.update-helper`, a notarization staple, and Gatekeeper execute assessment. The candidate is verified after extraction, after copy onto the destination volume, and after replacement. An ad-hoc development app cannot pass these gates. Tests inject command results because no production identity exists locally.

## ZIP is a preflighted envelope

The release artifact is ZIP only. ZIP is a transport envelope. It cannot carry an Apple staple. Developer ID, notarization, and the staple apply to the contained app. The ZIP itself is authenticated by the signed exact byte count and SHA-256.

`DittoNativeUpdateArchiveExtractor` runs a bounded central-directory reader before `ditto` is allowed to write a member. Rejected classes include ZIP64, encryption, unsupported compression, multi-disk archives, oversized expansion, invalid UTF-8, path traversal, absolute or Windows paths, control characters, duplicate or case-colliding names, ambiguous local headers, links, and special files. The archive must describe exactly one top-level `RenderMacHost.app`. `__MACOSX` metadata is the only optional peer. After extraction the tree is inspected again before signature validation. That list is the implemented contract, not a construction recipe.

If the destination parent is not writable, staging fails without replacement. The updater does not improvise authorization or prompt through shell tools. A privileged XPC helper would need its own ADR.

## Two-process journal

Installation is not “replace the bundle and hope.” `NativeUpdateInstaller` is a two-process transaction. The running app stages and re-verifies a candidate on the destination volume, writes an owner-only recovery journal, starts its already-signed embedded helper, and quits. The helper waits for the parent to exit. Durable phases are:

```swift
public enum NativeUpdateInstallPhase: String, Codable {
    case prepared
    case backupCreated = "backup_created"
    case candidateInstalled = "candidate_installed"
    case healthCheckPassed = "health_check_passed"
    case ledgerCommitted = "ledger_committed"
    case committed
    case rolledBack = "rolled_back"
}
```

Journal publication writes a mode-0600 temporary file, `fsync`s it, `rename`s it over `install-journal.json`, and `fsync`s the directory. App, candidate, and backup names live in a different directory than the journal, so that parent is `fsync`ed after candidate publication, replacement, restoration, and cleanup before the corresponding phase is advanced. Each filesystem shape is validated against the recorded phase. Symlinks and wrong-owner objects at the state, journal, ledger, and lock boundaries fail closed.

The previous app remains as a sibling backup until the new executable completes a bounded one-time command-line self-check. A pre-health failure restores and re-verifies the backup. After health succeeds, the helper does not write the version floor. Keychain access groups are restricted entitlements on macOS; a plain embedded command-line helper is the wrong place to hold that authority. The helper starts a bounded command mode in the new app. That stable bundle identity commits the private Keychain floor and writes `ledger_committed`. The helper removes the backup only after that phase.

A post-health Keychain outage leaves the verified new app, backup, and journal pending rather than rolling back against an already-fsynced ledger entry. A crash can resume from every post-swap phase. Once the ledger commits, recovery moves forward.

The 2026-07-22 qualification card (`docs/evidence/2026-07-22-native-update-transaction-qualification.md`) ran the `RenderMacHost` scheme on a local MacBook Pro (macOS 26.5.1) with 46/46 tests passing. Injected interruptions covered `backup_created`, `candidate_installed`, `health_check_passed`, and `ledger_committed`. The Node signers passed 7/7. The current worktree’s native Swift suite is 53/53; that count is the whole host core, not an updater-only subset.

## Highest-ever floor and a separate rollback key

`NativeUpdateVersionLedger` is an append-only JSON-lines HMAC chain. Its random authentication key, sequence, and head MAC live in a ThisDeviceOnly Keychain item (`com.rendermac.host.update-ledger` / `version-floor-anchor-v1`) owned by the app’s stable designated identity. The helper never reads or writes it. Entry edits, truncation, missing anchors, duplicate normal artifacts, and non-increasing normal versions fail closed. One authenticated trailing entry is repairable after a crash between ledger `fsync` and Keychain-head advancement. An incomplete unanchored tail is truncated without lowering the floor.

The policy remembers the highest version ever installed, not merely the current version. `authorize` in `NativeUpdateLedger.swift` accepts an ordinary upgrade only when the candidate is newer than that floor and the SHA-256 has never been recorded. A caller cannot turn the ordinary path into a downgrade with a Boolean flag. `prepareEmergencyRollback` is a distinct API.

A downgrade needs both the ordinary signed manifest and `EmergencyRollbackAuthorization`, an exact version and SHA-256 statement signed by a separately pinned, normally offline Ed25519 authority. The window is at most 24 hours. The statement contains a one-time nonce and a reason code. The full signed authorization is retained in the recovery journal and reverified against the transaction’s creation time before a resumed commit, so an unsigned journal edit cannot manufacture downgrade power. Consumed nonces are recorded in the ledger. Key rotation is outside schema v1. A feed-delivered replacement key is never acceptable.

Trust boundaries, in one line of sight:

```text
HTTPS feed
  -> compiled ordinary Ed25519 pin (nil in this tree)
  -> ZIP size + SHA-256, then ZIP class preflight, then ditto
  -> Developer ID + staple + Gatekeeper on app and helper
  -> helper filesystem swap (no Keychain)
  -> new app commits Keychain version floor
  -> distinct offline Ed25519 pin (downgrade only; also nil)
```

## Limits

Production pins are nil. The updater is locally proven and cryptographically disabled in the public tree. Passing local tests does not make `RenderMacHost.app` distributable.

We do not claim Developer ID signing, notarization, staple, or Gatekeeper success against a production artifact. Those tools are invoked by `SystemNativeAppReleaseVerifier`, but the positive real-credential path has not run. Cross-version continuity of the app-owned Keychain anchor still needs two real signed releases.

The Keychain floor detects offline or file-only ledger tampering. It does not claim resistance to arbitrary code already running as the current app identity. Broader-host release, per ADR 0009, still needs a separately authorized updater or an externally signed floor witness.

Simulated interruption and `fsync` tests are not physical APFS power-cut evidence. User-writable locations are supported; non-writable locations fail closed. Canary, revoked-release, real-network, and overnight device-matrix qualification remain release gates. Adopting Sparkle later would need a new ADR and equivalent proof for pins, rollback authority, the authenticated floor, and recovery.

This article describes rejected ZIP classes. It does not publish malformation recipes, private-key handling, or a live update-feed URL as an installable channel.