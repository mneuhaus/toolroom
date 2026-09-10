# Scope and maturity

This is a working local edition for discussion and practical use. It combines ten skill entrypoints, shared technical references, profiles, selected executable helpers and project case studies.

## Included in the repository

- The eight existing CAD skill collections, organised into concise entrypoints and technical references, plus workflow and joints entrypoints.
- A consolidated mesh/STEP screening workflow with tests from both source projects.
- An independently testable resolver for profile inheritance and ordered includes.
- Existing design-language and manufacturing profiles, clearly identified project examples, and rendering/layout data.
- Actual project images with source hashes, detailed examples and knowledge articles.
- A fully local website with search, profile comparison, before/after views and discussion notes.

## Separately installed runtimes

| System | Purpose | Status in this framework edition |
| --- | --- | --- |
| Build123d / cad-khana | Local modelling and assembly diagnostics | Skill knowledge consolidated; the cad-khana library remains an external dependency |
| Onshape + Electron/Jarvis | Native construction and document access | Printed Joints Lab newly built: eight variants, 16 native Part Studios, a frozen version and geometry checks |
| Fusion + fusion-khana | Execute source programs in native CAD | Adapter documented; no native Fusion run in this edition |
| OrcaSlicer / Bambu Studio | Actual manufacturing toolpaths | Rules and profile resolver available; no new machine slice in this edition |
| Blender / PDF tools | CAD illustrations and page layout | Existing project pipeline documented; no universal renderer claimed |
| Scan-Toolkit / STL2STEP | Reconstruction | Methods and sources available; runtime integration remains open |
| FreeCAD / Gmsh / CalculiX | Structural simulation | Documented studies; no general FEM adapter |
| MuJoCo | Bristlebot motion model | Experimental project example |

## Interpreting the examples

The [Printed Joints Lab](../examples/printed-joints/README.md) is a new native experiment with its own validation report. Images and historical measurements from imported projects belong to their stated revision and original inspection scope. The website does not trigger a fresh check of cloud geometry. Physical validation remains separate.

FDM has the broadest project evidence. Laser cutting has a concrete export example. CNC and SLA are identified as reference or experimental areas. Generic profile values are not measured machine capabilities.
