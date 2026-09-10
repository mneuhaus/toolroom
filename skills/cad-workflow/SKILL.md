---
name: cad-workflow
description: "Coordinate multi-stage CAD work: establish the authoritative design, select the required CAD, manufacturing or documentation skills, and retain revision-bound evidence. Use for a new CAD project, cross-tool work or an explicit workflow review; a small isolated edit does not need a full lifecycle."
---

# CAD workflow

Start with the requested outcome and the current project. Read [Shared project and evidence conventions](../../knowledge/core.md) when source identity, units, revision handling or evidence is relevant. Preserve the user's selected backend, established interfaces and existing authorization.

## Select the necessary work

| Work | Skill | Shared reference |
| --- | --- | --- |
| Native Onshape design or revision | [onshape-cad](../onshape-cad/SKILL.md) | [Assembly](../../knowledge/assembly-review.md) |
| Session-backed Onshape transport | [onshape-bridge](../onshape-bridge/SKILL.md) | [Evidence](../../knowledge/verification.md) |
| Local Build123d design | [cad-khana](../cad-khana/SKILL.md) | [Patterns](../../knowledge/construction-patterns.md) |
| Fusion source-program workflow | [fusion360](../fusion360/SKILL.md) | [Assembly](../../knowledge/assembly-review.md) |
| Printed parts and slicer preparation | [cad-fdm-design](../cad-fdm-design/SKILL.md) | [Print preparation](../../knowledge/print-preparation.md) |
| A coherent product design language | [cad-design-system](../cad-design-system/SKILL.md) | Project profiles |
| Illustrated CAD assembly manual | [onshape-build-manuals](../onshape-build-manuals/SKILL.md) | [Evidence](../../knowledge/verification.md) |
| Scan-derived replacement geometry | [scan-reverse-engineering](../scan-reverse-engineering/SKILL.md) | [Recipes](../../knowledge/recipes.md) |

Read only the applicable branches. A manual layout change needs no CAD rebuild. A process profile cannot authorize a new machine job or cloud publication.

## Establish a reviewable result

Identify source authority, affected parts, protected interfaces and output before selecting tools. Reuse the project's native CAD when it includes user edits absent from generators. State unmeasured quantities explicitly. Use relevant native, assembly, toolpath or physical evidence; preserve incomplete results.

For a longer project, use [project layout](../../knowledge/project-layout.md). A small prototype needs only the files it actually uses.

This framework supplies skills, shared references and selected offline helpers. Cloud adapters and full CAD runtimes remain separately installed; see [scope](../../docs/scope.md).
