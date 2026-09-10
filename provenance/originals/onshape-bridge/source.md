---
name: onshape-bridge
description: "Marc's Onshape session-bridge workflow using the signed-in Electron app and localhost proxy on port 8317. Load before live Onshape work: session reuse, verified metering, endpoint budgets, runtime/cache configuration, write-timeout reconciliation and binary exports. Also covers sharing the app/workflow without credentials. Geometry methods are in onshape-cad."
---

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
                 cad.onshape.com   (ungemetert — session auth)
```

The proxy relays GET/POST/DELETE + binary (base64 roundtrip, byte-exact).
`/_bridge/health` and `/_bridge/screenshot` (capturePage, free renders) are local
extras. `inject.js` auto-clicks session-timeout reconnects.

**Auto-Relogin (seit 2026-07-22):** `~/Workspace/onshape-app/settings.json`
(chmod 600, gitignored) hält `{ "email", "password" }`. Kette bei Server-Logout:
API-Call liefert 401 → main.js lädt die Seite neu (debounced 60 s) → dom-ready
injiziert `window.__onshapeCreds` + inject.js → Signin-Formular wird React-konform
(native value setter + input-Event) befüllt und abgeschickt. inject.js klickt
außerdem BEIDE Banner-Varianten weg („Your Onshape session has timed out" UND
„Onshape is not connected"). Symptome eines Logouts: `sessioninfo` → HTTP 204,
beliebige API → 401 „Unauthenticated API request". Manuell anstoßen: einen
API-Call machen (401 triggert den Reload), dann ~20 s warten. **Seit 2026-09-02:** Onshape-Signin ist
zweistufig (E-Mail → „Continue" → Passwort → „Sign in"), inject.js kennt beide
Schritte. Relogin ohne 60-s-Debounce: `GET /_bridge/reload`; Formular-Inventar
der aktuellen Seite (Inputs/Buttons/Text, wenn der Login wieder hängt):
`GET /_bridge/dom`. Inject-Konsolenzeilen landen im App-Log. Die App liegt
seit 2026-09-02 unter Git. Kein 2FA-Support —
wenn Onshape einen Code verlangt, muss Marc einmal manuell ran.

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
4. **Check rate-limit budgets BEFORE working** (Pflicht seit 2026-07-04):
   ```bash
   curl -s http://127.0.0.1:8317/_bridge/limits    # sessioninfo-Probe + lastSeen
   ```
   und für den Endpoint, den der geplante Batch nutzt, EINEN echten Call machen
   und den `x-rate-limit-remaining`-Header lesen (Bridge reicht ihn durch).
   Details + gemessene Fenstergrößen: Abschnitt „Limits proaktiv managen".

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

Fixed in `builders/extrude.py`, seit 2026-07-19 auch `offset_plane.py`,
`fillet.py`, `chamfer.py` (jeweils Cache + Marketplace); Rest der Builder
(boolean, pattern, revolve, shell, thicken, mate) vermutlich noch betroffen:
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

## Limits proaktiv managen (2026-07-04 — PFLICHTLEKTÜRE vor jedem Batch)

Onshape rate-limitet **pro Endpoint mit eigenen Fenstern**, account-gebunden
(VPN/frisches Dokument/Relogin ändern NICHTS). Jede Antwort trägt
`x-rate-limit-remaining`; bei 429 kommt `retry-after` (Sekunden). Die Bridge
reicht beide Header durch, und `GET /_bridge/limits` liefert einen Gratis-Check
(`{probe:{status,remaining,retryAfter}, lastSeen}`). Im MCP: Tool `get_api_limits`.
Jahres-Metering und Endpoint-Rate-Limits getrennt behandeln. Aus einer
HTTP-Fehlerantwort nicht auf einen kostenlosen Rate-Limit-Probe schließen:
Antwortheader auswerten. Auch HTTP 200 mit fehlgeschlagenem FS-Eval verbraucht
den Eval-Aufruf; `result`, `notices` und Feature-Status mitprüfen.

Gemessene Buckets (2026-09-02; ein Call pro Endpoint auf einem frischen
Dokument, Startwert = Kappe; Skript `bucket_probe.py`, siehe
[[onshape-features-budget-plan]]):
- **`GET partstudios/.../features`: Kappe 100.** Alle API-Versionen (v6, v9,
  unversioniert) teilen den Topf. DAS ist der knappe Endpoint, nicht die
  Writes. Verbraucher: get_features, inspect_sketch, list_sketches,
  render_sketch, delete_feature_by_name, edit_sketch (GET+POST),
  describe_part_studio, Fallback-GET in apply_feature_and_check.
- **`POST partstudios/.../featurescript` (FS-Eval): Kappe 100, EIGENER Topf**
  (nicht mit features geteilt; die frühere Handoff-Notiz war falsch).
  Verbraucher: list_entities, measure, get_face_coordinate_system,
  eval_featurescript, Jarvis get_bounding_box, face_areas. Ein
  describe_part_studio kostet damit 1 % des GET-Topfs plus 3 % des FS-Topfs.
- **Writes: Kappe 3000, ein geteilter Topf** für features POST (add),
  featureid POST (update), featureid DELETE, featurestudios create und
  contents-POST. Bauen ist billig, Lesen ist teuer.
- **Reads-Topf 3000, geteilt**: featurestudio GET, featurespecs,
  massproperties, boundingboxes (REST-Endpoint, nicht der FS-Eval-Wrapper).
  `sessioninfo`: eigener 3000er.
- Je ein eigener 500er: `parts`, `bodydetails`, `shadedviews`.
  `elements`: 1500. `documents` create/delete: 200. `assemblies`: 1000
  (Stand 07-04). `features/updates` (Batch-Update) → 404, existiert nicht.
- Refill: sessioninfo gleitend (~50 Calls in 10 min zurück). **GET features:
  in 40 min KEIN Refill** (89 → 88 → 87 bei je einem Call), also ein
  Tages-Topf: ~100 Feature-Tree-Reads pro ~11–24 h. Bei 0 kam am 2026-07-04
  Retry-After ~39000 s (~11 h).

**Arbeitsregeln (verbindlich):**
1. **Vor jedem Batch:** `/_bridge/limits` prüfen und den Header des ersten
   ohnehin nötigen Ziel-Requests auswerten; keinen zusätzlichen Feature-Tree-
   Read allein als Probe verschwenden. Unter 20% Rest den Batch verkleinern
   und Budget für die verbleibende Verifikation reservieren.
2. **Batch-Planung:** Calls vorher grob zählen (jede Feature-Op = 1-2 features-Calls;
   apply_feature_and_check macht GET+POST!). Features-Budget ist TAGESBUDGET —
   große Rebuilds auf mehrere Tage planen statt in einer Nacht durchziehen.
3. **Client-Automatik** (client.py, Cache+Marketplace): Drossel `_MIN_GAP`
   (Default 0,4s, via env `ONSHAPE_MIN_GAP` erhöhen — nach Limit-Nähe 2-3s fahren);
   429-Backoff 15→300s mit Retry-After-Vorrang; **Budget-Guard**: warnt unter 100
   Rest, bremst unter 30 Rest automatisch 10s pro Call. Die Schwellen passen
   NICHT zu den 100er-Töpfen (GET features, FS-Eval): dort ist 30 Rest schon
   knapp; Anpassung offen.
4. Keine parallelen Prozesse gegen die Bridge; Massen-Ops bündeln; zwischen
   Groß-Batches die tatsächlichen Budget-/Backoff-Signale beachten; Renders
   sparsam (beobachtetes 500er-Fenster). Lange Wartezeiten unterbrechbar halten
   und den Arbeitsstand mitteilen, statt die Unterhaltung blockierend anzuhalten.
5. Bei hartem 429 trotz allem: `retry-after` lesen und die Zahl GLAUBEN —
   bei vierstelligen Sekunden nicht pollen, sondern Arbeit auf später planen.


## Projektdateien und Nachweise

- Bei einem abgebrochenen/langsamen Schreibaufruf vor einem Retry den Ist-Zustand
  abgleichen: ein Timeout kann nach erfolgreicher Änderung eintreten. Vorgehen
  und Weitergabe der Electron-App ohne Zugangsdaten stehen in
  [Recovery und Workflow-Pakete](references/recovery-and-sharing.md).

- Den zu Beginn gelesenen `keyCount`/`clientCount` mit dem Endstand vergleichen;
  keinen früheren Projekt-Zähler als universellen Sollwert festschreiben.
- Dokument-/Workspace-/Element-IDs und veröffentlichte Draft-IDs dauerhaft etwa
  in `var/state/` halten. API-Antworten nach `var/cache/`, HTTP-Status und
  Budget-Header nach `var/logs/`. Details zur Ablage im
  [CAD-Projektschema](../cad-fdm-design/references/project-layout.md).
- Lokale Umordnungen, Offline-Reportprüfung und Galerie-Erzeugung brauchen
  keine Cloud-Neuveröffentlichung. Teil-Exporte an ihre Quell-Mikroversion
  binden; eine unveränderte `partId` beweist keine unveränderte Geometrie.
- STEP-Translation bis `DONE` verfolgen, externe Ergebnisdaten binär über die
  Bridge laden und Format/Dateigröße prüfen. Eine Job-ID allein ist kein Export.
