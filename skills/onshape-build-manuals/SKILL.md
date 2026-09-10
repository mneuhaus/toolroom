---
name: onshape-build-manuals
description: "Create or regenerate illustrated assembly manuals from Onshape CAD using durable native stages, semantic parts, explicit inventory and a maintained rendering recipe. Use for manuals, stage planning, layout or rendering-style work."
---

# Onshape assembly manuals

**Use when** an illustrated assembly manual is created or regenerated from Onshape CAD: durable native stages, semantic part identities, explicit inventory, page layout and the maintained rendering recipe. **Do not use when** the task is mechanical redesign, machine operation or public sharing — each needs its own scope.

The manual is a reproducible output of three things: CAD source, a build sequence and an illustration recipe.

## Procedure

1. Plan real preassemblies and tool access before polishing pages.
2. Keep native stages for completed assembly poses; explosion offsets belong to the illustration recipe, not to the CAD.
3. Preserve the source master and the user's additions. Resolve semantic identities after topology changes instead of trusting array order.
4. Render from actual exported CAD geometry with consistent cameras. Inspect every rendered page.
5. Reconcile quantities across CAD solids, physical purchased units and handled assembly items.
6. Neither a posed assembly nor an animation proves a collision-free insertion path.
7. For a generated PDF on the known UTF-8 upload bridge, use the [PDF transport helper](scripts/make_pdf_transport_safe.py) and verify the downloaded bytes. Skip the encoding workaround on a binary-safe transport.

The previous two-steps-per-page layout and instrument palette are editable example defaults: [layout data](assets/layout-defaults.json) and [render presets](assets/render-style-presets.json) are bundled but do not constitute a standalone renderer. The worked implementations are documented in [scope](../../docs/scope.md).

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [What a check actually establishes](../../knowledge/foundations/verification.md)
- [Assembly, access and load-path review](../../knowledge/construction/assembly-review.md)

## References

- [Assembly process and data](references/assembly-process-and-data.md) — source hierarchy, purchased units, stage ownership, inventory.
- [Illustration and layout](references/illustration-and-layout.md) — page density, insertion arrows, readable hardware, parts trays.
- [Rendering styles and colour](references/rendering-styles-and-colour.md) — stable physical roles versus temporary step highlights.
- [Local tooling and examples](references/local-tooling-and-example.md) — the CAD adapter, publication verification and PDF transport.
- [Field notes](references/field-notes.md) — the imported manual-production notes; layouts and palettes in them are examples.

## Environment

Transport endpoint and defaults for rendering and publishing from this machine: [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml), driven through [onshape-bridge](../onshape-bridge/SKILL.md).
