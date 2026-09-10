# Conventions for working in Toolroom

## Where things go

- `knowledge/` holds the reasoning: rule, why, evidence, limits. Backend-independent. One maintained source per rule; other places link to it. Every article is listed in `knowledge/catalog.json`.
- `skills/` holds thin entrypoints (`SKILL.md`, under about 60 lines) that say when to load which knowledge and how to do the work in a backend. Backend details and imported field notes live in `skills/<name>/references/`. Helper scripts live in `skills/<name>/scripts/` and are covered by tests and evidence hashes.
- `profiles/` holds numbers: design languages, manufacturing processes, protected interfaces and the workstation profile. A value that describes one machine or one setup belongs here, not in a knowledge article.
- `labs/` holds reproducible experiments with their own inputs, outputs and hashes. Each lab is listed in `labs/catalog.json`.
- `docs/` is about the repository itself: architecture, scope, history, provenance.
- Personal project narratives do not belong in the repository. Distil the transferable rule into `knowledge/lessons/` and name the origin in one line.

## Writing

- Author filenames, code, entrypoints and all maintained documentation in English. Preserve original source snapshots and historical evidence in their original language.
- Keep nominal design values, calibrated measurements and historical example dimensions distinct. A stated number from a video, a vendor page or an old project is an example until this repository records a measurement.
- Preserve native-source authority, declared transforms, raw findings and incomplete analysis. A rendered example is not a physical acceptance result. "Not run" is never a success.
- Do not repeat a rule; link to its maintained source with a relative link. The validator fails on any broken link or missing heading anchor.

## Changing things

- Edit Markdown, YAML and the three catalogs, then regenerate with `uv run python tools/build_site.py` and check with `uv run python tools/validate.py`. Never edit `site/data.js`, `site/app.js`, `site/style.css` or `index.html` directly; their sources are under `site/src/`.
- For helper changes run `uv run python -m unittest discover -s tests` and refresh `validation/tests.json`.
- For website changes inspect desktop and mobile layouts and the actual interactions.
- When moving files, record the old and new paths in a `provenance/` record and update `provenance/imports.json` destinations.
- Keep the existing installed skills and original project directories intact unless migration is explicitly requested.
- No live CAD, slicer job, device or publishing operation is required for documentation work. Uploading the reading edition is a public step and needs an explicit request.
