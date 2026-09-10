---
name: cad-joints
description: "Select, reconstruct or design mechanical connections between CAD parts, including printed sliding joints, dovetails, keyed scarfs and snap fits. Use for joint geometry, assembly paths, retention or comparative fit coupons; cosmetic seams and ordinary assembly illustration alone do not require this skill."
---

# CAD joints

**Use when** two parts have to be connected and the connection is the design problem: selecting, reconstructing or dimensioning printed sliding joints, dovetails, keyed scarfs, snap fits, assembly paths, retention or comparative fit coupons. **Do not use when** the seam is cosmetic, or when an existing joint only has to be illustrated in an assembly drawing.

## Procedure

1. Start from load direction, required freedoms, assembly access and whether disassembly must be possible. Separate geometric restraint, friction or preload, and any added locking element. Classify the assembly as rigid, elastic or both before choosing a verification method. Ask only for the missing constraints that change the choice.
2. Distinguish source observations, measured dimensions and proposed reconstruction values. Link the original reference and its timestamp. A video demonstration is not a transferable strength rating.
3. Construct both mating parts from common reference geometry. Define which part owns the allowance and in which direction — per face, diametral, profile-plane or normal to the surface. Do not offset both parts by accident.
4. Check the complete assembly and removal paths including keys, adjacent parts and stops. End-position nonintersection does not prove assembly. For elastic snaps, record the free, maximally deflected and seated shapes, identify the compliant region, and justify the strain through an appropriate model or a measured coupon; a rigid overlap test cannot establish elastic assembly. Preserve failed path findings and state the sampling resolution.
5. Verify native feature status, expected solid count, valid geometry, pairwise interference and revision-bound exports. Record the transforms between assembled, separated and print poses explicitly.
6. Prepare a small clearance series in the intended material and orientation. Keep CAD clearance, measured fit, insertion force, repeated assembly, creep and load testing as separate levels of evidence.

For bending and tensile loads, examine the weakest root, the remaining socket wall and the layer-normal opening load. A longer engagement or a steeper wedge does not by itself establish strength; compare matched specimens against a continuous control before ranking designs.

Use the project's authoritative CAD backend: [onshape-cad](../onshape-cad/SKILL.md) for native cloud construction, [cad-fdm-design](../cad-fdm-design/SKILL.md) for print pose, material and slicing.

## Knowledge

- [Joints: connections as construction knowledge](../../knowledge/construction/joints.md) — selection and verification.
- [Slide-in fit, preload and one-piece latches](../../knowledge/construction/fits-and-retention.md) — snaps, preload, compensation.
- [Assembly, access and load-path review](../../knowledge/construction/assembly-review.md) — access and completeness.
- [Print orientation for FDM parts](../../knowledge/manufacturing/print-orientation.md) — layer direction against the opening load on a printed joint.
- [Further joint references: panels and elastic clips](../../knowledge/construction/joints-panels-and-clips.md) — reviewed references with no reconstructed CAD or physical verification yet; keep them distinct from the lab.
- [Shared project and evidence conventions](../../knowledge/foundations/core.md) and [what a check actually establishes](../../knowledge/foundations/verification.md).

## References

- [Printed Joints Lab](../../labs/printed-joints/README.md) — independent native reconstructions with their actual verification status. An example library, not a validated catalogue of structural joints.
