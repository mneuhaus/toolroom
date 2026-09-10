# Illustration and layout

## Compact pages with readable operations

The Sparky iteration went from 33 portrait pages to 17 landscape pages for the same
23 operations. This is a worked result, not a target page count for other guides.
Start with two steps per A4 landscape page when the assembly is tall and narrow.
Use a full-width detail or a different density when the operation needs it.

The tested starting layout uses a 297 × 210 mm page, approximately 11 mm margins,
two 133 mm panels separated by a fine rule, and a 30 mm parts sidebar. The main CAD
picture uses the remaining panel width and nearly all the height below the title.
Do not shrink hardware labels to force a busy step into this arrangement.

Keep the header to a large step number and short title. Put the guide title in the
footer, centred between the step range and page number. Avoid running headers,
repeated branding or descriptions that say only what the image already shows.

Use a brief note only when omission would invite a specific mistake: a hidden shim,
opposing fastener directions, different left/right screw lengths, belt engagement,
or a required carriage position. Routine actions such as placing an obvious part
or tightening the illustrated screw normally need no prose.

## Parts sidebars

Give each required item a tightly framed CAD picture and one centred quantity/name
caption. Keep quantity and label in the same paragraph so they cannot drift onto
unrelated baselines. Use a separate small badge for the established print-part ID.

Show dimensions that distinguish hardware: `2× M3 × 12`, `1× Ø8 × 0.5 shim`, or
the thread and relevant sleeve length. Include a legend for nominal lengths if
needed. Do not claim every item is illustrated at 1:1 scale.

Use short sidebar aliases when the inventory name is too long. Keep the full
canonical name in the recipe or inventory. If a step needs many items, use two
columns, a shared preparation tray or another panel; do not leave huge blank cells
or let long names collide with the next row.

For repeated units, place the repetition count near the subassembly and make the
parts box's counting convention explicit. For example: a box for one wheel core
plus `Build 4×`; the inventory still lists eight bearings, not two.

Use subtly rounded rectangular boxes. The Sparky reference reduced an 8 pt radius
to roughly 2.7 pt; its small 3 pt badges became 1 pt. The provided scale of one
third is a default to adapt, not a geometry requirement.

## Component colour and visual hierarchy

Choose the colour logic deliberately. Stage highlighting can mute installed parts
and emphasize the current operation. Stable functional materials can instead keep
each component recognizable across every stage and inventory image, using exploded
poses, framing and arrows to explain the operation. Avoid accidentally combining
the two so a part changes its apparent material when it becomes an "old" part.

The original Sparky Workbench guide used grey installed structure, orange printed
parts, a light steel-blue rail, a darker blue wagon and neutral fasteners. Its
selected N product treatment uses stable functional colours and a dark rail against
the pale base. Read [Rendering styles and colour roles](rendering-styles-and-colour.md)
for the current palette, all A–P treatments and comparison workflow.

Prioritize optical readability over styling. Check adjacent faces under the actual
lighting and at the final page size: nominally different RGB values can render
almost identically, and reflections or outlines can obscure a small screw recess.
Keep touching dark housings, rail, wagon and fasteners distinguishable. Use the same
material profile for assembly views, individual parts and prepared subassemblies.
Illustration colours alone do not specify physical material, filament or strength.

## Cameras, explosions and arrows

Use consistent orthographic views for comparisons, then turn to the side that
actually exposes the operation. A uniform camera is less useful than a visible
fastener. A seated module with only its joining screws exploded can be clearer
than moving the whole module in front of the target holes.

Render with a transparent background when compositing onto the PDF. Add arrows and
labels as vector overlays. The tested arrow style is red at 78% opacity, with no
opaque white underlay or rectangular raster background. Transparency belongs to
the PDF graphics state, not a white JPEG surrounding an arrow. Save and restore
the state so later labels are not accidentally translucent.

Derive arrow endpoints from the same object transforms and camera projection as
the rendered geometry. Do not estimate targets by eye on an unrelated screenshot.
When trimming image whitespace:

1. Find the visible alpha bounds.
2. Extend them to contain all arrow endpoints, paths and intended labels.
3. Add a small margin and compute the crop/fit transform.
4. Apply that transform to the projected overlay coordinates too.

Otherwise a tighter crop can make perfectly valid world-space arrows point at the
wrong screw. An arrow describes the operation's direction; it does not demonstrate
a collision-free physical insertion trajectory.

Where CAD uses simplified belt runs, a labelled schematic can explain the actual
loop and open ends. Keep it visually distinct from the geometric illustration and
do not draw a continuous belt through an open clamping gap.

## Page review

Render every final PDF page. Contact sheets reveal inconsistent density and colour;
full-size pages reveal clipped captions, hidden targets and small part labels.
Inspect at least the busiest tray, smallest hardware, darkest adjoining parts and
each unusual fastening direction at readable scale.

Check that the delivered file contains the latest images, not only an updated
source recipe. Retain source/export, recipe, layout, resolved render-profile and
final PDF hashes with the build report. A style change also reaches the small
inventory images. After mesh or renderer-code changes, explicitly rerender affected
assets when the cache key does not cover those inputs. When applying a transport-only
PDF conversion, compare decoded content and rendered pages so a file-format fix
does not conceal visual changes. Automated page checks support the visual review;
they do not replace inspecting every final page.
