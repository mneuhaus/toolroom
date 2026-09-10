# Adaptation record — 2026-09-09

Source: the user-supplied `cad-design-system.skill` inside `files.zip`, plus its style-tile and flawed-part examples. The Sparky project retains unmodified originals and SHA-256 hashes under `reference/cad-design-system-2026-09-09/`.

Maintained changes:

- Narrowed activation to design-system work and made user constraints, real mechanisms and prior authorization take precedence over generic profiles.
- Separated physical material colours, instruction highlights and rendering style.
- Marked uncalibrated source examples as references; removed mandatory grid snapping, universal insert selection, blanket support bans and claims of guaranteed printability.
- Made mesh analysis errors and zero-valid-ray results fail as incomplete; added winding, positive-volume and component checks, exact orientation fit and optional bed contact.
- Made STEP inlays explicit; retained other findings and measured build height along the chosen up axis. Empty STEP files cannot pass. Mesh errors propagate to the STEP result.
- Kept the generic tile as an enclosure demonstration, with an explicit warning that its insert holes and knob do not test project-specific fasteners or hardware.

Tests and the applied Sparky R14 report are maintained in `scripts/design-system/` and `output/r14/design-system/` in that project. All nine current STL files are screened in their released print orientation. Numerical thresholds remain hypotheses until suitable physical calibration has been recorded.
