# Pivoting snap latches: closing two parts under preload

A pivoting snap latch pulls two parts together and holds them under tension. A separate latch plate swings on a pivot fixed to one part, hooks under a catch on the other part, and clicks into a detent so it stays closed. It is opened by hand and needs no hardware. This article treats it as its own connection type. It stands beside the [tile clip joint](tile-clip-joints.md), which joins edges without preload and hides inside the part, and the [one-piece latch](fits-and-retention.md), where the snap is a cantilever grown on the part itself.

The reviewed example is SnapLock V3 by Hugo on MakerWorld, a rugged storage box whose two printed latches close the lid against a gasket [SL: MW-API]. Its files are under the MakerWorld Exclusive License: non-commercial, derivatives only on MakerWorld, and the designer objected when a user treated the parametric file as public domain [SL: §2; MW-V1P]. This article therefore describes the mechanism and the lessons, quotes measured extents as a reviewed example, and never presents SnapLock geometry as something to copy into a Toolroom design. Sources are tagged [SL] with the sub-source from the findings; our own reasoning is marked "derived" or "proposed". Provenance: [`provenance/references/snaplock/manifest.json`](../../provenance/references/snaplock/manifest.json).

## What a pivoting snap latch is

Three bodies take part. The **latch plate** is U-shaped. Its two arms end in inward **wings**. Between the arms sits a thin **tongue** that can flex in the plane of the plate, and at the bottom a **finger lip**. The **pivot boss** is a rib on the lid; the arms snap over it and swing on it. The boss carries a **slot** for the tongue. The **catch bar** is a rib on the base; the wings hook under it when the latch is swung down [SL: §3 mechanism, inferred from IMG DSCF2412, DSCF2424; MW-API; MW-THIN].

Closing: the plate swings down, the wings ride over the catch bar and hook under it, and the tongue flexes and drops into the boss slot with a click. Opening: a finger lifts the lip, the tongue flexes out of the slot, and the plate swings up. The wings release the catch and the lid is free [SL: §3, inferred].

The three joint effects from [Joints](joints.md) map onto this latch as follows.

| Effect | Where it happens |
| --- | --- |
| Geometric interlocking | The wings under the catch bar block the lid from lifting. The arms around the pivot boss block the latch from leaving the lid. |
| Preload | The distance from pivot to wing hook face is slightly shorter than the distance from pivot to catch underside in the closed state. The arms act as tension links. The difference is taken up by gasket compression and a little arm stretch (derived). |
| Retention of the closed state | The tongue in the boss slot. Not friction: a latch that relied on friction at the pivot would creep open under vibration (derived). |

The latch is good at a reversible, tensioned closure without tools. It suits a lid that must seal on a gasket, because the arms keep the gasket compressed. It survives many open-close cycles if the flexing tongue is sized for its strain, because the tongue only clicks and the rigid wings carry the load (derived; no durability data exists in the sources [SL: §8]).

Its limits. It needs space outside the wall: the SnapLock bosses and latch stand 7.0 mm proud of the wall face [SL: MEAS]. It adds two extra parts per box. The latch is the wear part. Lifting the lid with the latch closed puts a peel load on the pivot boss and the catch bar, both ribs printed as overhangs (derived).

## Where it fits

| Connection | Preload | Reversible | Hardware | Space | Wear part | Typical use |
| --- | --- | --- | --- | --- | --- | --- |
| Pivoting snap latch | Yes, set by arm length and gasket | Yes, by hand | None | Outside the wall, about 7 mm in the example [SL: MEAS] | The latch | Lid on a box, cover on a case, sealed enclosure |
| One-piece cantilever latch ([Fits and retention](fits-and-retention.md)) | Slight, from tooth overlap | Yes, with a release tab | None | Inside the part envelope | The part itself | Slide-in guide, holder that snaps in |
| Tile clip in pocket ([Tile clip joints](tile-clip-joints.md)) | None, seated clip is nearly stress free | Yes, pull apart | None | Hidden in the edge | The clip | Modular tiles and panels, edge to edge |
| Screw | Yes, adjustable | Yes, with a tool | Screw, often an insert | Boss and head clearance | Thread in plastic | Permanent or rarely opened joints |
| Magnet | Weak, constant | Yes, by hand | Magnets | Pocket in the wall | None | Doors, covers, alignment aids |

Choose the pivoting latch when the joint must be opened often, must stay tight under a seal, and there is room outside the wall. Choose a one-piece latch when no extra part is allowed. Choose a tile clip when the edges must stay flush and hidden.

## SnapLock V3 as a reviewed example

