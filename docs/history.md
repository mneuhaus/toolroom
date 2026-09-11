# History: consolidation and restructure

## 10 September 2026, morning: consolidation

The eight previously installed skill collections were imported into one repository with their origins hashed. Entrypoints were shortened; the detailed guides stayed as identified field notes. A workflow skill and a joints skill were added. Assembly, fits and retention, project layout and slicer preparation each received one shared reference.

### A shared mesh checker

Two project versions of the checker contained different improvements. The consolidated version keeps:

| Origin | Retained behaviour |
| --- | --- |
| Z-axis project | Body integrity, positive volumes, connected components, actual print pose, bed contact, incomplete analysis and explicit STEP inlays |
| Distributor project | Rasterisation within individual triangle bounding boxes instead of a large points-by-triangles intermediate array |
| Distributor project | Classifying a narrow underside as a lip only after verifying attachment at its boundary |
| Both | Regressions for analysis failures, thin walls and known failure cases |

Status values are `no_findings`, `review` and `incomplete`. The older regression tests use this shared naming while keeping their geometric expectations.

### Profile resolution as a helper

The resolver recursively resolves parents and ordered `include` references. Missing references, ambiguity and cycles are errors. It returns values and a traceable source order. It does not construct machine-specific G-code routines.

### Differences kept visible

The historical Workshop edge family is a separate profile. Instrument, Soft Consumer, Rugged Industrial and Mosey remain distinct design languages. Personal machine dimensions are not universal settings.

## 10 September 2026, afternoon: restructure into Toolroom

The consolidated edition was correct but hard to navigate: the knowledge lived partly in `knowledge/`, partly in skill references and partly in docs; seven personal project case studies carried most of the reasoning as narrative; the website and reading edition mirrored that mix.

### What changed

- **Name.** The repository became Toolroom. Package name, site branding and this documentation follow.
- **Knowledge base in sections.** `knowledge/` was split into `foundations/`, `workflow/`, `construction/`, `manufacturing/`, `design/` and `lessons/`, with `knowledge/catalog.json` as the single index. The generic manufacturing references of the design-system skill moved to `knowledge/manufacturing/`. The joint reference review and the Mosey study moved from `docs/` into the knowledge base.
- **Case studies removed, lessons kept.** The seven project case studies and their project images were removed. Their transferable rules were distilled into [Lessons from projects](../knowledge/lessons/project-lessons.md), and the construction-pattern table names typical applications instead of private projects.
- **Labs instead of examples.** The two reproducible experiments, the Printed Joints Lab and the checker lab, moved to `labs/` with `labs/catalog.json`.
- **Skills as thin entrypoints.** Each `SKILL.md` follows one shape: use when, procedure, knowledge, references, environment. Imported guides are named `references/field-notes.md`. A `skills/README.md` explains installation and layering.
- **Workstation profile.** Endpoints, library paths and default machine and style of the owner's setup moved from field notes into `profiles/environment/`, with a template for other setups.
- **Repository docs.** `docs/` now covers only the repository itself. The consolidation notes became this history.
- **Validation records.** Screenshots and site-validation records of the earlier layout were removed; the build, content and test records are regenerated. The published reading edition of the morning predates the restructure and was not re-uploaded.

The complete old-to-new path map is `provenance/restructure-2026-09-10.json`.

## Open topics

1. Should CAD runtimes remain separate projects or become framework packages later?
2. Which small independent reference model should demonstrate the first complete Onshape, FDM and manual workflow?
3. Which design languages and machine profiles should become maintained defaults?
4. Which physically measured coupons should replace values that are still assumptions?
5. Which parts of Toolroom should receive a public licence, and under which name-space for skills?

## 11 September 2026: flatter navigation and structured skill pages

The site's sidebar became an explorer tree: every skill, every knowledge article by section, every lab and the profile and repository documents are one click away, and the group of the current page opens automatically. Skill entrypoints render from their fixed shape into a structured page: category and description, a "use when / not for" pair, numbered step cards, and link cards for the knowledge and references they load. Knowledge articles open with a summary card that names the section, the reading time and the skills that load the article. The overview ends with the whole map. The Markdown sources did not change; only `site/src/` did.

## 12 September 2026: pivoting snap latches

SnapLock V3 (Hugo, MakerWorld) turned out to be a storage box with pivoting latches, not a tile system. It became its own construction article on latches that close two parts under preload, with the reviewed example, design rules, print poses and the licence limits that forbid copying its geometry. The research archive and the token-level read of the Fusion file stay local; the provenance manifest records the sources.
