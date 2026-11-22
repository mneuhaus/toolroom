"""Execute the frozen R10b regression and verify the exported STEP geometry."""

import hashlib
import json
import math
import time
from pathlib import Path

from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader

from fsocct.api import run
from fsocct.kernel import bounds, members, valid, volume

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]
EXPECTED = {
    "R59B",
    "R62B",
    "P03B",
    "side_rack_24T",
    "side_pinion_24T",
    "T40BL",
    "T40BR",
    "T41BL",
    "T41BR",
    "L04",
    "T60",
    "T61",
    "T51",
    "A01",
    "A02",
    "A03",
    "D01",
    "D02",
    "D03L",
    "D03R",
    "D04L",
    "D04R",
    "D05",
    "L01B",
    "L02B",
    "L03B",
    "T01",
    "C11L",
    "C11R",
    "C11LU",
    "C11RU",
    "C11S",
    "K15",
    "T05",
    "T06",
    "R10",
    "R39",
    "R77",
}


def main():
    source = json.loads((CASE / "source.json").read_text())
    assert hashlib.sha256((CASE / "r10b.fs").read_bytes()).hexdigest() == source["sha256"]
    imports = {k: CASE / v for k, v in json.loads((CASE / "imports.json").read_text()).items()}
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    started = time.perf_counter()
    with (output / "r10b.trace.log").open("w") as trace:
        build = run(
            CASE / "r10b.fs",
            feature=source["entrypoint"],
            imports=imports,
            parameters=json.loads((CASE / "parameters.json").read_text()),
            max_steps=5_000_000,
            progress=lambda event: print(
                f"{time.perf_counter() - started:.3f}",
                event["operation"],
                "/".join(event["id"]),
                file=trace,
                flush=True,
            ),
        )
    report = build.report()
    assert not report["failed_operations"], report["failed_operations"]
    assert report["body_count"] == len(EXPECTED) == 38
    assert {b["name"].split()[0] for b in report["bodies"]} == EXPECTED
    assert all(b["valid"] and b["volume_mm3"] > 0 for b in report["bodies"])
    step = output / "r10b.step"
    build.step(step)
    reader = STEPControl_Reader()
    assert reader.ReadFile(str(step)) == IFSelect_RetDone
    assert reader.TransferRoots() > 0
    shape = reader.OneShape()
    solids = members(shape, "SOLID")
    assert len(solids) == 38 and all(valid(s) for s in solids)
    exported = sorted(volume(s) for s in solids)
    original = sorted(b["volume_mm3"] for b in report["bodies"])
    assert all(math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-3) for a, b in zip(original, exported))
    original_bounds, exported_bounds = bounds(build.context.shape()), bounds(shape)
    assert all(
        abs(a - b) < 1e-4
        for row_a, row_b in zip(original_bounds, exported_bounds)
        for a, b in zip(row_a, row_b)
    )
    verification = {
        "status": "passed",
        "body_count": len(solids),
        "all_solids_valid_before_and_after_export": True,
        "expected_part_names_matched": True,
        "caught_operation_failures": len(report["failed_operations"]),
        "step_sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
        "step_volume_mm3": sum(exported),
        "step_volume_difference_mm3": sum(exported) - report["volume_mm3"],
        "per_solid_volume_relative_tolerance": 1e-7,
        "per_solid_volume_absolute_tolerance_mm3": 1e-3,
        "bounds_tolerance_mm": 1e-4,
        "implementation_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src/fsocct").glob("*.py"))
        },
    }
    (output / "r10b.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "r10b-verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(f"38 valid solids; {len(report['operations'])} operations; {build.elapsed_seconds:.3f}s")
    print(
        f"STEP round trip passed; volume change {verification['step_volume_difference_mm3']:.6f} mm³"
    )
    print(f"Artifacts: {output}")


if __name__ == "__main__":
    main()
