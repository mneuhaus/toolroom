# Deriving a design language from references

Goal: turn "make it look like X" into a `profiles/design-language/<id>.yaml` whose values a
generator can consume and a style tile can verify. Work axis by axis; write down what was
seen before deciding what it means.

Contents
1. Inputs and what each can give you
2. Measuring from photos
3. Observation procedure per axis (what to look for)
4. Style vs process artefact — the translation table
5. Confidence tags and the write-up
6. Shortcut when only a brand name is given

---

## 1. Inputs

| Input | Gives reliably | Doesn't give |
|---|---|---|
| Orthogonal product photos (front/top/side) | proportions, corner radii, layering, fastener pattern, colour balance | absolute size without a scale reference |
| Detail/macro photos | edge treatment, reveals, texture, label method | overall proportion |
| Spec sheet / store page | overall dimensions, weight, materials | edge sizes |
| Teardown photos (iFixit etc.) | part split, fastener type/size, inserts, PCB standoff pattern | cosmetic decisions |
| Existing STL/STEP | everything geometric (run `check_step.py` for the radius/chamfer/hole inventory) | colour, finish, intent |
| 3D scan of the object | proportions, radii ≥ ~1 mm | radii < 1 mm, texture |
| Brand name + adjectives | intent, colour semantics from prior knowledge | any number — mark all as `estimated` |

Prefer at least one photo with a known object for scale and one macro of an edge.

## 2. Measuring from photos

Pick a known feature in the same photo, at similar depth, and scale everything from it:

| Known feature | Size |
|---|---|
| USB-C receptacle opening | 8.4 × 2.6 mm (with housing ≈ 9 × 3.2) |
| USB-A receptacle | 12.5 × 5 mm (hole ≈ 13.1 × 5.7) |
| 3.5 mm jack hole | 6–6.5 mm |
| Keyboard keycap pitch | 19.05 mm (Choc: 18 × 17) |
| Cherry MX keycap top | ≈ 12.7 × 12.7 mm |
| 6 × 6 mm tact switch | 6 mm body |
| AA / AAA cell | 14.5 × 50.5 / 10.5 × 44.5 mm |
| M3 socket head | 5.5 mm head dia, M3 countersunk ≈ 6 mm |
| Potentiometer knob (small synth) | typically 10–14 mm dia |
| 0.96" OLED window | ≈ 22 × 11 mm; 1.3" ≈ 30 × 15 mm |
| 128 × 64 pixel display, 2.42" | ≈ 57 × 30 mm |

Edge sizes from a photo: a chamfer shows as a uniform bright band along the edge; its
apparent width in pixels × scale ≈ chamfer leg × cos(view angle). A fillet shows as a
graded highlight whose width ≈ 1–1.5 × radius. Plan-view corner radii are read directly
from the top view; if the corner looks "just not sharp", it is 1–2 mm; if you clearly see
an arc, it is ≥ 3 mm.

Reveals: a dark hairline between plates ≈ 0.4–0.8 mm; a visible shadow gap ≈ 1–1.5 mm;
a step you can see the depth of ≈ 2 mm+.

## 3. Observation procedure

Go through the axes of `design-language-schema.md` in this order and note *observation →
inference*:

1. **Silhouette.** Trace the plan-view outline. Rectangle with corners? Radius size?
   Any taper or draft? (Draft ≈ 1° is a moulding artefact, not style.)
2. **Edges.** Chamfer or fillet, size, where it changes (top edges vs bottom, outer vs
   pocket). One treatment everywhere or a hierarchy?
3. **Layering.** Count visible planes front-to-back. Are plates proud, flush or inset? Is
   there a reveal? Does the reveal have a colour (a darker body showing through)?
4. **Fasteners.** Visible? Type, head, colour, count, pattern, inset from edge (measure in
   grid units once you have a grid guess).
5. **Grid.** Measure control pitches and hole spacings; find the largest common module.
   TE-type products: 5 mm-ish; keyboards: 19.05; Eurorack: 5.08 (HP). Then check whether
   plate outlines and label positions also sit on it.
