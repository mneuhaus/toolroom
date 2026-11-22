# Frozen workspace compatibility corpus

The [manifest](manifest.json) preserves 12 unmodified FeatureScript sources and
21 entrypoint/parameter cases selected from Marc's CAD workspace on 21 September
2026. Each source entry records its original path, byte count and SHA-256. The
test runner reads only these copies; subsequent changes in the project folders
do not change the corpus. Explicit parameters in the manifest are part of each
case, so passing does not imply that every possible parameter combination works.

The selection exercises a wider range than R10b: open-path sweeps, nested sketch
regions, mirror/coordinate transforms, sheared solids, face queries, surface
descriptors, text engraving, lofts and multiple imported Part Studios. The
workspace inventory found 379 distinct `.fs` contents; 340 parsed as complete
modules. The other 39 were 22 top-level-variable fragments and 17 anonymous
evaluation functions, rather than automatically 39 language deficiencies.
This corpus is a selected compatibility sample, not a coverage percentage for
FeatureScript or the entire workspace.

## Observed results

The initial run passed **0/21** selected cases. After the compatibility extensions,
the complete run passed **19/21**, with **zero recovered operation failures**.
The scripts are unchanged. The text case additionally supplies the exact font
mapping described below. [Recorded results](results.json) retain the initial
failures and final measurements, manifest hash and interpreter implementation
hashes. This run used Python 3.12 and OCP 7.9.3.1.1.

| Source | Cases | Result | Valid solids per case |
| --- | ---: | --- | --- |
| NEON GT | 2 | Assembled and print layouts pass | 7 / 7 |
| Hot wire | 2 | Deployed and stowed pass | 65 / 66 |
| Lochwand | 1 | Pass | 34 |
| Step feeder | 1 | Pass | 5 |
| Mini camera R4 | 1 | Pass | 3 |
| Corner inserts R1 | 1 | Pass | 2 |
| Corner ramps R3 | 1 | Source unit error | — |
| Rear wall R29 | 1 | Pass | 1 |
| Channel bases R3 | 1 | Pass | 2 |
| Skirt halves | 1 | Pass, including text cuts | 2 |
| Printed joints | 8 | All eight kinds pass | 2 each; kind 8 has 4 |
| Sparky Z | 1 | Missing imports; further unsupported APIs | — |

NEON retains appearance on 21 monocoque faces and two faces per wheel after its
booleans and pose changes. Ten cases completed both before and after the native
history-iterator optimization; their body names, validity, volumes, bounds,
face/edge counts, appearance counts and creator lists were identical.
The two skirt text cuts were also measured independently: they remove
3.886753 and 4.066340 mm³, with no caught operation failures.

## Reproduce

From the fsocct directory:

```sh
uv sync --locked
uv run fsocct batch cases/workspace/manifest.json \
  --output output/workspace-current --timeout 240

uv run fsocct batch cases/workspace/manifest.json \
  --output output/workspace-joints --case printed_joints-printedJoint=3

uv run fsocct run cases/workspace/neon_gt.fs --feature neonGTPrint \
  --step output/neon-gt-print.step --report output/neon-gt-print.json
```

Each batch case runs in a separate process. The output directory contains logs,
measured reports and an incremental `summary.json` with implementation hashes.
`passed` means execution completed with positive, valid solids and no failed
native solid operations. `recovered` means the script caught an operation error
and continued; it is not counted as an error-free pass. A timeout or unsupported
API remains a failure. The batch exits nonzero when any case is not `passed`.

Batch execution does not export every case as STEP or compare it with Parasolid.
Use the single-file CLI for exports. The separate
[R10b regression](../r10b/README.md) verifies its 38 named solids through a STEP
round trip. Analytic geometry and history behavior are also covered by the
package's focused tests.

Current generated files are under `output/workspace-step/`, with a `README.md`
index and `exports.json` measurements. All 19 successful cases have STEP exports
checked by reimport. The two hot-wire cases require closed-face splitting on an
export-only copy of their toroidal ring; the in-memory models are unchanged.
STEP verification tolerances are recorded per export. Colors and part names are
not included in these files.

## Dependencies and limits

- `skirt_halves` uses [fonts.json](fonts.json) to map its original font name to
  the captured Open Sans Regular file. [Font provenance](fonts/source.json) and
  the [SIL Open Font License](fonts/OFL.txt) accompany it. Execution records the
  font hash. No fallback font is chosen. Glyph holes are tested, but Onshape text
  placement and kerning have not been compared.
- `corner_ramp` adds dimensionless `q0` to a length-valued vector at source line
  30. The source also extrudes under `id` but returns `qCreatedBy(id + "ex", ...)`.
  These inconsistencies remain visible in the frozen input; the runtime does not
  relax unit or ID semantics to make the case pass.
- `sparky_z` needs three imported Part Studio snapshots not supplied by this
  corpus. It also uses `qCompressed` to select from imported history and calls
  `opChamfer`, both outside the current adapter scope. Supplying geometry files
  alone would not establish compatibility for this source.

The [compatibility contract](../../COMPATIBILITY.md) describes supported options
and explicit exclusions. Valid OpenCascade solids do not establish identical
Onshape geometry, design intent, fit, strength or manufacturing acceptance.
