#!/usr/bin/env python
"""Canonical exact M3 hybrid-hole cutters and FeatureScript generator.

Coordinates and lengths are millimetres. ``origin`` is the entry face and
``axis`` points inward. The optional ``x_dir`` is a unitless vector orthogonal
to ``axis`` and fixes the three-rib rotational phase. No screw-size or scale
parameter is accepted: this module is only the declared M3 interface.
"""

from __future__ import annotations

import argparse
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence


TOOLROOM_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROFILE = TOOLROOM_ROOT / "profiles/interfaces/m3-hybrid-hole.json"
DEFAULT_FS = Path(__file__).resolve().parents[1] / "lib/m3_hybrid_hole.fs"


@lru_cache(maxsize=4)
def load_profile(path: str | Path = DEFAULT_PROFILE) -> dict[str, Any]:
    """Load the sole dimensional authority for both generated backends."""
    with Path(path).open(encoding="utf-8") as stream:
        profile = json.load(stream)
    if profile.get("name") != "03_m3_hybrid_hole":
        raise ValueError("profile is not the canonical 03_m3_hybrid_hole")
    if profile["interface"].get("screw_nominal") != "M3":
        raise ValueError("this module does not scale or substitute screw sizes")
    if len(profile["contour"].get("arcs", [])) != 12:
        raise ValueError("canonical M3 hybrid contour must contain 12 arcs")
    return profile


