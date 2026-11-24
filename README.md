# Toolroom

A CAD knowledge base and skill framework for AI-assisted design. Toolroom keeps the reusable know-how of designing, checking and manufacturing parts in one place so that an agent loads the right rules for the task instead of guessing.

The name is the workshop metaphor: a toolroom is where the jigs, gauges and fixtures live that make the shop's work repeatable. Here the jigs are **skills**, the gauges are the **knowledge base** with its verification rules, and the fixtures are **profiles** that describe a machine, a style or a workstation. Toolroom is not a CAD kernel and does not run machines. It tells an agent what to do, where the reasoning is, and which evidence counts.

**Reading as a person:** open [`index.html`](index.html) for the offline documentation, or read [the architecture](docs/architecture.md). Local preview:

```sh
uv run python tools/serve.py
```

Then open `http://127.0.0.1:4176`.

## Start here as an agent

Read these six pages in this order, then stop: this page, [the conventions](AGENTS.md), [the skill list](skills/README.md), [the workflow entrypoint](skills/cad-workflow/SKILL.md), [the toolbox](toolbox/README.md) and [the SolidCraft house reference](toolbox/solidcraft/README.md). Load anything else only when the task needs it; the repository is too large to read whole.

**Set up once**

1. Check what the machine has and report what is missing instead of working around it: SolidCraft (the tools call `/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli`; its own skills ship with the app), `uv`, `node`, and Bambu Studio for build plates.
2. Install the skills by symlinking each folder from the checkout, for example `ln -s "$PWD/skills/cad-fdm-design" ~/.claude/skills/cad-fdm-design`. A skill folder is an entrypoint, not a standalone package: it links into `../../knowledge` and `../../profiles`, and a copy breaks those links. For new printed parts take `cad-workflow`, `cad-fdm-design`, `cad-joints`, `cad-design-system` and `scan-reverse-engineering`; the Onshape, Build123d and Fusion skills serve existing projects. Do not overwrite a skill that is already installed under the same name.
3. Run `uv run python tools/validate.py`, `toolbox/check/selftest.sh` and `toolbox/solidcraft/examples/run-examples.sh`. The last two need SolidCraft, the last one also Bambu Studio. When one fails, find the cause (a path, another SolidCraft version, a missing program) before changing anything.

**Build a part**

1. Model it in SolidCraft with SolidCraft's own skills, and load `cad-fdm-design` for print orientation, fits and house style. The house reference says which command is the tried way for screw joints, bosses, threads, honeycomb and scans.
2. Store the print orientation in the design (`body.print_face`).
3. Run [`toolbox/check/check design.sc`](toolbox/check/README.md) before printing. It lists thin spots, tiny gaps and overlaps as hints, not as rules; judge each one and say which matter.
4. Build the plate and slice it as described in [print hand-off](toolbox/solidcraft/print-handoff.md), and deliver the normal 3MF.

**What belongs to one person's setup**

- The tools assume macOS with the programs under `/Applications`. [The A1 profile](profiles/manufacturing/fdm-bambu-a1-0.4.yaml) is for a Bambu Lab A1 with a 0.4 mm nozzle and is marked uncalibrated; for another printer add a profile next to it from the template instead of changing this one. The same goes for the workstation profile in [`profiles/environment/`](profiles/environment/README.md) (endpoints, default printer, library paths).
- A statement in the house reference marked as run was run on the SolidCraft version named there. On another version, what `run-examples.sh` reports on that machine counts.
- House-style numbers (R4.2 fillets, 0.42 mm chamfers, the M3 hybrid hole) are the owner's defaults. For another user they are proposals.
- The Onshape bridge, the sorting machine, `fsocct`, `pruefstand` and the delegation rules with their team profile describe the owner's projects and agent team. Skip them unless the task is about them.
- Keep your own projects outside this repository, one folder per project. Change Toolroom itself only when asked to.

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

## Installed skill copies

Skills installed under `~/.claude/skills` before this repository existed stay independent copies until they are replaced by symlinks; `provenance/originals/` preserves their entrypoints for comparison.

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
