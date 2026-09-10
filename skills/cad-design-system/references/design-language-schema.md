# Design-language profile — schema and decision guide

A design language is the set of decisions that stay constant across every object of a
family, so that two parts designed months apart still look like siblings. The profile
stores those decisions as values a CAD script can consume. It deliberately contains no
manufacturing candidates — those live in the manufacturing profile. Explicit user constraints, protected interfaces and calibrated evidence take precedence over uncalibrated defaults.

Contents
1. Field reference (what each key means, how to choose it)
2. Three archetypes as calibration points
3. Decision questionnaire (for writing a profile from scratch)
4. Style tile specification
5. Writing good `intent` and `anti_patterns`

---

## 1. Field reference

All lengths in mm. Every value may carry a confidence tag in a comment:
`# observed | measured | estimated | derived`.

### `meta`
- `id` — slug, used in file names and reports.
- `name` — one line a human recognises.
- `intent` — three sentences: what the language is for, what it should feel like, what it
  refuses. Read first by any generator; more influential than the numbers.
- `references` — products, photos, brands used to derive it (so later edits know the source).

### `edges` — the single most identity-defining axis
- `policy`: `sharp | broken | chamfer | fillet | mixed`
  - *sharp*: as-modelled edges (only credible on laser-cut/machined parts; FDM always rounds a little).
  - *broken*: tiny uniform edge break 0.3–0.6 mm, reads as precise/machined. Chamfer or fillet, doesn't matter visually at that size — choose chamfer for FDM (prints cleaner on the underside).
  - *chamfer*: a visible, deliberate 45° (or other) facet, 0.6–3 mm. Reads technical, "instrument", Braun/TE.
  - *fillet*: rounded, 2–20 mm. Reads soft, consumer, hand-friendly. Size decides between "pebble" (≥ 8) and "toolish" (≤ 3).
  - *mixed*: e.g. filleted plan-view corners with chamfered top edges. Write the rule, not just the word.
- `edge_treatment`: `{type, size, angle}` — the default treatment for outer edges.
- `outer_corner_radius` — radius of the vertical corners in plan view (the silhouette when viewed from above). Independent of edge treatment: TE bodies have ≈ 2 mm plan corners with ≈ 0.5 mm edge break; a Muji-style body has 8–12 mm plan corners and 3 mm edge fillets.
- `radius_family` — the list of allowed fillet radii, e.g. `[0.5, 1, 2]` or `[3, 6, 12]`.
  A family with a constant ratio (×2 or ×1.618) reads as intentional; random radii read as CAD defaults. `check_step.py` flags radii outside the family (± tolerance).
- `max_radius` — hard ceiling; anything above needs a stated reason.
- `inner_corner_radius` — for pockets and cut-outs; on FDM this can be smaller than outer, on CNC it is ≥ tool radius, on laser it can be 0.
- `bottom_edge` — treatment of the edge that touches the bed; usually a chamfer for elephant foot, sized from the manufacturing profile but declared here because it is visible.

### `proportions`
- `grid` — base module; align new unconstrained graphics and controls to it when useful. Do not move purchased hardware, fits or existing interfaces to satisfy a grid.
- `sub_grid` — for fine alignment (labels, small holes).
- `control_pitch` — centre distance of repeated controls (buttons/keys), a grid multiple.
- `preferred_aspect_ratios` — for plates and footprints; keeps the family consistent.
- `plate_thickness` — thickness of visible plates (front/back), typically 1.6–3.
- `layering` — visible stack from front to back, e.g. `[front_plate, body, back_plate]` or `[shell]` for seamless. Layering gives the product a "constructed" look; a single shell reads "moulded".
- `reveal` — width/depth of the visible gap or step between layers (0.4–1 mm). A deliberate reveal hides tolerance mismatch and is a strong stylistic signal.
- `nesting_offset` — inset of the front plate relative to the body (0 = flush, >0 = stepped).

### `surfaces`
- `finish`: `matte | satin | gloss | textured` for the main body; FDM credibility strongly favours matte.
- `texture_zones` — where texture is allowed (grip areas, feet, TPU parts) and which (`fuzzy_skin`, `knurl`, `ribs {pitch, depth}`).
- `visible_face_rule` — which faces are cosmetic and what print orientation achieves their required finish; also whether a bed-texture face is acceptable as a cosmetic face (textured PEI plate gives a good uniform matte).
- `parting_lines`: `celebrated | hidden` — celebrated means they are turned into reveals, hidden means they coincide with an edge treatment.

### `fasteners`
- `visible`: bool — visible screws are a design feature (instrument/industrial look) or a failure (consumer look). Decide explicitly.
- `type` — e.g. `M3 socket head cap, black`, `M3 countersunk, black`, `M2.5 pan head`.
- `pattern` — rule for placement: `corners inset 2×grid`, `symmetric pairs on centreline`.
- `method` — `heat-set inserts | self-tapping | captive nuts | snap-fit | press-fit pins`.
- `head_treatment` — counterbore/countersink depth rule, whether the head sits flush, proud or sunk by one grid step.

### `color`
- `base` — list of body colours (RAL/Pantone/filament names). 1–2 max.
- `accents` — allowed accent colours.
- `max_colors_per_object` — usually 2–3.
- `accent_rule` — where accents may appear: `functional parts only (caps, buttons, one signature element)` or `none`.
- `semantics` — colour → meaning map, if the language uses one (`record: orange`, `power: red`, `input: blue`). Once defined, never violated within the family.
- `filament_map` — concrete filaments that hit the palette (so the generator can name them).

