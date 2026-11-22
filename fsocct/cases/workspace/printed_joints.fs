FeatureScript 3070;
import(path : "onshape/std/common.fs", version : "3070.0");

// Independent teaching specimens after NeedItMakeIt's three cited videos.
// Millimetres; X = rail axis, Y = width, Z = specimen thickness.
// Clearance is a CAD allowance, not a calibrated physical fit or strength claim.

function jlSolid(q is Query) returns Query { return qBodyType(q, BodyType.SOLID); }
function jlOne(context is Context, q is Query, stage is string) returns Query
{
    var result = jlSolid(q);
    if (size(evaluateQuery(context, result)) != 1) throw regenError("Expected one connected solid: " ~ stage);
    return result;
}
function jlSketchPoly(context is Context, id is Id, pl is Plane, points is array) returns Query
{
    var sk = newSketchOnPlane(context, id, {"sketchPlane" : pl});
    for (var i = 0; i < size(points); i += 1)
        skLineSegment(sk, "e" ~ i, {"start" : vector(points[i][0], points[i][1]) * millimeter,
            "end" : vector(points[(i + 1) % size(points)][0], points[(i + 1) % size(points)][1]) * millimeter});
    skSolve(sk);
    return qSketchRegion(id, false);
}
function jlPrism(context is Context, id is Id, pl is Plane, points is array, depth is number) returns Query
{
    var q = jlSketchPoly(context, id + "sk", pl, points);
    opExtrude(context, id + "ex", {"entities" : q, "direction" : pl.normal,
        "endBound" : BoundingType.BLIND, "endDepth" : depth * millimeter});
    opDeleteBodies(context, id + "clean", {"entities" : qCreatedBy(id + "sk", EntityType.BODY)});
    return jlOne(context, qCreatedBy(id + "ex", EntityType.BODY), "prism");
}
function jlBlock(context is Context, id is Id, x0, y0, z0, x1, y1, z1) returns Query
{
    return jlPrism(context, id, plane(vector(0, 0, z0) * millimeter, vector(0, 0, 1), vector(1, 0, 0)),
        [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], z1 - z0);
}
function jlCombine(context is Context, id is Id, a is Query, b is Query, operation) returns Query
{
    if (operation == BooleanOperationType.SUBTRACTION)
        opBoolean(context, id, {"targets" : a, "tools" : b, "operationType" : operation});
    else opBoolean(context, id, {"tools" : qUnion([a, b]), "operationType" : operation});
    var candidates = operation == BooleanOperationType.SUBTRACTION ? [a, qCreatedBy(id, EntityType.BODY)] : [a, b, qCreatedBy(id, EntityType.BODY)];
    return jlOne(context, qUnion(candidates), "boolean " ~ id);
}
function jlAdd(context is Context, id is Id, a is Query, b is Query) returns Query
{ return jlCombine(context, id, a, b, BooleanOperationType.UNION); }
function jlCut(context is Context, id is Id, a is Query, b is Query) returns Query
{ return jlCombine(context, id, a, b, BooleanOperationType.SUBTRACTION); }

