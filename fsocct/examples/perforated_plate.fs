FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

function bore(context is Context, id is Id, x, y, thickness, radius)
{
    fCylinder(context, id, {
        "bottomCenter" : vector(x, y, -1 * millimeter),
        "topCenter" : vector(x, y, thickness + 1 * millimeter),
        "radius" : radius
    });
}

annotation { "Feature Type Name" : "Local perforated plate" }
export const perforatedPlate = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Width" }
        isLength(definition.width, POSITIVE_LENGTH_BOUNDS);
        annotation { "Name" : "Height" }
        isLength(definition.height, POSITIVE_LENGTH_BOUNDS);
        annotation { "Name" : "Thickness" }
        isLength(definition.thickness, POSITIVE_LENGTH_BOUNDS);
        isLength(definition.radius, POSITIVE_LENGTH_BOUNDS);
        definition.width > 2 * (definition.margin + definition.radius);
        definition.height > 2 * (definition.margin + definition.radius);
    }
    {
        var sketch = newSketchOnPlane(context, id + "profile", {
            "sketchPlane" : plane(vector(0, 0, 0) * millimeter, vector(0, 0, 1), vector(1, 0, 0))
        });
        skRectangle(sketch, "outline", {
            "firstCorner" : vector(0, 0) * millimeter,
            "secondCorner" : vector(definition.width, definition.height)
        });
        skSolve(sketch);
        opExtrude(context, id + "plate", {
            "entities" : qSketchRegion(id + "profile"),
            "direction" : vector(0, 0, 1),
            "endBound" : BoundingType.BLIND,
            "endDepth" : definition.thickness
        });
        opDeleteBodies(context, id + "removeSketch", {
            "entities" : qCreatedBy(id + "profile", EntityType.BODY)
        });

        var tools = [];
        var points = [
            vector(definition.margin, definition.margin),
            vector(definition.width - definition.margin, definition.margin),
            vector(definition.width - definition.margin, definition.height - definition.margin),
            vector(definition.margin, definition.height - definition.margin)
        ];
        for (var i, point in points)
        {
            const holeId = id + ("hole" ~ i);
            bore(context, holeId, point[0], point[1], definition.thickness, definition.radius);
            tools = append(tools, qCreatedBy(holeId, EntityType.BODY));
        }
        opBoolean(context, id + "drill", {
            "targets" : qCreatedBy(id + "plate", EntityType.BODY),
            "tools" : qUnion(tools),
            "operationType" : BooleanOperationType.SUBTRACTION
        });
        setProperty(context, {
            "entities" : qCreatedBy(id + "plate", EntityType.BODY),
            "propertyType" : PropertyType.NAME,
            "value" : "Perforated plate"
        });
    }, {
        "width" : 80 * millimeter,
        "height" : 50 * millimeter,
        "thickness" : 6 * millimeter,
        "radius" : 4 * millimeter,
        "margin" : 12 * millimeter
    });
