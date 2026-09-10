# Project integration

Precedence: explicit user requirements and protected interfaces → verified native geometry and purchased hardware → calibrated process data → visual rules → uncalibrated defaults. Resolve incompatibilities in a per-part decision ledger, with evidence. Do not invent an approval requirement.

A project entry point should identify:

- `design_language`: file with ID, colour roles, selected edge/label parameters, and source/calibration status.
- `manufacturing`: file with actual process setup plus separately labelled screening thresholds.
- `interfaces`: file with immutable or intentionally revisioned dimensions and access requirements.
- `part_manifest`: file with part identity, native-to-print matrix, export hash and orientation.
- `evidence`: native checks, toolpath review, actual physical tests, and any unresolved limits.

Checker-compatible manufacturing keys: `id`, `build_volume: [x,y,z]`, `walls: {hard_min, min_thickness}`, `overhang: {max_angle_deg, max_bridge}`, optional `expected_components` and `require_bed_contact`. These screening limits do not size a load-bearing section. XY placement, brims, supports and purge objects still require a plate check. A hypothetical quarter-turn fit is reported separately and is not counted as the given orientation fitting.

Use sRGB hex values for screen appearance; if CAD expects linear RGB, record both and validate conversion. A screen approximation is not a physical RAL match. Record per-part colours independently of the number of printer toolheads or AMS slots. A single-filament plate cannot manufacture three colours at once without a revised print strategy.

Keep human-readable documentation and machine-readable profiles consistent with automated checks. Never assert measured fit, strength, colour match or printability from a profile alone.
