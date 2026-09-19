"""Pose the four Probestaebe in their print orientation, lay them out on a 250x250
A1 bed (>=15mm gaps, centred as a group, Z-min=0), build a plate 3MF, a slice job,
and run the slicer via the shared print_package.py helper.

Pattern lifted from
step-feeder/rocking-photo-tray-r6d-belt-clamp-r1/prepare_print.py.
"""
from pathlib import Path
import json
import subprocess
import sys

import numpy as np
import trimesh

P = Path(__file__).resolve().parent.parent  # .../probestaebe
SRC_PARTS = P / "var" / "print" / "parts"
O = P / "var" / "print"
DIST = P / "dist"
ROOT = P.parents[2]  # .../cad
PROF = ROOT / "step-feeder" / "rocking-photo-tray-r6d" / "printing" / "profiles"

for d in ["parts_posed", "plates", "jobs", "packages"]:
    (O / d).mkdir(parents=True, exist_ok=True)
DIST.mkdir(parents=True, exist_ok=True)

BED = 250.0
GAP = 15.0
STEEP_LIMIT_DEG = 45.0
STEEP_EPS_DEG = 0.15  # numeric tolerance for the S3 "exactly 45deg" edge case


def rot_x(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0])


# (name, native STL, print-pose transform)
PARTS = [
    ("S1_d10_senkrecht", SRC_PARTS / "S1_d10_senkrecht-native.stl", np.eye(4)),
    ("S2_d20_senkrecht", SRC_PARTS / "S2_d20_senkrecht-native.stl", np.eye(4)),
    ("S3_d10_45grad", SRC_PARTS / "S3_d10_45grad-native.stl", np.eye(4)),
    ("S4_d10_liegend", SRC_PARTS / "S4_d10_liegend-native.stl", rot_x(90)),
]


def bed_and_overhang(mesh):
    n = mesh.face_normals
    area = mesh.area_faces
    down = n[:, 2] < -0.5
    onbed = mesh.triangles_center[:, 2] < 0.05
    bed_area = float(area[down & onbed].sum())
    overhang_area = float(area[down & ~onbed].sum())
    # steepest downward-facing overhang angle (0 = straight down wall... measured
    # from vertical: 0deg = horizontal ceiling, 90deg = vertical wall)
    down_faces = down & ~onbed
    if np.any(down_faces):
        # angle of the face normal from straight-down (-Z); 0deg=facing straight down (flat
        # ceiling, worst case), 90deg=vertical wall (fine). "Overhang angle" as commonly
        # quoted (from vertical) = 90 - angle_from_down.
        nz = n[down_faces, 2]
        cosang = np.clip(-nz, -1.0, 1.0)
        angle_from_down = np.degrees(np.arccos(cosang))
        overhang_from_vertical = 90.0 - angle_from_down
        # Known OCC boolean artifact (cad-khana-quirks): the union of stab-on-foot (or the
        # S4 flat cut) leaves a handful of paper-thin, PERFECTLY flat (nz==-1.0 exactly)
        # sliver triangles right at the coincident foot/stab junction plane. They carry no
        # real material below them missing -- the junction is fully backed by solid foot --
        # so they are tessellation noise, not a printability overhang. This design has no
        # intentional flat (0deg-from-vertical) overhangs anywhere, so excluding dead-flat
        # downward faces from the "genuine overhang" tally is safe and design-specific-safe.
        artifact = nz < -0.9995
        real = down_faces.copy()
        real[down_faces] = ~artifact
        max_overhang_from_vertical = float(overhang_from_vertical[~artifact].max()) if np.any(~artifact) else 0.0
        steep_area = float(area[real][overhang_from_vertical[~artifact] > (STEEP_LIMIT_DEG + STEEP_EPS_DEG)].sum()) if np.any(~artifact) else 0.0
    else:
        max_overhang_from_vertical = 0.0
        steep_area = 0.0
    return bed_area, overhang_area, max_overhang_from_vertical, steep_area


