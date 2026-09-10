# Lessons from projects

The rules below were distilled from real design work and are stated generically, so that they apply to the next part rather than to the one that produced them. The originating project is named only as provenance at the end of each section; it is not a reference you can look up here, and its figures, renders and measured results are not part of this repository's evidence. Nothing in these projects has been re-verified for general use, so treat every number that appears below as belonging to that study alone. Where a rule already has a maintained home in another article, it is stated once and linked rather than repeated.

## Design language must not touch protected interfaces

Keep visual rules, process profile and protected interfaces in separate layers, and resolve them in that order of authority. A grid, radius family or accent colour selects and signals; it never moves a mounting axis, thins a loaded carrier or reduces engagement. Apply facets, labels and accents to named faces chosen per part, not by a blanket rule across all edges. This prevents the common failure in which a styling pass silently changes a fit that other parts depend on, and it prevents the opposite failure of refusing a deliberate manufacturing choice (a supported print, for example) because it looks untidy. To apply it, list the protected interfaces before styling and re-check them afterwards; a product's character should be visible across the part family, not on every chamfer. See [the design-system skill](../../skills/cad-design-system/SKILL.md) and the precedence table in [the shared core](../foundations/core.md).

Origin: Sparky X/Z unit, R13→R14 comparison.

## Assembly inventory is not the CAD part count

Treat CAD occurrences, purchased-component count and assembly handling units as three separate layers, each counted for its own purpose. A multipart marker or a complete purchased bearing is one handling unit, not a set of individually assembled pieces; conversely one CAD body may be several inventory lines. Reconcile the layers explicitly instead of deriving one from another. The failure this prevents is a manual that instructs a build no one can perform, because the count came from the model tree rather than from the hands doing the work. Evidence is an accessible fastener sequence per stage, not a plausible final pose; in one documented revision the same assembly yielded 45 CAD occurrences, 43 handling units and 20 inventory entries, and those figures belong to that study only. An exploded animation explains a step; it does not establish an insertion path. See [assembly review](../construction/assembly-review.md) and [the assembly-manual skill](../../skills/onshape-build-manuals/SKILL.md).

Origin: C2 Channel assembly manual, documented revision.

## A simulation result belongs to its exact model

State geometry revision, contact model, material and its assumptions, print orientation and load case together, or do not state the result at all. A displacement figure is a property of that combination; carrying it into a later revision, a different support arrangement or a different material is a new claim requiring a new run. This prevents "FEM checked" from becoming a label detached from any traceable input. In practice: record solver progress, equilibrium and sensitivity to contact stiffness, name what is still open (mesh refinement, creep, yielding), and keep the study's own numbers marked as belonging to it. One documented contact study reported roughly 3.97 mm maximum vertical displacement under an assumed 1 kg load with assumed friction; that value is valid only for that geometry and load case. The general distinction between simulation, slicing and physical testing is maintained in [verification](../foundations/verification.md).

Origin: Distributor contact study, R8.

## A scan is a hypothesis until measured

Keep photos, raw scans, reference frames and the functional replacement model as four distinct sources, and never let a smoothed surface stand as a dimension. Cleaning, registration and canonical alignment come before any measurement; leftover fixture or turntable geometry corrupts registration, and attached markers are not features of the part. Reconstruct a simple functional form and then measure its deviation, rather than tracing every scan irregularity. The failure prevented is a model that reproduces noise faithfully and function poorly. Check functional surfaces and local openings individually: a global average deviation hides exactly the local errors that matter, and sample points inside CAD triangles so tessellation structure is not mistaken for geometry. See [the scan reconstruction skill](../../skills/scan-reverse-engineering/SKILL.md).

Origin: LINAK motor-cover scan reconstruction.

## Compensation has one owner

Assign each manufacturing correction, kerf, hole allowance, shrink or scale, to exactly one step in the chain and record where that is. Either the model carries nominal geometry and CAM offsets the path, or the exporter emits compensated contours and CAM must not offset again; both are valid, applying both is not. This prevents the double-correction that turns a good fit into a loose one without any visible modelling error. To apply it, separate nominal geometry, material thickness, manufacturing contour and sheet layout as distinct artifacts, and state the owner in the workflow description before the first cut. Kerf values and the nominal-plus-CAM convention are maintained in [laser cutting](../manufacturing/laser.md).

Origin: File-trolley laser extension, export workflow.

## Variants isolate one question

Build variants on a shared frame so that each set differs in one respect only, and keep form questions apart from mechanical ones. Form studies need identical cameras, scale and lighting; mechanical comparisons need identical boundary conditions, and the two must not be read from the same picture. The failure prevented is a decision made on an attractive render or a high simulated speed that came from a changed camera or a changed contact assumption rather than from the design. Applying it means parameter-driven geometry over duplicated models, dedicated calibration coupons for anything you intend to measure, and treating a physics prototype's output as a hypothesis until it is calibrated against a printed specimen. See [construction patterns](../construction/patterns.md) for the patterns a shared frame usually reuses.

Origin: Bristlebot variant study, Fusion branch.

## Joint families share a principle, not dimensions

Describe a joint by its function, interface and limitations; the edge treatment, radii and wall thicknesses that a family happens to use are an optional profile, not part of the definition. Reusing a fork-and-tongue interface across a product family is sound; reusing its dimensions on a new material, load or print pose is not, and each such change requires its own evidence. This prevents a validated joint from being credited with validation it never had. Note also that a project preference (printed hand-operated threads, for example) is a preference and not a prohibition, a purchased ball joint or a metal fastener remains available where it is the better answer. Comparing dimensions between two modelling routes does not establish that all surfaces are equivalent. See [joints](../construction/joints.md) and [fits and retention](../construction/fits-and-retention.md).

Origin: Modular camera-arm mount family, fork-and-tongue interfaces.

## Origins

| Project | Contribution | Maintained home |
| --- | --- | --- |
| Sparky X/Z unit (R13→R14) | Separation of design language, process profile and protected interfaces | [the design-system skill](../../skills/cad-design-system/SKILL.md), [the shared core](../foundations/core.md) |
| C2 Channel assembly manual | Counting layers, build stages, accessible fastener sequence | [assembly review](../construction/assembly-review.md), [the assembly-manual skill](../../skills/onshape-build-manuals/SKILL.md) |
| Distributor contact study (R8) | Binding a simulation result to its exact model | [verification](../foundations/verification.md) |
| LINAK scan reconstruction | Scan as hypothesis; local instead of averaged deviation | [the scan reconstruction skill](../../skills/scan-reverse-engineering/SKILL.md) |
| File-trolley laser extension | Single ownership of manufacturing compensation | [laser cutting](../manufacturing/laser.md) |
| Bristlebot variants | Shared frame, one question per variant, honest comparisons | [construction patterns](../construction/patterns.md) |
| Camera-arm mount family | Joint families share a principle, not dimensions | [joints](../construction/joints.md), [fits and retention](../construction/fits-and-retention.md) |
