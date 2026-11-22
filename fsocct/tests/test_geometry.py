import hashlib
import json
import math
import struct
from pathlib import Path

import pytest
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopoDS import TopoDS_Shape

from fsocct.api import run
from fsocct.cli import main
from fsocct.kernel import (
    Context,
    Query,
    boolean_shape,
    export_step,
    members,
    opBoolean,
    valid,
    volume,
)
from fsocct.runtime import Engine
from fsocct.syntax import Unsupported
from fsocct.values import Id, RuntimeErrorFS, Tagged

ROOT = Path(__file__).resolve().parents[1]


def model(body, **context_options):
    module = Engine().load_source(
        """
        export const test = defineFeature(function(c is Context, id is Id, d is map)
        precondition {} {"""
        + body
        + "});"
    )
    c = Context(**context_options)
    module.call("test", c, Id(("test",)), {})
    return c


BOX = """
    fCuboid(c, id+"box", {corner1: vector(0,0,0)*millimeter, corner2: vector(10,20,30)*millimeter});
    var box = qCreatedBy(id+"box", EntityType.BODY);
"""


def test_plate_analytic_volume_bounds_and_retained_name():
    report = run(ROOT / "examples/perforated_plate.fs").report()
    assert report["body_count"] == 1
    assert report["bodies"][0]["valid"]
    assert report["bodies"][0]["bounds_mm"] == [[0, 0, 0], [80, 50, 6]]
    assert report["bodies"][0]["name"] == "Perforated plate"
    assert report["volume_mm3"] == pytest.approx(80 * 50 * 6 - 4 * math.pi * 4**2 * 6, rel=1e-10)
    assert len(report["sources"][0]["sha256"]) == 64


def test_parameter_override_changes_geometry():
    report = run(
        ROOT / "examples/perforated_plate.fs", parameters={"width": "100*millimeter"}
    ).report()
    assert report["bodies"][0]["bounds_mm"][1] == [100, 50, 6]
    assert report["definition"]["width"]["value_si"] == 0.1
    assert report["definition"]["height"]["value_si"] == 0.05
    assert report["volume_mm3"] == pytest.approx(100 * 50 * 6 - 4 * math.pi * 4**2 * 6)


def test_revolve_loft_analytic_volume():
    report = run(ROOT / "examples/revolve_and_loft.fs").report()
    assert report["body_count"] == 2
    sleeve = math.pi * (18**2 - 12**2) * 24
    taper = math.pi * 20 / 3 * (12**2 + 12 * 8 + 8**2)
    assert report["volume_mm3"] == pytest.approx(sleeve + taper, rel=1e-9)
    assert all(b["valid"] for b in report["bodies"])


def test_canonical_m3_module_executes_without_translation():
    report = run(ROOT / "examples/canonical_m3_tool.fs").report()
    assert report["body_count"] == 1
    assert report["bodies"][0]["valid"]
    assert report["bodies"][0]["bounds_mm"][0] == pytest.approx([-2.1, -2.1, 0], abs=2e-7)
    assert report["bodies"][0]["bounds_mm"][1] == pytest.approx([2.1, 2.1, 8.4], abs=2e-7)
    assert len(report["sources"]) == 2


def test_step_round_trip_and_binary_stl(tmp_path):
    result = run(ROOT / "examples/perforated_plate.fs")
    step, stl = tmp_path / "plate.step", tmp_path / "plate.stl"
    result.step(step)
    result.stl(stl)
    reader = STEPControl_Reader()
    assert reader.ReadFile(str(step)) == IFSelect_RetDone
    assert reader.TransferRoots() == 1
    shape = reader.OneShape()
    assert valid(shape)
    assert len(members(shape, "SOLID")) == 1
    assert volume(shape) == pytest.approx(result.report()["volume_mm3"], rel=1e-9)
    data = stl.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert count > 100
    assert len(data) == 84 + 50 * count


