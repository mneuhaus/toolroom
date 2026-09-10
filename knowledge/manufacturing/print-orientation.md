# Print orientation for FDM parts

Print orientation decides where a part is strong, where it looks clean, where it needs support and where it holds its dimensions. This article collects the transferable rules on that topic from one external reference: *Stop Printing Flat: The 45° Secret for Stronger Parts* by CNC Kitchen (Stefan Hermann), 26 October 2025. The knowledge is video-derived, not physically verified in this repository; every figure below is stated in that source under its own conditions, never a calibrated process value for our work. Reviewed from the author's subtitles and sampled frames; see [Source and limits](#source-and-limits).

## Why orientation changes strength

An FDM part is anisotropic. Bonds along a bead are polymer chains; bonds between layers are a partial re-melt of the layer below, so pulling layers apart is the weak direction. The source's core move is to align the principal tensile stress with the print lines, and where no orientation does that for all load directions, to accept an intermediate angle. The response is not linear: strength falls steeply away from flat, then flattens towards upright. A few degrees buy nothing, so if layer adhesion is the problem, tilt far enough to matter.

## What the source measured

Tensile coupons, 0.2 mm layers, Prusa CORE One, AzureFilm green PLA, pulled on the author's own tensile tester.

| Print angle | Tensile strength stated in the source |
| --- | --- |
| 0° (flat, load along the layers) | 63 MPa |
| 30° | 44 MPa |
| 45° | 40 MPa (three coupons) |
| 60° | 36 MPa |
| 90° (upright, load across the layers) | 31 MPa |

Further stated numbers: 45° is "27 % stronger" than the upright reference; layer adhesion is "typically around 50 %" of in-plane strength, higher for some materials and much lower for ABS printed with heavy cooling; the angled hose adapter gains "roughly 30 % more layer strength"; surfaces stay clean without support while slope angles stay "below roughly 45°". The plotted curve is a quadratic interpolation of the five points.

A second measured case is a hook, pulled to failure in three orientations. The flat (XY) hook carried by far the highest load; the 45° and 90° hooks failed at nearly the same, much lower load. Tilting did not help, it only moved the failure location, because the loading is not a simple uniaxial pull.

## What the source asserts without a test

| Assertion | Shown how |
| --- | --- |
| Slicer auto-orientation optimises bed contact and support, not strength | Stated |
| A countersunk screw in a side-printed bracket splits it through the hole | Demonstrated, not instrumented |
| A corner bracket has no good orientation, so its tip is the balanced compromise | Reasoned and printed, not tested |
| Tilting makes every face a perimeter face, so top, bottom and sides look and feel alike | Printed samples |
| Tilting a relief removes stair-stepping on shallow slopes | Printed samples, a mountain relief flat versus rotated 90° |
| Shrink lines (the Benchy hull line) come from a thin wall pulled together when a full deck starts in one layer; tilting spreads that deck over many layers | Arch demonstrator and Benchy |
| Side-printing warp-prone material lifts the ends | Stated |

## Getting an angled part to print

Angling costs bed contact, support and time, and adds its own failure mode.

- **Bed contact.** Rotate into the wanted pose, then use the slicer's cut tool to shave a small flat off the corner that touches the plate, and add a brim. This is the source's routine when the CAD cannot be changed.
- **Support release is a real failure mode.** All of the author's angled coupons printed with normal supports failed; those without supports printed cleanly. The mechanism given: even PLA curls, the loosely coupled support holds it, tension accumulates, the support lets go, the part springs up and the nozzle hits it.
- **Two fixes offered.** Custom supports rigidly attached at only a few points (credited to Slant3D), or a reduced support-to-object XY distance with supports that are harder to remove but hold. The values visible in the slicer panel are the author's defaults, not a recommendation.
- **Split instead of tilt.** The strongest structural example is the Multiboard system: rather than tilting a clip so its hooks print strong, the part is split down the middle, both halves print flat joined by a thin living bridge, and it is folded afterwards.

## Our derived rules

| Situation | Rule we take from this |
| --- | --- |
| One dominant tensile load | Orient so the load runs along the beads; a flat pose with a bad load direction is worse than an awkward pose with a good one |
| Two load directions, no pose serves both | Tilt to an intermediate angle, and tilt properly |
| Load case is not a simple pull (hooks, clips, bearings) | Do not assume tilting helps; it can just relocate the failure. Test, or split the part |
| A screw head, insert or press-fit sits on a layer boundary | Splitting hazard: reorient or move the feature; tightening force pushes layers apart |
| A surface must look or measure well | Decide before detailing whether it is a bed, top or perimeter face; a clean first layer can itself be the intent |
| Shallow or organic surfaces stair-step | Rotate until the slopes fall into the printable band instead of chasing layer height |
| A thin wall meets a large flat top | Expect a shrink line there; tilt, or break the transition up in CAD |
| The pose needs support | Plan support with the orientation, not after it, and verify in the slicer preview |
| The model is published or handed on | Export the mesh already in the intended print pose |

## How this applies here

None of this changes our own process values; it sharpens decisions we already make.

**The bed face is chosen before detailing.** Orientation fixes the strength directions, the support strategy and which faces are perimeter faces, and all three get expensive once fillets, bosses and labels exist. Ask it at the first sketch, together with how the part is loaded; see [print preparation](print-preparation.md) and the [cad-fdm-design skill](../../skills/cad-fdm-design/SKILL.md).

**Protected mating interfaces stay protected.** Reorienting fixes a weak part but changes hole roundness, overhang quality and effective clearance on exactly the faces that mate. The source's adapter split during installation at its new angle because it was too tight, and only worked once the dimensions were corrected. A reorientation changes the interface; it is not free; see [fits and retention](../construction/fits-and-retention.md).

**Fits need their own coupon in the same print pose.** A clearance measured on a flat-printed block does not carry over to the same feature printed at 45°. If the pose changes, the fit evidence is stale.

**Slicer evidence beats assumptions.** Support contact, bridges, bed contact area and the first layers of an angled part are visible in the sliced preview, and the source's failed prints show that plausible-looking support can still wreck a job. Video numbers are uncalibrated search limits in the sense of [FDM profile guidance](fdm.md); confirming them belongs to [verification](../foundations/verification.md).

## Source and limits

- Source: <https://www.youtube.com/watch?v=7aJ4dDyyf20>, CNC Kitchen, *Stop Printing Flat: The 45° Secret for Stronger Parts*, 26 October 2025, 17:05.
- Evidence used: the author's subtitle track, converted locally to a plain-text transcript, plus 105 sampled frames (roughly one per 9.8 s) reviewed as contact sheets. The frames confirm the tensile and hook charts, the coupon and bracket geometry, the slicer poses, the cut-for-bed-contact trick, the failed angled prints and the finished adapter.
- Not verified: nothing from this reference was printed or measured here. The MPa figures, the percentages and the 45° guidance are the author's results on his machine, material and settings. The hook loads were read off a low-resolution chart frame and are used only qualitatively. The video stream itself could not be retrieved, so the review is frame-sampled rather than complete.
- Provenance record with hashes, method and the copyright note: [`provenance/references/print-orientation/manifest.json`](../../provenance/references/print-orientation/manifest.json).
