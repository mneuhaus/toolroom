function(context is Context, queries)
{
    var nodes = [];
    const registry = getVariable(context, "toolroomPurposeRegistry", {});
    for (var key in keys(registry))
    {
        var node = registry[key];
        const entities = qHasAttribute(node.attribute_name);
        const hits = evaluateQuery(context, entities);
        var witnesses = [];
        for (var entity in hits)
        {
            const measuredBox = evBox3d(context, {"topology" : entity, "tight" : true});
            witnesses = append(witnesses, {
                "topology_id" : transientQueriesToStrings([entity])[0],
                "bounds_mm" : [measuredBox.minCorner / millimeter, measuredBox.maxCorner / millimeter]
            });
        }
        const owners = qUnion([qEntityFilter(entities, EntityType.BODY), qOwnerBody(entities)]);
        var ownerNames = [];
        for (var owner in evaluateQuery(context, owners))
            ownerNames = append(ownerNames, getProperty(context,
                {"entity" : owner, "propertyType" : PropertyType.NAME}));
        node.entity_count = size(hits);
        node.owner_count = size(ownerNames);
        node.owner_names = ownerNames;
        node.owner_ids = transientQueriesToStrings(evaluateQuery(context, owners));
        node.witnesses = witnesses;
        node.binding_scope = "Surviving attributed boundary/body witnesses; not an exact material partition";
        nodes = append(nodes, node);
    }
    var parts = [];
    for (var body in evaluateQuery(context, qAllModifiableSolidBodies()))
    {
        const measuredBox = evBox3d(context, {"topology" : body, "tight" : true});
        parts = append(parts, {"topology_id" : transientQueriesToStrings([body])[0],
            "volume_mm3" : evVolume(context, {"entities" : body}) / (millimeter ^ 3),
            "bounds_mm" : [measuredBox.minCorner / millimeter, measuredBox.maxCorner / millimeter]});
    }
    return {"schema" : "toolroom.native-purpose/1", "nodes" : nodes, "parts" : parts,
        "coverage" : "Explicitly registered function elements only"};
}
