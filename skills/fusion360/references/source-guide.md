> Imported field notes. Project-specific numbers, personal preferences and historical runtime assumptions are examples. The current framework entrypoint and explicit project profiles govern reuse.

# Fusion 360 via MCP + fusion-khana

## Transport

- MCP server `fusion` (Streamable HTTP, `http://127.0.0.1:27182/mcp`), with `mcp__fusion__*` tools for execute/read/update. The Fusion desktop app must be running.
- Without a registered server, the recorded fallback uses direct JSON-RPC (`initialize` → `notifications/initialized` → `tools/call`); helper `tools/fcall.py` (`uv run python fcall.py script <file.py>` / `shot <out.png> [dir]`).
- `fusion_mcp_execute {featureType:"script", object:{script}}` executes Python in the Fusion process: `def run(_context)`, prints become tool output, and exceptions become errors with tracebacks. Never swallow exceptions in the script.
- **The Fusion instance is shared and single-threaded.** An open modal dialog or hanging cloud `documents.open` blocks every script call (“Cannot perform 'script' while a command dialog is open” / timeout). Do not poll repeatedly. The source workflow used a background watcher with a 120-second interval and asked the user to close the dialog; keep any waiting interruptible.

## Architecture: rebuild from source

In this workflow, the part program in git is the source of truth; the Fusion timeline is the published result. For changes, edit the program and rebuild a fresh document rather than patching the timeline. This avoids depending on face or edge IDs.

- Library: `~/Workspace/cad/fusion-khana/fusion_khana/`, a separate git repository.
- Part programs: `~/Workspace/cad/fusion-khana/parts/<part>.py`, with a `P` parameter dictionary, `build(k)` and `main()`. Factor shared frames and helpers into `<project>_common.py`, imported by the variants. The BristleBot family uses `bristlebot_common.build_frame(k, P)` plus a variant-specific belly. Calculate expected frame volume through `frame_expect(P)` rather than a literal sum.
- **One stable cloud document per part program:** `Khana(new_doc=...)` reuses and clears an open document with the same name instead of accumulating tabs. `k.accept("note")` saves a passing build as a Fusion version. Failed builds remain unsaved. Do not query the version number immediately after saving: cloud saves are asynchronous and can return a stale value.
- Set **`direct=True` (DirectDesign)** when free planes or lofts are needed; `setByPlane` is available only without a timeline. `_clear_design` catches the `des.timeline` runtime error and clears construction planes as well.
- Bootstrap: `tools/bootstrap.py`, with the `PART` constant set, sent through `fusion_mcp_execute`. **Fusion caches modules in the process.** `reload()` alone leaves transitive part-to-part imports stale. Remove all modules whose `__file__` contains `BASE` from `sys.modules` before importing; the template does this.

## Assembly, print preparation and project layout

- For screwed or moving assemblies, add the [assembly review](../../../knowledge/assembly-review.md): check that each screw can be inserted, and inspect tool corridors and approach paths. A final-position interference test alone is insufficient.
- For Bambu Studio, read [Profile and print checks](../../../knowledge/print-preparation.md). The Orca/Voron workflow below is an existing example; select the printer, material and plate from the current task.
- Use [Project layout](../../../knowledge/project-layout.md) for ongoing projects. Update existing library and import paths when reorganising files.

## Required verification loop in the source workflow

