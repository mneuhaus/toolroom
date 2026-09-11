---
name: cad-fdm-design
description: "Design or revise FDM parts in the selected CAD backend: choose the print pose, preserve mating interfaces, assess assembly access and fits, and inspect actual slicer output. Also use for preparing or comparing print files."
---

# FDM design and preparation

**Use when** a part is designed or revised for FDM printing in any backend: choosing the print pose, preserving mating interfaces, judging assembly access and fits, preparing or comparing print files and inspecting actual slicer output. **Do not use when** the connection geometry itself is the question — start at [cad-joints](../cad-joints/SKILL.md) — or when nothing will be printed.

## Procedure

1. Establish the constraints separately: material, fastening method, part count and which mating parts may change. An answer such as "PLA" confirms the material only; it does not select a fastening scheme.
2. Choose the bed face before detailing — see [print orientation](../../knowledge/manufacturing/print-orientation.md) for how that choice sets strength, support and surface quality. "Vertical" is defined relative to it, and nothing may protrude below it.
3. Preserve functional seating faces, load paths and motion. Keep design-language detailing off protected mating faces.
4. Check access and the full assembly path, not just the final pose. For snaps, preload and slide-in retention, separate rigid location from elastic retention.
5. Resolve the manufacturing profile explicitly and keep nominal design values, calibrated process measurements and historical example dimensions distinct.
6. Verify the exact final 3MF and its deposited layers — printer, nozzle, filament, plate, real machine start/end G-code, estimates and preview — not the UI dropdown. Machine identity and start/end routines stay under the slicer's control.
7. Record printing, physical assembly and load testing separately from file preparation. Nothing here dispatches a physical job.

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [FDM profile guidance](../../knowledge/manufacturing/fdm.md)
- [Print orientation for FDM parts](../../knowledge/manufacturing/print-orientation.md) — anisotropy, angled poses, support release, splitting instead of tilting.
- [OrcaSlicer / Bambu Studio preparation and review](../../knowledge/manufacturing/print-preparation.md)
- [Assembly, access and load-path review](../../knowledge/construction/assembly-review.md)
- [Slide-in fit, preload and one-piece latches](../../knowledge/construction/fits-and-retention.md)
- [CAD project files and revisions](../../knowledge/workflow/project-layout.md) — for longer work.

## References

- [Print-package helper](references/print-package.md) — inspect existing 3MFs or run a frozen posed-source job through native slicing, reimport and source/profile checks. Actual-layer and critical engineering review remain separate.

- [Field notes](references/field-notes.md) — local Build123d/OCC pitfalls, connection recipes, house-style edge treatment and historical prototype dimensions. Apply one relevant pattern at a time and confirm it against the current material, orientation and interfaces.
- [Profile resolver](scripts/resolve_profiles.py) — resolves `inherits` and ordered `include` dependencies, detects missing and cyclic inputs, keeps child overrides. It produces data for review; it is not a G-code generator.
- [Geometry screening](../cad-design-system/scripts/check_mesh.py) and [STEP screening](../cad-design-system/scripts/check_step.py) — sampled checks with explicit findings and an incomplete status.
- [Project scaffold](references/pyproject.toml) and [rebuild watcher](references/watch.py) for a build123d project.

## Environment

Default printer, slicers and the manufacturing and design-language profiles this machine assumes: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml). The [workshop-042 style](../../profiles/design-language/workshop-042.yaml) is a preference, not a process rule.
