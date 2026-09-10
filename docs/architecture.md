# Architecture

Toolroom separates four kinds of content that are easy to mix up: reasoning, procedure, data and evidence. Each has one home, one catalog and one way of being verified.

## Layers

| Layer | Directory | Responsibility | Prevents |
| --- | --- | --- | --- |
| Knowledge | `knowledge/` | Rules with their reasons, evidence and limits, independent of any CAD backend | Restating the same rule in five skills with five wordings |
| Skills | `skills/` | Thin entrypoints: when to load which knowledge, and how to execute in Onshape, Build123d or Fusion | Loading every tool and every reference for every request |
| Profiles | `profiles/` | Design languages, manufacturing processes, protected interfaces and the workstation profile | Presenting one person's printer or style as a universal rule |
| Labs | `labs/` | Reproducible experiments with their own inputs, outputs and hashes | Documentation without anything that can be re-run |
| Repository docs | `docs/`, `provenance/`, `validation/` | How Toolroom is organised, where content came from, what was actually checked | Losing track of origins after imports and moves |

## How a task travels

1. The agent matches a task to a skill entrypoint. The entrypoint states when it applies and when it does not.
2. The entrypoint names the knowledge articles to read for this task, the profile to resolve, and the backend references it needs.
3. The knowledge article states the rule and the evidence the result must carry. The profile supplies numbers with provenance.
4. The result is bound to its inputs, revision and geometry hash. Verification states are `no_findings`, `review` or `incomplete`; "not run" is a separate state and never a success.

A layout change of a manual does not require a CAD rebuild. A different design language does not authorise moving a screw. A larger print bed does not merge parts the user wants modular. The layers make such non-consequences explicit.

## Three independent profile roles

The design language defines colour roles, selected edges, labelling and form families. The manufacturing profile describes the actual process and, separately, provisional screening thresholds. The interface profile protects fastenings, fits, motion envelopes and load paths. The workstation profile describes endpoints, library locations and defaults of one specific setup. A change in one role does not change another.

## Where does a new piece of content go?

| You have | Put it in | And register it in |
| --- | --- | --- |
| A rule and its reason | `knowledge/<section>/` | `knowledge/catalog.json` |
| A procedure for one backend | `skills/<name>/references/` | The skill's `SKILL.md` |
| A number that describes a machine, material, style or setup | `profiles/` | The profile's own YAML |
| An experiment others can re-run | `labs/<name>/` | `labs/catalog.json` |
| Something learned from a project | `knowledge/lessons/` as a generic rule with a one-line origin | `knowledge/catalog.json` |
| A change to the repository layout | `provenance/` record with the old and new paths | `docs/history.md` |

## Kept out of scope

Toolroom adds no CAD kernel, no workflow execution engine and no cloud synchronisation. Native applications keep their APIs. The bundled helpers are the consolidated mesh and STEP screeners, the profile resolver, the joints verifier and the documentation tools. Cloud adapters and CAD runtimes are separately installed; see [scope](scope.md).

The website reads only Markdown and the catalogs. Viewing it needs neither a build server nor an internet connection.
