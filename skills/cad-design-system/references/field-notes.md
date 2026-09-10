> Field notes imported from the previously installed skill on 2026-09-10. Project-specific numbers, personal defaults and historical runtime assumptions are examples, not rules. The entrypoint, the knowledge base and the environment profile (`../../../profiles/environment/local-workstation.yaml`) govern current use.


# CAD design system

Keep three independent layers: **design language**, **manufacturing**, and **protected interfaces**. Product function and the user's established constraints take precedence over generic style or process defaults. All supplied numeric profiles are starting points unless their provenance records actual calibration.

## Choose the work

- **Apply:** translate an agreed visual language into selected native CAD features and assess the whole requested part family.
- **Define:** extract explicit colour roles, edge sizes, graphics and process limits into versioned project profiles. Separate measured facts, current CAD values and proposals.
- **Calibrate:** make small relevant specimens; record actual material, orientation, slicer settings and measurements before changing a fit.

Read project conventions, current release notes and existing profiles first. Reuse approved geometry, tools and permissions. Resolve routine implementation choices without introducing an approval gate. Work in the requested scope; a style reference does not itself authorize changing mechanism interfaces or adding decorative hardware.

## Establish the three profiles

1. Record a design-language ID, palette with meanings, edge families and face selection rules, label sizes, and exceptions. Keep hardware colours truthful and distinguish physical colour from temporary instruction highlights.
2. Record the actual process, usable bed, nozzle, material, layer height, orientation and support strategy. Mark unmeasured hole compensation, text strokes and bridge limits as calibration candidates.
3. Record protected mounting patterns, fits, motion envelopes, wrench access, load paths and purchased hardware. A 5 mm graphic grid must not move a 31 mm motor pattern or a verified interface.

Use `profiles/design-language/te-like.yaml` for a restrained instrument-style starting point and `profiles/manufacturing/fdm-bambu-a1-0.4.yaml` only when that machine/nozzle is applicable. The other supplied profiles are uncalibrated examples; read them only for the relevant process. Do not copy their dimensions into an existing mechanism automatically. See `references/project-integration.md` for the schema and precedence.

## Apply to the complete scope

Create a per-part ledger: identity, role/colour, selected surfaces, current change, protected interfaces, print orientation and evidence. Keep source parameters reusable. Apply chamfers to deliberate exposed edges; preserve bearing seats, belt teeth, locating faces, joint sections and stress-relief fillets. Plain millimetre dimensions are appropriate for purchased hardware and established fits.

Do not reduce structural walls to a generic enclosure minimum. Treat a broken print as a load-path problem; connectivity, continuous sections and interface access need inspection before cosmetic treatment. Slicer wall count cannot reconnect separated solids.

For TE-inspired work, follow `references/functional-colour.md`. Colour encodes the project's function: an audio product's orange recording key does not assign the same meaning to a laser carriage. Preserve conventional notation such as M3 and GT2 even when labels use lowercase.

## Verify with layered evidence

Use native solids and assembly/motion checks for geometry and interfaces. Use the scripts as **screening**, then inspect actual sliced paths and a physical specimen where needed. Never substitute an attractive render or a checker result for load or fit testing.

```bash
uv run --with numpy --with scipy --with trimesh --with pyyaml --with rtree python scripts/check_mesh.py part.stl --mfg project-fdm.yaml --up +Z --json mesh-check.json
uv run --with build123d --with numpy --with scipy --with trimesh --with pyyaml --with rtree python scripts/check_step.py part.step --mfg project-fdm.yaml --style project-style.yaml --up +Y --json step-check.json
```

Paths above are relative to this skill directory. Point to the real installed/source directory when invoking them. Each mesh should represent one intended printed body in a declared orientation. Exit 0 means no findings within the configured screening scope; 1 means findings require review; 2 means incomplete analysis. Preserve raw findings and explicit dispositions; do not relabel failures as passing or suppress unresolved analysis errors.

Mesh thickness uses deterministic sampling and excludes some sharp-edge samples. Small bridges, ribs or lettering may escape detection. Overhang classification does not know the sliced support geometry. STEP cylindrical/chamfer recognition cannot reliably distinguish functional features from styling. Inspect flagged coordinates in the native model. See `references/checker-limitations.md`.

Thin solids are **not automatically inlays**. Designate an actual STEP colour layer with `--inlay-solid INDEX --inlay-max-height HEIGHT`; the height is measured along `--up`. This skips wall sampling for that designated layer only. Do not use it for thin structural plates. Preserve assembled coordinates for multimaterial inlays.

## Coupons and visuals

`style_tile.py` makes the supplied **generic enclosure demonstration**, including an insert-based tile, a knob and colour inlay. It is not a mechanical prototype of the user's assembly. It must not be used to claim verification of a custom crush-rib hole, belt clamp or wheel stack. Build a dedicated specimen from actual native feature geometry for those interfaces.

`render_views.py` creates basic technical views of actual meshes. For exact assemblies, reuse the native CAD/Blender pipeline; for assembly guides and comparative rendering use `onshape-build-manuals`. Keep geometry, camera, crop and lighting matched in before/after comparisons. Any generative concept image must be labelled as an illustration rather than a dimensional check.

## Deliver and maintain

Deliver profiles, an applied per-part report and any actual changed CAD/coupons. State the important adopted rules, project exceptions, completed checks and remaining physical measurements. Keep unmodified supplied assets as reference with a source manifest. Archive previous releases instead of silently rewriting them. Add the profile/check commands to the project workflow so the system is used on the next revision.

This adapted skill originates from the user's CAD design-system package supplied on 2026-09-09. See `references/adaptation.md` for the changes and provenance.
