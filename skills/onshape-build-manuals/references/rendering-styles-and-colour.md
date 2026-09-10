# Rendering styles and colour roles

Read this reference when comparing illustration styles, applying a chosen material
profile to a manual, or preparing a functional colour plan. Layout and vector
overlays remain in [Illustration and layout](illustration-and-layout.md); native
stages remain in [Assembly process and data](assembly-process-and-data.md).

## Stable A–P style library

[render-style-presets.json](../assets/render-style-presets.json) retains the 16
Sparky study presets and their numeric palette, contour, exposure, sample, light
and resolution settings. Its `defaults` records the original base palette and
1800 × 1500 study size. `mode` selects a shader implementation; this data is not a
standalone Blender renderer. The project renderer is listed in the
[local-tooling reference](local-tooling-and-example.md).

The example's complete-manual renderer currently implements `product` mode. Other
modes live in the style-study renderer; factor their material/contour setup into
the shared view/icon renderer when adopting them for a whole manual. Changing a
preset ID alone does not add that implementation.

The portable catalogue omits the original `sourceView: step-15` and N's original
Sparky `partColors`. Choose a source view and bind semantic part roles for the new
project. Preserve each letter-to-ID mapping when selecting or reordering styles;
letters identify treatments, not current positions in a sheet. Retain the user's
chosen style or order. This library is a starting set and does not limit new styles.
Most original presets honour the recipe's current/previous-stage colour choices.
N's `semanticColors` instead uses persistent part roles; its manual profile adds
the functional assignments described below.

| Letter / stable ID | Treatment | Rendering recipe |
| --- | --- | --- |
| A / `a-current` | Current CAD / Workbench | Reuse the current CAD render as the baseline. The example uses studio shading, bright cavity edges and object outlines. |
| B / `b-illustrated` | Illustrated manual | Matte Cycles surfaces, soft depth and fine dark Freestyle contours. |
| C / `c-studio` | Soft studio | Broad area lights, separate metal/plastic materials and soft reflections. |
| D / `d-technical` | Technical line art | White emission surfaces and visible feature lines; monochrome with Standard colour management. |
| E / `e-blueprint` | Blueprint | Navy emission surfaces, cyan contours and a drafting grid composited behind the model. |
| F / `f-iridescent` | Iridescent concept | Facing-dependent metallic colour shifts mixed with broad procedural variation; a presentation treatment. |
| G / `g-hdr-4k` | HDR studio / 4K | Studio HDR environment, reflective material detail and subtle bevel normals. Render at 3840 × 3200 and also retain a 32-bit OpenEXR. |
| H / `h-sketch` | Pencil sketch | Warm monochrome matte shading, repeated graphite contours, slight stroke wobble and pressure variation. |
| I / `i-brick-manual` | LEGO-inspired brick manual | Strong role colours, plastic sheen and bold clean contours applied to the actual CAD parts. |
| J / `j-editorial` | Design studio | Slate/sand palette, satin surfaces, warm key light and subtle bevel normals. |
| K / `k-ghibli` | Ghibli-inspired | Sage/terracotta colour, smooth painted light ramps, blue-grey shadows, warm highlights, fine ink lines and restrained grain. |
| L / `l-sci-fi-anime` | Sci-fi punk anime | Discrete cel shading, deep graphic shadows, orange/cyan palette and strong contours. |
| M / `m-architecture` | Shaded architecture | Pale clay surfaces, fine grey contours and stronger contact shading with restrained blue accents. |
| N / `n-industrial-product` | Teenage Engineering-inspired | Neutral product materials, graphite, satin metal and sparse orange accents; semantic materials, studio environment, 3840 × 3200 study image. |
| O / `o-garage-diorama` | Garage diorama | Warm miniature lighting and muted olive/terracotta materials, adapted from the project's garage-image reference. |
| P / `p-sketchup` | SketchUp-style | Simple discrete face shading, muted material colours and clean visible edges. |

Reference-inspired treatments describe materials, lighting, palette and contours.
They do not add the reference image's rooms, furniture, characters or props to the
assembly. I does not convert parts into bricks. These render changes preserve the
CAD solids, holes, part placement and fastener stacks. Shader bevels and bump affect
normals only; adding a geometry bevel or displacement changes the subject being
compared. K, L and O were mood studies in Sparky and remain available choices.

### Shared scene and mode implementation

