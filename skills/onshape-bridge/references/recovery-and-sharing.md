# Recovering uncertain writes and sharing the local workflow

Observed during Alternate Chute / SC15 in September 2026. All live Onshape
requests still use the session bridge; local packaging and document checks do
not require a cloud request.

## A write timeout does not mean the write failed

One feature POST exceeded the client's 180-second timeout but had committed in
Onshape. Repeating it blindly could insert a duplicate feature or rebuild over
the user's state. The same uncertainty exists after an interrupted agent turn.

1. Save the intended document/workspace/element, feature ID when known, source
   hash/revision, operation and previous state before a non-idempotent write.
2. If the call times out, record its outcome as **unknown**. Check whether the
   local request process is still running before starting another bridge writer.
3. Reconcile with a purposeful read of the affected state: existing feature ID,
   consumed source revision, parameters/status and resulting part geometry.
   Reuse known responses and save enough feature-read budget for this check.
   The continued existence of an old part is not proof of a successful update.
4. If the intended change is present, continue from that state. If it is
   demonstrably absent and no request is still pending, retry the specific
   operation. If still uncertain, inspect the uncertainty rather than delete/
   reinsert the whole studio. Preserve user edits that appeared meanwhile.
5. Audit downstream references and caches after regeneration. Part-ID remapping
   may already have succeeded; see the onshape-cad revision workflow.

Respect response `Retry-After` and endpoint-specific limits while reconciling.
A localhost health check does not prove that the upstream write finished, and
another app login/restart does not replenish an account rate-limit bucket.
Keep long regeneration waits resumable and report progress without duplicate
calls. Do not introduce direct API-key fallback during recovery.

## Build a shareable source package from an allowlist

For a requested workflow ZIP, collect the maintained skill directories, their
referenced files, app/MCP source, manifests/lockfiles, setup instructions and
selected reproducible CAD examples. Preserve relative cross-skill links and
identify the exact source revisions. Copy the **actually used** runtime source,
not an assumed marketplace/cache path. Review redistribution/license files for
included third-party code; include those files with it.

Exclude app `settings.json`, `.env` secrets, API keys, passwords, session cookies,
browser/Electron user-data profiles, personal account databases, raw login DOM,
logs and private printer/device credentials. Do not copy the whole home/workspace,
installed `node_modules`, caches or unrelated inventory by default. A setup
example contains empty placeholders and localhost defaults, never real values.

Audit the staged tree and final ZIP contents. Inspect nested configuration in
3MF/ZIP examples as well as text files: printer host, access-code and API-key
fields can travel with a slicer profile. Filter those without corrupting the
machine's print settings. Add a file manifest/hashes and scan for likely secrets;
record what was checked rather than treating a pattern scan as an absolute
guarantee. Report findings by file/field without printing secret values.

The Electron guide should explain installation from the included manifest and
lockfile, startup, the recipient's **own Onshape login**, keeping the app open,
local health/session checks, port 8317, MCP base URL, current meter comparison,
logout/reconnect and troubleshooting. Use the normal signed-in browser session
and XSRF flow. Optional local auto-login settings stay private and out of Git/ZIP.
Never require the sender's credentials for the recipient's installation.

Label the ZIP as a dated snapshot. Later skill edits belong in the active source;
when another package is requested, build a new dated snapshot and validate its
contents rather than quietly changing an already delivered archive.

The historical September 7 export and its one-off packaging/finalizer scripts
were retired on September 10 at the user's request. They are not prerequisites
for this framework. A future package should be built from its maintained sources
and explicitly selected runtime dependencies.
