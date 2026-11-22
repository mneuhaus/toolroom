"""Explicit FeatureScript API adapters to OpenCascade (via OCP).

Kernel coordinates are millimeters. Query identity is local to a Context, not
Parasolid/Onshape persistent topology. Unsupported options are never ignored.
"""

import hashlib
import math
import tempfile
import time
from dataclasses import dataclass, field, replace
from functools import wraps
from itertools import pairwise
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_Copy,
    BRepBuilderAPI_GTransform,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeVertex,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Transform,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe, BRepOffsetAPI_ThruSections
from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeRevol,
)
from OCP.GC import GC_MakeArcOfCircle
from OCP.GeomAbs import (
    GeomAbs_BezierSurface,
    GeomAbs_BSplineSurface,
    GeomAbs_Circle,
    GeomAbs_Cone,
    GeomAbs_Cylinder,
    GeomAbs_Ellipse,
    GeomAbs_Line,
    GeomAbs_Plane,
    GeomAbs_Sphere,
    GeomAbs_SurfaceOfExtrusion,
    GeomAbs_SurfaceOfRevolution,
    GeomAbs_Torus,
)
from OCP.gp import (
    gp_Ax1,
    gp_Ax2,
    gp_Ax3,
    gp_Circ,
    gp_Dir,
    gp_GTrsf,
    gp_Mat,
    gp_Pln,
    gp_Pnt,
    gp_Trsf,
    gp_Vec,
    gp_XYZ,
)
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.NCollection import NCollection_Utf8String
from OCP.ShapeUpgrade import ShapeUpgrade_ShapeDivideClosed, ShapeUpgrade_UnifySameDomain
from OCP.StdPrs import StdPrs_BRepFont, StdPrs_BRepTextBuilder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import (
    TopAbs_EDGE,
    TopAbs_FACE,
    TopAbs_IN,
    TopAbs_ON,
    TopAbs_REVERSED,
    TopAbs_SOLID,
    TopAbs_VERTEX,
    TopAbs_WIRE,
)
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.TopTools import TopTools_IndexedMapOfShape, TopTools_ListOfShape

from .syntax import Unsupported
from .values import (
    ANGLE,
    LENGTH,
    Id,
    Matrix,
    Quantity,
    RuntimeErrorFS,
    Tagged,
    UnstableIdComponent,
    Vector,
    boolean,
    clone,
    cross,
    dot,
    normalize,
    number,
    scalar,
)

TOPOLOGY = {
    "EDGE": TopAbs_EDGE,
    "FACE": TopAbs_FACE,
    "VERTEX": TopAbs_VERTEX,
    "SOLID": TopAbs_SOLID,
    "WIRE": TopAbs_WIRE,
}
TOL = 1e-7  # mm; OpenCascade's nominal geometric tolerance.


def members(shape, kind):
    shapes = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TOPOLOGY[kind], shapes)
    return [shapes.FindKey(i) for i in range(1, shapes.Extent() + 1)]


def compound(shapes):
    builder, result = BRep_Builder(), TopoDS_Compound()
    builder.MakeCompound(result)
    for shape in shapes:
        builder.Add(result, shape)
    return result


def volume(shape):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, p)
    return p.Mass()


def area(shape):
    p = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, p)
    return p.Mass()


def bounds(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, b, False, False)
    if b.IsVoid():
        raise RuntimeErrorFS("Cannot bound empty geometry")
    v = b.Get()
    return [list(v[:3]), list(v[3:])]


def valid(shape):
    return not shape.IsNull() and BRepCheck_Analyzer(shape).IsValid()


def xyz(v, dims=LENGTH, size=3):
    if not isinstance(v, Vector) or len(v) != size:
        raise RuntimeErrorFS(f"Expected a {size}D Vector")
    vals = [scalar(x, dims) for x in v]
    if not all(math.isfinite(x) for x in vals):
        raise RuntimeErrorFS("Non-finite vector")
    return [x * 1000 for x in vals] if dims == LENGTH else vals


def mm(v):
    value = scalar(v, LENGTH) * 1000
    if not math.isfinite(value):
        raise RuntimeErrorFS("Non-finite length")
    return value


def positive(v):
    value = mm(v)
    if value <= TOL:
        raise RuntimeErrorFS("Length must exceed kernel tolerance (1e-7 mm)")
    return value


def options(d, required, optional=()):
    if not isinstance(d, dict):
        raise RuntimeErrorFS("Operation definition must be a map")
    missing = set(required) - d.keys()
    if missing:
        raise RuntimeErrorFS("Missing parameters: " + ", ".join(sorted(missing)))
    unknown = d.keys() - set(required) - set(optional)
    if unknown:
        raise Unsupported("Unsupported parameters: " + ", ".join(sorted(unknown)))


def enum_value(value, tag):
    if not isinstance(value, Tagged) or value.tag != tag:
        raise RuntimeErrorFS(f"Expected {tag}")
    return value.value


def feature_id(value):
    if not isinstance(value, Id) or not value or not all(isinstance(v, str) and v for v in value):
        raise RuntimeErrorFS("Expected a nonempty Id")
    if any("*" in v and not isinstance(v, UnstableIdComponent) for v in value):
        raise Unsupported("Wildcard/unstable Id components are not implemented")
    return value


def prefix(ancestor, child):
    return child[: len(ancestor)] == ancestor


@dataclass(frozen=True)
class Plane:
    origin: Vector
    normal: Vector
    x: Vector
    fs_fields = ("origin", "normal", "x")

    @property
    def y(self):
        return cross(self.normal, self.x)

    def point(self, v):
        u, w = xyz(v, size=2)
        o, x, y = xyz(self.origin), xyz(self.x, (0, 0)), xyz(self.y, (0, 0))
        return gp_Pnt(*[o[i] + x[i] * u + y[i] * w for i in range(3)])

    def axis(self):
        return gp_Ax2(
            gp_Pnt(*xyz(self.origin)),
            gp_Dir(*xyz(self.normal, (0, 0))),
            gp_Dir(*xyz(self.x, (0, 0))),
        )


def plane(origin, normal, x=None):
    xyz(origin)
    xyz(normal, (0, 0))
    n = normalize(normal)
    if x is None:
        # Deterministic orthonormal frame; matches common principal planes.
        axis = Vector((1.0, 0.0, 0.0)) if abs(n[0]) < 0.9 else Vector((0.0, 1.0, 0.0))
        proj = dot(axis, n)
        x = Vector(axis[i] - proj * n[i] for i in range(3))
    xyz(x, (0, 0))
    x = normalize(x)
    if abs(dot(x, n)) > 1e-9:
        raise RuntimeErrorFS("Plane x axis must be perpendicular to normal")
    return Plane(origin, n, x)


@dataclass(frozen=True)
class Line:
    origin: Vector
    direction: Vector
    fs_fields = ("origin", "direction")


def line(origin, direction):
    xyz(origin)
    xyz(direction, (0, 0))
    return Line(origin, normalize(direction))


@dataclass(frozen=True)
class Transform:
    value: object

    def fs_binary(self, op, other):
        if op == "*" and isinstance(other, Transform):
            if isinstance(self.value, gp_GTrsf) or isinstance(other.value, gp_GTrsf):
                return Transform(
                    general_transform(self.value).Multiplied(general_transform(other.value))
                )
            return Transform(self.value.Multiplied(other.value))
        if op == "*" and isinstance(other, Vector):
            if isinstance(self.value, gp_GTrsf):
                coordinates = gp_XYZ(*xyz(other))
                self.value.Transforms(coordinates)
                return Vector(Quantity(x / 1000) for x in coordinates.Coord())
            point = gp_Pnt(*xyz(other)).Transformed(self.value)
            return Vector(Quantity(x / 1000) for x in point.Coord())
        raise Unsupported(f"Unsupported Transform operator {op}")


def general_transform(t):
    return t if isinstance(t, gp_GTrsf) else gp_GTrsf(t)


def transformed_shape(shape, t, history=None):
    cls = BRepBuilderAPI_GTransform if isinstance(t, gp_GTrsf) else BRepBuilderAPI_Transform
    maker = cls(shape, t, True)
    if history is not None:
        history.append((maker, False))
    return maker.Shape()


