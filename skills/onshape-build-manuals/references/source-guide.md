> Imported field notes. Project-specific numbers, personal preferences and historical runtime assumptions are examples. The current framework entrypoint and explicit project profiles govern reuse.


# Onshape Build Manuals

Build a manual that can be regenerated from the CAD revision, permanent assembly
stages and a maintained illustration recipe. The PDF is an output of that system.

## Choose the work that is needed

- **New guide or changed assembly sequence:** read
  [Assembly process and data](assembly-process-and-data.md). Establish
  the mechanical sequence and reusable native stages before polishing pages.
- **Layout, arrows or parts-box feedback:** read
  [Illustration and layout](illustration-and-layout.md). Keep the
  existing stages and change only the affected presentation sources and outputs.
- **Rendering styles or functional colours:** read
  [Rendering styles and colour roles](rendering-styles-and-colour.md).
  It contains the A–P comparison library, the selected product treatment and the
  distinction between render materials, CAD appearances and physical print colours.
- **Publishing through Marc's local Onshape installation:** read
  [Local tooling and the worked example](local-tooling-and-example.md).
  It records the bridge's binary-upload failure and the verified workaround.

Use existing authorization and the user's chosen document, revision, language
and format. A local layout edit needs no cloud startup. A manual request does not
by itself authorize redesigning parts, replacing the main assembly, starting a
print or changing document access. Continue already authorized guide work without
adding a separate approval gate.

## Workflow

1. **Establish the source.** Identify the master assembly, revision, included
   subassemblies and excluded equipment. Inspect the real hierarchy and hardware,
   not just a screenshot. Record uncertain physical dimensions separately from
   confirmed facts. Existing IDs, counts or poses alone do not prove unchanged
   geometry.
2. **Plan a buildable sequence.** Check opposing screw directions, tool access,
   captive hardware, adjustment access and assemblies that must be prepared first.
   Preserve confirmed user answers. Do not add nominal screws to covered holes
   just to make a familiar bolt pattern look complete.
3. **Keep durable stages.** For a new guide, create or reuse numbered native
   Onshape assemblies in a dedicated guide folder when this is within the task's
   scope. Group them by subassembly or build phase. Store completed states there;
   store illustration cameras and explosion offsets separately. Reconcile changes
   in guide-owned instances and preserve stable tab IDs and user additions.
4. **Use one maintained recipe.** Give physical occurrences semantic identities.
   Record source references, explicit units and transforms, stage contents,
   repeated subassemblies, parts-box quantities, hardware dimensions, cameras,
   insertion arrows and essential notes. Resolve semantic identities again when
   CAD topology or import order changes; stop ambiguous mappings before writing.
5. **Render actual geometry.** Prefer native Onshape views where they give adequate
   control. A faithful export rendered in Blender is also suitable. Use CAD
   geometry for instructional parts; generative pictures are unsuitable for
   authoritative hole patterns, screw stacks and fit. Check mesh units and bounds.
   Compare styles with the same geometry, poses and camera. Keep styles in separate
   outputs, then apply the chosen profile consistently to views and inventory icons.
   Judge small hardware and adjoining surfaces at the intended page size.
6. **Build the illustrated PDF.** Start from the compact layout preferences below,
   adjusting page density to preserve readable assembly detail. Link step titles
   to the native stages. Keep quantities, sizes and part identifiers legible.
7. **Verify the deliverable.** Inspect every rendered PDF page, then inspect small
   hardware labels and difficult assembly details at readable size. Check stage
   membership and placements, inventory arithmetic, uncertainties, links and page
   bounds. A posed assembly and an arrow do not certify a collision-free insertion
   path, physical strength or firmware behaviour.
8. **Publish the verified result.** When publication is in scope, update the
   existing guide PDF and recipe tabs, verify the uploaded artifact, then save a
   release version. Retain the local editable sources and stable publication map.
   Give the user a direct link to the final PDF and its Onshape location.

## Established presentation preferences

These are Marc's preferences from the Sparky guide, not fixed requirements for
every product or page. A later user instruction takes precedence.

- Author names, labels and manual text in English unless another language is
  requested. Conversation may remain German.
- Prefer two steps on an A4 landscape page, a narrow parts sidebar beside the
  assembly image, a large step number and a short title.
- Put the running document title in the footer between step range and page number.
- Show each required item with its picture, quantity and relevant size. Keep the
  quantity and name together; use a small separate badge for a printed part ID.
- Give pictures most of the space. Retain short notes only for plausible assembly
  mistakes or necessary checks. Use an inset or a full detail panel when needed.
- Use restrained box rounding, transparent red vector arrows without white
  underlays, and consistent component contrast. Choose stage highlighting or stable
  functional materials deliberately; earlier parts need not be recoloured in a
  product-style guide.
- The selected Sparky treatment is N, Teenage Engineering-inspired: light grey
  structure, graphite supports and sparse orange adjustment/clamping parts. Its
  exact assignments are a worked example, not universal device rules or official
  brand, RAL or filament matches. Read the colour reference before adapting them.

[Layout defaults](../assets/layout-defaults.json) provides starting values compatible
with the earlier Workbench guide. Its blue rail/wagon colours are that mode's
fallbacks. [Render presets](../assets/render-style-presets.json) provides the separate
A–P style catalogue. Both are configuration data, not standalone renderers.

## Reusable PDF transport helper

Use [make_pdf_transport_safe.py](../scripts/make_pdf_transport_safe.py) only when the
active upload path requires an ASCII PDF, as Marc's observed UTF-8 request bridge
does. It wraps binary streams losslessly, preserves the PDF structure and checks
decoded streams, text, links and outlines. A binary-safe transport needs no such
conversion. Run it with `uv run` so its declared dependency is available; details
and the upload round-trip check are in the local-tooling reference.
