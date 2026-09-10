# Checker limits

The supplied tools were adapted to stop reporting success after an analysis failure.

- `analysis_complete` reports whether configured algorithmic checks executed; `clean` additionally requires no screening findings. Neither is a physical guarantee.
- Mesh reports include winding, positive closed volume, connected components, exact oriented dimensions and bed height. Scene formats should be exported as individual bodies for unambiguous per-part checks.
- Thickness sampling is probabilistic geometric coverage with a fixed seed, not a minimum-section proof. It excludes some convex-edge samples. Invalid rays and execution errors are reported; fewer than 95% valid rays makes analysis incomplete.
- The minimum sampled distance can be a bevel, engraved glyph, hole rim or tooth tip. Map it to native coordinates and examine the section before changing geometry.
- The overhang classifier inspects model faces, not support paths, adhesion, cooling, layer order or strength. A bridge or narrow lip is a candidate requiring validation; unknown geometric classification is not proof of support.
- STEP cylinders, strip widths and outer edges are heuristic candidates. A small cylindrical tooth relief is not necessarily a cosmetic fillet. The script cannot infer face intent.
- Inlay exemptions must be explicit. No thin structural solid is automatically exempted. Mesh inlay height only skips wall sampling; STEP requires explicit solid indices as well.
- Inventory coordinates remain in native STEP space; mesh checks use the declared build orientation. Preserve the transform and units. The legacy `z_extent` inventory field describes extent along the selected build axis.
- Build-volume dimensions do not prove that nine parts, support, brims and a purge line fit together. Use the actual plate and slicer output.

Keep raw reports immutable within a review. Add dispositions with evidence rather than deleting findings. Genuine disconnected bodies, invalid exports or new thin load paths need correction. Supported faces may be accepted with actual path inspection; a successful old print or old revision is not a physical test of a new one.