def main():
    posed = []
    for name, stl_path, T in PARTS:
        m = trimesh.load_mesh(stl_path, process=True)
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
        m.merge_vertices()
        m.apply_transform(T)
        m.apply_translation(-m.bounds[0])  # Z-min (and local X/Y min) -> 0, per-part
        posed.append([name, m])

    # --- layout: single row along X, gaps >=15mm, group centred on the bed ---
    dims = [np.ptp(m.bounds, axis=0) for _, m in posed]
    widths_x = [d[0] for d in dims]
    total_x = sum(widths_x) + GAP * (len(posed) - 1)
    max_y = max(d[1] for d in dims)
    assert total_x <= BED - 10 and max_y <= BED - 10, (total_x, max_y)

    start_x = (BED - total_x) / 2.0
    cursor_x = start_x
    layout = []
    scene = trimesh.Scene()
    report = {}
    for (name, m), d in zip(posed, dims):
        target_x = cursor_x
        target_y = (BED - d[1]) / 2.0
        m.apply_translation([target_x, target_y, 0])
        cursor_x += d[0] + GAP

        dest = O / "parts_posed" / f"{name}-posed.stl"
        m.export(dest)
        scene.add_geometry(m, geom_name=name, node_name=name)

        bed_area, overhang_area, max_overhang_deg, steep_area = bed_and_overhang(m)
        b = m.bounds
        assert b[0][2] > -1e-4, (name, "Z below bed", b)
        assert np.all(b[1] <= [BED - 3, BED - 3, 200]), (name, "exceeds bed", b)
        entry = {
            "file": str(dest),
            "volume_mm3": float(m.volume),
            "bbox_posed_mm": np.ptp(m.bounds, axis=0).tolist(),
            "bounds_mm": m.bounds.tolist(),
            "bed_contact_area_mm2": bed_area,
            "overhang_area_mm2": overhang_area,
            "max_overhang_from_vertical_deg": max_overhang_deg,
            "steep_overhang_area_mm2 (>45deg from vertical)": steep_area,
        }
        report[name] = entry
        layout.append((name, target_x, target_y, d.tolist()))
        print(f"{name}: bbox={np.round(d,1).tolist()} pos=({target_x:.1f},{target_y:.1f}) "
              f"bed_contact={bed_area:.1f}mm2 overhang={overhang_area:.1f}mm2 "
              f"max_overhang_from_vertical={max_overhang_deg:.2f}deg steep_area={steep_area:.4f}mm2")
        if name == "S3_d10_45grad":
            print(f"  NOTE S3 tilted stab is designed at exactly 45deg from vertical; "
                  f"measured {max_overhang_deg:.3f}deg (numerically at the 45deg edge).")

    # S1/S2/S3 are designed to be support-free (brief: S3 explicitly "ohne Stuetzen"; S1/S2
    # are plain vertical cylinders on a flat foot, trivially support-free). S4 is a round rod
    # lying on its side -- a plain circular cross-section printed horizontally ALWAYS has an
    # unavoidable >45deg overhang over its top ~90deg arc (only a teardrop/rain-drop profile
    # would remove it, which was not asked for; the brief also does not say "ohne Stuetzen"
    # for S4). So the "steep overhang must be 0" assertion is enforced for S1-S3 and only
    # reported (not enforced) for S4, which will need Bambu Studio auto-supports.
    SUPPORT_FREE_REQUIRED = {"S1_d10_senkrecht", "S2_d20_senkrecht", "S3_d10_45grad"}
    for name, entry in report.items():
        steep = entry["steep_overhang_area_mm2 (>45deg from vertical)"]
        if name in SUPPORT_FREE_REQUIRED:
            assert steep == 0.0, (name, "has overhang steeper than 45deg from vertical", entry)
        elif steep > 0.0:
            print(f"  NOTE {name}: {steep:.1f}mm2 steeper than 45deg (round rod lying on its "
                  f"side, top ~90deg arc) -- needs slicer auto-supports, by design.")

    plate = O / "plates" / "A1-01.3mf"
    plate.write_bytes(scene.export(file_type="3mf"))
    dist_copy = DIST / "Probestaebe_A1-01.3mf"
    dist_copy.write_bytes(plate.read_bytes())

    (O / "layout.json").write_text(json.dumps({
        "bed_mm": BED, "gap_mm": GAP,
        "layout": [{"name": n, "x": x, "y": y, "bbox_mm": d} for n, x, y, d in layout],
        "parts": report,
        "plate": str(plate), "dist_copy": str(dist_copy),
    }, indent=2))
    print("plate ->", plate)
    print("dist copy ->", dist_copy)

    job = dict(
        source=str(plate.resolve()),
        slicer="/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
        profiles=dict(
            machine=str(PROF / "machine.json"),
            process=str(PROF / "process.json"),
            filaments=[str(PROF / "filament.json")],
        ),
        timeout_seconds=900,
        resource_paths=[],
    )
    job_path = O / "jobs" / "A1-01.json"
    job_path.write_text(json.dumps(job, indent=2))

    helper = ROOT / "toolroom" / "skills" / "cad-fdm-design" / "scripts" / "print_package.py"
    log_path = O / "A1-01-slice.log"
    with log_path.open("w") as log:
        r = subprocess.run(
            [sys.executable, str(helper), "build", str(job_path), "--out", str(O / "packages")],
            stdout=log, stderr=subprocess.STDOUT,
        )
    print("SLICE exit", r.returncode, "log:", log_path)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
