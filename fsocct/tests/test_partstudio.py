import json

import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool

from fsocct.api import run
from fsocct.partstudio import create_snapshot, load_snapshot
from fsocct.values import RuntimeErrorFS


def named_step(path):
    document = TDocStd_Document(TCollection_ExtendedString("test"))
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    label = shapes.AddShape(BRepPrimAPI_MakeBox(10, 20, 30).Shape(), False)
    TDataStd_Name.Set_s(label, TCollection_ExtendedString("Named reference"))
    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    assert writer.Transfer(document, STEPControl_AsIs)
    assert writer.Write(str(path)) == IFSelect_RetDone


def test_snapshot_instances_preserve_names_and_apply_rigid_pose(tmp_path):
    step, snapshot = tmp_path / "reference.step", tmp_path / "reference.json"
    named_step(step)
    data = create_snapshot(step, snapshot)
    assert [p["name"] for p in data["parts"]] == ["Named reference"]
    source = tmp_path / "model.fs"
    source.write_text("""
        ref::import(path:"reference",version:"pinned");
        export enum Position { annotation {"Name":"Moved"} MOVED, ORIGIN }
        export const demo=defineFeature(function(c,id,d) {
            var loaded=ref::build({});
            var i=newInstantiator(id+"import");
            var pose=d.position==Position.MOVED ?
                transform(matrix([[0,-1,0],[1,0,0],[0,0,1]]),vector(40,0,0)*millimeter) :
                identityTransform();
            var part=addInstance(i,ref::build,{name:"one",
                partQuery:qAllModifiableSolidBodies(),loadedContext:loaded,transform:pose});
            instantiate(c,i);
            if(size(evaluateQuery(c,part))!=1) throw "lost instance";
            if(getProperty(c,{entity:part,propertyType:PropertyType.NAME})!="Named reference")
                throw "lost name";
            if(evVolume(loaded,{entities:qAllModifiableSolidBodies()})/(millimeter^3)!=6000)
                throw "changed source";
        });
    """)
    result = run(
        source, imports={"reference@pinned": snapshot}, parameters={"position": "Position.MOVED"}
    ).report()
    assert result["body_count"] == 1
    assert result["volume_mm3"] == pytest.approx(6000)
    assert result["bodies"][0]["valid"]
    assert result["bodies"][0]["bounds_mm"] == [[20, 0, 0], [40, 10, 30]]
    assert {s.get("kind") for s in result["sources"]} >= {"partstudio-snapshot", "imported-brep"}
    with pytest.raises(RuntimeErrorFS, match="new manifest"):
        create_snapshot(step, snapshot)
    asset = snapshot.parent / data["parts"][0]["file"]
    asset.write_bytes(asset.read_bytes() + b"tampered")
    with pytest.raises(RuntimeErrorFS, match="hash mismatch"):
        load_snapshot(snapshot, [])


def test_frozen_configuration_is_not_silently_ignored(tmp_path):
    snapshot = tmp_path / "empty.json"
    snapshot.write_text(json.dumps({"schema": "fsocct-partstudio-v1", "parts": []}))
    from fsocct.syntax import Unsupported

    with pytest.raises(Unsupported, match="configuration"):
        load_snapshot(snapshot, [])["build"]({"width": 10})
