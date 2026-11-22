FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");

// GENERIERT von gen_feeder.py. Step-Feeder mit NEMA17-Kurbeltrieb, Hub 10 mm, 3 Stufen.
annotation { "Feature Type Name" : "Step Feeder" }
export const stepFeeder = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Crank angle" }
        isAngle(definition.angle, ANGLE_360_BOUNDS);
    }
    {
        var th = definition.angle;
        var px = 6.8 + 5.0 * sin(th);
        var pz = 20.0 - 5.0 * cos(th);
        var s = pz + sqrt(20.0^2 - (5.0 * sin(th))^2) - 35.0;   // Schlittenhub in mm
        var zp = 35.0 + s;
        var mm = millimeter;
        fCuboid(context, id + "floor", { "corner1" : vector(-24.000000, -16.000000, -3.000000) * millimeter, "corner2" : vector(14.000000, 74.000000, 0.000000) * millimeter });
        fCuboid(context, id + "bayFloor", { "corner1" : vector(-24.000000, 74.000000, -3.000000) * millimeter, "corner2" : vector(30.000000, 104.000000, 0.000000) * millimeter });
        fCuboid(context, id + "farWall", { "corner1" : vector(-24.000000, -16.000000, -3.000000) * millimeter, "corner2" : vector(-20.000000, 104.000000, 50.000000) * millimeter });
        fCuboid(context, id + "nearWall", { "corner1" : vector(0.000000, -16.000000, -3.000000) * millimeter, "corner2" : vector(14.000000, 74.000000, 50.000000) * millimeter });
        fCuboid(context, id + "frontWall", { "corner1" : vector(-24.000000, 70.000000, -3.000000) * millimeter, "corner2" : vector(14.000000, 74.000000, 50.000000) * millimeter });
        fCuboid(context, id + "mountPlate", { "corner1" : vector(-24.000000, 100.000000, -3.000000) * millimeter, "corner2" : vector(30.000000, 104.000000, 50.000000) * millimeter });
        var step1Sk = newSketchOnPlane(context, id + "step1Sk", { "sketchPlane" : plane(vector(-20.500000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(step1Sk, "p", { "points" : [vector(28.000000, 0.000000) * millimeter, vector(36.000000, 0.000000) * millimeter, vector(36.000000, 15.059470) * millimeter, vector(28.000000, 13.935143) * millimeter, vector(28.000000, 0.000000) * millimeter] });
        skSolve(step1Sk);
        opExtrude(context, id + "step1", { "entities" : qSketchRegion(id + "step1Sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 21.0000 * millimeter });
        var step2Sk = newSketchOnPlane(context, id + "step2Sk", { "sketchPlane" : plane(vector(-20.500000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(step2Sk, "p", { "points" : [vector(14.000000, 0.000000) * millimeter, vector(22.000000, 0.000000) * millimeter, vector(22.000000, 23.091898) * millimeter, vector(14.000000, 21.967572) * millimeter, vector(14.000000, 0.000000) * millimeter] });
        skSolve(step2Sk);
        opExtrude(context, id + "step2", { "entities" : qSketchRegion(id + "step2Sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 21.0000 * millimeter });
        var step3Sk = newSketchOnPlane(context, id + "step3Sk", { "sketchPlane" : plane(vector(-20.500000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(step3Sk, "p", { "points" : [vector(0.000000, 0.000000) * millimeter, vector(8.000000, 0.000000) * millimeter, vector(8.000000, 31.124327) * millimeter, vector(0.000000, 30.000000) * millimeter, vector(0.000000, 0.000000) * millimeter] });
        skSolve(step3Sk);
        opExtrude(context, id + "step3", { "entities" : qSketchRegion(id + "step3Sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 21.0000 * millimeter });
        var hopperSk = newSketchOnPlane(context, id + "hopperSk", { "sketchPlane" : plane(vector(-20.500000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(hopperSk, "p", { "points" : [vector(42.000000, 0.000000) * millimeter, vector(70.500000, 0.000000) * millimeter, vector(70.500000, 16.275867) * millimeter, vector(42.000000, 5.902715) * millimeter, vector(42.000000, 0.000000) * millimeter] });
        skSolve(hopperSk);
        opExtrude(context, id + "hopper", { "entities" : qSketchRegion(id + "hopperSk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 21.0000 * millimeter });
        var exitRampSk = newSketchOnPlane(context, id + "exitRampSk", { "sketchPlane" : plane(vector(-20.500000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(exitRampSk, "p", { "points" : [vector(-16.000000, 0.000000) * millimeter, vector(0.500000, 0.000000) * millimeter, vector(0.500000, 30.000000) * millimeter, vector(-16.000000, 22.000000) * millimeter, vector(-16.000000, 0.000000) * millimeter] });
        skSolve(exitRampSk);
        opExtrude(context, id + "exitRamp", { "entities" : qSketchRegion(id + "exitRampSk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 21.0000 * millimeter });
        opBoolean(context, id + "frameU", { "tools" : qUnion([qCreatedBy(id + "floor", EntityType.BODY), qCreatedBy(id + "bayFloor", EntityType.BODY), qCreatedBy(id + "farWall", EntityType.BODY), qCreatedBy(id + "nearWall", EntityType.BODY), qCreatedBy(id + "frontWall", EntityType.BODY), qCreatedBy(id + "mountPlate", EntityType.BODY), qCreatedBy(id + "step1", EntityType.BODY), qCreatedBy(id + "step2", EntityType.BODY), qCreatedBy(id + "step3", EntityType.BODY), qCreatedBy(id + "hopper", EntityType.BODY), qCreatedBy(id + "exitRamp", EntityType.BODY)]), "operationType" : BooleanOperationType.UNION });
        fCuboid(context, id + "pocket", { "corner1" : vector(3.600000, 5.600000, 0.000000) * millimeter, "corner2" : vector(10.000000, 74.500000, 50.500000) * millimeter });
        fCuboid(context, id + "slot1", { "corner1" : vector(-0.600000, 36.000000, 0.000000) * millimeter, "corner2" : vector(3.700000, 42.000000, 50.500000) * millimeter });
        fCuboid(context, id + "slot2", { "corner1" : vector(-0.600000, 22.000000, 0.000000) * millimeter, "corner2" : vector(3.700000, 28.000000, 50.500000) * millimeter });
        fCuboid(context, id + "slot3", { "corner1" : vector(-0.600000, 8.000000, 0.000000) * millimeter, "corner2" : vector(3.700000, 14.000000, 50.500000) * millimeter });
        fCylinder(context, id + "pilotBore", { "topCenter" : vector(6.800000, 99.000000, 20.000000) * millimeter, "bottomCenter" : vector(6.800000, 105.000000, 20.000000) * millimeter, "radius" : 11.2000 * millimeter });
        fCylinder(context, id + "m3_0", { "topCenter" : vector(-8.700000, 99.000000, 4.500000) * millimeter, "bottomCenter" : vector(-8.700000, 105.000000, 4.500000) * millimeter, "radius" : 1.7000 * millimeter });
        fCylinder(context, id + "m3_1", { "topCenter" : vector(22.300000, 99.000000, 4.500000) * millimeter, "bottomCenter" : vector(22.300000, 105.000000, 4.500000) * millimeter, "radius" : 1.7000 * millimeter });
        fCylinder(context, id + "m3_2", { "topCenter" : vector(-8.700000, 99.000000, 35.500000) * millimeter, "bottomCenter" : vector(-8.700000, 105.000000, 35.500000) * millimeter, "radius" : 1.7000 * millimeter });
        fCylinder(context, id + "m3_3", { "topCenter" : vector(22.300000, 99.000000, 35.500000) * millimeter, "bottomCenter" : vector(22.300000, 105.000000, 35.500000) * millimeter, "radius" : 1.7000 * millimeter });
        opBoolean(context, id + "frameCut", { "tools" : qUnion([qCreatedBy(id + "pocket", EntityType.BODY), qCreatedBy(id + "slot1", EntityType.BODY), qCreatedBy(id + "slot2", EntityType.BODY), qCreatedBy(id + "slot3", EntityType.BODY), qCreatedBy(id + "pilotBore", EntityType.BODY), qCreatedBy(id + "m3_0", EntityType.BODY), qCreatedBy(id + "m3_1", EntityType.BODY), qCreatedBy(id + "m3_2", EntityType.BODY), qCreatedBy(id + "m3_3", EntityType.BODY)]), "targets" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(-22.000000, 30.000000, 10.000000) * millimeter), "operationType" : BooleanOperationType.SUBTRACTION });
        setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(-22.000000, 30.000000, 10.000000) * millimeter), "propertyType" : PropertyType.NAME, "value" : "Frame" });
        try silent { setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(-22.000000, 30.000000, 10.000000) * millimeter), "propertyType" : PropertyType.APPEARANCE, "value" : color(0.75, 0.75, 0.78) }); }
        var sz = vector(0, 0, 1) * s * mm;
        fCuboid(context, id + "plate", { "corner1" : vector(3.800000, 6.000000, 1.000000) * millimeter, "corner2" : vector(9.800000, 74.000000, 40.000000) * millimeter });
        var blade1Sk = newSketchOnPlane(context, id + "blade1Sk", { "sketchPlane" : plane(vector(-19.600000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(blade1Sk, "p", { "points" : [vector(36.300000, 1.000000) * millimeter, vector(41.700000, 1.000000) * millimeter, vector(41.700000, 5.860553) * millimeter, vector(36.300000, 5.101632) * millimeter, vector(36.300000, 1.000000) * millimeter] });
        skSolve(blade1Sk);
        opExtrude(context, id + "blade1", { "entities" : qSketchRegion(id + "blade1Sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 29.4000 * millimeter });
        var blade2Sk = newSketchOnPlane(context, id + "blade2Sk", { "sketchPlane" : plane(vector(-19.600000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(blade2Sk, "p", { "points" : [vector(22.300000, 1.000000) * millimeter, vector(27.700000, 1.000000) * millimeter, vector(27.700000, 13.892981) * millimeter, vector(22.300000, 13.134061) * millimeter, vector(22.300000, 1.000000) * millimeter] });
        skSolve(blade2Sk);
        opExtrude(context, id + "blade2", { "entities" : qSketchRegion(id + "blade2Sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 29.4000 * millimeter });
        var blade3Sk = newSketchOnPlane(context, id + "blade3Sk", { "sketchPlane" : plane(vector(-19.600000, 0.000000, 0.000000) * millimeter, vector(1, 0, 0), vector(0, 1, 0)) });
        skPolyline(blade3Sk, "p", { "points" : [vector(8.300000, 1.000000) * millimeter, vector(13.700000, 1.000000) * millimeter, vector(13.700000, 21.925409) * millimeter, vector(8.300000, 21.166489) * millimeter, vector(8.300000, 1.000000) * millimeter] });
        skSolve(blade3Sk);
        opExtrude(context, id + "blade3", { "entities" : qSketchRegion(id + "blade3Sk", false), "direction" : vector(1, 0, 0), "endBound" : BoundingType.BLIND, "endDepth" : 29.4000 * millimeter });
        fCylinder(context, id + "carPin", { "topCenter" : vector(6.800000, 73.000000, 35.000000) * millimeter, "bottomCenter" : vector(6.800000, 78.800000, 35.000000) * millimeter, "radius" : 2.0000 * millimeter });
        opBoolean(context, id + "carU", { "tools" : qUnion([qCreatedBy(id + "plate", EntityType.BODY), qCreatedBy(id + "blade1", EntityType.BODY), qCreatedBy(id + "blade2", EntityType.BODY), qCreatedBy(id + "blade3", EntityType.BODY), qCreatedBy(id + "carPin", EntityType.BODY)]), "operationType" : BooleanOperationType.UNION });
        opTransform(context, id + "carMove", { "bodies" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 40.000000, 30.000000) * millimeter), "transform" : transform(sz) });
        setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), (vector(6.800000, 40.000000, 30.000000) * millimeter + sz)), "propertyType" : PropertyType.NAME, "value" : "Carriage" });
        try silent { setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), (vector(6.800000, 40.000000, 30.000000) * millimeter + sz)), "propertyType" : PropertyType.APPEARANCE, "value" : color(0.9, 0.55, 0.15) }); }
        fCylinder(context, id + "disc", { "topCenter" : vector(6.800000, 79.000000, 20.000000) * millimeter, "bottomCenter" : vector(6.800000, 85.000000, 20.000000) * millimeter, "radius" : 9.0000 * millimeter });
        fCylinder(context, id + "hub", { "topCenter" : vector(6.800000, 85.000000, 20.000000) * millimeter, "bottomCenter" : vector(6.800000, 93.000000, 20.000000) * millimeter, "radius" : 6.0000 * millimeter });
        fCylinder(context, id + "crankPin", { "topCenter" : vector(6.800000, 74.600000, 15.000000) * millimeter, "bottomCenter" : vector(6.800000, 79.500000, 15.000000) * millimeter, "radius" : 2.0000 * millimeter });
        opBoolean(context, id + "crankU", { "tools" : qUnion([qCreatedBy(id + "disc", EntityType.BODY), qCreatedBy(id + "hub", EntityType.BODY), qCreatedBy(id + "crankPin", EntityType.BODY)]), "operationType" : BooleanOperationType.UNION });
        fCylinder(context, id + "crankBore", { "topCenter" : vector(6.800000, 78.500000, 20.000000) * millimeter, "bottomCenter" : vector(6.800000, 94.000000, 20.000000) * millimeter, "radius" : 2.6000 * millimeter });
        fCuboid(context, id + "boreFlat", { "corner1" : vector(8.900000, 78.000000, 16.000000) * millimeter, "corner2" : vector(10.800000, 95.500000, 24.000000) * millimeter });
        opBoolean(context, id + "boreD", { "tools" : qUnion([qCreatedBy(id + "boreFlat", EntityType.BODY)]), "targets" : qCreatedBy(id + "crankBore", EntityType.BODY), "operationType" : BooleanOperationType.SUBTRACTION });
        fCylinder(context, id + "grub", { "topCenter" : vector(6.800000, 89.000000, 20.000000) * millimeter, "bottomCenter" : vector(14.800000, 89.000000, 20.000000) * millimeter, "radius" : 1.4000 * millimeter });
        opBoolean(context, id + "crankCut", { "tools" : qUnion([qCreatedBy(id + "crankBore", EntityType.BODY), qCreatedBy(id + "grub", EntityType.BODY)]), "targets" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 82.000000, 27.000000) * millimeter), "operationType" : BooleanOperationType.SUBTRACTION });
        opTransform(context, id + "crankRot", { "bodies" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 82.000000, 27.000000) * millimeter), "transform" : rotationAround(line(vector(6.800000, 80.000000, 20.000000) * millimeter, vector(0, -1, 0)), th) });
        setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 82.000000, 27.000000) * millimeter), "propertyType" : PropertyType.NAME, "value" : "Crank" });
        try silent { setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 82.000000, 27.000000) * millimeter), "propertyType" : PropertyType.APPEARANCE, "value" : color(0.2, 0.45, 0.85) }); }
        var dx = (6.8 - px); var dz = (zp - pz); var ln = sqrt(dx^2 + dz^2);
        var ux = dx / ln; var uz = dz / ln;   // Einheitsvektor Zapfen -> Bolzen
        var nx = -uz * 3; var nz = ux * 3;    // halbe Stangenbreite 3 mm senkrecht dazu
        var rodSk = newSketchOnPlane(context, id + "rodSk", { "sketchPlane" : plane(vector(0.000000, 78.500000, 0.000000) * millimeter, vector(0, -1, 0), vector(1, 0, 0)) });
        skPolyline(rodSk, "p", { "points" : [vector(px + nx, pz + nz) * mm, vector(px - nx, pz - nz) * mm, vector(6.8 - nx, zp - nz) * mm, vector(6.8 + nx, zp + nz) * mm, vector(px + nx, pz + nz) * mm] });
        skSolve(rodSk);
        opExtrude(context, id + "rodBar", { "entities" : qSketchRegion(id + "rodSk", false), "direction" : vector(0, -1, 0), "endBound" : BoundingType.BLIND, "endDepth" : 4 * mm });
        fCylinder(context, id + "eyeA", { "topCenter" : vector(px, 78.5, pz) * mm, "bottomCenter" : vector(px, 74.5, pz) * mm, "radius" : 4.5 * mm });
        fCylinder(context, id + "eyeB", { "topCenter" : vector(6.8, 78.5, zp) * mm, "bottomCenter" : vector(6.8, 74.5, zp) * mm, "radius" : 4.5 * mm });
        opBoolean(context, id + "rodU", { "tools" : qUnion([qCreatedBy(id + "rodBar", EntityType.BODY), qCreatedBy(id + "eyeA", EntityType.BODY), qCreatedBy(id + "eyeB", EntityType.BODY)]), "operationType" : BooleanOperationType.UNION });
        fCylinder(context, id + "holeA", { "topCenter" : vector(px, 79, pz) * mm, "bottomCenter" : vector(px, 74, pz) * mm, "radius" : 2.15 * mm });
        fCylinder(context, id + "holeB", { "topCenter" : vector(6.8, 79, zp) * mm, "bottomCenter" : vector(6.8, 74, zp) * mm, "radius" : 2.15 * mm });
        opBoolean(context, id + "rodCut", { "tools" : qUnion([qCreatedBy(id + "holeA", EntityType.BODY), qCreatedBy(id + "holeB", EntityType.BODY)]), "targets" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector((px + 6.8) / 2, 76.5, (pz + zp) / 2) * mm), "operationType" : BooleanOperationType.SUBTRACTION });
        setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector((px + 6.8) / 2, 76.5, (pz + zp) / 2) * mm), "propertyType" : PropertyType.NAME, "value" : "Rod" });
        try silent { setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector((px + 6.8) / 2, 76.5, (pz + zp) / 2) * mm), "propertyType" : PropertyType.APPEARANCE, "value" : color(0.3, 0.7, 0.3) }); }
        fCuboid(context, id + "motorBody", { "corner1" : vector(-14.350000, 104.000000, -1.150000) * millimeter, "corner2" : vector(27.950000, 144.000000, 41.150000) * millimeter });
        fCylinder(context, id + "pilot", { "topCenter" : vector(6.800000, 102.000000, 20.000000) * millimeter, "bottomCenter" : vector(6.800000, 104.500000, 20.000000) * millimeter, "radius" : 11.0000 * millimeter });
        fCylinder(context, id + "shaft", { "topCenter" : vector(6.800000, 80.000000, 20.000000) * millimeter, "bottomCenter" : vector(6.800000, 103.000000, 20.000000) * millimeter, "radius" : 2.5000 * millimeter });
        opBoolean(context, id + "motorU", { "tools" : qUnion([qCreatedBy(id + "motorBody", EntityType.BODY), qCreatedBy(id + "pilot", EntityType.BODY), qCreatedBy(id + "shaft", EntityType.BODY)]), "operationType" : BooleanOperationType.UNION });
        fCuboid(context, id + "dFlat", { "corner1" : vector(8.800000, 79.000000, 16.000000) * millimeter, "corner2" : vector(10.800000, 95.000000, 24.000000) * millimeter });
        opTransform(context, id + "flatRot", { "bodies" : qCreatedBy(id + "dFlat", EntityType.BODY), "transform" : rotationAround(line(vector(6.800000, 90.000000, 20.000000) * millimeter, vector(0, -1, 0)), th) });
        opBoolean(context, id + "motorCut", { "tools" : qUnion([qCreatedBy(id + "dFlat", EntityType.BODY)]), "targets" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 124.000000, 20.000000) * millimeter), "operationType" : BooleanOperationType.SUBTRACTION });
        setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 124.000000, 20.000000) * millimeter), "propertyType" : PropertyType.NAME, "value" : "Motor NEMA17" });
        try silent { setProperty(context, { "entities" : qContainsPoint(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), vector(6.800000, 124.000000, 20.000000) * millimeter), "propertyType" : PropertyType.APPEARANCE, "value" : color(0.25, 0.25, 0.27) }); }
        opDeleteBodies(context, id + "delSk", { "entities" : qUnion([qCreatedBy(id + "step1Sk", EntityType.BODY), qCreatedBy(id + "step2Sk", EntityType.BODY), qCreatedBy(id + "step3Sk", EntityType.BODY), qCreatedBy(id + "hopperSk", EntityType.BODY), qCreatedBy(id + "exitRampSk", EntityType.BODY), qCreatedBy(id + "blade1Sk", EntityType.BODY), qCreatedBy(id + "blade2Sk", EntityType.BODY), qCreatedBy(id + "blade3Sk", EntityType.BODY), qCreatedBy(id + "rodSk", EntityType.BODY)]) });
    });
