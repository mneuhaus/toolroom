---
name: cad-fdm-design
description: "Design or revise FDM parts in the selected CAD backend: choose the print pose, preserve mating interfaces, assess assembly access and fits, and inspect actual slicer output. Also use for preparing or comparing print files."
---

# FDM design and preparation

Read [Shared project and evidence conventions](../../knowledge/core.md). Use the user's selected CAD backend and actual machine/material configuration. Material, fastening method, part count and permitted mating-part changes are separate constraints.

Choose the bed face before detailing. Preserve functional seating faces, load paths and motion. For tight assemblies, read [assembly review](../../knowledge/assembly-review.md). For selecting or constructing mating joint geometry, use [cad-joints](../cad-joints/SKILL.md). For snaps, preload or slide-in retention, read [fits and retention](../../knowledge/fits-and-retention.md). For profile resolution, print files and actual extrusion evidence, read [print preparation](../../knowledge/print-preparation.md).

Keep nominal design values, calibrated process measurements and historical example dimensions distinct. Use the project's manufacturing and design-language profiles. The [workshop-042 style](../../profiles/design-language/workshop-042.yaml) is an optional preference, not a process rule.

[Construction field notes](references/source-guide.md) contain local Build123d/OCC pitfalls, connection recipes and historical prototype dimensions. Apply only the relevant pattern and confirm it against the current material, orientation and interfaces. [Project layout](../../knowledge/project-layout.md) applies to longer work.

## Available local helpers

- [Profile resolver](scripts/resolve_profiles.py): resolve `inherits` and ordered `include` dependencies, detect missing/cyclic inputs, retain child overrides.
- [Geometry screening](../cad-design-system/scripts/check_mesh.py): sampled mesh checks with explicit findings and incomplete status.
- [Geometric STEP screening](../cad-design-system/scripts/check_step.py): native solids and explicit inlay handling.

The profile resolver produces data for review; it is not a machine-specific G-code generator or a replacement for slicer compatibility handling. Keep actual machine identity and start/end routines under the slicer's control. Verify the exact final 3MF and its deposited layers.

Record printing, physical assembly and load testing separately from file preparation. Commands here do not dispatch physical jobs.
