---
name: fusion360
description: "Construct or revise Fusion designs using the existing fusion-khana source-program workflow, explicit volume balances and native assembly checks. Requires a configured running Fusion application; generic STL review does not require this skill."
---

# Fusion / fusion-khana

Read [Shared project and evidence conventions](../../knowledge/core.md). The existing Fusion workflow rebuilds from a maintained part program. Confirm that this source-authority model applies before clearing an existing document; a natively edited document must not be overwritten by an older generator.

Read [Fusion API and source-program field notes](references/source-guide.md) for library operations, volume assertions, module reload behavior, coordinate conversion and shared-application pitfalls. The application's raw units and the wrapper's millimetres are distinct.

Before a rebuild, identify the intended document and affected components. Preserve source parameters, imported hardware and the user's constraints. A failed build must retain its actual exception and must not be saved as an accepted result.

Use geometric identities, real component bounds and relevant motion checks. A screenshot of whichever document is currently active cannot establish the intended document's state. Account for modal dialogs and the shared single-threaded application.

Use [assembly review](../../knowledge/assembly-review.md) for tight mechanisms and [cad-fdm-design](../cad-fdm-design/SKILL.md) for printing. Slicer and structural mesh tools are independent of Fusion.

The Fusion runtime is separately installed and was not started to prepare this documentation. Historical absolute paths and machine examples in the field notes are setup references. See [scope](../../docs/scope.md).
