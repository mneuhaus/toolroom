# fsocct

Run a useful subset of **Onshape FeatureScript locally against OpenCascade**.
The input stays FeatureScript: a tokenizer, parser and interpreter evaluate it,
and explicit library adapters create real B-rep solids through OCP. No Onshape
session, server, JavaScript transpilation, or Python `eval` is involved.

This is an experimental compatibility engine, not a replacement for Onshape's
runtime or Parasolid. Unsupported language constructs, imports, API calls and
operation options fail explicitly. See [compatibility](COMPATIBILITY.md) before
running an existing Feature Studio.

## Run it

From this directory, with [uv](https://docs.astral.sh/uv/) installed:

```sh
uv sync --locked
uv run fsocct run examples/perforated_plate.fs \
  --step output/plate.step \
  --stl output/plate.stl \
  --report output/plate.json

uv run fsocct run examples/perforated_plate.fs \
  --param 'width=100*millimeter' --step output/wider.step

uv run fsocct run examples/revolve_and_loft.fs --step output/turned.step
uv run fsocct run examples/canonical_m3_tool.fs --step output/m3-tool.step
```

The environment uses Python 3.12 and the locked OCP/OpenCascade package. After
dependencies are installed, execution is offline. `uv run --project /path/to/fsocct
fsocct ...` also works from another directory; input and output paths are relative
to the current working directory.

STEP export checks solid count, validity, per-solid volume and overall bounds by
reading the file back. If trimmed periodic faces become invalid during transfer,
it retries after splitting closed faces on a private export copy. The CLI report's
`exports.step` records this and its tolerances. The in-memory model is unchanged.
Exports contain geometry without colors, part names or assembly structure.

`--feature NAME` selects an exported `defineFeature` value (or an exported
function taking `context, id, definition`). A single exported feature is selected
automatically. `--param NAME=EXPRESSION` accepts FeatureScript expressions, so
lengths retain their units and module-local enums/constants are available. The `defineFeature` defaults map supplies omitted
parameters; UI annotations do not supply defaults.

`fsocct check file.fs` checks **parsing only**, not library support or geometry.
Failures print a source path, line and column when available, and exit with code
2. Failed evaluation does not overwrite exports. The CLI stages requested files
before replacing destinations; an operating-system failure during final file
replacement can still leave a partially replaced set.

## What works

- Typed functions and overloads, closures and arrow lambdas, predicates and
  preconditions, variables, constants, loops, maps, arrays, boxes, exceptions.
- Dimension-checked length/angle arithmetic, vectors, matrices, hierarchical IDs and
  `defineFeature` defaults.
- `fCuboid`, `fCylinder`, directly positioned sketch lines/arcs/circles/rectangles,
  nested regions with holes, open sweep paths and text from an explicitly mapped font.
- Extrusion, revolution, loft, sweep, booleans, fillets, affine transforms,
  coordinate systems and patterns.
- Body queries, face lineage through supported modifications, point/geometry
  filters, surface descriptions, volumes, areas and bounding boxes.
- Named, hash-checked Part Studio snapshots, body instantiation, STEP and binary STL output.

The [API support table](COMPATIBILITY.md) states the restrictions for each
operation. In particular, `skSolve` assembles explicit geometry; it does not solve
sketch constraints or partition crossing loops. Face lineage uses local OCCT
history; it is not Onshape's complete persistent naming system. Evaluated
face/edge handles still become stale after body modification.

## Existing source and imports

The [canonical M3 example](examples/canonical_m3_tool.fs) imports Toolroom's
[existing FeatureScript module](../skills/onshape-cad/lib/m3_hybrid_hole.fs)
**unchanged**. It exercises 12 exact circular arcs, helper functions, unit and
frame checks, extrusion, revolved entry relief and a union. The result is a cutter
used for software verification, not a manufactured joint acceptance result.

Standard-library imports bind to the local adapters. Their version string is
recorded in a warning; it does not select or emulate that Onshape release.
Cloud tab imports require an explicit local mapping:

```json
{
  "documentId/versionId/elementId@microversion": "vendor/source.fs"
}
```

```sh
uv run fsocct run my-feature.fs --imports imports.json --step output/result.step
```

Mapping paths are relative to the JSON file. A key without `@version` is an
explicit version-independent override. Namespaces and exported functions/constants
are supported. Relative `./` and `../` imports are a local extension resolved
against the importing source file. No cloud source is fetched automatically.

For imported Part Studios, freeze a named STEP export into a local manifest:

```sh
uv run fsocct snapshot reference.step --output vendor/reference.json
```

Map the imported tab/version to that JSON file. Its `build({})` creates a context
from the captured B-rep solids with their original part names. Every B-rep hash is
checked on load. This replays the exported geometry; it does not interpret the
Part Studio's feature history or recalculate another configuration. The snapshot
command accepts named single-solid STEP roots and rejects assemblies.

The [frozen R10b case](cases/r10b/README.md) evaluates the complete captured
construction with eight local Part Studio dependencies. Its regression runner
checks all 38 named solids and a STEP round trip:

```sh
uv run python cases/r10b/verify.py
```

The [workspace compatibility corpus](cases/workspace/README.md) freezes another
12 sources and 21 parameter/entrypoint cases, including sweeps, printed joints,
lofts, text engraving and NEON GT's face coloring:

```sh
uv run fsocct batch cases/workspace/manifest.json \
  --output output/workspace-current --timeout 240
```

Each case runs in a separate process with a wall-clock timeout. Reports include
solid validity, measurements, source and implementation hashes, and failures
caught by the script itself. `passed` requires valid solids and no caught native
operation failures. A `recovered` case needs review; a valid final solid alone
does not establish that every requested operation succeeded. The batch exits
nonzero unless every selected case passes. Use repeated `--case ID` options to
select cases. Originals remain untouched; snapshot hashes are checked each run.

Current local exports and their file index are under `output/workspace-step/`:
19 successful workspace cases, each checked after STEP reimport. These are
generated artifacts; use the single-file CLI to reproduce an individual export.

Sketch text requires a JSON mapping of font names to exact local font files:

```sh
uv run fsocct run cases/workspace/skirt_halves.fs --feature skirtHalves \
  --fonts cases/workspace/fonts.json --step output/skirt.step
```

There is no system-font fallback. The report records each font's SHA-256. Text
layout has not been compared with Onshape and can differ despite matching font files.

## Python API

```python
from fsocct.api import run

build = run("examples/perforated_plate.fs", parameters={"width": "100*millimeter"})
build.step("output/plate.step")
print(build.report()["volume_mm3"])
occt_shape = build.context.shape()  # OCP TopoDS_Compound
```

For language-only evaluation, use `Engine().load_source(source).call(name, *args)`
from `fsocct.runtime`. [Architecture](ARCHITECTURE.md) describes the extension
points and the distinction between runtime errors and missing compatibility.

## Verification

```sh
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
```

The tests measure solids, rather than just checking that code executed: analytic
plate/revolve/loft/sweep volumes, nested holes, affine and coordinate transforms,
face lineage/appearance, text holes, STEP re-import, binary STL structure and
evaluation of the existing M3 module. A captured boolean regression checks that
OCCT's optional face unification cannot damage a valid result or its operands.
Language errors, failed-operation rollback, corpus timeouts, unsupported options,
stale topology and execution limits are also covered.

Development runs also compared the M3 cutter to the maintained Build123d adapter:
both in-memory volumes were approximately **82.6554057246 mm³** (difference under
1e-9 mm³). STEP re-import introduced about 1.14e-5 mm³ of volume drift; both
directional boolean differences were empty at the kernel's tolerance. This is
local geometric evidence, not cross-kernel Onshape conformance.

The default plate is 80 × 50 × 6 mm, with four radius-4 mm through holes. Its
analytic and computed volume is **22,793.628421 mm³**. Generated artifacts and
reports go under ignored `output/`; source and regression tests are maintained.
