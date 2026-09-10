---
name: cad-joints
description: "Select, reconstruct or design mechanical connections between CAD parts, including printed sliding joints, dovetails, keyed scarfs and snap fits. Use for joint geometry, assembly paths, retention or comparative fit coupons; cosmetic seams and ordinary assembly illustration alone do not require this skill."
---

# CAD joints

Read [shared evidence conventions](../../knowledge/core.md) and the relevant sections of [joint selection and verification](../../knowledge/joints.md). Start with the load direction, required freedoms, assembly access and whether disassembly must be possible. Separate geometric restraint, friction/preload and any added locking element. Classify assembly as rigid, elastic or a combination before choosing a verification method.

Use the project's authoritative CAD backend. Route native Onshape construction to [onshape-cad](../onshape-cad/SKILL.md) and its session adapter; use [cad-fdm-design](../cad-fdm-design/SKILL.md) for print pose, material and slicing. Keep design-language detailing outside protected mating faces.

## Workflow

1. Identify the members, supported loads, remaining motion, assembly order, available insertion space and service access. Ask only for missing constraints that change the choice.
2. Distinguish source observations, measured dimensions and proposed reconstruction values. Link the original reference and relevant timestamp. A video demonstration is not a transferable strength rating.
3. Construct both mating parts from common reference geometry. Define which part owns the allowance and its direction: per face, diametral, profile-plane or normal to the surface. Do not offset both parts inadvertently.
4. Check the complete assembly and removal paths, including keys, adjacent parts and stops. End-position nonintersection alone does not prove assembly. For elastic snaps, record free, maximally deflected and seated shapes, identify the compliant region, and justify allowable strain through an appropriate model or measured coupon. A rigid overlap test cannot establish elastic assembly. Preserve failed path findings and state the sampling resolution.
5. Verify native feature status, expected solid count, valid geometry, pairwise interference and revision-bound exports. Record transforms between assembled, separated and print poses explicitly.
6. Prepare a small clearance series in the intended material and orientation. Keep CAD clearance, measured fit, insertion force, repeated assembly, creep and load testing as separate evidence levels.

Use [fits and retention](../../knowledge/fits-and-retention.md) for snaps, preload and compensation; [assembly review](../../knowledge/assembly-review.md) for access and completeness. The [Printed Joints Lab](../../examples/printed-joints/README.md) contains independent native reconstructions and their actual verification status. It is an example library, not a validated catalogue of structural joints.

For bending and tensile applications, examine the weakest root, remaining socket wall and layer-normal opening load. A longer engagement or steeper wedge does not by itself establish adequate strength. Compare matched specimens and a continuous control before ranking designs.

For thin panels, separate connectors and rim clips, consult the [additional reference review](../../docs/joints/additional-references.md). Keep these reviewed references distinct from the native lab: they have no reconstructed CAD or physical verification yet.