def mirror_across(pl):
    if not isinstance(pl, Plane):
        raise RuntimeErrorFS("mirrorAcross needs a Plane")
    t = gp_Trsf()
    t.SetMirror(pl.axis())
    return Transform(t)


def transform(rotation_or_translation, translation=None):
    t = gp_Trsf()
    if translation is None:
        t.SetTranslation(gp_Vec(*xyz(rotation_or_translation)))
    else:
        r = rotation_or_translation
        if not isinstance(r, Matrix) or len(r) != 3 or len(r[0]) != 3:
            raise RuntimeErrorFS("Transform needs a 3x3 Matrix")
        if not all(math.isfinite(v) for row in r for v in row):
            raise RuntimeErrorFS("Non-finite transform matrix")
        d = xyz(translation)
        if all(
            abs(sum(r[k][i] * r[k][j] for k in range(3)) - (i == j)) <= 1e-9
            for i in range(3)
            for j in range(3)
        ):
            t.SetValues(*[v for i in range(3) for v in (*r[i], d[i])])
        else:
            m = gp_Mat(*[v for row in r for v in row])
            if m.IsSingular():
                raise RuntimeErrorFS("Singular transform matrix")
            t = gp_GTrsf(m, gp_XYZ(*d))
    return Transform(t)


def rotation_around(axis, angle):
    if not isinstance(axis, Line):
        raise RuntimeErrorFS("rotationAround needs a Line")
    t = gp_Trsf()
    t.SetRotation(
        gp_Ax1(gp_Pnt(*xyz(axis.origin)), gp_Dir(*xyz(axis.direction, (0, 0)))),
        scalar(angle, ANGLE),
    )
    return Transform(t)


@dataclass(frozen=True)
class CoordSystem:
    origin: Vector
    xAxis: Vector
    zAxis: Vector
    fs_fields = ("origin", "xAxis", "zAxis")


def coord_system(origin, x_axis, z_axis):
    frame = plane(origin, z_axis, x_axis)
    return CoordSystem(frame.origin, frame.x, frame.normal)


def to_world(frame, point=None):
    if not isinstance(frame, CoordSystem):
        raise RuntimeErrorFS("toWorld needs a CoordSystem")
    axes = (frame.xAxis, cross(frame.zAxis, frame.xAxis), frame.zAxis)
    pose = transform(Matrix([[axis[i] for axis in axes] for i in range(3)]), frame.origin)
    return pose if point is None else pose.fs_binary("*", point)


def from_world(frame, point=None):
    pose = Transform(to_world(frame).value.Inverted())
    return pose if point is None else pose.fs_binary("*", point)


@dataclass
class FaceRecord:
    shape: object
    origins: set
    properties: dict = field(default_factory=dict)
    contributors: set = field(default_factory=set)


def history_shapes(shapes):
    # OCP 7.9's native StopIteration path costs about 3 ms per list, including
    # empty lists. Consume its known size without triggering that exception.
    iterator = iter(shapes)
    return [next(iterator) for _ in range(shapes.Size())]


def remap_faces(shape, records, history, id, reset=False):
    """Propagate face lineage through OCCT's actual Modified/Generated history."""
    for mapper, creates in history:
        mapped, indices, donors = [], TopTools_IndexedMapOfShape(), []
        for record in records:
            modified = [
                f
                for f in history_shapes(mapper.Modified(record.shape))
                if f.ShapeType() == TopAbs_FACE
            ]
            generated = [
                f
                for f in history_shapes(mapper.Generated(record.shape))
                if f.ShapeType() == TopAbs_FACE
            ]
            removed = (
                mapper.IsRemoved(record.shape)
                if hasattr(mapper, "IsRemoved")
                else mapper.IsDeleted(record.shape)
            )
            successors = [(f, creates and len(modified) > 1) for f in modified]
            successors.extend((f, creates) for f in generated)
            if not modified and not removed:
                successors.append((record.shape, False))
            for face, created in successors:
                index = indices.FindIndex(face)
                if not index:
                    index = indices.Add(face)
                    mapped.append(FaceRecord(face, set()))
                    donors.append(set())
                target = mapped[index - 1]
                donors[index - 1].add(record.shape)
                target.origins.update(record.origins)
                target.contributors.update(record.contributors)
                if created or (creates and len(donors[index - 1]) > 1):
                    target.origins.add(id)
                for key, value in record.properties.items():
                    target.properties.setdefault(key, clone(value))
        records = mapped
    output = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, output)
    result = [FaceRecord(output.FindKey(i), set()) for i in range(1, output.Extent() + 1)]
    for record in records:
        index = output.FindIndex(record.shape)
        if index:
            result[index - 1] = record
    for face in result:
        if reset or not face.origins:
            face.origins = {id}
    return result


def select_faces(shape, records):
    selected = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, selected)
    return [r for r in records if selected.Contains(r.shape)]


def contributing_faces(body):
    return [replace(f, contributors={body.key}) for f in body.faces]


@dataclass
class Body:
    key: int
    shape: object
    origins: set
    properties: dict = field(default_factory=dict)
    revision: int = 0
    faces: list = field(default_factory=list)


@dataclass(frozen=True)
class Entity:
    kind: str
    shape: object
    owner: object
    revision: int = 0


@dataclass(frozen=True)
class Query:
    kind: str
    args: tuple = ()
    fs_builtin = True


@dataclass
class Sketch:
    context: object
    id: Id
    plane: Plane
    edges: list = field(default_factory=list)
    names: set = field(default_factory=set)
    faces: list | None = None
    outer_faces: list = field(default_factory=list)
    fs_builtin = True


@dataclass
class Instantiator:
    id: Id
    entries: list = field(default_factory=list)
    consumed: bool = False
    fs_builtin = True


def newInstantiator(id):
    return Instantiator(feature_id(id))


def addInstance(inst, build_function, d):
    if not isinstance(inst, Instantiator) or inst.consumed:
        raise RuntimeErrorFS("Expected an unused Instantiator")
    options(d, ("name", "partQuery", "loadedContext"), ("transform",))
    name = d["name"]
    if not isinstance(name, str) or not name or any(e[0] == name for e in inst.entries):
        raise RuntimeErrorFS("Instance name must be a unique nonempty string")
    source = d["loadedContext"]
    if not isinstance(source, Context):
        raise RuntimeErrorFS("loadedContext must be a Context")
    selected = bodies(source, d["partQuery"])
    pose = d.get("transform", Transform(gp_Trsf()))
    if not isinstance(pose, Transform):
        raise RuntimeErrorFS("Instance pose must be a Transform")
    inst.entries.append((name, selected, pose))
    return Query("created", (Id((*inst.id, name)), "BODY"))


def instantiate(c, inst):
    if not isinstance(inst, Instantiator) or inst.consumed:
        raise RuntimeErrorFS("Expected an unused Instantiator")
    instantiate_operation(c, inst.id, {"entries": inst.entries})
    inst.consumed = True


class Context:
    fs_builtin = True

    def __init__(self, progress=None, fonts=None):
        self.bodies, self.sketches, self.used_ids = {}, {}, set()
        self.next_key, self.operations = 1, []
        self.progress = progress
        self.fonts, self.assets = fonts or {}, []
        self.failed_operations = []

    def reserve(self, id):
        feature_id(id)
        if id in self.used_ids:
            raise RuntimeErrorFS("Operation Id already used: " + "/".join(id))
        self.used_ids.add(id)

    def add(self, shape, origins, properties=None, revision=0, faces=None):
        if not valid(shape):
            raise RuntimeErrorFS("OpenCascade produced an invalid shape")
        solids = members(shape, "SOLID")
        result = []
        for solid in solids:
            if volume(solid) <= TOL**3:
                raise RuntimeErrorFS("Non-positive solid volume")
            key = self.next_key
            self.next_key += 1
            self.bodies[key] = Body(
                key,
                solid,
                set(origins),
                dict(clone(properties or {})),
                revision,
                select_faces(solid, faces)
                if faces is not None
                else [FaceRecord(f, set(origins)) for f in members(solid, "FACE")],
            )
            result.append(key)
        return result

    def report(self):
        bodies = []
        for b in self.bodies.values():
            bodies.append(
                {
                    "id": b.key,
                    "name": b.properties.get("NAME"),
                    "valid": valid(b.shape),
                    "volume_mm3": volume(b.shape),
                    "bounds_mm": bounds(b.shape),
                    "faces": len(members(b.shape, "FACE")),
                    "faces_with_appearance": sum("APPEARANCE" in f.properties for f in b.faces),
                    "edges": len(members(b.shape, "EDGE")),
                    "created_by": [list(x) for x in sorted(b.origins)],
                }
            )
        return {
            "kernel": "OpenCascade",
            "units": "mm",
            "body_count": len(bodies),
            "volume_mm3": sum(b["volume_mm3"] for b in bodies),
            "bodies": bodies,
            "operations": self.operations,
            "failed_operations": self.failed_operations,
        }

    def shape(self):
        return compound([b.shape for b in self.bodies.values()])


