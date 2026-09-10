> Imported field notes. Project-specific numbers, personal preferences and historical runtime assumptions are examples. The current framework entrypoint and explicit project profiles govern reuse.

# Onshape CAD — construction and revisions

This skill covers construction. Transport rules (session bridge, no direct calls to cad.onshape.com, rate limits and Mode A/B) are in `onshape-bridge`, which applies first.

## Principle: FeatureScript first

Feature-tree reads and FS evaluation have scarce, separate rate-limit budgets. Measurements to date found that studio edits through the session bridge did not consume API-key quota, but they still have rate limits. A custom feature pinned to a source microversion does not adopt studio edits merely because the source was uploaded: its namespace reference must be updated. See [FS revisions and local files](revision-workflow.md).

Before changing an existing studio, preserve its current native features and user edits. An old generator must not replace them; add a separate finishing feature when the geometry permits. For adapters, flap variants or shared parts, also read [Interfaces and variants](retrofit-and-variants.md).

- Build new geometry as a custom feature in the central Feature Studio, with one `annotation { "Feature Type Name": … } defineFeature` block per feature. Edit through studio contents: `GET/POST /api/v9/featurestudios/d/{d}/w/{w}/e/{e}` (`BTFeatureStudioContents-2239`).
- Use `op*` primitives (`opExtrude`, `opBoolean`, `opLoft`, `opSweep`, `opDeleteBodies`, `newSketchOnPlane` + `sk*`). The high-level wrappers (`extrude()` etc.) were unavailable in the tested `defineFeature` context.
- `defineFeature` requires `precondition { }`; only `==` is allowed in preconditions, not `>`. Avoid umlauts in annotation names. `~` converts to a string; `toString()` does not exist.

### Editing studio source with scripts

- **Keep splices local to a segment:** isolate the feature block first (`i0 = src.index('"Feature Type Name" : "X"')`, `i1 = src.index('annotation { "Feature Type Name"', i0+10)`), then replace only within `src[i0:i1]`. Never use an unscoped global `src.index()` or replacement: patterns such as `id + "u"` occur repeatedly, and a match in the wrong feature can duplicate code.
- Before each POST, check balanced `(){}[]` delimiters and assert replacement counts (`assert seg.count(old) == n`).
- **Parse-error signature:** all Part Studios suddenly show zero parts, indicating that the studio no longer parses. Previous causes include a global splice hitting another feature and Python escapes leaving backslashes in FS.
- Inserted snippets may use only variables declared by the target feature. Otherwise the feature errors and the part falls back to base features. Delete sketches explicitly with `opDeleteBodies` per block rather than relying on a shared `sketches` variable.
- Numbers in `plane()` normals and `opExtrude` directions need full precision (at least 15 digits). Unit vectors rounded to 4–6 digits can fail silently: no sketch is created or a cut misses the material.

## Geometry patterns

- **Boolean joins:** tangential contacts between a boss and round surface, rib and face, or rib and bore wall needed 0.2–0.5 mm overlap in the recorded examples. Exact tangency can produce `NON_MANIFOLD` errors or disconnected bodies. Anchor rib profiles into fresh bore walls at r + 0.25 mm.
- **Avoid per-edge fillet loops** across union edges: regeneration can hang for minutes. If a local fallback skips individual edges, record them and inspect the actual edge result; `try silent` does not prove success. Kernel fillets often fail because the radius exceeds the available geometry. In such cases, calculate analytic tangent arcs directly in the sketch profile.
- **Slab trap:** nested rectangles in one sketch fill the region. Build a frame from four rectangular strips; create holes as separate REMOVE extrudes after the union, not in the panel sketch.
- **Frustum/cone cuts:** use `opLoft` with `"profileSubqueries": [qSketchRegion(a,false), qSketchRegion(b,false)]` between two offset planes. Start the opening 0.1 mm outside the material.
- **Rounded rectangles in FS:** four lines and four `skArc` calls; the arc's intermediate point is the corner plus r/√2 along the diagonal.
- **Determine the sketch basis explicitly:** local y = normal × local x. With x = +X and normal = +Y, y = −Z; with normal = −Y, y = +Z. Derive the intended side from this basis, not a generic front/back name. Select the extrusion direction separately and check unit vectors.
- Resolve target queries again after cuts or unions that change topology, and check the expected body count. Even a previously robust query can become invalid; see the revision workflow for diagnosis.
- **Tapered plug connections, learned from the brace fit:** matching tapered tongue and pocket surfaces provide alignment, but a planar depth stop defines the dimension: tip face against pocket floor. The cone itself must not define it, since a press fit makes the dimension tolerance-dependent. The full section must end exactly at the mating face: even 0.6 mm of excess creates a visible step and jams in the taper.

## Assembly before detailed design

Apply the [assembly review](../../../knowledge/assembly-review.md) to adapters and mechanisms: check separate preassemblies, actual screw heads and tool paths, joining the subassemblies, then operating movement. For a plate with opposing screw directions, first look for a cyclic assembly sequence. Large access windows must not casually remove the load-bearing wall. A split adapter with broad seating and an accessible connection is one possible solution, not a requirement for every part.

## Verification loop matched to the geometry change

