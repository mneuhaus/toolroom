# SolidCraft house reference

How this workspace uses SolidCraft for printed parts, on top of SolidCraft's own skills (`solidcraft-modeling`,
`-editing`, `-checking`, `-mechanisms`, `-sheetmetal`, `-reporting`). Those skills explain the commands. The files here
record the decisions that are ours: which command we use for which job, where our own standard wins, and what was
actually run.

| Read | When |
| --- | --- |
| [print-handoff.md](print-handoff.md) | A design is ready to print: print faces, export, plate, slice |
| [printed-features.md](printed-features.md) | Screw joints, bosses, lips, snap hooks, threads, honeycomb fields |
| [scan-to-cad.md](scan-to-cad.md) | A flatbed scan, a photo or a 3D scan is the starting point |

Every statement marked **run** was executed headless on SolidCraft 0.46.2 (build 0.46.2-nightly.20261122.155.1) on
2026-11-22 and is one of the 36 checks of [`examples/run-examples.sh`](examples/run-examples.sh). Statements marked
**not run** come from the command documentation only. Run the script after every SolidCraft update; a failure means
a statement here no longer holds:

```sh
toolbox/solidcraft/examples/run-examples.sh
```

Parameters change between releases (five of the twenty-two commands used here changed between 0.45.0 and 0.46.2), so
these files name the command and the decision and leave the parameter list to `describe_command` or
`solidcraft-cli commands`.

## Tools in this folder

| Tool | Does | Checked |
| --- | --- | --- |
| `sc-guard.sh` | Runs `solidcraft-cli` with a resident-memory limit (default 8 GB) and prints the peak and the time. | Used for every run of the examples |
| `sc_head.py` | Writes the first N commands of a script to a new file, to bisect a failing or heavy step. | Syntax only |
| `m3_hybrid_hole.py` | The [M3 hybrid hole](../../knowledge/construction/printed-screw-joints.md) as commands, from the interface profile, for any entry point and axis. | Demo run in three directions; the result equals the block cut with the build123d adapter of the same profile (no material in only one of them) |
| `examples/` | One minimal script per topic of the three files above, the generator of the scan test inputs, the runner and its two checkers. | 36 checks pass on 0.46.2 |

## Working rules

- **Headless for tests and parallel work.** `solidcraft-cli run script.json` builds in its own process. The MCP
  server without `--headless` attaches to the running app and works in the design the user has open.
- **`--param-check strict` on every script run.** It stops at a parameter the command does not take or takes in
  another form, which a plain run can accept silently.
- **`ok` proves nothing.** Compare the volume and the bounding box after each stage with the numbers worked out
  before, and check every mesh export for open edges
  ([`check_mesh.py`](../../skills/cad-design-system/scripts/check_mesh.py)).
- **Light runs need no guard, heavy ones do.** The examples peak below 400 MB. A design with many bodies or imported
  spline geometry runs under `sc-guard.sh`, one at a time.

## Earlier traps, re-tested on 0.46.2

The traps below were recorded on 0.27, before SolidCraft changed its geometry kernel. Three states are possible:
gone on the original design, not reproduced by a new probe (which does not prove it is gone everywhere), and not
re-tested.

| Trap on 0.27 | State on 0.46.2 | Evidence |
| --- | --- | --- |
| STL exports left small open edges near tangent features in every quality | Gone on the original design | The unchanged script of a three-body clip enclosure: two of the three STLs exported then are open, all six exported now (standard and fine) are closed |
| A relief cone whose circle lies exactly on the hole profile's arc made the cut fail, so it was drawn 0.01 wider | Gone on the original design | The same script with the 0.01 removed builds, and its exports are closed |
| A hole tool ending on the part face, a profile extruded "positive", and a true cone relief left zero-thickness sheets or open seams | Not reproduced by a new probe | `m3_hybrid_hole.py demo`: flush tool, exact cone, three directions, closed export. The lever it was first seen on was not rebuilt |
| Joining bodies along shared coplanar faces, or a cylinder with exactly the radius of a round end, gave "no result" | Not re-tested | |
| An edge fillet made before several cuts broke every later cut | Not re-tested | |
| About fifty engraved labels in one sketch cut ran longer than fifteen minutes | Not re-tested | |
| Interference over all bodies with several overlapping imported spline bodies ran past fifteen minutes | Not re-tested | |

The clip enclosure (276 commands, three printed bodies and their reference parts) builds in 12 s and 365 MB without
its checks. These re-tests on project designs were run by hand on 2026-11-22 and are not part of the runner.

If a mesh export does have open edges, mesh the STEP export instead with [`step2stl.py`](../mesh/step2stl.py), and
report the case upstream with the `solidcraft-reporting` skill. A STEP export is never laid on its print face, so that
mesh is as modelled and gets its orientation from `rotate` in the plate file. A project whose own instructions
prescribe the STEP route keeps it until its design has been re-tested.
