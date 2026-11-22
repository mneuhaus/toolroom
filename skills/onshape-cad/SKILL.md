---
name: onshape-cad
description: "Construct or revise native Onshape geometry with FeatureScript, preserve user features and stable assembly references, and verify the affected interfaces. Use for native Onshape design, retrofit or variant work."
---

# Onshape CAD

**Use when** building or revising native Onshape geometry: FeatureScript features, retrofits, shared variants, and verifying the interfaces they touch. **Do not use when** the question is transport, session health or metering — that is [onshape-bridge](../onshape-bridge/SKILL.md) — or when a local file can answer it without opening a document.

## Procedure

1. Read the project's source and assembly state first. Capture the live native features and the source reference before editing an existing Feature Studio.
2. Preserve user finishing features and downstream dependencies. A microversion-pinned custom feature needs its consumed namespace updated and verified after a source upload.
3. For adapters and shared variants, align mounting axes and seats before detailing. Select functional parts semantically, never by their position in an API array.
4. Verify part count, bounds, changed contours and protected interfaces. Volume is a change signal, not a shape identity.
5. After topology changes, reacquire queries and inspect all affected assembly references; repair only the broken ones. Verify nested leaf poses after applying assembly transforms.
6. For new fastenings or changed access, complete the [assembly review before delivery](../../knowledge/construction/assembly-review.md#review-before-delivery), including the actual sequence and tool use.
7. Keep source revisions, exports and the actual checks together. This task does not require changing unrelated documents.

Style is an explicit profile choice. The historical workshop edge family is available as [workshop-042](../../profiles/design-language/workshop-042.yaml); it never overrides functional edges or load paths.

## Knowledge

- [Shared project and evidence conventions](../../knowledge/foundations/core.md)
- [What a check actually establishes](../../knowledge/foundations/verification.md)
- [Assembly, access and load-path review](../../knowledge/construction/assembly-review.md)
- [Reusable construction patterns](../../knowledge/construction/patterns.md)
- [CAD project files and revisions](../../knowledge/workflow/project-layout.md)

## References

- [Field notes](references/field-notes.md) — FeatureScript operations, coordinate bases, Boolean pitfalls. The project recipes, dimensions, bed sizes and style values in them are examples; the current project's profiles govern.
- [Revision workflow](references/revision-workflow.md) — source uploads, custom-feature namespaces.
- [Retrofit and variants](references/retrofit-and-variants.md) — adapters on existing interfaces, symmetric siblings.
- [Sharing views](references/sharing-views.md) — only when a review artifact is required.

## Environment

The transport, endpoint and defaults for this machine are in [`profiles/environment/local-workstation.yaml`](../../profiles/environment/local-workstation.yaml). Use [onshape-bridge](../onshape-bridge/SKILL.md) when the configured transport is the local session bridge.
