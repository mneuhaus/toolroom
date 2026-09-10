"""Generate small independent meshes and record actual shared-checker results."""
import hashlib
import json
from pathlib import Path
import sys

import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/cad-design-system/scripts"))
import check_mesh

OUT = Path(__file__).resolve().parent / "results"
PROFILE = {"id": "checker-lab", "build_volume": [30, 30, 30],
           "walls": {"hard_min": .84, "min_thickness": 1.26},
           "expected_components": 1, "require_bed_contact": True}


def box(dimensions, shift=(0, 0, 0)):
    mesh = trimesh.creation.box(extents=dimensions)
    mesh.apply_translation([shift[0], shift[1], shift[2] + dimensions[2] / 2])
    return mesh


def main():
    OUT.mkdir(exist_ok=True)
    cases = [
        ("solid", "Closed solid block", box((12, 12, 3)), PROFILE, "no_findings"),
        ("thin", "Thin plate", box((12, 12, .4)), PROFILE, "review"),
        ("orientation", "Incorrect print orientation", box((16, 9, 3)),
         {**PROFILE, "build_volume": [10, 20, 10]}, "review"),
        ("island", "Floating island", trimesh.util.concatenate([
            box((12, 12, 2)), box((1, 10, 1), (18, 0, 6))]), PROFILE, "review"),
    ]
    summary = []
    for ident, title, mesh, profile, expected in cases:
        path = OUT / f"{ident}.stl"
        mesh.export(path)
        report = check_mesh.analyse(str(path), profile, samples=1024)
        report["file"] = f"labs/checker-lab/results/{ident}.stl"
        report["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report["checker_sha256"] = hashlib.sha256(Path(check_mesh.__file__).read_bytes()).hexdigest()
        report["manufacturing_profile"] = profile
        report["title"] = title
        (OUT / f"{ident}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        assert report["status"] == expected, f"Unexpected {ident}: {report['status']}; {report['analysis_errors']}"
        if ident == "island":
            assert any("floating underside" in r["verdict"] for r in report["overhangs"]["regions"])
        summary.append({"id": ident, "title": title, "status": report["status"],
                        "report": f"labs/checker-lab/results/{ident}.json",
                        "mesh": report["file"], "problems": report["problems"],
                        "input_sha256": report["input_sha256"]})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"cases": len(summary), "status": "expected outcomes confirmed"}))


if __name__ == "__main__":
    main()
