# CNC milling (small hobby router) — reasoning behind the profile numbers

For desktop routers with 3.175 mm (1/8") shank tooling cutting plastics, plywood,
aluminium plate and FR4. Profile: `profiles/manufacturing/cnc-small-hobby.yaml`.
In this design system CNC is the process for plates with pockets, aluminium front panels,
and anything that must be flat and dimensionally exact.

## Process facts
- **Inner corners have a radius ≥ tool radius.** A 3.175 mm end mill leaves R ≥ 1.6 in every
  pocket corner. If a square part must fit, use a dog-bone or T-bone relief; if a square
  corner must *look* square, use a smaller tool for a corner pass (1 mm end mill → R0.5).
- Outer corners can be sharp.
- Pocket depth per tool ≤ 3 × tool diameter (chatter, deflection); through-cuts in
  6 mm plate with a 3 mm tool are fine in plastic/wood, marginal in aluminium.
- Parts need holding: tabs, double-sided tape, clamps outside the outline, or a vacuum.
  Leave 3 mm of stock around the outline for clamps.
- Surface finish depends on step-over; a 0.1 mm finishing pass gives a "machined" look
  with visible tool paths — that is a texture, decide whether the style wants it.
- Accuracy ±0.05–0.1 mm on a rigid machine; ±0.2 on light gantries.

## Numbers and why

| Rule | Value | Why |
|---|---|---|
| min wall (plastic/wood) | 1.5–2.0 | chatter, breakout |
| min wall (aluminium) | 1.0 | plate is stiff |
| inner corner radius | tool radius + 0.1 | tool cannot be smaller |
| min slot width | tool Ø + 0.1 | one pass |
| pocket depth | ≤ 3 × tool Ø per tool | deflection |
| clearance for fitted parts | 0.05–0.1 | machined faces are accurate |
| engraving (V-bit 60°/90°) | text ≥ 2 mm, depth 0.1–0.3 | crisp labels in aluminium/acrylic |
| hole diameters | drill or interpolate; interpolated holes are +0.05 accurate | |

## Design rules
- Model the corner relief (dog-bone Ø = tool Ø, or radius ≥ tool radius) in CAD; do not
  leave it to CAM.
- Keep a consistent tool list per project (e.g. 3.175 mm 2-flute, 1 mm end mill, 90° V-bit)
  and derive every inner radius from it.
- Aluminium front plates: 2 mm 5754/6061, chamfer edges 0.3–0.5 with a chamfer bit —
  this is the real "instrument" edge that FDM can only imitate.
- FR4 isolation routing: separate profile; the same corner rules apply, plus 0.2 mm
  minimum isolation width.

## Calibration coupon
Mill a 40 × 40 plate with a 20 mm square pocket and boss (measure both for tool
runout/diameter), holes Ø3–6 interpolated, slots at tool Ø + 0.0/0.1/0.2, and a V-bit
text line at 2/3/4 mm. Record the effective tool diameter and the slot fit.
