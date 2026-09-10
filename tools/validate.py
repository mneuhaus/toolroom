#!/usr/bin/env python3
"""Validate repository links, catalogue contracts, assets and generated output."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import yaml

from build_site import ROOT, build_data, digest, generated_files


def main():
    checks, errors = [], []

    def check(name, condition, detail=""):
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            errors.append(name + (": " + detail if detail else ""))

    data, links = build_data()  # Also checks every local Markdown link and heading.
    check("markdown links and headings", all(l["exists"] for l in links), str(len(links)))
    ids = [m["id"] for m in data["modules"]]
    check("unique module identifiers", len(ids) == len(set(ids)))
    for module in data["modules"]:
        path = module["document"]
        raw = data["sources"][path]["text"]
        front = re.match(r"\A---\n(.*?)\n---\n", raw, re.S)
        metadata = yaml.safe_load(front[1]) if front else {}
        check(f"skill metadata: {module['id']}",
              metadata.get("name") == module["id"] and metadata.get("description") == module["description"])
        check(f"skill entrypoint length: {module['id']}", len(raw.splitlines()) < 180)
    sections = [s["id"] for s in data["knowledge"]["sections"]]
    check("unique knowledge sections", len(sections) == len(set(sections)))
    for article in data["knowledge"]["articles"]:
        check(f"knowledge article: {article['path']}",
              article["path"] in data["documents"] and article["section"] in sections,
              "missing document" if article["path"] not in data["documents"] else "")
    for lab in data["labs"]:
        check(f"lab references: {lab['id']}",
              lab["document"] in data["documents"] and (ROOT / lab["image"]).is_file()
              and all(skill in ids for skill in lab["skills"]))
    for asset in data["assets"]:
        check(f"recorded image bytes: {asset['file']}",
              (ROOT / asset["file"]).is_file() and digest(ROOT / asset["file"]) == asset["sha256"],
              "" if (ROOT / asset["file"]).is_file() else "file is missing")
    for manifest in (ROOT / "provenance/references").glob("*/manifest.json"):
        for asset in json.loads(manifest.read_text())["images"]:
            check(f"reference image bytes: {asset['file']}", digest(ROOT / asset["file"]) == asset["sha256"])
    joints = json.loads((ROOT / "labs/printed-joints/native-manifest.json").read_text())
    joint_report = json.loads((ROOT / "labs/printed-joints/verification.json").read_text())
    native = json.loads((ROOT / "labs/printed-joints/native-checks.json").read_text())
    check("joints native source current", digest(ROOT / joints["source_file"]) == joints["source_sha256"])
    check("joints frozen native checks", native["status"] == "passed" and native["versionId"] == joints["versionId"] and len(native["checks"]) == 16)
    check("joints verifier current", digest(ROOT / "labs/printed-joints/verify.py") == joint_report["script_sha256"])
    check("joints complete geometry checks", joint_report["status"] == "passed" and len(joint_report["cases"]) == 8)
    for artifact in joints["artifacts"]:
        check(f"joint native source consumed: {artifact['name']}", artifact["featureSourceSha256"] == joints["source_sha256"] and artifact["featureStatus"] == "OK")
        if "step" in artifact:
            case = next(c for c in joint_report["cases"] if c["id"] == artifact["name"].split("-")[0])
            check(f"joint STEP evidence: {artifact['name']}", digest(ROOT / artifact["step"]) == artifact["step_sha256"] == case["step_sha256"])
    checker_hash = digest(ROOT / "skills/cad-design-system/scripts/check_mesh.py")
    for case in data["lab"]:
        report = data["reports"][case["report"]]
        check(f"lab input bytes: {case['id']}", digest(ROOT / case["mesh"]) == case["input_sha256"])
        check(f"lab checker revision: {case['id']}", report.get("checker_sha256") == checker_hash)
        check(f"lab status: {case['id']}", report["status"] == case["status"])
    for path, source in data["sources"].items():
        if path.endswith(".py"):
            ast.parse(source["text"], filename=path)
        if path.endswith((".yaml", ".yml")):
            yaml.safe_load(source["text"])
    check("Python and YAML parse", True)
    for name, expected in generated_files(data).items():
        check(f"generated file current: {name}", (ROOT / name).read_text() == expected)
    tests = json.loads((ROOT / "validation/tests.json").read_text())
    for path, sha in tests["inputs_sha256"].items():
        present = (ROOT / path).is_file()
        check(f"test evidence current: {path}", present and digest(ROOT / path) == sha,
              "" if present else "recorded test input no longer exists")
    report = {"status": "failed" if errors else "passed", "checks_run": len(checks),
              "errors": errors, "checks": checks}
    (ROOT / "validation/content.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(checks)} content checks; {len(errors)} failures")
    for error in errors:
        print(error)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