// Miter offset of a simple counter-clockwise polygon; small offsets only.
// Callers keep the offset below the narrowest local feature.
function jlOffsetPoly(points is array, amount is number) returns array
{
    var out = [];
    for (var i = 0; i < size(points); i += 1)
    {
        var a = vector(points[(i + size(points) - 1) % size(points)][0], points[(i + size(points) - 1) % size(points)][1]);
        var b = vector(points[i][0], points[i][1]);
        var c = vector(points[(i + 1) % size(points)][0], points[(i + 1) % size(points)][1]);
        var u = normalize(b - a); var v = normalize(c - b);
        var n = vector(u[1], -u[0]); var m = vector(v[1], -v[0]);
        var d = dot(n, b) + amount; var e = dot(m, b) + amount;
        var det = n[0] * m[1] - n[1] * m[0];
        out = append(out, [(d * m[1] - n[1] * e) / det, (n[0] * e - d * m[0]) / det]);
    }
    return out;
}
function jlJointLoft(context is Context, id is Id, planes is array, outlines is array) returns Query
{
    var regions = []; var sketches = [];
    for (var i = 0; i < size(planes); i += 1)
    {
        var sid = id + ("s" ~ i);
        regions = append(regions, jlSketchPoly(context, sid, planes[i], outlines[i]));
        sketches = append(sketches, qCreatedBy(sid, EntityType.BODY));
    }
    opLoft(context, id + "loft", {"profileSubqueries" : regions});
    opDeleteBodies(context, id + "clean", {"entities" : qUnion(sketches)});
    return jlOne(context, qCreatedBy(id + "loft", EntityType.BODY), "loft");
}
function jlDrafted(context is Context, id is Id, points is array, angle, allowance, height) returns Query
{
    var planes = []; var outlines = [];
    for (var z in [-0.02, height + 0.02])
    {
        planes = append(planes, plane(vector(0, 0, z) * millimeter, vector(0, 0, 1), vector(1, 0, 0)));
        outlines = append(outlines, jlOffsetPoly(points, allowance - z * tan(angle * degree)));
    }
    return jlJointLoft(context, id, planes, outlines);
}
function jlReflected(points is array, centerY is number) returns array
{
    var out = [];
    for (var i = size(points) - 1; i >= 0; i -= 1) out = append(out, [-points[i][0], points[i][1] + centerY]);
    return out;
}
function jlShifted(points is array, centerY is number) returns array
{
    var out = []; for (var p in points) out = append(out, [p[0], p[1] + centerY]); return out;
}
function jlTrimHeight(context is Context, id is Id, a is Query, height) returns Query
{
    return jlCombine(context, id + "trim", a, jlBlock(context, id + "box", -70, -14, 0, 70, 14, height), BooleanOperationType.INTERSECTION);
}
function jlFinger(context is Context, id is Id, centerY, mirrored, angle, allowance, height) returns Query
{
    // Analytic circular cap and tangent flanks, with parallel profile allowance.
    var nx = -0.25; var ny = -sqrt(1 - nx * nx);
    var regions = []; var sketches = [];
    for (var i = 0; i < 2; i += 1)
    {
        var z = i == 0 ? -0.02 : height + 0.02;
        var off = allowance - z * tan(angle * degree);
        var radius = 2.4 + off; var rootX = -2 - off;
        var rootY = (4 * nx + radius - nx * rootX) / ny;
        var pts = [[rootX, rootY], [4 + radius * nx, radius * ny], [4 + radius, 0], [4 + radius * nx, -radius * ny], [rootX, -rootY]];
        var v = [];
        for (var pt in pts) v = append(v, vector((mirrored ? -1 : 1) * pt[0], pt[1] + centerY) * millimeter);
        var sid = id + ("s" ~ i);
        var sk = newSketchOnPlane(context, sid, {"sketchPlane" : plane(vector(0, 0, z) * millimeter, vector(0, 0, 1), vector(1, 0, 0))});
        skLineSegment(sk, "lower", {"start" : v[0], "end" : v[1]});
        skArc(sk, "cap", {"start" : v[1], "mid" : v[2], "end" : v[3]});
        skLineSegment(sk, "upper", {"start" : v[3], "end" : v[4]});
        skLineSegment(sk, "root", {"start" : v[4], "end" : v[0]}); skSolve(sk);
        regions = append(regions, qSketchRegion(sid, false)); sketches = append(sketches, qCreatedBy(sid, EntityType.BODY));
    }
    opLoft(context, id + "loft", {"profileSubqueries" : regions});
    opDeleteBodies(context, id + "clean", {"entities" : qUnion(sketches)});
    return jlOne(context, qCreatedBy(id + "loft", EntityType.BODY), "rounded finger");
}