def test_boolean_union_and_intersection():
    for mode, expected in (("UNION", 1500), ("INTERSECTION", 500)):
        c = model(
            """
            fCuboid(c, id+"a", {corner1: vector(0,0,0)*millimeter, corner2: vector(10,10,10)*millimeter});
            fCuboid(c, id+"b", {corner1: vector(5,0,0)*millimeter, corner2: vector(15,10,10)*millimeter});
            opBoolean(c, id+"combine", {tools: qAllModifiableSolidBodies(), operationType: BooleanOperationType."""
            + mode
            + """});
        """
        )
        assert c.report()["body_count"] == 1
        assert c.report()["volume_mm3"] == pytest.approx(expected)


def test_disjoint_union_keeps_two_solids():
    c = model(
        BOX
        + """
        fCuboid(c, id+"b", {corner1: vector(40,0,0)*millimeter, corner2: vector(50,20,30)*millimeter});
        opBoolean(c, id+"union", {tools: qAllModifiableSolidBodies(), operationType: BooleanOperationType.UNION});
        if (size(evaluateQuery(c,box)) != 1) throw "disjoint provenance leaked";
        if (evVolume(c,{entities:box}) / millimeter^3 != 6000) throw "wrong source body";
    """
    )
    assert c.report()["body_count"] == 2
    assert c.report()["volume_mm3"] == pytest.approx(12000)


def test_disconnected_union_attributes_fully_enclosed_tools():
    c = model("""
        fCuboid(c,id+"outer",{corner1:vector(0,0,0)*millimeter,corner2:vector(10,10,10)*millimeter});
        fCuboid(c,id+"inner",{corner1:vector(2,2,2)*millimeter,corner2:vector(3,3,3)*millimeter});
        fCuboid(c,id+"other",{corner1:vector(20,0,0)*millimeter,corner2:vector(30,10,10)*millimeter});
        opBoolean(c,id+"union",{tools:qAllModifiableSolidBodies(),operationType:BooleanOperationType.UNION});
        if(size(evaluateQuery(c,qCreatedBy(id+"inner",EntityType.BODY)))!=1) throw "lost enclosed tool";
        if(abs(evVolume(c,{entities:qCreatedBy(id+"inner",EntityType.BODY)})/millimeter^3-1000)>1e-6) throw "wrong enclosing part";
    """)
    assert c.report()["body_count"] == 2
    assert c.report()["volume_mm3"] == pytest.approx(2000)


def test_copied_r10b_solids_use_history_instead_of_coincident_intersection():
    c = Context()
    expected = {}
    for name in ("a", "b"):
        shape = TopoDS_Shape()
        assert BRepTools.Read_s(
            shape, str(ROOT / "tests/fixtures/disjoint_union" / (name + ".brep")), BRep_Builder()
        )
        expected[name] = volume(shape)
        c.add(shape, {Id((name,))}, {"NAME": name})
    opBoolean(
        c,
        Id(("union",)),
        {"tools": Query("all_solids"), "operationType": Tagged("UNION", "BooleanOperationType")},
    )
    assert c.report()["body_count"] == 2
    for b in c.bodies.values():
        name = b.properties["NAME"]
        assert valid(b.shape) and volume(b.shape) == pytest.approx(expected[name])
        assert b.origins == {Id((name,)), Id(("union",))}


def test_step_splits_periodic_export_copy_and_preserves_original(tmp_path):
    shape = TopoDS_Shape()
    assert BRepTools.Read_s(
        shape, str(ROOT / "tests/fixtures/periodic_step/ring.brep"), BRep_Builder()
    )
    c = model(BOX)
    c.add(shape, {Id(("ring",))})
    before = volume(shape)
    check = export_step(c, tmp_path / "ring.step")
    assert check["valid_solids"] == 2 and check["closed_faces_split"]
    assert check["split_solid_count"] == 1
    assert abs(check["volume_difference_mm3"]) < 0.002
    assert valid(shape) and volume(shape) == pytest.approx(before, abs=1e-9)
    assert len(members(shape, "FACE")) == 7


