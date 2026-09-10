# Assembly process and data

## Source of truth and scope

Start from the requested Onshape assembly and the intended revision. Record its
document, workspace or immutable version, configuration and assembly element.
Inspect the recursive hierarchy, including repeated parts and purchased modules.
An imported complete machine can still omit spacers, washers or newly needed
fasteners. Distinguish three evidence levels:

- **Confirmed:** present and measured in the source or explicitly confirmed by the
  user. Preserve the origin of the confirmation.
- **Nominal or proposed:** hardware selected to complete the illustration but not
  confirmed in the physical build. Label it once in the inventory and at any
  critical operation; do not silently present it as purchased hardware.
- **Unresolved:** a dimension, fit or order that would change the assembly. Inspect
  the available CAD and prior answers first; request only the missing information
  that matters, while progressing independent parts of the manual.

A document microversion may change after renaming or organizing tabs without a
shape change. Conversely, a stable part ID can refer to altered geometry. Keep a
source snapshot or export hash together with identity and configuration records;
refresh the geometry export when the design changes. Neither volume nor bounding
box equality alone proves shape equality.

## Plan the sequence before the layout

Treat a build as subassemblies with dependencies, not a traversal of the CAD tree.
Trace each operation from loose parts to a reachable fastening or retention action.

Check the details that often defeat an apparently correct assembly:

- Opposing screw directions and whether fitting one part hides the next screws.
- Nuts or spacers that become inaccessible after a cover or module is fitted.
- Full bearing stacks: sleeves on both sides, internal shims, inner-race loading,
  eccentric pilot direction and the final adjustment tool's access.
- Actual screw length under the head, grip thickness, engagement and bottoming.
  Do not infer physical length from a label on a legacy reference screw.
- Open belt ends, their fixed/moving anchors, clamping order and tension-screw
  access. Simplified continuous CAD belt strips can misrepresent a real open belt.
- The pose needed to reach each screw group. Store that pose; do not illustrate
  every operation at a single convenient but inaccessible carriage height.

If a source design cannot be assembled, explain the specific conflict. Do not
quietly redesign it to make the manual work unless design work is already in scope.
Depict reused motors, PCBs and laser modules as complete units unless their own
internal assembly is part of the requested manual.

## Durable native stages

Use a folder such as `Assembly Guide`, then phase folders such as `X Carriage`,
`Z Module` and `Final Assembly`. Those names are examples, not a required product
structure. Preserve an existing document's numbering convention.

Use short English tab names such as `06 - Mount the rail and wagon`. Maintain a
stable logical step key and a publication map to the native assembly ID. Renumbering
a displayed step should not needlessly replace its native tab or break PDF links.

A stage stores the **completed state** of its operation. A detail illustration
may show exploded parts or focus on only one prepared subassembly. Keep these
illustration offsets out of the completed native pose unless an explicitly named
exploded-view assembly was requested. Fixed documentation placements need no new
motion mates; label their scope accurately.

For updates:

1. Read observed instances and resolve the intended source references.
2. Reuse matching guide-owned instances. Change only real deltas.
3. Preserve user additions; investigate differences outside the recorded ownership.
4. Verify every resulting source reference, placement and expected occurrence count.
5. Store observed results alongside the intended state for the next regeneration.

After a write timeout, inspect the destination before retrying. A timed-out create
may already have succeeded. If the result cannot be determined, stop the affected
write sequence and continue local preparation; do not create duplicate stages.

## Maintained recipe records

Keep these concepts even if an existing project uses different field names.

| Record | Information to retain |
| --- | --- |
| Source | Document/revision/configuration, master assembly, export hash, units and scope |
| Part role | Semantic occurrence key, canonical name, source part and element, parent path, configuration, mesh, transform, bounds and visual role |
| Hardware item | Quantity, type, thread diameter, under-head length or relevant dimensions, evidence status and source |
| Step | Stable key, display number, title, phase, prerequisite subassemblies, completed occurrences, newly handled items and essential notes |
| Repetition | How many identical units to build; whether the parts box is per unit or for the whole repeated operation |
| Illustration | Step/detail key, source occurrences, completed pose, temporary explosion offsets, camera, focus region, size, arrows and labels |
| Layout | Page format, density, sidebar captions, palette, box radii, arrow style and optional critical notes |
| Render profile | Stable preset ID, renderer/version, role-to-material mapping, profile overrides, colour space, lighting, sample counts and output directory |
| Publication | Native folder/tab IDs, owned instance IDs, source fingerprint, uploaded-file hashes and saved release version |

Store transforms with an explicit matrix layout, coordinate convention and unit.
Onshape API placement translations and STL coordinates can use different units;
convert intentionally and check a known dimension before rendering a full batch.
Record whether tessellation is already in world coordinates so a placement is not
applied twice.

Resolve roles by canonical name plus parent hierarchy and configuration; use an
expected native centre or another measured discriminator for repeated identical
parts. If a role is ambiguous or missing, do not assign the nearest arbitrary STL
number. Import order and temporary mesh UIDs are not durable identities.

### Counts and subassemblies

Do not require every stage to contain all previous stages. A wheel-core stage can
describe one prepared unit; a later carriage stage consumes four copies. Record
that repetition explicitly in new recipes rather than hiding `4×` in PDF code.

The whole-build inventory counts physical raw items once. A step tray can list a
prepared subassembly once, with its component hardware already accounted for in
the earlier preparation. Expand the subassembly graph when reconciling totals;
do not add both its raw components and its assembled unit to one hardware total.

## Local structure and regeneration

Follow existing project conventions. A useful starting structure is:

```text
src/assembly-guide/             recipe, selectors, layout, render presets
scripts/assembly-guide/         extraction, reconciliation, rendering, PDF build
docs/                          workflow and assembly decisions
exports/<revision>/docs/        final PDF
output/<revision>/assembly-guide/
  renders/                     illustrations and projection data
  renders-<profile>/            selected style without replacing comparison inputs
  style-study/                 same-source previews, comparisons and their records
  review/                      PDF page previews
  reports/                     native-stage, layout and publication checks
var/state/                     persistent IDs and publication maps
var/cache/                     tessellation, raw responses, compressed PDF images
var/logs/                      execution and API logs
archive/                       superseded revision sources
```

Regenerate in dependency order: source/hardware changes → semantic resolution →
native stages → affected renders → PDF → review → publication. A colour or camera
change skips source export and native assembly reconciliation. CAD appearance
publication, if requested, is a separate metadata operation. A typography-only
change normally skips all CAD rendering. A geometry change invalidates affected
mesh caches even when native IDs match. Keep source/export and mesh fingerprints
alongside recipe, layout, resolved profile and renderer-code fingerprints; a cache
is valid only for the inputs it actually checks. Rerender affected views and icons
explicitly when code or mesh changes are outside the existing cache key.

Prefer actual CAD shaded views when they provide the necessary framing. Native
export plus local rendering is a valid alternative for controlled explosions and
repeatable cameras. Keep the native step map and local views tied to the same
recipe, and state where the images were rendered.

## Verification evidence

- Native step references and transforms match the intended completed stages.
- Required hardware is accounted for, with nominal dimensions marked accurately.
- Final physical occurrence totals reconcile with prepared subassemblies.
- Mesh units, bounds and placement are consistent with the source.
- All PDF pages and difficult details have been visually inspected.
- Page dimensions, captions, quantities, links and embedded font/text handling work.
- The published PDF downloads and matches the validated local artifact before a
  saved release is declared complete.

Keep these checks proportional to the change. Layout feedback does not justify
re-running mechanical travel tests or redesigning parts.