1. **Part count** (`GET /api/parts/...`): compare with the expected count. More can indicate a silent Boolean failure leaving small tool bodies; fewer or zero can indicate a parse or regeneration error.
2. **Bounding box:** compare with target dimensions.
3. **Volume delta:** use it as a plausibility check. For a single expected cut, unchanged volume may indicate an empty cut. Equal total volume proves neither equal shape nor correct mating faces; also measure the affected contours, axes and contacts.
4. **Renders** (`shadedviews`, with its own budget window): use an isometric view for context and **top/front silhouettes for mating faces**. A step appears as a notch in the outline; a clean taper appears as a smooth trapezoid. `pixelSize:0` means auto-fit; a fixed `pixelSize` is in m/px (0.0001 ≈ 0.1 mm/px).
5. Include new adapter halves, screws, nuts and washers in moving groups. Define permitted contacts by function and part identity, not old array indices. Check changed mounts and protruding screws across the affected travel against the complete reference. Local path or documentation changes need only the corresponding offline checks.
6. If parts disappear from renders, check their hidden status in the UI first: hidden parts affect `shadedviews`.

## Assembly hygiene

- **Changing part IDs:** feature deletion/insertion and topology-changing FS edits can change `partId`. Onshape can update assembly references automatically; this happened for all six instances in Funnel Guide R4. Audit the actual result and repair only broken references rather than deleting and reinserting all instances. Use `sorter-beltfeeder-handoff/scripts/asm_audit.py` as a pattern to check every instance's `partId` against its element across all assemblies in the document. Cleanup can also affect instances in secondary assemblies.
- Keep baseline and result separate. Record existing legacy orphans without counting them as new errors or changing unrelated assemblies. Check changed body identity separately from stale geometry caches.
- **Compute poses deterministically** from the carrier part and known relative pose (`T_brace = T_plate ⊕ local offset`). Avoid relative nudges based on heuristic instance classification.
- Insert an instance with `POST .../instances`; it starts at identity. Diff the instance list to obtain its new ID, then call `POST .../occurrencetransforms`. For ASSEMBLY instances use `isRelative:true`; `false` collapses children. The mate endpoint tested at the time returned 404, so this workflow used fixed poses. Label these as positioned assemblies. Complete instance lists and a sweep test establish neither motion mates nor calibrated servo end angles.
- Onshape recycles instance node IDs: never hard-code deleted IDs for reuse. Instances from empty or ERROR studios are immediate orphans. Feature IDs may contain `/`; URL-encode them.
- Standard-content configuration strings for DIN screws are signed. Clone them from a reference instance inserted through the UI rather than constructing them manually.

## Recorded project design standards

These were Marc's project standards in the source notes; apply their dimensions only through an explicit current project profile.

- **Geometric interlocking before screws; avoid notches:** 0.42 mm chamfers / R4.2 rounds. Print plastic screws horizontally.
- **M3 crush grip** (`m3_hybrid_hole`): wall r2.1, three ribs formed by R0.84 arcs tangent to r1.1 (clear diameter 2.2 mm), transitions R0.42. Retrofit recipe: Ø6.3 clean bore → fresh Ø6.6 disc with 0.15 mm anchoring overlap → one wavy contour cut comprising 12 arcs. Through-hole diameter: 3.4 mm.
- **608 bearing seat:** Ø22.7 pocket plus six crush ribs, r0.7 at r11.6.
- **Shaft clamp:** an axial M3 screw presses the flank against the D-flat through a Ø2.8 channel with 0.2 mm overlap into the bore wall.
- **Revision engraving:** each part carries “NAME Rn”, height 2.4 mm, on a hidden underside or inside face. Maintain a central `REVS` table (`const REVS = {...}` in the Feature Studio). Increment for geometry changes; cosmetic engraving-position changes do not increment it.
- **Printability before appearance:** parts fit a 250 × 250 mm bed, are designed for support-free printing (walls ≥45°, inverted or horizontal orientations), and do not protrude below the print plane.
- **Conveyor paths:** nothing may narrow the uphill lane in the conveying direction, which can trap parts. Meter flow with a tunnel section: closed channel, opening = cleat height + clearance, rather than gate walls.
- **One binding dimension and height system per project:** for example, BeltFeeder belt top 51.93 mm, rails 45.93 mm, tunnel roof 59.93 mm, bolted plate spacing 100.8 mm. Measure every part against it rather than choosing locally convenient dimensions.
- **Document local coordinates:** record which local face is inside/outside or top/bottom in the standard pose. For the BeltFeeder plate, local y = 0 is outside and y = −8 is inside. Guessing sides causes avoidable errors.

## Working practice

- For ongoing projects, separate sources, active scripts, references, exports, results, working data and archives; see [Project layout](../../../knowledge/project-layout.md). Keep established scripts in `scripts/`, not a collection of API JSON files in the project root.
- Maintain a project handoff such as `docs/HANDOFF.md`, covering IDs, dimension system, part status, quirks and open issues. Read it before resuming work.
- If the user cannot see local images, provide a checked, reachable review artefact link; see [Sharing CAD views](sharing-views.md) for the workflow and Postplan experience.
- For screenshot-based feedback, find the cause in the model first through measurements and silhouette renders, fix it, then verify with a render from the same viewpoint.
