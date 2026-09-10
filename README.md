# CAD Skills Framework

A shared workbench for CAD with AI assistants: maintained skills, common technical knowledge, profiles, traceable examples and searchable HTML documentation.

**Start:** [Open the documentation](index.html). The generated website works directly from local files and entirely offline. To run a local preview:

```sh
python3 tools/serve.py
```

Then open `http://127.0.0.1:4176`. The server serves only this framework.

## Contents

| Directory | Purpose |
| --- | --- |
| `skills/` | Ten concise skill entrypoints with references and helpers loaded as needed |
| `knowledge/` | Shared rules for source authority, assembly, fits, manufacturing and evidence |
| `profiles/` | Design and manufacturing profiles; example values are explicitly uncalibrated |
| `examples/` | Case studies and an executable local checker lab |
| `site/` | Website sources and actual CAD images from the case studies |
| `tests/` | Consolidated checker regressions and profile resolution tests |
| `provenance/` | Origins, import hashes and recorded changes |
| `validation/` | Results of checks that were actually run |

## Rebuild the documentation and run tests

```sh
uv sync
uv run python tools/build_site.py
uv run python tools/validate.py
uv run python -m unittest discover -s tests -v
uv run python examples/checker-lab/build.py
```

The HTML is generated from Markdown, catalogues and example reports. Edit those sources, rather than the generated `site/data.js`.

## Printed Joints Lab

[Eight native connections](examples/printed-joints/README.md) add the `cad-joints` skill to the framework: dovetail variants, Echo-Lock, Drop-Lock and a keyed scarf. The local website offers assembled and separated views, with corresponding native Onshape links, STEP files and the assembly inspection report. [Four additional video references](docs/joints/additional-references.md) cover thin panels and elastic clips; they are reviewed references, not additional native models.

## Mosey design language

The [illustrated Mosey study](docs/design-languages/mosey.md) presents references, three form variants and applications to other objects. The versioned [Mosey profile](profiles/design-language/mosey.yaml) distinguishes observed features from our proposed CAD values. It is available in the profile workbench.

## Postplan reading edition

[Open the published reading edition](https://hn0ai0tcfhrd.postplan.dev).

```sh
uv run python tools/build_postplan.py
npx --yes postplan@0.0.4 upload site/postplan.html --api-url https://postplan.dev --description "CAD Skills Framework — architecture, skills and eight case studies"
```

The export contains 29 selected documents, ten skill entrypoints and eight case studies in a single HTML file below 512 KiB. Reference and project images are embedded as WebP; our vector illustrations remain SVG. Chapter links and expandable sections work without JavaScript. The interactive workbench, full-text search and notes belong to the complete local edition. Postplan uploads are public. Building creates only the local file; the separate upload command publishes it.

This repository is a local discussion and development edition. The bundled helpers have their own validation reports. The Printed Joints Lab was newly constructed in Onshape and checked geometrically. The other imported project examples were not rerun in their CAD applications or slicers; physical trials are outside this documentation update. Installed skills and existing project sources remain independent active work until an explicit migration. See [scope](docs/scope.md), [consolidation](docs/consolidation.md) and [provenance](docs/provenance.md).

The old handoff package dated 7 September was removed on request on 10 September. This repository is built from the current sources.