def test_pattern_and_transform_keep_original_query():
    c = model(
        BOX
        + """
        opPattern(c, id+"pattern", {entities: box, instanceNames: ["right"],
            transforms: [transform(vector(30,0,0)*millimeter)]});
        opTransform(c, id+"move", {bodies: box, transform: transform(vector(0,0,5)*millimeter)});
        if (size(evaluateQuery(c,box)) != 1) throw "lost original";
    """
    )
    report = c.report()
    assert report["body_count"] == 2
    assert report["volume_mm3"] == pytest.approx(12000)
    assert report["bodies"][0]["bounds_mm"] == [[0, 0, 5], [10, 20, 35]]
    assert report["bodies"][1]["bounds_mm"] == [[30, 0, 0], [40, 20, 30]]


def test_operation_ids_are_hierarchical_not_string_prefixes():
    c = model(
        BOX
        + """
        fCuboid(c, id+"box2", {corner1: vector(40,0,0)*millimeter, corner2: vector(50,20,30)*millimeter});
        if (size(evaluateQuery(c,box)) != 1) throw "prefix collision";
        if (size(evaluateQuery(c,qCreatedBy(id,EntityType.BODY))) != 2) throw "missing descendant";
    """
    )
    assert c.report()["body_count"] == 2


def test_duplicate_operation_id_rejected_and_rollback():
    c = model(
        BOX
        + """
        try {
            fCuboid(c, id+"bad", {corner1: vector(0,0,0)*millimeter, corner2: vector(0,0,0)*millimeter});
        } catch (error) {}
        fCuboid(c, id+"bad", {corner1: vector(40,0,0)*millimeter, corner2: vector(50,20,30)*millimeter});
    """
    )
    assert c.report()["body_count"] == 2
    assert len(c.report()["failed_operations"]) == 1
    assert c.report()["failed_operations"][0]["id"] == ["test", "bad"]
    with pytest.raises(RuntimeErrorFS, match="already used"):
        model(BOX + BOX.replace("var box", "var another"))


def test_stale_topology_is_explicit():
    with pytest.raises(Unsupported, match="stale"):
        model(
            BOX
            + """
            var edge = evaluateQuery(c,qOwnedByBody(box,EntityType.EDGE))[0];
            opTransform(c,id+"move",{bodies:box,transform:transform(vector(1,0,0)*millimeter)});
            evaluateQuery(c,edge);
        """
        )


def test_fillet_reduces_volume_and_keeps_body():
    c = model(
        BOX
        + """
        opFillet(c,id+"round",{entities:qOwnedByBody(box,EntityType.EDGE),radius:1*millimeter});
        if (size(evaluateQuery(c,box)) != 1) throw "lost original";
    """
    )
    report = c.report()
    assert report["body_count"] == 1
    assert 5800 < report["volume_mm3"] < 6000
    assert report["bodies"][0]["valid"]


def test_fillet_without_tangent_propagation_when_selection_is_complete():
    c = model(
        BOX
        + """
        opFillet(c,id+"round",{entities:qOwnedByBody(box,EntityType.EDGE),radius:1*millimeter,tangentPropagation:false});
    """
    )
    assert c.report()["bodies"][0]["valid"]


def test_cli_protects_imported_source(tmp_path, capsys):
    source = tmp_path / "source.fs"
    helper = tmp_path / "helper.fs"
    helper_text = "export function helper() { return 1; }"
    helper.write_text(helper_text)
    source.write_text(
        'h::import(path:"./helper.fs",version:"local"); export const demo=defineFeature(function(c,id,d) {});'
    )
    assert main(["run", str(source), "--report", str(helper)]) == 2
    assert "must not overwrite source" in capsys.readouterr().err
    assert helper.read_text() == helper_text


def test_unknown_options_and_bounds_do_not_silently_succeed():
    with pytest.raises(Unsupported, match="unexpected"):
        model(
            'fCuboid(c,id+"box",{corner1:vector(0,0,0)*millimeter,corner2:vector(1,1,1)*millimeter,unexpected:42});'
        )
    with pytest.raises(Unsupported, match="BLIND"):
        model(
            'opExtrude(c,id+"ex",{entities:qNothing(),direction:vector(0,0,1),endBound:BoundingType.THROUGH_ALL,endDepth:10*millimeter});'
        )