**The box.** A hinged storage box in two printed halves plus two latches and an optional TPU gasket [SL: MW-API; F3D body names]. It is parametric: Inside_width, Inside_length, height and Corner_radius describe the cavity, with 110, 100, 50 and 25 mm as the file defaults [SL: MW-API; F3D]. Walls are 2.0 mm, the floor 5.0 mm, the lid ceiling 2.0 mm [SL: MEAS]. A 3.0 mm skirt on the lid reaches below the parting line into the gasket groove [SL: MEAS, inferred]. The gasket is a ring 2.0 wide and 1.5 thick, centred on the wall [SL: MEAS]. The hinges are integral snap knuckles on lid and base, no pin, pressed together at a 45 degree angle [SL: MW-V2; MW-API; IMG DSCF2414].

**Versions.** V1 of February 2024 offered 36 fixed sizes with a separate clip inserted "with a twisting motion" [SL: MW-V1]. The parametric V1 added the gasket and a bump on the wall so the latch could not be mounted backwards, and V2 of May 2025 redesigned the hinges, went to a single latch and set a 45 degree assembly angle [SL: MW-V1P; MW-V2]. V3 of December 2025 returned to two latches and moved the detent into the latch: "without any visible bumps on the enclosure, only the latches themselves" [SL: MW-API; §1].

**The latch.** The values below are vertex and plane extents read from the Fusion archive, not evaluated curved faces. Which plane is a wall, a catch or a pivot is inferred from photos and parameter expressions [SL: §3 caveat].

| Feature | Value | Source |
| --- | --- | --- |
| Latch overall, one body | 30.0 wide × 10.0 deep × 44.0 tall | [SL: MEAS bbox] |
| Latch centre position | Inside_width / 4 from the box centre, so 27.5 at the default width | [SL: MEAS; F3D expressions] |
| Main plate thickness | 3.0 | [SL: MEAS planes, inferred] |
| Finger lip | Lowest 4 mm of the body, only at the plate | [SL: MEAS, inferred] |
| Catch bar on the base | 8 wide, protruding 7 beyond the wall | [SL: MEAS, inferred] |
| Pivot boss on the lid | 15.6 wide, with a central slot 2.9 wide | [SL: MEAS, inferred] |
| Central tongue | 2.6 wide | [SL: MEAS vertex x-levels, inferred] |
| Protrusion of both halves at the latch side | 7.0 beyond the wall face | [SL: MEAS] |
| Clearances in the model | 0.10 used nine times, 0.2 once, 0.5 once; which joint each belongs to is unconfirmed | [SL: F3D] |
| Design angles | 45 used eighteen times, 63 four times, 60, 40, 5 | [SL: F3D] |

**Print advice from the designer.** PETG is the preferred material for the latches, PLA works [SL: MW-API]. V1 recommended PETG and 15 percent infill or more, and the clip face that touched the bed should face outward [SL: MW-V1]. The MakerWorld export is one assembled box; split it to objects and print the parts as shown, latches flat on their outer face, lid and base open side up [SL: MW-API; IMG DSCF2404]. The designer's V2 profiles used 0.2 mm layers with 3 walls and 10 percent infill, or 0.16 mm layers with 2 walls and 15 percent [SL: MW-V2F]. No source states "no supports" in words; the steep undersides on the bosses and the remix note about steepening them imply support-free printing [SL: MW-THIN, inferred].

**The Thin Remix lesson.** DBT85 shrank the lid to 10 mm from 25 mm and the base to 10 mm minimum, steepened the overhang angles, and added hard parameter limits because the original file "explodes" outside them [SL: MW-THIN]. The remix had to rescale "the little wings that actually do the latching": a tiny latch with an incorrectly sized wing is "very hard to open" [SL: MW-THIN].

**Reception.** The V3 print profiles are rated 4.9 of 5 [SL: MW-API]. The 689 comments could not be read; no comment endpoint is public [SL: MW-API; §8].

## Design rules for a latch of this kind

Everything here is derived unless tagged.

1. **Separate the flex element from the load path.** A thin tongue gives the click. Rigid arms and wings carry the closing tension. A jaw that flexes and holds at the same time is permanently loaded and relaxes [SL: §7.3].
2. **Put the detent in the moving part.** The box walls stay clean, and a latch with the detent on board cannot be mounted backwards. V3 did this after V1 users mounted the clip the wrong way [SL: MW-API; §7.1].
3. **Give the assembly an orientation groove** so hinge and latch find their pose without instructions [SL: MW-API; §7.2].
4. **Keep the detent height absolute, not proportional,** across a size family. The Thin Remix showed that scaling the whole latch also scales the wing, and a small wing is hard to release [SL: MW-THIN; §7.4].
5. **Size the tongue as a cantilever.** The strain at the root is proportional to the tip deflection times the thickness, divided by the length squared. Keep PLA below about one percent strain and prefer PETG for the flexing part. Both figures are calibration candidates in the sense of [FDM](../manufacturing/fdm.md), not measured values. The screening model and its limits are in [Fits and retention](fits-and-retention.md).
6. **Set the preload deliberately.** The pivot-to-wing distance against the pivot-to-catch distance defines how far the lid is pulled down. Gasket compression takes most of that difference; the arm stretch must stay within elastic strain, or the latch loosens after a few days closed.
7. **Make bosses and catches self-supporting.** Undersides at 45 degrees or steeper print without support. The example uses 45 degrees throughout and 60 to 63 degrees where the remix later steepened further [SL: F3D angles; MW-THIN].
8. **Lead-ins on the wings and the pivot snap.** The wings ride over the catch bar and the arms snap over the boss; both need a ramp so the peak deflection is reached gradually. Chamfers must not remove the hook face.
9. **The latch is the sacrificial part.** It is cheap to reprint; the box is not.
10. **Document the parametric limits.** V2 told users to change values in 5 mm steps or the sketches fail; the Thin Remix had to add hard limits to V3 [SL: MW-V2F; MW-THIN].