def operation(fn):
    @wraps(fn)
    def wrapped(context, id, definition):
        if not isinstance(context, Context):
            raise RuntimeErrorFS("First argument must be a Context")
        started = time.perf_counter()
        if context.progress:
            context.progress({"id": list(id), "operation": fn.__name__})
        snapshot = (
            {
                k: replace(v, origins=set(v.origins), properties=dict(clone(v.properties)))
                for k, v in context.bodies.items()
            },
            dict(context.sketches),
            set(context.used_ids),
            context.next_key,
        )
        try:
            context.reserve(id)
            value = fn(context, id, definition)
            context.operations.append(
                {
                    "id": list(id),
                    "operation": fn.__name__,
                    "bodies_after": len(context.bodies),
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
            return value
        except Exception as e:
            context.bodies, context.sketches, context.used_ids, context.next_key = snapshot
            context.failed_operations.append(
                {"id": list(id), "operation": fn.__name__, "error": str(e)}
            )
            if isinstance(e, (RuntimeErrorFS, Unsupported)):
                raise
            raise RuntimeErrorFS(f"OpenCascade {fn.__name__} failed: {e}") from e

    return wrapped


@operation
def instantiate_operation(c, id, d):
    for name, selected, pose in d["entries"]:
        for b in selected:
            history, instance_id = [], Id((*id, name))
            shape = transformed_shape(b.shape, pose.value, history)
            faces = remap_faces(shape, b.faces, history, instance_id, reset=True)
            c.add(shape, {instance_id}, b.properties, faces=faces)


def unique(entities):
    result = []
    for e in entities:
        if not any(
            e.kind == v.kind and e.owner == v.owner and e.shape.IsSame(v.shape) for v in result
        ):
            result.append(e)
    return result


def resolve(c, q):
    if not isinstance(c, Context) or not isinstance(q, Query):
        raise RuntimeErrorFS("Query evaluation needs a Context and Query")
    k, a = q.kind, q.args
    if k == "nothing":
        return []
    if k == "union":
        return unique([e for v in a[0] for e in resolve(c, v)])
    if k in ("subtract", "intersect"):
        left, right = resolve(c, a[0]), resolve(c, a[1])
        return [
            e
            for e in left
            if (
                any(
                    e.owner == v.owner and e.kind == v.kind and e.shape.IsSame(v.shape)
                    for v in right
                )
            )
            == (k == "intersect")
        ]
    if k == "nth":
        values = resolve(c, a[0])
        i = number(a[1])
        if i != int(i) or i < 0:
            raise RuntimeErrorFS("qNthElement needs a non-negative integer")
        return values[int(i) : int(i) + 1]
    if k == "transient":
        e, owner_context = a
        if owner_context is not c:
            raise RuntimeErrorFS("Query belongs to a different Context")
        if isinstance(e.owner, int):
            body = c.bodies.get(e.owner)
            if body is None:
                return []
            if e.kind == "BODY":
                return [Entity("BODY", body.shape, body.key, body.revision)]
            if body.revision != e.revision:
                raise Unsupported(
                    "Topology query became stale after a body modification; reselect its edges/faces"
                )
        elif e.owner not in c.sketches:
            return []
        return [e]
    if k == "filter":
        return [e for e in resolve(c, a[0]) if e.kind == a[1]]
    if k == "geometry":
        return [e for e in resolve(c, a[0]) if geometry_type(e) == a[1]]
    if k == "contains_point":
        point = gp_Pnt(*xyz(a[1]))
        vertex = BRepBuilderAPI_MakeVertex(point).Vertex()
        result = []
        for e in resolve(c, a[0]):
            if e.kind == "BODY" and isinstance(e.owner, int):
                contains = BRepClass3d_SolidClassifier(e.shape, point, TOL).State() in (
                    TopAbs_IN,
                    TopAbs_ON,
                )
            else:
                distance = BRepExtrema_DistShapeShape(e.shape, vertex)
                if not distance.IsDone():
                    raise RuntimeErrorFS("Cannot evaluate distance to query point")
                contains = distance.Value() <= TOL
            if contains:
                result.append(e)
        return result
    if k == "solid_filter":
        return [e for e in resolve(c, a[0]) if e.kind == "BODY" and isinstance(e.owner, int)]
    if k == "owned":
        result = []
        for e in resolve(c, a[0]):
            if e.kind != "BODY":
                raise RuntimeErrorFS("qOwnedByBody requires bodies")
            result.extend(Entity(a[1], s, e.owner, e.revision) for s in members(e.shape, a[1]))
        return unique(result)
    if k == "owner":
        result = []
        for e in resolve(c, a[0]):
            if e.owner in c.bodies:
                b = c.bodies[e.owner]
                result.append(Entity("BODY", b.shape, b.key, b.revision))
        return unique(result)
    if k == "sketch_region":
        sk = c.sketches.get(a[0])
        if sk is None:
            return []
        if sk.faces is None:
            raise RuntimeErrorFS("Sketch has not been solved")
        return [Entity("FACE", f, sk.id) for f in (sk.outer_faces if a[1] else sk.faces)]
    if k in ("created", "everything", "all_solids"):
        typ = a[-1] if k != "all_solids" else "BODY"
        result = []
        for b in c.bodies.values():
            if (
                k == "created"
                and typ != "FACE"
                and not any(prefix(a[0], origin) for origin in b.origins)
            ):
                continue
            if typ == "BODY":
                result.append(Entity("BODY", b.shape, b.key, b.revision))
            elif typ == "FACE" and k == "created":
                result.extend(
                    Entity("FACE", f.shape, b.key, b.revision)
                    for f in b.faces
                    if any(prefix(a[0], origin) for origin in f.origins)
                )
            else:
                if k == "created" and b.revision:
                    raise Unsupported(
                        "qCreatedBy for modified topology needs Onshape history; use qOwnedByBody"
                    )
                result.extend(Entity(typ, s, b.key, b.revision) for s in members(b.shape, typ))
        if k != "all_solids":
            for sk in c.sketches.values():
                if k == "created" and not prefix(a[0], sk.id):
                    continue
                if sk.faces is None:
                    continue
                if typ == "BODY":
                    result.append(Entity("BODY", compound([*sk.faces, *sk.edges]), sk.id))
                elif typ == "FACE":
                    result.extend(Entity("FACE", f, sk.id) for f in sk.faces)
                else:
                    result.extend(Entity(typ, s, sk.id) for s in members(compound(sk.edges), typ))
        return unique(result)
    raise Unsupported(f"Query kind {k!r} not implemented")


def bodies(c, q, allow_empty=False):
    entities = resolve(c, q)
    if any(e.kind != "BODY" or not isinstance(e.owner, int) for e in entities):
        raise RuntimeErrorFS("Operation needs solid bodies")
    if not entities and not allow_empty:
        raise RuntimeErrorFS("Query matched no solid bodies")
    return [c.bodies[e.owner] for e in entities]


@operation
def fCuboid(c, id, d):
    options(d, ("corner1", "corner2"))
    a, b = xyz(d["corner1"]), xyz(d["corner2"])
    lo, hi = [min(x, y) for x, y in zip(a, b)], [max(x, y) for x, y in zip(a, b)]
    if any(y - x <= TOL for x, y in zip(lo, hi)):
        raise RuntimeErrorFS("Cuboid corners must enclose positive volume")
    c.add(BRepPrimAPI_MakeBox(gp_Pnt(*lo), gp_Pnt(*hi)).Shape(), {id})


@operation
def fCylinder(c, id, d):
    options(d, ("bottomCenter", "topCenter", "radius"))
    a, b = xyz(d["bottomCenter"]), xyz(d["topCenter"])
    v = gp_Vec(gp_Pnt(*a), gp_Pnt(*b))
    if v.Magnitude() <= TOL:
        raise RuntimeErrorFS("Cylinder endpoints coincide")
    axis = gp_Ax2(gp_Pnt(*a), gp_Dir(v))
    c.add(BRepPrimAPI_MakeCylinder(axis, positive(d["radius"]), v.Magnitude()).Shape(), {id})


def newSketchOnPlane(c, id, d):
    options(d, ("sketchPlane",))
    if not isinstance(d["sketchPlane"], Plane):
        raise RuntimeErrorFS("sketchPlane must be a Plane")
    c.reserve(id)
    sk = Sketch(c, id, d["sketchPlane"])
    c.sketches[id] = sk
    return sk


def sketch_entity(fn):
    @wraps(fn)
    def wrapped(sk, name, d):
        if not isinstance(sk, Sketch) or sk.id not in sk.context.sketches:
            raise RuntimeErrorFS("Expected a live Sketch")
        if sk.faces is not None:
            raise RuntimeErrorFS("Cannot add entities to a solved sketch")
        if not isinstance(name, str) or name in sk.names:
            raise RuntimeErrorFS("Sketch entity name must be a unique string")
        d = dict(d)
        if boolean(d.pop("construction", False)):
            raise Unsupported("Construction geometry is not implemented")
        try:
            edges = fn(sk, d)
        except (RuntimeErrorFS, Unsupported):
            raise
        except Exception as e:
            raise RuntimeErrorFS(f"Invalid {fn.__name__}: {e}") from e
        sk.edges.extend(edges)
        sk.names.add(name)
        if fn.__name__ == "skText":
            return {"textId": name}

    return wrapped


@sketch_entity
def skLineSegment(sk, d):
    options(d, ("start", "end"))
    return [BRepBuilderAPI_MakeEdge(sk.plane.point(d["start"]), sk.plane.point(d["end"])).Edge()]


@sketch_entity
def skCircle(sk, d):
    options(d, ("center", "radius"))
    frame = sk.plane.axis()
    frame.SetLocation(sk.plane.point(d["center"]))
    return [BRepBuilderAPI_MakeEdge(gp_Circ(frame, positive(d["radius"]))).Edge()]


def poly_edges(sk, points):
    if not isinstance(points, list) or len(points) < 2:
        raise RuntimeErrorFS("Polyline needs at least two points")
    pts = [sk.plane.point(v) for v in points]
    return [BRepBuilderAPI_MakeEdge(a, b).Edge() for a, b in pairwise(pts)]


@sketch_entity
def skPolyline(sk, d):
    options(d, ("points",))
    return poly_edges(sk, d["points"])


@sketch_entity
def skRectangle(sk, d):
    options(d, ("firstCorner", "secondCorner"))
    a, b = d["firstCorner"], d["secondCorner"]
    xyz(a, size=2)
    xyz(b, size=2)
    return poly_edges(sk, [a, Vector((b[0], a[1])), b, Vector((a[0], b[1])), a])


@sketch_entity
def skArc(sk, d):
    options(d, ("start", "mid", "end"))
    curve = GC_MakeArcOfCircle(*[sk.plane.point(d[k]) for k in ("start", "mid", "end")]).Value()
    return [BRepBuilderAPI_MakeEdge(curve).Edge()]


@sketch_entity
def skText(sk, d):
    options(
        d,
        ("text", "fontName", "firstCorner", "secondCorner"),
        ("mirrorHorizontal", "mirrorVertical"),
    )
    if not isinstance(d["text"], str) or not d["text"].strip():
        raise RuntimeErrorFS("Text needs visible characters")
    if "\n" in d["text"]:
        raise Unsupported("Multiline sketch text is not implemented")
    path = sk.context.fonts.get(d["fontName"])
    if path is None:
        raise Unsupported(f"Font {d['fontName']!r} needs an explicit --fonts mapping")
    path = Path(path).resolve()
    font = StdPrs_BRepFont()
    if not font.Init(NCollection_Utf8String(str(path)), 1.0, 0):
        raise RuntimeErrorFS(f"Cannot load font {path}")
    shape = StdPrs_BRepTextBuilder().Perform(font, NCollection_Utf8String(d["text"]))
    lo, hi = bounds(shape)
    a, b = xyz(d["firstCorner"], size=2), xyz(d["secondCorner"], size=2)
    height = abs(b[1] - a[1])
    if height <= TOL or abs(b[0] - a[0]) <= TOL or hi[1] - lo[1] <= TOL:
        raise RuntimeErrorFS("Text rectangle must have positive width and height")
    scale = height / (hi[1] - lo[1])
    sx = -scale if boolean(d.get("mirrorHorizontal", False)) else scale
    sy = -scale if boolean(d.get("mirrorVertical", False)) else scale
    left = min(a[0], b[0]) if sx > 0 else max(a[0], b[0])
    bottom = min(a[1], b[1]) if sy > 0 else max(a[1], b[1])
    pose = gp_GTrsf(
        gp_Mat(sx, 0, 0, 0, sy, 0, 0, 0, scale), gp_XYZ(left - sx * lo[0], bottom - sy * lo[1], 0)
    )
    shape = transformed_shape(shape, pose)
    x, y, n, o = (
        xyz(sk.plane.x, (0, 0)),
        xyz(sk.plane.y, (0, 0)),
        xyz(sk.plane.normal, (0, 0)),
        xyz(sk.plane.origin),
    )
    place = gp_Trsf()
    place.SetValues(*[v for i in range(3) for v in (x[i], y[i], n[i], o[i])])
    shape = transformed_shape(shape, place)
    if not valid(shape):
        raise RuntimeErrorFS("Font outlines produced invalid geometry")
    record = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "kind": "font",
    }
    if record not in sk.context.assets:
        sk.context.assets.append(record)
    return [TopoDS.Edge_s(e) for e in members(shape, "EDGE")]


def endpoints(edge):
    return (BRep_Tool.Pnt_s(TopExp.FirstVertex_s(edge)), BRep_Tool.Pnt_s(TopExp.LastVertex_s(edge)))


def connected_wires(edges):
    """Join exact edges using tolerance only for endpoint connectivity."""
    from itertools import product

    nodes, buckets, adjacency, endpoints_by_edge = [], {}, {}, []
    for index, edge in enumerate(edges):
        pair = []
        for point in endpoints(edge):
            cell = tuple(math.floor(x / TOL) for x in point.Coord())
            matches = [
                n
                for offset in product((-1, 0, 1), repeat=3)
                for n in buckets.get(tuple(a + b for a, b in zip(cell, offset)), [])
                if nodes[n].Distance(point) <= TOL
            ]
            if len(matches) > 1:
                raise Unsupported("Ambiguous sketch endpoint connectivity")
            node = matches[0] if matches else len(nodes)
            if not matches:
                nodes.append(point)
                buckets.setdefault(cell, []).append(node)
                adjacency[node] = []
            adjacency[node].append(index)
            pair.append(node)
        endpoints_by_edge.append(pair)
    if any(len(es) > 2 for es in adjacency.values()):
        raise Unsupported("Branched sketch paths require a planar arrangement solver")
    remaining, wires = set(range(len(edges))), []
    while remaining:
        first = min(remaining)
        # Prefer an open endpoint in this component, independent of input order.
        component, todo = set(), [first]
        while todo:
            edge = todo.pop()
            if edge in component:
                continue
            component.add(edge)
            todo.extend(
                e for n in endpoints_by_edge[edge] for e in adjacency[n] if e not in component
            )
        candidates = [
            n for e in sorted(component) for n in endpoints_by_edge[e] if len(adjacency[n]) == 1
        ]
        start = candidates[0] if candidates else endpoints_by_edge[first][0]
        current, wire = start, BRepBuilderAPI_MakeWire()
        while True:
            next_edges = [e for e in adjacency[current] if e in remaining]
            if not next_edges:
                break
            index = next_edges[0]
            a, b = endpoints_by_edge[index]
            edge = edges[index] if current == a else TopoDS.Edge_s(edges[index].Reversed())
            wire.Add(edge)
            if not wire.IsDone():
                raise RuntimeErrorFS("Cannot connect sketch edges")
            remaining.remove(index)
            current = b if current == a else a
        wires.append((wire.Wire(), current == start))
    return wires


def skSolve(sk):
    if not isinstance(sk, Sketch) or sk.faces is not None:
        raise RuntimeErrorFS("Expected an unsolved sketch")
    if not sk.edges:
        raise RuntimeErrorFS("Empty sketch")
    faces = []
    for wire, closed in connected_wires(sk.edges):
        if not closed:
            continue
        face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Ax3(sk.plane.axis())), wire, True).Face()
        if not valid(face) or area(face) <= TOL**2:
            raise RuntimeErrorFS("Sketch loop is invalid or has zero area")
        faces.append(face)
    sizes, containers = [area(f) for f in faces], [set() for _ in faces]
    for i, face in enumerate(faces):
        for j in range(i):
            common = boolean_shape(face, faces[j], "INTERSECTION")
            overlap = area(common)
            if overlap <= TOL**2:
                continue
            inner, outer = (i, j) if sizes[i] < sizes[j] else (j, i)
            if not math.isclose(overlap, sizes[inner], rel_tol=1e-10, abs_tol=TOL**2):
                raise Unsupported("Intersecting sketch loops require a planar arrangement solver")
            separation = BRepExtrema_DistShapeShape(
                members(faces[inner], "WIRE")[0], members(faces[outer], "WIRE")[0]
            )
            if not separation.IsDone() or separation.Value() <= TOL:
                raise Unsupported(
                    "Touching or duplicate sketch loops require a planar arrangement solver"
                )
            containers[inner].add(outer)
    parents = [min(cs, key=lambda i: sizes[i]) if cs else None for cs in containers]
    regions, outer_regions = [], []
    for i, face in enumerate(faces):
        region = face
        for j, parent in enumerate(parents):
            if parent == i:
                region = boolean_shape(region, faces[j], "SUBTRACTION")
        parts = members(region, "FACE")
        regions.extend(parts)
        if parents[i] is None:
            outer_regions.extend(parts)
    sk.faces, sk.outer_faces = regions, outer_regions


