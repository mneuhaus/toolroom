---
name: cad-fdm-design
description: Design FDM parts or prepare and inspect print files, preserving mating interfaces and the intended print orientation.
---

# FDM design and preparation

Design for the intended print pose, or prepare a usable package for the selected geometry, printer and material. Keep fastening choices and permitted geometry changes separate from material confirmation. For connection design, use [cad-joints](../cad-joints/SKILL.md); an unchanged export does not require redesigning its joint.

| Task | Load when needed |
| --- | --- |
| Choosing or changing a bed face | [Print orientation](../../knowledge/manufacturing/print-orientation.md): layer strength, protrusions and support access |
| Exporting, arranging or slicing parts | [Print preparation](../../knowledge/manufacturing/print-preparation.md): source units, transforms, native profiles and actual deposited layers |
| Slicing or inspecting an already posed 3MF | [Print-package helper](references/print-package.md): frozen inputs, native slice/reimport and cached evidence |
| Resolving missing/inherited presets | [Profile resolver](scripts/resolve_profiles.py) and [FDM profiles](../../knowledge/manufacturing/fdm.md) |
| A part mates with a machine or is screwed in place | [Offline verification](../../knowledge/workflow/offline-verification.md): `access`, posed `overlap`/`gap` and `absatz` from `pruefstand` on the STEP before slicing |
| A mesh or STEP concern | [Mesh screening](../cad-design-system/scripts/check_mesh.py) or [STEP screening](../cad-design-system/scripts/check_step.py) |
| A local CAD-library issue | [Field notes](references/field-notes.md) |

Preserve protected seating faces and load paths. Reuse approved source rotations and Z phase when repacking existing parts; choose a new pose only when the task requires it. Record supported elevation explicitly rather than automatically lowering every component to the bed.

Judge the exact final 3MF and its actual deposition: effective poses, bed fit, printer/nozzle/material, native machine routines, functional layers and support removal. A dropdown or support flag alone is insufficient. Use [verification](../../knowledge/foundations/verification.md) to reuse unchanged evidence and inspect the effects of the change.

For print-file tasks, completion means the verified file is available with its printer/material, estimated time/mass and any necessary assembly or cleaning notes. Physical fit, load tests and printer dispatch remain separate events. The [workstation profile](../../profiles/environment/local-workstation.yaml) holds local defaults; project confirmations take precedence.