function jlStraightJoint(context is Context, id is Id, kind, gap, height) returns array
{
    var a = jlBlock(context, id + "A", -50, -14, 0, -gap / 2, 14, height);
    var b = jlBlock(context, id + "B", gap / 2, -14, 0, 50, 14, height);
    var angle = kind == 1 ? 0 : (kind == 6 ? 1.5 : 0.5);
    var central = [[-2, -4.5], [8, -7.18], [8, 7.18], [-2, 4.5]];
    if (kind != 7)
    {
        a = jlAdd(context, id + "maleA", a, jlDrafted(context, id + "tongue", central, angle, 0, height));
        b = jlCut(context, id + "socketB", b, jlDrafted(context, id + "cutter", central, angle, gap, height));
    }
    if (kind == 6)
    {
        var counter = [[-2, -1.6], [4.5, -3.0], [4.5, 3.0], [-2, 1.6]];
        for (var yc in [-10, 10])
        {
            var q = jlReflected(counter, yc); var sid = id + ("counter" ~ yc);
            b = jlAdd(context, sid + "add", b, jlDrafted(context, sid + "male", q, -angle, 0, height));
            a = jlCut(context, sid + "cut", a, jlDrafted(context, sid + "female", q, -angle, gap, height));
        }
    }
    if (kind == 7)
    {
        angle = 1;
        for (var yc in [-9, 0, 9])
        {
            var sid = id + ("fingerA" ~ yc); 
            a = jlAdd(context, sid + "add", a, jlFinger(context, sid + "male", yc, false, angle, 0, height));
            b = jlCut(context, sid + "cut", b, jlFinger(context, sid + "female", yc, false, angle, gap, height));
        }
        for (var yc in [-4.5, 4.5])
        {
            var sid = id + ("fingerB" ~ yc); 
            b = jlAdd(context, sid + "add", b, jlFinger(context, sid + "male", yc, true, -angle, 0, height));
            a = jlCut(context, sid + "cut", a, jlFinger(context, sid + "female", yc, true, -angle, gap, height));
        }
    }
    a = jlTrimHeight(context, id + "finishA", a, height);
    b = jlTrimHeight(context, id + "finishB", b, height);
    if (kind == 3)
    {
        // A shear preserves the common joint construction and creates a scarf plane.
        var shear = matrix([[1, 0, 1.5], [0, 1, 0], [0, 0, 1]]);
        opTransform(context, id + "scarf", {"bodies" : qUnion([a, b]), "transform" : transform(shear, vector(-0.75 * height, 0, 0) * millimeter)});
    }
    return [a, b];
}

function jlCone(context is Context, id is Id, cx, r0, r1, height) returns Query
{
    var regions = []; var sketches = [];
    for (var k = 0; k < 2; k += 1)
    {
        var sid = id + ("s" ~ k); var sk = newSketchOnPlane(context, sid, {"sketchPlane" : plane(vector(cx, 0, k * height) * millimeter, vector(0, 0, 1))});
        skCircle(sk, "c", {"center" : vector(0, 0) * millimeter, "radius" : (k == 0 ? r0 : r1) * millimeter}); skSolve(sk);
        regions = append(regions, qSketchRegion(sid, false)); sketches = append(sketches, qCreatedBy(sid, EntityType.BODY));
    }
    opLoft(context, id + "cone", {"profileSubqueries" : regions});
    opDeleteBodies(context, id + "clean", {"entities" : qUnion(sketches)});
    return jlOne(context, qCreatedBy(id + "cone", EntityType.BODY), "cone");
}
function jlCurvedTooth(context is Context, id is Id, radius, slope, gap, height, cutter) returns Query
{
    var planes = []; var outlines = []; var endAngle = cutter ? 31 : 30;
    var p = [[-1, -3], [4, -4.34], [4, 4.34], [-1, 3]];
    for (var k = 0; k <= 12; k += 1)
    {
        var angle = -90 + (endAngle + 90) * k / 12;
        var allowance = (cutter ? gap : 0) - (angle + 90) * PI / 180 * radius * tan(0.5 * degree);
        var section = jlOffsetPoly(p, allowance); var mapped = [];
        for (var v in section) mapped = append(mapped, [radius + v[0] + slope * v[1], height / 2 + v[1]]);
        var radial = vector(cos(angle * degree), sin(angle * degree), 0);
        planes = append(planes, plane(vector(-radius, 0, 0) * millimeter, vector(radial[1], -radial[0], 0), radial));
        outlines = append(outlines, mapped);
    }
    return jlJointLoft(context, id, planes, outlines);
}
function jlCurvedJoint(context is Context, id is Id, conical, gap, height) returns array
{
    var radius = conical ? 20 : 18; var slope = conical ? 0.2 : 0;
    var ca = jlCone(context, id + "coreA", -radius, radius - slope * height / 2, radius + slope * height / 2, height);
    var a = jlCombine(context, id + "clipA", ca, jlBlock(context, id + "windowA", -radius, -14, 0, 50, 14, height), BooleanOperationType.INTERSECTION);
    a = jlAdd(context, id + "backA", a, jlBlock(context, id + "railA", -50, -14, 0, -radius + 0.1, 14, height));
    var b = jlBlock(context, id + "railB", -radius, -14, 0, 50, 14, height);
    b = jlCut(context, id + "coreGap", b, jlCone(context, id + "coreB", -radius, radius - slope * height / 2 + gap, radius + slope * height / 2 + gap, height));
    a = jlAdd(context, id + "addTooth", a, jlCurvedTooth(context, id + "tooth", radius, slope, 0, height, false));
    b = jlCut(context, id + "cutGroove", b, jlCurvedTooth(context, id + "groove", radius, slope, gap, height, true));
    return [jlTrimHeight(context, id + "finishA", a, height), jlTrimHeight(context, id + "finishB", b, height)];
}

