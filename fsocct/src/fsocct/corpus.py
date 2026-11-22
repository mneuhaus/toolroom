"""Run frozen compatibility cases in separate, time-limited evaluator processes."""

import hashlib
import json
import math
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .syntax import FSError


def run_corpus(manifest, output, timeout=120, selected=()):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    data = json.loads(manifest.read_text())
    if not math.isfinite(timeout) or timeout <= 0:
        raise FSError("Corpus timeout must be finite and positive")
    sources = {source["file"] for source in data["sources"]}
    for source in data["sources"]:
        path = manifest.parent / source["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise FSError(f"Frozen source hash mismatch: {path}")
    cases = [c for c in data["cases"] if not selected or c["id"] in selected]
    unknown = set(selected) - {c["id"] for c in data["cases"]}
    if unknown:
        raise FSError("Unknown corpus cases: " + ", ".join(sorted(unknown)))
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise FSError("Corpus selection must have unique, nonempty cases")
    for case in cases:
        if not re.fullmatch(r"[A-Za-z0-9_.=-]+", case["id"]):
            raise FSError(f"Invalid case ID: {case['id']}")
        if case["source"] not in sources:
            raise FSError(f"Case source is not frozen: {case['source']}")
        limit = case.get("timeout", timeout)
        if not math.isfinite(limit) or limit <= 0:
            raise FSError(f"Invalid timeout for case {case['id']}")
    protected = {manifest, *((manifest.parent / name).resolve() for name in sources)}
    destinations = {output / "summary.json"}
    for case in cases:
        destinations.update(output / (case["id"] + ext) for ext in (".json", ".log"))
    if protected.intersection(p.resolve() for p in destinations):
        raise FSError("Corpus output must not overwrite frozen inputs")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    evidence = {
        "schema_version": 1,
        "started_utc": datetime.now(UTC).isoformat(),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "implementation_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        },
        "selected_count": len(cases),
    }
    for case in cases:
        key = case["id"]
        report_path, log_path = output / (key + ".json"), output / (key + ".log")
        report_path.unlink(missing_ok=True)
        command = [
            sys.executable,
            "-m",
            "fsocct",
            "run",
            str(manifest.parent / case["source"]),
            "--feature",
            case["feature"],
            "--max-steps",
            str(case.get("max_steps", 5_000_000)),
            "--report",
            str(report_path),
            "--verbose",
        ]
        if "imports" in case:
            command.extend(["--imports", str(manifest.parent / case["imports"])])
        if "fonts" in case:
            command.extend(["--fonts", str(manifest.parent / case["fonts"])])
        for name, value in case.get("parameters", {}).items():
            command.extend(["--param", name + "=" + value])
        started = time.perf_counter()
        result = {"id": key, "feature": case["feature"], "source": case["source"]}
        with log_path.open("w") as log:
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=case.get("timeout", timeout),
                )
                result["status"] = "passed" if completed.returncode == 0 else "failed"
                result["exit_code"] = completed.returncode
            except subprocess.TimeoutExpired:
                result.update(
                    status="timeout", error=f"Exceeded {case.get('timeout', timeout)}s timeout"
                )
        result["elapsed_seconds"] = time.perf_counter() - started
        if result["status"] == "passed":
            try:
                report = json.loads(report_path.read_text())
                result.update(
                    body_count=report["body_count"],
                    volume_mm3=report["volume_mm3"],
                    operation_count=len(report["operations"]),
                    recovered_operations=report.get("failed_operations", []),
                    report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                )
                if not report["bodies"] or not all(
                    b["valid"] and b["volume_mm3"] > 0 for b in report["bodies"]
                ):
                    result.update(status="failed", error="No solids or invalid final geometry")
                elif result["recovered_operations"]:
                    result.update(
                        status="recovered", error="FeatureScript caught failed geometry operations"
                    )
            except (OSError, ValueError, KeyError, TypeError) as error:
                result.update(status="failed", error=f"Missing or invalid report: {error}")
        elif "error" not in result:
            lines = log_path.read_text().splitlines()
            result["error"] = next(
                (line for line in reversed(lines) if line.startswith("fsocct:")),
                lines[-1] if lines else result["status"],
            )
        results.append(result)
        print(
            f"{key}: {result['status']} ({result['elapsed_seconds']:.2f}s)"
            + (
                " — " + result["error"]
                if "error" in result
                else f" — {result['body_count']} solid(s)"
            ),
            flush=True,
        )
        summary = {
            **evidence,
            "cases": results,
            "passed": sum(r["status"] == "passed" for r in results),
            "recovered": sum(r["status"] == "recovered" for r in results),
            "total": len(results),
            "complete": len(results) == len(cases),
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
