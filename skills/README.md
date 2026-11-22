# Skills

A skill in Toolroom is a **thin entrypoint**, not a manual. It says when the task
matches, what to do in order, and where the real material lives: the knowledge base
for the reasoning, the profiles for the data, its own `references/` for the imported
detail. An agent host loads it only when the task matches its description, so the
entrypoint stays short enough to be worth loading and points at everything else.

Every entrypoint has the same shape: front matter (`name`, `description`), an H1, a
"use when / do not use when" paragraph, a procedure, a **Knowledge** list, a
**References** list, and where applicable an **Environment** line pointing at
[`profiles/environment/local-workstation.yaml`](../profiles/environment/local-workstation.yaml).

## The eleven skills

| Skill | Use when |
| --- | --- |
| [cad-workflow](cad-workflow/SKILL.md) | A CAD job spans stages or tools and needs routing, source authority and evidence. |
| [onshape-cad](onshape-cad/SKILL.md) | Native Onshape geometry is built or revised: FeatureScript, retrofits, variants, interface checks. |
| [onshape-bridge](onshape-bridge/SKILL.md) | Live Onshape work runs over the configured session bridge: health, budgets, timeouts, artifacts. |
| [onshape-build-manuals](onshape-build-manuals/SKILL.md) | An illustrated assembly manual is generated from CAD with stages, inventory and a render recipe. |
| [cad-khana](cad-khana/SKILL.md) | A local Build123d script is written or its assembly diagnostics are interpreted. |
| [fusion360](fusion360/SKILL.md) | A Fusion document is rebuilt from its part program with volume balances and native checks. |
| [cad-fdm-design](cad-fdm-design/SKILL.md) | A part is designed or prepared for FDM: print pose, fits, assembly access, slicer output. |
| [cad-joints](cad-joints/SKILL.md) | The connection between two parts is the design problem: snaps, slides, dovetails, retention. |
| [cad-design-system](cad-design-system/SKILL.md) | A reusable design language is defined, applied to a part family or screened against a process. |
| [cad-physics-simulation](cad-physics-simulation/SKILL.md) | A CAD mechanism handling loose parts is simulated or animated, or control software runs against a virtual machine. |
| [scan-reverse-engineering](scan-reverse-engineering/SKILL.md) | A 3D scan has to become measured, parametric CAD. |

## Backend

SolidCraft is the CAD backend for new work since 22 November 2026. Its skills ship with SolidCraft and are not part
of this repository; how this workspace uses it is recorded in the
[house reference](../toolbox/solidcraft/README.md). The Onshape skills stay in use for the sorting machine. The
Build123d and Fusion skills are kept for the projects built with them.

## Layering

**Entrypoint → references → knowledge.** The entrypoint carries the procedure and
the rules that must not be missed. `references/` holds skill-specific detail,
including the `field-notes.md` imported from the previously installed skills — that
is historical evidence, kept verbatim, and its numbers are examples rather than
rules. `../knowledge` holds the reasoning that outlives any one skill, and
`../profiles` holds the data: manufacturing, design language, interfaces and the
[environment layer](../profiles/environment/README.md).

A skill folder is therefore **not a standalone package**. Entrypoints link into
`../../knowledge` and `../../profiles` on purpose; copying one folder out of the
repository leaves those links dangling.

## Installing into an agent host

Symlink the whole folder, so the relative links still land inside the repository:

```sh
ln -s "$PWD/skills/onshape-cad" ~/.claude/skills/onshape-cad
```

Clone or copy the repository first if it is not already where it should live, then
symlink from there. Skills already installed under `~/.claude/skills` are
independent copies until they are migrated; changes here do not reach them.

Hosts that read the OpenAI agent format pick up `agents/openai.yaml` inside a skill
folder, where one exists — display name, short description and default prompt.
