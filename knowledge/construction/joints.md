# Joints: connections as construction knowledge

A joint is described by its geometry, assembly path, manufacturing process and intended load case. Its name alone is not enough to select it. The [cad-joints skill](../../skills/cad-joints/SKILL.md) guides these decisions; the [Printed Joints Lab](../../labs/printed-joints/README.md) illustrates them with native Onshape examples.

## Three distinct effects

**Geometric interlocking** prevents a particular relative movement through engaging faces. A dovetail can prevent separation across its sliding direction while remaining free along that direction.

**Frictional retention and preload** require contact forces. A tapered assembly path can become tighter with further insertion. Whether the joint holds by itself also depends on friction, deformation, surface condition and load. An angle alone does not establish self-locking.

**Retention** limits a remaining movement through a stop, snap hook, transverse wedge, pin or cover. Its assembly and subsequent access are part of the design. A snap hook must not be declared assemblable by assuming excessive elastic deformation.

## Select by task

| Task | Suitable approach | Decisive check |
| --- | --- | --- |
| Repeatedly join parts with a straight movement | Slider, tongue and groove, straight dovetail | Insertion space and retention against sliding out |
| Reduce clearance during assembly | Tapered slider | Insertion depth, press-in force, removal and creep |
| Split a long bar | Lap or scarf joint | Bending, remaining section, lever arm and layer orientation |
| Resist straight separation through a spatial assembly path | Curved dovetail | Complete sweep clearance, entry and end stop |
| Limit socket spreading | Opposing interlocking flanks, such as the Echo-Lock principle | Thinnest root and wall, shared assembly path |
| Use several fingers for geometric interlocking | Finger or Drop-Lock principle | Spacing, withdrawal direction and load sharing |
| Apply preload after joining and release deliberately | Scarf with opposing wedges | Wedge access, push-out travel, stops and lateral guidance |
| Connect quickly and open frequently | Snap fit | Strain limit, notches, fatigue and release access |

This is a selection guide, not a strength ranking. Printed threads, bayonets, pins, magnet pockets and adhesive joints can extend the knowledge later; the first native collection covers the three linked video sources.

## Shared geometry and one clearance owner

Derive male and female partners from the same centreline, surface or profile definition. An independent second sketch can introduce unnoticed differences, particularly on inclined or curved surfaces. Then assign the clearance to exactly one partner.

Record whether 0.10 mm means per flank, total width allowance or profile offset. An offset in a sketch section does not automatically produce a constant normal gap on drafted or curved faces. Nominally positive clearance does not guarantee a printed fit either.

A small trial series could compare **0.05 / 0.10 / 0.15 / 0.20 mm profile offsets**. These are proposed search points. Keep material, nozzle, layer height, extrusion width, wall count, orientation, seam position and slicer compensation constant and record them. Measure first, then transfer the chosen value into the specific manufacturing profile.

## Assembly is a path

Checking the final position is insufficient. Specify the moving and fixed components, axis or translation, and installation order of the retainers. Check the entire path from fully separated parts to the final position. An exploded view illustrates parts; it does not prove that path or define a print orientation.

For tapered profiles, the smaller end must enter the larger opening first. With opposing flanks, draft signs can reverse even though both bodies share the same assembly movement. Curved guides also need room for the attached bar ends to sweep.

A numerical path test states its distance or angle increments, volume tolerance and CAD revision. There is a gap in the evidence between samples. An intentionally incorrect movement provides a countercheck: does the test detect the expected engagement there?

## FDM and load

First check the remaining section at tooth roots and socket walls. More engagement length spreads contact but cannot indefinitely compensate for a thin root or one vulnerable to layer separation. A steeper wedge also increases the spreading effect on its socket.

Choose print orientation together with the load path and mating faces. Support contact, bridge undersides, elephant foot and the Z seam can impair a good CAD fit. Relief chamfers and small radii must not remove protected seating or locking surfaces. Specific compensation and print preparation are covered in [Fits and retention](fits-and-retention.md) and [Print preparation](../manufacturing/print-preparation.md).

A meaningful comparison needs equal bar dimensions, equal support and load application points, identical print conditions and multiple specimens. An unbroken specimen used as a control reveals the cost of introducing the joint. Alongside maximum load, assess stiffness, permanent deformation, fracture pattern, repeated assembly and sustained-load behaviour.

## Sources and limits of the first collection

All three videos are by **NeedItMakeIt**. The analysis used transcripts and selected CAD and assembly frames. Our geometries are independent teaching models, not dimensionally identical copies of the original Fusion files.

- [Strong 3D Printed Connections on BIG parts](https://www.youtube.com/watch?v=fSISiR5XIbk), 20 January 2024: stopped scarf and opposing wedges. The bending demonstration compares different joints with geometry and supports that are not fully identical. The lap joint assembled with screws and inserts is also not a purely printed joint.
- [Modernizing the best Woodworking Joint to use for 3D Printing](https://www.youtube.com/watch?v=zI8OgRRF5d8), 20 April 2024: straight, tapered, scarf, curved and conical curved dovetails. The more complex conical form is also an experiment in the video.
- [Adapting the BEST Woodworking Joints for 3D Printing](https://www.youtube.com/watch?v=WY8yd191qVE), 4 May 2024: Echo-Lock and Drop-Lock. Hand demonstrations and design arguments do not replace a comparable strength test. The wedge-force measurement in the video is not a load test of these finished joints.

No load figure from these videos is adopted as the capacity of our reconstructions. Native geometry, numerical assembly checks, physical printing, measured fit and physical load testing each retain a separate status.

## Panels and elastic connectors

The [additional reference review](joints-panels-and-clips.md) adds thin panel seams, separate snap connectors and rim clips from four further videos. A through-thickness panel joint needs checks in both bending directions. A separate clip also needs its own material, print pose, insertion access and release path.

For a snap fit, distinguish free, maximally deflected and seated shapes. The rigid path checker in the first lab does not establish elastic assemblability. Do not dismiss all overlap as a collision or silently permit it: identify the compliant region and justify its strain through an appropriate model or measured coupon.
