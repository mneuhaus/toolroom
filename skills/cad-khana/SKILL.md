---
name: cad-khana
description: "Use the cad-khana Build123d wrapper for local parametrically generated parts, assembly assertions, geometric diagnostics, drawing and export. Apply when editing cad_khana scripts or interpreting its diagnostic output."
---

# Build123d / cad-khana

Read [Shared project and evidence conventions](../../knowledge/core.md). Keep pure part builders, named physical occurrences, explicit units and parameter-derived poses. The cad-khana runtime is a separate dependency; this repository bundles its current skill knowledge.

Read [API, diagnostics and worked patterns](references/source-guide.md) only for the operations being used. [Build123d reference](references/build123d_quickref.md) and [standard parts](references/standard_parts.md) provide backend details. Inspect the installed CLI before relying on historical commands.

The current library's assembly module is `cad_khana.mechanism.assembly`; mechanism checks are in `cad_khana.mechanism.check`. The older `core.assembly` README example is not the current import path.

```python
from cad_khana.mechanism.assembly import Assembly
from cad_khana.mechanism.check import check
```

Declare intended clearances and interferences against the actual parts. Use narrow, explained contact allowances; a waiver is not a fit test. Rebuild the final exported slicer files after geometry changes so output folders do not silently diverge.

Read [cad-fdm-design](../cad-fdm-design/SKILL.md) for manufacturing work. House-style values from old projects are optional profiles, not implicit library requirements. Native viewer topology selections refer to one pushed snapshot and must be resolved again after rebuilding.

The source notes include joint animation, GLB, drawing, orientation and diagnostic details. Use those capabilities as needed; do not invoke every check for a documentation-only change.
