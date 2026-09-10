---
name: onshape-cad
description: "Construct or revise native Onshape geometry with FeatureScript, preserve user features and stable assembly references, and verify the affected interfaces. Use for native Onshape design, retrofit or variant work."
---

# Onshape CAD

Read [Shared project and evidence conventions](../../knowledge/core.md) and the current project's source/assembly state. Use [onshape-bridge](../onshape-bridge/SKILL.md) when the configured transport is the local session bridge.

## Native design and revision

Read [FeatureScript and geometry field notes](references/source-guide.md) for backend-specific operations, coordinate bases and Boolean pitfalls. Those notes contain historical project recipes; dimensions, bed sizes and style values are examples, governed by the current project's profiles.

Before editing an existing Feature Studio, capture the live native features and source reference. Preserve user finishing features and downstream dependencies. A microversion-pinned custom feature needs its consumed namespace updated and verified after a source upload. See [revision workflow](references/revision-workflow.md).

For adapters and shared variants, align mounting axes and seats first; read [retrofit and variants](references/retrofit-and-variants.md) and [assembly review](../../knowledge/assembly-review.md). Select functional parts semantically, not by their position in an API array.

Verify part count, bounds, changed contours and protected interfaces. Volume is a useful change signal, not a shape identity. After topology changes, reacquire queries and inspect all affected assembly references; repair only broken references. Verify nested leaf poses after applying assembly transforms.

Style is an explicit profile choice. The historical workshop edge family is available as [workshop-042](../../profiles/design-language/workshop-042.yaml); it does not override functional edges or load paths.

Keep source revisions, exports and actual checks together. Use [sharing notes](references/sharing-views.md) only when a review artifact is required. This task does not require changing unrelated documents.