For the worked Cycles setup, enable denoising and adaptive sampling, use six total
bounces and three diffuse/glossy bounces. The observed run used Blender 5.1.2 on CPU
with four threads; these are reproducibility records, not platform requirements.
Use transparent RGBA renders so comparison backgrounds and PDF overlays remain
separate. Most material modes use AgX with Medium High Contrast and the preset's
exposure. D, E, K, L and P use emission with Standard/None at exposure zero.

Convert the entire scene consistently from CAD millimetres to rendering metres:
meshes, transforms, explosion offsets, camera location, orthographic scale and
clipping distances. Keep projection records in explicit units. The example first
projects arrows in CAD units, then scales geometry and camera together. Scaling
only the model changes framing, lighting and overlay alignment.

The base studio uses three camera-relative disk area lights. Let `c` be the model
centre, `r` camera right, `u` camera up and `d` the normalized direction from the
model toward the camera; offsets and sizes below are metres.

| Light | Position | Base energy / size | N energy / size |
| --- | --- | --- | --- |
| Large key | `c - 0.32r + 0.38u + 0.42d` | 35 / 0.32 | 38 / 0.38 |
| Soft fill | `c + 0.30r + 0.08u + 0.30d` | 12 / 0.42 | 8 / 0.48 |
| Upper rim | `c + 0.10r + 0.36u - 0.24d` | 24 / 0.24 | 22 / 0.18 |

Aim the lights at `c`; apply the preset overrides. J's key is tinted `(1, .86, .73)`
and O's `(1, .70, .43)`. G and N used Blender's bundled `studio.exr`; retain its
licence/provenance with externally distributed environments. Environment resolution
is independent of output resolution. G's PNG is tone-mapped; a PDF is not an HDR
display format, and a wide image alone is not HDR.

Useful implementation details beyond the preset data:

- **A:** the historical Workbench baseline uses `paint.sl`, studio rotation `.35`,
  studio shadows/specular highlights, cavity type `BOTH`, curvature ridge/valley
  `1.35/1.0`, cavity ridge/valley `1.1/.8`, dark outlines and 32-sample render AA.
- **Contours:** use visible silhouettes, borders, creases and external contours,
  with a 135° crease threshold. The study omits material-boundary, ridge/valley and
  suggestive-contour lines. Use the preset thickness and colour, then check them at
  the final page size. H adds two sketchy rounds, spatial-noise amplitude `1.25`
  and scale `18`, plus thickness noise amplitude `.35`, period `24`, seed `7`.
- **B/C/G/I/J/O:** Principled BSDF settings distinguish appearance without changing
  geometry. B uses roughness `.86`, metallic `0`, specular `.08`. C uses metallic
  `.78/0`, roughness `.30/.48`, specular `.50/.28` for metal/plastic. G changes those
  roughness values to `.20/.36`. I uses metallic `0`, roughness `.34`, specular `.28`
  and coat `.12`. J uses metallic `.65/0`, roughness `.36/.56`, specular `.25`.
  O uses metallic `.15/0`, roughness `.43/.71`, specular `.25`. G/J use an `.08 mm`
  shader bevel; O uses `.20 mm`, each with four samples.
- **D/E/H/M:** E's surface emission is linear RGB `(.0052, .0252, .0612)`; the navy
  background and grid remain separate. H's base is `(.80, .77, .70)` with roughness
  `1` and specular `0`. M also uses roughness `1` and specular `0`, with a `9 mm`
  ambient-occlusion distance feeding its clay base colour.
- **F:** metallic `.86`, roughness `.24`, coat `.35`, coat roughness `.18`. Mix facing
  with noise (noise scale `3`, weight `.35`) and drive a blue/cyan/magenta/amber/violet
  ramp. The original ramp positions/linear RGB were `0:(.04,.09,.55)`,
  `.22:(.03,.7,.95)`, `.45:(.65,.03,.32)`, `.68:(.98,.50,.08)`, `1:(.16,.05,.55)`.
- **K/L/P:** map the dot product of surface normal and normalized
  `(.35d - .65r + .70u)` into `[0,1]`, use the ramps below, multiply by the role
  palette and feed emission. K uses smooth `EASE` interpolation; L/P use `CONSTANT`.
  K adds subtle noise (scale `85`, detail `2`, range `.91–1`). K/L multiply in
  ambient occlusion at `4 mm` distance with `.5` weight; P omits that AO layer.

