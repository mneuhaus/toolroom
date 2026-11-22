# check: hints before printing

A small helper that looks at a SolidCraft design and points at places that often go wrong in a print. It gives
hints, each with a place and a number. It is not a rule book: nothing passes or fails, nothing is blocked, and there
are no exceptions to manage. A hint can be perfectly fine (looks only, a designed flexure, a deliberate press fit);
whoever designs the part decides.

```sh
toolbox/check/check design.sc                      # every body not named like a reference part
toolbox/check/check design.sc --printed "Base,Lid"
```

It opens the design read-only and headless, so it does not touch the design open in the app. A single part takes a
few seconds; a design that rebuilds in 12 s took 41 s.

## What it points at

| Hint | Meaning | Measured how |
| --- | --- | --- |
| `thin` | Less material than two print lines at that place: likely weak, or a feather edge | From points all over the surface straight through the material to the opposite face |
| `gap` | A slot inside a body, or the distance between two printed bodies, too narrow to stay open | Surface points straight out to the next face of the same body; SolidCraft's distance between bodies |
| `overlap` | A printed body shares volume with another body | SolidCraft's interference check |
| `bed` | A printed body is larger than the printer's build volume | The mesh laid on its print face |
| `mesh` | A body is not closed, its mesh export has open edges, or SolidCraft cannot export it | The fine-quality export |
| `print face` | A printed body has no print face; only a reminder | The export reply |

The numbers (two print lines 0.84 mm, a printable gap about 0.5 mm, a tight fit 0.15 mm, build volume) come from
[the A1 profile](../../profiles/manufacturing/fdm-bambu-a1-0.4.yaml), which is itself marked as uncalibrated.

## What it leaves out, on purpose

- Walls at a planned three-line thickness are not listed, and neither is anything only just under the limit.
- Overlaps between two reference parts (a board and its header) are not listed.
- It knows nothing about screws, loads, overhangs or assembly order. For overhangs and supports the slicer is the
  judge ([mesh tools](../README.md)); for requirements stated per project there is [pruefstand](../../pruefstand/README.md).
- No silence means "fine": it only looks at the things in the table.

## How far it was tried (2026-11-22, SolidCraft 0.46.2)

- `selftest.sh` builds one design with a thin fin, a narrow slot, two overlapping bodies, two bodies 0.08 mm apart
  and a body too long for the bed, and one plain sound block. Every hint appears on the first, none on the second.
- On a lamp holder it found two real feather edges (0.03 mm where a lip ran into a curved cut) and then a mistake in
  the first fix. After the correction it has nothing to point at.
- On a three-body clip enclosure it gives ten hints. They were not checked one by one.

Grow it only when a printed part shows a miss that a simple measurement would have caught.
