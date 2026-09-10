---
name: cad-fdm-design
description: Marc's CAD workflow for FDM parts in the requested backend — print orientation, assembly access, fits, one-piece snap latches, house style and slicer verification. Use when designing or revising printable parts, adapters, enclosures or mechanisms, including loose slide-in connections. Includes the build123d + cad-khana scaffold and Onshape-compatible review methods.
---

# cad-fdm-design

Workflow + design doctrine for printed parts. The `cad-khana` skill
documents the tool and its JSON diagnostics; THIS skill says how Marc
wants parts designed. Reference builds: `~/Workspace/cad/opi-cm5-case/`
(slide-in DIN-rail case), `~/Workspace/cad/lego-rack-bar/` (rack +
carriage linear drive), `~/Workspace/cad/unifi-mount/` (all-plastic
clevis joints, printed Tr wing screws, Formschluss doctrine).

## Backend, assembly and project layout

Use the CAD backend requested by the user. The assembly and FDM rules here
also apply to Onshape/Fusion; the build123d scaffold below is only for a
build123d project.

- For screwed adapters, belt drives or close-packed mechanisms, read
  [assembly-review.md](references/assembly-review.md) before choosing access
  cutouts or a split. A clear final pose does not establish assemblability.
- For loose slide-in parts, preload or snap latches, read
  [fit-and-snap-review.md](references/fit-and-snap-review.md). Separate rigid
  location from elastic retention and check the complete mating assembly.
- For a multi-revision project or a requested cleanup, read
  [project-layout.md](references/project-layout.md). Keep persistent cloud IDs
  separate from cache and generated files. Preserve an existing layout unless
  restructuring is part of the task.
- For OrcaSlicer/Bambu Studio preparation, profile inheritance, or a suspicious bridge
  report, read [bambu-preparation.md](references/bambu-preparation.md).

Keep material, fastening method, part count and permitted mating-part changes
as separate constraints. An answer such as “PLA” confirms only the material;
it does not select a screw clamp from a bundled question. Apply the user's
explicit one-piece/tool-free requirement within that scope, without making it
a global prohibition on screws or other materials in future projects.

## Minimal build123d scaffold

One uv project per design under `~/Workspace/cad/<project>/`:

```
pyproject.toml   # copy references/pyproject.toml, adjust the name
<part>.py        # parameters + pure part functions + __main__ export to out/
assembly.py      # khana Assembly + assertions + suggest_orientation + inspect
watch.py         # copy references/watch.py (generic, watches *.py)
out/             # per-part STL/STEP for the slicer
outputs/         # khana JSON diagnostics
```

Start once per session, both in background:
`uv run python -m ocp_vscode` (viewer, port 3939) and `uv run watch.py`
(keep-alive: a reloaded browser tab shows the OCP logo until re-pushed).

Loop: edit → `uv run khana check assembly.py` → read `outputs/*.json`
(mechanism results live under the `assertions` key) → viewer updates
itself. After geometry changes ALWAYS also run `uv run <part>.py` —
khana only writes `outputs/`, the slicer files in `out/` go stale
silently. Log khana paper-cuts to
`~/Workspace/cad/cad-khana/field-notes.md`.

## Review loop (shared IDs instead of screenshot guessing)

Marc reviews in the OCP viewer. For precise feedback both sides use
topology indices: he activates the selection tool (`f`/`e`/`v`
filters), clicks entities, quotes part name + indices; resolve them
with `khana pick assembly.py --part <name> --faces 12,30` — it answers
the actual review questions directly (coplanar? parallel? offset?
edge length/direction). Indices are per pushed snapshot — after a
rebuild push again and re-quote. Screenshots with markings remain the
fallback for "this general area" feedback.

## House style (edge treatment)

Pick the bed face first — "vertical" is defined relative to it. Then:

- vertically rising edges: **R4.2 fillet** (also silences khana's
  sharp-vertical-edge warning);
- all other non-critical edges: **0.42 chamfer** (deburr), run as
  CONTINUOUS rings including corner arcs — a chamfer dead-ending into
  a fillet leaves >45° blend patches;
