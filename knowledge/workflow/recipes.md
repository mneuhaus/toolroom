# Combining tasks

A recipe selects existing capabilities and their handoffs. It does not require a complete development cycle for every small change.

## Design a new FDM part

Requirements and interfaces → selected CAD backend → deliberate print pose → geometry and assembly checks ([offline verification](offline-verification.md) for parts that mate with a machine) → actual slicer profile → verified export. Give any required fit experiment its own small coupon.

## Revise an existing Onshape mount

Preserve native user features → inspect mating axes and seating faces → targeted FeatureScript or native change → current body mapping → check affected assemblies → fresh exports. A stable tab alone does not prove stable geometry.

## Design a product family

Functional roles and protected interfaces → selected design language → manufacturing profile → targeted face and edge treatment per part → paired views with the same camera → output bound to evidence.

## Create an assembly manual

CAD snapshot and complete purchased components → manageable bill of materials → subassemblies and accessible screw sequence → durable build stages → separate illustration → PDF/web → inspect every page and quantity.

## Reconstruct a scan

Review photos and scans → clean and register → reference axes → distinguish base forms from features → reconstruct functional surfaces → inspect local bidirectional deviations. A smoothed image is not dimensional evidence.

## Compare structures

Current geometry and load assumptions → actual print orientations → appropriate contact/material model → equilibrium and sensitivity checks → prediction limits → suitable physical comparison. This extension currently exists in the framework as a documented project study.

## Select and construct a joint

[cad-joints](../../skills/cad-joints/SKILL.md) establishes loads, assembly paths, geometric restraint and locking. The selected CAD skill creates native geometry; [cad-fdm-design](../../skills/cad-fdm-design/SKILL.md) handles print pose and physical fit trials. The [Printed Joints Lab](../../labs/printed-joints/README.md) presents eight reconstructed principles from three video sources.

## Simulate or animate a mechanism with loose parts

Question and required evidence → assembly export with honoured tolerances and a known frame → collision set for touched parts only, part library with explicit mass and inertia → velocity-driven heavy joints, contact masks, overlap-free spawn → logged poses → cheap camera and window preview → replay render bound to log, camera and export. The [cad-physics-simulation](../../skills/cad-physics-simulation/SKILL.md) skill and [CAD to rigid-body simulation](../simulation/cad-to-physics-simulation.md) carry the decisions; an uncalibrated run is a hypothesis, not a throughput figure.
