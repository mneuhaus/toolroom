---
name: onshape-build-manuals
description: "Create or regenerate illustrated assembly manuals from Onshape CAD using durable native stages, semantic parts, explicit inventory and a maintained rendering recipe. Use for manuals, stage planning, layout or rendering-style work."
---

# Onshape assembly manuals

Read [Shared project and evidence conventions](../../knowledge/core.md). The manual is a reproducible output of CAD source, a build sequence and a maintained illustration recipe. Mechanical redesign, machine operation and public sharing need their own task scope.

Choose the relevant branch:

- [Assembly process and data](references/assembly-process-and-data.md): source hierarchy, purchased units, stage ownership and inventory.
- [Illustration and layout](references/illustration-and-layout.md): page density, insertion arrows, readable hardware and parts trays.
- [Rendering styles and colour](references/rendering-styles-and-colour.md): stable physical roles versus temporary step highlights.
- [Local tooling and examples](references/local-tooling-and-example.md): the existing Onshape adapter, publication verification and PDF transport.

Plan real preassemblies and tool access before polishing pages. Native stages store completed assembly poses; explosion offsets belong to the illustration recipe. Preserve the source master and user additions. Resolve semantic identities after topology changes instead of trusting array order.

Use actual exported CAD geometry and consistent cameras. Inspect every rendered page and reconcile quantities of CAD solids, physical purchased units and handled assembly items. Neither a posed assembly nor an animation proves a collision-free insertion path.

The previous two-steps-per-page layout and instrument palette are editable example defaults. [Layout data](assets/layout-defaults.json) and [render presets](assets/render-style-presets.json) are bundled. They do not constitute a standalone renderer; Sparky and C2 remain the worked implementations documented in [scope](../../docs/scope.md).

The [PDF transport helper](scripts/make_pdf_transport_safe.py) is bundled for generated PDFs on the known UTF-8 upload bridge. Verify downloaded bytes. Skip the encoding workaround on a binary-safe transport.
