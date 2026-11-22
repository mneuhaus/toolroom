FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");

// Skirt Halves — zweiteiliger Trichter (Spiegelhaelften) fuer den Sorter BeltFeeder.
// Koordinaten wie Part Studio "Skirt" (Tail-lokal: z senkrecht zum Band, Band steigt
// nach -x zur Tunnelbruecke). Gebaut symmetrisch um y=0, am Ende um Y_SHIFT verschoben,
// damit es mit Marcs "Skirt" (Bandmitte y=-55) deckungsgleich liegt.
// Druckorientierung je Haelfte: Nahtflaeche (Trennebene) aufs Bett.

const WALL_T = 5.0;        // Wandstaerke
const DAM_H = 100.0;       // Hoehe des vorderen Damms (lokal z); darueber bleibt die Front als Einfuellfenster offen
const SIDE_ANGLE = 50.0;   // Seitenwand gegen die Bandebene (Grad)
const BACK_LEAN = 11.0;    // Rueckwand lehnt nach -x (wie Marcs Skirt, 10.9 gemessen)
const BACK_X0 = 41.0;      // Rueckwand-Aussenflaeche bei z=0 (stoesst an Tunnelbruecke x=41)
const FRONT_S = 183.7;     // Frontebene x+z = FRONT_S (45 Grad, wie Skirt)
const THROAT_IN = 51.0;    // Hals innen  (Platten-Innenflaeche 50.4 + 0.6)
const THROAT_OUT = 59.0;   // Hals aussen (Platten-Aussenflaeche 58.4 + 0.6)
const THROAT_H = 10.0;     // Halswand ueber Plattenkrone, ab hier flaren die Seiten
const Z_TOP = 230.0;       // Hilfshoehe ueber dem Apex
const Y_BIG = 320.0;
const Z_IN = -25.0;        // Innenkoerper reicht unter z=0 -> kein Boden
const FLANGE_W = 12.0;     // Nahtflansch-Auskragung
const FLANGE_T = 6.0;      // Nahtflansch je Haelfte
const FLANGE_Z = 160.0;    // Nahtflansch Rueckwand bis z
const FLANGE_HOLES_BACK = [15, 85, 150];
const FOOT_X0 = 47.0; const FOOT_X1 = 124.0;   // Fuesse innen an den Platten (x-Bereich)
const BOSS_X = [55.0, 110.0];                  // senkrechte Bohrungen wie Skirt (Ø6.3)
const BOSS_Y0 = 51.0; const BOSS_Y1 = 67.0; const BOSS_H = 26.0; const BOSS_R = 3.15; const BOSS_W = 12.0;
const LINTEL_X1 = 46.0; const LINTEL_Z = -10.3;   // Tunnelsturz (8.4 ueber Band -18.7)
const Y_SHIFT = -55.0;
const NUT_AF = 5.8; const NUT_D = 2.5;          // M3-Mutterntasche (5.5 AF + 0.3), auf Haelfte B
const REV_A = "SKIRT A R1"; const REV_B = "SKIRT B R1";

function polyPts(pts is array) returns array
{
    var v = [];
    for (var p in pts)
        v = append(v, vector(p[0], p[1]) * millimeter);
    v = append(v, vector(pts[0][0], pts[0][1]) * millimeter);
    return v;
}