## Print orientation

Decide the pose first, per [Print orientation](../manufacturing/print-orientation.md). Reasoning is derived; nothing was printed here.

| Pose | What happens | Verdict |
| --- | --- | --- |
| Latch flat on its outer face | Designer's pose [SL: MW-API; IMG DSCF2404]. Tongue and wings bend in the plane of the plate, so layers are not peeled. The pivot snap loads across layers at the arm root; keep the radii there. | Preferred |
| Latch standing | Layer lines run across the tongue root; the tongue peels apart on the first hard open. | Not recommended |
| Box open side up | Walls vertical. Catch bar and pivot boss overhang at 45 degrees or steeper [SL: F3D angles]. The gasket groove prints as a recess. | Designer's pose [SL: IMG DSCF2404] |
| Lid open side up | Skirt vertical, boss as above. | Designer's pose [SL: IMG DSCF2404] |

Checks after printing: tongue thickness against the slot width, wing hook depth against the catch bar, first-layer squish on the latch outer face (it is the visible face and the bed side), and sag on the boss and catch undersides.

## What transfers to other connections

Five ideas from the review carry over to other joints, including the [tile clip](tile-clip-joints.md) [SL: §7].

1. **Detent in the moving part.** Keep walls and edges clean and make the wrong orientation impossible, by symmetry or by keying.
2. **Orientation groove as assembly guide.** A chamfered or grooved throat aligns a part during blind insertion.
3. **Flex element separated from load element.** A thin tongue for the click, rigid features for the load, so a PLA spring is not held under permanent strain.
4. **Scale-aware detent.** In a size family, keep the detent height constant rather than proportional.
5. **Material.** PETG for the flexing part, PLA acceptable [SL: MW-API].

What not to borrow: the external captive pivoting latch itself, which needs room outside the wall and a lid-side boss and so cannot sit on a flush tile edge; the gasket, which has no role between tiles; and any actual SnapLock geometry, because of the licence [SL: §7].

## Sources and limits

**Measured versus read.** Measured: vertex coordinates and axis-aligned plane positions of the final Top, Bottom, Latch and Gasket bodies in the designer's `SnapLock V3.f3d` [SL: MEAS]. The archive is a zip with Zstandard members; the ASM blobs were read at token level, from the last body record to its points and planes, because entity-level parsing fails on ASM extensions [SL: §3 caveat]. No curved faces and no face adjacency were evaluated. Read: the MakerWorld design API records of V1, V1 parametric, V2, V2 f3d, V3, V3 single latch and the Thin Remix, the design photos and the assembly GIF [SL: MW-API; MW-V1; MW-V1P; MW-V2; MW-V2F; MW-V3S; MW-THIN; IMG].

**No mesh.** Model downloads require a MakerWorld login and were not obtained [SL: §8]. All extents are therefore model-exact but their feature mapping is inferred.

**Licence.** MakerWorld Exclusive License on V1, V2, V2 f3d, V3 and the Thin Remix: derivatives only on MakerWorld with attribution, no commercial use [SL: MW-LIC; §2]. V1 parametric and V3 single latch carry the Standard Digital File License, Community Use, whose text was not fetched [SL: §2]. Describing the mechanism is not a derivative; copying geometry would be. That reading is ours and not legal advice [SL: §2, inferred].

**Unconfirmed.** Tongue thickness, hook depth, pivot diameter and the assignment of the model's clearances and angles to features [SL: §8]. The 689 V3 comments and the version history [SL: §8]. Whether the second gasket body belongs to the 150 × 50 box [SL: §8]. Any tolerance, scaling or durability data beyond the ratings and the Thin Remix remarks [SL: §8].

**No physical trial.** Nothing in this article was printed, fitted or cycled in this repository. The strain limit, the preload rule and the orientation verdicts are derived reasoning. They become process values only after a printed trial series in the sense of [Verification](../foundations/verification.md).
