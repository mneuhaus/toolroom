---
name: onshape-bridge
description: "Operate the configured Onshape session bridge: reuse the signed-in local app, verify runtime and endpoint budgets, reconcile uncertain writes, and verify binary artifacts. Use only for live work through this adapter; local CAD file review needs no startup."
---

# Onshape session bridge

This is an adapter for the existing Electron/Jarvis setup. It is not a universal Onshape connection requirement. Endpoint and runtime locations come from the active project or environment.

Read [transport field notes](references/source-guide.md) for the known setup and [recovery](references/recovery-and-sharing.md) for timeouts and sharing. Historical account windows and measured rate limits are observations, not current guarantees.

For live work, reuse the running signed-in app, inspect health and current budgets, then issue requests sequentially. Keep one consuming writer for this session adapter. If a write times out, reconcile the destination state before retrying; retain the uncertain operation across interrupted work.

Respect an explicitly selected session transport. A connection failure must not silently select API-key authentication or change the user's account configuration. Use the recipient's own sign-in when setting up a new installation.

Responses and request bodies have different binary behavior in the inspected implementation. A successful upload status is insufficient: download and hash the artifact. For generated PDFs on the UTF-8 request bridge, see the [manual transport helper](../onshape-build-manuals/references/local-tooling-and-example.md).

The Electron app and Jarvis runtime are separately installed dependencies, not duplicated into this framework. The framework can be read and its local helpers tested without either application. See [scope and dependencies](../../docs/scope.md).
