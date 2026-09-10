---
name: fusion360
description: "Construct or revise Fusion designs using the existing fusion-khana source-program workflow, explicit volume balances and native assembly checks. Requires a configured running Fusion application; generic STL review does not require this skill."
---

# Fusion / fusion-khana

**Use when** a Fusion design is built or revised through the maintained source-program workflow: rebuilding a document from its part program, asserting volume balances, and running native assembly and motion checks against a running Fusion application. **Do not use when** the task is generic STL review, slicing or structural mesh work — those tools are independent of Fusion.

## Procedure

1. Confirm that the source-authority model applies before clearing an existing document. A natively edited document must not be overwritten by an older generator.
2. Identify the intended document and the affected components. Preserve source parameters, imported hardware and the user's constraints.
3. Rebuild from the part program, then verify with geometric identities, real component bounds and the relevant motion checks. The application's raw units and the wrapper's millimetres are distinct.
4. A failed build keeps its actual exception and is never saved as an accepted result.
5. A screenshot of whichever document happens to be active cannot establish the intended document's state. Account for modal dialogs and the shared single-threaded application.

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [What a check actually establishes](../../knowledge/foundations/verification.md)
- [Assembly, access and load-path review](../../knowledge/construction/assembly-review.md) — for tight mechanisms.
- [OrcaSlicer / Bambu Studio preparation and review](../../knowledge/manufacturing/print-preparation.md) — before print release.
- [cad-fdm-design](../cad-fdm-design/SKILL.md) for printed parts.

## References

- [Field notes](references/field-notes.md) — library operations, volume assertions, module reload behaviour, coordinate conversion and shared-application pitfalls. The absolute paths and machine examples in them are historical setup references.

## Environment

MCP endpoint and library location for this machine: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml). The Fusion runtime is separately installed and was not started to prepare this documentation; see [scope](../../docs/scope.md).