| Mode | Ramp stops: position → linear RGB |
| --- | --- |
| K | `0 → (.29,.34,.43)`; `.43 → (.39,.46,.53)`; `.49 → (.67,.73,.72)`; `.73 → (1,.94,.76)`; `1 → (1,.97,.84)` |
| L | `0 → (.035,.048,.10)`; `.47 → (.10,.19,.31)`; `.64 → (.72,.63,.53)`; `.82 → (1,.93,.66)` |
| P | `0 → (.37,.40,.43)`; `.40 → (.60,.62,.65)`; `.66 → (.85,.85,.83)`; `.84 → (1,1,.96)` |

## Compare the same subject

Choose a representative assembly view with touching parts, dark housings, small
hardware and any important exploded fasteners. Sparky's historical study used step
15 with 74 source objects; those are example values. Fix the source geometry,
occurrences, transforms, explosion offsets, camera and orthographic projection for
all alternatives. Change material, lighting, contours and background only. If an
individual operation needs a different camera, make that a separate comparison.

Retain the baseline render and projection record. Store study renders and their
metadata separately from the released manual and selected production profile.
Before combining images, verify source view, occurrence count, camera, dimensions
and rendered preset against the intended settings. Camera/count equality cannot
detect changed mesh bytes; tie the set to its source/export and recipe fingerprint.

Compute one common crop in normalized image coordinates from the union of visible
alpha bounds, with a small margin. Apply it to every tile before fitting. This
keeps the 3840 × 3200 G/N images and 1800 × 1500 alternatives at the same apparent
scale. Keep RGBA originals plus opaque previews for viewers that show transparency
against black. Offer overview sheets and larger paired PDF pages when detail needs
inspection; the example overview tiles link to their larger pair pages.

The existing project supports these commands from its root (discover the local
Blender executable rather than assuming the shell command is installed):

```sh
blender -b -t 4 --python scripts/r12/assembly-guide/render-style-study.py \
  -- m-architecture p-sketchup

uv run --with pillow --with reportlab python \
  scripts/r12/assembly-guide/build-style-comparison.py

uv run --with pillow --with reportlab python \
  scripts/r12/assembly-guide/build-style-comparison.py \
  --styles a b e i h m n --image-only
```

Renderer arguments are full preset IDs; omitting them renders all styles. The
comparison builder accepts letters or IDs and preserves the supplied order, so
that shortlist is **A, B, E, I, H, M, N**, not alphabetized. It rejects unknown or
duplicate choices. In the current builder, `--styles` requires `--image-only` and
writes a separately named shortlist image/report, preserving the full comparison.
A shortlist from valid existing renders needs no CAD export or rerender.

If geometry or poses change, rebuild the source view/projection and all comparison
variants that use it together. If only a preset changes, rerender that preset and
rebuild its comparisons. Preserve the original presented N image when adopting a
different functional palette for the production manual.

## Apply N as a functional product treatment

Keep a named base preset and a separate project profile, such as
`layout.renderStyle`, containing the selected ID, role mappings, palette overrides,
view/icon samples and output directory. The original N study used lighter panels
and made the idler axle orange. Sparky's selected manual profile deliberately uses
darker graphite panels and makes that axle neutral metal. Treat these as two
maintained treatments; do not silently rewrite the historical choice sheet.

N uses Principled materials with metallic `.72` for hardware/rail/wagon and `.05`
otherwise, roughness `.32/.45`, and specular `.36`. Its fine appearance texture uses
noise scale `240`, detail `2`, bump strength `.13`, bump distance `.006 mm`, and
four-sample `.08 mm` bevel normals. These are illustration settings, with no
material-property, print-quality or strength claim. Keep physical/material role
separate from colour role so colour overrides do not accidentally turn a fastener
into a plastic-looking part.

The adopted Sparky profile used 64 Cycles samples for its 31 assembly views and 40
for its 39 inventory icons. It retained the original recipe cameras, image sizes,
23 steps and 17 A4 landscape pages. N's study resolution does not automatically
override every production view or icon. Adjust samples and resolution to the
required detail; apply the same material system to the complete view/icon set.

The shared Sparky `render.py` also accepts `--recipe <path>` and `--layout <path>`.
Use these for a separate CAD-revision or design-review scene without replacing a
released manual's recipe. Record its source STEP and mesh hashes separately; a
design review render does not update the historical PDF.

The transferable colour idea is a restrained hierarchy: quiet structural surfaces,
distinct supporting components and a limited accent for adjustment or clamping.
Decide roles from the actual device and the user's intent. A component's size,
visibility or motion alone does not determine its colour. In Sparky, the structural
probe arm is graphite while its height-adjustable bracket is orange; both jaws are
orange even though they clamp different fixed/moving belt ends.