### `typography`
- `font` — a family or a description (`heavy grotesk, Univers/DIN-like`); for FDM the weight matters more than the face.
- `case` — `lowercase | uppercase | mixed`.
- `method` — `multicolor_inlay | embossed | debossed | engraved | printed_plate`; each has a minimum size in the manufacturing profile.
- `min_height` — candidate cap/x-height target for this style; measure the actual glyph, then calibrate with the chosen process.
- `placement` — rule: `left of control, baseline on grid`, `centred under control`.
- `density` — `sparse (function labels only) | full (every control) | none`.

### `controls` (for devices)
- `knob_cap` — shape, top treatment, colour rule, shaft type.
- `button` — footprint, corner radius, gap to bezel, travel feel (dictates TPU vs rigid).
- `display` — flush vs recessed, bezel colour, corner radius of the window.
- `ports` — exposed connectors: `bare | framed | recessed`.

### `grilles`
- `pattern` — `round_holes {dia, pitch, arrangement} | slots {w, l, pitch} | none`.
- `alignment` — on grid, symmetric, inside a defined field.
- `edge_margin` — distance from field edge to first hole (usually ≥ hole dia).

### `feet_and_handles`
- `feet` — `none | printed bumps | TPU pads | rubber inserts {dia}`.
- `handles` — `none | slot | bar | strap loop`.

### `signature`
- `playfulness` — `none | one element | pervasive`.
- `element_examples` — icon, character, absurd label, colour easter egg.
- `humour_in_labels` — bool.

### `anti_patterns`
List of concrete things that break the look. Written as observations, e.g.
"random radii between 1 and 4 mm on the same body", "gloss filament", "text under 5 mm",
"hidden-screw shell with visible seams". A generator uses this list as a final self-check.

---

## 2. Three archetypes as calibration points

| Axis | Hard-edged instrument (TE/Braun) | Soft consumer (Muji/Apple-ish) | Rugged industrial (Pelican/tool) |
|---|---|---|---|
| edge policy | chamfer 0.6–1 / broken | fillet 3–12 | chamfer 2–4 + fillet 1 |
| plan corner radius | 1–3 | 8–20 | 4–8 |
| radius family | 0.5 / 1 / 2 | 3 / 6 / 12 | 1 / 2 / 4 |
| grid | 5 (2.5) | none visible (proportion-driven) | 10 (5) |
| layering | front/body/back, reveals | single shell, hidden seam | shell + bumpers + ribs |
| fasteners | visible, black, corners | hidden | visible, large, recessed |
| colour | grey/off-white/black + 1–2 semantic accents | monochrome, 1 colour | dark + 1 safety colour |
| labels | lowercase grotesk, inlay | none or minimal | uppercase, debossed |
| surface | matte | satin/matte | textured / fuzzy |
| signature | one playful element | none | none |

Use the columns to sanity-check a new profile: if a value lands in a different column than
the rest, either the language is "mixed" on purpose or the value is wrong.

---

## 3. Decision questionnaire

Answer in order; each answer narrows the next. Ask the user only where the references
don't answer.

1. What is the object family for? (instrument, everyday consumer, workshop, toy, furniture)
2. Hard or soft? Pick the edge policy first — it drives 60 % of the perceived style.
3. Where is the largest radius allowed and how big? (sets `max_radius` and the family)
4. Constructed or moulded? (layering + reveals vs seamless shell)
5. Are screws part of the look? If yes: which head, which colour, which pattern.
6. Base colour(s), accent colour(s), and does colour mean anything?
7. Labels: yes/no, case, method, where.
8. Any repeated controls? Their pitch (→ grid).
9. What must never appear? (→ `anti_patterns`)
10. One thing that makes it *this* family and nothing else? (→ `signature`)

---

## 4. Style tile specification

`scripts/style_tile.py` generates this from a style + manufacturing profile. It is a 60 × 40 mm
block (height ≈ 12 mm) that exhibits, in one print:
- the plan-view corner radius and the outer edge treatment on all top edges,
- the bottom chamfer,
- a 2-layer multicolour label in the style's case and minimum size,
- a grille patch (pattern, pitch, margin) in a 20 × 14 mm field,
- one knob cap (separate body) with the cap treatment and accent colour,
- four screw bosses with the fastener pattern and the profile's insert hole,
- a reveal step if the style has layering.

Print it in the intended filament(s). Judge at arm's length against the reference: edge
crispness, corner size, label legibility, grille rhythm, colour balance. Adjust the profile,
regenerate, reprint. Two iterations usually settle a language; keep the tiles as physical
documentation.

---

## 5. Writing `intent` and `anti_patterns`

Bad intent: "Modern, minimal, high quality." (says nothing a generator can act on)

Good intent: "A small electronic instrument that looks assembled, not moulded: flat plates
on a block, edges broken just enough to feel machined, colour only where a hand or eye
needs it. It refuses softness — no radius above 2 mm — and it never hides a screw."

Bad anti-pattern: "Don't make it ugly."

Good anti-patterns: "gloss filament", "fillets and chamfers mixed on the same edge run",
"accent colour on a structural part", "text below 5 mm or in mixed case", "holes not on the
grid", "a fastener pattern that isn't symmetric", "supports scars on a visible face".
