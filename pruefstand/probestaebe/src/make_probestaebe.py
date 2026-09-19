"""Vier Probestaebe zur Kalibrierung eines FDM-Stabilitaetsindex (PLA, Bambu A1, 0.4mm Duese).

Gemeinsamer Fuss 30x30x8 mit zwei M3-Durchgangsloechern (Oe3.4), Stab freie Laenge 60mm,
KEINE Verrundung am Uebergang Stab->Fuss (Kerbwirkung ist Messziel). Vier Varianten:
  S1 d10 senkrecht | S2 d20 senkrecht | S3 d10 45 Grad | S4 d10 liegend (Stab-Abflachung).

Jede Variante wird in EINEM durchgehenden `with BuildPart() as p:` Block gebaut (kein
Wiedereintritt eines bereits geschlossenen Builders -- build123d haelt den aktiven
Builder auf einem globalen Stack, ein zweites `with p:` nach dem ersten Exit fuehrt zu
leeren Sketches). Foot-Helfer und Dimple-Helfer sind deshalb "inline" Funktionen, die
voraussetzen, dass sie innerhalb eines offenen BuildPart-Kontexts aufgerufen werden.

Exportiert je Variante eine "native" STL (wie modelliert) nach var/print/parts/.
Die Druckpose-Transformation (nur S4 braucht eine 90 Grad Drehung um X) passiert
separat in prepare_print.py, analog zum Muster in
step-feeder/rocking-photo-tray-r6d-belt-clamp-r1/prepare_print.py.
"""
from pathlib import Path
import json

import numpy as np
from build123d import (
    Align, BuildPart, BuildSketch, Circle, Cylinder, Box, Sphere, Location,
    Locations, Mode, Plane, chamfer, export_stl, extrude,
)

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "var" / "print" / "parts"
OUT.mkdir(parents=True, exist_ok=True)

CHAMFER = 0.42
HOLE_R = 3.4 / 2
HOLE_X = 10.0
FOOT_Z = 8.0
STAB_LEN = 60.0

# Dimple (Kalotte) geometry: opening diameter 2mm, depth 0.6mm.
# Sphere radius r and outward offset c solved from spherical-cap formula
# a^2 = d*(2r - d) with a = half-opening = 1mm, d = depth = 0.6mm.
DIMPLE_OPEN_R = 1.0
DIMPLE_DEPTH = 0.6
DIMPLE_SPHERE_R = (DIMPLE_OPEN_R ** 2 + DIMPLE_DEPTH ** 2) / (2 * DIMPLE_DEPTH)
DIMPLE_OFFSET = DIMPLE_SPHERE_R - DIMPLE_DEPTH  # sphere centre this far OUTSIDE the face

DIMPLE_PATTERNS = {
    1: [(0.0, 0.0)],
    2: [(-1.8, 0.0), (1.8, 0.0)],
    3: [(-1.8, -1.0), (1.8, -1.0), (0.0, 2.0)],
    4: [(-1.8, -1.8), (1.8, -1.8), (-1.8, 1.8), (1.8, 1.8)],
}


def dimple_points(count, face_center, normal, u_hat, v_hat):
    n = np.array(normal, dtype=float); n /= np.linalg.norm(n)
    u = np.array(u_hat, dtype=float); u /= np.linalg.norm(u)
    v = np.array(v_hat, dtype=float); v /= np.linalg.norm(v)
    fc = np.array(face_center, dtype=float)
    return [tuple(fc + du * u + dv * v + DIMPLE_OFFSET * n) for du, dv in DIMPLE_PATTERNS[count]]


def add_foot_box(size_x, size_y, size_z, center_y=0.0):
    """Add + chamfer the foot block. Must run first in a fresh BuildPart context so
    chamfer(p.edges()) only ever sees the 12 pristine box edges (never the later
    stab-foot junction edge, which must stay sharp on purpose)."""
    with Locations((0, center_y, 0)):
        Box(size_x, size_y, size_z, align=(Align.CENTER, Align.CENTER, Align.MIN))


def try_chamfer(p):
    try:
        chamfer(p.edges(), length=CHAMFER)
        return True
    except Exception as exc:  # pragma: no cover - reported in README if it happens
        print(f"  WARN chamfer failed: {exc}")
        return False


def build_s1():
    """S1: d10, vertical (+Z), foot 30x30x8, stab Z=8..68."""
    with BuildPart() as p:
        add_foot_box(30, 30, FOOT_Z)
        chamfered = try_chamfer(p)
        with Locations((HOLE_X, 0, 0), (-HOLE_X, 0, 0)):
            Cylinder(HOLE_R, FOOT_Z, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(FOOT_Z)):
            Circle(5.0)
        extrude(amount=STAB_LEN)
        with Locations(*dimple_points(1, (0, 0, FOOT_Z + STAB_LEN), (0, 0, 1), (1, 0, 0), (0, 1, 0))):
            Sphere(radius=DIMPLE_SPHERE_R, mode=Mode.SUBTRACT)
    return p.part, {"chamfer_ok": chamfered}


