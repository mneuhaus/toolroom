# Compatibility contract

Version 0.1 targets programmatically constructed **solid** geometry. It is a
subset implementation of the public language and API, with OpenCascade geometry
semantics. It does not execute Onshape's full standard-library source or replace
Parasolid. Passing the tests is not proof that arbitrary FeatureScript behaves
identically on Onshape.

## Language

| Area | Implemented scope |
| --- | --- |
| Modules | Optional version header, `export`, standard-library bindings, explicit local imports and namespaces. Functions are hoisted; constants initialize in source order. |
| Functions | Typed parameters/returns, most-specific overload selection, anonymous functions, `=>` lambdas and `->` call syntax. |
| Control flow | Blocks, if/else, while, classic for, one/two-variable for-in, break, continue, return, throw, try/catch, try expressions, `try silent`. |
| Values | Booleans, double-precision numbers, strings, arrays, maps with string, number or unit-quantity keys, boxes, enums, custom tags, vectors, matrices, quantities, IDs and native CAD objects. Boolean map keys are unsupported. |
| Copying | Arrays/maps have value semantics with shared immutable storage and copy-on-write paths; boxes and CAD builtins retain identity; closures capture local values. |
| Types | Standard type checks, enum/custom tags, typed bindings, predicates, preconditions. No full static analysis or predicate purity analysis. |
| Operators | Arithmetic including `^`, `~`, comparisons, strict boolean logic, short circuiting, conditional expressions, `is`/`as`, `??`, safe access, compound assignments. |
| Units | SI length and angle dimensions, their products/powers, meter/centimeter/millimeter/inch/foot/radian/degree; `unitless` is the number 1. Length/angle/integer/real bounds accept a single unit-keyed bound specification. No mass/time/temperature units yet. Geometry converts to mm only at the kernel boundary. |
| Metadata | Annotations, including enum-entry annotations, are parsed but do not produce dialogs or alter execution. `defineFeature`'s explicit defaults map is applied and its precondition executes. |

Custom operator declarations, general map keys, inspecting the underlying
`ValueWithUnits` map, namespaced custom type declarations, and automatic dependency
ordering of constants are not implemented. The interpreter is not a complete
FeatureScript static checker. Unsupported APIs fail when reached; dead branches
can contain unknown calls. There is no promise of byte-identical string formatting
for non-string `~` operands or of all Onshape floating-point corner cases.

The supported standard-library import module names are listed in
`runtime.py`. Imports provide the native compatibility bindings, not the precise
export set of the selected Onshape module/release. These bindings are also
available to functions-only source fragments.

## Geometry API

| API | Scope |
| --- | --- |
| `fCuboid`, `fCylinder` | Solid primitives, dimensioned corners/endpoints/radius. |
| `plane`, `line` | Unit directions; explicit plane x must be perpendicular to normal. Prefer explicit x for reproducible orientation; the default is a deterministic local choice. |
| `newSketchOnPlane` | Explicit Plane only. No inferred support face or `newSketch`. |
| `skLineSegment`, `skArc`, `skCircle`, `skRectangle`, `skPolyline` | Direct coordinates. No construction geometry, constraints or dimensions. |
| `skSolve`, `qSketchRegion` | Unbranched closed loops form regions; open paths remain available as edges. Fully nested loops partition into regions with holes. `filterInnerLoops=true` selects outer regions, preserving their holes. Crossing, branched and touching arrangements needing a planar solver are unsupported. |
| `skText` | One line, exact font file supplied through `--fonts` or the Python API; no implicit font substitution. OCCT outlines are scaled to rectangle height, with width overflow and optional mirrors. Font hashes are reported. Kerning, glyph placement and layout are not validated against Onshape. |
| `opExtrude` | Faces to solids, positive depth, one BLIND bound, explicit dimensionless direction. |
| `opRevolve` | Faces to solids, explicit Line axis, angleForward, zero/omitted angleBack. Zero/full-turn angles produce a full revolve. |
| `opLoft` | Solid through two or more profiles, each exactly one face/outer wire; no guides, constraints or connections. |
| `opSweep` | Face profiles swept along a connected, unbranched edge path. Input edges may be unordered. Default rotating orientation only; `keepProfileOrientation=true` is unsupported. |
| `opBoolean` | UNION and INTERSECTION of tools; SUBTRACTION from targets, optional keepTools. No target/tool grouping or SUBTRACT_COMPLEMENT. Splits yield separate solids. |
| `opFillet` | Constant radius on current body edges. OpenCascade tangent contours; `tangentPropagation=false` is accepted only when no unselected tangent edge is added. |
| `transform`, `rotationAround`, `mirrorAcross`, `identityTransform`, `inverse` | Translation, axis/angle rotation, reflection and nonsingular affine 3×3 matrices, including shear/nonuniform scaling. Transform composition and multiplication by dimensioned points. General affine geometry may become B-splines. |
| `coordSystem`, `toWorld`, `fromWorld` | Coordinate system from origin and orthogonal x/z directions; directions are normalized. Both point conversion and transform-returning overloads. Plane conversion and general coordinate-system operators are not implemented. |
| `opTransform`, `opPattern` | Solid bodies only. Pattern transforms and unique instance names must correspond. |
| `opDeleteBodies` | Solid bodies or solved sketch bodies. |
| `evVolume`, `evArea`, `evBox3d` | SI quantities, with world-axis tight bounding boxes. `tight=false` currently returns the same tight bounds. |
| `evLine` | Exactly one straight edge; curved edges raise a catchable error. |
| `evPlane`, `evSurfaceDefinition` | Planes and analytic cylinders/cones/spheres/tori; nonperiodic B-splines expose poles/knots/weights. Other surface categories return `surfaceType`. Periodic B-spline and Bezier descriptors require `returnBSplinesAsOther=true`. |
| `newInstantiator`, `addInstance`, `instantiate` | Selected solid bodies from an explicit `loadedContext`, unique instance names and optional transforms. Frozen imported Part Studio manifests provide `build({})` for their default configuration only. |
| `setProperty`, `getProperty`, `color` | Body name/appearance and face appearance stored in memory; `color` returns a typed Color. Getter is body-only. Face appearance follows supported geometry history; reports count colored faces. STEP/STL export geometry only; no STEP colors/names/assemblies. |
| STEP export | Reads back and checks solid count/validity, sorted per-solid volumes (relative tolerance 1e-5 or absolute 0.001 mm³), and overall bounds (0.001 mm). Invalid periodic-face transfer triggers one retry with closed faces split on a private copy. Failure preserves the previous destination. `Build.step` returns verification measurements; CLI reports include them under `exports.step`. R10b's dedicated runner uses stricter comparison tolerances. |

