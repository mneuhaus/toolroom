FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");

// HEISSER DRAHT R1 — conceptual dimensions in mm, all assumptions.
// X = width, -Y = player/front, Z = height from floor in deployed pose.
// Two posed native Part Studios are intended. No motion mates are claimed.
export const HD = {
    "width" : 660, "panelHeight" : 370, "panelThickness" : 6,
    "panelBottom" : 620, "panelY" : 42,
    "pivotZ" : 600, "pivotY" : 100, "legAngle" : 23,
    "legWidth" : 48, "legThickness" : 24, "legX" : 302,
    "wireDiameter" : 4, "courseY" : -20,
    "ringInnerDiameter" : 30, "ringWireDiameter" : 3,
    "parkX" : 248, "parkHeight" : 720
};

function slab(context is Context, id is Id, o is Vector, n is Vector, x is Vector, pts is array, h is number) returns Query
{
    var s = newSketchOnPlane(context, id + "sk", { "sketchPlane" : plane(o * millimeter, n, x) });
    var p = [];
    for (var v in pts) p = append(p, vector(v[0], v[1]) * millimeter);
    p = append(p, p[0]);
    skPolyline(s, "outline", { "points" : p }); skSolve(s);
    opExtrude(context, id + "ex", { "entities" : qSketchRegion(id + "sk", true), "direction" : n, "endBound" : BoundingType.BLIND, "endDepth" : h * millimeter });
    opDeleteBodies(context, id + "ds", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    return qCreatedBy(id + "ex", EntityType.BODY);
}
function makeBox(context is Context, id is Id, a is Vector, b is Vector) returns Query
{
    return slab(context, id, vector(0, 0, a[2]), vector(0, 0, 1), vector(1, 0, 0), [[a[0], a[1]], [b[0], a[1]], [b[0], b[1]], [a[0], b[1]]], b[2] - a[2]);
}
function cylinder(context is Context, id is Id, o is Vector, n is Vector, r is number, h is number) returns Query
{
    var s = newSketchOnPlane(context, id + "sk", { "sketchPlane" : plane(o * millimeter, n) });
    skCircle(s, "circle", { "center" : vector(0, 0) * millimeter, "radius" : r * millimeter }); skSolve(s);
    opExtrude(context, id + "ex", { "entities" : qSketchRegion(id + "sk", true), "direction" : n, "endBound" : BoundingType.BLIND, "endDepth" : h * millimeter });
    opDeleteBodies(context, id + "ds", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    return qCreatedBy(id + "ex", EntityType.BODY);
}
function cut(context is Context, id is Id, b is Query, t is Query)
{ opBoolean(context, id, { "targets" : b, "tools" : t, "operationType" : BooleanOperationType.SUBTRACTION }); }
function join(context is Context, id is Id, b is array) returns Query
{
    opBoolean(context, id, { "tools" : qUnion(b), "operationType" : BooleanOperationType.UNION });
    return qBodyType(qUnion(append(b, qCreatedBy(id, EntityType.BODY))), BodyType.SOLID);
}
function named(context is Context, b is Query, name is string, c)
{
    if (size(evaluateQuery(context, b)) != 1) throw regenError("Expected one solid: " ~ name);
    setProperty(context, { "entities" : b, "propertyType" : PropertyType.NAME, "value" : name });
    setProperty(context, { "entities" : b, "propertyType" : PropertyType.APPEARANCE, "value" : c });
}
function fold(context is Context, id is Id, q is Query, y is number, angle)
{ opTransform(context, id, { "bodies" : q, "transform" : rotationAround(line(vector(0, y, HD.pivotZ) * millimeter, vector(1, 0, 0)), angle) }); }

function game(context is Context, id is Id, stowed is boolean)
{
    const wood = color(0.76, 0.62, 0.43);
    const plywood = color(0.91, 0.81, 0.60);
    const metal = color(0.66, 0.71, 0.77);
    const dark = color(0.14, 0.19, 0.24);
    const green = color(0.15, 0.60, 0.38);
    const orange = color(0.97, 0.45, 0.10);
    const blue = color(0.12, 0.49, 0.70);
    var b = makeBox(context, id + "back", vector(-HD.width / 2, HD.panelY, HD.panelBottom), vector(HD.width / 2, HD.panelY + HD.panelThickness, HD.panelBottom + HD.panelHeight));
    var carry = makeBox(context, id + "carryOpening", vector(-50, 41, 956), vector(50, 49, 976));
    cut(context, id + "carryOpeningCut", b, carry);
    named(context, b, "LASER 01 Backboard 660x370x6 - assumed plywood", plywood);
    for (var side in [-1, 1])
    {
        var sx = side * HD.legX;
        b = makeBox(context, id + ("stile" ~ side), vector(sx - 24, 48, 576), vector(sx + 24, 72, 1010));
        for (var zz in [600, 640])
        {
            var t = cylinder(context, id + ("stileHole" ~ side ~ "_" ~ zz), vector(sx - 25, 60, zz), vector(1, 0, 0), 3.25, 50);
            cut(context, id + ("stileCut" ~ side ~ "_" ~ zz), b, t);
        }
        named(context, b, "TIMBER Fixed side stile 434x48x24 " ~ side, wood);
        for (var zz in [600, 640])
        {
            b = cylinder(context, id + ("stileBolt" ~ side ~ "_" ~ zz), vector(sx - 38, 60, zz), vector(1, 0, 0), 3, 76);
            named(context, b, "HARDWARE M6 stile to cheek bolt " ~ side ~ "_" ~ zz, metal);
            for (var ss in [-1, 1])
            {
                var xx = sx + (ss == -1 ? -26 : 24);
                b = cylinder(context, id + ("spacer" ~ side ~ "_" ~ zz ~ "_" ~ ss), vector(xx, 60, zz), vector(1, 0, 0), 6, 2);
                var h = cylinder(context, id + ("spacerHole" ~ side ~ "_" ~ zz ~ "_" ~ ss), vector(xx - 1, 60, zz), vector(1, 0, 0), 3.25, 4);
                cut(context, id + ("spacerCut" ~ side ~ "_" ~ zz ~ "_" ~ ss), b, h);
                named(context, b, "HARDWARE 2mm spacer washer stile to cheek " ~ side ~ "_" ~ zz ~ "_" ~ ss, metal);
            }
        }
        // Side guards protect the unchanged course and support a removable cover.
        var gx = side == 1 ? 330 : -336;
        b = makeBox(context, id + ("guard" ~ side), vector(gx, -146, 620), vector(gx + 6, 48, 990));
        named(context, b, "LASER Side guard 370x194x6 " ~ side, plywood);
        for (var cheek in [0, 1])
        {
            var cx = side == 1 ? (cheek == 0 ? 270 : 328) : (cheek == 0 ? -276 : -334);
            var cid = id + ("cheek" ~ side ~ "_" ~ cheek);
            b = makeBox(context, cid, vector(cx, -140, 530), vector(cx + 6, 140, 660));
            // Both upper stow pin and deployed pin bores are real geometry.
            for (var s in [-1, 1])
            {
                var hy = s * HD.pivotY;
                var holes = [[hy, 600, 4.25], [hy, 642, 3.25], [hy + s * 42 * sin(23 * degree), 600 - 42 * cos(23 * degree), 3.25]];
                for (var k = 0; k < size(holes); k += 1)
                {
                    var p = holes[k];
                    var t = cylinder(context, cid + ("h" ~ s ~ "_" ~ k), vector(cx - 1, p[0], p[1]), vector(1, 0, 0), p[2], 8);
                    cut(context, cid + ("c" ~ s ~ "_" ~ k), b, t);
                }
            }
            for (var zz in [600, 640])
            {
                var t = cylinder(context, cid + ("stileBore" ~ zz), vector(cx - 1, 60, zz), vector(1, 0, 0), 3.25, 8);
                cut(context, cid + ("stileBoreCut" ~ zz), b, t);
            }
            for (var yy in [-100, 100])
                for (var zz in [584, 616])
                {
                    var t = cylinder(context, cid + ("screw" ~ yy ~ "_" ~ zz), vector(cx - 1, yy, zz), vector(1, 0, 0), 2.75, 8);
                    cut(context, cid + ("screwCut" ~ yy ~ "_" ~ zz), b, t);
                }
            named(context, b, "LASER Hinge cheek 280x130x6 - M8 axle M6 lock " ~ side ~ "_" ~ cheek, plywood);
        }
    }
    const legL = (HD.pivotZ - HD.legThickness / 2 * sin(HD.legAngle * degree)) / cos(HD.legAngle * degree);
    for (var s in [-1, 1])
    {
        var hy = s * HD.pivotY;
        var angle = s * (stowed ? 180 : HD.legAngle) * degree;
        b = makeBox(context, id + ("fixedBeam" ~ s), vector(-270, hy - 24, 576), vector(270, hy + 24, 624));
        named(context, b, "TIMBER Fixed hinge beam 540x48x48 " ~ s, wood);
        for (var side in [-1, 1])
        {
            var x = side * HD.legX;
            var lid = id + ("leg" ~ s ~ "_" ~ side);
            b = makeBox(context, lid, vector(x - 24, hy - 12, 600 - legL), vector(x + 24, hy + 12, 620));
            for (var h in [[600, 4.25], [558, 3.25]])
            {
                var t = cylinder(context, lid + ("bore" ~ h[0]), vector(x - 25, hy, h[0]), vector(1, 0, 0), h[1], 50);
                cut(context, lid + ("boreCut" ~ h[0]), b, t);
            }
            fold(context, lid + "pose", b, hy, angle);
            named(context, b, "TIMBER Folding leg L=" ~ legL ~ " 48x24 " ~ s ~ "_" ~ side, wood);
            b = cylinder(context, lid + "axle", vector(x - 36, hy, 600), vector(1, 0, 0), 4, 72);
            named(context, b, "HARDWARE M8 shoulder axle with washers " ~ s ~ "_" ~ side, metal);
            var lockY = hy + s * 42 * sin((stowed ? 180 : HD.legAngle) * degree);
            var lockZ = 600 - 42 * cos((stowed ? 180 : HD.legAngle) * degree);
            b = cylinder(context, lid + "lock", vector(x - 36, lockY, lockZ), vector(1, 0, 0), 3, 72);
            named(context, b, "HARDWARE Captive M6 positive angular stop pin " ~ s ~ "_" ~ side, orange);
        }
        b = makeBox(context, id + ("crossbar" ~ s), vector(-278, hy - 12, 600 - legL + 22), vector(278, hy + 12, 600 - legL + 70));
        fold(context, id + ("crossbarPose" ~ s), b, hy, angle);
        named(context, b, "TIMBER Folding U-frame crossbar 556x48x24 " ~ s, wood);
    }
    // Continuous conductive route: tangent lines and R20/R30 bends, no mid supports.
    var pathId = id + "coursePath";
    var path = newSketchOnPlane(context, pathId, { "sketchPlane" : plane(vector(0, HD.courseY, 0) * millimeter, vector(0, -1, 0), vector(1, 0, 0)) });
    var lines = [[[-288,720],[-220,720]],[[-200,740],[-200,880]],[[-170,910],[-100,910]],[[-80,890],[-80,800]],[[-50,770],[10,770]],[[40,800],[40,900]],[[70,930],[150,930]],[[180,900],[180,750]],[[210,720],[288,720]]];
    var arcs = [[[-220,720],[-205.857864376269,725.857864376269],[-200,740]],[[-200,880],[-191.213203435596,901.213203435596],[-170,910]],[[-100,910],[-85.857864376269,904.142135623731],[-80,890]],[[-80,800],[-71.213203435596,778.786796564404],[-50,770]],[[10,770],[31.213203435596,778.786796564404],[40,800]],[[40,900],[48.786796564404,921.213203435596],[70,930]],[[150,930],[171.213203435596,921.213203435596],[180,900]],[[180,750],[188.786796564404,728.786796564404],[210,720]]];
    for (var i = 0; i < size(lines); i += 1)
        skLineSegment(path, "l" ~ i, { "start" : vector(lines[i][0][0], lines[i][0][1]) * millimeter, "end" : vector(lines[i][1][0], lines[i][1][1]) * millimeter });
    for (var i = 0; i < size(arcs); i += 1)
        skArc(path, "a" ~ i, { "start" : vector(arcs[i][0][0], arcs[i][0][1]) * millimeter, "mid" : vector(arcs[i][1][0], arcs[i][1][1]) * millimeter, "end" : vector(arcs[i][2][0], arcs[i][2][1]) * millimeter });
    skSolve(path);
    var profile = newSketchOnPlane(context, id + "wireProfile", { "sketchPlane" : plane(vector(-288, HD.courseY, 720) * millimeter, vector(1, 0, 0)) });
    skCircle(profile, "circle", { "center" : vector(0, 0) * millimeter, "radius" : HD.wireDiameter / 2 * millimeter }); skSolve(profile);
    opSweep(context, id + "wireSweep", { "profiles" : qSketchRegion(id + "wireProfile", true), "path" : qCreatedBy(pathId, EntityType.EDGE) });
    b = qCreatedBy(id + "wireSweep", EntityType.BODY);
    named(context, b, "METAL Continuous 4mm course - endpoints only - no joints", metal);
    opDeleteBodies(context, id + "courseSketchDelete", { "entities" : qUnion([qCreatedBy(pathId, EntityType.BODY), qCreatedBy(id + "wireProfile", EntityType.BODY)]) });
    for (var side in [-1, 1])
    {
        var x = side * HD.parkX;
        var endpointX = side == -1 ? -296 : 280;
        b = makeBox(context, id + ("insulator" ~ side), vector(endpointX, -30, 710), vector(endpointX + 16, 42, 730));
        var bore = cylinder(context, id + ("wireSocket" ~ side), vector(endpointX - 1, -20, 720), vector(1, 0, 0), 2.1, 18);
        cut(context, id + ("wireSocketCut" ~ side), b, bore);
        named(context, b, "PLA End insulator with 4.2mm conductor socket " ~ side, blue);
        var cradle = makeBox(context, id + ("cradle" ~ side), vector(x - 18, -42, 624), vector(x + 18, 42, 634));
        var pocket = makeBox(context, id + ("switchPocket" ~ side), vector(x - 11, -26, 626), vector(x + 11, -14, 633));
        cut(context, id + ("switchPocketCut" ~ side), cradle, pocket);
        var slot = makeBox(context, id + ("leverSlot" ~ side), vector(x - 8, -23, 632), vector(x + 8, -17, 636));
        cut(context, id + ("leverSlotCut" ~ side), cradle, slot);
        var ears = [cradle];
        for (var sign in [-1, 1])
            ears = append(ears, makeBox(context, id + ("ear" ~ side ~ "_" ~ sign), vector(x + sign * 13 - 2, -31, 633), vector(x + sign * 13 + 2, -9, 641)));
        cradle = join(context, id + ("cradleUnion" ~ side), ears);
        named(context, cradle, side == -1 ? "PLA START handle cradle - 7mm lift clearance" : "PLA FINISH handle cradle - independent microswitch", side == -1 ? green : orange);
        b = makeBox(context, id + ("microswitch" ~ side), vector(x - 10, -25, 626), vector(x + 10, -15, 632));
        named(context, b, "ELECTRONICS Microswitch 20x10x6 assumption " ~ side, dark);
        b = makeBox(context, id + ("lever" ~ side), vector(x - 8, -22, 635), vector(x + 8, -18, 637));
        named(context, b, "ELECTRONICS Lever compressed by parked handle " ~ side, metal);
        b = makeBox(context, id + ("channel" ~ side), vector(side == -1 ? -248 : 110, 35, 643), vector(side == -1 ? -110 : 248, 41, 651));
        named(context, b, "WIRING Fixed carrier channel - no hinge crossing " ~ side, dark);
    }
    // Ring is parked on START, threaded onto the course before end installation.
    var ringPath = newSketchOnPlane(context, id + "ringPath", { "sketchPlane" : plane(vector(-248, -20, 720) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
    const ringR = (HD.ringInnerDiameter + HD.ringWireDiameter) / 2;
    skCircle(ringPath, "ring", { "center" : vector(0, 0) * millimeter, "radius" : ringR * millimeter }); skSolve(ringPath);
    var ringProfile = newSketchOnPlane(context, id + "ringProfile", { "sketchPlane" : plane(vector(-248, -20, 720 - ringR) * millimeter, vector(0, 1, 0)) });
    skCircle(ringProfile, "wire", { "center" : vector(0, 0) * millimeter, "radius" : 1.5 * millimeter }); skSolve(ringProfile);
    opRevolve(context, id + "ringSweep", { "entities" : qSketchRegion(id + "ringProfile", true), "axis" : line(vector(-248, -20, 720) * millimeter, vector(1, 0, 0)), "angleForward" : 360 * degree });
    b = qCreatedBy(id + "ringSweep", EntityType.BODY);
    var stem = cylinder(context, id + "wandStem", vector(-248, -20, 650), vector(0, 0, 1), 1.5, 55);
    b = join(context, id + "wandUnion", [b, stem]);
    named(context, b, "METAL Ring ID30 wire3 plus stem - captive on course", metal);
    opDeleteBodies(context, id + "ringSketchDelete", { "entities" : qUnion([qCreatedBy(id + "ringPath", EntityType.BODY), qCreatedBy(id + "ringProfile", EntityType.BODY)]) });
    b = cylinder(context, id + "handle", vector(-248, -20, 636), vector(0, 0, 1), 8, 57);
    var relief = cylinder(context, id + "handleCableHole", vector(-248, -30, 648), vector(0, 1, 0), 2.2, 12);
    cut(context, id + "handleCableCut", b, relief);
    named(context, b, "PLA Wand grip 16x57 - 4.4mm side cable outlet", green);
    b = cylinder(context, id + "wandPigtail", vector(-248, -53, 648), vector(0, 1, 0), 2, 25);
    named(context, b, "WIRING Wand flexible pigtail - 1.2m service lead required", dark);
    // Electronics remain on fixed carrier; named bodies are assumption envelopes.
    b = makeBox(context, id + "case", vector(-110, -30, 638), vector(110, 42, 708));
    var pocket = makeBox(context, id + "casePocket", vector(-107, -31, 641), vector(107, 39, 705));
    cut(context, id + "casePocketCut", b, pocket);
    var usb = makeBox(context, id + "usbSlot", vector(-112, 2, 669), vector(-106, 18, 681));
    cut(context, id + "usbCut", b, usb);
    for (var x in [-100, 100]) for (var z in [648, 698])
    {
        var h = cylinder(context, id + ("caseScrew" ~ x ~ "_" ~ z), vector(x, 38, z), vector(0, 1, 0), 1.7, 5);
        cut(context, id + ("caseScrewCut" ~ x ~ "_" ~ z), b, h);
    }
    for (var x in [-40, 40])
    {
        var h = cylinder(context, id + ("shelfScrew" ~ x), vector(x, 36, 637), vector(0, 0, 1), 1.2, 5);
        cut(context, id + ("shelfScrewCut" ~ x), b, h);
    }
    named(context, b, "PLA Electronics enclosure 220x72x70 - four M3 back mount holes", dark);
    b = makeBox(context, id + "usbExtension", vector(-111, 3, 670), vector(-100, 17, 680));
    named(context, b, "ELECTRONICS Panel USB extension to Pico - opening aligned", metal);
    var cableDir = normalize(vector(14, 24, 0));
    b = cylinder(context, id + "usbExtensionCable", vector(-100, 10, 675), cableDir, 2, sqrt(14 * 14 + 24 * 24));
    named(context, b, "WIRING Internal flexible USB extension route - connector fit pending", dark);
    b = makeBox(context, id + "lid", vector(-110, -33, 638), vector(110, -30, 708));
    var window = makeBox(context, id + "window", vector(-24, -34, 663), vector(24, -29, 685));
    cut(context, id + "windowCut", b, window);
    var grille = cylinder(context, id + "grille", vector(72, -34, 673), vector(0, 1, 0), 17, 5);
    cut(context, id + "grilleCut", b, grille);
    named(context, b, "PLA Service lid - display window and 34mm speaker opening", dark);
    b = makeBox(context, id + "pico", vector(-86, 34, 654), vector(-35, 36, 675));
    named(context, b, "ELECTRONICS Raspberry Pi Pico 51x21 envelope - check mounting", green);
    for (var x in [-84, -37]) for (var z in [658.8, 670.2])
    {
        b = cylinder(context, id + ("picoBoss" ~ x ~ "_" ~ z), vector(x, 36, z), vector(0, 1, 0), 2.5, 3);
        var h = cylinder(context, id + ("picoBossHole" ~ x ~ "_" ~ z), vector(x, 35, z), vector(0, 1, 0), 1.1, 5);
        cut(context, id + ("picoBossCut" ~ x ~ "_" ~ z), b, h);
        named(context, b, "HARDWARE M2 separate 3mm standoff - pitch assumed " ~ x ~ "_" ~ z, metal);
    }
    b = makeBox(context, id + "display", vector(-27.5, -30, 660), vector(27.5, -22, 688));
    named(context, b, "ELECTRONICS Timer display 55x28x8 assumption", blue);
    b = cylinder(context, id + "speaker", vector(72, -29, 673), vector(0, 1, 0), 20, 14);
    named(context, b, "ELECTRONICS 40mm speaker - driven by amplifier not GPIO", metal);
    b = makeBox(context, id + "sound", vector(-25, 27, 644), vector(5, 37, 666));
    named(context, b, "ELECTRONICS UART sample player amp 30x22x10 assumption", green);
    b = makeBox(context, id + "power", vector(-45, 5, 598), vector(45, 30, 618));
    named(context, b, "ELECTRONICS USB powerbank 90x25x20 assumption - carrier strap mount", dark);
    var shelf = makeBox(context, id + "powerShelf", vector(-49, 1, 594), vector(49, 38, 598));
    var riser = makeBox(context, id + "powerRiser", vector(-49, 34, 596), vector(49, 38, 638));
    shelf = join(context, id + "shelfUnion", [shelf, riser]);
    for (var x in [-39, 39])
    {
        var t = makeBox(context, id + ("strapSlot" ~ x), vector(x - 2, 12, 593), vector(x + 2, 25, 599));
        cut(context, id + ("strapSlotCut" ~ x), shelf, t);
    }
    for (var x in [-40, 40])
    {
        var h = cylinder(context, id + ("shelfMount" ~ x), vector(x, 36, 624), vector(0, 0, 1), 1.2, 15);
        cut(context, id + ("shelfMountCut" ~ x), shelf, h);
    }
    named(context, shelf, "PLA Powerbank shelf with strap slots - M2 screws upward to case", dark);
    // A separate front cover clips to fixed side guards after folding supports.
    if (stowed)
    {
        b = makeBox(context, id + "cover", vector(-330, -150, 620), vector(330, -146, 990));
        named(context, b, "LASER Transport cover 660x370x4 - removable before play", plywood);
    }
}

annotation { "Feature Type Name" : "Heisser Draht - deployed R1" }
export const hotWireDeployed = defineFeature(function(context is Context, id is Id, definition is map)
    precondition { }
    { game(context, id, false); });

annotation { "Feature Type Name" : "Heisser Draht - stowed R1" }
export const hotWireStowed = defineFeature(function(context is Context, id is Id, definition is map)
    precondition { }
    { game(context, id, true); });