@operation
def opSweep(c, id, d):
    options(d, ("profiles", "path"), ("keepProfileOrientation",))
    if boolean(d.get("keepProfileOrientation", False)):
        raise Unsupported("Fixed-orientation sweeps are not implemented")
    path, profiles = resolve(c, d["path"]), resolve(c, d["profiles"])
    if not path or any(e.kind != "EDGE" for e in path):
        raise RuntimeErrorFS("Sweep path needs edges")
    wires = connected_wires([TopoDS.Edge_s(e.shape) for e in path])
    if len(wires) != 1:
        raise RuntimeErrorFS("Sweep path must be connected")
    if not profiles or any(e.kind != "FACE" for e in profiles):
        raise Unsupported("Sweep currently needs face profiles")
    for profile in profiles:
        maker = BRepOffsetAPI_MakePipe(wires[0][0], profile.shape)
        if not maker.IsDone() or not c.add(maker.Shape(), {id}):
            raise RuntimeErrorFS("Sweep did not produce a valid solid")


@operation
def opExtrude(c, id, d):
    options(d, ("entities", "direction", "endBound", "endDepth"), ("startBound", "startDepth"))
    if enum_value(d["endBound"], "BoundingType") != "BLIND":
        raise Unsupported("opExtrude supports only BLIND bounds")
    if "startBound" in d and enum_value(d["startBound"], "BoundingType") != "BLIND":
        raise Unsupported("opExtrude supports only BLIND start bounds")
    if "startDepth" in d or "startBound" in d:
        raise Unsupported("Two-sided extrusions are not implemented")
    direction = xyz(normalize(d["direction"]), (0, 0))
    depth = positive(d["endDepth"])
    entities = resolve(c, d["entities"])
    if not entities or any(e.kind != "FACE" for e in entities):
        raise RuntimeErrorFS("opExtrude needs faces/sketch regions")
    for e in entities:
        shape = BRepPrimAPI_MakePrism(e.shape, gp_Vec(*[x * depth for x in direction])).Shape()
        if not c.add(shape, {id}):
            raise RuntimeErrorFS("Extrusion did not produce a solid")