def test_intersecting_regions_explicitly_rejected():
    with pytest.raises(Unsupported, match="Intersecting"):
        model("""
            var sk = newSketchOnPlane(c,id+"s",{sketchPlane:plane(vector(0,0,0)*millimeter,vector(0,0,1))});
            skCircle(sk,"outer",{center:vector(0,0)*millimeter,radius:10*millimeter});
            skCircle(sk,"other",{center:vector(9,0)*millimeter,radius:5*millimeter});
            skSolve(sk);
        """)


def test_cli_error_does_not_replace_exports(tmp_path, capsys):
    destination = tmp_path / "previous.step"
    destination.write_text("previous artifact")
    code = main(
        [
            "run",
            str(ROOT / "examples/perforated_plate.fs"),
            "--param",
            "width=1*millimeter",
            "--step",
            str(destination),
        ]
    )
    assert code == 2
    assert "Precondition failed" in capsys.readouterr().err
    assert destination.read_text() == "previous artifact"


def test_nested_regions_keep_holes_and_filter_inner_disks():
    c = model("""
        var sk=newSketchOnPlane(c,id+"s",{sketchPlane:plane(vector(0,0,0)*millimeter,vector(0,0,1))});
        skCircle(sk,"outer",{center:vector(0,0)*millimeter,radius:10*millimeter});
        skCircle(sk,"inner",{center:vector(0,0)*millimeter,radius:5*millimeter});
        skSolve(sk);
        if(size(evaluateQuery(c,qSketchRegion(id+"s",false)))!=2) throw "missing region";
        opExtrude(c,id+"ex",{entities:qSketchRegion(id+"s",true),direction:vector(0,0,1),endBound:BoundingType.BLIND,endDepth:3*millimeter});
    """)
    report = c.report()
    assert report["body_count"] == 1
    assert report["volume_mm3"] == pytest.approx(math.pi * (100 - 25) * 3)


def test_open_path_sweep_has_analytic_tube_volume():
    c = model("""
        var path=newSketchOnPlane(c,id+"path",{sketchPlane:plane(vector(0,0,0)*millimeter,vector(0,0,1))});
        skLineSegment(path,"a",{start:vector(0,0)*millimeter,end:vector(20,0)*millimeter});
        skLineSegment(path,"b",{start:vector(30,10)*millimeter,end:vector(30,40)*millimeter});
        skArc(path,"curve",{start:vector(20,0)*millimeter,mid:vector(20+10/sqrt(2),10-10/sqrt(2))*millimeter,end:vector(30,10)*millimeter});
        skSolve(path);
        if(!isQueryEmpty(c,qSketchRegion(id+"path"))) throw "open path has a region";
        var sk=newSketchOnPlane(c,id+"profile",{sketchPlane:plane(vector(0,0,0)*millimeter,vector(1,0,0))});
        skCircle(sk,"c",{center:vector(0,0)*millimeter,radius:2*millimeter});skSolve(sk);
        opSweep(c,id+"sweep",{profiles:qSketchRegion(id+"profile"),path:qCreatedBy(id+"path",EntityType.EDGE)});
        opDeleteBodies(c,id+"clean",{entities:qCreatedBy(id+"path",EntityType.BODY)});
    """)
    assert c.report()["body_count"] == 1
    assert c.report()["volume_mm3"] == pytest.approx(math.pi * 4 * (50 + 5 * math.pi), rel=1e-9)


def test_point_queries_surface_filters_and_transform_composition():
    c = model(
        BOX
        + """
        if(size(evaluateQuery(c,qContainsPoint(box,vector(5,10,15)*millimeter)))!=1) throw "inside";
        if(!isQueryEmpty(c,qContainsPoint(box,vector(11,10,15)*millimeter))) throw "outside";
        if(size(evaluateQuery(c,qGeometry(qOwnedByBody(box,EntityType.FACE),GeometryType.PLANE)))!=6) throw "planes";
        var p=evSurfaceDefinition(c,{face:qNthElement(qOwnedByBody(box,EntityType.FACE),0)});
        if(!(p is Plane)) throw "plane type";
        var t=transform(vector(100,0,0)*millimeter)*mirrorAcross(plane(vector(0,0,0)*millimeter,vector(1,0,0)));
        opTransform(c,id+"pose",{bodies:box,transform:t});
    """
    )
    assert c.report()["bodies"][0]["bounds_mm"] == [[90, 0, 0], [100, 20, 30]]