These exact assignments describe the nine printed pieces in that project:

| Function in Sparky | Colour role | Printed pieces / semantic keys |
| --- | --- | --- |
| Fixed carriage structure | Warm light grey / `shell` | 01 Z base / `z_base`; 09 permanent X carrier / `x_carrier` |
| Moving structural supports | Graphite / `panel` | 02 wagon adapter / `wagon_adapter`; 04 laser adapter / `laser_adapter`; 06 structural probe arm / `probe_arm` |
| Belt tension adjustment and clamping | Orange / `accent` | 03 tension slider / `tension_slider`; both 10 clamp jaws / `lower_clamp_jaw`, `upper_clamp_jaw` |
| Probe-height adjustment | Orange / `accent` | 07 height-adjustable probe bracket / `probe_bracket` |

Hardware, including `idler_axle`, uses neutral metal; motor/laser housings use black,
and belts/wheels use black rubber-like appearances. The dark rail remains clearly
separated from the pale base, and the wagon from the rail. Inspect these interfaces
under the actual lighting at the final page size. The profile retains role colours
throughout the sequence instead of recolouring earlier parts. Arrows and exploded
poses carry the operation emphasis.

## Render colour, CAD appearance and physical colour

Keep these records separate: linear RGB shader values, display/sRGB appearance
metadata, and any physical filament/paint/RAL specification. The functional palette
can guide manufacturing colour choices, but its rendering does not establish an
available filament, exact colour match, RAL code, mechanical property or validated
physical part. These are the project's choices inspired by Teenage Engineering;
they are not official Teenage Engineering colour specifications.

| Colour role | Linear RGB in the selected profile | Converted 8-bit sRGB |
| --- | --- | --- |
| Warm light grey / `shell` | `(.62, .61, .57)` | `(206, 205, 199)` / `#cecdc7` |
| Graphite / `panel` | `(.18, .19, .185)` | `(118, 121, 119)` / `#767977` |
| Orange / `accent` | `(1, .12, .008)` | `(255, 97, 22)` / `#ff6116` |

Convert each linear channel `c` using
`s = 12.92*c` for `c <= .0031308`, otherwise
`s = 1.055*c**(1/2.4) - .055`; then round `255*s` for the Onshape colour channel.
Multiplying linear RGB directly by 255 gives the wrong display colour. The swatch
conversion also does not predict a lit, exposed, AgX-rendered pixel. Page ink and
accent colours are separate design values and need not equal the shader swatches.

When CAD appearances are included in the requested work, resolve exact part
identities within the intended Part Studios; save prior appearances and opacity,
apply only the intended metadata, then read back and verify every result. Sparky
matched unique English names for nine original pieces and nine buildplate copies,
preserved opacity and left hardware CAD appearances intact. Assembly references
inherited those appearances after refresh. The stored before/after state supports
later updates; after geometry regeneration, check which overrides survived before
reapplying them. A render-style request alone needs no appearance publication,
manufacturing-export change, slicer job or mechanical redesign.

## Regeneration and review evidence

Retain source/revision/export and mesh identity, recipe/layout hashes, base-preset
plus override profile hash, renderer version/code identity, camera/projection
records, image dimensions, sample counts and final image/PDF hashes. Keep the
original study, selected profile output and final PDF sources distinguishable.

The current Sparky `--stale` mode checks recipe and resolved profile hashes only.
If renderer code or mesh files change without changing those hashes, explicitly
rerender affected views and icons; an unchanged part ID/path is not enough. A full
cache key can include those inputs when adapting the pipeline. Rebuild the PDF
from the selected directory and reject stale profile/recipe records before use.

Render every final PDF page and inspect the pages, with larger views of the busiest
trays, smallest fasteners, dark adjoining parts and unusual insertion directions.
Automated checks cover text bounds, image profiles, native step links and page
dimensions; a generated contact sheet is not evidence that someone inspected it.
Use the original native completed-state assemblies and stable links throughout a
style revision. Rendering evidence does not validate a later mechanical repair.

For the observed local UTF-8 request bridge, preserve the lossless ASCII85 PDF
transport conversion and compare decoded content plus rendered pages. Download
published bytes and compare their SHA256 before declaring publication complete.
Use the existing helper and [transport instructions](local-tooling-and-example.md)
when that bridge is active; a binary-safe upload path needs no ASCII conversion.
