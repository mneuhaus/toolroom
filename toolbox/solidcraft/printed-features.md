# Printed features in SolidCraft

SolidCraft has ready-made commands for holes, fasteners, bosses, lips, snap hooks, threads and cell fields. A command
that builds is not a print-tested joint. This file says where the command is the house way, and where our own
standard wins. Design rules themselves are in the `cad-fdm-design` skill and in
[knowledge/construction](../../knowledge/construction/printed-screw-joints.md).

## M3 screw joints

| Part of the joint | Use | State |
| --- | --- | --- |
| Receiving hole in the printed part | [`m3_hybrid_hole.py`](m3_hybrid_hole.py): `hybrid_hole(name, body, origin, axis)` cuts the profile of the interface file to its depth, with the 45 degree entry relief | **Run:** from above, from below and from the side; the block equals the one cut with the build123d adapter of the same profile, export closed |
| Clearance hole in the parts before it | `solid.hole` with `clearance: "M3"`, `fit: "normal"` | **Run:** 3.4 mm, the clearance diameter the interface profile names |
| Recess for a socket head | add `head: "ISO 4762"` to that hole | **Run:** counterbore 6.5 mm wide and 3.5 mm deep (head plus 0.5 mm all round) |
| Recess that opens toward the bed | add `bridge: "0.2 mm"` (one layer height) | **Run:** two bridge layers above the recess, a slot then a square, 178.09 mm3 removed in total. Not printed from SolidCraft yet |
| The screw as a body for collision checks | `parts.insert` with family, size and length, `at` a point on the hole's wall | **Run:** an M3 x 10 cap screw seats in the recess with a joint, no overlap with the plate |

- **The hybrid hole stays the default receiving hole.** `solid.hole` with `thread: "M3"` cuts a tapped metric hole
  (**run:** it builds, with `modeled: true` as a real thread). That is a different joint and needs the user's
  explicit choice, like any exception to the standard.
- **A recess needs material under it, and SolidCraft does not say so.** A recess for an M3 head in a 2 mm floor is
  cut without a warning as a plain 6.5 mm through hole: no seat is left and the head falls through (**run**). Only
  with `bridge` is it refused, with the reason (**run**). Compare the wall with the recess depth of 3.5 mm before
  placing one; thicken the floor locally or use a boss.
- **`parts.insert` names the screw's body `Body1`** inside the new component. Name the component, and pass the body
  to `inspect.clearance` as `against`, with the part in `bodies`: with only one side given, no pair is checked
  (**run**).

## Bosses, lips and snap hooks

- **`plastic.boss`** stands a boss with optional ribs and a round hole on a face. **Run:** on the floor of a shelled
  tray, with four ribs and a root fillet. Give it the `fillet`; the house rule asks for a base fillet on every thin
  upright feature. For a screw boss leave its own hole out and cut the hybrid hole with the helper; the boss then
  needs at least 2.1 mm of profile radius plus the wall around it. That combination is **not run**.
- **`plastic.lip`** runs a lip or a groove along the rim of a shelled body. **Run:** a lip 1 mm wide and 1.5 mm high
  on the inside of the rim. The matching `type: "groove"` with its `gap` on the lid is **not run**; take the gap from
  the fit rules, not from the command's default.
- **`plastic.snap_fit`** builds a cantilever hook. **Run:** it builds, with a sharp root. The doctrine does not
  change: a slide-in beats a snap for a box and its tray, a snap is only chosen when the task asks for one, its
  length and deflection come from the fit and snap review, and the root gets a fillet afterwards.
- **`plastic.rest`** and the plastic rules (`plastic.manage_rules`, `plastic.assign_rule`: default wall, draft and
  clearance per body) are **not run**. The rules are made for injection moulding; our numbers come from the
  manufacturing profile.

## Threads

- **Printed adjusting screws keep the house pairing: Tr12x3 in the nut, Tr11x3 on the screw.** `solid.thread` with
  `form: "trapezoidal"`, the `designation` written out and `modeled: true`. **Run:** the nut thread in a 9 mm bore
  and the screw thread on an 11 mm shaft both build and export closed. Always give the form and the designation;
  what the command chooses on its own for a face was **not run**.
- The command gives no teardrop and no apex relief. The rule for horizontal threaded bores stays a modelling step of
  its own.
- Not printed from SolidCraft yet. The first print of a new thread pair is the test.

## Cell fields

- **`solid.cell_grid`** cuts a honeycomb or another cell pattern into the profile of a sketch; a loop inside the
  profile is kept clear. **Run:** hexagons of 8 mm with 1.6 mm webs through a 2 mm panel, export closed.
- **One lattice per part:** pass the part's centre as `anchor`. Fields with the same anchor, size and web line up,
  which is the house rule against re-centring each row or each field.
- **`clip: "whole"` with a `margin`** keeps only complete cells and a guaranteed rim. The default clips cells along
  the grid, which leaves part cells at the edge.
- One call cuts at most 1000 cells (250 before 0.46).

## Examples

[`tray-boss-lip.json`](examples/tray-boss-lip.json), [`screw-holes.json`](examples/screw-holes.json),
[`recess-too-deep.json`](examples/recess-too-deep.json),
[`refused-bridged-recess.json`](examples/refused-bridged-recess.json) (has to fail),
[`fastener.json`](examples/fastener.json), [`snap-fit.json`](examples/snap-fit.json),
[`trapezoid-threads.json`](examples/trapezoid-threads.json), [`honeycomb.json`](examples/honeycomb.json).
