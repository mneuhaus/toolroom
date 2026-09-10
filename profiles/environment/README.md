# Environment profiles

This layer describes **a machine**, not a subject. It holds the facts that are true
of one workstation and of nothing else: where a runtime is installed, which port a
local adapter listens on, which printer and which profiles that machine defaults to.

It exists so the rest of the framework can stop repeating them. A skill entrypoint
says "read the endpoint from the environment profile"; the knowledge base explains
why a session bridge or a print pose matters; this file says the bridge is on
`127.0.0.1:8317` and the app lives in `~/Workspace/onshape-app`. Change machines and
only this layer changes.

## Files

- [`local-workstation.yaml`](local-workstation.yaml) — the framework owner's macOS
  setup. Every value was extracted from the imported field notes on 2026-09-10 and
  names the file it came from in its `source` field.
- [`_template.yaml`](_template.yaml) — copy this to describe your own machine.

## How to use it

- A skill reads this profile for endpoints, start commands, installed library paths
  and default profile names. It does not read design rules from here.
- Nothing in this layer is authoritative about geometry, tolerances or process
  limits. A default printer entry does not calibrate anything; a manufacturing
  profile still has to be calibrated on its own terms.
- A recorded value can go stale. Ports, plugin versions and installed slicer
  profiles drift, so probe before trusting: the health path is cheaper than a failed
  batch.

## If you are not the owner

Replace `local-workstation.yaml` — do not edit around it. Copy `_template.yaml`,
fill in your own paths and endpoints, delete the sections for tools you do not run,
and point the skills at your file. The rest of the framework carries no assumption
that the owner's machine exists.
