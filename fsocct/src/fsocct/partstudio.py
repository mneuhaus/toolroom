"""Hash-checked local B-rep snapshots implementing an imported Part Studio build()."""

import hashlib
import json
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.STEPControl import STEPControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopoDS import TopoDS_Shape
from OCP.XCAFDoc import XCAFDoc_DocumentTool

from .kernel import Context, members, valid
from .syntax import Unsupported
from .values import Id, RuntimeErrorFS


def create_snapshot(source, destination):
    """Freeze the named, single-solid roots of a Part Studio STEP export."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise RuntimeErrorFS("Snapshot destination must be a new manifest path")
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    if reader.ReadFile(str(source)) != IFSelect_RetDone:
        raise RuntimeErrorFS(f"Cannot read STEP: {source}")
    document = TDocStd_Document(TCollection_ExtendedString("fsocct"))
    if not reader.Transfer(document):
        raise RuntimeErrorFS(f"Cannot transfer STEP: {source}")
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    shapes.GetFreeShapes(roots)
    parts, names = [], set()
    for index in range(1, roots.Length() + 1):
        label = roots.Value(index)
        name_attr = TDataStd_Name()
        if not label.FindAttribute(TDataStd_Name.GetID_s(), name_attr):
            raise RuntimeErrorFS("Every snapshot part must have a STEP name")
        name = name_attr.Get().ToExtString()
        if not name or name in names:
            raise RuntimeErrorFS(f"Empty or duplicate STEP part name: {name!r}")
        shape = shapes.GetShape_s(label)
        if shapes.IsAssembly_s(label) or len(members(shape, "SOLID")) != 1:
            raise Unsupported("Snapshot requires named single-solid roots, not assemblies")
        if not valid(shape):
            raise RuntimeErrorFS(f"Invalid imported STEP part: {name}")
        names.add(name)
        parts.append((name, members(shape, "SOLID")[0]))
    if not parts:
        raise RuntimeErrorFS("STEP contains no named solids")
    folder = destination.parent / (destination.stem + "-parts")
    folder.mkdir(parents=True, exist_ok=False)
    data = {
        "schema": "fsocct-partstudio-v1",
        "source": {"file": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "parts": [],
    }
    for index, (name, shape) in enumerate(parts):
        asset = folder / f"{index:03d}.brep"
        if not BRepTools.Write_s(shape, str(asset)):
            raise RuntimeErrorFS(f"Cannot write B-rep: {asset}")
        data["parts"].append(
            {
                "name": name,
                "file": str(asset.relative_to(destination.parent)),
                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            }
        )
    destination.write_text(json.dumps(data, indent=2) + "\n")
    return data


def load_snapshot(path, source_records):
    path = Path(path).resolve()
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get("schema") != "fsocct-partstudio-v1":
        raise Unsupported(f"Unknown Part Studio snapshot schema: {path}")
    source_records.append(
        {
            "path": str(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "kind": "partstudio-snapshot",
        }
    )
    templates = []
    names = set()
    for part in data["parts"]:
        asset = (path.parent / part["file"]).resolve()
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if digest != part["sha256"]:
            raise RuntimeErrorFS(f"Part snapshot hash mismatch: {asset}")
        if part["name"] in names:
            raise RuntimeErrorFS("Duplicate part name in snapshot")
        names.add(part["name"])
        if asset.suffix.lower() == ".brep":
            shape = TopoDS_Shape()
            if not BRepTools.Read_s(shape, str(asset), BRep_Builder()):
                raise RuntimeErrorFS(f"Cannot read B-rep: {asset}")
        else:
            reader = STEPControl_Reader()
            if reader.ReadFile(str(asset)) != IFSelect_RetDone or reader.TransferRoots() == 0:
                raise RuntimeErrorFS(f"Cannot read STEP: {asset}")
            shape = reader.OneShape()
        if len(members(shape, "SOLID")) != 1:
            raise RuntimeErrorFS(f"Each named snapshot part must contain one solid: {asset}")
        templates.append((part["name"], shape))
        source_records.append({"path": str(asset), "sha256": digest, "kind": "imported-brep"})

    def build(configuration):
        if configuration:
            raise Unsupported(
                "Frozen Part Studio snapshots only support their captured default configuration"
            )
        context = Context()
        for i, (name, shape) in enumerate(templates):
            context.add(shape, {Id(("imported", str(i)))}, {"NAME": name})
        return context

    return {"build": build}
