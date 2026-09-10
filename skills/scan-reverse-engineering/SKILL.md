---
name: scan-reverse-engineering
description: "Reconstruct functional CAD from 3D scans: inspect and clean the source, register and orient it, fit primitives, distinguish base form from features, and compare the reconstruction with a meaningful reference surface."
---

# Scan to parametric CAD

**Use when** a 3D scan has to become usable CAD: inspecting and cleaning the source mesh, registering scans, establishing a canonical frame, fitting primitives, separating base form from features and measuring the reconstruction against the scan. **Do not use when** the part can simply be measured, or when the scan is only needed as a visual reference.

## Procedure

1. Look at photographs of the actual part first. Topology is resolved in seconds from a photo and can cost an hour from scans alone; photographs also separate real form features from acquisition artefacts such as attached markers.
2. Clean unwanted turntable geometry and register the scans. Scanned coordinates are not automatically world-aligned and the turntable is not necessarily normal to Z.
3. Establish a canonical frame, then measure sections and functional features. Preserve the uncertainty carried in from acquisition and registration.
4. Separate the simplest plausible base form from local ribs, grooves and other features, and model them as distinct parametric elements.
5. Fit and test design hypotheses. Compare both directions of surface deviation and inspect local zones: a global median can hide an unacceptable fit at a mounting surface. Sample within triangles so the comparison does not merely measure tessellation vertices.
6. Treat an exact faceted mesh-to-BRep conversion and a reconstructed parametric model as different goals. A prism-extraction shortcut suits genuinely extrusion-like geometry only; compare bounds, topology and volume before accepting it.

No physical fit claim follows from a scan-to-CAD distance map.

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [What a check actually establishes](../../knowledge/foundations/verification.md)
- [Combining tasks](../../knowledge/workflow/recipes.md) — handing the reconstruction on to a design skill.
- [Reusable construction patterns](../../knowledge/construction/patterns.md)

## References

- [Field notes](references/field-notes.md) — the recorded working sequence, module-by-module notes and fitting traps. The Python and wheel statements are observations of one environment; verify the installed versions elsewhere.

## Environment

Scan toolkit location and pinned interpreter for this machine: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml). The toolkit and any mesh-to-BRep experiment are external runtime dependencies; see [scope](../../docs/scope.md).
