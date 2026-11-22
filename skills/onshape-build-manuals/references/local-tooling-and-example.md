# Local tooling and the Sparky example

This reference describes Marc's installation as observed on 2026-09-09. Use it
when those tools are present. It is not an Onshape-wide API or account guarantee.

## Existing Onshape connection

The signed-in Electron app is at `~/Workspace/onshape-app`; its HTTP session bridge
listens at `http://127.0.0.1:8317`. In this setup all Onshape REST goes through that
bridge. Do not silently fall back to a metered API-key connection. Live transport
instructions also exist at `~/.claude/skills/onshape-bridge/SKILL.md` when installed.

Reuse the signed-in app. For live work, check the local health, current endpoint
budgets and authoritative metering counters. Compare the same reporting window
before and after a batch. Historical counter totals and exhausted buckets are not
permanent values to copy into a new task.

Do not run bridge writers concurrently. Inspect destination state after a timeout
before retrying a mutation. Stop the affected batch on a repeated unexplained
failure, changed metering or exhausted bucket; keep useful local work moving.
Creating guide assemblies and updating PDF/blob tabs does not ordinarily need
Part Studio feature-tree reads or FeatureScript evaluation. A blocked feature
bucket need not block documentation endpoints with available budget.

## Observed publication operations

The existing project has tested bridge scripts for assembly reconciliation,
metadata updates, multipart blob uploads and folders. Prefer those known helpers
over inventing new undocumented calls.

- Upload a new file: `POST /api/blobelements/d/{did}/w/{wid}` with multipart `file`.
- Replace an existing guide file: the same path plus `/e/{eid}`.
- Download it for verification: `GET /api/blobelements/d/{did}/w/{wid}/e/{eid}`.
- Create a saved version: `POST /api/documents/d/{did}/versions`. The tested body
  includes **both** `documentId` and `workspaceId`, plus `name` and `description`.
  Omitting `documentId` returned HTTP 400 in this workflow.

Keep the existing blob element IDs and record the returned state after writes.
Create a new saved release when the artifact fingerprint changes. Verify upload
content before creating the release; HTTP 200 alone only confirms acceptance.

Folder operations in the worked example used the running client's element-tree
singleton through CDP, rather than replacing the document. The private client
methods and numeric webpack module IDs are version-sensitive: inspect the current
UI or existing helper before using them in another installation.

Similarly, the observed absolute-transform operation on an existing assembly
occurrence could collapse child placements. Do not copy a transform operation
without verifying all nested part poses. Guide stages can use directly placed
part references where this makes ownership and verification clearer.

## Binary uploads: detect the running bridge

The maintained `onshape-app` was corrected on 12 September 2026: HTTP request
bytes now cross the Node/renderer boundary as base64 and are decoded to a
`Uint8Array` before the authenticated fetch. `/_bridge/health` reports
`capabilities.binaryRequestBodies: true` in the running fixed version. A real
13,232,394-byte SolidWorks ZIP upload/download matched SHA-256 and translated
successfully; the app's multipart/Unicode regression checks also passed.
Source changes alone do not establish that an older running process has the fix.

With that capability present, upload the original bytes normally and retain the
download/hash verification. The following PDF workaround is for older bridges
that still decode request bodies as UTF-8; it is unnecessary for the fixed one.

### Historical PDF failure and legacy workaround

In the previously inspected `onshape-app/src/main.js`, **responses** use an array-buffer/base64
round trip and preserve binary bytes. **Requests** are collected with
`Buffer.concat(chunks).toString('utf8')`. This includes multipart uploads: binary
PDF font streams become Unicode replacement characters before reaching Onshape.
The earlier bridge description saying binary traffic was byte-exact was too broad.

Evidence from the guide: the uploaded PDF's downloaded hash equalled the local
PDF after UTF-8 decode with replacement and re-encode, rather than the original
file hash. The upload had returned HTTP 200. JSON and ASCII STEP transfers did not
establish that arbitrary binary uploads worked.

For this bridge, prepare the generated PDF with:

```sh
uv run /path/to/onshape-build-manuals/scripts/make_pdf_transport_safe.py \
  output/assembly-guide.pdf exports/assembly-guide.pdf \
  --report output/reports/pdf-transport.json
```

The helper wraps non-ASCII PDF streams with an `ASCII85Decode` filter, preserves
their existing filter chain, rewrites cross-references and uses an ASCII comment
in the header. Images and fonts decode to the same data. It checks stream content,
text, page geometry, annotations and outlines before writing the output. It does
not rasterize the PDF. Run it on generated manuals, not signed PDF originals.

After uploading through the bridge, read the downloaded response as bytes and
compare SHA256 with the exact local file. Keep that check in the publisher. If the
transport has since been made binary-safe, skip the workaround but retain the
artifact verification. Do not broaden a manual task into changing app credentials
or restarting the CAD environment just to work around this known format issue.

