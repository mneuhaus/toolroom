---
name: onshape-bridge
description: "Operate the configured Onshape session bridge: reuse the signed-in local app, verify runtime and endpoint budgets, reconcile uncertain writes, and verify binary artifacts. Use only for live work through this adapter; local CAD file review needs no startup."
---

# Onshape session bridge

**Use when** live Onshape work has to run over the configured session bridge: bringing the transport up, checking session health and endpoint budgets, reconciling a write that timed out, or verifying an uploaded artifact. **Do not use when** the work is local — reviewing a cached report, editing files or reading documentation needs no startup and no cloud probe. Geometry methods live in [onshape-cad](../onshape-cad/SKILL.md).

The endpoint, the app location and the start command come from the environment profile, not from this file. The adapter is built on a locally installed signed-in Electron app plus an MCP server; both are separate dependencies and are not duplicated into this framework.

## Procedure

1. Reuse the running, signed-in app. Check local health first; launch it only if it is down, from a persistent terminal that stays open.
2. Verify the session, then read the authoritative metering counters. Note them before and after the session and compare the same reporting window.
3. Check endpoint budgets before a batch. Make one real request to the endpoint the batch needs and inspect its forwarded `x-rate-limit-remaining` header.
4. Issue requests sequentially and keep a single consuming writer for this adapter.
5. If a write times out, reconcile the destination state before retrying — a timeout can follow a successful mutation. Carry the uncertain operation across interrupted work.
6. For uploads, a successful status is not evidence: download the artifact and hash it. Check the running bridge's `binaryRequestBodies` capability; older versions decoded uploads as UTF-8. The transport reference below covers the legacy workaround.

**No call may reach the Onshape servers directly.** If the bridge is down, calls must fail. A connection failure must never silently fall back to API-key authentication or change the user's account configuration. If the key counter moves, something leaked to the metered API — stop and fix it. Use the recipient's own sign-in when setting up a new installation.

## Knowledge

- [What a check actually establishes](../../knowledge/foundations/verification.md) — a status code is not an artifact.
- [Shared project and evidence conventions](../../knowledge/foundations/core.md)

## References

- [Field notes](references/field-notes.md) — the recorded setup, architecture, automatic sign-in, plugin-cache pitfall and measured rate-limit buckets. Historical account windows and measured limits are observations, not current guarantees.
- [Recovery and sharing](references/recovery-and-sharing.md) — write timeouts, interrupted work, and sharing the app without credentials.
- [PDF transport helper](../onshape-build-manuals/references/local-tooling-and-example.md) — for generated PDFs on the UTF-8 request bridge.

## Environment

Base URL, health path, limits path, app location, start command and MCP adapter: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml). See [scope and dependencies](../../docs/scope.md) for what is installed separately.
