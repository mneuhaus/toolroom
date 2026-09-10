# Labs

A lab is a **reproducible, non-personal experiment with its own evidence**. It exists to answer one narrow question — what does this joint principle actually constrain, what does this checker actually detect — using geometry and program output that anyone can rebuild from this repository. Labs are deliberately not project case studies: there is no client, no deadline and no product history in them. Lessons that came out of real projects live in [`knowledge/lessons/`](../knowledge/lessons/project-lessons.md) instead.

Each lab keeps its inputs, its script and its recorded results next to each other, so a result can always be traced back to the source that produced it. [`catalog.json`](catalog.json) is the maintained list; the documentation reads it rather than scanning the folders.

## The two labs

### [Printed Joints Lab](printed-joints/README.md)

Eight native joint principles built as parametric teaching models in Onshape, with assembly paths, a parametric clearance and traceable geometry verification. Evidence: 16 native models, eight STEP exports and a frozen native check report.

```sh
node labs/printed-joints/onshape.mjs   # rebuilds the native models (needs a live Onshape session)
uv run python labs/printed-joints/verify.py   # re-checks the exported STEP geometry
```

### [Checker lab](checker-lab/README.md)

Four generated test geometries — a closed block, a thin plate, a wrong print pose and a detached island — run through the consolidated mesh checker. Evidence: the STL inputs, the raw JSON reports and a summary with input hashes.

```sh
uv run python labs/checker-lab/build.py
```

Regenerate the site afterwards (`uv run python tools/build_site.py`) so the documentation shows the current results.

## What a lab result is not

A lab result is evidence about **geometry or about a helper program**, never a physical acceptance. Nothing here establishes fit, strength, printability on a specific machine or fitness for a load. A passing check means the stated conditions held for the stated inputs, and nothing more — see [what a check establishes](../knowledge/foundations/verification.md).