def test_unification_cannot_damage_boolean_result_or_operands():
    shapes = []
    for name in ("a", "b"):
        shape = TopoDS_Shape()
        path = ROOT / "tests/fixtures/boolean_unification" / (name + ".brep")
        assert BRepTools.Read_s(shape, str(path), BRep_Builder())
        shapes.append(shape)
    original = [volume(shape) for shape in shapes]
    result = boolean_shape(*shapes, "UNION")
    assert valid(result)
    assert volume(result) == pytest.approx(37234.504628831484, abs=1e-6)
    assert all(valid(shape) for shape in shapes)
    assert [volume(shape) for shape in shapes] == pytest.approx(original, abs=1e-9)


def test_face_lineage_and_appearance_survive_merge_pose_and_pattern():
    c = model("""
        fCuboid(c,id+"a",{corner1:vector(0,0,0)*millimeter,corner2:vector(10,10,10)*millimeter});
        fCuboid(c,id+"b",{corner1:vector(5,0,0)*millimeter,corner2:vector(15,10,10)*millimeter});
        var a=qCreatedBy(id+"a",EntityType.FACE);
        setProperty(c,{entities:a,propertyType:PropertyType.APPEARANCE,value:color(1,0,0)});
        opBoolean(c,id+"merge",{tools:qAllModifiableSolidBodies(),operationType:BooleanOperationType.UNION});
        if(size(evaluateQuery(c,a))!=5) throw "lost a lineage";
        if(size(evaluateQuery(c,qCreatedBy(id+"b",EntityType.FACE)))!=5) throw "lost b lineage";
        if(size(evaluateQuery(c,qCreatedBy(id+"merge",EntityType.FACE)))!=4) throw "wrong merged face creators";
        opTransform(c,id+"move",{bodies:qAllModifiableSolidBodies(),transform:transform(vector(0,0,20)*millimeter)});
        if(size(evaluateQuery(c,a))!=5) throw "lost transformed lineage";
        if(!isQueryEmpty(c,qCreatedBy(id+"move",EntityType.FACE))) throw "move created faces";
        opPattern(c,id+"pattern",{entities:qAllModifiableSolidBodies(),instanceNames:["copy"],transforms:[transform(vector(30,0,0)*millimeter)]});
        if(size(evaluateQuery(c,a))!=5) throw "pattern leaked original creators";
        if(size(evaluateQuery(c,qCreatedBy(id+"pattern",EntityType.FACE)))!=6) throw "missing pattern faces";
    """)
    assert c.report()["body_count"] == 2
    assert [b["faces_with_appearance"] for b in c.report()["bodies"]] == [5, 5]
    assert not c.failed_operations


def test_cut_face_lineage_is_independent_of_body_lineage():
    c = model(
        BOX
        + """
        fCylinder(c,id+"tool",{topCenter:vector(5,10,40)*millimeter,bottomCenter:vector(5,10,-10)*millimeter,radius:2*millimeter});
        opBoolean(c,id+"cut",{targets:box,tools:qCreatedBy(id+"tool",EntityType.BODY),operationType:BooleanOperationType.SUBTRACTION});
        if(!isQueryEmpty(c,qCreatedBy(id+"tool",EntityType.BODY))) throw "tool body survived";
        if(size(evaluateQuery(c,qCreatedBy(id+"tool",EntityType.FACE)))!=1) throw "cut wall lineage missing";
    """
    )
    assert c.report()["volume_mm3"] == pytest.approx(6000 - math.pi * 4 * 30)


def test_affine_shear_points_inverse_and_solid_volume():
    c = model(
        BOX
        + """
        var t=transform(matrix([[1,0,1.5],[0,1,0],[0,0,1]]),vector(2,3,4)*millimeter);
        var p=vector(2,5,8)*millimeter;
        if(norm(t*p-vector(16,8,12)*millimeter)>1e-8*millimeter) throw "wrong point";
        if(norm(inverse(t)*(t*p)-p)>1e-8*millimeter) throw "wrong inverse";
        opTransform(c,id+"shear",{bodies:box,transform:t});
    """
    )
    report = c.report()
    assert report["volume_mm3"] == pytest.approx(6000)
    assert report["bodies"][0]["valid"]
    for actual, expected in zip(report["bodies"][0]["bounds_mm"], [[2, 3, 4], [57, 23, 34]]):
        assert actual == pytest.approx(expected, abs=1e-6)


