---
name: cad-design-system
description: "Define, apply or calibrate a reusable CAD design language with manufacturing and protected-interface profiles. Use for coherent part families, functional colours, edge and label rules, design screening or style coupons."
---

# CAD design system

**Use when** a reusable design language is defined, applied to a part family, or calibrated against a process: edge and label rules, functional colours, profile authorship, design screening and style coupons. **Do not use when** a single part needs a functional fix — function and established constraints outrank generic visual defaults, and a style profile never authorizes moving purchased hardware or a verified interface.

Keep three independent layers apart: design language, manufacturing and protected interfaces. Choose the work first — define a language, apply it, or calibrate a process with a relevant specimen.

## Procedure

1. Read the existing project profiles before writing a new one. Generic profiles are uncalibrated starting points, and different design languages must not have their edge treatments silently combined.
2. For each affected part, keep a ledger of role, physical colour, selected faces, protected geometry, print pose and evidence.
3. Distinguish physical filament colours, CAD appearance and temporary instruction highlights. A graphic grid is not permission to move hardware.
4. Screen candidate geometry from the framework root:

   ```sh
   uv run python skills/cad-design-system/scripts/check_mesh.py part.stl --mfg profiles/manufacturing/fdm-bambu-a1-0.4.yaml --up +Z --json report.json
   uv run python skills/cad-design-system/scripts/check_step.py part.step --mfg profiles/manufacturing/fdm-bambu-a1-0.4.yaml --up +Y --json step-report.json
   ```

   Exit 0 means no findings within the sampled scope, 1 means findings, 2 means incomplete analysis. Preserve raw findings. A declared orientation must itself fit; a hypothetical rotated fit is reported separately. Structural thin solids must not be silently exempted as inlays.
5. The two scripts are one consolidated checker, merging the body, orientation and error handling of one source implementation with the bounded raster and anchored-lip checks of another; see [consolidation decisions](../../docs/history.md). No screen result establishes physical strength or fit.
6. Custom crush-rib, belt-clamp or wheel-stack fits need specimens made from the actual interface. The bundled [style tile](scripts/style_tile.py) is a generic enclosure demonstration.

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [What a check actually establishes](../../knowledge/foundations/verification.md)
- [FDM](../../knowledge/manufacturing/fdm.md), [CNC](../../knowledge/manufacturing/cnc.md), [laser](../../knowledge/manufacturing/laser.md) and [SLA](../../knowledge/manufacturing/sla.md) — the reasoning behind the profile numbers.
- [Mosey](../../knowledge/design/mosey.md) — a worked design language derived from references.
- [Profiles](../../profiles/README.md) — where the data lives.

## References

- [Project integration](references/project-integration.md) — precedence and the per-part decision ledger.
- [Design-language schema](references/design-language-schema.md) — what each field means.
- [Deriving a design language from references](references/reverse-engineering.md)
- [Functional colour](references/functional-colour.md)
- [Checker limits](references/checker-limitations.md) — what the scripts do not see.
- [Tool choice](references/tooling.md) and [adaptation record](references/adaptation.md).
- [Field notes](references/field-notes.md) — additional source context for profile authoring.

## Environment

The manufacturing and design-language profiles this machine defaults to: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml).