def boolean_shape(a, b, mode, history=None):
    maker = {
        "UNION": BRepAlgoAPI_Fuse,
        "SUBTRACTION": BRepAlgoAPI_Cut,
        "INTERSECTION": BRepAlgoAPI_Common,
    }[mode]()
    arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    arguments.Append(a)
    tools.Append(b)
    maker.SetArguments(arguments)
    maker.SetTools(tools)
    # The two-shape constructor builds immediately, before these controls can be
    # set, and a later Build would repeat that entire computation.
    maker.SetNonDestructive(True)
    maker.Build()
    if not maker.IsDone():
        raise RuntimeErrorFS(f"OpenCascade {mode} failed")
    raw = maker.Shape()
    # OCCT 7.9 can mutate even a safe-input unifier's source when unification
    # fails. Isolate this optional pass from the boolean and its input bodies.
    copy = BRepBuilderAPI_Copy(raw, True, False)
    candidate = copy.Shape()
    simplify = ShapeUpgrade_UnifySameDomain(candidate, True, True, False)
    simplify.SetSafeInputMode(True)
    simplify.Build()
    shape = simplify.Shape()
    if not valid(shape):
        # Same-domain simplification is optional. OCCT can invalidate an otherwise
        # correct boolean while merging coplanar faces; retain its exact raw B-rep.
        if valid(raw):
            if history is not None:
                history.append((maker.History(), True))
            return raw
        raise RuntimeErrorFS(f"Invalid boolean result ({mode})")
    if history is not None:
        history.extend([(maker.History(), True), (copy, False), (simplify.History(), True)])
    return shape