def test_coordinate_system_world_direction_and_roundtrip():
    c = model(
        BOX
        + """
        var frame=coordSystem(vector(100,0,0)*millimeter,vector(0,2,0),vector(4,0,0));
        if(!(frame is CoordSystem)) throw "wrong type";
        var p=vector(2,3,4)*millimeter;
        if(norm(toWorld(frame,p)-vector(104,2,3)*millimeter)>1e-8*millimeter) throw "wrong world point";
        if(norm(fromWorld(frame,toWorld(frame)*p)-p)>1e-8*millimeter) throw "wrong local point";
        opTransform(c,id+"pose",{bodies:box,transform:toWorld(frame)});
    """
    )
    assert c.report()["bodies"][0]["bounds_mm"] == [[100, 0, 0], [130, 10, 20]]
    with pytest.raises(RuntimeErrorFS, match="perpendicular"):
        model("coordSystem(vector(0,0,0)*millimeter,vector(1,0,0),vector(1,1,0));")


def test_cylinder_surface_frame_can_transform_points():
    c = model("""
        fCylinder(c,id+"cylinder",{bottomCenter:vector(10,20,30)*millimeter,topCenter:vector(10,20,40)*millimeter,radius:2*millimeter});
        var surface=evSurfaceDefinition(c,{face:qGeometry(qCreatedBy(id+"cylinder",EntityType.FACE),GeometryType.CYLINDER)});
        if(!(surface is Cylinder)) throw "wrong surface type";
        var frame=surface.coordSystem;
        if(norm(toWorld(frame)*(vector(0,0,0)*millimeter)-frame.origin)>1e-8*millimeter) throw "wrong cylinder origin";
    """)
    assert c.report()["volume_mm3"] == pytest.approx(math.pi * 4 * 10)


def test_text_preserves_letter_hole_and_exact_font_provenance():
    source = """
        var sk=newSketchOnPlane(c,id+"s",{sketchPlane:plane(vector(0,0,0)*millimeter,vector(0,0,1))});
        skText(sk,"letter",{text:"O",fontName:"fixture",firstCorner:vector(0,0)*millimeter,secondCorner:vector(20,10)*millimeter});
        skSolve(sk);
        if(size(evaluateQuery(c,qSketchRegion(id+"s",true)))!=1) throw "wrong letter regions";
        if(size(evaluateQuery(c,qSketchRegion(id+"s",false)))!=2) throw "missing letter hole";
        opExtrude(c,id+"text",{entities:qSketchRegion(id+"s",true),direction:vector(0,0,1),endBound:BoundingType.BLIND,endDepth:2*millimeter});
        if(!isQueryEmpty(c,qContainsPoint(qAllModifiableSolidBodies(),vector(4,5,1)*millimeter))) throw "letter hole filled";
    """
    with pytest.raises(Unsupported, match="explicit --fonts"):
        model(source)
    font = ROOT / "cases/workspace/fonts/OpenSans-Regular.ttf"
    c = model(source, fonts={"fixture": font})
    assert c.assets == [
        {"path": str(font), "sha256": hashlib.sha256(font.read_bytes()).hexdigest(), "kind": "font"}
    ]
    report = c.report()
    assert report["body_count"] == 1 and report["bodies"][0]["valid"]
    assert 30 < report["volume_mm3"] < 100
    assert report["bodies"][0]["bounds_mm"][1][1:] == pytest.approx([10, 2], abs=1e-5)


def test_cli_report_and_parse_only(tmp_path, capsys):
    destination = tmp_path / "report.json"
    assert main(["check", str(ROOT / "examples/perforated_plate.fs")]) == 0
    assert "not checked" in capsys.readouterr().out
    assert (
        main(["run", str(ROOT / "examples/perforated_plate.fs"), "--report", str(destination)]) == 0
    )
    assert json.loads(destination.read_text())["body_count"] == 1
