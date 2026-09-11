# Profiles

Design language, manufacturing and mechanical interfaces are maintained independently.

- `design-language/`: Instrument, Soft Consumer, Rugged Industrial, the historical Workshop 0.42 family and [Mosey](../knowledge/design/mosey.md).
- `manufacturing/`: generic starting profiles for FDM, CNC, laser cutting and SLA.
- `interfaces/`: an illustrative interface profile showing the structure of protected requirements.
- `agents/`: [task-level CAD team preferences](agents/cad-team.yaml), context allowances and critical-role boundaries; no model-quality calibration.
- `environment/`: one machine's local facts — endpoints, installed runtimes, default profiles.

The [environment layer](environment/README.md) is deliberately separate from the other three. Design language, manufacturing and interface profiles describe a subject and can be reused by anyone; an environment profile describes a single workstation and is expected to be replaced. It records where a CAD runtime is installed, which port a local adapter listens on and which manufacturing and design-language profiles that machine defaults to, so no skill entrypoint has to hard-code a path or a port. Nothing there calibrates anything: a default printer entry names the machine in the room, it does not establish a tolerance.

Imported generic numbers are starting values. A field name such as `measured_thickness` does not turn an inherited default into a measurement. Source, material, machine, date, measurement method and result must establish the actual calibration.

The website's profile workbench illustrates roles and consequences schematically. It does not modify a CAD file or approve a manufacturing job.

## Mosey 0.1

[Mosey](design-language/mosey.yaml) was derived from 18 selected form studies on mosey.camera. It combines calm sculptural bodies, large tactile controls and colours assigned by function. Three form variants support soft volumes, broad facets and useful supporting shells.

The [illustrated study](../knowledge/design/mosey.md) distinguishes observations, our design rules and proposed CAD values. The references are AI-assisted concepts. Numbers, screen colours and mechanisms have not been physically calibrated.
