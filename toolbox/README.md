# Toolbox

Working tools that are independent of the CAD backend: they take STL, 3MF, STEP, G-code or scans and were written
during earlier projects. They were collected here on 2026-11-22 so that they no longer live inside single projects
or inside the shelved kernel repository. SolidCraft is the CAD backend for new work; nothing here needs it, except
the folder `solidcraft/`.

"Checked" below means what was actually run on 2026-11-22 from this folder. A syntax check proves no behaviour.

## print/ : build plates and slicing for Bambu printers

| Tool | Does | Checked |
| --- | --- | --- |
| `plate-3mf.mjs` | Builds a 3MF build plate from STL parts: quarter-turn print orientation, drop to bed, placement, multi-colour pieces, per-object settings. Input is a plate JSON (format in the file header). | Run end to end on a four-part plate |
| `slice-a1.sh` | Turns that plate into a Bambu Studio project for the A1 (nozzle, process, filament, AMS colours, process overrides), slices it as a check and prints time and weight. Delivers the normal 3MF; `GCODE=1` also keeps the `.gcode.3mf`. | Run end to end (4 h 45 min, 174 g reported) |
| `slice-h3c.sh` | The same for a Bambu Lab H3C (330 x 320 bed). | Syntax only |
| `resolve-bambu-profile.mjs` | Flattens Bambu system profiles (`inherits`, include templates); the Bambu Studio CLI resolves neither. Used by the two slice scripts. | Through `slice-a1.sh` |
| `pack_plates.py` | Packs many parts onto A1 plates by their real outlines, with room for tree supports; writes plate JSONs for `plate-3mf.mjs`. | Syntax only |
| `slice_plates.sh` | Runs plate, slice and support check for every plate JSON of a directory. | Syntax only (paths changed on collection) |
| `support_check.py` | Counts the support actually deposited per part from the G-code. | Syntax only |
| `toolpath_layers.py`, `toolpath_layers_3colour.py` | Draw the first layers per filament from the G-code, to check that fine bed-side detail and colour changes print. | Syntax only |
| `tower_extent.py` | Measures the prime tower footprint and its distance to the parts from the G-code. | Syntax only |
| `bambu_native_profiles.py` | Resolves installed Bambu Studio presets from the user data folder (older helper from the Onshape period). | Syntax only |

The older package inspector [`print_package.py`](../skills/cad-fdm-design/scripts/print_package.py) checks an
existing multi-plate 3MF; the pipeline above is the one in use for deliveries.

`wonky-kernel/tmp/print` is a symlink to `print/`, because project scripts and READMEs written before the move call
the tools by that path.

## mesh/ : printability checks on exported meshes

SolidCraft has no overhang, wall-thickness or watertightness check, so these stay our own.

| Tool | Does | Checked |
| --- | --- | --- |
| `sliceability.py` | Slices STLs headless with OrcaSlicer and reports print time, weight, support volume, bridge spans and bed contact; `--compare` tries orientations. | Syntax only |
| `strengthcheck.py` | Cuts a part in print pose into layers and reports cross-section minima and bending resistance per layer (layer-adhesion weak spots). | Syntax only |
| `step2stl.py` | Meshes a STEP file with OpenCascade, as a fallback when a CAD export has open edges. | Run on one STEP of a block with a profiled hole: closed mesh, same volume |

A watertightness and STEP check lives in
[`skills/cad-design-system/scripts`](../skills/cad-design-system/scripts) (`check_mesh.py`, `check_step.py`).
Geometry checks against a machine context (gaps, overlaps, coverage) are in [`pruefstand`](../pruefstand/README.md).

## check/ : hints before printing

[`check/check design.sc`](check/README.md) opens a SolidCraft design and points at thin spots, tiny gaps, overlaps
and parts too big for the bed. Hints only: nothing passes or fails. Its `selftest.sh` shows each hint on a design
built to trigger it (run on SolidCraft 0.46.2, 2026-11-22).

## solidcraft/ : house reference and helpers for SolidCraft

The [house reference](solidcraft/README.md) says how this workspace uses SolidCraft for printed parts: print
hand-off, printed features, scan to CAD, and which of the earlier traps were re-tested. Its statements are checked
by `solidcraft/examples/run-examples.sh` (36 checks pass on SolidCraft 0.46.2, 2026-11-22); run it after every
SolidCraft update.

| Tool | Does | Checked |
| --- | --- | --- |
| `sc-guard.sh` | Runs `solidcraft-cli` and kills it above a resident-memory limit (default 8 GB), prints the peak. | Used for every run of the examples |
| `sc_head.py` | Writes the first N commands of a command script to another file, to bisect a failing or heavy step. | Syntax only |
| `m3_hybrid_hole.py` | The M3 hybrid hole as SolidCraft commands, read from the interface profile, for any entry point and axis. | Demo run in three directions; equals the build123d adapter's result as a solid |
| `examples/` | One minimal script per topic of the house reference, with a runner and a checker. | Run on 0.46.2 |

## scan/ : from flatbed scan to sketch

| Tool | Does | Checked |
| --- | --- | --- |
| `scan_kontur.py` | Traces a profile section from a flatbed scan with a ruler beside it and writes the outline as DXF in mm. | Syntax only; a DXF of the form it writes was imported into SolidCraft at exact size ([scan to CAD](solidcraft/scan-to-cad.md)) |

## Where the tools came from

| Tool | Origin | Original |
| --- | --- | --- |
| `print/plate-3mf.mjs`, `slice-a1.sh`, `slice-h3c.sh`, `resolve-bambu-profile.mjs` | `wonky-kernel/tmp/print/` (ignored by that repository's git) | Moved; symlink left behind |
| `print/pack_plates.py`, `slice_plates.sh`, `support_check.py` | `cad/step-feeder/steve-s1/tools/` | Copy; the project keeps its own |
| `print/toolpath_layers.py`, `tower_extent.py` | the `tools/` folder of a client project | Copy |
| `print/toolpath_layers_3colour.py` | `cad/futterspender/tools/toolpath_layers.py` | Copy |
| `print/bambu_native_profiles.py` | `cad/tools/` | Copy; sorter scripts import the original |
| `mesh/sliceability.py`, `strengthcheck.py` | `cad/fusion-khana/tools/` | Copy |
| `solidcraft/sc-guard.sh`, `sc_head.py` | `cad/ano-remote/tools/` (a second identical `sc-guard.sh` is in `cad/laubsauger-empfaenger/tools/`) | Copy |
| `scan/scan_kontur.py` | the `tools/` folder of a client project | Copy |
| `mesh/step2stl.py` | `cad/bristle-bot/solidcraft/scripts/` | Copy; the project keeps its own |
| `solidcraft/m3_hybrid_hole.py` | Written new on 2026-11-22; frame and rib phase follow `skills/onshape-cad/scripts/m3_hybrid_hole.py` | New |

Changes made on collection: neutral header comments, a neutral default title and application tag in the 3MF that
`plate-3mf.mjs` writes, and `slice_plates.sh` now finds its neighbours relative to itself and takes the plate glob
as an optional second argument. New projects call the tools from here instead of copying them again.
