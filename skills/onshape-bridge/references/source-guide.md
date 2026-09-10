> Imported field notes. Project-specific numbers, personal preferences and historical runtime assumptions are examples. The current framework entrypoint and explicit project profiles govern reuse.


# Onshape via Session-Bridge (token-free)

This bridge was introduced to avoid consuming the account's metered API-key
quota during CAD iteration. Route Onshape calls through the **logged-in browser
session** instead of an API key. Controlled session-bridge runs observed no
increase in `keyCount`/`clientCount` (including a 60-call comparison). Treat that
as an observed transport result and verify the current counters; do not turn an
old quota, counter total or endpoint limit into a permanent account guarantee.

The Jarvis `onshape` skill covers tool conventions (units, coordinates, REMOVE
auto-flip, deterministic-ID remapping, render-first loop). THIS skill covers the
transport + the gotchas that silently burn tokens or break builds.

## GOLDEN RULE

**No call may hit `cad.onshape.com` directly.** Every Onshape request goes through
`http://127.0.0.1:8317` (the session bridge). If the bridge is down, calls must
*fail* (connection refused) — never silently fall back to the metered API. Watch
`keyCount` (below); if it moves, something leaked to the real API — stop and fix.

## Architecture

```
Claude Code ──stdio──> Jarvis MCP (Python)   base_url = http://127.0.0.1:8317
                          │
                          ▼
                 Electron app  ~/Workspace/onshape-app  (src/main.js)
                   proxy on :8317 → webContents.executeJavaScript(
                     fetch('/api/...', {credentials:'include'}))  IN the
                     logged-in cad.onshape.com tab  → session cookie + XSRF
                          │
                          ▼
                 cad.onshape.com   (unmetered in the recorded tests — session auth)
```

The proxy relays GET/POST/DELETE + binary (base64 roundtrip, byte-exact).
`/_bridge/health` and `/_bridge/screenshot` (capturePage, free renders) are local
extras. `inject.js` auto-clicks session-timeout reconnects.

**Automatic sign-in, recorded from 22 July 2026:** `~/Workspace/onshape-app/settings.json` (mode 600, gitignored) holds `{ "email", "password" }`. After a server logout, an API call returns 401; `main.js` reloads the page with a 60-second debounce. At `dom-ready`, it injects `window.__onshapeCreds` and `inject.js`, which fills and submits the sign-in form using React-compatible native value setters and input events. It also dismisses both session banners: “Your Onshape session has timed out” and “Onshape is not connected”. Logout symptoms are HTTP 204 from `sessioninfo` and 401 “Unauthenticated API request” from other API calls. A call returning 401 triggers the reload; allow approximately 20 seconds for recovery.

**Recorded update on 2 September 2026:** Onshape sign-in uses two stages, email → “Continue” → password → “Sign in”; `inject.js` handles both. `GET /_bridge/reload` triggers recovery without the 60-second debounce. `GET /_bridge/dom` provides the current page's inputs, buttons and text for diagnosing a stuck sign-in. Injection console output goes to the app log. The app has been tracked in git since 2 September 2026. There is no 2FA support; if Onshape requests a code, the user must complete that step manually.

## Startup checklist (every session)

For local-only skill/documentation edits or cached report review, no bridge
startup or cloud probe is needed. For live Onshape work:

1. **Reuse the running, signed-in app.** Check local health first. If it is not
   running, launch it from a persistent terminal and keep it open:
   ```bash
   cd ~/Workspace/onshape-app && npm start
   ```
2. **Verify the bridge + session:**
   ```bash
   curl -s http://127.0.0.1:8317/_bridge/health
   curl -s http://127.0.0.1:8317/api/users/sessioninfo   # isGuest:false, name:Marc → logged in
   ```
3. **Verify metering is untouched** (the safety net — read the authoritative counter):
   ```bash
   curl -s "http://127.0.0.1:8317/api/v14/metrics/api/summary?startDate=2025-11-08T00:00:00.000Z"
   # Historical account window shown: verify the current reporting period.
   # Note both counters; compare the same window at completion.
   ```
4. **Check rate-limit budgets BEFORE working** (required in the source workflow since 4 July 2026):
   ```bash
   curl -s http://127.0.0.1:8317/_bridge/limits    # sessioninfo probe + lastSeen
   ```
   Make one actual request to the endpoint needed by the planned batch and inspect its `x-rate-limit-remaining` header, which the bridge forwards. See “Manage limits proactively” for details and measured window sizes.

## THE cache-vs-marketplace gotcha (this is what burned tokens)

In the investigated installation, Jarvis launched from the **cache** copy, not
the marketplace copy. Identify the actually launched runtime/version first;
these paths are historical examples, not a reason to patch an unused old install:

- runs from: `~/.claude/plugins/cache/jarvis-onshape-mcp/jarvis-onshape-mcp/1.2.0/`
- (also present, but NOT what runs: `~/.claude/plugins/marketplaces/jarvis-onshape-mcp/`)

**Patches must be applied to the cache copy** (at minimum). Two edits make the MCP
token-free:

