# Provenance and maintenance

Toolroom was built from the previously installed skills and selected project sources. An older handoff package dated 7 September 2026 was removed at the owner's request and is not an import source.

## Records

| Record | Contents |
| --- | --- |
| `provenance/imports.json` | Origin paths and SHA-256 hashes of every copied resource, with its current destination |
| `provenance/originals/` | The original skill entrypoints, preserved unchanged for comparison; not active skills |
| `provenance/consolidation.json` | The two checker source versions and the specific consolidation |
| `provenance/assets.json` | Every image under `site/assets/` with its source and hash |
| `provenance/references/` | Manifests of external reference material: the Mosey render thumbnails and video-derived sources, each with hashes |
| `provenance/restructure-2026-09-10.json` | The old-to-new path map and the list of removed files from the restructure |
| `provenance/workspace-inventory.json` | The project directories that were surveyed for the consolidation |
| `validation/` | Results of checks that were actually run: site build, content checks, unit tests and the published reading edition |

Import hashes describe the moment of import; curated versions differ. Hashes in `validation/tests.json` identify the helper revisions that were actually tested. Paths in provenance records use logical labels such as `workspace/cad` and `home`. Credentials, browser profiles, API response collections and slicer projects are not part of the import.

## Removed project material

The restructure removed seven project case studies and twelve project images. Their transferable rules live in [Lessons from projects](../knowledge/lessons/project-lessons.md); the originating project directories remain untouched outside this repository. Removed paths are listed in the restructure record, and the previous edition remains in git history.

## Attribution

cad-khana identifies Apache-2.0 as its licence; the Onshape adapter is based on an MIT-licensed project. Toolroom does not import those runtime packages in full. Existing author and source credits in field notes are retained.

The Mosey design language was derived from the public Mosey concept gallery on 10 September 2026; `provenance/references/mosey/manifest.json` records 18 unchanged render thumbnails with direct sources and hashes. They remain identified as AI-assisted reference images. `site/assets/mosey-family.svg` is our own schematic illustration.

The Printed Joints Lab reconstructs principles from three NeedItMakeIt videos using transcripts and selected frames; `labs/printed-joints/sources.json` and `additional-sources.json` record metadata and hashes. No original CAD files or full transcripts are redistributed. The same rule applies to any further video-derived article: short quotations at most, a source record with hashes, and an explicit statement that nothing was physically verified here.

No blanket public licence has been assigned to original Toolroom text, helpers, imported design-system templates or lab images. The repository is a local working edition. The reading edition published on 10 September 2026 at `https://hn0ai0tcfhrd.postplan.dev` reflects the earlier layout; `validation/postplan-publish.json` records that upload.

## Maintenance

Changes to entrypoints, shared rules and helpers are maintained here. Installed skills and active project directories are not synchronised back automatically; a later migration must compare their then-current state again. When files move, add the mapping to a provenance record and update the destinations in `provenance/imports.json`.
