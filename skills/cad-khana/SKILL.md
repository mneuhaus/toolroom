---
name: cad-khana
description: "Use the cad-khana Build123d wrapper for local parametrically generated parts, assembly assertions, geometric diagnostics, drawing and export. Apply when editing cad_khana scripts or interpreting its diagnostic output."
---

# Build123d / cad-khana

**Use when** writing or editing a script that imports `cad_khana`, running its assembly assertions and geometric diagnostics, or interpreting its JSON output, drawings and exports. **Do not use when** the design lives in a cloud backend — use [onshape-cad](../onshape-cad/SKILL.md) or [fusion360](../fusion360/SKILL.md) — or when a documentation-only change would trigger checks for nothing.

The cad-khana runtime is a separate dependency; this repository bundles its skill knowledge, not the library.

## Procedure

1. Keep pure part builders, named physical occurrences, explicit units and parameter-derived poses.
2. Inspect the installed CLI before relying on a historical command. The current assembly module is `cad_khana.mechanism.assembly` and mechanism checks are in `cad_khana.mechanism.check`; the older `core.assembly` README example is not the current import path.

   ```python
   from cad_khana.mechanism.assembly import Assembly
   from cad_khana.mechanism.check import check
   ```

3. Declare intended clearances and interferences against the actual parts. Keep contact allowances narrow and explained — a waiver is not a fit test.
4. After geometry changes, rebuild the exported slicer files as well. The checks only write diagnostics; export folders otherwise diverge silently.
5. Viewer topology selections refer to one pushed snapshot. After a rebuild, push again and resolve the indices again.

House-style values from older projects are optional profiles, not implicit library requirements.

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [What a check actually establishes](../../knowledge/foundations/verification.md)
- [Reusable construction patterns](../../knowledge/construction/patterns.md)
- [FDM profile guidance](../../knowledge/manufacturing/fdm.md) — for the numbers the printability checks compare against.
- [cad-fdm-design](../cad-fdm-design/SKILL.md) for print pose, material and slicer preparation.

## References

- [Field notes](references/field-notes.md) — API, diagnostics and worked patterns including joint animation, GLB, drawing and orientation. Read only the operations in use.
- [build123d quick reference](references/build123d_quickref.md) — the parts of the backend that are reliably misremembered.
- [Standard parts](references/standard_parts.md) — bd_warehouse fasteners and profiles.
- [Printability diagnostics](references/printability.md) — how wall thickness and overhangs are computed, and where the approximation breaks.
- [Install](references/install.md) — when `khana --version` fails.
- [Worked example: pin hinge](references/examples/pin_hinge/README.md)

## Environment

Library checkout and viewer port for this machine: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml).
