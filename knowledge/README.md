# Knowledge base

The knowledge base holds the reasoning behind the skills: what a rule is, why it exists and what evidence it needs. It is backend-independent. Backend details (FeatureScript idioms, Build123d calls, slicer menus) stay with the skill that uses them under `skills/<name>/references/`.

`catalog.json` in this directory is the single maintained index. The website, the reading edition and the validator read it. Add an article by writing the Markdown file and adding one catalog entry with `path`, `title`, `summary` and `section`.

## Sections and reading order

| Section | Read when | Articles |
| --- | --- | --- |
| `foundations/` | Before any multi-step task | [The shared core](foundations/core.md) · [What a check establishes](foundations/verification.md) |
| `workflow/` | Combining tools or starting a longer project | [Combining tasks](workflow/recipes.md) · [Project layout and revisions](workflow/project-layout.md) · [Bounded delegation](workflow/delegation.md) |
| `construction/` | Designing parts that meet, move or hold | [Assembly, access and load paths](construction/assembly-review.md) · [Fits, preload and latches](construction/fits-and-retention.md) · [Joints](construction/joints.md) · [Panels and elastic clips](construction/joints-panels-and-clips.md) · [Clip-in-pocket tile joints](construction/tile-clip-joints.md) · [Reusable patterns](construction/patterns.md) |
| `manufacturing/` | Choosing a process or preparing a job | [Slicer preparation](manufacturing/print-preparation.md) · [FDM](manufacturing/fdm.md) · [Print orientation](manufacturing/print-orientation.md) · [Laser cutting](manufacturing/laser.md) · [CNC](manufacturing/cnc.md) · [SLA](manufacturing/sla.md) |
| `design/` | Applying or defining a design language | [Mosey](design/mosey.md) |
| `simulation/` | Simulating or animating a mechanism from CAD | [From CAD assembly to rigid-body simulation and replay](simulation/cad-to-physics-simulation.md) |
| `lessons/` | Looking for the rule behind a past mistake | [Lessons from projects](lessons/project-lessons.md) |

## What belongs here and what does not

- **Here:** a rule, its reason, the failure it prevents, the evidence that establishes it, and its limits. Generic worked examples are welcome.
- **In `skills/`:** when to load which knowledge, the concrete procedure in a backend, and imported field notes.
- **In `profiles/`:** numbers that describe a machine, a material, a style or a workstation. A knowledge article may quote a value as an example but never as the maintained source of it.
- **In `labs/`:** reproducible experiments with their own evidence files.
- **Not here:** project narratives, personal defaults presented as rules, or results that this repository did not produce. Distil the rule into `lessons/` and cite the origin in one line.

## Conventions

One maintained source per rule. If two articles would state the same rule, one states it and the other links. Keep nominal design values, calibrated measurements and historical example dimensions distinct. State what remains unverified. English throughout; a source snapshot keeps its original language.
