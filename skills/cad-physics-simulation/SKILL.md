---
name: cad-physics-simulation
description: "Simulate or animate a CAD mechanism handling loose parts, exercise control software against a virtual machine, or produce physically driven footage from a logged trajectory; not for FEM strength analysis and not for a static render of an assembly."
---

# CAD physics simulation

**Use when** a mechanism has to be watched handling loose parts before it exists, control software has to run against a virtual machine, or footage must come from contact physics rather than keyframes. **Do not use when** the question is stress or deflection (that is FEM), or when a still or turntable render of the assembly is all that is needed.

## Procedure

1. Establish the question and the evidence it needs. A simulation establishes the behaviour of the defined model under its assumptions, nothing about the real machine until calibrated; say which claim the output has to support.
2. Export the assembly with honoured tessellation tolerances and a known frame (units, up axis, origin). Record the preset. Deduplicate repeated parts by name, face count and bounds; gate fastener removal by size.
3. Build the collision set: convex-decompose only what loose parts touch, cap hulls per piece, keep the rest visual. Build the part library with explicit mass and inertia from one solid per body.
4. Model drives as velocity-driven, armature-heavy joints where the real drive cannot slip. Set contact masks so machine geoms meet pieces only. Keep the drive-to-controller ratio as arithmetic in one place and check spin direction against the machine.
5. Choose timestep and solref together, spawn on a grid with clearance, run with a seed, log every pose at the target frame rate, and stop on the first non-finite state.
6. Pick camera and time window with the engine's own renderer, and write the camera to a file the replay reads unchanged.
7. Replay in the renderer: one object per simulated body, pivots per driven joint, frames written whole and renamed so a run resumes. Keep emissive high-poly meshes out of light sampling.
8. Bind log, camera file, export preset and tool versions to the output. A re-simulation is equivalent, not identical.
9. State the calibration status in the report: which values are placeholders and what footage or measurement would replace them.

## Knowledge

- [From CAD assembly to rigid-body simulation and replay](../../knowledge/simulation/cad-to-physics-simulation.md): the pipeline, the modelling decisions and their reasons, the checklist.
- [What a check establishes](../../knowledge/foundations/verification.md): the simulation row and what stays unresolved.
- [Assembly, access and load paths](../../knowledge/construction/assembly-review.md): the motion and interface questions a simulation should not replace.
- [Project layout and revisions](../../knowledge/workflow/project-layout.md): where logs, camera files and renders live next to the CAD revision.

## References

- [Field notes](references/field-notes.md): the Sorter V2 feeder clip handoff README and the simulation repository's AGENTS.md, verbatim.
- [Vendored code snapshot](references/sorter-v2-feeder-clip/MANIFEST.json): `sim/` (MuJoCo scene, extraction, decomposition, piece library, clip recorder), `render/code/` (Onshape export, LDraw loader, Blender replay, encode job), with `MANIFEST.json` and `LICENSE-NOTE.md`. Software MIT + Commons Clause, design content CC BY-NC-SA 4.0; a snapshot for study, not maintained here.

**Environment:** the handoff ran on a Linux box with an RTX 3090 and a 4-core CPU, the export on a Mac through a local Onshape bridge. Endpoints, paths and GPU details belong in [`profiles/environment/`](../../profiles/environment/README.md), not in this skill.