1. `onshape_mcp/server.py` — default `base_url` to the bridge:
   ```python
   _base = os.getenv("ONSHAPE_BASE_URL", "http://127.0.0.1:8317")
   credentials = OnshapeCredentials(access_key=_ak, secret_key=_sk, base_url=_base)
   ```
   (Default = bridge → fails safe if the app is down; never silently metered.)
2. `.claude-plugin/plugin.json` — add `"ONSHAPE_BASE_URL": "http://127.0.0.1:8317"` to `env`.

A running MCP holds OLD code in RAM — **restart Claude Code** after patching so it
reloads the cache. Plugin updates overwrite the cache → reapply (also keep the
marketplace copy patched as the durable source; the real fix is a PR upstream).

## Building: two modes

### Mode A — MCP tools (preferred; after a Claude Code restart)

Once the patched cache is loaded, use the normal Jarvis tools
(`create_document`, `create_sketch_*`, `create_extrude`, `describe_part_studio`,
`create_assembly`, mates …). They now ride the bridge = free. Follow the Jarvis
`onshape` skill for conventions. Verify `keyCount` stays flat as you go.

### Mode B — bridge scripts (when the MCP is stale / pre-restart)

If Claude Code hasn't been restarted since patching, the in-RAM MCP still hits the
real API — **do NOT call MCP tools**. Build via a script that imports the (patched,
on-disk) Jarvis builders and drives `OnshapeClient` at the bridge:

```python
import sys; sys.path.insert(0, CACHE_DIR)   # the 1.2.0 dir above
from onshape_mcp.api.client import OnshapeClient, OnshapeCredentials
from onshape_mcp.api.partstudio import PartStudioManager
from onshape_mcp.builders.sketch import SketchBuilder, SketchPlane
from onshape_mcp.builders.extrude import ExtrudeBuilder, ExtrudeType

creds = OnshapeCredentials(access_key="x", secret_key="x", base_url="http://127.0.0.1:8317")
async with OnshapeClient(creds) as c:
    doc = await c.post("/api/documents", data={"name":"...","isPublic":True})  # DocumentInfo attrs differ; raw post returns a dict
    did = doc["id"]; wid = doc["defaultWorkspace"]["id"]
    eid = [e for e in await c.get(f"/api/documents/d/{did}/w/{wid}/elements") if e["elementType"]=="PARTSTUDIO"][0]["id"]
    ps = PartStudioManager(c)
    top = await ps.get_plane_id(did, wid, eid, "Top")
    features = f"/api/v9/partstudios/d/{did}/w/{wid}/e/{eid}/features"
    s = SketchBuilder(plane=SketchPlane.TOP); s.add_circle((0,0), 30)
    sk = (await c.post(features, data=s.build(top)))["feature"]["featureId"]
    ex = (await c.post(features, data=ExtrudeBuilder(name="Disc", sketch_feature_id=sk, depth=10,
              operation_type=ExtrudeType.NEW).build()))["feature"]["featureId"]
```

Run with `uv run python` from the cache `1.2.0` dir (`uv --directory` there).
NOTE: a shell hook blocks bare `python`/`python3` — use `uv run python`, and edit
scratch scripts with the Edit tool (not `python3 -c` / heredocs).
Render for feedback: fetch `/api/partstudios/.../shadedviews` (returns JSON with
base64 `images[]`) or `/_bridge/screenshot` (PNG), save, and Read the PNG.

## Onshape v9 /features payload quirks (found the hard way)

Onshape's current `/api/v9/.../features` endpoint is stricter than Jarvis's stock
builders. Error signature: `BTWeirdStringValueException (… ArrayList[i])` — it
names the first offending parameter; fix it and the error walks to the next.

Fixed in `builders/extrude.py` and, from 19 July 2026, in `offset_plane.py`, `fillet.py` and `chamfer.py`, in both cache and marketplace copies. The remaining builders (boolean, pattern, revolve, shell, thicken and mate) were suspected to need the same changes:
- Sketch-region query must be **minimal** `{btType, featureId}` — sending
  `queryString` / `filterInnerLoops` / `queryStatement` / `deterministicIds` → 400.
- **`libraryRelationType: "NONE"` must NOT be sent on extrude parameters** — the
  string "NONE" is rejected on every param type here (tolerated elsewhere).

If a fillet/chamfer/boolean/pattern builder throws the same exception, suspect the
same two culprits and strip them; isolate over the bridge (free) with a param matrix.

## Constraints & facts

- **Free plan → public documents only.** Private create/write → HTTP 409 (business
  rule, not a bridge fault). Build with `isPublic: True`.
- **ToS grey zone:** automated session use sidesteps the metering intent. Hobby
  volume, human-ish pace; a bridge until the official PTC Onshape MCP ships.
- Marc wants Onshape specifically for the **Parasolid kernel** (robust fillets /
  booleans where build123d/OCCT stalls). See [[cad-backend-strategie]].
- Units/coordinates/render-loop/REMOVE-auto-flip: defer to the Jarvis `onshape` skill.

## If keyCount rises