1. Give every volume operation an `expect=<mm³>` value, calculated beforehand. A mismatch raises `BalanceError` with context. Recorded tolerances: extrudes 0.5 mm³, fillets/chamfers 1.5–3 mm³, lofts 5–18 mm³ because of section interpolation. Text engraving is not predictably analytic because of small font wedges, so `k.text()` deliberately omits `expect`.
2. **Volume accounting catches geometry errors.** Recorded examples: the poke beneath a round channel forms a saddle rather than a flat ring (`poke_expect` integral); the foot-gap target needed trapezoidal rather than rectangular integration (−9 mm³ per leg); a rear snap hook silently refilled the switch window (+2 mm³). Check the geometry assumption before relaxing tolerance.
3. End each program with `check_total` (or tub volume when reference parts are present), `check_interference` over `all_bodies`, `check_clearance` (example gaps ≥0.19 mm), `check_bed` (example 250 × 250 mm), and a targeted `export_stl(dir, bodies=…)`.
4. Cross-check externally against Onshape with a bidirectional trimesh difference using sampling and `closest_point`. **`tessellatedfaces?chordTolerance=` uses metres**: 0.02 mm = `0.00002`. In the recorded comparison, differences ≤0.2 mm were tessellation noise; larger differences indicated missing features. The check needs `trimesh` and `rtree`; scale the Onshape mesh from metres by ×1000.
5. Before print release, run `uv run tools/sliceability.py <stl…>`. The existing CLI default uses OrcaSlicer with Voron presets; adapt the binary and actual profiles for another printer or Bambu Studio. Review time, weight, support percentage, maximum bridge span and bed-contact percentage. `--compare` checks the supplied pose against flip-x180 using a temporary trimesh STL; Orca's own `--rotate-x` / `--ensure-on-bed` flags crashed with the composed profiles. `--map DIR` writes underside overhang maps: blue = bed, red = shallow unsupported surfaces. The bed plane is a design decision per part: nothing may protrude below it; change the split and fastening if needed. The source notes refer to `cad-design-preferences` memory.
6. Structural screening: `uv run tools/strengthcheck.py <stl…>` sweeps Z sections in the print pose and examines A(z), Wx/Wy(z) and island splitting. It reports necks at layer interfaces, features with thin layer attachments, and slender upright bars. The source notes used approximately 50% as a layer-tension heuristic for pads loaded in Z; this is not a calibrated material value. `--compare` checks both poses; `--plot DIR` writes A/W curves. The beam calculation was checked analytically against W = b·h²/6. This is a geometry heuristic, not FEA.
7. Capture a screenshot with `fcall.py shot` or `fusion_mcp_read {queryType:"screenshot"}`. In a shared instance, the screenshot captures the currently active document, which may belong to another session. Use an STL comparison or local trimesh render to verify the intended geometry.

## fusion-khana API quick reference

All dimensions are in **mm**, with the same world frame as the Onshape projects. Initialise with `k = Khana(new_doc="…", direct=True)`.

- **Plane sketches:** `k.sketch(name, plane="xy"|"xz"|"yz")`. All sketch coordinates are world-coordinate pairs: xy → (x,y), xz → (x,z), yz → (y,z). The internal `modelToSketchSpace` conversion handles the xZ mirroring quirk without guessed signs. Primitives: `.rect(x0,y0,x1,y1)`, `.circle(x,y,d)`, `.circles(pos,d)`, `.polyline(pts, close=True)`, `.rounded_rect(...)` (xy only).
- **Extrude:** the `[w0,w1]` interval follows the plane normal (xy → z, xz → y, yz → x), with signs resolved from the actual sketch world normal. Use `k.new_body(sk, w0, w1, name, expect=)`, `k.cut(sk, w0, w1, [bodies], name, expect=)` and `k.join(...)`. Always specify participants.
- **Free planes and lofts:** for sections across paths, such as a foot gap along a sine curve, use `sk = k.sketch_free(name, origin, normal)` and `sk.poly3(world_pts)`, then `k.loft_cut([sk0,sk1,…], [bodies], name, expect=)`. Requires `direct=True`. Extend the section 1–2 mm beyond the tip; ending at the free path endpoint can leave spikes.
- **Components:** `with k.component("Tub X"):` builds sketches and bodies in a named subcomponent. Use this for reference dummies. Otherwise, in DirectDesign, a `new_body` created inside a tight pocket or on a neighbouring body can silently merge with it, as happened to a miniature motor dummy and tub. `k.all_bodies()` collects the root and all occurrences for interference, reports and exports.
- **Colours:** `k.color(body, "petg"|"pcb"|"gold"|"silber"|…|(r,g,b))` uses a matte plastic appearance with a custom colour, copied from “Plastic - Matte (Gray)” in the “Fusion Appearance Library”, property “Color”. Palette keys are in `_RGB`; `silber` is the existing API key for silver.
- **Text engraving:** `k.text(s, box=(x0,y0,x1,y1), z_top, depth, [bodies], name, height=)`. Use SketchText directly as the extrusion profile; `sk.profiles` is empty for text. No `expect`.
- **Render hygiene:** `k.hide_construction()` hides sketches and planes.
- **Edges:** `k.edges_flat_at(z)`, `k.edges_vertical_at(corners)`, `k.is_convex(edge)`. Convexity uses an orientation-independent dihedral test through chord midpoint and `pointContainment`; bisector tests did not work.
- **Style:** `k.fillet(coll, r, name, expect=)`, `k.chamfer(coll, d, name, expect=)`, `k.chamfer_flat_convex(z)`. The latter chamfers convex edges in the plane and logs skipped notches. For stud-head chamfers, use `edges_flat_at(top)` and `chamfer`; this finds cap edges after a union.
- **Reference parts:** represent purchased parts as dummies or envelopes in `<project>_ref.py`, separate from the print program. A strict outer envelope makes clearance checks conservative for the represented geometry. Place and colour them in situ inside `k.component("Reference")`. `k.import_body(doc_prefix, matrix, name)` copies a body from an open document using TemporaryBRep and a transform. Cloud `open` repeatedly hung in the source workflow; a reference drawn from measurements was more robust. `k.import_step(path)` collects bodies recursively from STEP sub-occurrences.
- **Kinematics:** `k.sweep_check(moving, statics, [(dx,dy,dz)…])` / `k.check_sweep_free(...)` checks moving parts across all sampled travel positions. Include a negative test beyond the stop to establish check sensitivity.
- **Macros:** `puzzle_seam_profile(sk, x_line, tab_dir)`, `pt_axis(k, pos, z_top, z_seam, top_body, bottom_body)`.
- **Loft/spline/shell:** `sk.spline(pts)`, `skfree.spline3(world_pts)`, `skfree.circle3(centre_world, d)` use fitted splines and `isClosed`. `k.loft(sections, name, op="new"|"join"|"cut", bodies=…, expect=)` requires exactly one profile per section; otherwise the library reports the section name and likely open contour. `k.shell(body, faces, t, name)` hollows inward. Pick faces and edges geometrically with `k.face_planar_at(body, "x", 126)`, `k.faces_planar_at(...)`, and `k.edges_planar_at("x", 0.0)`, which generalises the Z-only `edges_flat_at`.
- **Report/export:** `k.report()` uses all bodies; `k.export_stl(dir, bodies=[…])` uses MeshRefinementHigh; `k.save(name)` and `k.accept(note)` save the result.