def build_s2():
    """S2: d20, vertical (+Z), foot 30x30x8, stab Z=8..68."""
    with BuildPart() as p:
        add_foot_box(30, 30, FOOT_Z)
        chamfered = try_chamfer(p)
        with Locations((HOLE_X, 0, 0), (-HOLE_X, 0, 0)):
            Cylinder(HOLE_R, FOOT_Z, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(FOOT_Z)):
            Circle(10.0)
        extrude(amount=STAB_LEN)
        with Locations(*dimple_points(2, (0, 0, FOOT_Z + STAB_LEN), (0, 0, 1), (1, 0, 0), (0, 1, 0))):
            Sphere(radius=DIMPLE_SPHERE_R, mode=Mode.SUBTRACT)
    return p.part, {"chamfer_ok": chamfered}


def build_s3():
    """S3: d10, 45 deg between +Z and +Y. Foot enlarged to 30(X) x 45(Y, -15..30) x 8(Z)
    so the tilted stab never overhangs past the foot edge (overhang stays exactly 45deg)."""
    center_y = 7.5  # (-15 + 30) / 2
    axis_dir = np.array([0.0, 1.0, 1.0]); axis_dir /= np.linalg.norm(axis_dir)
    start = np.array([0.0, 0.0, FOOT_Z])
    end = start + STAB_LEN * axis_dir
    u_hat = (1.0, 0.0, 0.0)  # already perpendicular to axis_dir (no X component)
    v_hat = tuple(np.cross(axis_dir, u_hat))
    with BuildPart() as p:
        add_foot_box(30, 45, FOOT_Z, center_y=center_y)
        chamfered = try_chamfer(p)
        with Locations((HOLE_X, 0, 0), (-HOLE_X, 0, 0)):
            Cylinder(HOLE_R, FOOT_Z, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        pl = Plane(origin=tuple(start), z_dir=tuple(axis_dir))
        with BuildSketch(pl):
            Circle(5.0)
        extrude(amount=STAB_LEN)
        with Locations(*dimple_points(3, tuple(end), tuple(axis_dir), u_hat, v_hat)):
            Sphere(radius=DIMPLE_SPHERE_R, mode=Mode.SUBTRACT)
    return p.part, {"chamfer_ok": chamfered, "axis_dir": axis_dir.tolist(), "end": end.tolist()}


def build_s4():
    """S4: modelled like S1 but with a taller/thinner foot (30 X x 8 Y x 30 Z) so that
    the foot's -Y side face (Y=-4) and a 1mm-deep flat cut on the stab's -Y side
    (also landing at Y=-4) share one plane. Printed rotated +90deg about X (done in
    prepare_print.py) so that shared plane becomes the bed."""
    with BuildPart() as p:
        Box(30, 8, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
        chamfered = try_chamfer(p)
        # holes run through the 8mm Y-thickness; in-plane coords X=+-10, Z=15 (foot mid-height)
        with Locations(Location((HOLE_X, 0, 15), (90, 0, 0)), Location((-HOLE_X, 0, 15), (90, 0, 0))):
            Cylinder(HOLE_R, 8, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(30)):
            Circle(5.0)
        extrude(amount=STAB_LEN)
        # flat on the -Y side of the stab only (Z=30..90), 1mm deep -> flat plane at Y=-4
        with Locations((0, -4, 30)):
            Box(20, 6, STAB_LEN, align=(Align.CENTER, Align.MAX, Align.MIN), mode=Mode.SUBTRACT)
        with Locations(*dimple_points(4, (0, 0, 30 + STAB_LEN), (0, 0, 1), (1, 0, 0), (0, 1, 0))):
            Sphere(radius=DIMPLE_SPHERE_R, mode=Mode.SUBTRACT)
    return p.part, {"chamfer_ok": chamfered}


def main():
    import trimesh

    variants = {
        "S1_d10_senkrecht": build_s1,
        "S2_d20_senkrecht": build_s2,
        "S3_d10_45grad": build_s3,
        "S4_d10_liegend": build_s4,
    }

    report = {}
    for name, builder in variants.items():
        print(f"building {name} ...")
        part, meta = builder()
        stl_path = OUT / f"{name}-native.stl"
        export_stl(part, str(stl_path), tolerance=0.01, angular_tolerance=0.1)
        mesh = trimesh.load_mesh(stl_path, process=True)
        # OCC tessellation of sphere-cap dimples leaves a benign degenerate (zero-area)
        # triangle at the sphere pole seam; strip it before the watertight check.
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
        assert mesh.is_watertight, f"{name}: mesh not watertight"
        assert len(mesh.split()) == 1, f"{name}: mesh not a single solid ({len(mesh.split())} pieces)"
        mesh.export(stl_path)  # persist the cleaned-up (now genuinely watertight) mesh
        vol = float(mesh.volume)
        bbox = np.ptp(mesh.bounds, axis=0).tolist()
        report[name] = {
            "stl": str(stl_path),
            "volume_mm3": vol,
            "bbox_native_mm": bbox,
            **meta,
        }
        print(f"  volume={vol:.1f} mm3  bbox(native)={[round(x,2) for x in bbox]}  meta={meta}")

    (HERE.parent / "var" / "print" / "geometry-report.json").write_text(
        json.dumps(report, indent=2, default=str)
    )
    print("done ->", HERE.parent / "var" / "print" / "geometry-report.json")


if __name__ == "__main__":
    main()
