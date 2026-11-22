FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");
// Local import is an fsocct extension. The imported source is used unchanged.
M3::import(path : "../../skills/onshape-cad/lib/m3_hybrid_hole.fs", version : "local");

annotation { "Feature Type Name" : "Canonical M3 cutter compatibility example" }
export const canonicalM3Tool = defineFeature(function(context is Context, id is Id, definition is map)
    precondition {}
    {
        // A cutter solid for software verification, not a designed screw joint.
        var tool = M3::m3HybridTool(context, id + "tool",
            vector(0, 0, 0) * millimeter, vector(0, 0, 1),
            8.4 * millimeter, vector(1, 0, 0), true);
        setProperty(context, { "entities" : tool, "propertyType" : PropertyType.NAME,
            "value" : "Canonical M3 hybrid cutter" });
    });