// Prisma aus XZ-Polygon, extrudiert von y=y0 nach y=y1 (y1 < y0). Sketch: sx=x, sy=z.
function xzPrism(context is Context, id is Id, pts is array, y0 is number, y1 is number) returns Query
{
    var sk = newSketchOnPlane(context, id + "sk", { "sketchPlane" : plane(vector(0, y0, 0) * millimeter, vector(0, -1, 0), vector(1, 0, 0)) });
    skPolyline(sk, "p", { "points" : polyPts(pts) });
    skSolve(sk);
    opExtrude(context, id + "ex", { "entities" : qSketchRegion(id + "sk", false), "direction" : vector(0, -1, 0), "endBound" : BoundingType.BLIND, "endDepth" : (y0 - y1) * millimeter });
    opDeleteBodies(context, id + "del", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    return qCreatedBy(id + "ex", EntityType.BODY);
}

// Prisma aus YZ-Polygon, extrudiert von x=x0 nach x=x1 (x1 > x0). Sketch: sx=y, sy=z.
function yzPrism(context is Context, id is Id, pts is array, x0 is number, x1 is number) returns Query
{
    var sk = newSketchOnPlane(context, id + "sk", { "sketchPlane" : plane(vector(x0, 0, 0) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
    skPolyline(sk, "p", { "points" : polyPts(pts) });
    skSolve(sk);
    opExtrude(context, id + "ex", { "entities" : qSketchRegion(id + "sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : (x1 - x0) * millimeter });
    opDeleteBodies(context, id + "del", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    return qCreatedBy(id + "ex", EntityType.BODY);
}

function oneBody(context is Context, opId is Id, qs is array, what is string) returns Query
{
    // Boolean-Ergebnisse tragen mal die Identitaet der Operation, mal die eines Tools -> beides pruefen
    const cands = [qBodyType(qCreatedBy(opId, EntityType.BODY), BodyType.SOLID), qBodyType(qUnion(qs), BodyType.SOLID)];
    for (var q in cands)
    {
        if (size(evaluateQuery(context, q)) == 1)
            return q;
    }
    throw regenError(what ~ ": expected 1 body, got " ~ toString(size(evaluateQuery(context, cands[0]))) ~ "/" ~ toString(size(evaluateQuery(context, cands[1]))));
}

function cub(context is Context, id is Id, a is array, b is array)
{
    fCuboid(context, id, {
        "corner1" : vector(min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2])) * millimeter,
        "corner2" : vector(max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])) * millimeter });
    return qCreatedBy(id, EntityType.BODY);
}

function engraveRev(context is Context, id is Id, pln is Plane, pos is Vector, h is number, w is number, txt is string, target is Query)
{
    var sk = newSketchOnPlane(context, id + "revSk", { "sketchPlane" : pln });
    skText(sk, "t0", { "text" : txt, "fontName" : "OpenSans-Regular.ttf", "firstCorner" : pos * millimeter, "secondCorner" : (pos + vector(w, h)) * millimeter });
    skSolve(sk);
    opExtrude(context, id + "revEx", { "entities" : qSketchRegion(id + "revSk", true), "direction" : -pln.normal, "endBound" : BoundingType.BLIND, "endDepth" : 0.4 * millimeter });
    try silent { opBoolean(context, id + "revCut", { "tools" : qCreatedBy(id + "revEx", EntityType.BODY), "targets" : target, "operationType" : BooleanOperationType.SUBTRACTION }); }
    opDeleteBodies(context, id + "revDel", { "entities" : qCreatedBy(id + "revSk", EntityType.BODY) });
}

annotation { "Feature Type Name" : "Skirt Halves" }
export const skirtHalves = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
    }
    {
        const kb = tan(BACK_LEAN * degree);
        const cosB = cos(BACK_LEAN * degree);
        const flare = (90 - SIDE_ANGLE) * degree;
        const k = tan(flare);
        const cosF = cos(flare);

        // ---- Aussenkoerper: Keil (XZ) geschnitten mit Flare-Trapez (YZ)
        const zAp = (FRONT_S - BACK_X0) / (1 - kb);
        const xAp = BACK_X0 - kb * zAp;
        var oXZ = xzPrism(context, id + "oxz", [[BACK_X0, 0], [FRONT_S, 0], [xAp, zAp]], Y_BIG, -Y_BIG);
        const yTop = THROAT_OUT + k * (Z_TOP - THROAT_H);
        var oYZ = yzPrism(context, id + "oyz", [[-THROAT_OUT, 0], [THROAT_OUT, 0], [THROAT_OUT, THROAT_H], [yTop, Z_TOP], [-yTop, Z_TOP], [-THROAT_OUT, THROAT_H]], -100, 320);
        opBoolean(context, id + "outer", { "tools" : qUnion([oXZ, oYZ]), "operationType" : BooleanOperationType.INTERSECTION });
        var body = oneBody(context, id + "outer", [oXZ, oYZ], "outer");

        // ---- Innenkoerper (Wand nach innen versetzt), reicht unter z=0
        const xbIn = BACK_X0 + WALL_T / cosB;
        const sIn = FRONT_S - WALL_T * sqrt(2);
        const zApIn = (sIn - xbIn) / (1 - kb);
        const xApIn = xbIn - kb * zApIn;
        var iXZ = xzPrism(context, id + "ixz", [[xbIn - kb * Z_IN, Z_IN], [sIn - Z_IN, Z_IN], [xApIn, zApIn]], Y_BIG, -Y_BIG);
        const yIn0 = THROAT_OUT - WALL_T / cosF;
        const z1 = THROAT_H - (yIn0 - THROAT_IN) / k;
        const yInTop = yIn0 + k * (Z_TOP - THROAT_H);
        const innerYZ = [[-THROAT_IN, Z_IN], [THROAT_IN, Z_IN], [THROAT_IN, z1], [yInTop, Z_TOP], [-yInTop, Z_TOP], [-THROAT_IN, z1]];
        var iYZ = yzPrism(context, id + "iyz", innerYZ, -100, 320);
        opBoolean(context, id + "inner", { "tools" : qUnion([iXZ, iYZ]), "operationType" : BooleanOperationType.INTERSECTION });
        var inner = oneBody(context, id + "inner", [iXZ, iYZ], "inner");
        opBoolean(context, id + "shell", { "tools" : inner, "targets" : body, "operationType" : BooleanOperationType.SUBTRACTION });

        // ---- Einfuellfenster: Front oberhalb des Damms innerhalb der Innenkontur weg
        var wXZ = xzPrism(context, id + "wxz", [[sIn - DAM_H, DAM_H], [600, DAM_H], [600, 600], [sIn - 600, 600]], Y_BIG, -Y_BIG);
        var wYZ = yzPrism(context, id + "wyz", innerYZ, -100, 320);
        opBoolean(context, id + "win", { "tools" : qUnion([wXZ, wYZ]), "operationType" : BooleanOperationType.INTERSECTION });
        var win = oneBody(context, id + "win", [wXZ, wYZ], "window");
        opBoolean(context, id + "wincut", { "tools" : win, "targets" : body, "operationType" : BooleanOperationType.SUBTRACTION });

        // ---- Anbauten: Sturz, Fuesse, Bosse, Nahtflansche
        var adds = [body];
        adds = append(adds, cub(context, id + "lintel", [BACK_X0, -THROAT_IN, LINTEL_Z], [LINTEL_X1, THROAT_IN, 0.5]));
        for (var s in [1, -1])
        {
            const nm = s > 0 ? "P" : "N";
            // Fuss: haengt innen an der Platte, oben 45-Grad-Schraege damit nichts liegen bleibt
            const foot = [[42.5, -13], [50.1, -13], [50.1, 0], [53, 0], [53, 5], [42.5, -5.5]];
            var fp = [];
            for (var p in foot)
                fp = append(fp, [s * p[0], p[1]]);
            adds = append(adds, yzPrism(context, id + ("foot" ~ nm), fp, FOOT_X0, FOOT_X1));
            for (var i = 0; i < size(BOSS_X); i += 1)
                adds = append(adds, cub(context, id + ("boss" ~ nm ~ toString(i)), [BOSS_X[i] - BOSS_W / 2, s * BOSS_Y0, 0], [BOSS_X[i] + BOSS_W / 2, s * BOSS_Y1, BOSS_H]));
        }
        adds = append(adds, xzPrism(context, id + "flB", [[BACK_X0 - FLANGE_W, 0], [BACK_X0 + 3, 0], [BACK_X0 + 3 - kb * FLANGE_Z, FLANGE_Z], [BACK_X0 - FLANGE_W - kb * FLANGE_Z, FLANGE_Z]], FLANGE_T, -FLANGE_T));
        adds = append(adds, xzPrism(context, id + "flF", [[FRONT_S - 3, 0], [FRONT_S + FLANGE_W, 0], [FRONT_S + FLANGE_W - DAM_H, DAM_H], [FRONT_S - 3 - DAM_H, DAM_H]], FLANGE_T, -FLANGE_T));
        opBoolean(context, id + "union", { "tools" : qUnion(adds), "operationType" : BooleanOperationType.UNION });
        body = oneBody(context, id + "union", adds, "union");

        // ---- Bohrungen: Naht M3 (Ø3.4, Achse y) + Bosse Ø6.3 (Achse z)
        var cyls = [];
        for (var z in FLANGE_HOLES_BACK)
        {
            const cid = id + ("hb" ~ toString(z));
            const x = BACK_X0 - FLANGE_W / 2 - kb * z;
            fCylinder(context, cid, { "topCenter" : vector(x, 25, z) * millimeter, "bottomCenter" : vector(x, -25, z) * millimeter, "radius" : 1.7 * millimeter });
            cyls = append(cyls, qCreatedBy(cid, EntityType.BODY));
        }
        for (var z in [15, DAM_H - 12])
        {
            const cid = id + ("hf" ~ toString(z));
            const x = FRONT_S + FLANGE_W / 2 - z;
            fCylinder(context, cid, { "topCenter" : vector(x, 25, z) * millimeter, "bottomCenter" : vector(x, -25, z) * millimeter, "radius" : 1.7 * millimeter });
            cyls = append(cyls, qCreatedBy(cid, EntityType.BODY));
        }
        for (var s in [1, -1])
        {
            for (var i = 0; i < size(BOSS_X); i += 1)
            {
                const cid = id + ("hz" ~ (s > 0 ? "P" : "N") ~ toString(i));
                const yc = s * (THROAT_IN + THROAT_OUT) / 2;
                fCylinder(context, cid, { "topCenter" : vector(BOSS_X[i], yc, 40) * millimeter, "bottomCenter" : vector(BOSS_X[i], yc, -20) * millimeter, "radius" : BOSS_R * millimeter });
                cyls = append(cyls, qCreatedBy(cid, EntityType.BODY));
            }
        }
        opBoolean(context, id + "holes", { "tools" : qUnion(cyls), "targets" : body, "operationType" : BooleanOperationType.SUBTRACTION });

        // ---- M3-Mutterntaschen auf der Aussenflaeche des Flansches von Haelfte B (y = -FLANGE_T)
        var hexCenters = [];
        for (var z in FLANGE_HOLES_BACK)
            hexCenters = append(hexCenters, [BACK_X0 - FLANGE_W / 2 - kb * z, z]);
        for (var z in [15, DAM_H - 12])
            hexCenters = append(hexCenters, [FRONT_S + FLANGE_W / 2 - z, z]);
        var hs = newSketchOnPlane(context, id + "hexSk", { "sketchPlane" : plane(vector(0, -FLANGE_T, 0) * millimeter, vector(0, -1, 0), vector(1, 0, 0)) });
        const nutR = NUT_AF / sqrt(3);
        var n = 0;
        for (var hc in hexCenters)
        {
            var pts = [];
            for (var i = 0; i < 6; i += 1)
            {
                const a = (30 + 60 * i) * degree;
                pts = append(pts, vector(hc[0] + nutR * cos(a), hc[1] + nutR * sin(a)) * millimeter);
            }
            pts = append(pts, pts[0]);
            skPolyline(hs, "h" ~ toString(n), { "points" : pts });
            n += 1;
        }
        skSolve(hs);
        opExtrude(context, id + "hexEx", { "entities" : qSketchRegion(id + "hexSk", false), "direction" : vector(0, 1, 0), "endBound" : BoundingType.BLIND, "endDepth" : NUT_D * millimeter });
        opBoolean(context, id + "hexCut", { "tools" : qCreatedBy(id + "hexEx", EntityType.BODY), "targets" : body, "operationType" : BooleanOperationType.SUBTRACTION });
        opDeleteBodies(context, id + "hexDel", { "entities" : qCreatedBy(id + "hexSk", EntityType.BODY) });

        // ---- Spiegelhaelften: Kopie, je eine Seite wegschneiden
        opPattern(context, id + "copy", { "entities" : body, "transforms" : [identityTransform()], "instanceNames" : ["c"] });
        var bodyN = qCreatedBy(id + "copy", EntityType.BODY);
        var cutN = cub(context, id + "hN", [-300, -400, -300], [700, 0, 400]);
        var cutP = cub(context, id + "hP", [-300, 0, -300], [700, 400, 400]);
        opBoolean(context, id + "halfP", { "tools" : cutN, "targets" : body, "operationType" : BooleanOperationType.SUBTRACTION });
        opBoolean(context, id + "halfN", { "tools" : cutP, "targets" : bodyN, "operationType" : BooleanOperationType.SUBTRACTION });
        // ---- Revisions-Gravur auf der Damm-Aussenflaeche (45-Grad-Ebene), je Haelfte
        const revPln = plane(vector(FRONT_S - 45, 0, 45) * millimeter, vector(1, 0, 1) / sqrt(2), vector(0, 1, 0));
        engraveRev(context, id + "revA", revPln, vector(12, 0), 2.4, 17.5, REV_A, body);
        engraveRev(context, id + "revB", revPln, vector(-12 - 17.5, 0), 2.4, 17.5, REV_B, bodyN);
        opTransform(context, id + "shift", { "bodies" : qUnion([body, bodyN]), "transform" : transform(vector(0, Y_SHIFT, 0) * millimeter) });
        setProperty(context, { "entities" : body, "propertyType" : PropertyType.NAME, "value" : "Skirt Half A (+y)" });
        setProperty(context, { "entities" : bodyN, "propertyType" : PropertyType.NAME, "value" : "Skirt Half B (-y)" });
    });
