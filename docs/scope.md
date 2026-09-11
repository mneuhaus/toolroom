# Scope and maturity

Toolroom is a local working edition for practical use and discussion. It combines a knowledge base in six sections, ten skill entrypoints with references, profiles, two reproducible labs and selected executable helpers.

## Included in the repository

- [Shared CAD work helpers](cad-work-basis.md): short source-bound worker jobs, bounded source snapshots/excerpts and native Bambu print-package inspection/preparation. Critical release remains outside their automated scope.

- The knowledge base: foundations, workflow, construction, manufacturing, design languages and lessons, each article listed in `knowledge/catalog.json`.
- Ten skill entrypoints consolidated from the previously installed skill collections, with their imported field notes kept as identified historical sources.
- A consolidated mesh and STEP screening workflow with regression tests from both source projects.
- An independently testable resolver for profile inheritance and ordered includes.
- Design-language, manufacturing, interface and workstation profiles. Generic profiles are explicitly uncalibrated.
- The Printed Joints Lab: eight native Onshape joint principles with STEP exports, a frozen version and geometry checks.
- The checker lab: four generated test geometries with the real reports of the mesh checker.
- A fully local website with search, a profile workbench and the lab views, plus a single-file reading edition builder.

## Separately installed runtimes

| System | Purpose | Status in this edition |
| --- | --- | --- |
| Build123d / cad-khana | Local modelling and assembly diagnostics | Skill knowledge consolidated; the library remains an external dependency |
| Onshape + session bridge | Native construction and document access | Printed Joints Lab built natively; the bridge and its adapter are external |
| Fusion + fusion-khana | Execute source programs in native CAD | Adapter documented; no native Fusion run in this edition |
| OrcaSlicer / Bambu Studio | Actual manufacturing toolpaths | Rules and profile resolver available; no new machine slice in this edition |
| Blender / PDF tools | CAD illustrations and page layout | Manual pipeline documented; no universal renderer claimed |
| Scan toolkit / STL2STEP | Reconstruction | Methods documented; runtime integration remains open |
| FreeCAD / Gmsh / CalculiX | Structural simulation | Lessons recorded; no general FEM adapter |

## Interpreting the labs and lessons

The [Printed Joints Lab](../labs/printed-joints/README.md) is a native experiment with its own validation report. The [checker lab](../labs/checker-lab/README.md) tests a helper, not a product. [Lessons from projects](../knowledge/lessons/project-lessons.md) states rules generically; the figures of the originating projects are not evidence in this repository. Physical validation remains separate everywhere.

FDM has the broadest documented experience. Laser cutting has a documented kerf-ownership rule and an exporter pattern. CNC and SLA are reference areas. Generic profile values are not measured machine capabilities.
