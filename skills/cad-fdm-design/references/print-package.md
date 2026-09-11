# Native Bambu print packages

Use [print_package.py](../scripts/print_package.py) for repeatable inspection or native slice/reimport jobs. It accepts an already authoritative, posed 3MF, including multiple plates. It does not export native CAD, choose bed faces, place parts, merge plates or dispatch a printer. Those decisions remain in the [FDM workflow](../SKILL.md).

## Inspect an existing package

```sh
uv run python skills/cad-fdm-design/scripts/print_package.py inspect \
  /path/to/candidate.3mf --out /path/to/project/checks
```

The report checks archive integrity, standard 3MF component/build transforms, finite mesh data, plate assignments, every plate's G-code member, outside/skipped flags and native metadata counts. Non-millimeter geometry or unsupported component structures remain incomplete. Meshes are not proven watertight or printable by this inspection.

## Build from a frozen input

Create a job JSON in the project:

```json
{
  "source": "posed-plates.3mf",
  "slicer": "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
  "profiles": {
    "machine": "profiles/machine.json",
    "process": "profiles/process.json",
    "filaments": ["profiles/filament.json"]
  },
  "timeout_seconds": 900,
  "resource_paths": []
}
```

```sh
uv run python skills/cad-fdm-design/scripts/print_package.py build \
  /path/to/project/job.json --out /path/to/project/packages
```

Paths are relative to the job JSON. Supply resolved native profiles with their correct identities and all five machine routines. The [profile resolver](../scripts/resolve_profiles.py) provides dependency-resolution data; its report is not itself a native slicer preset. Review the actual machine/material values before invoking the build. Unresolved includes are rejected. A slicer-compatible `inherits` identity anchor may remain, so include external preset resources in `resource_paths`. On macOS the slicer's application `Contents/Resources` directory is included automatically.

The first command runs Bambu with explicit machine/process/filament profiles, arrangement and orientation disabled, and all plates selected. The second reimports and reslices with **no profile overrides**. Commands use argument arrays. Slicer side effects and logs remain in the job's output directory. A timeout or missing output ends the job and preserves the evidence.

Checks compare the source geometry to the native export and native geometry to reimport. The current signature includes transformed vertex coordinates and triangle indexing. It is conservative: vertex reindexing or harmless floating-point/coordinate normalization can require review even when geometry is equivalent. Do not loosen a dimensional criterion merely to turn the report green. Examine the changed geometry or run an independently defined comparison.

Profile names, task values and native machine routines are compared with the output; reimport settings are compared with the native result. Differences caused by slicer normalization or unsupported preset fields are retained for review, not silently ignored. Existing vendor profiles can therefore yield `review` even when a slicer generated paths successfully.

## Cache and evidence

Packages live under an input-hash directory. The key covers the job, source, profiles, helper, slicer executable and declared/bundled resources. Inputs are checked again after the run. Reusing a package verifies all recorded artifact hashes; changed inputs produce a new directory. An interrupted or failed package is preserved; rerunning identical inputs reports that result rather than repeating an unchanged failure. After resolving an external failure, use a fresh output root for an explicit retry.

Stdout contains only status, report path and artifact paths. Full reports and logs remain on disk. Each subprocess log records elapsed time; compare the same inputs before considering a parser or numeric hot path for Rust. This command is a bounded preparation helper, not an arbitrary workflow runner or model host.

## Meaning of the result

Exit codes are 0 `no_findings`, 1 `review`, 2 `incomplete`, as in [verification](../../../knowledge/foundations/verification.md#result-states). `no_findings` applies only to the listed automated checks. Actual deposited-layer/support review and critical engineering release are always listed separately as pending. A G-code member's presence does not establish useful supports, bed adhesion, bridge coverage, material strength or physical fit.

Regression coverage includes two plates, composed transforms, missing second-plate G-code, unsupported units, profile mismatches, geometry drift, subprocess failure and cache invalidation/tampering. Fake-process tests verify orchestration without a machine; a read-only inspection of a real native package exercises the format parser. Neither is a new physical print test.
