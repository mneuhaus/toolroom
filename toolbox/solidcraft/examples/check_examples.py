"""Checks the results of run-examples.sh against the values the house reference states. Run by that script."""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

work, failures = Path(sys.argv[1]), []


def results(name):
    return [r for r in json.loads((work / f"{name}.results.json").read_text()) if isinstance(r, dict)]


def volumes(name):
    return [{b["name"]: b["volume_mm3"] for b in r["bodies"]} for r in results(name)
            if isinstance(r.get("bodies"), list) and r["bodies"] and isinstance(r["bodies"][0], dict)]


def check(label, ok, detail):
    print(("ok    " if ok else "FAIL  ") + f"{label}: {detail}")
    if not ok:
        failures.append(label)


def close(a, b, tol):
    return abs(a - b) <= tol


for stl in sorted(work.glob("*.stl")):
    mesh = trimesh.load(stl)
    check(f"{stl.name} closed", mesh.is_watertight, f"{len(mesh.faces)} triangles")

laid = trimesh.load(work / "bracket-laid.stl")
check("print face laid on the bed", close(laid.bounds[0][2], 0, 1e-6) and close(laid.bounds[1][2], 20, 1e-4)
      and np.allclose(laid.center_mass[:2], 0, atol=1e-3), f"z {laid.bounds[0][2]:.4f}..{laid.bounds[1][2]:.4f}, "
      f"centre of mass {laid.center_mass[0]:.4f}, {laid.center_mass[1]:.4f}")

plate = volumes("screw-holes")
check("bridged M3 counterbore", close(plate[0]["Plate"] - plate[1]["Plate"], 178.09, 0.05),
      f"removed {plate[0]['Plate'] - plate[1]['Plate']:.3f} mm3 (3.4 hole, 6.5 x 3.5 counterbore, two bridge layers)")

tray = volumes("tray-boss-lip")
check("boss and lip add material", tray[0]["Tray"] < tray[1]["Tray"] < tray[2]["Tray"],
      " < ".join(f"{t['Tray']:.1f}" for t in tray))

thread = volumes("trapezoid-threads")[-1]
check("Tr11x3 screw and Tr12x3 nut are cut", thread["Screw"] < 1900.66 - 300 and thread["Nut"] < 6148.59 - 200,
      f"screw {thread['Screw']:.1f} of 1900.7, nut {thread['Nut']:.1f} of 6148.6 mm3")

seat = [r for r in results("fastener") if "pairs_checked" in r][-1]
check("M3 screw seated without overlap", not seat["overlaps"] and seat["near"] and seat["near"][0]["distance_mm"] < 1e-6,
      f"{len(seat['overlaps'])} overlaps, head to seat {seat['near'][0]['distance_mm']:.4f} mm" if seat["near"]
      else "no near pair reported")

dxf = volumes("scan-dxf")[-1]["FromDxf"]
check("DXF outline keeps its size", close(dxf, 4677.46, 0.05), f"{dxf:.2f} mm3 (4677.46 expected)")

canvas = volumes("scan-canvas")[-1]["FromCanvas"]
check("canvas trace within 1 %", close(canvas, 4677.26, 46.8), f"{canvas:.1f} mm3 ({(canvas / 4677.26 - 1) * 100:+.2f} %)")

deviation = next(r for r in results("pointcloud-deviation") if "mean_signed_mm" in r)
check("point cloud deviation", close(deviation["mean_signed_mm"], 0.05, 1e-4) and deviation["failed"] == 0,
      f"mean {deviation['mean_signed_mm']:+.5f} mm over {deviation['measured']} points")

hole = volumes("m3-hybrid-hole-demo")
removed = [hole[i]["Block"] - hole[i + 1]["Block"] for i in range(3)]
check("M3 hybrid hole, three directions", max(removed) - min(removed) < 1e-3, ", ".join(f"{r:.4f}" for r in removed) + " mm3")

grown = trimesh.load(work / "bracket-laid-h50.stl")
check("print face follows a parameter change", close(grown.bounds[0][2], 0, 1e-6) and close(grown.bounds[1][2], 20, 1e-4)
      and close(float(grown.volume), 6880, 0.01), f"z {grown.bounds[0][2]:.4f}..{grown.bounds[1][2]:.4f}, {grown.volume:.1f} mm3")

both = trimesh.load(work / "both-laid.3mf").geometry
check("laid export of two bodies moves only the marked one", np.allclose(both["Bracket"].center_mass[:2], 0, atol=1e-3)
      and np.allclose(both["Cube"].bounds, [[60, 0, 0], [70, 10, 10]], atol=1e-4),
      f"Bracket centre {both['Bracket'].center_mass[0]:.3f}, {both['Bracket'].center_mass[1]:.3f}; "
      f"Cube from x {both['Cube'].bounds[0][0]:.1f}")

check("installed slicers are listed", any("slicers" in r for r in results("print-handoff")),
      "file.slicers answered")

deep = volumes("recess-too-deep")[-1]["Floor"]
check("a recess deeper than the wall becomes a through hole without a warning", close(deep, 800 - np.pi * 3.25 ** 2 * 2, 0.01),
      f"{deep:.2f} mm3 left of 800: a plain 6.5 mm hole, no seat")
refused = (work / "refused-bridged-recess.log").read_text()
check("the same recess with bridge layers is refused", "bridge layers" in refused, refused.strip().splitlines()[0][:110])

pairs = [r["pairs_checked"] for r in results("fastener") if "pairs_checked" in r]
check("clearance needs both sides named", pairs == [0, 1], f"pairs checked without and with `against`: {pairs}")

converted = {b["name"]: b for r in results("mesh-convert") if isinstance(r.get("bodies"), list) and r["bodies"]
             and isinstance(r["bodies"][0], dict) for b in r["bodies"]}
flat, bore, cone = converted["convert-flat"], converted["convert-bore"], converted["convert-cone"]
check("mesh.convert: flat-faced mesh becomes its planar solid", flat["faces"] == 6 and close(flat["volume_mm3"], 6000, 1e-6),
      f"{flat['faces']} faces, {flat['volume_mm3']:.1f} mm3")
check("mesh.convert: a straight bore comes back as a cylinder", bore["faces"] == 7 and bore["face_types"].get("cylinder") == 1,
      f"{bore['faces']} faces {bore['face_types']}, {bore['volume_mm3']:.1f} mm3")
check("mesh.convert: a countersunk part stays faceted", cone["faces"] > 30 and set(cone["face_types"]) == {"plane"},
      f"{cone['faces']} faces {cone['face_types']}")

scan = results("scan-canvas")
width = next(r["width"] for r in scan if "width" in r)
traced = next(r for r in scan if "outlines" in r)
box = next(b["bbox"] for r in scan if isinstance(r.get("bodies"), list) and r["bodies"] and isinstance(r["bodies"][0], dict)
           for b in r["bodies"] if b["name"] == "FromCanvas")
size = [box["max"][i] - box["min"][i] for i in (0, 1)]
check("canvas calibration", close(width, 70, 0.01), f"image {width:.4f} mm wide for 70")
check("canvas trace: about a pixel large, unconstrained, bar traced too", all(0 < size[i] - (40, 30)[i] < 0.1 for i in (0, 1))
      and traced["info"]["dof"] > 0 and traced["outlines"] == 2,
      f"{size[0]:.3f} x {size[1]:.3f} mm for 40 x 30, {traced['info']['dof']} free degrees, {traced['outlines']} outlines")

sys.exit(1 if failures else 0)
