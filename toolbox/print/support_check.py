"""Support actually generated on a sliced plate: reads the G-code of a Bambu .gcode.3mf (slice-a1.sh GCODE=1) and the
plate's plate-3mf.mjs spec, assigns every support extrusion (FEATURE Support / Support interface / Support transition)
to the nearest part outline on the bed and reports per part the support filament (mm3) and how far the support
reaches beyond the part's own footprint (the gap that part needs to its neighbours). "Enabled" is not "generated":
this counts deposited paths only (relative E, retraction restores excluded).
Usage: support_check.py plate.json plate.gcode.3mf"""
import json
import math
import re
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

RES = 0.25  # mm Raster cell
BED = 256
FILAMENT_AREA = math.pi * 0.875 ** 2  # mm2 1.75 mm filament
MOVE = re.compile(r"^G[123] (?=.*X(-?[\d.]+))?(?=.*Y(-?[\d.]+))?(?=.*E(-?[\d.]+))?")


def read_stl(path):
    data = np.fromfile(path, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), offset=84)
    return data["v"].astype(float)


def placed_labels(spec):
    """Raster of the bed: 0 free, k + 1 inside the footprint of part k (as plate-3mf.mjs places it)."""
    n = int(BED / RES)
    img = Image.new("I", (n, n), 0)
    draw = ImageDraw.Draw(img)
    for k, part in enumerate(spec["parts"]):
        tri = read_stl(part["stl"])[:, :, :2]
        lo, hi = tri.reshape(-1, 2).min(axis=0), tri.reshape(-1, 2).max(axis=0)
        tri = tri + (np.array(part["at"]) - (lo + hi) / 2)
        for t in tri / RES:
            draw.polygon([tuple(p) for p in t], fill=k + 1, outline=k + 1)
    return np.array(img)


def support_points(gcode):
    """(x, y, deposited mm3) of every support extrusion move."""
    feature, x, y, debt, out = "", 0.0, 0.0, 0.0, []
    for line in gcode.splitlines():
        if line.startswith("; FEATURE:"):
            feature = line[10:].strip()
            continue
        m = MOVE.match(line)
        if not m:
            continue
        nx = float(m.group(1)) if m.group(1) else x
        ny = float(m.group(2)) if m.group(2) else y
        e = float(m.group(3)) if m.group(3) else 0.0
        if e < 0:
            debt -= e
        elif e > 0:
            used = min(e, debt)
            debt -= used
            e -= used
            if e > 0 and feature.startswith("Support"):
                for s in np.linspace(0, 1, max(2, int(math.hypot(nx - x, ny - y) / RES) + 1)):
                    out.append((x + s * (nx - x), y + s * (ny - y), e * FILAMENT_AREA / max(2, int(math.hypot(nx - x, ny - y) / RES) + 1)))
        x, y = nx, ny
    return np.array(out).reshape(-1, 3)


def main(plate_json, gcode_3mf):
    spec = json.load(open(plate_json))
    with zipfile.ZipFile(gcode_3mf) as z:
        gcode = z.read("Metadata/plate_1.gcode").decode()
    labels = placed_labels(spec)
    dist, (iy, ix) = distance_transform_edt(labels == 0, return_indices=True)
    pts = support_points(gcode)
    report = {p["name"]: {"support_mm3": 0.0, "reach_mm": 0.0} for p in spec["parts"]}
    if len(pts):
        cols = np.clip((pts[:, 0] / RES).astype(int), 0, labels.shape[1] - 1)
        rows = np.clip((pts[:, 1] / RES).astype(int), 0, labels.shape[0] - 1)
        owner = labels[iy[rows, cols], ix[rows, cols]] - 1
        reach = dist[rows, cols] * RES
        for k, part in enumerate(spec["parts"]):
            mine = owner == k
            if mine.any():
                report[part["name"]] = {"support_mm3": round(float(pts[mine, 2].sum()), 0),
                                        "reach_mm": round(float(reach[mine].max()), 1)}
    for name, r in report.items():
        print(f"{name:18s} support {r['support_mm3']:7.0f} mm3  reach beyond footprint {r['reach_mm']:5.1f} mm")
    print(f"total support {sum(r['support_mm3'] for r in report.values()):.0f} mm3")
    json.dump(report, open(gcode_3mf.replace(".gcode.3mf", ".support.json"), "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
