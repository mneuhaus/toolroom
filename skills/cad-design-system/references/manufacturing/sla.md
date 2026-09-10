# SLA / MSLA resin — reasoning behind the profile numbers

For hobby MSLA printers (Elegoo, Anycubic, Phrozen; 35–50 µm pixels, 0.05 mm layers) with
standard or ABS-like resins. Profile: `profiles/manufacturing/sla-generic.yaml`.
In this design system SLA is mostly the "fine parts" process: knob caps, buttons, small
bezels, logos, gears — pieces where FDM's 0.4 mm resolution or layer lines would show.

## Process facts
- Resolution is excellent (features 0.2–0.3 mm), but **everything needs supports** except
  what sits directly on the plate, and every support leaves a mark. Orientation and
  support placement decide the cosmetic result more than any dimension.
- Resin cures with 0.2–0.5 % shrinkage and continues to harden for a day; thin walls warp
  during post-cure if unsupported.
- Parts are isotropic (no layer-bond weakness) but standard resin is brittle; use ABS-like
  or tough resin for anything clipped or screwed.
- Hollow parts trap resin; they need drain holes and get washed inside.
- Surfaces printed at a steep angle to the plate look best; horizontal top faces show
  "pixel" texture, overhanging faces show support scars.

## Numbers and why

| Rule | Value | Why |
|---|---|---|
| min wall, supported | 0.6 | thinner walls warp/crack on removal |
| min wall, free-standing | 1.0 | post-cure warp |
| recommended wall | 1.5–2.0 | rigidity, clean drain |
| min positive feature (pin, text stroke) | 0.3 | pixel size × ~8 |
| min negative feature (slot, gap) | 0.4 | light bleed closes narrower slots |
| min hole | 0.5 (through), 0.8 (blind) | uncured resin plugs smaller holes |
| min text height (debossed 0.2–0.3 deep) | 2.0 | legible at this depth |
| overhang | any, with supports; ≤ 30° from vertical unsupported | supports are assumed |
| hollowing: wall 2.0, drain holes ≥ 2 × Ø2.5 | avoid suction and trapped resin |
| clearance tight / slip / free | 0.1 / 0.2 / 0.3 | dimensionally more accurate than FDM |
| hole compensation | +0.1 (light bleed shrinks holes) | calibrate with exposure test |
| tilt for cosmetic parts | 20–45° | avoids suction, hides supports on the back |

## Design rules
- Put supports on one designated back/hidden face and orient the part so cosmetic faces
  point away from the plate and up.
- Knobs and caps: print with the shaft bore down/angled, supports inside the bore side.
- No fillets under 0.3 mm — they vanish; edge breaks of 0.3–0.5 read as "moulded".
- Text: debossed 0.2–0.3 deep is crisp; embossed 0.3 proud is fine; inlays are possible
  by pausing and painting/filling.
- Screws: self-tapping into tough resin only; prefer press-fit steel pins or inserts set
  with epoxy (heat-set inserts crack resin).
- Snap-fits only in tough/flexible resins, with 2× the FDM safety margins.

## Calibration coupon
A 40 × 40 × 3 plate with holes Ø0.5–3 in 0.25 steps, pins Ø0.3–2, slots 0.2–1.0, text
1.5–3 mm; plus a cube-in-cube fit test with 0.05–0.3 gaps. Adjust exposure until Ø1 hole
and Ø1 pin both hit nominal ± 0.05; set `holes.compensation` to the residual.
