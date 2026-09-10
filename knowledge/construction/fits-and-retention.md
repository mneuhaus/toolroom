# Slide-in fit, preload and one-piece latches

Use when a printed guide rocks, a mating seam opens, or the user wants a part
to snap in under slight tension. Derived from Alternate Chute / Funnel Guide
R2–R4, September 2026. R4 was checked in CAD and OrcaSlicer; physical fit and
retained PLA preload were still untested. Its dimensions are not general rules.

## Establish the actual constraint and contact system

- Record material, allowed part count, adjustment method and which existing
  parts/poses may change separately. “PLA” is not consent to add a screw.
  “One-piece, snaps in during insertion” excludes a separate clamp wedge for
  that task. Existing mounting screws may still be part of the unchanged design.
- Identify how the part moves: lateral translation, withdrawal, rocking, or
  opening of a seam under load. Map the relevant degrees of freedom to contacts
  in the **whole assembly**, including the core and the opposite guide.
- Read the current geometry and identify parts by role/source and measured
  features, not by array position. The first core solid in this project was a
  bearing holder, not the main chute body.
- Preserve specified mounting axes, mating parts and assembly transforms.
  Measure the existing end stop before inventing additional seating travel.
  A local guide/funnel calculation omitted the core; moving the funnel inward
  to “pull it tight” then caused a large core collision. That candidate was rejected.

## Design rigid location and elastic retention together

1. Define which rigid faces stop insertion and resist rocking. Give bearing
   shoulders useful separation along the rocking lever arm and sufficient
   support behind them. A tiny clearance reduction alone establishes no preload.
2. Use the latch to keep those faces seated. Check the contact normal and force
   direction at the **existing seated pose**. A latch that only blocks withdrawal
   may still permit the seam to open or the part to rock.
3. Check a small virtual withdrawal: for an elastic draw latch, required
   deflection/strain energy should initially increase in the withdrawal
   direction. A tooth that unloads on withdrawal may push the part away from
   the stop instead. Include friction assumptions rather than relying on them
   silently; evaluate retention against the expected separating load.
4. Provide a lead-in and a reachable release action. Check that the tooth clears
   and does not bottom against the tongue slot throughout insertion and release.
   A printed integral release tab can satisfy a one-piece requirement.

Use long flexures with rounded slot roots and gradual load transfer where the
available envelope allows. Check both seated deflection and the higher excursion
over the lead-in, including plausible print variation. Do not turn R4's tongue
length, thickness, strain estimates or the usual 0.42 mm deburr into defaults for
other latches. Chamfers must preserve retaining faces and the flexure root.

For PLA, describe relaxation and repeated insertion as validation needs, not a
reason to silently substitute PETG or new hardware. A linear solid-beam estimate
is only a screening model: record its modulus assumption, loaded length,
section, deflection and orientation. Infill, perimeters, stress concentrations,
temperature and time affect the printed part. It is neither an FEA result nor
an allowable-strain or fatigue certification. A clearance or latch measured in
one print pose does not carry over to another; see
[print orientation](../manufacturing/print-orientation.md).

## Verify the three states explicitly

- **Unloaded print geometry:** one connected solid for a one-piece holder;
  mounting hole axes and reference faces retained; usable bed face, no slivers,
  enclosed support traps or accidental severing of the tongue.
- **Insertion/removal:** sample the real path, including the peak ramp crossing,
  both end conditions and release. Track deformation/clearances with the mating
  parts present. Final-pose clearance alone does not establish insertability.
- **Seated assembly:** distinguish intentional undeformed tooth overlap from
  rigid collision. Record partner, location and magnitude of that overlap;
  compare a justified deflected-tongue model and check all remaining neighbour
  pairs. Do not waive the entire guide/funnel pair or translate a fixed mate to
  make the undeformed overlap disappear. A rigid-only legacy test must be
  adapted to this distinction, not simply disabled.

Run the relevant cases for each funnel size and both guide positions. Record
which geometry is exact and which deformation or contact calculation is an
approximation. Mesh intersection volume alone is not a stiffness or retention
measurement; coplanar FCL penetration reports also need a localized check.

## Print and physical acceptance

Choose a broad real bed face on the final part and orient the tongue/root for
the load path. Check perimeters and actual support extrusion in the slicer;
see [slicer preparation](../manufacturing/print-preparation.md). State how many identical pieces
are required and how many are included in the plate.

The first physical check is a complete mating set: insert fully, inspect seam
opening and rocking under representative hand/load directions, and confirm
release access. Repeat after several insertions and a documented hold time at
the intended temperature. Compare with the user's actually printed revision.
Until that is done, report “geometry/slicing checked; physical fit and retained
preload open,” rather than “cannot wobble” or “permanently play-free.”

Worked evidence in the CAD workspace:
`alternate-chute-design/funnel-holder-r4/README.md`, `verification.json`,
`audit.json` and `print-verification.json`. Historical R2/R3 checks describe
different retention concepts and are not the current acceptance criteria.
