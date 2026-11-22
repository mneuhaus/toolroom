# Conventions for working in Toolroom

## Where things go

- `knowledge/` holds the reasoning: rule, why, evidence, limits. Backend-independent. One maintained source per rule; other places link to it. Every article is listed in `knowledge/catalog.json`.
- `skills/` holds concise entrypoints (`SKILL.md`) with precise triggers, essential constraints and task-specific routes. Keep substantial conditional detail in references; a low line count alone does not make an entrypoint small. Backend details and imported field notes live in `skills/<name>/references/`. Helper scripts live in `skills/<name>/scripts/` and are covered by tests and evidence hashes.
- `profiles/` holds numbers: design languages, manufacturing processes, protected interfaces and the workstation profile. A value that describes one machine or one setup belongs here, not in a knowledge article.
- `labs/` holds reproducible experiments with their own inputs, outputs and hashes. Each lab is listed in `labs/catalog.json`.
- `toolbox/` holds working tools collected from projects (print pipeline, mesh checks, scan tracing) and, in `toolbox/solidcraft/`, the house reference for SolidCraft with its tested examples. Its README states for each tool where it came from and what was actually run; a new project calls a tool from there instead of copying it again. A statement in the house reference marked as run is a check in `toolbox/solidcraft/examples/run-examples.sh`; add the check when you add the statement.
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

## Using Toolroom for CAD work

Use the [workflow entrypoint](skills/cad-workflow/SKILL.md) for CAD tasks spanning stages or backends. For an isolated edit, print-file preparation or documentation change, use the relevant skill directly. Load linked material only when it affects the task, and reuse already-read guidance within the session.

For independent routine work, the [delegation rules](knowledge/workflow/delegation.md) and [team profile](profiles/agents/cad-team.yaml) define narrow worker scopes. Critical engineering decisions remain with Astra at the highest available quality. The lead owns the user-facing delivery through acceptance and handoff; a worker's completed preparation is an internal milestone.
