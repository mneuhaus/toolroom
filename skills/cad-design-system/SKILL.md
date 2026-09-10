---
name: cad-design-system
description: "Define, apply or calibrate a reusable CAD design language with manufacturing and protected-interface profiles. Use for coherent part families, functional colours, edge and label rules, design screening or style coupons."
---

# CAD design system

Keep three independent layers: design language, manufacturing and protected interfaces. Read [Shared project and evidence conventions](../../knowledge/core.md) and the existing project profiles. Function and established constraints take precedence over generic visual defaults.

Choose the work: define a language, apply it to the requested part family, or calibrate a process with a relevant specimen. Read [project integration](references/project-integration.md), [functional colour](references/functional-colour.md) and [checker limitations](references/checker-limitations.md) as applicable.

Profiles live in the framework's [profiles directory](../../profiles/README.md). Generic profiles are uncalibrated starting points. The [workshop-042](../../profiles/design-language/workshop-042.yaml) and instrument-style profiles describe different design languages. Do not automatically combine their edge treatments.

For each affected part, retain a ledger of role, physical colour, selected faces, protected geometry, print pose and evidence. Distinguish physical filament colours, CAD appearance and temporary instruction highlights. Never treat a graphic grid as permission to move purchased hardware or a verified interface.

## Screening

Run commands from the framework root:

```sh
uv run python skills/cad-design-system/scripts/check_mesh.py part.stl --mfg profiles/manufacturing/fdm-bambu-a1-0.4.yaml --up +Z --json report.json
uv run python skills/cad-design-system/scripts/check_step.py part.step --mfg profiles/manufacturing/fdm-bambu-a1-0.4.yaml --up +Y --json step-report.json
```

Exit 0 means no findings within sampled scope; 1 means findings; 2 means incomplete analysis. Preserve raw findings. A declared orientation must itself fit; a hypothetical rotated fit is reported separately. Structural thin solids must not be silently exempted as inlays.

The shared checker combines Sparky's body/orientation/error handling with Distributor's bounded raster and anchored-lip checks. See [consolidation decisions](../../docs/consolidation.md). No screen result establishes physical strength or fit.

The supplied [style tile](scripts/style_tile.py) is a generic enclosure demonstration. Custom crush-rib, belt-clamp or wheel-stack fits require specimens made from the actual interface. Read [historical detailed guidance](references/source-guide.md) for additional source context.
