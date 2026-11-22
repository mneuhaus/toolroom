# Printed screw joints

## Workspace default

Marc selected `03_m3_hybrid_hole` as the default receiving profile for new printed M3 screw joints on 20 September 2026. The upstream part and its captured revision are recorded in the [interface profile](../../profiles/interfaces/m3-hybrid-hole.json). Use the matching clearance hole in preceding parts; only the receiving part bites the screw. Do not substitute a plain round pilot, nut pocket, heatset or insert unless explicitly specified. This does not replace purchased metal threads, bearing bores or non-M3 interfaces.

The reference is an exact curved profile, not a circle with three approximate cylinders added. Preserve its circular arcs and one-sided entry relief. The older Sparky variant with different rib and tip radii is a separate interface, not an interchangeable source. Do not silently scale the M3 contour to other screw sizes.

## Reusable implementation

In SolidCraft, the [command helper](../../toolbox/solidcraft/m3_hybrid_hole.py) reads the same interface profile and cuts the hole from above, from below or along a horizontal axis.

The [FeatureScript module](../../skills/onshape-cad/lib/m3_hybrid_hole.fs) and [local geometry adapter](../../skills/onshape-cad/scripts/m3_hybrid_hole.py) share the versioned interface profile. Native consumers should import a verified, pinned Feature Studio revision, or reproducibly embed the module's generated functions when cross-document dependencies are undesirable. Record the profile and module hashes with the consuming design.

Keep position, direction and depth as caller parameters. The caller owns the screw stack, material surrounding the hole and assembly sequence. Library reuse removes repeated contour reconstruction; it does not remove engineering review of each joint.

## Evidence and limits

Check the exact profile against the source, then review engagement, remaining wall, screw length, head seating, insertion and driver access in the actual assembly. A source-derived hole is not proof of pull-out strength, repeated service life or compatibility with every print process. Qualify critical load-bearing uses with a coupon made from the same profile in the intended material and print orientation.

See [assembly review](assembly-review.md) for installation and service requirements and [fits and retention](fits-and-retention.md) for allowance ownership. The chosen geometry is a user-approved design standard; nominal dimensions are not measured manufacturing capability.