@operation
def opBoolean(c, id, d):
    options(d, ("tools", "operationType"), ("targets", "keepTools", "targetsAndToolsNeedGrouping"))
    if boolean(d.get("targetsAndToolsNeedGrouping", False)):
        raise Unsupported("Grouped boolean tools/targets are not implemented")
    mode = enum_value(d["operationType"], "BooleanOperationType")
    tools = bodies(c, d["tools"])
    keep = boolean(d.get("keepTools", False))
    if mode == "SUBTRACTION":
        if "targets" not in d:
            raise RuntimeErrorFS("SUBTRACTION needs targets")
        targets = bodies(c, d["targets"])
        if {b.key for b in targets} & {b.key for b in tools}:
            raise RuntimeErrorFS("A boolean body cannot be both target and tool")
        for target in targets:
            shape = target.shape
            faces = target.faces
            for tool in tools:
                history = []
                shape = boolean_shape(shape, tool.shape, mode, history)
                faces = remap_faces(shape, faces + tool.faces, history, id)
            replace_body(c, target, shape, id, faces=faces)
        if not keep:
            for tool in tools:
                c.bodies.pop(tool.key)
    elif mode in ("UNION", "INTERSECTION"):
        if "targets" in d or keep:
            raise Unsupported("UNION/INTERSECTION use tools only, without keepTools")
        shape = tools[0].shape
        faces = contributing_faces(tools[0])
        for b in tools[1:]:
            history = []
            shape = boolean_shape(shape, b.shape, mode, history)
            faces = remap_faces(shape, faces + contributing_faces(b), history, id)
        for b in tools:
            c.bodies.pop(b.key)
        # A disjoint union must not make qCreatedBy(a) select unrelated body b.
        # Attribute each output solid only to inputs contributing volume to it.
        parts = members(shape, "SOLID")
        part_sources = [
            set().union(*(f.contributors for f in select_faces(part, faces))) for part in parts
        ]
        if len(parts) > 1 and mode == "UNION":
            represented = set().union(*part_sources)
            # Face history identifies which input solid belongs to each disconnected
            # output, even after the private geometry copy. Re-intersecting an exact
            # copied solid can incorrectly produce an empty Common in OCCT 7.9.
            # Fully enclosed tools leave no boundary faces; only these need a
            # geometric attribution fallback.
            for b in tools:
                if b.key not in represented:
                    for part, sources in zip(parts, part_sources):
                        if volume(boolean_shape(part, b.shape, "INTERSECTION")) > TOL**3:
                            sources.add(b.key)
            if set().union(*part_sources) != {b.key for b in tools}:
                raise RuntimeErrorFS("Cannot attribute all union inputs to output bodies")
        for part, sources in zip(parts, part_sources):
            # Every operand contributes to a connected union or an intersection.
            # Re-intersecting coincident faces solely to recover provenance is both
            # expensive and less robust than the original successful operation.
            contributors = (
                tools
                if len(parts) == 1 or mode == "INTERSECTION"
                else [b for b in tools if b.key in sources]
            )
            if not contributors:
                raise RuntimeErrorFS("Cannot attribute boolean result to source bodies")
            first = contributors[0]
            origins = set().union(*(b.origins for b in contributors)) | {id}
            if first.key not in c.bodies:
                c.bodies[first.key] = Body(
                    first.key,
                    part,
                    origins,
                    dict(clone(first.properties)),
                    first.revision + 1,
                    select_faces(part, faces),
                )
            else:
                c.add(part, origins, first.properties, first.revision + 1, faces=faces)
    else:
        raise Unsupported(f"Boolean mode {mode} is not implemented")


def replace_body(c, body, shape, id, origins=None, faces=None, history=()):
    shapes = members(shape, "SOLID")
    if not valid(shape):
        raise RuntimeErrorFS("Invalid modified body")
    if not shapes:
        c.bodies.pop(body.key)
        return
    origins = origins or (body.origins | {id})
    if faces is None:
        faces = remap_faces(shape, body.faces, history, id)
    c.bodies[body.key] = Body(
        body.key,
        shapes[0],
        origins,
        dict(clone(body.properties)),
        body.revision + 1,
        select_faces(shapes[0], faces),
    )
    for part in shapes[1:]:
        c.add(part, origins, body.properties, body.revision + 1, faces=faces)


@operation
def opDeleteBodies(c, id, d):
    options(d, ("entities",))
    entities = resolve(c, d["entities"])
    if any(e.kind != "BODY" for e in entities):
        raise RuntimeErrorFS("opDeleteBodies needs body entities")
    for e in entities:
        if isinstance(e.owner, int):
            c.bodies.pop(e.owner, None)
        else:
            c.sketches.pop(e.owner, None)


@operation
def opTransform(c, id, d):
    options(d, ("bodies", "transform"))
    if not isinstance(d["transform"], Transform):
        raise RuntimeErrorFS("Expected Transform")
    for b in bodies(c, d["bodies"]):
        history = []
        shape = transformed_shape(b.shape, d["transform"].value, history)
        replace_body(c, b, shape, id, history=history)


@operation
def opPattern(c, id, d):
    options(d, ("entities", "transforms", "instanceNames"))
    transforms, names = d["transforms"], d["instanceNames"]
    if len(transforms) != len(names) or len(set(names)) != len(names):
        raise RuntimeErrorFS("Pattern requires one unique instanceName per transform")
    source = bodies(c, d["entities"])
    for t, name in zip(transforms, names):
        if not isinstance(t, Transform) or not isinstance(name, str):
            raise RuntimeErrorFS("Invalid pattern transform/name")
        for b in source:
            history, instance_id = [], Id((*id, name))
            shape = transformed_shape(b.shape, t.value, history)
            faces = remap_faces(shape, b.faces, history, instance_id, reset=True)
            c.add(shape, {instance_id}, b.properties, faces=faces)


@operation
def opFillet(c, id, d):
    options(d, ("entities", "radius"), ("tangentPropagation",))
    propagate = boolean(d.get("tangentPropagation", True))
    radius = positive(d["radius"])
    groups = {}
    for e in resolve(c, d["entities"]):
        if e.kind != "EDGE" or not isinstance(e.owner, int):
            raise RuntimeErrorFS("opFillet needs solid-body edges")
        groups.setdefault(e.owner, []).append(e)
    if not groups:
        raise RuntimeErrorFS("Fillet query matched no edges")
    for owner, edges in groups.items():
        b = c.bodies[owner]
        fillet = BRepFilletAPI_MakeFillet(b.shape)
        for e in edges:
            fillet.Add(radius, TopoDS.Edge_s(e.shape))
        if not propagate:
            for contour in range(1, fillet.NbContours() + 1):
                for index in range(1, fillet.NbEdges(contour) + 1):
                    edge = fillet.Edge(contour, index)
                    if not any(edge.IsSame(e.shape) for e in edges):
                        raise Unsupported(
                            "OpenCascade would propagate the fillet to an unselected tangent edge"
                        )
        fillet.Build()
        if not fillet.IsDone():
            raise RuntimeErrorFS("OpenCascade could not build fillet")
        replace_body(c, b, fillet.Shape(), id, history=[(fillet, True)])


@operation
def opRevolve(c, id, d):
    options(d, ("entities", "axis", "angleForward"), ("angleBack",))
    if "angleBack" in d and scalar(d["angleBack"], ANGLE) != 0:
        raise Unsupported("Nonzero angleBack is not implemented")
    axis = d["axis"]
    if not isinstance(axis, Line):
        raise RuntimeErrorFS("Revolve axis must be Line")
    angle = scalar(d["angleForward"], ANGLE) % math.tau
    angle = angle if angle > 1e-12 else math.tau
    ax = gp_Ax1(gp_Pnt(*xyz(axis.origin)), gp_Dir(*xyz(axis.direction, (0, 0))))
    entities = resolve(c, d["entities"])
    if not entities or any(e.kind != "FACE" for e in entities):
        raise RuntimeErrorFS("opRevolve needs faces")
    for e in entities:
        if not c.add(BRepPrimAPI_MakeRevol(e.shape, ax, angle, True).Shape(), {id}):
            raise RuntimeErrorFS("Revolve produced no solid")


@operation
def opLoft(c, id, d):
    options(d, ("profileSubqueries",), ("bodyType",))
    if "bodyType" in d and enum_value(d["bodyType"], "BodyType") != "SOLID":
        raise Unsupported("Only solid lofts are supported")
    if len(d["profileSubqueries"]) < 2:
        raise RuntimeErrorFS("Loft needs at least two profiles")
    loft = BRepOffsetAPI_ThruSections(True, False, TOL)
    for q in d["profileSubqueries"]:
        entities = resolve(c, q)
        if len(entities) != 1 or entities[0].kind != "FACE":
            raise Unsupported("Each loft profile must select exactly one face")
        wires = members(entities[0].shape, "WIRE")
        if len(wires) != 1:
            raise Unsupported("Lofts with inner wires are not supported")
        loft.AddWire(TopoDS.Wire_s(wires[0]))
    loft.Build()
    if not loft.IsDone() or not c.add(loft.Shape(), {id}):
        raise RuntimeErrorFS("OpenCascade could not build solid loft")


def evaluateQuery(c, q):
    return [Query("transient", (e, c)) for e in resolve(c, q)]


def evVolume(c, d):
    options(d, ("entities",))
    return Quantity(sum(volume(b.shape) for b in bodies(c, d["entities"], True)) / 1e9, (3, 0))


def evBox3d(c, d):
    options(d, ("topology",), ("tight",))
    if "tight" in d:
        boolean(d["tight"])
    entities = resolve(c, d["topology"])
    if not entities:
        raise RuntimeErrorFS("Cannot bound an empty query")
    lo, hi = bounds(compound([e.shape for e in entities]))
    return {
        "minCorner": Vector(Quantity(x / 1000) for x in lo),
        "maxCorner": Vector(Quantity(x / 1000) for x in hi),
    }


