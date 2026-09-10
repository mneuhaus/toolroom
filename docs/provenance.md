# Provenance and maintenance

This workbench uses current local skills and selected project sources. The old handoff package dated 7 September was removed at the user's explicit request and is not an import source.

`provenance/imports.json` records the origins and SHA-256 hashes of copied resources. `provenance/assets.json` describes imported project images. `provenance/originals/` preserves the original skill entrypoints for comparison; they are not selected as additional active skills.

Import hashes describe the moment of import; curated versions may differ. `provenance/consolidation.json` records the two source versions and the specific checker consolidation. Hashes in `validation/tests.json` identify the helper revisions that were actually tested.

Paths in provenance records use logical labels such as `workspace/cad` and `home`. Personal credentials, browser profiles, API response collections and slicer projects are not part of the documentation import.

## Existing attribution

cad-khana identifies Apache-2.0 as its licence; the Jarvis adapter is based on an MIT-licensed project. This workbench does not import those runtime packages in full. Existing author and source credits in skill references are retained.

No blanket public licence has yet been assigned to original framework text, helpers, imported design-system templates or project images. The repository remains a local workbench. Its [Postplan reading edition](https://hn0ai0tcfhrd.postplan.dev) contains 28 selected documents, ten skill entrypoints and eight case studies. The verified publication is recorded in `validation/postplan-publish.json`.

## Maintenance

The [Mosey design language](design-languages/mosey.md) was derived from the public Mosey concept gallery on 10 September 2026. `provenance/references/mosey/manifest.json` records 18 unchanged render thumbnails with direct sources and hashes. They remain identified as AI-assisted reference images. `site/assets/mosey-family.svg` is our own schematic illustration; the YAML explicitly contains proposed geometry and colour values.

All maintained documentation and website text use English. Original source snapshots, filenames, proper names and historical evidence retain their original identity. Translating an explanation does not change the underlying CAD revision or establish a new physical result.

Changes to entrypoints, shared rules and helpers are maintained here. Existing active project directories and installed skills are not automatically synchronised back. A later migration must compare their then-current changes again.

The [additional joint reference review](joints/additional-references.md) covers four further videos. `examples/printed-joints/additional-sources.json` records metadata, sampled-frame analysis and evidence hashes. These references have not been reconstructed as native CAD or physically tested.

The Distributor illustration uses the existing English R8 project figure. The Bristlebot comparison was regenerated from its frozen CAD inputs with the original camera, scale and renderer; the verification found zero changed pixels outside the label bands. Original German figures remain preserved as historical evidence. `validation/bristlebot-english-figure.json` binds the English output to the frozen source hashes and the [optional regeneration helper](../examples/bristlebot/render_english.py).
