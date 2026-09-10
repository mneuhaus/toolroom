---
name: scan-reverse-engineering
description: "Reconstruct functional CAD from 3D scans: inspect and clean the source, register and orient it, fit primitives, distinguish base form from features, and compare the reconstruction with a meaningful reference surface."
---

# Scan to parametric CAD

Read [Shared project and evidence conventions](../../knowledge/core.md) and [scan field notes](references/source-guide.md). Use the actual photos and scanned surfaces to establish topology, marker artifacts and missing data before fitting geometry. Scanned coordinates are not automatically world-aligned.

Clean unwanted turntable geometry, register scans, establish a canonical frame, then measure sections and functional features. Separate the simplest plausible base form from local ribs, grooves and other features. Preserve uncertainty from acquisition and registration.

Fit and test design hypotheses. Compare both directions of surface deviation and inspect local zones; global median deviation can hide an unacceptable fit at a mounting surface. Sample within triangles so comparisons do not merely measure tessellation vertices.

An exact faceted mesh-to-BRep conversion and a reconstructed parametric model serve different goals. The STL2STEP prism experiment is only suitable for genuine extrusion-like geometry; compare bounds, topology and volume before accepting it.

The source [scan-toolkit and STL2STEP workflows](../../docs/scope.md) are external runtime dependencies. Historical Python/wheel statements are observations of that environment; verify the installed versions when setting up another machine. No physical fit claim follows from a scan/CAD distance map.
