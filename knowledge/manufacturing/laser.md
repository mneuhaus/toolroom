# Laser cutting — reasoning behind the profile numbers

For small diode lasers (5–20 W optical, 450 nm) and desktop CO2 machines cutting 2–6 mm
sheet. Profile: `profiles/manufacturing/laser-diode-3mm.yaml`. Laser parts are 2.5D: a
plate with an outline, holes and engraving. In this design system they are the front
plates, spacers, brackets and stacked "layered" bodies, usually combined with an FDM body.

Contents
1. Process facts
2. Kerf and fits
3. Joints: tab/slot, finger, T-slot, stacking
4. Features, holes, engraving, text
5. Living hinges
6. Materials by laser type
7. Hybrids with printed parts (and the anodised-aluminium label trick)
8. Calibration coupon

## 1. Process facts
- The beam removes a **kerf** of 0.1–0.3 mm; outlines come out smaller, holes larger,
  unless the CAM offsets the path by half the kerf (LightBurn "kerf offset").
- The cut wall is slightly tapered (0.5–2° on thick material) and charred on wood; the
  bottom edge has more burn than the top.
- **Inner corners can be sharp** (unlike CNC) — but sharp inner corners in acrylic are
  crack starters; 0.5 mm radius costs nothing visually.
- Sheet thickness varies: "3 mm" plywood is 2.6–3.2 mm. Slots that must fit the sheet
  need the measured thickness, not the nominal.
- Position accuracy of a decent machine is ±0.1 mm; repeatability better.

## 2. Kerf and fits

| Material (3 mm) | Kerf diode | Kerf CO2 |
|---|---|---|
| birch plywood | 0.15–0.20 | 0.15–0.25 |
| MDF | 0.15–0.20 | 0.20–0.30 |
| cast acrylic (opaque for diode) | 0.15–0.20 | 0.15–0.30 |
| cardboard 2 mm | 0.20 | 0.25 |

Design workflow: model everything **nominal** and let CAM compensate the kerf. Then:

| Fit | Slot width | Use |
|---|---|---|
| press (needs a mallet) | t_measured − 0.05 | permanent boxes, glue optional |
| firm (push by hand, stays) | t_measured + 0.05 | most tab/slot work |
| slip (assembles loose, screws or glue hold it) | t_measured + 0.2 | stacked plates, brackets |

Holes for screws: nominal ISO clearance (M3 → 3.4) works when kerf is compensated;
without compensation cut them 0.1 smaller.

## 3. Joints
- **Tab and slot**: tab length = sheet thickness (flush) or +1 mm (proud, as a style
  feature); tab width ≥ 2 × thickness; at least two tabs per edge; slot width from the fit
  table.
- **Finger joints** (box corners): finger width 2–3 × thickness, odd finger count per edge
  so corners are symmetric; kerf compensation makes them firm without glue in plywood.
- **T-slot with nut**: for M3 in 3 mm sheet: slot 3.4 wide, nut pocket 5.6 wide × 2.6
  deep, pocket starts ≥ 6 mm from the edge; screw length = sheet + 3 + 2.
- **Stacked plates** (2–6 layers through-bolted): the cleanest way to get a "layered"
  design language from a laser; every layer can be a different colour/material; align with
  two Ø3 dowel/screw holes per plate; inner layers carry pockets for PCBs and nuts.
- Glue: wood glue for plywood, solvent (dichloromethane/acrylic cement) for acrylic; CA
  glue fogs acrylic.

## 4. Features, holes, engraving, text
- Minimum structural feature width ≥ 1 × sheet thickness (plywood), ≥ 0.7 × in acrylic;
  decorative features down to 0.5 mm in acrylic, 1 mm in plywood (fibres tear).
- Minimum hole Ø 1.0; below that the hole is a burn mark.
- Distance between adjacent cuts ≥ 1 mm (heat merges them).
- **Vector engraving** (outline, one pass): lines 0.1–0.2 mm wide; text down to 2 mm high.
- **Raster engraving** (filled): text ≥ 3 mm high, strokes ≥ 0.5 mm; on plywood the fill
  chars unevenly — masking tape or a light pass; on black acrylic it gives a crisp frosted
  white — the best laser label there is.
- Engraving depth is cosmetic (0.05–0.3 mm); for deep pockets use CNC.
- Cut order: inner features first, outline last (otherwise the part drops and shifts).

## 5. Living hinges (plywood/MDF 3 mm)
Slot length 20–25 mm, slot spacing 1.5–2.0 mm across, gap between slot ends 1.0 mm (offset
rows), minimum bend radius ≈ 10 × spacing. Acrylic hinges need thinner sheet (2 mm) and
fatigue fast; use them for a one-time bend and glue.

## 6. Materials by laser type

| | Diode 450 nm | CO2 | Fibre (marking) |
|---|---|---|---|
| plywood/MDF ≤ 6 mm | yes (slow beyond 4) | yes | no |
| opaque acrylic | yes (black, dark colours) | yes | no |
| clear/white acrylic | **no** (beam passes through) | yes | no |
| cardboard, leather, felt | yes | yes | no |
| anodised aluminium (marking) | yes, surface bleach | weak | excellent |
| bare metal (cutting) | no | no (thin with O2 on big machines) | thin sheet only |
| PVC, vinyl, polycarbonate | never (chlorine gas / burns) | never | — |

## 7. Hybrids with printed parts
- **Front plate laser, body FDM**: the plate gets the fine cut-outs, sharp corners and
  engraved labels FDM cannot do; the body gets the 3D features. Plate sits on a 0.6–1 mm
  reveal step in the printed body, fixed with the body's insert bosses. Design the reveal
  as a style feature.
- **Anodised aluminium plate, fibre- or diode-marked**: 1–2 mm anodised sheet cut to size
  (or bought as blank), labels marked by laser, edges broken with a file. This is the
  honest way to the "machined instrument" look; a printed body carries it.
- **Acrylic display windows**: 2 mm black or smoked cast acrylic, 0.2 mm slip fit in a
  printed pocket, glued at the corners.
- **Laser-cut TPU/EVA/silicone sheet**: feet and gaskets; cut with the same kerf rules.

## 8. Calibration coupon
Cut a 60 × 40 plate with: a 20 mm square (measure to get kerf: nominal − measured),
holes Ø1–6, slots for the actual sheet with −0.1 … +0.3 steps, a finger-joint corner
pair, text 2/3/4/5 mm vector and raster, a 10 mm living-hinge strip. Record kerf and
the slot fit that came out "firm".