def evArea(c, d):
    options(d, ("entities",))
    return Quantity(sum(area(e.shape) for e in resolve(c, d["entities"])) / 1e6, (2, 0))


def evLine(c, d):
    options(d, ("edge",))
    selected = resolve(c, d["edge"])
    if len(selected) != 1 or selected[0].kind != "EDGE":
        raise RuntimeErrorFS("evLine needs exactly one edge")
    curve = BRepAdaptor_Curve(TopoDS.Edge_s(selected[0].shape))
    if curve.GetType() != GeomAbs_Line:
        raise RuntimeErrorFS("Edge is not linear")
    value = curve.Line()
    return Line(
        Vector(Quantity(x / 1000) for x in value.Location().Coord()),
        Vector(value.Direction().Coord()),
    )


def geometry_type(entity):
    if entity.kind == "EDGE":
        kind = BRepAdaptor_Curve(TopoDS.Edge_s(entity.shape)).GetType()
        return {GeomAbs_Line: "LINE", GeomAbs_Circle: "CIRCLE", GeomAbs_Ellipse: "ELLIPSE"}.get(
            kind, "OTHER"
        )
    if entity.kind == "FACE":
        kind = BRepAdaptor_Surface(TopoDS.Face_s(entity.shape)).GetType()
        return {
            GeomAbs_Plane: "PLANE",
            GeomAbs_Cylinder: "CYLINDER",
            GeomAbs_Cone: "CONE",
            GeomAbs_Sphere: "SPHERE",
            GeomAbs_Torus: "TORUS",
            GeomAbs_BSplineSurface: "SPLINE",
            GeomAbs_BezierSurface: "SPLINE",
            GeomAbs_SurfaceOfExtrusion: "EXTRUDED",
            GeomAbs_SurfaceOfRevolution: "REVOLVED",
        }.get(kind, "OTHER")
    return "OTHER"


def evSurfaceDefinition(c, d):
    options(d, ("face",), ("returnBSplinesAsOther",))
    entities = resolve(c, d["face"])
    if not entities or entities[0].kind != "FACE":
        raise RuntimeErrorFS("Surface evaluation needs a face")
    entity = entities[0]
    surface = BRepAdaptor_Surface(TopoDS.Face_s(entity.shape))
    kind = geometry_type(entity)
    constructors = {
        "PLANE": surface.Plane,
        "CYLINDER": surface.Cylinder,
        "CONE": surface.Cone,
        "SPHERE": surface.Sphere,
        "TORUS": surface.Torus,
    }
    if kind not in constructors:
        if kind == "SPLINE" and not boolean(d.get("returnBSplinesAsOther", False)):
            if surface.GetType() != GeomAbs_BSplineSurface:
                raise Unsupported("Bezier surface descriptors are not implemented")
            spline = surface.BSpline()
            if spline.IsUPeriodic() or spline.IsVPeriodic():
                raise Unsupported("Periodic B-spline surface descriptors are not implemented")
            us, vs = range(1, spline.NbUPoles() + 1), range(1, spline.NbVPoles() + 1)
            rational = spline.IsURational() or spline.IsVRational()
            data = {
                "uDegree": spline.UDegree(),
                "vDegree": spline.VDegree(),
                "isUPeriodic": False,
                "isVPeriodic": False,
                "isRational": rational,
                "controlPoints": Tagged(
                    [
                        [Vector(Quantity(x / 1000) for x in spline.Pole(u, v).Coord()) for v in vs]
                        for u in us
                    ],
                    "ControlPointMatrix",
                ),
                "uKnots": Tagged(
                    [
                        spline.UKnot(i)
                        for i in range(1, spline.NbUKnots() + 1)
                        for _ in range(spline.UMultiplicity(i))
                    ],
                    "KnotArray",
                ),
                "vKnots": Tagged(
                    [
                        spline.VKnot(i)
                        for i in range(1, spline.NbVKnots() + 1)
                        for _ in range(spline.VMultiplicity(i))
                    ],
                    "KnotArray",
                ),
            }
            if rational:
                data["weights"] = Matrix(tuple(spline.Weight(u, v) for v in vs) for u in us)
            return Tagged(data, "BSplineSurface")
        return {"surfaceType": Tagged("OTHER" if kind == "SPLINE" else kind, "SurfaceType")}
    value = constructors[kind]()
    axes = value.Position()
    origin = Vector(Quantity(x / 1000) for x in axes.Location().Coord())
    normal, x = Vector(axes.Direction().Coord()), Vector(axes.XDirection().Coord())
    if kind == "PLANE":
        if entity.shape.Orientation() == TopAbs_REVERSED:
            normal = Vector(-v for v in normal)
        return Plane(origin, normal, x)
    if kind == "CONE":
        origin = Vector(Quantity(v / 1000) for v in value.Apex().Coord())
        # OCCT's signed half-angle determines which direction opens the cone.
        if value.SemiAngle() < 0:
            normal = Vector(-v for v in normal)
    result = {"coordSystem": CoordSystem(origin, x, normal)}
    if kind == "CONE":
        result["halfAngle"] = Quantity(abs(value.SemiAngle()), ANGLE)
    elif kind == "TORUS":
        result.update(
            radius=Quantity(value.MajorRadius() / 1000),
            minorRadius=Quantity(value.MinorRadius() / 1000),
        )
    else:
        result["radius"] = Quantity(value.Radius() / 1000)
    return Tagged(result, kind.title())


def evPlane(c, d):
    result = evSurfaceDefinition(c, d)
    if not isinstance(result, Plane):
        raise RuntimeErrorFS("Selected face is not planar")
    return result


def setProperty(c, d):
    options(d, ("entities", "propertyType", "value"))
    prop = enum_value(d["propertyType"], "PropertyType")
    if prop not in ("NAME", "APPEARANCE"):
        raise Unsupported(f"Property {prop} is not implemented")
    selected = resolve(c, d["entities"])
    if any(e.kind not in ("BODY", "FACE") or not isinstance(e.owner, int) for e in selected):
        raise Unsupported("Properties need solid bodies or their faces")
    if any(e.kind == "FACE" for e in selected) and prop != "APPEARANCE":
        raise Unsupported("Only appearance can be set on faces")
    if not selected:
        raise RuntimeErrorFS("Property query matched no entities")
    for e in selected:
        b = c.bodies[e.owner]
        if e.kind == "BODY":
            b.properties[prop] = clone(d["value"])
        else:
            record = next(f for f in b.faces if f.shape.IsSame(e.shape))
            record.properties[prop] = clone(d["value"])


def getProperty(c, d):
    options(d, ("entity", "propertyType"))
    selected = bodies(c, d["entity"])
    if len(selected) != 1:
        raise RuntimeErrorFS("getProperty needs one body")
    return clone(selected[0].properties.get(enum_value(d["propertyType"], "PropertyType")))


