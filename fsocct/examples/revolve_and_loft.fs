FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

annotation { "Feature Type Name" : "Local revolve and loft" }
export const turnedParts = defineFeature(function(context is Context, id is Id, definition is map)
    precondition {}
    {
        var profile = newSketchOnPlane(context, id + "section", {
            "sketchPlane" : plane(vector(0, 0, 0) * millimeter, vector(0, -1, 0), vector(1, 0, 0))
        });
        skRectangle(profile, "section", {
            "firstCorner" : vector(12, 0) * millimeter,
            "secondCorner" : vector(18, 24) * millimeter
        });
        skSolve(profile);
        opRevolve(context, id + "sleeve", {
            "entities" : qSketchRegion(id + "section"),
            "axis" : line(vector(0, 0, 0) * millimeter, vector(0, 0, 1)),
            "angleForward" : 360 * degree
        });

        var profiles = [];
        for (var i = 0; i < 2; i += 1)
        {
            const profileId = id + ("loftProfile" ~ i);
            var sk = newSketchOnPlane(context, profileId, {
                "sketchPlane" : plane(vector(50, 0, i * 20) * millimeter, vector(0, 0, 1), vector(1, 0, 0))
            });
            skCircle(sk, "circle", {
                "center" : vector(0, 0) * millimeter,
                "radius" : (i == 0 ? 12 : 8) * millimeter
            });
            skSolve(sk);
            profiles = append(profiles, qSketchRegion(profileId));
        }
        opLoft(context, id + "taper", { "profileSubqueries" : profiles, "bodyType" : BodyType.SOLID });
    });
