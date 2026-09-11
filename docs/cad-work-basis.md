# Toolroom as the shared CAD work basis

Toolroom now supplies a common procedure for economical routine work while keeping critical decisions with the lead model. Start with [CAD workflow](../skills/cad-workflow/SKILL.md); use the [delegation rules](../knowledge/workflow/delegation.md) only when a task benefits from a bounded worker. Project data and native CAD remain authoritative in their originating projects.

## Available commands

| Need | Maintained command | What remains with the lead |
| --- | --- | --- |
| A small source-bound worker assignment | [Worker jobs](../skills/cad-workflow/references/worker-jobs.md) | Scope, protected requirements and critical acceptance |
| Short evidence instead of entire webpages | [Source extraction](../skills/cad-workflow/references/source-extraction.md) | Interpretation and applicability of critical sources |
| Reusable native 3MF preparation and checks | [Print packages](../skills/cad-fdm-design/references/print-package.md) | Print poses, actual layers/support and critical release |

The [team profile](../profiles/agents/cad-team.yaml) assigns routine research/preparation to Terra, bounded implementation to Sol and critical CAD work to Astra at the highest supported quality. It records task-level preferences; it does not change account defaults or enforce a process sandbox. The host dispatches workers using the brief and actual available runtime. No model-quality equivalence or percentage saving has been established by these helper tests.

## Adoption and validation

The surrounding CAD workspace has a short `AGENTS.md` routing to this checkout. Existing installed skill copies and project-local instructions are preserved. A host using another workspace can use the [installation guidance](../skills/README.md#installing-into-an-agent-host) or point its workspace instructions at the checkout. Copying individual skill folders without the knowledge/profile tree breaks their relative links.

New scripts are covered by the repository test suite and evidence hashes in `validation/tests.json`. Site build and link validation include their documentation. Keep new capabilities behind the same acceptance rules as the tasks they replace: scripts establish specific file/format properties, while engineering and physical findings retain their own states.

This is a local integration. No cloud upload, printer dispatch, global model switch or native CAD source modification is part of it. Python provides the initial adapters. Port a measured CPU or memory bottleneck to Rust only after the shared command and its regression behavior are established.
