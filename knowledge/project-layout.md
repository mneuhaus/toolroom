# CAD project files and revisions

For a multi-session design, use a small set of predictable directories. Preserve
an established layout unless cleanup is requested; a tiny prototype need not
start with empty scaffolding. Use the chosen CAD backend rather than introducing
a build123d/uv project for an Onshape-only task.

```text
README.md                  current revision, links and useful commands
AGENTS.md                  local filing conventions when useful
src/                       maintained CAD source and parameters
scripts/                   active build, verify, render and export tools
docs/                      assembly notes and HANDOFF.md
reference/                 original CAD, measurements and vendor references
exports/<revision>/        final STEP, STL and 3MF deliverables
output/<revision>/         renders, gallery, previews and readable reports
var/state/                 durable cloud IDs and publication state
var/cache/                 API responses, raw tessellation, generated profiles
var/logs/                  request and slicer logs
archive/                   superseded revisions and obsolete workflows
vendor/                    third-party tools, only when present
```

`var/state/` is not disposable: losing document/element/version or publication
IDs can lead to duplicate documents or publishing over the wrong artifact.
Caches may still be needed for offline verification; document how to recreate
them before suggesting deletion. Do not collect another set of intermediate
JSON files in the project root after reorganizing it.

## Paths and revisions

Anchor active script paths to the project root, not the shell working directory.
Keep generated-data routing in a shared helper where practical. Adapt watchers,
imports, sibling tools, export manifests and documentation links when paths move;
copying an old root-relative watcher into `scripts/` alone is not sufficient.
Update the current README and handoff to point at actual maintained entrypoints.

Bind raw geometry caches to source revision/microversion and relevant export
settings as well as part ID. A part can keep its ID while its geometry changes.
Make “current source” distinguishable from earlier generator drafts. Archive
historical workflows without rewriting their old assumptions into the new design.
Name revised parts/reports consistently and preserve which revision was printed.

## Onshape tabs, variants and shared sources

When document cleanup is requested, use readable English functional names and
folders for working assemblies, printable parts, hardware/reference sources and
archive. Add a servo/size prefix when an interface is variant-specific; leave
truly interchangeable parts shared. Keep print revisions in the revision table,
part marking and export names without creating a new tab for every small edit.

Inventory element IDs and dependencies before archiving or deleting a variant.
An apparently unused Feature Studio, imported source or generated BOM can still
back a working part or assembly. Moving a tab to an archive does not remove that
dependency; preserve the source. An explicitly discarded branch should leave
active build manifests and exports, with the disposition recorded in the handoff.

Compare semantic feature definitions and geometry when checking a rename/move:
Onshape may update import namespaces or serialized query-node IDs. Such metadata
changes are not automatically user geometry edits, but must not be used to waive
real sketch/constraint changes. Audit the resulting assembly references and
retain the old/new element map; historical exact-name audits may need updating.

## Reorganizing an existing project

Inventory old/new paths before moving; detect destination collisions. Preserve
original content, and use hashes for CAD sources, final exports and large sets
of moved files. Back up edited scripts/manifests where no version-control baseline
exists. Update absolute paths in manifests consumed by tooling, while keeping
historical logs/snapshots intact and clearly labelled.

Validate proportionally: syntax and local imports, report decoding, gallery
creation and path resolution from another working directory. A mesh-generation
stage can run in a temporary layout and compare hashes with existing exports.
Do not rebuild live CAD, republish a gallery or start a print to test a local
folder cleanup. Provide a readable top-level index and an old/new path mapping
for a substantial migration.

Worked example: `~/Workspace/cad/spar-key-z-axis/README.md` and
`docs/reorganization/` in that project. Its exact folder names are a convention,
not a reason to migrate unrelated projects.
