// Toolroom purpose registry. Include after the project's standard-library imports.
// Semantic declarations are not a proof of physical function or necessary volume.
// Unique attribute names keep different purposes distinct through Boolean unions.

function declarePurpose(context is Context, definition is map, entities is Query)
{
    if (!(definition.id is string) || definition.id == "" ||
        !(definition.kind is string) || !(definition.supports is array) ||
        !(definition.description is string) || !(definition.generated is boolean))
        throw regenError("Invalid purpose declaration");
    var registry = getVariable(context, "toolroomPurposeRegistry", {});
    if (registry[definition.id] != undefined)
        throw regenError("Duplicate purpose id: " ~ definition.id);
    const count = size(evaluateQuery(context, entities));
    if (definition.generated && count == 0)
        throw regenError("Generated purpose has no geometry: " ~ definition.id);
    if (!definition.generated && count != 0)
        throw regenError("Disabled purpose unexpectedly has geometry: " ~ definition.id);
    const attributeName = "toolroom.purpose." ~ definition.id;
    definition.attribute_name = attributeName;
    definition.initial_entity_count = count;
    registry[definition.id] = definition;
    setVariable(context, "toolroomPurposeRegistry", registry);
    if (definition.generated)
        setAttribute(context, {"entities" : entities, "name" : attributeName,
            "attribute" : {"schema" : "toolroom.purpose-anchor/1", "id" : definition.id}});
}
