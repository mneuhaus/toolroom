# FDM profile guidance

Treat every generic value as a calibration candidate. A line-width multiple is a useful design aid, not a universal strength rule or a ban on gap fill. A 0.4 mm nozzle does not establish load capacity; section shape, material, print orientation, walls, infill and temperature all matter.

The supplied 0.84 / 1.26 mm thresholds are useful for finding small geometric details. They are not minimum safe carriage walls. Inspect the continuous load path and real interfaces in native CAD, and test a specimen where needed.

Declare the build orientation and actual usable plate. A nominal machine volume differs from a user-imposed plate boundary. Include support, brim and purge geometry in the final arrangement check.

An overhang angle is measured from vertical in these profiles. The 45-degree angle and 20 mm bridge span are uncalibrated search limits. The classifier cannot decide adhesion, cooling, support contact or surface quality. Existing deliberately supported mating faces can be the correct choice. The strength and surface consequences of a chosen pose are collected in [print orientation](print-orientation.md).

Retain approved screw contours and fits. A generic insert table, plain pilot-hole diameter or hole compensation cannot replace a purchased insert's geometry or a custom crush-rib feature. State whether a clearance is radial, diametral or per side before using it.

A sketch text box, font em size, x-height and physical stroke width are different quantities. Check actual glyph geometry and sliced strokes; test small labels. A 0.3 mm engraving may cross one or two layers at a 0.2 mm layer height depending on orientation and slicing phase. Do not promise legibility from the nominal box size.

Use the current machine/material preset as evidence of intent, not as proof of a successful physical print. Record coupon material, nozzle, layer height, orientation and measured outcomes with a date before updating calibrated values.