- dimension-critical edges (reference lengths, mating faces, rack
  teeth, slide ribs) stay **sharp** — function beats style. When the
  full R4.2 would eat a functional wall, use the largest radius that
  keeps ≥1 mm web (khana's `min_wall_at` finds the violation).

## Formschluss doctrine (unifi-mount, iterated with Marc)

Marc rejects on sight: steps, grooves, "Einkerbungen", half-hearted
patterns. The rules that emerged:

- **Adjoining bodies close flush.** Webs run at full hub width; plate
  height = silhouette width; pillar faces tangent-flush or coplanar
  with hex flats. Derive the dimensions from each other
  (`CHEEK_T = (HUB_AF - GAP) / 2` so fork width == hex AF) instead of
  picking two numbers that almost match.
- **Silhouette-defining features are ONE extruded profile**, not a
  stack of unioned boxes: cheek+pillar as a "house" profile, bar+blend+
  hub outline as one sketch. Tangent blends become SKETCH VERTEX
  FILLETS (exact tangency, no boolean lottery); chamfer rings then run
  uninterrupted around the whole profile.
- **Kerben sind Schwachstellen**: every re-entrant junction gets a
  fillet (R2-6). A generic notch-fillet pass (scan concave plane/cyl
  line edges, fillet with radius fallback) beats hand-picking — BUT
  exclude the swing envelope around joint axes (gap slab × hex-corner
  sweep + blend radius), or the pass fills the joint with coves.
- **Edge-treatment ORDER: raw → notch fillets → blends → ONE deburr
  pass at the end.** Never pre-chamfer pieces that later union — the
  rings get severed at every seam and chamfers dead-end into later
  geometry (Marc spotted every single case in the viewer).
- **Patterns are committed, not token.** One row of small hex cutouts
  reads "halbherzig"; a true staggered honeycomb (row pitch = 0.866 ×
  col pitch, ONE lattice anchored at the part centre — per-row
  re-centering breaks the stagger and pinches walls) reads intentional.
- **Hand-adjustable plastic knobs (unifi-mount pattern):** prefer printed screws
  where their size, load and access permit. Preserve specified metal fasteners
  and compact metal pull-screw tensioners when the task calls for them. Tr12x3 internal /
  Tr11x3 external (bd_warehouse `MetricTrapezoidalThread`) is
  print-tolerant by the size mismatch. Nut bore teardropped like any
  horizontal bore; after fusing the internal thread, re-cut the apex
  with a CENTRE-to-apex kite (a triangle-only cutter leaves a thread
  band bridging the opening — "hängt in der Luft"). Wing screw: flat
  stretched-hexagon wing, constant thickness = 2×flat distance, prints
  LYING (layers along the axis); ~2×90° engagement is plenty.
- **Friction joints bite via micro ridges**: 8 radial ridges 0.8 × 0.2
  proud on the fork clamp faces (added LAST, after fillet/deburr
  passes, excluded from wall checks via a `ridges=False` variant).

## build123d / OCC gotchas (cost real hours)

- **Edges from OCC ancestor maps have no `topo_parent`** —
  `fillet`/`chamfer` raise "Nothing to chamfer", and inside a
  try/except loop that's a SILENT NO-OP. Iterate `part.edges()` (they
  carry the parent) and use `TopExp.MapShapesAndAncestors_s` only for
  face adjacency. After adding any fillet pass, VERIFY it did
  something (face_count, or khana's rim warning count).
- **Tangent-contact and coplanar booleans are a lottery**: one band
  fuses, the mirror one stays a floating solid. Give every glued-on
  body ≥1 mm of overlap skirt into its neighbour. khana's
  `floating_solids` warning catches the failures.
- **Batch chamfer can SEGFAULT OCC** on tangent-rich parts (concave
  cylinder cuts). Keep the generic deburr pass opt-out per part and
  fall back to local edge selections there.
- **Concave-vs-convex edge classification**: the bisector probe is air
  for both; the diagonal quadrant `mid + (n1 - n2)·ε` is solid only
  for concave corners.
- **`Part + Part` sometimes returns Solid/ShapeList** (algebra
  quirks); normalise before `.moved()` / khana hand-off.
- 120°-open junctions (hex flank meets web) are still notches — don't
  filter notch candidates by "sharp interior" angle.

## FDM rules (record which were physically tested)

- **Every thin vertical feature on a plate gets a base fillet/haunch.**
  Screw standoffs: full-height concave flare (radius = post height).
  Walls/pedestals: haunches both sides up to standoff height. Rims: as
  large as the wall height allows.
- **Build fillets as geometry when OCC would choke**: posts =
  `Cylinder(R+r, h) - Torus(R+r, r)`; straight walls = `Box(r,L,r) -
  Cylinder(r)`; then `& footprint` to clip overshoot at plate edges.
- **Slide-in beats snap-on** for box+tray: E/W/S half-round ridge
  (0.6 proud) / groove (0.7 deep, profile r0.55), entry wall opened
  full-width so grooves exit through the face.
- **End-of-travel detent: stay in the profile family.** A short ridge
  RELIEF on the tray (R0.8 cylinder along the ridge axis, 45° ramped
  ends, ~0.6 proud of the crest) drops into a matching groove
  DEEPENING in the hood (R0.8 × 2.4, 0.4 deeper, ramped); riding
  squeeze ~0.3. Do NOT use spheres or radial pins against the small
  round ridge bulge — five variants all met it tangentially and left
  feather slivers (its flat band is only ~0.6 wide). Prisms sharing
  the groove axis cross every surface transversally, never tangent.
- **No feather edges, ever.** Anything tapering below ~0.5 at a
  tangent (snap lips over cylinders, chamfers wrapping arcs into
  walls, hole cutters poking past inner faces, ribs crossing hole
  mouths) prints as fussel. Prefer open U-troughs (bore = Ø + 0.2),
  flush-ended cutters, ribs clear of holes.
- **Lateral protrusions on end-printed parts** (axle towers): build as
  45° trapezoid profiles, not boxes + step chamfers.
- **Horizontal bores that must fit pins/axles: teardrop them** (45°
  apex in the print-up direction) — round bores sag 0.1-0.2 and bind.
  Vertical bores print 0.1-0.3 undersize. Technic pin holes also need
  Ø6.2 × 0.9 counterbores on the outer face or beams never sit flush.
- **Clearances**: 0.2/side sliding fits; 0.1 at rib line-contacts
  (cavity +0.3/side, ribs 0.2 proud, RIB_W ≥ 1.6). PCB hole grids from
  datasheets are suspect — the first print measures truth.
- **PLA under preload:** account for relaxation, layer direction and peak
  insertion strain. A requested one-piece PLA latch can use a long, rounded
  flexure to retain a part against rigid stops; do not promise lasting zero
  play from nominal clearance or a beam estimate. Verify insertion, release
  and retained fit physically; see the fit-and-snap reference. Lubrication
  choices for slides/gears do not automatically apply to retaining contacts.
- **Anti-racking**: guide length ≥ 1.5-2× the lever arm of the applied
  force (64 mm = 8 Technic modules worked); put motors flat alongside
  the axis, bear axles in BOTH cheeks.

## Mass-production rules (Slant 3D doctrine)

- Chamfer under every protrusion instead of accepting an overhang.
- Simple, small first layer; no text/spikes on layer 1.
- Removing material is CNC thinking — ADD volume, let infill hollow;
  sealed internal voids are a modeling-error smell (khana warns).
- Texture hides layer lines on cosmetic faces; don't buy resolution.
- **Compliance beats precision**: grip via 3-4 thin flexible fins
  (0.8-1.2, deflect 0.2-0.4) instead of tight bores — they absorb the
  designed tolerance band. These are example dimensions, not a material limit;
  check actual printer variation and insertion strain. Slide ribs use the same
  idea for rails.
- Snap-fit types: cantilever (lids), annular (caps), torsion (levers);
  orient the loaded length/root to avoid interlayer peeling. A groove/ridge
  slide-in can print well; choose its detent to match the existing profile and
  retaining force direction, rather than defaulting to a sphere.

## Validation patterns (khana)

- `suggest_orientation()` BEFORE picking `FDM(up_axis=...)` — it ranks
  by true support demand (small bores + short anchored bridges exempt)
  and surfaces the "zero support but sagging bores" vs "clean bores
  but real supports" trade-off. Don't trust your own
  constant-cross-section claim; it caught 53 mm² of tower ceiling.
- Extra assembly instances check representative motion poses: a mid-slide tray, a
  just-entering tray. A designed elastic squeeze is
  `assert_interference(..., reason=...)` — it alarms when the feature
  silently disappears. Limit the expected contact to the intended bodies and
  region, then check a defensible deflected state. Keep the rest of the assembly
  subject to collision checks; an interference exemption alone proves no fit.
- Waivers: tight and documented. Non-bore micro-bridges (snap flanks)
  → `overhang_max_deg=91`; chamfer-wrap-on-arc in the elephant-foot
  zone → 48; LEGO module-1 teeth → `wall_min_mm=0.8`. Never waive
  broadly to silence a check you haven't located (`min_wall_at`!).
- The sharp-vertical-edge warning is noisy on intentional micro
  features (slide ribs) — read with judgment.

## Ecosystem (check before hand-rolling)

Curated index: github.com/phillipthelen/awesome-build123d and
build123d docs "External Tools & Libraries". Worth reaching for:

- **bd_warehouse** (bundled with khana): fasteners, modeled Tr/ISO/Acme
  threads, bearings, V-slot — see khana's `standard_parts.md`.
- **py_gearworks**: parametric gears (before hand-rolling involutes);
  **gridfinity_build123d** / **gfthings**: gridfinity bins+grids;
  **bd_vslot**: V-slot rails; **bd_beams_and_bars**: standard sections.
- **yet-another-cad-viewer (yacv)**: browser viewer on glTF with
  hot-reload server AND fully static deployment — khana already
  exports GLB, so yacv is the way to hand Marc a standalone shareable
  viewer page (ocp_vscode stays the live-iteration viewer).
- **PartCAD**: package manager/registry for parts — watch item, not
  adopted yet.

## LEGO interface dimensions

Module 1 gears: pitch radius = teeth/2 mm (8z: 4, 24z 3648: 12, tip Ø
25.4). Racks: pitch 3.2 (10 teeth / 4 studs), PA 20°, tooth height
~2.1, tip width ~0.85. Gear disc ~3.7 thick → guide channels 4.2.
Axle: 4.72 across → free bore Ø4.9 (teardropped). Pin holes: Ø4.9 +
Ø6.2×0.9 counterbore, 8 mm grid, beam thickness 7.4 (pins seat flush
in a 7.4 wall). Gear mesh: axle height = rack pitch line + pitch
radius.
