# Frozen R10b regression

This case executes the unmodified 402,921-byte FeatureScript snapshot captured
from `step-feeder/single-step-r10/jobs/r10b/r10b.fs` on 21 September 2026.
The original project file may change independently.

- Source SHA-256: `662e09ef212e163dadd691358fa8b89cc60f52b951767c92ae57f7cf09fd6ecd`
- Entrypoint: `singleStepR10b`
- Parameters: [parameters.json](parameters.json), including K15 and the nominal tray cavity.
- Dependencies: [imports.json](imports.json), pinned to the eight original tab IDs
  and document microversion `e0aa7b219e284b36c72c543e`.

From the fsocct directory:

```sh
uv sync --locked
uv run python cases/r10b/verify.py
```

The runner checks the source hash, evaluates all nine construction sections,
requires the 38 expected named solids, validates every body, exports STEP and
reimports it. It rejects caught native solid-operation failures, then checks
the solid count, every solid's volume, overall bounds and
OpenCascade validity after export. Runtime progress is written to
`output/r10b.trace.log`; final artifacts are `output/r10b.step`, `output/r10b.json`
and `output/r10b-verification.json`. The verification records interpreter source
hashes. Evaluation uses a five-million-AST-step budget; the nominal case requires
2,476,944 steps.

The initial successful run produced 38 valid solids from 1,920 operations, with
a total volume of 2,939,235.462299 mm³. STEP reimport preserved all 38 valid solids
and changed the total volume by approximately -0.004816 mm³. These are local
OpenCascade regression measurements, not proof of equality to Parasolid or
physical manufacturing acceptance.

The [latest recorded verification](verification.json), after the workspace
compatibility extensions, again passes all 38 named solids and 1,920 operations
without caught operation failures. The run took 161.756 seconds. Its total
in-memory volume differs from the initial baseline by only -0.000022707 mm³;
all individual body volumes and bounds remain within the regression tolerances.
STEP reimport preserves 38 valid solids, with total volume drift -0.004663 mm³.
These timings are observations, not a controlled benchmark.

## Imported geometry

The eight imported Part Studios are frozen as named B-rep contexts. Their original
feature histories are **not** replayed by this case. STEP exports were acquired
through the existing signed-in session bridge with document storage disabled.
Each imported element's microversion matched the element at the requested
document microversion and remained unchanged before and after export. The
`dependencies/*-export-source.json` records retain that provenance and each STEP
hash; manifests retain each B-rep hash. Runtime evaluation needs no network.

To reproduce an individual construction section or change supported parameters:

```sh
uv run fsocct run cases/r10b/r10b.fs \
  --feature r10bUpperCore --imports cases/r10b/imports.json \
  --step output/r10b-upper.step --report output/r10b-upper.json

uv run fsocct run cases/r10b/r10b.fs \
  --feature singleStepR10b --imports cases/r10b/imports.json \
  --max-steps 5000000 \
  --param 'edgeAngle=R10bEdgeAngle.K15' --param 'overrideNose=false' \
  --param 'noseLength=0*millimeter' --param 'catchPitch=4*millimeter' \
  --param 'catchHeight=0.5*millimeter' --param 'innerWallThickness=3.2*millimeter' \
  --step output/r10b.step --report output/r10b.json
```

Add `--verbose` for per-operation progress. Other parameter combinations are not
covered by the nominal-case result above.
