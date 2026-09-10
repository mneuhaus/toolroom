#!/usr/bin/env python3
"""check_step.py — B-rep inventory of a STEP file against a design-language profile and a
manufacturing profile, followed by the mesh checks of check_mesh.py.

Reports per solid:
  * fillets: radius inventory split into plan-view corner fillets (axis ∥ build direction)
    and edge fillets; each radius compared with style.edges.radius_family / max_radius /
    outer_corner_radius
  * holes (full concave cylinders): diameter, orientation (vertical / horizontal relative
    to the build direction), mfg minimum, nearest insert / screw-clearance match
  * bosses / pins (full convex cylinders): diameter vs features.min_positive
  * chamfer candidates: narrow planar strips at ~45° to their neighbours, leg size
  * unbroken convex ~90° edges (if the style policy is broken/chamfer/fillet): count,
    total length, longest ones with midpoints
  * then: tessellation → thin regions / overhangs / build volume (check_mesh.analyse)

Usage:
  check_step.py part.step --mfg fdm.yaml --style te-like.yaml [--up +Z] [--json report.json]

Exit code 0 = no screening findings, 1 = findings, 2 = incomplete analysis.
Cylinder/edge classification is heuristic; it cannot infer mating or load-bearing intent.
Dependencies: build123d (OCP), plus those of check_mesh.py.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_mesh  # noqa: E402

try:
    import yaml
    from build123d import Axis, Edge, Face, GeomType, Vector, export_stl, import_step
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
except ImportError as e:  # pragma: no cover
    print(f"missing dependency: {e}. pip install build123d pyyaml", file=sys.stderr)
    sys.exit(2)

TOL_R = 0.06        # radius match tolerance vs. family (mm)
TOL_ANG = 8.0       # degrees


def load(path):
    if not path:
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n else v


def angle_deg(a, b):
    a, b = unit(a), unit(b)
    return math.degrees(math.acos(float(np.clip(np.dot(a, b), -1, 1))))


def vec(v) -> np.ndarray:
    return np.array([v.X, v.Y, v.Z], dtype=float)


def build_limits(bb, up):
    """Axial bounds in the selected build direction, including a negative up axis."""
    return sorted([float(np.dot(vec(bb.min), up)), float(np.dot(vec(bb.max), up))])


def strip_width(f: Face) -> float:
    """Width of a strip-like or ring-like planar face: 2·area / perimeter (exact for long
    strips and rings, a harmless underestimate for compact faces)."""
    per = sum(float(e.length) for e in f.edges())
    return 2.0 * float(f.area) / per if per > 0 else 0.0


# ----------------------------------------------------------------------------- adjacency
def edge_face_map(solid):
    m = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid.wrapped, TopAbs_EDGE, TopAbs_FACE, m)
    out = []
    for i in range(1, m.Extent() + 1):
        e = Edge(m.FindKey(i))
        fs = [Face(s) for s in m.FindFromIndex(i)]
        out.append((e, fs))
    return out


# ----------------------------------------------------------------------------- cylinders
def cylinder_info(f: Face, up: np.ndarray):
    ad = f.geom_adaptor()
    cyl = ad.Cylinder()
    ax = cyl.Axis()
    d = unit([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
    loc = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
    umin, umax, _, _ = BRepTools.UVBounds_s(f.wrapped)
    span = math.degrees(umax - umin)
    pt = vec(f.position_at(0.5, 0.5))
    n = vec(f.normal_at(f.position_at(0.5, 0.5)))
    radial = pt - loc - d * np.dot(pt - loc, d)
    convex = float(np.dot(n, radial)) > 0
    tilt = angle_deg(d, up)
    tilt = min(tilt, 180 - tilt)               # axis direction sign is arbitrary
    orient = "vertical" if tilt < 10 else ("horizontal" if tilt > 80 else f"tilted {tilt:.0f}°")
    return {
        "radius": round(float(cyl.Radius()), 3),
        "full": span >= 359.0,
        "span_deg": round(span, 1),
        "convex": convex,
        "orientation": orient,
        "centre": [round(float(x), 2) for x in vec(f.center())],
        "area": round(float(f.area), 2),
        "axis": [round(float(x), 3) for x in d],
    }


def nearest_table_match(dia: float, table: dict, key=None):
    best = None
    for name, val in (table or {}).items():
        v = val.get(key) if isinstance(val, dict) else val
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        d = abs(v - dia)
        if best is None or d < best[1]:
            best = (name, d, v)
    return best


# ----------------------------------------------------------------------------- analysis
def analyse_solid(solid, style: dict, mfg: dict, up: np.ndarray) -> dict:
    edges_cfg = style.get("edges", {})
    family = [float(r) for r in edges_cfg.get("radius_family", []) or []]
    max_r = edges_cfg.get("max_radius")
    corner_r = edges_cfg.get("outer_corner_radius")
    policy = edges_cfg.get("policy", "")
    bottom_edge = edges_cfg.get("bottom_edge", {}) or {}
    feats = mfg.get("features", {})
    min_hole_v = feats.get("min_hole_dia_vertical")
    min_hole_h = feats.get("min_hole_dia_horizontal")
    min_pos = feats.get("min_positive")

    fillets, holes, bosses = [], [], []
    for f in solid.faces():
        if f.geom_type != GeomType.CYLINDER:
            continue
        info = cylinder_info(f, up)
        r = info["radius"]
        # full cylinders are holes/bosses; so are D-holes, D-pins and slot ends (≥ ~180° of arc).
        # Anything shorter is an edge or corner fillet.
        if info["full"] or info["span_deg"] >= 170:
            if info["convex"]:
                item = {**info, "dia": round(2 * r, 3), "problems": []}
                if min_pos and 2 * r < float(min_pos):
                    item["problems"].append(f"pin Ø{2*r:.2f} < min_positive {min_pos}")
                bosses.append(item)
            else:
                dia = round(2 * r, 3)
                item = {**info, "dia": dia, "problems": [], "matches": []}
                lim = min_hole_v if info["orientation"] == "vertical" else min_hole_h
                if lim and dia < float(lim):
                    item["problems"].append(f"hole Ø{dia} < minimum {lim} ({info['orientation']})")
                if info["orientation"] == "horizontal":
                    item["problems"].append("horizontal hole: teardrop / flat-top the crown or print the axis vertical")
                ins = nearest_table_match(dia, mfg.get("inserts", {}), key="hole")
                scr = nearest_table_match(dia, mfg.get("screw_clearance", {}))
                for tag, m in (("insert", ins), ("screw clearance", scr)):
                    if m and m[1] <= 0.35:
                        item["matches"].append(f"{tag} {m[0]} ({m[2]} mm{' exact' if m[1] < 0.01 else f', off by {m[1]:+.2f}'})")
                holes.append(item)
        else:
            kind = ("plan corner" if info["orientation"] == "vertical" and info["convex"]
                    else ("edge fillet" if info["convex"] else "inner fillet"))
            item = {**info, "kind": kind, "problems": []}
            if kind == "plan corner" and corner_r is not None:
                if abs(r - float(corner_r)) > TOL_R:
                    item["problems"].append(f"plan corner R{r} ≠ outer_corner_radius {corner_r}")
            elif kind == "edge fillet":
                # convex edge fillets are the style's business: family, ceiling, bottom edge
                ok_bottom = bottom_edge.get("type") == "fillet" and abs(r - float(bottom_edge.get("size", 0) or 0)) <= TOL_R
                if family and not ok_bottom and not any(abs(r - fr) <= TOL_R for fr in family):
                    item["problems"].append(f"R{r} not in radius_family {family}")
                if max_r is not None and r > float(max_r) + TOL_R:
                    item["problems"].append(f"R{r} > max_radius {max_r}")
            else:
                # inner (concave) fillets belong to cut-outs and pockets: slot ends, pocket corners.
                # They follow inner_corner_radius / the process, not the outer family — inventory only.
                if max_r is not None and r > float(max_r) + TOL_R:
                    item["problems"].append(f"inner R{r} > max_radius {max_r}")
            fillets.append(item)

    # ---- chamfer candidates & unbroken edges via adjacency
    ef = edge_face_map(solid)
    planar_neighbors = defaultdict(list)     # face hash -> list of (edge, other face)
    unbroken = []

    def on_inner_wire(e: Edge, f: Face) -> bool:
        try:
            for w in f.inner_wires():
                for x in w.edges():
                    if x.is_same(e):
                        return True
        except Exception:
            pass
        return False

    for e, fs in ef:
        if len(fs) != 2:
            continue
        f1, f2 = fs
        if f1.geom_type != GeomType.PLANE or f2.geom_type != GeomType.PLANE:
            continue
        n1, n2 = vec(f1.normal_at()), vec(f2.normal_at())
        a = angle_deg(n1, n2)
        planar_neighbors[hash(f1)].append((e, f2, a))
        planar_neighbors[hash(f2)].append((e, f1, a))
        if 70 <= a <= 110 and e.length >= 3.0:
            # ignore edges of narrow strips (grooves, reveals, counterbore rims): nothing to break there
            if min(strip_width(f1), strip_width(f2)) < 1.5:
                continue
            # rims of holes, slots and pockets (edge sits on an inner loop of a face) are cut-out
            # edges, not silhouette edges — the edge policy is about the outer form
            if on_inner_wire(e, f1) or on_inner_wire(e, f2):
                continue
            # convex test: chord between the two faces near the edge lies inside the solid
            m = vec(e.position_at(0.5))
            p1 = vec(f1.position_at(0.5, 0.5))
            p2 = vec(f2.position_at(0.5, 0.5))
            d1 = unit(p1 - m) * 0.4
            d2 = unit(p2 - m) * 0.4
            chord_mid = m + (d1 + d2) / 2.0
            try:
                inside = solid.is_inside(Vector(*chord_mid), tolerance=1e-3)
            except Exception:
                inside = False
            if inside:
                bb = solid.bounding_box()
                on_outer = any(abs(m[i] - lim) < 0.3 for i, lim in
                               ((0, bb.min.X), (0, bb.max.X), (1, bb.min.Y), (1, bb.max.Y), (2, bb.min.Z), (2, bb.max.Z)))
                unbroken.append({"length": round(float(e.length), 2), "midpoint": [round(float(x), 2) for x in m],
                                 "dihedral": round(a, 1), "outer": bool(on_outer)})
    unbroken.sort(key=lambda d: (not d["outer"], -d["length"]))

    chamfers = []
    for f in solid.faces():
        if f.geom_type != GeomType.PLANE:
            continue
        nb = planar_neighbors.get(hash(f), [])
        at45 = [x for x in nb if abs(x[2] - 45) <= TOL_ANG]
        if len(at45) < 2:
            continue
        longest = max((x[0].length for x in nb), default=0.0)
        if longest <= 0:
            continue
        width = strip_width(f)
        if width > 4.0 or width < 0.2:            # slivers are not chamfers
            continue
        leg = width / math.sqrt(2)
        fb = f.bounding_box()
        chamfers.append({"leg": round(leg, 2), "strip_width": round(width, 2), "length": round(longest, 1),
                         "centre": [round(float(x), 2) for x in vec(f.center())],
                         "z_extent": round(float(np.dot(vec(fb.max) - vec(fb.min), np.abs(up))), 2), "convex": True})

    # conical faces: chamfers on round bosses/knobs (convex) and countersinks / insert
    # mouths (concave). Only convex ones are style features; concave ones are functional.
    for f in solid.faces():
        if f.geom_type != GeomType.CONE:
            continue
        try:
            cone = f.geom_adaptor().Cone()
            ax = cone.Axis()
            d = unit([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
            apex = np.array([cone.Apex().X(), cone.Apex().Y(), cone.Apex().Z()])
            pt = vec(f.position_at(0.5, 0.5))
            n = vec(f.normal_at(f.position_at(0.5, 0.5)))
            radial = pt - apex - d * np.dot(pt - apex, d)
            convex = float(np.dot(n, radial)) > 0
            bb = f.bounding_box()
            ext = np.array([bb.max.X - bb.min.X, bb.max.Y - bb.min.Y, bb.max.Z - bb.min.Z])
            tilt = angle_deg(d, up)
            tilt = min(tilt, 180 - tilt)
            leg = float(np.dot(ext, np.abs(up))) if tilt < 10 else float(ext.min())
            semi = abs(math.degrees(cone.SemiAngle()))
        except Exception:
            continue
        if leg < 0.15 or leg > 4.0:
            continue
        chamfers.append({"leg": round(leg, 2), "strip_width": round(leg * math.sqrt(2), 2), "length": round(float(f.area) / max(leg, 1e-6), 1),
                         "centre": [round(float(x), 2) for x in vec(f.center())], "conical": True,
                         "angle": round(semi, 1), "convex": bool(convex), "z_extent": round(float(np.dot(ext, np.abs(up))), 2)})

    # ---- summaries
    def inventory(items, key):
        inv = defaultdict(lambda: {"count": 0, "problems": 0})
        for it in items:
            k = it[key]
            inv[k]["count"] += 1
            inv[k]["problems"] += int(bool(it.get("problems")))
        return {str(k): v for k, v in sorted(inv.items())}

    chamfer_inv = defaultdict(int)
    for c in chamfers:
        chamfer_inv[round(c["leg"], 1)] += 1              # bin to 0.1 mm

    edge_treatment = edges_cfg.get("edge_treatment", {}) or {}
    outer_unbroken = [u for u in unbroken if u["outer"]]
    unbroken_flag = policy in ("broken", "chamfer", "fillet") and len(outer_unbroken) > 0
    problems = []
    for it in fillets + holes + bosses:
        for p in it.get("problems", []):
            problems.append(f"{p} at {it['centre']}")
    if unbroken_flag:
        total = sum(u["length"] for u in outer_unbroken)
        problems.append(f"{len(outer_unbroken)} unbroken ~90° convex edges on the outer silhouette ({total:.0f} mm) but style policy is '{policy}'")
    if edge_treatment.get("type") == "chamfer" and edge_treatment.get("size") and chamfers:
        want = float(edge_treatment["size"])
        bottom = float((edges_cfg.get("bottom_edge") or {}).get("size", want) or want)
        knob = float(((style.get("controls", {}) or {}).get("knob_cap", {}) or {}).get("chamfer", 0) or 0)
        allowed = [want, bottom] + ([knob] if knob else [])
        # strip widths are estimated (2·area/perimeter), ~5–10 % low on short mitred strips,
        # and sizes get quantised to layer multiples: compare with a relative tolerance
        # the edge treatment applies to the silhouette: chamfers on the top/bottom rim and on
        # vertical corner edges. Mid-height chamfers (groove ceilings, lip reliefs) and
        # concave ones (countersinks, insert mouths) are functional and not compared.
        sb = solid.bounding_box()
        zmin, zmax = build_limits(sb, up)

        def on_silhouette(c):
            z, leg = float(np.dot(c["centre"], up)), c["leg"]
            near_rim = (zmax - z) <= 1.5 * leg + 0.3 or (z - zmin) <= 1.5 * leg + 0.3
            vertical = c.get("z_extent", 0) >= 0.5 * (zmax - zmin)
            return c.get("convex", True) and (near_rim or vertical)

        styled = [c for c in chamfers if on_silhouette(c)]
        off = [c for c in styled if all(abs(c["leg"] - a) > max(0.2, 0.15 * a) for a in allowed)]
        if off:
            problems.append(f"{len(off)} chamfer(s) deviate from edge_treatment.size {want}: legs {sorted({c['leg'] for c in off})}")

    return {
        "faces": len(solid.faces()),
        "edges": len(solid.edges()),
        "fillets": fillets,
        "fillet_inventory": inventory(fillets, "radius"),
        "holes": holes,
        "hole_inventory": inventory(holes, "dia"),
        "bosses": bosses,
        "chamfers": chamfers,
        "chamfer_inventory": {str(k): v for k, v in sorted(chamfer_inv.items())},
        "unbroken_edges": unbroken[:20],
        "unbroken_count": len(unbroken),
        "unbroken_outer_count": len(outer_unbroken),
        "problems": problems,
    }


def analyse(path: str, style: dict, mfg: dict, up_name: str = "+Z", samples: int = 0,
            inlay_indices: tuple = (), inlay_max_height: float = 0.0) -> dict:
    shape = import_step(path)
    solids = shape.solids()
    if not solids:
        raise ValueError("STEP contains no solid bodies")
    if any(i < 0 or i >= len(solids) for i in inlay_indices):
        raise ValueError("inlay solid index is outside the STEP solid list")
    up = check_mesh.UP[up_name]
    report = {"file": path, "style": style.get("meta", {}).get("id", "none"), "profile": mfg.get("id", "none"),
              "up": up_name, "solids": []}
    all_problems = []
    errors = []
    for i, s in enumerate(solids):
        rep = analyse_solid(s, style, mfg, up)
        rep["index"] = i
        bb = s.bounding_box()
        lo, hi = build_limits(bb, up)
        rep["build_height"] = hi - lo
        rep["inlay"] = i in inlay_indices
        if rep["inlay"] and (inlay_max_height <= 0 or hi - lo > inlay_max_height + 1e-6):
            raise ValueError(f"solid {i}: explicit inlay exceeds the supplied build-height limit")
        with tempfile.TemporaryDirectory() as td:
            stl = Path(td) / f"solid_{i}.stl"
            export_stl(s, str(stl), tolerance=0.02, angular_tolerance=0.1)
            rep["mesh"] = check_mesh.analyse(str(stl), mfg, up=up_name, samples=samples,
                                             inlay_max_height=inlay_max_height if rep["inlay"] else 0)
        errors += [f"solid {i}: {p}" for p in rep["mesh"]["analysis_errors"]]
        all_problems += [f"solid {i}: {p}" for p in rep["problems"]]
        all_problems += [f"solid {i}: {p}" for p in rep["mesh"]["problems"]]
        report["solids"].append(rep)
    report["problems"] = all_problems
    report["analysis_errors"] = errors
    report["analysis_complete"] = not errors
    report["clean"] = not all_problems and not errors
    report["status"] = "incomplete" if errors else ("review" if all_problems else "no_findings")
    report["limitations"] = "B-rep feature candidates and sampled mesh screening; not functional or physical validation."
    return report


def print_report(rep: dict) -> None:
    print(f"== {rep['file']}  (style {rep['style']}, profile {rep['profile']}, up {rep['up']})")
    for s in rep["solids"]:
        print(f"-- solid {s['index']}: {s['faces']} faces, {s['edges']} edges" + ("  [inlay / colour layer]" if s.get("inlay") else ""))
        if s.get("inlay"):
            print("   wall sampling skipped by explicit inlay designation; other checks retained")
        if s["fillet_inventory"]:
            print("   fillets (radius: count/problems): " + ", ".join(
                f"R{k}: {v['count']}/{v['problems']}" for k, v in s["fillet_inventory"].items()))
            kinds = defaultdict(list)
            for f in s["fillets"]:
                kinds[f["kind"]].append(f["radius"])
            print("   " + "; ".join(f"{k}: R{sorted(set(v))}" for k, v in kinds.items()))
        else:
            print("   fillets: none")
        if s["chamfer_inventory"]:
            print("   chamfers (leg mm: count): " + ", ".join(f"{k}: {v}" for k, v in s["chamfer_inventory"].items()))
        else:
            print("   chamfers: none detected")
        if s["holes"]:
            print("   holes:")
            for h in s["holes"]:
                extra = ("  " + "; ".join(h["matches"])) if h["matches"] else ""
                print(f"     Ø{h['dia']:<6} {h['orientation']:<10} at {h['centre']}{extra}")
                for p in h["problems"]:
                    print(f"        ! {p}")
        if s["bosses"]:
            print("   bosses/pins: " + ", ".join(f"Ø{b['dia']} {b['orientation']}" for b in s["bosses"]))
        print(f"   unbroken ~90° convex edges ≥ 3 mm: {s['unbroken_outer_count']} on the outer silhouette, "
              f"{s['unbroken_count'] - s['unbroken_outer_count']} interior"
              + (f"; longest {s['unbroken_edges'][0]['length']} mm at {s['unbroken_edges'][0]['midpoint']}" if s["unbroken_edges"] else ""))
        for p in s["problems"]:
            print(f"   ! {p}")
        print("   mesh checks:")
        m = s["mesh"]
        t = m["thickness"]
        print(f"     thickness min {t.get('min_thickness_found')} mm (limit {t.get('threshold_min')}), "
              f"thin regions {len(t.get('regions', []))}; overhang regions {len(m['overhangs']['regions'])}; "
              f"watertight {m['watertight']}; build volume "
              f"{'ok' if m['bounds'].get('fits_build_volume') else ('TOO BIG' if m['bounds'].get('fits_build_volume') is False else 'n/a')}")
        for r in t.get("regions", [])[:6]:
            print(f"       thin [{r['severity']}] {r['min_thickness']} mm at {r['centre']}")
        for r in m["overhangs"]["regions"][:6]:
            print(f"       overhang [{r['severity']}] {r['mean_angle_from_vertical']}° at {r['centre']}: {r['verdict']}")
    for err in rep.get("analysis_errors", []):
        print(f"   INCOMPLETE: {err}")
    print("   RESULT: " + rep["status"] + f"; {len(rep['problems'])} screening finding(s)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step")
    ap.add_argument("--mfg", help="manufacturing profile YAML")
    ap.add_argument("--style", help="design-language profile YAML")
    ap.add_argument("--up", default="+Z", choices=list(check_mesh.UP))
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--inlay-solid", type=int, action="append", default=[], help="explicit zero-based inlay solid index; repeat as needed")
    ap.add_argument("--inlay-max-height", type=float, default=0, help="maximum inlay height along --up; requires --inlay-solid")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    if not Path(args.step).exists():
        print(f"no such file: {args.step}", file=sys.stderr)
        return 2
    try:
        rep = analyse(args.step, load(args.style), load(args.mfg), up_name=args.up, samples=args.samples,
                      inlay_indices=tuple(args.inlay_solid), inlay_max_height=args.inlay_max_height)
        print_report(rep)
    except Exception as exc:
        rep = {"file": args.step, "clean": False, "status": "incomplete", "analysis_complete": False,
               "analysis_errors": [str(exc)], "problems": []}
        print(f"INCOMPLETE: {exc}", file=sys.stderr)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(rep, f, indent=2, default=str)
    return 2 if not rep["analysis_complete"] else (0 if rep["clean"] else 1)


if __name__ == "__main__":
    sys.exit(main())
