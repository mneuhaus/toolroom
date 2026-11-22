FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");

// NEW Part Studio only. Does not reference or alter the R19 source studio.
// Millimetres, nominal plywood 3.2, no kerf compensation.
// Original R19 outer hopper hole axes retained; legacy central hatch holes retired.
annotation { "Feature Type Name" : "Hopper rear wall R29" }
export const hopperRearWallR29 = defineFeature(function(context is Context, id is Id, definition is map)
    precondition {}
    {
        var pl = plane(vector(77.1263837814323,-498.4724643754777,-184.5128995194368) * millimeter, vector(0,-0.9614110033020126,-0.2751161258992604), vector(1,0,0));
        var s = newSketchOnPlane(context, id + "profile", {"sketchPlane" : pl});
        skLineSegment(s, "edge0", {"start" : vector(-372.7816519320052,321.9360902427784) * millimeter, "end" : vector(372.7816519320052,321.9360902427784) * millimeter});
        skLineSegment(s, "edge1", {"start" : vector(372.7816519320052,321.9360902427784) * millimeter, "end" : vector(93.73340366941191,42.75391346118118) * millimeter});
        skArc(s, "edge2", {"start" : vector(93.73340366941191,42.75391346118118) * millimeter, "mid" : vector(89.49046497478483,40.9955361911903) * millimeter, "end" : vector(85.2471045390988,42.75289546090119) * millimeter});
        skLineSegment(s, "edge3", {"start" : vector(85.2471045390988,42.75289546090119) * millimeter, "end" : vector(66.34314575050762,61.65685424949238) * millimeter});
        skArc(s, "edge4", {"start" : vector(66.34314575050762,61.65685424949238) * millimeter, "mid" : vector(64.60896373990971,64.25224104006405) * millimeter, "end" : vector(64,67.31370849898477) * millimeter});
        skLineSegment(s, "edge5", {"start" : vector(64,67.31370849898477) * millimeter, "end" : vector(64,125.8366351713157) * millimeter});
        skArc(s, "edge6", {"start" : vector(64,125.8366351713157) * millimeter, "mid" : vector(58.18597502568824,133.532186690672) * millimeter, "end" : vector(49.19462170323317,130.0422060288682) * millimeter});
        skLineSegment(s, "edge7", {"start" : vector(49.19462170323317,130.0422060288682) * millimeter, "end" : vector(43.17243597098096,120.2972145712237) * millimeter});
        skArc(s, "edge8", {"start" : vector(43.17243597098096,120.2972145712237) * millimeter, "mid" : vector(41.7176762726669,118.9063527857621) * millimeter, "end" : vector(39.76974682259755,118.4) * millimeter});
        skLineSegment(s, "edge9", {"start" : vector(39.76974682259755,118.4) * millimeter, "end" : vector(-39.76974682259755,118.4) * millimeter});
        skArc(s, "edge10", {"start" : vector(-39.76974682259755,118.4) * millimeter, "mid" : vector(-41.71767627266689,118.9063527857621) * millimeter, "end" : vector(-43.17243597098096,120.2972145712237) * millimeter});
        skLineSegment(s, "edge11", {"start" : vector(-43.17243597098096,120.2972145712237) * millimeter, "end" : vector(-49.19462170323317,130.0422060288682) * millimeter});
        skArc(s, "edge12", {"start" : vector(-49.19462170323317,130.0422060288682) * millimeter, "mid" : vector(-58.18597502568824,133.532186690672) * millimeter, "end" : vector(-64,125.8366351713157) * millimeter});
        skLineSegment(s, "edge13", {"start" : vector(-64,125.8366351713157) * millimeter, "end" : vector(-64,67.31370849898477) * millimeter});
        skArc(s, "edge14", {"start" : vector(-64,67.31370849898477) * millimeter, "mid" : vector(-64.60896373990971,64.25224104006405) * millimeter, "end" : vector(-66.34314575050762,61.65685424949238) * millimeter});
        skLineSegment(s, "edge15", {"start" : vector(-66.34314575050762,61.65685424949238) * millimeter, "end" : vector(-85.2471045390988,42.75289546090119) * millimeter});
        skArc(s, "edge16", {"start" : vector(-85.2471045390988,42.75289546090119) * millimeter, "mid" : vector(-89.49046497478483,40.9955361911903) * millimeter, "end" : vector(-93.73340366941191,42.75391346118118) * millimeter});
        skLineSegment(s, "edge17", {"start" : vector(-93.73340366941191,42.75391346118118) * millimeter, "end" : vector(-372.7816519320052,321.9360902427784) * millimeter});
        skCircle(s, "mount0", {"center" : vector(-325.8519240627237,294.7875802655336) * millimeter, "radius" : 1.7 * millimeter});
        skCircle(s, "mount1", {"center" : vector(-151.7218432848038,120.5739259615895) * millimeter, "radius" : 1.7 * millimeter});
        skCircle(s, "mount2", {"center" : vector(151.7218437219391,120.5739259615895) * millimeter, "radius" : 1.7 * millimeter});
        skCircle(s, "mount3", {"center" : vector(325.8519244998591,294.7875802655336) * millimeter, "radius" : 1.7 * millimeter});
        skSolve(s);
        opExtrude(context, id + "panel", {"entities" : qSketchRegion(id + "profile", true),
            "direction" : pl.normal, "endBound" : BoundingType.BLIND, "endDepth" : 3.2 * millimeter});
        opDeleteBodies(context, id + "removeSketch", {"entities" : qCreatedBy(id + "profile", EntityType.BODY)});
        var panel = qCreatedBy(id + "panel", EntityType.BODY);
        var clearance0 = newSketchOnPlane(context, id + "intake0", {"sketchPlane" : plane(vector(77.1263837814323,-497.5110533721757,-184.2377833935376) * millimeter, vector(0,-0.9614110033020126,-0.2751161258992604), vector(1,0,0))});
        skArc(clearance0, "edge0", {"start" : vector(58.10100231303005,122.0751632593239) * millimeter, "mid" : vector(88.91119166186783,138.9112874188642) * millimeter, "end" : vector(117.218966846569,159.6812828093094) * millimeter});
        skArc(clearance0, "edge1", {"start" : vector(117.218966846569,159.6812828093094) * millimeter, "mid" : vector(117.8259969211553,166.7262465770337) * millimeter, "end" : vector(110.781033153431,167.33327665162) * millimeter});
        skArc(clearance0, "edge2", {"start" : vector(110.781033153431,167.33327665162) * millimeter, "mid" : vector(83.54389999538265,147.3488332804806) * millimeter, "end" : vector(53.89899768696991,131.1494762979274) * millimeter});
        skArc(clearance0, "edge3", {"start" : vector(53.89899768696992,131.1494762979274) * millimeter, "mid" : vector(51.46284348069824,124.5113174655956) * millimeter, "end" : vector(58.10100231303005,122.0751632593239) * millimeter});
        skSolve(clearance0);
        opExtrude(context, id + "intakeTool0", {"entities" : qSketchRegion(id + "intake0", true), "direction" : pl.normal, "endBound" : BoundingType.BLIND, "endDepth" : 5.2 * millimeter});
        opBoolean(context, id + "intakeCut0", {"tools" : qCreatedBy(id + "intakeTool0", EntityType.BODY), "targets" : panel, "operationType" : BooleanOperationType.SUBTRACTION});
        opDeleteBodies(context, id + "intakeSketchDelete0", {"entities" : qCreatedBy(id + "intake0", EntityType.BODY)});
        var clearance1 = newSketchOnPlane(context, id + "intake1", {"sketchPlane" : plane(vector(77.1263837814323,-497.5110533721757,-184.2377833935376) * millimeter, vector(0,-0.9614110033020126,-0.2751161258992604), vector(1,0,0))});
        skArc(clearance1, "edge0", {"start" : vector(105.5,161.5) * millimeter, "mid" : vector(106.3786796564404,159.3786796564404) * millimeter, "end" : vector(108.5,158.5) * millimeter});
        skLineSegment(clearance1, "edge1", {"start" : vector(108.5,158.5) * millimeter, "end" : vector(119.5,158.5) * millimeter});
        skArc(clearance1, "edge2", {"start" : vector(119.5,158.5) * millimeter, "mid" : vector(121.6213203435596,159.3786796564404) * millimeter, "end" : vector(122.5,161.5) * millimeter});
        skLineSegment(clearance1, "edge3", {"start" : vector(122.5,161.5) * millimeter, "end" : vector(122.5,165.7) * millimeter});
        skArc(clearance1, "edge4", {"start" : vector(122.5,165.7) * millimeter, "mid" : vector(121.6213203435596,167.8213203435596) * millimeter, "end" : vector(119.5,168.7) * millimeter});
        skLineSegment(clearance1, "edge5", {"start" : vector(119.5,168.7) * millimeter, "end" : vector(108.5,168.7) * millimeter});
        skArc(clearance1, "edge6", {"start" : vector(108.5,168.7) * millimeter, "mid" : vector(106.3786796564404,167.8213203435596) * millimeter, "end" : vector(105.5,165.7) * millimeter});
        skLineSegment(clearance1, "edge7", {"start" : vector(105.5,165.7) * millimeter, "end" : vector(105.5,161.5) * millimeter});
        skSolve(clearance1);
        opExtrude(context, id + "intakeTool1", {"entities" : qSketchRegion(id + "intake1", true), "direction" : pl.normal, "endBound" : BoundingType.BLIND, "endDepth" : 5.2 * millimeter});
        opBoolean(context, id + "intakeCut1", {"tools" : qCreatedBy(id + "intakeTool1", EntityType.BODY), "targets" : panel, "operationType" : BooleanOperationType.SUBTRACTION});
        opDeleteBodies(context, id + "intakeSketchDelete1", {"entities" : qCreatedBy(id + "intake1", EntityType.BODY)});
        var clearance2 = newSketchOnPlane(context, id + "intake2", {"sketchPlane" : plane(vector(77.1263837814323,-497.5110533721757,-184.2377833935376) * millimeter, vector(0,-0.9614110033020126,-0.2751161258992604), vector(1,0,0))});
        skArc(clearance2, "edge0", {"start" : vector(-58.10100231303005,122.0751632593239) * millimeter, "mid" : vector(-88.91119166186783,138.9112874188642) * millimeter, "end" : vector(-117.218966846569,159.6812828093094) * millimeter});
        skArc(clearance2, "edge1", {"start" : vector(-117.218966846569,159.6812828093094) * millimeter, "mid" : vector(-117.8259969211553,166.7262465770337) * millimeter, "end" : vector(-110.781033153431,167.33327665162) * millimeter});
        skArc(clearance2, "edge2", {"start" : vector(-110.781033153431,167.33327665162) * millimeter, "mid" : vector(-83.54389999538265,147.3488332804806) * millimeter, "end" : vector(-53.89899768696991,131.1494762979274) * millimeter});
        skArc(clearance2, "edge3", {"start" : vector(-53.89899768696992,131.1494762979274) * millimeter, "mid" : vector(-51.46284348069824,124.5113174655956) * millimeter, "end" : vector(-58.10100231303005,122.0751632593239) * millimeter});
        skSolve(clearance2);
        opExtrude(context, id + "intakeTool2", {"entities" : qSketchRegion(id + "intake2", true), "direction" : pl.normal, "endBound" : BoundingType.BLIND, "endDepth" : 5.2 * millimeter});
        opBoolean(context, id + "intakeCut2", {"tools" : qCreatedBy(id + "intakeTool2", EntityType.BODY), "targets" : panel, "operationType" : BooleanOperationType.SUBTRACTION});
        opDeleteBodies(context, id + "intakeSketchDelete2", {"entities" : qCreatedBy(id + "intake2", EntityType.BODY)});
        var clearance3 = newSketchOnPlane(context, id + "intake3", {"sketchPlane" : plane(vector(77.1263837814323,-497.5110533721757,-184.2377833935376) * millimeter, vector(0,-0.9614110033020126,-0.2751161258992604), vector(1,0,0))});
        skArc(clearance3, "edge0", {"start" : vector(-105.5,161.5) * millimeter, "mid" : vector(-106.3786796564404,159.3786796564404) * millimeter, "end" : vector(-108.5,158.5) * millimeter});
        skLineSegment(clearance3, "edge1", {"start" : vector(-108.5,158.5) * millimeter, "end" : vector(-119.5,158.5) * millimeter});
        skArc(clearance3, "edge2", {"start" : vector(-119.5,158.5) * millimeter, "mid" : vector(-121.6213203435596,159.3786796564404) * millimeter, "end" : vector(-122.5,161.5) * millimeter});
        skLineSegment(clearance3, "edge3", {"start" : vector(-122.5,161.5) * millimeter, "end" : vector(-122.5,165.7) * millimeter});
        skArc(clearance3, "edge4", {"start" : vector(-122.5,165.7) * millimeter, "mid" : vector(-121.6213203435596,167.8213203435596) * millimeter, "end" : vector(-119.5,168.7) * millimeter});
        skLineSegment(clearance3, "edge5", {"start" : vector(-119.5,168.7) * millimeter, "end" : vector(-108.5,168.7) * millimeter});
        skArc(clearance3, "edge6", {"start" : vector(-108.5,168.7) * millimeter, "mid" : vector(-106.3786796564404,167.8213203435596) * millimeter, "end" : vector(-105.5,165.7) * millimeter});
        skLineSegment(clearance3, "edge7", {"start" : vector(-105.5,165.7) * millimeter, "end" : vector(-105.5,161.5) * millimeter});
        skSolve(clearance3);
        opExtrude(context, id + "intakeTool3", {"entities" : qSketchRegion(id + "intake3", true), "direction" : pl.normal, "endBound" : BoundingType.BLIND, "endDepth" : 5.2 * millimeter});
        opBoolean(context, id + "intakeCut3", {"tools" : qCreatedBy(id + "intakeTool3", EntityType.BODY), "targets" : panel, "operationType" : BooleanOperationType.SUBTRACTION});
        opDeleteBodies(context, id + "intakeSketchDelete3", {"entities" : qCreatedBy(id + "intake3", EntityType.BODY)});
        if (size(evaluateQuery(context, panel)) != 1) throw regenError("R29 rear wall must be one body");
        setProperty(context, {"entities" : panel, "propertyType" : PropertyType.NAME,
            "value" : "HOPPER PANEL B R29 - plywood 3.2 mm"});
        setProperty(context, {"entities" : panel, "propertyType" : PropertyType.APPEARANCE,
            "value" : color(0.66, 0.45, 0.24)});
    });