def _vector3(value: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(value) != 3:
        raise ValueError(f"{name} must contain exactly three components")
    result = tuple(float(v) for v in value)
    if not all(math.isfinite(v) for v in result):
        raise ValueError(f"{name} components must be finite")
    return result  # type: ignore[return-value]


def _basis(
    axis: Sequence[float], x_dir: Sequence[float] | None
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    a = _vector3(axis, "axis")
    an = math.sqrt(sum(v * v for v in a))
    if an <= 1e-12:
        raise ValueError("axis must be nonzero")
    a = tuple(v / an for v in a)
    if x_dir is None:
        reference = (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0)
        projection = sum(reference[i] * a[i] for i in range(3))
        x = tuple(reference[i] - projection * a[i] for i in range(3))
    else:
        x = _vector3(x_dir, "x_dir")
        xn0 = math.sqrt(sum(v * v for v in x))
        if xn0 <= 1e-12:
            raise ValueError("x_dir must be nonzero")
        cosine = sum(a[i] * x[i] for i in range(3)) / xn0
        if abs(cosine) > 1e-9:
            raise ValueError("x_dir must be orthogonal to axis")
    xn = math.sqrt(sum(v * v for v in x))
    return a, tuple(v / xn for v in x)  # type: ignore[return-value]


def _positive_depth(depth_mm: float, relief: bool = False) -> float:
    depth = float(depth_mm)
    if not math.isfinite(depth) or depth <= 0:
        raise ValueError("depth_mm must be a finite positive length in millimetres")
    relief_depth = float(load_profile()["interface"]["entry_relief"]["apex_depth"])
    if relief and depth < relief_depth:
        raise ValueError(f"entry relief requires depth_mm >= {relief_depth:g}")
    return depth


def _local_contour_face():
    from build123d import Edge, Face, Vector, Wire

    edges = []
    for arc in load_profile()["contour"]["arcs"]:
        points = [Vector(float(p[0]), float(p[1]), 0.0) for p in arc["points"]]
        edges.append(Edge.make_three_point_arc(*points))
    wires = Wire.combine(edges, tol=1e-9)
    if len(wires) != 1 or not wires[0].is_closed:
        raise ValueError("profile arcs do not form one closed wire")
    face = Face(wires[0])
    if not face.is_valid:
        raise ValueError("profile arcs do not form a valid face")
    return face


def hybrid_tool(
    origin: Sequence[float],
    axis: Sequence[float],
    depth_mm: float,
    x_dir: Sequence[float] | None = None,
    entry_relief: bool = True,
):
    """Return the canonical M3 biting-hole cutter as a Build123d ``Solid``.

    ``origin`` is the relief/entry face in mm and the normalized ``axis`` points
    into the receiving material. ``x_dir`` is unitless and must be orthogonal to
    ``axis``. With relief enabled, the 45 degree cone narrows from R2.1 at the
    entry to its apex 2.1 mm inward. The cutter then continues to ``depth_mm``.
    """
    from build123d import Plane, Solid

    o = _vector3(origin, "origin")
    a, x = _basis(axis, x_dir)
    depth = _positive_depth(depth_mm, relief=entry_relief)
    plane = Plane(origin=o, x_dir=x, z_dir=a)
    core = Solid.extrude(_local_contour_face(), (0.0, 0.0, depth)).located(plane.location)
    if not entry_relief:
        return core
    relief = load_profile()["interface"]["entry_relief"]
    cone = Solid.make_cone(
        float(relief["entry_radius"]), 0.0, float(relief["apex_depth"])
    ).located(plane.location)
    result = core.fuse(cone)
    if len(result.solids()) != 1 or not result.is_valid:
        raise RuntimeError("hybrid cutter Boolean did not produce one valid solid")
    return result


def clearance_tool(
    origin: Sequence[float],
    axis: Sequence[float],
    depth_mm: float,
    x_dir: Sequence[float] | None = None,
):
    """Return the canonical M3 Ø3.4 clearance cutter as a Build123d ``Solid``.

    Units and frame conventions match :func:`hybrid_tool`; ``x_dir`` only fixes
    the otherwise irrelevant circular frame. The cylinder extends inward from
    ``origin`` by ``depth_mm``.
    """
    from build123d import Plane, Solid

    o = _vector3(origin, "origin")
    a, x = _basis(axis, x_dir)
    depth = _positive_depth(depth_mm)
    radius = float(load_profile()["interface"]["clearance_diameter"]) / 2.0
    return Solid.make_cylinder(radius, depth).located(
        Plane(origin=o, x_dir=x, z_dir=a).location
    )


def _fs_number(value: float) -> str:
    return repr(float(value))


def render_featurescript(profile: dict[str, Any] | None = None) -> str:
    """Generate the functions-only FeatureScript fragment from the profile."""
    p = profile or load_profile()
    interface = p["interface"]
    source = p["source"]
    arc_rows = []
    for arc in p["contour"]["arcs"]:
        points = ",".join(
            "[" + ",".join(_fs_number(v) for v in point) + "]"
            for point in arc["points"]
        )
        arc_rows.append(f"    [{points}]")
    arcs = ",\n".join(arc_rows)
    return f'''// GENERATED by scripts/m3_hybrid_hole.py from profiles/interfaces/m3-hybrid-hole.json.
// Functions-only fragment for FeatureScript 3044. Units: millimetres.
// Source: {source["document_id"]} / {source["microversion_id"]},
// part {source["part_id"]} / face {source["face_id"]} inner loop (12 exact arcs).
// origin is the entry face; axis points inward; xDirection fixes rib phase.

const M3_HYBRID_DEPTH = {_fs_number(interface["depth"])} * millimeter;
const M3_HYBRID_RELIEF_DEPTH = {_fs_number(interface["entry_relief"]["apex_depth"])} * millimeter;
const M3_HYBRID_RELIEF_RADIUS = {_fs_number(interface["entry_relief"]["entry_radius"])} * millimeter;
const M3_CLEARANCE_RADIUS = {_fs_number(interface["clearance_diameter"] / 2)} * millimeter;
const M3_HYBRID_ARCS = [
{arcs}
];

function m3CheckFrame(axis is Vector, xDirection is Vector, depth is ValueWithUnits, entryRelief is boolean)
{{
    if (abs(norm(axis) - 1) > 1e-10)
        throw regenError("M3 hybrid axis must be unit length");
    if (abs(norm(xDirection) - 1) > 1e-10 || abs(dot(axis, xDirection)) > 1e-10)
        throw regenError("M3 hybrid xDirection must be unit length and orthogonal to axis");
    if (depth <= 0 * millimeter)
        throw regenError("M3 hybrid depth must be positive");
    if (entryRelief && depth < M3_HYBRID_RELIEF_DEPTH)
        throw regenError("M3 hybrid depth is shorter than its entry relief");
}}

function m3HybridSketch(context is Context, id is Id, origin is Vector, axis is Vector, xDirection is Vector) returns Query
{{
    var sk = newSketchOnPlane(context, id, {{"sketchPlane": plane(origin, axis, xDirection)}});
    for (var i = 0; i < size(M3_HYBRID_ARCS); i += 1)
    {{
        var a = M3_HYBRID_ARCS[i];
        skArc(sk, "a" ~ i, {{"start": vector(a[0][0], a[0][1]) * millimeter,
                              "mid": vector(a[1][0], a[1][1]) * millimeter,
                              "end": vector(a[2][0], a[2][1]) * millimeter}});
    }}
    skSolve(sk);
    return qSketchRegion(id, false);
}}

function m3CircleSketch(context is Context, id is Id, origin is Vector, axis is Vector, xDirection is Vector, radius is ValueWithUnits) returns Query
{{
    var sk = newSketchOnPlane(context, id, {{"sketchPlane": plane(origin, axis, xDirection)}});
    skCircle(sk, "c", {{"center": vector(0, 0) * millimeter, "radius": radius}});
    skSolve(sk);
    return qSketchRegion(id, false);
}}

function m3ReliefTool(context is Context, id is Id, origin is Vector, axis is Vector, xDirection is Vector) returns Query
{{
    var sketchNormal = cross(xDirection, axis);
    var sk = newSketchOnPlane(context, id + "Profile", {{"sketchPlane": plane(origin, sketchNormal, xDirection)}});
    skLineSegment(sk, "entry", {{"start": vector(0, 0) * millimeter, "end": vector({_fs_number(interface["entry_relief"]["entry_radius"])}, 0) * millimeter}});
    skLineSegment(sk, "slope", {{"start": vector({_fs_number(interface["entry_relief"]["entry_radius"])}, 0) * millimeter, "end": vector(0, {_fs_number(interface["entry_relief"]["apex_depth"])}) * millimeter}});
    skLineSegment(sk, "axis", {{"start": vector(0, {_fs_number(interface["entry_relief"]["apex_depth"])}) * millimeter, "end": vector(0, 0) * millimeter}});
    skSolve(sk);
    opRevolve(context, id + "Revolve", {{"entities": qSketchRegion(id + "Profile", false),
        "axis": line(origin, axis), "angleForward": 360 * degree}});
    opDeleteBodies(context, id + "Clean", {{"entities": qCreatedBy(id + "Profile", EntityType.BODY)}});
    return qCreatedBy(id + "Revolve", EntityType.BODY);
}}

// origin: Vector of length; axis/xDirection: dimensionless unit vectors;
// depth: LENGTH. Returns one solid Query and performs no target Boolean.
export function m3HybridTool(context is Context, id is Id, origin is Vector, axis is Vector,
                              depth is ValueWithUnits, xDirection is Vector,
                              entryRelief is boolean) returns Query
{{
    m3CheckFrame(axis, xDirection, depth, entryRelief);
    var profile = m3HybridSketch(context, id + "Profile", origin, axis, xDirection);
    opExtrude(context, id + "Core", {{"entities": profile, "direction": axis,
        "endBound": BoundingType.BLIND, "endDepth": depth}});
    opDeleteBodies(context, id + "ProfileClean", {{"entities": qCreatedBy(id + "Profile", EntityType.BODY)}});
    var result = qCreatedBy(id + "Core", EntityType.BODY);
    if (entryRelief)
    {{
        var relief = m3ReliefTool(context, id + "Relief", origin, axis, xDirection);
        opBoolean(context, id + "ReliefUnion", {{"tools": qUnion([result, relief]),
            "operationType": BooleanOperationType.UNION}});
        result = qUnion([result, relief, qCreatedBy(id + "ReliefUnion", EntityType.BODY)]);
    }}
    return result;
}}

// Subtracts the canonical cutter from targets and returns the modified targets.
export function m3HybridHole(context is Context, id is Id, targets is Query, origin is Vector,
                              axis is Vector, depth is ValueWithUnits, xDirection is Vector,
                              entryRelief is boolean) returns Query
{{
    var tool = m3HybridTool(context, id + "Tool", origin, axis, depth, xDirection, entryRelief);
    opBoolean(context, id + "Cut", {{"targets": targets, "tools": tool,
        "operationType": BooleanOperationType.SUBTRACTION}});
    return qUnion([targets, qCreatedBy(id + "Cut", EntityType.BODY)]);
}}

// Canonical M3 clearance cutter: diameter {_fs_number(interface["clearance_diameter"])} mm.
export function m3ClearanceTool(context is Context, id is Id, origin is Vector, axis is Vector,
                                 depth is ValueWithUnits, xDirection is Vector) returns Query
{{
    m3CheckFrame(axis, xDirection, depth, false);
    var profile = m3CircleSketch(context, id + "Profile", origin, axis, xDirection, M3_CLEARANCE_RADIUS);
    opExtrude(context, id + "Core", {{"entities": profile, "direction": axis,
        "endBound": BoundingType.BLIND, "endDepth": depth}});
    opDeleteBodies(context, id + "Clean", {{"entities": qCreatedBy(id + "Profile", EntityType.BODY)}});
    return qCreatedBy(id + "Core", EntityType.BODY);
}}
'''


def render_compile_fixture(fragment: str | None = None) -> str:
    """Return a standalone Feature Studio fixture for native compilation."""
    lib = fragment or render_featurescript()
    return f'''FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

{lib}
function m3CouponBlock(context is Context, id is Id, corner is Vector) returns Query
{{
    var sk = newSketchOnPlane(context, id + "Sketch", {{"sketchPlane": plane(corner, vector(0, 0, 1), vector(1, 0, 0))}});
    skLineSegment(sk, "e0", {{"start": vector(0, 0) * millimeter, "end": vector(16, 0) * millimeter}});
    skLineSegment(sk, "e1", {{"start": vector(16, 0) * millimeter, "end": vector(16, 16) * millimeter}});
    skLineSegment(sk, "e2", {{"start": vector(16, 16) * millimeter, "end": vector(0, 16) * millimeter}});
    skLineSegment(sk, "e3", {{"start": vector(0, 16) * millimeter, "end": vector(0, 0) * millimeter}});
    skSolve(sk);
    opExtrude(context, id + "Extrude", {{"entities": qSketchRegion(id + "Sketch", false),
        "direction": vector(0, 0, 1), "endBound": BoundingType.BLIND, "endDepth": 10 * millimeter}});
    opDeleteBodies(context, id + "Clean", {{"entities": qCreatedBy(id + "Sketch", EntityType.BODY)}});
    return qCreatedBy(id + "Extrude", EntityType.BODY);
}}

annotation {{"Feature Type Name":"M3 hybrid module native coupon"}}
export const m3HybridModuleFixture = defineFeature(function(context is Context, id is Id, definition is map)
precondition {{ }}
{{
    var hybridDisplay = m3HybridTool(context, id + "HybridDisplay", vector(-24, 0, 0) * millimeter,
        vector(0, 0, 1), M3_HYBRID_DEPTH, vector(1, 0, 0), true);
    var hybridTarget = m3CouponBlock(context, id + "HybridCoupon", vector(-8, -8, 0) * millimeter);
    var hybridCoupon = m3HybridHole(context, id + "HybridHole", hybridTarget, vector(0, 0, 0) * millimeter,
        vector(0, 0, 1), M3_HYBRID_DEPTH, vector(1, 0, 0), true);
    var clearanceDisplay = m3ClearanceTool(context, id + "ClearanceDisplay", vector(24, 0, 0) * millimeter,
        vector(0, 0, 1), M3_HYBRID_DEPTH, vector(1, 0, 0));
    setProperty(context, {{"entities": hybridDisplay, "propertyType": PropertyType.NAME, "value":"M3 hybrid cutter"}});
    setProperty(context, {{"entities": hybridCoupon, "propertyType": PropertyType.NAME, "value":"M3 hybrid coupon"}});
    setProperty(context, {{"entities": clearanceDisplay, "propertyType": PropertyType.NAME, "value":"M3 clearance cutter 3.4 mm"}});
}});
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the maintained FeatureScript fragment")
    parser.add_argument("--fixture", type=Path, help="write a standalone native compile fixture")
    args = parser.parse_args()
    fragment = render_featurescript()
    if args.write:
        DEFAULT_FS.write_text(fragment, encoding="utf-8")
    if args.fixture:
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        args.fixture.write_text(render_compile_fixture(fragment), encoding="utf-8")
    if not args.write and args.fixture is None:
        print(fragment, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
