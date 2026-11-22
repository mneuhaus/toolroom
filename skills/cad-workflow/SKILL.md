---
name: cad-workflow
description: Coordinate CAD work spanning stages or backends, or review a CAD workflow. Use a specialist skill directly for an isolated task.
---

# CAD workflow

Establish the requested deliverable, authoritative source and protected interfaces. Preserve the user's chosen mechanism and scope; added complexity needs a concrete functional reason. Define completion for this task, such as a checked native revision and a usable test-print package, with remaining physical tests stated separately.

Load only the branch needed now. A link is a route, not an instruction to read every document.

SolidCraft is the CAD backend for new work since 22 November 2026. Its own skills (`solidcraft-modeling`,
`solidcraft-editing`, `solidcraft-checking`, `solidcraft-mechanisms`) ship with SolidCraft and are installed beside
this repository, not in it. The sorting machine continues in Onshape; Build123d and Fusion are for existing projects
only.

| Task | Guidance |
| --- | --- |
| New part or a change, in SolidCraft | The installed skills `solidcraft-modeling` and `solidcraft-editing`, with the [house reference](../../toolbox/solidcraft/README.md) for print hand-off, screw joints and scans |
| A look at a design before printing | [check](../../toolbox/check/README.md): hints on thin spots, tiny gaps and overlaps |
| Build plate and slicing | [toolbox](../../toolbox/README.md) |
| Sorting machine: native Onshape design or revision | [onshape-cad](../onshape-cad/SKILL.md) |
| Sorting machine: session-backed Onshape transport | [onshape-bridge](../onshape-bridge/SKILL.md) |
| Existing Build123d project | [cad-khana](../cad-khana/SKILL.md) |
| Existing Fusion project | [fusion360](../fusion360/SKILL.md) |
| FDM design or print preparation | [cad-fdm-design](../cad-fdm-design/SKILL.md) |
| Joint geometry, fit or retention | [cad-joints](../cad-joints/SKILL.md) |
| Fastenings or changes to their assembly/service access | [Required assembly review](../../knowledge/construction/assembly-review.md#review-before-delivery) |
| Product-family design language | [cad-design-system](../cad-design-system/SKILL.md) |
| Illustrated assembly manual | [onshape-build-manuals](../onshape-build-manuals/SKILL.md) |
| Scan-derived replacement | [scan-reverse-engineering](../scan-reverse-engineering/SKILL.md) |
| Physics simulation | [cad-physics-simulation](../cad-physics-simulation/SKILL.md) |

Use [verification](../../knowledge/foundations/verification.md) to define the evidence needed for the deliverable and reuse valid checks. The lead carries authorized work through that evidence and delivery; internal review milestones do not create new user-approval requirements. Physical printing or publication requires its own existing authorization.

For delegation, use [bounded worker scopes and delivery ownership](../../knowledge/workflow/delegation.md), the [team profile](../../profiles/agents/cad-team.yaml) and [worker-job helper](references/worker-jobs.md). Routine workers receive concrete execution inputs; Astra retains critical decisions without inheriting a prescribed script for every design choice.

Reusable tools: [source extraction](references/source-extraction.md) for focused source evidence; [print packages](../cad-fdm-design/references/print-package.md) for frozen posed 3MFs. Environment endpoints and defaults live in the [workstation profile](../../profiles/environment/local-workstation.yaml). Use [project layout](../../knowledge/workflow/project-layout.md) when organizing persistent sources and evidence.