6. **Surface.** Matte/gloss, texture zones, parting lines, sink marks (moulding artefact),
   tool marks (machining artefact), anodising (process).
7. **Colour.** Count colours. Which parts carry the accent — always functional ones (caps,
   buttons, one label) or decorative panels? Is the same colour used for the same function
   across the range? That is a semantic map; write it down as a rule.
8. **Labels.** Case, weight, size relative to control, method (printed, engraved, inlaid,
   embossed). Sparse or full?
9. **Controls.** Cap shapes, top surface treatment, gap to bezel, button footprint and corner
   radius, display recess.
10. **Grilles/feet/handles.** Pattern, pitch, margin; feet material.
11. **Signature.** One thing that is deliberate and non-functional (a character, a colour
    joke, an absurd label). Note if it is one element or everywhere.
12. **Anti-patterns.** Write what the reference visibly avoids (no gradients, no glossy
    parts, no mixed radii, no visible seams …).

## 4. Style vs process artefact — translation table

Everything in the left column is *how the reference was made*. Keep the meaning, replace
the means.

| Reference feature (process) | What it signals | FDM translation | Laser / hybrid translation |
|---|---|---|---|
| Machined anodised aluminium body, 0.5–1 mm broken edges | precision, mass, coolness | matte PLA/ASA, 0.4–0.6 mm chamfer, textured plate for the bottom, 0.12 mm layers on visible curves | fibre-marked anodised aluminium plate on a printed body (the honest version) |
| Injection-moulded ABS shell, 3–8 mm fillets, draft 1° | consumer softness | fillet family 3/6/12, no draft, split shell along a reveal so no support is needed | — |
| Silicone keypad / rubber feet | tactility | TPU 95A caps/feet, printed separately (external spool on AMS lite) | laser-cut EVA/silicone sheet for feet |
| Exposed PCB as the "body" (Pocket Operator) | honesty, kit feel | thin plate 2 mm with exposed screws and a visible "PCB" colour layer; or actually mount the real PCB as a visible layer | laser-cut FR4/acrylic plate as the visible layer |
| Perforated sheet-metal grille, Ø1.5 on 3 mm pitch | technical texture | Ø2.0 on 3.5 pitch (FDM minimum negative feature), or slots 1.5 × 10 | laser-cut plate with the original pitch |
| Chrome / polished parts | luxury | do not imitate; use black or the accent colour | polished acrylic edge (flame or laser polished) |
| Screen-printed labels 3 mm high | density | ≥ 5 mm inlay on FDM, or move labels to a laser-engraved/printed plate | laser engraving handles 2–3 mm text |
| Snap-fit shell, no screws | seamlessness | possible in PETG with cantilever snaps (see fdm.md) but tolerance-sensitive; accept visible screws or a reveal instead | — |
| Sheet-metal fold radius (≈ thickness) | industrial | chamfer 1 × thickness or fillet = thickness on the outside only | bend acrylic on a strip heater, radius ≈ 2 × thickness |
| Living hinge in PP | integrated hinge | TPU strip screwed to both halves or printed pin hinge | living hinge in plywood/acrylic (laser.md) |
| Knurled aluminium knob | grip, precision | printed knob with 60–90 ribs is not knurl; use 12–24 flutes or fuzzy skin on the grip band; SLA for fine knurl | — |

## 5. Confidence tags and the write-up

Tag every value: `observed` (seen clearly), `measured` (from a scaled photo/STEP),
`estimated` (plausible from context), `derived` (translation of a process feature, or a
rule inferred from several observations). Keep the tags in the YAML comments; when a style
tile contradicts a value, the tag tells you how much to trust the original.

Deliver: the YAML, a ten-line rationale (observation → inference per major axis), the list
of open questions for the user, and the style tile command.

## 6. Shortcut when only a brand name is given

Use prior knowledge to fill the archetype column of the schema, mark everything
`estimated`, and ask at most three questions:
1. Which product of theirs is closest to what you mean? (one reference beats the brand average)
2. Hard or soft edges — and how big may the biggest radius be?
3. Base colour and whether colour should carry meaning.
Then generate the style tile; the print answers the rest faster than more questions.