Absent operations such as shell, draft, chamfer, sheet metal,
and general sketch solving fail explicitly. No feature regeneration
UI, parameter editor, live cloud Part Studio context, assembly mates or server service
is implemented.

## Queries and identity

Supported queries: `qCreatedBy` (explicit EntityType), `qEverything`,
`qAllModifiableSolidBodies`, `qNothing`, `qUnion`, `qSubtraction`, `qIntersection`,
`qNthElement`, `qEntityFilter`, `qBodyType(SOLID)`, `qOwnedByBody`, `qOwnerBody`,
`qSketchRegion`, `qContainsPoint`, `qGeometry`, `evaluateQuery`, `isQueryEmpty`.
Point containment uses solid classification or distance to the selected topology.
Geometry filters recognize analytic faces, spline surfaces and line/circle/ellipse
edges. Compressed Onshape queries (`qCompressed`) and imported feature history
are unsupported.

IDs are component arrays: `id + "box"` is distinct from `id + "box2"`.
An ancestor ID matches descendants. Exact operation IDs cannot be reused after
a successful operation; failed solid operations roll back their changes and ID.
`unstableIdComponent` supplies a local ID segment. Wildcard matching and stable
correspondence across regenerations are not implemented.

Body queries follow surviving local provenance through modifications, splits and
unions. Disconnected union outputs retain only their contributing sources. A
surviving body's key and properties prefer the earliest contributing tool/target.
These are local rules, not Onshape's complete persistent naming system.
Disconnected unions use actual face history to attribute input solids after
private copying. Fully enclosed tools with no surviving boundary faces use a
geometric intersection fallback; missing attribution raises an error.

Queries from `evaluateQuery` carry context identity. A body handle follows its
surviving local key. A face/edge handle becomes stale when its body is modified;
using it raises a compatibility error. Reselect current topology with
`qOwnedByBody`, or use a supported creator query.

`qCreatedBy(..., FACE)` follows OCCT Modified/Generated/Removed history through
booleans, same-domain unification, fillets and transforms. Splits and merges
retain contributing face creators; moving a face preserves its creators.
Patterns and instantiated copies receive their own creator IDs. This is local
face lineage, with deterministic first-contributor appearance inheritance; it
does not emulate every Parasolid identity decision. Historical edge/vertex
creator queries on modified bodies remain explicitly unsupported. No stable
cross-run topology identifiers are promised.

## Failure and resource behavior

Ordinary language/geometry errors can be caught in FeatureScript. Compatibility
errors and execution limits deliberately bypass `try`/`try silent`, so an absent
operation cannot produce an apparently successful model. This differs from
Onshape exception semantics and is a deliberate compatibility diagnostic.
Native solid-operation failures are recorded in `failed_operations` even when
FeatureScript catches them. The single-file CLI still permits this recovery and
prints a diagnostic; the corpus runner classifies it separately as `recovered`.

`--max-steps` limits evaluated AST nodes and `--max-depth` limits function nesting.
They do not impose a wall-clock timeout on native OpenCascade operations or a
general memory/process sandbox. The Python API and CLI are intended for trusted
local design sources.
`fsocct batch` adds a per-case subprocess timeout and verifies frozen source
hashes before execution. A passing case establishes successful local execution
with valid solids, not geometric equality to an Onshape reference.

## Public references

Implementation references consulted on 21 September 2026:

- [Language syntax and semantics](https://cad.onshape.com/FsDoc/syntax.html)
- [Values, types and copying](https://cad.onshape.com/FsDoc/type-tags.html)
- [Functions, predicates and modules](https://cad.onshape.com/FsDoc/top-level.html)
- [Exceptions](https://cad.onshape.com/FsDoc/exceptions.html)
- [Standard-library API](https://cad.onshape.com/FsDoc/library.html)
- [OpenCascade modeling algorithms](https://dev.opencascade.org/doc/overview/html/occt_user_guides__modeling_algos.html)
