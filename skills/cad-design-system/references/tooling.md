# Tool choice

Use the project's established native CAD backend and access conventions. Preserve parametric source, stable part IDs and assembly references. Cloud interaction should use the approved connector or local bridge specified by that project; do not invent authentication or API endpoints.

Use Onshape/FeatureScript for native design changes when that is the source of truth. Use Fusion or another available native solid kernel for imported-body and assembly comparisons in isolated scratch documents. A tessellated mesh is not an editable parametric CAD source.

The bundled build123d script is an enclosure demonstration. Make a project-specific coupon from the actual feature definition for custom screw holes, belt teeth, mating registers or other functional interfaces.

Use exact CAD meshes in Blender for polished product views or a manual. The basic matplotlib renderer is useful for orthographic geometry inspection; it is not a dimensioned drawing or a photoreal renderer. Record camera, material and source geometry separately.

Use the installed slicer and the actual machine/material presets for paths and supports. Review the exported model and generated paths. Generating a slice does not require sending a print job.

For assembly manuals, use the separate onshape-build-manuals workflow. Keep product appearance, per-step highlighting and render style distinct.
