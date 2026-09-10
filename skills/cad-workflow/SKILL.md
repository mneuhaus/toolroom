---
name: cad-workflow
description: "Coordinate multi-stage CAD work: establish the authoritative design, select the required CAD, manufacturing or documentation skills, and retain revision-bound evidence. Use for a new CAD project, cross-tool work or an explicit workflow review; a small isolated edit does not need a full lifecycle."
---

# CAD workflow

**Use when** a CAD job spans several stages or tools: a new project, work that crosses backends, or an explicit review of how a project is organised and evidenced. **Do not use when** the task is one isolated edit, a layout change or a question answered by a single skill — read that skill directly.

## Procedure

1. State the requested outcome, the current project and its source authority before touching a tool. Preserve the user's selected backend, established interfaces and existing authorization.
2. Identify affected parts, protected interfaces and the actual output. Reuse the project's native CAD when it contains user edits a generator does not have.
3. Select only the applicable branches below. A manual layout change needs no CAD rebuild; a process profile cannot authorize a machine job or a cloud publication.
4. Keep source revisions, exports and checks together. State unmeasured quantities explicitly and preserve incomplete results rather than rounding them up to a pass.

| Work | Skill | Shared reference |
| --- | --- | --- |
| Native Onshape design or revision | [onshape-cad](../onshape-cad/SKILL.md) | [Assembly](../../knowledge/construction/assembly-review.md) |
| Session-backed Onshape transport | [onshape-bridge](../onshape-bridge/SKILL.md) | [Evidence](../../knowledge/foundations/verification.md) |
| Local Build123d design | [cad-khana](../cad-khana/SKILL.md) | [Patterns](../../knowledge/construction/patterns.md) |
| Fusion source-program workflow | [fusion360](../fusion360/SKILL.md) | [Assembly](../../knowledge/construction/assembly-review.md) |
| Printed parts and slicer preparation | [cad-fdm-design](../cad-fdm-design/SKILL.md) | [Print preparation](../../knowledge/manufacturing/print-preparation.md) |
| Mechanical connections between parts | [cad-joints](../cad-joints/SKILL.md) | [Joints](../../knowledge/construction/joints.md) |
| A coherent product design language | [cad-design-system](../cad-design-system/SKILL.md) | [Profiles](../../profiles/README.md) |
| Illustrated CAD assembly manual | [onshape-build-manuals](../onshape-build-manuals/SKILL.md) | [Evidence](../../knowledge/foundations/verification.md) |
| Scan-derived replacement geometry | [scan-reverse-engineering](../scan-reverse-engineering/SKILL.md) | [Recipes](../../knowledge/workflow/recipes.md) |

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md) — source identity, units, revisions, evidence.
- [What a check actually establishes](../../knowledge/foundations/verification.md) — before calling a result a pass.
- [CAD project files and revisions](../../knowledge/workflow/project-layout.md) — for a longer project; a small prototype needs only the files it uses.
- [Combining tasks](../../knowledge/workflow/recipes.md) — worked multi-skill sequences.
- [Lessons from projects](../../knowledge/lessons/project-lessons.md) — what went wrong before.

## Environment

Endpoints, installed runtimes and this machine's default profiles are in [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml). Cloud adapters and full CAD runtimes stay separately installed; see [scope](../../docs/scope.md).
