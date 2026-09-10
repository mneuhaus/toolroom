# What has been consolidated

## Concise entrypoints and shared technical knowledge

The original eight skill collections are bundled in one directory. The workflow skill selects the relevant branches; the joints skill adds connection selection and assembly-path reasoning. Assembly, fits and retention, project layout, and Bambu/Orca preparation each have one shared reference. Detailed imported guides remain available as clearly identified field notes.

## A shared mesh checker

The Sparky and Distributor versions contained different improvements. The consolidated version includes:

| Origin | Retained behaviour |
| --- | --- |
| Sparky | Body integrity, positive volumes, connected components, actual print pose, bed contact, incomplete analysis and explicit STEP inlays |
| Distributor | Rasterisation within individual triangle bounding boxes instead of a large points-by-triangles intermediate array |
| Distributor | Classifying a narrow underside as a lip only after verifying attachment at its boundary |
| Both | Regressions for analysis failures, thin walls and known failure cases |

Status values are `no_findings`, `review` and `incomplete`. The older Distributor tests use this shared naming while retaining their geometric expectations.

## Extracting profile resolution from the project

The helper recursively resolves parents and ordered `include` references. Missing references, ambiguity and cycles are errors. It returns values and a traceable source order. It does not construct machine-specific G-code routines.

## Keeping differences visible

The historical Workshop edge family is a separate profile. Instrument, Soft Consumer, Rugged Industrial and Mosey remain distinct design languages. Personal machine dimensions are not treated as universal settings.

## Topics for the next discussion

1. Should CAD runtimes remain separate projects or become framework packages later?
2. Which small independent reference model should demonstrate the first complete Onshape/FDM/manual workflow?
3. Which design languages and machine profiles should become maintained defaults?
4. Which physically measured test coupons should replace values that are still assumptions?
5. Which examples and original contributions should receive a public licence later?

These topics are available in the website's Roadmap section. They do not block local discussion or use of the documentation.
