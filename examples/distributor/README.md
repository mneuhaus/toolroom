# Distributor: modelling the actual contact

In the documented R8 study, two platforms and two posts form the actual four-part section. All three plug-in joints transfer load through unilateral contact on real CAD faces. The earlier rigid coupling represented a different mechanical assumption.

## The modelling decision

The faces can open and slide. Print orientation is considered for each part; effective material properties and friction are assumptions. The model includes CAD clearance and elastically modelled ribs, but no physically calibrated insertion process.

In the saved 1 kg scenario with assumed friction, the study gives approximately 3.97 mm maximum vertical displacement. This value belongs to that load case, support arrangement and R8 geometry. The image exaggerates deformation by a factor of five.

## Findings and limitations

The report checks solver progress, equilibrium and sensitivity to contact stiffness. A full mesh-refinement study of this contact model was still open. PLA creep, plastic yielding and actual load capacity are not established by these results.

Later CAD revisions must not present this value as a new simulation of their own geometry. The framework's FEM extension remains a documented study for now.

## Transferable rule

A simulation must identify geometry, contact, material, orientation and load together. “FEM checked” without this connection is not a traceable claim.

Continue: [Verification](../../knowledge/verification.md) · [Scope](../../docs/scope.md)