def export_step(c, path):
    if not c.bodies:
        raise RuntimeErrorFS("No solid bodies to export")
    path = Path(path)
    source = c.shape()
    originals = [b.shape for b in c.bodies.values()]
    source_volumes = [volume(s) for s in originals]
    original_volumes = sorted(source_volumes)
    original_bounds = bounds(source)
    split_indices = set()
    with tempfile.TemporaryDirectory(prefix="fsocct-step-", dir=path.parent) as folder:
        staged = Path(folder) / "model.step"
        for retry in (False, True):
            shape = source
            if retry:
                # STEP can lose the orientation of trimmed periodic faces that
                # are valid in memory. Split the closed faces of an export-only
                # deep copy; never run an in-place healer on the model itself.
                parts = list(originals)
                for index in split_indices:
                    copied = BRepBuilderAPI_Copy(parts[index], True, False).Shape()
                    splitter = ShapeUpgrade_ShapeDivideClosed(copied)
                    splitter.SetNbSplitPoints(1)
                    splitter.Perform()
                    parts[index] = splitter.Result()
                    if not valid(parts[index]):
                        raise RuntimeErrorFS("STEP closed-face splitting produced invalid geometry")
                shape = compound(parts)
            writer = STEPControl_Writer()
            if writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone:
                raise RuntimeErrorFS("STEP transfer failed")
            if writer.Write(str(staged)) != IFSelect_RetDone:
                raise RuntimeErrorFS("STEP write failed")
            reader = STEPControl_Reader()
            if reader.ReadFile(str(staged)) != IFSelect_RetDone or reader.TransferRoots() < 1:
                raise RuntimeErrorFS("STEP verification could not read the export")
            reloaded = reader.OneShape()
            solids = members(reloaded, "SOLID")
            if len(solids) != len(original_volumes):
                raise RuntimeErrorFS("STEP round trip changed the solid count")
            invalid = [s for s in solids if not valid(s)]
            if invalid:
                if not retry:
                    for failed in invalid:
                        failed_bounds, failed_volume = bounds(failed), volume(failed)
                        candidates = [
                            i
                            for i, original in enumerate(originals)
                            if math.isclose(
                                source_volumes[i], failed_volume, rel_tol=1e-5, abs_tol=1e-3
                            )
                            and all(
                                abs(a - b) <= 1e-3
                                for row_a, row_b in zip(bounds(original), failed_bounds)
                                for a, b in zip(row_a, row_b)
                            )
                        ]
                        if len(candidates) != 1:
                            raise RuntimeErrorFS(
                                "Cannot uniquely match an invalid STEP solid to its source"
                            )
                        split_indices.add(candidates[0])
                    continue
                raise RuntimeErrorFS("STEP round trip produced invalid or missing solids")
            exported_volumes = sorted(volume(s) for s in solids)
            if not all(
                math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-3)
                for a, b in zip(original_volumes, exported_volumes)
            ):
                raise RuntimeErrorFS("STEP round trip changed solid volumes beyond tolerance")
            if any(
                abs(a - b) > 1e-3
                for row_a, row_b in zip(original_bounds, bounds(reloaded))
                for a, b in zip(row_a, row_b)
            ):
                raise RuntimeErrorFS("STEP round trip changed model bounds beyond tolerance")
            staged.replace(path)
            return {
                "valid_solids": len(solids),
                "closed_faces_split": retry,
                "split_solid_count": len(split_indices),
                "volume_difference_mm3": sum(exported_volumes) - sum(original_volumes),
                "maximum_relative_solid_volume_difference": max(
                    abs(a - b) / a for a, b in zip(original_volumes, exported_volumes)
                ),
                "volume_relative_tolerance": 1e-5,
                "volume_absolute_tolerance_mm3": 1e-3,
                "bounds_tolerance_mm": 1e-3,
            }


def export_stl(c, path, tolerance=0.05):
    if not c.bodies:
        raise RuntimeErrorFS("No solid bodies to export")
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise RuntimeErrorFS("STL tolerance must be a positive number in mm")
    shape = c.shape()
    mesh = BRepMesh_IncrementalMesh(shape, tolerance, False, 0.15, False)
    if not mesh.IsDone():
        raise RuntimeErrorFS("STL meshing failed")
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(path)):
        raise RuntimeErrorFS("STL write failed")


def bindings():
    def enum(tag, names):
        return {n: Tagged(n, tag) for n in names.split()}

    entity_enum = enum("EntityType", "BODY FACE EDGE VERTEX")

    def entity_type(v):
        return enum_value(v, "EntityType")

    def created(id, typ=None):
        feature_id(id)
        if typ is None:
            raise Unsupported("qCreatedBy requires explicit EntityType in this runtime")
        return Query("created", (id, entity_type(typ)))

    def sketch_region(id, filter_inner=False):
        feature_id(id)
        boolean(filter_inner)
        return Query("sketch_region", (id, filter_inner))

    def body_type(q, typ):
        if enum_value(typ, "BodyType") != "SOLID":
            raise Unsupported("qBodyType supports SOLID only")
        return Query("solid_filter", (q,))

    def q_union(qs):
        if not isinstance(qs, list) or any(not isinstance(q, Query) for q in qs):
            raise RuntimeErrorFS("qUnion expects an array of queries")
        return Query("union", (tuple(qs),))

    return {
        "EntityType": entity_enum,
        "GeometryType": enum(
            "GeometryType",
            "LINE CIRCLE ELLIPSE PLANE CYLINDER CONE SPHERE TORUS OTHER SPLINE EXTRUDED REVOLVED",
        ),
        "SurfaceType": enum(
            "SurfaceType", "PLANE CYLINDER CONE SPHERE TORUS OTHER SPLINE EXTRUDED REVOLVED MESH"
        ),
        "BodyType": enum("BodyType", "SOLID SHEET WIRE POINT"),
        "BooleanOperationType": enum(
            "BooleanOperationType", "UNION SUBTRACTION INTERSECTION SUBTRACT_COMPLEMENT"
        ),
        "BoundingType": enum(
            "BoundingType", "BLIND SYMMETRIC UP_TO_SURFACE UP_TO_BODY THROUGH_ALL"
        ),
        "PropertyType": enum("PropertyType", "NAME APPEARANCE MATERIAL DESCRIPTION"),
        "newContext": Context,
        "newInstantiator": newInstantiator,
        "addInstance": addInstance,
        "instantiate": instantiate,
        "unstableIdComponent": lambda value: UnstableIdComponent("*" + str(value)),
        "makeId": lambda s: Id((s,)),
        "qCreatedBy": created,
        "qSketchRegion": sketch_region,
        "qEverything": lambda typ: Query("everything", (entity_type(typ),)),
        "qAllModifiableSolidBodies": lambda: Query("all_solids"),
        "qNothing": lambda: Query("nothing"),
        "qUnion": q_union,
        "qSubtraction": lambda a, b: Query("subtract", (a, b)),
        "qIntersection": lambda qs: query_intersection(qs),
        "qNthElement": lambda q, i: Query("nth", (q, i)),
        "qEntityFilter": lambda q, t: Query("filter", (q, entity_type(t))),
        "qGeometry": lambda q, t: Query("geometry", (q, enum_value(t, "GeometryType"))),
        "qContainsPoint": lambda q, p: Query("contains_point", (q, p)),
        "qBodyType": body_type,
        "qOwnedByBody": lambda q, t: Query("owned", (q, entity_type(t))),
        "qOwnerBody": lambda q: Query("owner", (q,)),
        "evaluateQuery": evaluateQuery,
        "isQueryEmpty": lambda c, q: not resolve(c, q),
        "evVolume": evVolume,
        "evBox3d": evBox3d,
        "evArea": evArea,
        "evLine": evLine,
        "evPlane": evPlane,
        "evSurfaceDefinition": evSurfaceDefinition,
        "fCuboid": fCuboid,
        "fCylinder": fCylinder,
        "plane": plane,
        "line": line,
        "transform": transform,
        "identityTransform": lambda: Transform(gp_Trsf()),
        "rotationAround": rotation_around,
        "mirrorAcross": mirror_across,
        "coordSystem": coord_system,
        "toWorld": to_world,
        "fromWorld": from_world,
        "inverse": lambda t: Transform(t.value.Inverted()),
        "newSketchOnPlane": newSketchOnPlane,
        "skLineSegment": skLineSegment,
        "skRectangle": skRectangle,
        "skCircle": skCircle,
        "skPolyline": skPolyline,
        "skArc": skArc,
        "skText": skText,
        "skSolve": skSolve,
        "opExtrude": opExtrude,
        "opSweep": opSweep,
        "opBoolean": opBoolean,
        "opDeleteBodies": opDeleteBodies,
        "opTransform": opTransform,
        "opPattern": opPattern,
        "opFillet": opFillet,
        "opRevolve": opRevolve,
        "opLoft": opLoft,
        "setProperty": setProperty,
        "getProperty": getProperty,
        "color": lambda r, g, b, a=1.0: Tagged(
            {
                "red": number(r),
                "green": number(g),
                "blue": number(b),
                "alpha": number(a),
            },
            "Color",
        ),
    }


def query_intersection(queries):
    if not queries:
        return Query("nothing")
    result = queries[0]
    for q in queries[1:]:
        result = Query("intersect", (result, q))
    return result
