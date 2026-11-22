# Toolroom

A CAD knowledge base and skill framework for AI-assisted design. Toolroom keeps the reusable know-how of designing, checking and manufacturing parts in one place so that an agent loads the right rules for the task instead of guessing.

The name is the workshop metaphor: a toolroom is where the jigs, gauges and fixtures live that make the shop's work repeatable. Here the jigs are **skills**, the gauges are the **knowledge base** with its verification rules, and the fixtures are **profiles** that describe a machine, a style or a workstation. Toolroom is not a CAD kernel and does not run machines. It tells an agent what to do, where the reasoning is, and which evidence counts.

**Start:** open [`index.html`](index.html) for the offline documentation, or read [the architecture](docs/architecture.md). Local preview:

```sh
uv run python tools/serve.py
```

Then open `http://127.0.0.1:4176`.

## Map

| Directory | Holds | Answers |
| --- | --- | --- |
| [`knowledge/`](knowledge/README.md) | Backend-independent rules in six sections: foundations, workflow, construction, manufacturing, design languages, lessons | Why a rule exists and what evidence it needs |
| [`skills/`](skills/README.md) | Thin entrypoints with backend-specific references and helper scripts | When to load what, and how to do it in Onshape, Build123d or Fusion |
| [`profiles/`](profiles/README.md) | Design-language, manufacturing, interface and workstation data in YAML | Which numbers apply to this machine, style or setup |
| [`labs/`](labs/README.md) | Reproducible experiments with their own evidence | What a helper or a joint principle actually demonstrates |
| [`docs/`](docs/architecture.md) | Architecture, scope, history and provenance of this repository | How Toolroom itself is organised and why |
| `tools/`, `tests/` | Site builder, validator, reading-edition builder and regression tests | How to rebuild and check the repository |
| [`toolbox/`](toolbox/README.md) | Working tools collected from earlier projects: build plates and slicing for Bambu printers, printability checks on meshes, scan tracing; and the [SolidCraft house reference](toolbox/solidcraft/README.md) with tested examples | Which tool already does this job, how far it was tested, and which SolidCraft command is the house way |
| [`fsocct/`](fsocct/README.md) | Experimental local FeatureScript interpreter with an OpenCascade backend | How to evaluate a supported FeatureScript subset and export STEP/STL offline |
| `provenance/`, `validation/` | Import hashes, original skill snapshots, reference manifests and the results of checks that were actually run | Where content came from and what was verified |

The rule of thumb: a **why** goes into `knowledge/`, a **when and how** into `skills/`, a **number** into `profiles/`, an **experiment** into `labs/`, and anything about the repository itself into `docs/`.

## CAD backend

Since 22 November 2026 SolidCraft is the CAD backend for new work; its own skills (`solidcraft-modeling`,
`solidcraft-editing`, `solidcraft-checking`, `solidcraft-mechanisms`) ship with SolidCraft and are not part of this
repository. The knowledge base, the profiles and the [toolbox](toolbox/README.md) do not depend on a backend and stay
in use. The Onshape skills and `knowledge/onshape` stay in active use for the sorting machine, which continues in
Onshape. The Fusion and Build123d skills and `fsocct` are kept for the existing projects built with them and are no
longer the default route.

## Shared CAD work basis

[Start here](docs/cad-work-basis.md) for the bounded worker, source-extraction and print-package commands. These keep routine work small while preserving critical CAD decisions and evidence requirements.

## Using it with an agent

Skill folders are entrypoints, not standalone packages: they link into `../../knowledge` and `../../profiles`. Install them by symlinking the folder from a checkout, for example `ln -s "$PWD/skills/cad-fdm-design" ~/.claude/skills/cad-fdm-design`, so the links keep resolving. The older skills already installed under `~/.claude/skills` stay independent until they are replaced; `provenance/originals/` preserves their entrypoints for comparison.

The workstation profile in `profiles/environment/` describes one specific setup (endpoints, default printer, library paths). Another user replaces it with their own copy of the template.

## Rebuild the documentation and run the checks

```sh
uv sync
uv run python labs/checker-lab/build.py
uv run python tools/build_site.py
uv run python tools/validate.py
uv run python -m unittest discover -s tests -v
```

The HTML is generated from Markdown and the three catalogs (`catalog.json`, `knowledge/catalog.json`, `labs/catalog.json`). Edit those sources, never `site/data.js`. The validator checks every local link and heading anchor, the catalog contracts, image and evidence hashes, and that the generated files are current.

## Reading edition

`tools/build_postplan.py` produces a single-file, script-free reading edition under 512 KiB. Uploading it to Postplan is a separate, public step and is not part of the build. The edition published on 10 September 2026 at `https://hn0ai0tcfhrd.postplan.dev` predates the restructure and shows the earlier layout with case studies.

## Status

This is a local working edition, version 0.1. The helpers have validation reports. The Printed Joints Lab was built natively in Onshape and checked geometrically. Nothing here is a physical acceptance result. Design and manufacturing profiles marked generic are uncalibrated starting values. See [scope](docs/scope.md), [history](docs/history.md) and [provenance](docs/provenance.md).