## Measuring and verifying dimensions

- **Prefer vendor CAD to shop photographs:** upload SLDPRT/STEP to the cloud with `folder.uploadFile`, poll `uploadState`, then sample the body bounding box and polar contour. This revealed that the LilyPad DEV-13883 measures 32.4 × 30.2 mm: its sewing tabs extend beyond the Ø29 circle. The photograph-based estimate of 28 × 29 mm was approximately 3 mm too narrow.
- Mark photograph-based estimates in the program docstring as “PROVISIONAL — measure before use”; keep them easy to correct in the parameter dictionary.

## Fusion quirks

These supplement the source `[[fusion-mcp-quirks]]` memory.

- Native API units are cm; the library wraps conversion. In raw scripts, convert mm by ×0.1.
- Use `chamferFeatures.createInput2` with `addEqualDistanceChamferEdgeSet(…, False)`, and `filletFeatures.createInput().edgeSetInputs.addConstantRadiusEdgeSet(…,False)`. Set `isTangentChain=False` to prevent unintended chain propagation.
- **Fusion rejects overflow fillets** when the radius exceeds a rib width (`ASM_ABL_CAP_COMPLEX`, for example on a 0.9 mm tongue). Construct a quarter-circle cutter with `round_cutter_pts`; the neighbouring cut trims it like a kernel fillet.
- Features added later through the Onshape UI are absent from the original FS source. Detect them during reconstruction with mesh sections from `tessellatedfaces`, as with the r1.2 bead on the flat tub.
- A cut that splits a body yields two bodies; name them afterwards by position.
- Export STL with MeshRefinementHigh. Recorded Onshape STLs were in metres; Fusion STLs were in mm.

## Reference pilots

- `parts/cff12_plattform_v7.py`: reported as matching Onshape, volume 1,654,611 mm³ and STL difference ≤0.17 mm. Timeline pilot.
- `parts/bristlebot_*.py`: shared frame (`bristlebot_common`), flat/torpedo/mini/gen2 variants, parametric lid and reference parts (`bristlebot_ref`) in coloured components. Demonstrates plane sketches, lofts, `direct=True`, components, colours, text and in-situ references.
- `parts/lego_studcal.py`: stud calibration strip with 2 × 2 blocks and engraved text.

## Not yet built in the source workflow

- Scan mesh import as a reference body for fitting against actual scan geometry.
- Overhang and wall-thickness printability checks like cad-khana.
