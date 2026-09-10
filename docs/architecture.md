# Framework architecture

The framework organises a shared CAD vocabulary and capabilities that can be combined as needed. Its smallest useful unit is a concrete task with defined inputs and a traceable result.

## Five layers

| Layer | Responsibility | Prevents |
| --- | --- | --- |
| Core | Source, revision, units, identity and evidence | Confusing an old generator with the current native model |
| Skills | Selecting and executing the appropriate workflow | Loading every tool for every request |
| Adapters | Backend operations and error handling | Mixing transport details into general design rules |
| Profiles | Design and manufacturing parameters with provenance | Presenting personal settings as universal material rules |
| Examples and checks | Observable behaviour and known failure cases | Documentation without verifiable applications |

## Three independent profiles

The design language defines colour roles, selected edges, labelling and form families. The manufacturing profile describes the actual process and, separately, provisional screening thresholds. The interface profile protects fastenings, fits, motion envelopes and load paths.

A profile change affects only its own responsibility. A different colour must not change a screw's insertion direction. A larger print bed does not authorise silently merging parts that the user wants to keep modular.

## One maintained source per rule

Shared assembly, fit, project layout and print preparation rules live in `knowledge/`. Backend details stay with their skill. Imported field notes are identified as historical sources; their personal defaults do not automatically become requirements.

This workbench does not overwrite the previously installed skills. Future framework changes are maintained in this repository. Installation into an agent host is a separate, later step.

Until then, use the framework as a complete directory. Individual skill folders are not independent installation packages because they refer to `knowledge/`, `profiles/` and other skills. A future installer must include those shared resources and preserve or resolve their references.

## Keeping the scope focused

The framework adds no CAD kernel, general workflow execution engine or automatic cloud synchronisation. Native applications retain their existing APIs and capabilities. Concrete helpers cover the consolidated checkers, profile resolution, the native joints example and local documentation.

The website obtains its content from Markdown and the catalogues. Text is included in the static build, so viewing it requires neither a build server nor an internet connection.
