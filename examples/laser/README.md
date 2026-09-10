# File trolley: flat parts with a spatial function

The extension consists of plates designed for laser cutting. The assembly defines their spatial relationships; the exporter places the flat parts in XY and arranges them on sheets.

## Nominal geometry and cutting paths

The existing exporter already compensates for kerf in the output contours: outer contours grow and internal cutouts become smaller accordingly. Additional CAM compensation would apply the same correction twice.

The design system's generic laser profile instead assigns compensation to CAM. Either approach can describe a defined process; the chosen workflow must assign ownership unambiguously.

## What the framework takes from it

The case study separates nominal geometry, material thickness, manufacturing contours and sheet layout. The technical image shows the actual CAD model. This documented workflow includes no new laser operation or measurement of a manufactured specimen.

## Transferable rule

Compensation is a process step with one clear owner. The same principle applies to hole allowances, scaling and other manufacturing corrections.

Continue: [Profiles](../../profiles/README.md) · [Task recipes](../../knowledge/recipes.md)