## Worked project and entry points

The retained implementation is at:

`~/Workspace/cad/spar-key-z-axis/`

Inspect only the modules relevant to the task:

| File | Reusable idea |
| --- | --- |
| `docs/Assembly-Guide-Workflow.md` | Source, sequence decisions and regeneration order |
| `docs/Rendering-Style-Study.md` | A–P treatments, same-camera comparisons and shortlist outputs |
| `src/assembly-guide/guide.json` | Semantic roles, stages, views and per-step inventory |
| `src/assembly-guide/part-roles.json` | Identity resolution independent of STL order |
| `src/assembly-guide/layout.json` | Sidebar captions, critical notes and rendering palette |
| `src/assembly-guide/render-styles.json` | Stable A–P preset IDs and original study settings |
| `scripts/r12/assembly-guide/prepare-recipe.py` | Build a shared native-stage/render recipe |
| `scripts/r12/assembly-guide/publish.mjs` | Reconcile only guide-owned native instances |
| `scripts/r12/assembly-guide/render.py` | Blender orthographic CAD renders and projections |
| `scripts/r12/assembly-guide/render_materials.py` | Shared product materials and camera-relative lights for views and icons |
| `scripts/r12/assembly-guide/render-style-study.py` | Same-geometry style rendering isolated from the manual cache |
| `scripts/r12/assembly-guide/build-style-comparison.py` | Normalized framing, linked overview/pair PDF and ordered image shortlists |
| `scripts/r12/assembly-guide/build-colour-plan.py` | Illustrated colour-role inventory including repeated physical pieces |
| `scripts/r12/assembly-guide/build-pdf.py` | ReportLab pages, crop-aware overlays and PDF checks |
| `scripts/r12/assembly-guide/review-pdf.py` | All-page previews, text/link/profile checks and transport pixel comparison |
| `scripts/r12/assembly-guide/publish-files.mjs` | Stable blob tabs, byte verification and releases |
| `scripts/r12/assembly-guide/publish-colours.mjs` | Scoped CAD appearances, saved prior state and linear RGB to sRGB conversion |
| `var/state/assembly-guide-r12.json` | Persistent step, folder and publication IDs |
| `var/state/functional-colours-r12.json` | Original and verified printed-part/buildplate appearance state |

The project scripts contain Sparky-specific roles, dimensions and paths. They are
examples to adapt; do not run them against another document or copy its IDs into a
new project's publication map. The new skill does not depend on this directory
being present. Its workflow, layout defaults and PDF helper stand alone.

For this example, actual geometry was exported from Onshape as STEP, tessellated
through native Fusion in an unsaved scratch document and rendered in Blender.
The native numbered Onshape stages remain the durable assembly reference. Future
projects can use direct Onshape views or a different faithful export route.

Local example executables were `uv`, `/Applications/Blender.app/Contents/MacOS/Blender`
and `/opt/homebrew/bin/pdftoppm`. Discover equivalents in another environment.
Native Fusion calls can return shell status 0 with `success: false` inside their
response; inspect the native result and expected files.

## Example-specific decisions, not defaults for other machines

The rendering edition inspected on 2026-09-09 has 23 native stages, 17 A4 landscape
pages, nine printed pieces and 153 illustrated physical parts. Ten of those are
clearly labelled nominal mounting screws added only to guide references. The manual
and colour work did not change solid geometry; this statement does not validate
later mechanical revisions or repairs.

The selected N profile and its functional overrides rendered all 31 assembly views
and 39 inventory icons with Cycles, using 64 and 40 samples respectively. They live
in `output/r12/assembly-guide/renders-teenage-engineering/`. The original Workbench
images in `renders/` remain the source of the historical comparison. N's study image
is 3840 × 3200; the manual retains each recipe view/icon's original dimensions and
camera. Selecting a 4K study preset does not make every manual image 4K.

`render.py -- --stale` compares recipe and resolved preset/settings hashes. It does
not detect changed renderer code or changed mesh bytes on unchanged paths. In those
cases explicitly rerender affected assets before rebuilding the PDF. Current
profile checks cover the full view/icon set; original study checks compare camera,
object count, dimensions and preset metadata, which alone cannot prove unchanged
mesh geometry. Preserve or refresh the source snapshot as described in
[Rendering styles and colour roles](rendering-styles-and-colour.md).

The user's motor really uses two right-hand screws; covered left holes must not
be populated for visual symmetry. Actual X axle length is unknown; M5×40 is a
proposal, not a confirmed measurement. The belt is open at the moving carriage,
and both ends are clamped before later assembly blocks access. These facts explain
the example sequence; they are not general instructions for all Onshape guides.
