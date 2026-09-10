#!/usr/bin/env python3
"""check_mesh.py — DFM checks on a mesh (STL/3MF/OBJ/PLY) against a manufacturing profile.

Reports, with coordinates so a generator can find and fix them:
  * watertightness / volume / bounding box vs. build volume (in the given build orientation)
  * thin regions: surface points whose ray thickness is below walls.min_thickness
    (error below walls.hard_min), clustered into regions with centre and extent
  * overhang regions: downward faces steeper than overhang.max_angle_deg (from vertical),
    clustered, with mean angle, area, horizontal span and a bridge verdict

Usage:
  check_mesh.py part.stl --mfg profiles/manufacturing/fdm-bambu-a1-0.4.yaml
  check_mesh.py part.stl --mfg fdm.yaml --up +Y --samples 8000 --json report.json

Exit code 0 = no screening findings, 1 = findings, 2 = incomplete analysis.
This is sampled geometric screening, not a strength or printability certificate.
Dependencies: numpy, scipy, trimesh, pyyaml, rtree.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import trimesh
    import yaml
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
except ImportError as e:  # pragma: no cover
    print(f"missing dependency: {e}. pip install numpy scipy trimesh pyyaml", file=sys.stderr)
    sys.exit(2)

UP = {
    "+Z": np.array([0, 0, 1.0]), "-Z": np.array([0, 0, -1.0]),
    "+Y": np.array([0, 1.0, 0]), "-Y": np.array([0, -1.0, 0]),
    "+X": np.array([1.0, 0, 0]), "-X": np.array([-1.0, 0, 0]),
}


# ----------------------------------------------------------------------------- helpers
def load_profile(path: str | None) -> dict:
    if not path:
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def rotate_to_z_up(mesh: trimesh.Trimesh, up: str) -> trimesh.Trimesh:
    """Return a copy of the mesh rotated so that the chosen 'up' axis becomes +Z."""
    if up == "+Z":
        return mesh.copy()
    target = np.array([0, 0, 1.0])
    src = UP[up]
    m = mesh.copy()
    rot = trimesh.geometry.align_vectors(src, target)
    m.apply_transform(rot)
    return m


def clusters_from_adjacency(flag_idx: np.ndarray, adjacency: np.ndarray, n: int):
    """Connected components among flagged faces using the face adjacency list."""
    if len(flag_idx) == 0:
        return []
    flagged = np.zeros(n, dtype=bool)
    flagged[flag_idx] = True
    a = adjacency[flagged[adjacency[:, 0]] & flagged[adjacency[:, 1]]]
    local = -np.ones(n, dtype=int)
    local[flag_idx] = np.arange(len(flag_idx))
    if len(a):
        rows, cols = local[a[:, 0]], local[a[:, 1]]
        g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(flag_idx), len(flag_idx)))
        _, labels = connected_components(g, directed=False)
    else:
        labels = np.arange(len(flag_idx))
    comps = []
    for lab in np.unique(labels):
        comps.append(flag_idx[labels == lab])
    return comps


def fmt(v) -> str:
    return f"{v:.2f}"


def region_raster(mesh: trimesh.Trimesh, faces_idx: np.ndarray, res: float = 0.1):
    """Rasterise a horizontal region in XY. Returns (mask, origin, res, width) where width is
    the largest inscribed width (2 x max distance to the boundary, distance transform) —
    the span a bridge or cantilever really has, independent of the bounding box (rings,
    L-shapes, thin lips)."""
    from scipy.ndimage import distance_transform_edt
    tri = mesh.vertices[mesh.faces[faces_idx]][:, :, :2]
    lo = tri.reshape(-1, 2).min(axis=0) - res
    hi = tri.reshape(-1, 2).max(axis=0) + res
    size = hi - lo
    n = np.ceil(size / res).astype(int) + 1
    while n[0] * n[1] > 1_200_000:          # cap the raster for very large regions
        res *= 2
        n = np.ceil(size / res).astype(int) + 1
    xs = lo[0] + np.arange(n[0]) * res
    ys = lo[1] + np.arange(n[1]) * res
    # Rasterise only each triangle's bounding rectangle. The original all-points
    # x 256-triangles intermediate used multiple gigabytes on a full-size shell.
    mask = np.zeros((n[0], n[1]), dtype=bool)
    for A, B, C in tri:
        ab, ac = B - A, C - A
        if abs(ab[0] * ac[1] - ab[1] * ac[0]) < 1e-12:
            continue
        begin = np.maximum(0, np.floor((np.minimum(np.minimum(A, B), C) - lo) / res).astype(int))
        end = np.minimum(n, np.ceil((np.maximum(np.maximum(A, B), C) - lo) / res).astype(int) + 1)
        gx = xs[begin[0]:end[0], None]
        gy = ys[None, begin[1]:end[1]]
        d1 = (gx - B[0]) * (A[1] - B[1]) - (A[0] - B[0]) * (gy - B[1])
        d2 = (gx - C[0]) * (B[1] - C[1]) - (B[0] - C[0]) * (gy - C[1])
        d3 = (gx - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (gy - A[1])
        mask[begin[0]:end[0], begin[1]:end[1]] |= ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
    if not mask.any():
        return mask, lo, res, 0.0
    dist = distance_transform_edt(mask) * res
    return mask, lo, res, float(max(0.0, 2.0 * dist.max() - res))


def exit_distance(mask, lo, res, start, direction, max_dist: float) -> float:
    """Walk from start along direction (XY) until leaving the region raster."""
    d = 0.0
    while d <= max_dist:
        p = start[:2] + direction[:2] * d
        ij = np.floor((p - lo) / res).astype(int)
        if ij[0] < 0 or ij[1] < 0 or ij[0] >= mask.shape[0] or ij[1] >= mask.shape[1] or not mask[ij[0], ij[1]]:
            return d
        d += res
    return max_dist


def classify_horizontal(mesh: trimesh.Trimesh, faces_idx: np.ndarray, max_bridge: float = 20.0,
                        step_out: float = 0.3, step_down: float = 0.5):
    """Verdict for a horizontal downward region: narrow lip / bridge / cantilever / island.

    For every boundary edge of the region we know locally which way is 'away from the
    region'. Material just beyond the edge and slightly below means that side is supported.
    A bridge has support on the far side across its width as well; a cantilever only on one
    side; an island on none. Widths ≤ 1.2 mm are narrow lips requiring print validation.
    Returns (kind, width_mm, supported_fraction).
    """
    faces = mesh.faces[faces_idx]
    v = mesh.vertices
    edge_owner = {}
    for fi, f in enumerate(faces):
        for k in range(3):
            key = tuple(sorted((int(f[k]), int(f[(k + 1) % 3]))))
            edge_owner.setdefault(key, []).append((fi, int(f[(k + 2) % 3])))
    b_mid, b_dir, b_len = [], [], []
    for key, owners in edge_owner.items():
        if len(owners) != 1:
            continue
        p1, p2 = v[key[0]], v[key[1]]
        opp = v[owners[0][1]]
        mid = (p1 + p2) / 2.0
        e = p2 - p1
        e[2] = 0.0
        ln = np.linalg.norm(e)
        if ln < 1e-9:
            continue
        e /= ln
        away = mid - opp
        away[2] = 0.0
        away -= e * np.dot(away, e)          # perpendicular to the edge, in plane
        na = np.linalg.norm(away)
        if na < 1e-9:
            continue
        b_mid.append(mid)
        b_dir.append(away / na)
        b_len.append(ln)
    if not b_mid:
        return "unknown", 0.0, 0.0
    b_mid, b_dir, b_len = np.array(b_mid), np.array(b_dir), np.array(b_len)
    mask, lo, res, width = region_raster(mesh, faces_idx)
    probe1 = b_mid + b_dir * step_out
    probe1[:, 2] -= step_down
    try:
        sup1 = mesh.contains(probe1)
    except Exception as exc:
        raise RuntimeError(f"near-side support classification failed: {exc}") from exc
    frac = float(b_len[sup1].sum() / b_len.sum())
    if frac < 0.05:
        return "island", width, frac
    if width <= 1.2:
        # A narrow underside still needs an anchored edge.
        return "lip", width, frac
    # from every supported edge, walk across the region to its far side and look for
    # material there: that is what makes it a bridge in that direction
    idx = np.nonzero(sup1)[0]
    if len(idx) > 160:                        # sample evenly, enough for a verdict
        idx = idx[np.linspace(0, len(idx) - 1, 160).astype(int)]
    spans = np.array([exit_distance(mask, lo, res, b_mid[i], -b_dir[i], 2.0 * max_bridge + 5.0) for i in idx])
    probe2 = b_mid[idx] - b_dir[idx] * (spans + step_out)[:, None]
    probe2[:, 2] -= step_down
    try:
        sup2 = mesh.contains(probe2)
    except Exception as exc:
        raise RuntimeError(f"far-side support classification failed: {exc}") from exc
    w = b_len[idx]
    far = float(w[sup2].sum() / w.sum()) if w.sum() else 0.0
    if far >= 0.5:
        span = float(np.median(spans[sup2])) if sup2.any() else width
        return "bridge", span, frac
    return "cantilever", width, frac


# ----------------------------------------------------------------------------- checks
def check_bounds(mesh: trimesh.Trimesh, mfg: dict) -> dict:
    ext = mesh.extents
    bv = mfg.get("build_volume")
    res = {"extents_xyz": [round(float(x), 2) for x in ext], "fits_build_volume": None,
           "min_xyz": mesh.bounds[0].tolist(), "max_xyz": mesh.bounds[1].tolist(),
           "on_bed": bool(abs(mesh.bounds[0, 2]) <= 0.05),
           "scope": "oriented dimensions and bed height; XY placement/overlap checked separately"}
    if bv:
        bv = np.array(bv, dtype=float)
        if bv.shape != (3,) or not np.isfinite(bv).all() or np.any(bv <= 0):
            raise ValueError("build_volume must contain three positive finite dimensions")
        fits = bool(np.all(ext <= bv + 1e-5))
        res["fits_after_z_quarter_turn"] = bool(np.all(ext[[1, 0, 2]] <= bv + 1e-5))
        res["fits_build_volume"] = bool(fits)
        res["build_volume"] = bv.tolist()
    return res


def check_thickness(mesh: trimesh.Trimesh, min_wall: float, hard_min: float,
                    samples: int, seed: int = 0) -> dict:
    """Ray thickness at sampled surface points; cluster the thin ones."""
    rng = np.random.default_rng(seed)
    area = mesh.area
    if samples <= 0:
        samples = int(np.clip(area / 4.0, 2000, 15000))  # roughly one point per 2x2 mm
    pts, fidx = trimesh.sample.sample_surface(mesh, samples, seed=seed)
    normals = mesh.face_normals[fidx]
    try:
        thick = trimesh.proximity.thickness(mesh, pts, exterior=False, normals=normals, method="ray")
    except Exception as e:  # pragma: no cover
        return {"error": f"thickness failed: {e}"}
    thick = np.asarray(thick, dtype=float)
    valid = np.isfinite(thick) & (thick > 0)
    if not valid.any():
        return {"error": "no valid thickness rays", "regions": [], "samples": 0}
    pts, thick, normals = pts[valid], thick[valid], normals[valid]

    thin = thick < min_wall
    # Ray thickness collapses next to sharp convex edges (a point 0.3 mm from a 90° corner
    # reads 0.3 mm) — those are corner artefacts, not thin walls. Drop thin samples that
    # sit closer to a sharp convex edge than ~1.3 x their measured thickness.
    if thin.any():
        try:
            sharp = (mesh.face_adjacency_angles > np.radians(45)) & mesh.face_adjacency_convex
            seg = mesh.vertices[mesh.face_adjacency_edges[sharp]]
            if len(seg):
                a, b = seg[:, 0], seg[:, 1]
                L = np.linalg.norm(b - a, axis=1)
                nseg = np.maximum(1, np.ceil(L / 0.3).astype(int))
                dense = np.concatenate([a[i] + (b[i] - a[i]) * np.linspace(0, 1, nseg[i] + 1)[:, None] for i in range(len(a))])
                d_edge, _ = cKDTree(dense).query(pts[thin])
                keep = d_edge > 1.3 * thick[thin]
                idx = np.nonzero(thin)[0]
                thin[idx[~keep]] = False
        except Exception:  # pragma: no cover
            pass
    result = {
        "requested_samples": samples,
        "valid_fraction": round(float(valid.mean()), 5),
        "method": "deterministic surface sampling with a convex-edge exclusion heuristic",
        "samples": int(len(thick)),
        "min_thickness_found": round(float(thick.min()), 3) if len(thick) else None,
        "threshold_min": min_wall,
        "threshold_hard": hard_min,
        "thin_fraction": round(float(thin.mean()), 4) if len(thick) else 0.0,
        "regions": [],
    }
    if not thin.any():
        return result

    tp, tt = pts[thin], thick[thin]
    tree = cKDTree(tp)
    pairs = tree.query_pairs(r=max(2.0 * min_wall, 2.0), output_type="ndarray")
    n = len(tp)
    if len(pairs):
        g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
        _, labels = connected_components(g, directed=False)
    else:
        labels = np.arange(n)
    for lab in np.unique(labels):
        sel = labels == lab
        if sel.sum() < 3:  # isolated samples: usually a sliver at an edge, still report as minor
            severity_floor = "minor"
        else:
            severity_floor = None
        p = tp[sel]
        t = tt[sel]
        lo, hi = p.min(axis=0), p.max(axis=0)
        sev = "error" if t.min() < hard_min else "warning"
        if severity_floor:
            sev = severity_floor
        result["regions"].append({
            "severity": sev,
            "samples": int(sel.sum()),
            "min_thickness": round(float(t.min()), 3),
            "median_thickness": round(float(np.median(t)), 3),
            "centre": [round(float(x), 2) for x in p.mean(axis=0)],
            "bbox_min": [round(float(x), 2) for x in lo],
            "bbox_max": [round(float(x), 2) for x in hi],
        })
    result["regions"].sort(key=lambda r: (r["severity"] != "error", r["min_thickness"]))
    return result


def check_overhangs(mesh: trimesh.Trimesh, max_angle: float, max_bridge: float,
                    min_area: float = 1.0, bed_tol: float = 0.05) -> dict:
    """Downward faces steeper than max_angle (measured from vertical), clustered."""
    n = mesh.face_normals
    nz = n[:, 2]
    # angle from vertical: 0 = vertical wall, 90 = horizontal ceiling
    angle = np.degrees(np.arcsin(np.clip(-nz, 0.0, 1.0)))
    down = nz < -1e-6
    zmin = mesh.bounds[0][2]
    tri_z = mesh.vertices[mesh.faces][:, :, 2]
    on_bed = np.all(tri_z <= zmin + bed_tol, axis=1)
    flagged = down & (angle > max_angle + 0.5) & ~on_bed
    idx = np.nonzero(flagged)[0]
    comps = clusters_from_adjacency(idx, mesh.face_adjacency, len(mesh.faces))
    areas = mesh.area_faces
    regions = []
    for c in comps:
        a = float(areas[c].sum())
        if a < min_area:
            continue
        verts = mesh.vertices[np.unique(mesh.faces[c])]
        lo, hi = verts.min(axis=0), verts.max(axis=0)
        span_xy = hi[:2] - lo[:2]
        mean_angle = float(np.average(angle[c], weights=areas[c]))
        max_a = float(angle[c].max())
        horizontal = mean_angle > 80
        severity = "error" if (mean_angle > max_angle + 10 or horizontal) else "warning"
        verdict = "steep overhang: chamfer it, rotate the part or split the body"
        if max_a > 85 and mean_angle < 75 and a < 60:
            verdict = "curved underside (top of a horizontal hole or arch): teardrop / flat-top it, or print the axis vertical"
        if horizontal:
            kind, width, _ = classify_horizontal(mesh, c, max_bridge=max_bridge)
            if kind == "lip":
                severity = "info"
                verdict = f"narrow overhang lip, {width:.1f} mm wide: inspect sliced paths and calibrate"
            elif kind == "bridge":
                if width <= max_bridge:
                    severity = "warning"
                    verdict = f"bridge candidate, span {width:.1f} mm ≤ screening limit {max_bridge}: verify paths and sag"
                else:
                    verdict = f"bridge, span {width:.1f} mm > {max_bridge}: needs support or a body split"
            elif kind == "cantilever":
                verdict = f"cantilever, {width:.1f} mm unsupported: 45° chamfer under it, rotate the part or split the body"
            elif kind == "island":
                verdict = f"floating underside, {width:.1f} mm wide (nothing below its edges): needs support or a different orientation"
            else:
                verdict = f"horizontal underside {span_xy[0]:.1f} x {span_xy[1]:.1f} mm: check support"
        regions.append({
            "severity": severity,
            "mean_angle_from_vertical": round(mean_angle, 1),
            "max_angle_from_vertical": round(float(angle[c].max()), 1),
            "area": round(a, 1),
            "centre": [round(float(x), 2) for x in verts.mean(axis=0)],
            "bbox_min": [round(float(x), 2) for x in lo],
            "bbox_max": [round(float(x), 2) for x in hi],
            "verdict": verdict,
        })
    regions.sort(key=lambda r: -r["area"])
    return {
        "threshold_angle": max_angle,
        "max_bridge": max_bridge,
        "flagged_area": round(float(areas[idx].sum()), 1) if len(idx) else 0.0,
        "total_area": round(float(areas.sum()), 1),
        "regions": regions,
    }


# ----------------------------------------------------------------------------- driver
def analyse(path: str, mfg: dict, up: str = "+Z", samples: int = 0, min_area: float = 1.0,
            inlay_max_height: float = 0.0) -> dict:
    mesh = trimesh.load(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):  # pragma: no cover
        mesh = trimesh.util.concatenate([g for g in mesh.geometry.values()])
    mesh = rotate_to_z_up(mesh, up)
    mesh.merge_vertices()
    if not len(mesh.faces) or not len(mesh.vertices) or not np.isfinite(mesh.vertices).all():
        raise ValueError("empty mesh or non-finite vertices")

    walls = mfg.get("walls", {})
    min_wall = float(walls.get("min_thickness", 1.2))
    hard_min = float(walls.get("hard_min", 0.8))
    ov = mfg.get("overhang", {})
    max_angle = float(ov.get("max_angle_deg", 45))
    max_bridge = float(ov.get("max_bridge", 20))

    report = {
        "file": str(path),
        "profile": mfg.get("id", "none"),
        "up": up,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "positive_volume": bool(mesh.is_volume and mesh.volume > 0),
        "connected_components": len(mesh.split(only_watertight=False)),
        "volume": round(float(mesh.volume), 1) if mesh.is_watertight else None,
        "faces": int(len(mesh.faces)),
        "bounds": check_bounds(mesh, mfg),
    }
    errors = []
    report["limitations"] = [
        "Thickness is sampled; convex-edge exclusions can hide thin details.",
        "Overhang classification does not inspect generated support or layer toolpaths.",
        "No material strength, fatigue, screw retention, assembly fit or motion test is performed.",
    ]
    if not mesh.is_watertight:
        report["note"] = "mesh is not watertight; thickness values are unreliable, fix the export first"
    if inlay_max_height and mesh.extents[2] <= inlay_max_height + 1e-6:
        report["note"] = (f"body is {mesh.extents[2]:.2f} mm tall: treated as a colour inlay / label layer, "
                          "wall-thickness check skipped (judge strokes by text.min_stroke instead)")
        report["thickness"] = {"skipped": True, "regions": [], "samples": 0, "min_thickness_found": None,
                               "threshold_min": min_wall, "threshold_hard": hard_min, "thin_fraction": 0.0}
    else:
        try:
            report["thickness"] = check_thickness(mesh, min_wall, hard_min, samples)
        except Exception as exc:
            report["thickness"] = {"error": str(exc), "regions": [], "samples": 0}
    if report["thickness"].get("error"):
        errors.append(report["thickness"]["error"])
    elif report["thickness"].get("valid_fraction", 1) < 0.95:
        errors.append("fewer than 95% of requested thickness rays returned valid measurements")
    try:
        report["overhangs"] = check_overhangs(mesh, max_angle, max_bridge, min_area=min_area)
    except Exception as exc:
        errors.append(f"overhang analysis failed: {exc}")
        report["overhangs"] = {"error": str(exc), "regions": [], "threshold_angle": max_angle,
                               "flagged_area": None, "total_area": float(mesh.area)}

    problems = []
    if report["bounds"].get("fits_build_volume") is False:
        problems.append("does not fit build volume")
    if not report["watertight"]:
        problems.append("not watertight")
    if not report["winding_consistent"] or not report["positive_volume"]:
        problems.append("inconsistent winding or non-positive closed volume")
    expected = mfg.get("expected_components")
    if expected is not None and report["connected_components"] != expected:
        problems.append(f"expected {expected} connected component(s), found {report['connected_components']}")
    if mfg.get("require_bed_contact") and not report["bounds"]["on_bed"]:
        problems.append("mesh is not on the Z=0 bed plane in the selected orientation")
    for r in report["thickness"].get("regions", []):
        if r["severity"] in ("error", "warning"):
            problems.append(f"thin region {r['min_thickness']} mm at {r['centre']}")
    for r in report["overhangs"]["regions"]:
        if r["severity"] == "error":
            problems.append(f"overhang {r['mean_angle_from_vertical']}° at {r['centre']}")
    report["problems"] = problems
    report["analysis_errors"] = errors
    report["analysis_complete"] = not errors
    report["clean"] = not problems and not errors
    report["status"] = "incomplete" if errors else ("review" if problems else "no_findings")
    return report


def print_report(rep: dict) -> None:
    print(f"== {rep['file']}  (profile {rep['profile']}, up {rep['up']})")
    b = rep["bounds"]
    fit = b.get("fits_build_volume")
    print(f"   extents {b['extents_xyz']} mm  build volume: "
          f"{'ok' if fit else ('TOO BIG' if fit is False else 'not checked')}")
    print(f"   watertight: {rep['watertight']}  faces: {rep['faces']}"
          + (f"  volume: {rep['volume']} mm³" if rep['volume'] else ""))
    if rep.get("note"):
        print(f"   note: {rep['note']}")
    t = rep["thickness"]
    if "error" in t:
        print(f"   thickness: {t['error']}")
    elif t.get("skipped"):
        print("   thickness: skipped (inlay / label layer)")
    else:
        print(f"   thickness: min {t['min_thickness_found']} mm over {t['samples']} samples "
              f"(min {t['threshold_min']}, hard {t['threshold_hard']}); thin fraction {t['thin_fraction']}")
        for r in t["regions"][:12]:
            print(f"     [{r['severity']:7}] {r['min_thickness']:5.2f} mm (median {r['median_thickness']:.2f}) "
                  f"at {r['centre']}  extent {r['bbox_min']}..{r['bbox_max']}  n={r['samples']}")
        if len(t["regions"]) > 12:
            print(f"     ... {len(t['regions']) - 12} more regions")
    o = rep["overhangs"]
    print(f"   overhangs > {o['threshold_angle']}°: {o['flagged_area']} of {o['total_area']} mm²")
    for r in o["regions"][:12]:
        print(f"     [{r['severity']:7}] {r['mean_angle_from_vertical']:5.1f}° (max {r['max_angle_from_vertical']:.0f}°) "
              f"area {r['area']} mm² at {r['centre']}  extent {r['bbox_min']}..{r['bbox_max']}")
        print(f"               -> {r['verdict']}")
    if len(o["regions"]) > 12:
        print(f"     ... {len(o['regions']) - 12} more regions")
    for err in rep.get("analysis_errors", []):
        print(f"   INCOMPLETE: {err}")
    print("   RESULT: " + rep["status"] + f"; {len(rep['problems'])} screening finding(s)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", nargs="+", help="STL/3MF/OBJ/PLY file(s), one body each, in print orientation")
    ap.add_argument("--mfg", help="manufacturing profile YAML")
    ap.add_argument("--up", default="+Z", choices=list(UP), help="which model axis points up on the printer")
    ap.add_argument("--samples", type=int, default=0, help="thickness sample points (0 = auto)")
    ap.add_argument("--min-area", type=float, default=1.0, help="ignore overhang clusters below this area (mm²)")
    ap.add_argument("--inlay-max-height", type=float, default=0.0,
                    help="bodies up to this height are colour inlays: skip the wall-thickness check (e.g. 0.5)")
    ap.add_argument("--json", help="write the full report(s) to this JSON file")
    args = ap.parse_args(argv)

    mfg = load_profile(args.mfg)
    reports, rc = [], 0
    for m in args.mesh:
        if not Path(m).exists():
            print(f"no such file: {m}", file=sys.stderr)
            return 2
        try:
            rep = analyse(m, mfg, up=args.up, samples=args.samples, min_area=args.min_area,
                          inlay_max_height=args.inlay_max_height)
            print_report(rep)
        except Exception as exc:
            rep = {"file": m, "analysis_complete": False, "analysis_errors": [str(exc)],
                   "status": "incomplete", "clean": False, "problems": []}
            print(f"INCOMPLETE: {m}: {exc}", file=sys.stderr)
        reports.append(rep)
        rc = max(rc, 2 if not rep["analysis_complete"] else (0 if rep["clean"] else 1))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(reports if len(reports) > 1 else reports[0], f, indent=2)
    return rc


if __name__ == "__main__":
    sys.exit(main())