function jlScarfJoint(context is Context, id is Id, gap, height) returns array
{
    // Simplified straight-plane stopped scarf, with a separate pair of opposing keys.
    // The reference's oblique plane and elongated centering cones are not copied.
    var outline = [[-60, 0], [-30, 0], [-30, 13], [-22, 13], [-22, 5], [22, 15], [22, 7], [30, 7], [30, 20], [-60, 20]];
    var pl = plane(vector(0, 14, 0) * millimeter, vector(0, -1, 0), vector(1, 0, 0));
    var a = jlPrism(context, id + "A", pl, outline, 28);
    var b = jlBlock(context, id + "B", -30 + gap, -14, 0, 60, 14, 20);
    var tool = jlPrism(context, id + "tool", plane(vector(0, 15, 0) * millimeter, vector(0, -1, 0), vector(1, 0, 0)), jlOffsetPoly(outline, gap), 30);
    b = jlCut(context, id + "complement", b, tool);
    var slotA = jlBlock(context, id + "slotA", -5, -15, 8, 5, 15, 12);
    var slotB = jlBlock(context, id + "slotB", -5, -15, 8, 5, 15, 12);
    a = jlCut(context, id + "keyholeA", a, slotA); b = jlCut(context, id + "keyholeB", b, slotB);
    var rise = 20 * tan(2 * degree);
    var kp = plane(vector(-5 + gap, 0, 0) * millimeter, vector(1, 0, 0), vector(0, 1, 0));
    var k1 = jlPrism(context, id + "key1", kp, [[-20, 8 + gap], [20, 8 + gap], [20, 10 + rise - gap / 2], [-20, 10 - rise - gap / 2]], 10 - 2 * gap);
    var k2 = jlPrism(context, id + "key2", kp, [[-20, 10 - rise + gap / 2], [20, 10 + rise + gap / 2], [20, 12 - gap], [-20, 12 - gap]], 10 - 2 * gap);
    return [a, b, k1, k2];
}

const KIND = { (unitless) : [1, 1, 8] } as IntegerBoundSpec;
const GAP = { (millimeter) : [0.02, 0.10, 0.30] } as LengthBoundSpec;
annotation { "Feature Type Name" : "Printed joints lab" }
export const printedJoint = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Joint number" } isInteger(definition.kind, KIND);
        annotation { "Name" : "Nominal profile allowance" } isLength(definition.gap, GAP);
        annotation { "Name" : "Separate parts", "Default" : false } definition.separate is boolean;
    }
    {
        var k = definition.kind; var gap = definition.gap / millimeter; var parts;
        if (k == 4 || k == 5) parts = jlCurvedJoint(context, id + "curved", k == 5, gap, 20);
        else if (k == 8) parts = jlScarfJoint(context, id + "scarf", gap, 20);
        else parts = jlStraightJoint(context, id + "straight", k, gap, 20);
        var titles = ["Straight dovetail", "Tapered dovetail", "Scarfed dovetail", "Curved tapered dovetail", "Conical curved dovetail", "Echo-Lock principle", "Drop-Lock principle", "Keyed stopped scarf"];
        var colors = [color(0.36, 0.57, 0.66), color(0.87, 0.49, 0.32), color(0.89, 0.75, 0.37), color(0.73, 0.61, 0.32)];
        for (var i = 0; i < size(parts); i += 1)
        {
            var q = jlOne(context, parts[i], "finished part");
            setProperty(context, {"entities" : q, "propertyType" : PropertyType.NAME, "value" : "J0" ~ k ~ " / " ~ (i == 0 ? "A" : (i == 1 ? "B" : (i == 2 ? "Key 1" : "Key 2"))) ~ " / " ~ titles[k - 1]});
            setProperty(context, {"entities" : q, "propertyType" : PropertyType.APPEARANCE, "value" : colors[i]});
            if (definition.separate)
            {
                var shift = i == 0 ? vector(-12, -25, 0) : (i == 1 ? vector(12, 25, 0) : vector((i - 2) * 18 - 9, -55, -8));
                opTransform(context, id + ("separate" ~ i), {"bodies" : q, "transform" : transform(shift * millimeter)});
            }
        }
        if (size(evaluateQuery(context, jlSolid(qEverything(EntityType.BODY)))) != size(parts)) throw regenError("Unexpected residual solids");
    });