Something bypassed the bridge. Likely causes: MCP not restarted after patching
(stale RAM hitting real API), a plugin update reverted the cache patch, or a call
made with real keys. Stop, re-check the two cache patches, restart Claude Code,
re-verify `keyCount` is flat.

## Manage limits proactively

Recorded on 4 July 2026 as required reading before each batch. Onshape rate limits are account-bound, with separate windows per endpoint. A VPN, fresh document or new sign-in does not change them. Each response carries `x-rate-limit-remaining`; HTTP 429 includes `retry-after` in seconds. The bridge forwards both headers. `GET /_bridge/limits` provides `{probe:{status,remaining,retryAfter}, lastSeen}`; the MCP tool is `get_api_limits`.

Treat annual metering and endpoint rate limits separately. An HTTP error does not establish that a probe was free: inspect response headers. HTTP 200 with failed FS evaluation still consumes an evaluation call; also inspect `result`, `notices` and feature status.

Measured buckets on 2 September 2026 used one call per endpoint on a fresh document, taking the initial value as the cap. The source script was `bucket_probe.py`; see the historical `[[onshape-features-budget-plan]]` reference.

- **`GET partstudios/.../features`: observed cap 100.** All API versions (v6, v9 and unversioned) shared this bucket. This was the scarce endpoint, rather than writes. Consumers include `get_features`, `inspect_sketch`, `list_sketches`, `render_sketch`, `delete_feature_by_name`, `edit_sketch` (GET + POST), `describe_part_studio` and fallback GET in `apply_feature_and_check`.
- **`POST partstudios/.../featurescript` (FS evaluation): observed cap 100 in a separate bucket.** It did not share the features bucket; the earlier handoff note was incorrect. Consumers include `list_entities`, `measure`, `get_face_coordinate_system`, `eval_featurescript`, Jarvis `get_bounding_box` and `face_areas`. One `describe_part_studio` therefore used 1% of the GET bucket and 3% of the FS bucket.
- **Writes: observed shared cap 3000** across features POST (add), feature-ID POST (update), feature-ID DELETE, Feature Studio creation and contents POST. In this observation, building had more budget than reading.
- **Shared read bucket 3000:** Feature Studio GET, feature specs, mass properties and the REST bounding-box endpoint, not the FS evaluation wrapper. `sessioninfo` had its own 3000 bucket.
- Separate observed caps of 500 for `parts`, `bodydetails` and `shadedviews`; 1500 for `elements`; 200 for document creation/deletion; 1000 for assemblies, as recorded on 4 July. `features/updates` returned 404; the tested batch-update endpoint was unavailable.
- Refill observations: `sessioninfo` rolled over, recovering approximately 50 calls in 10 minutes. **GET features showed no refill over 40 minutes**, falling 89 → 88 → 87 with one call each. The source inferred a daily-scale budget of approximately 100 feature-tree reads per 11–24 hours. At zero remaining on 4 July 2026, `Retry-After` was approximately 39,000 seconds, or 11 hours. Verify current headers instead of treating these measurements as permanent limits.

**Working rules:**

1. **Before each batch:** check `/_bridge/limits` and the header on the first target request already needed. Do not spend an extra feature-tree read merely to probe. Below 20% remaining, reduce the batch and reserve budget for the remaining verification.
2. **Plan the batch:** estimate calls in advance. Each feature operation may use 1–2 features calls; `apply_feature_and_check` uses GET + POST. With a daily-scale features budget, spread large rebuilds over the available windows.
3. **Recorded client automation** in cache and marketplace `client.py`: `_MIN_GAP` defaults to 0.4 seconds and can be increased through `ONSHAPE_MIN_GAP`; the source used 2–3 seconds near limits. HTTP 429 backoff runs from 15 to 300 seconds, with `Retry-After` taking precedence. The budget guard warns below 100 remaining and adds 10 seconds per call below 30. These thresholds do not fit 100-call buckets well; 30 remaining is already scarce. Threshold adjustment remained open.
4. Do not run parallel processes against the bridge. Group bulk operations and follow actual budget/backoff signals between large batches. Use renders sparingly, given the observed 500-call window. Keep long waits interruptible and communicate progress instead of blocking the conversation.
5. On a hard 429, respect `retry-after`. For delays of thousands of seconds, schedule work later rather than polling.

## Project files and evidence

- After an interrupted or slow write, inspect the actual state before retrying: a timeout can occur after a successful mutation. See [Recovery and workflow packages](recovery-and-sharing.md) for this workflow and for sharing the Electron app without credentials.
- Compare the initial `keyCount` / `clientCount` with the final values. Do not promote a previous project's counter into a universal target.
- Persist document, workspace, element and published draft IDs, for example in `var/state/`. Store API responses in `var/cache/`, and HTTP status and budget headers in `var/logs/`. See [CAD project layout](../../../knowledge/project-layout.md).
- Local reorganisation, offline report review and gallery generation do not require cloud republication. Bind part exports to their source microversion: an unchanged `partId` does not establish unchanged geometry.
- Follow STEP translation through to `DONE`, download external result data as binary through the bridge, and check format and file size. A job ID alone is not an export.
