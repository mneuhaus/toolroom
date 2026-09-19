# Offline verification of native CAD parts

`pruefstand` is a pytest-based checker that works on STEP exports and a per-revision
machine manifest (`machine.json`: bodies, frames, translation and rotation motions,
which motion moves which body). Tests never call the CAD service; that keeps the daily
API budget for building and makes a check repeatable from a file on disk. The tool lives in
[`pruefstand/`](../../pruefstand/README.md) with its [specification](../../pruefstand/SPEC.md)
and [documentation](../../pruefstand/docs/README.md).

## What has earned its place

Three checks have found real defects before printing and are worth running on every new
part that mates with a machine:

- **`access(screw, scene)`** sweeps a driver envelope (bit, shaft, grip) from outside to the
  screw head through all context bodies. Found that four hub screws on a modular tray were
  unreachable with the standard 192 mm driver (the trough offers 180 mm), which would have
  surfaced only during assembly of printed parts.
- **`overlap` / `gap` across poses** — exact BRep intersections and mesh distances with the
  machine posed at stroke and swing positions. Found a 3.29 mm³ sliver of a hook strip cutting
  into a trough wall and measured a full −135…+45° swing as collision-free instead of assuming it.
- **`absatz`** (contour steps): pairs of parallel convex/concave edges 0.3–3 mm apart with a
  narrow face between them, the signature of blocks unioned instead of one drawn contour. It
  reproduces what a designer flags by eye on a side plate and found the same class of defect
  on a floor plate.

Everything else (`same_as`, `Interface`, `kerbe`, `unverrundet`, `splitter`, `sweep`,
`print_pose`, `stability`, `relevance`) runs and is documented, but has not yet caught a defect
that a look at the model would not have; treat it as experimental and do not extend it until it
does. Style-rule counts without a declared print pose are upper bounds, and the tool says so.

## Rules that the tool enforces on itself

- **"Nothing measured" is never a pass.** An empty measurement window turns the test red;
  results carry `nichts_gemessen`, `unentschieden` (requirement mapped to no geometry) and
  `technischer_fehler` as distinct outcomes. A silently green misplaced window is the most
  dangerous state a checker can have.
- **Never loosen a tolerance to make a test green.** Report the measured value and mark the
  test `xfail(strict=True)` with the value in its reason.
- **A window can measure itself.** A cylinder r 4.5 placed over a Ø10.5 collar reported 4.41 mm
  instead of the pin's 3.95; a box over a seating plane reported the seat as a gap. Suspect the
  window first, then the geometry; every result records whether its window cut material.
- **A judgement says what it rests on.** `urteil_auf` is `brep` or `mesh`; an exactly computed
  side value does not make a sampled judgement exact. Mesh collision proofs prove things about
  the mesh only.
- `fcl`'s penetration depth is meaningless for flush contact (two flush cubes report the full
  body depth); intersection volume is the only trustworthy overlap measure.

## Limits

Measuring is not designing. The tool confirms or refutes an intended geometry; it does not
produce a revision, and a run that changes nothing is not progress. Intent files
(`schrauben.yaml`, `schnittstellen.yaml`, `montage.yaml`) are worth writing before the geometry,
so the check has something to hold the part against.

Origin: Single Step feeder R6d, modular tray and hopper floor R1, September 2026.
