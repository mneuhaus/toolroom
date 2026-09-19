"""Kollisionskern auf fcl-BVH-Modellen. Meshes werden nie prozessiert."""
from __future__ import annotations

import numpy as np

try:
    import fcl
except Exception as exc:  # pragma: no cover
    fcl = None
    _IMPORT_ERROR = exc


def bvh(mesh):
    """fcl.BVHModel je Mesh, gecacht am Mesh-Objekt."""
    cached = getattr(mesh, '_pruefstand_bvh', None)
    if cached is not None:
        return cached
    if fcl is None:  # pragma: no cover
        raise RuntimeError(f'python-fcl fehlt: {_IMPORT_ERROR}')
    m = fcl.BVHModel()
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    tris = np.asarray(mesh.faces, dtype=np.int64)
    m.beginModel(len(verts), len(tris))
    m.addSubModel(verts, tris)
    m.endModel()
    try:
        object.__setattr__(mesh, '_pruefstand_bvh', m)
    except Exception:  # pragma: no cover
        pass
    return m


def _obj(mesh):
    return fcl.CollisionObject(bvh(mesh), fcl.Transform())


def distance(mesh_a, mesh_b):
    """(d_mm, punkt_a, punkt_b). Bei Durchdringung d = 0.0."""
    req = fcl.DistanceRequest(enable_nearest_points=True)
    res = fcl.DistanceResult()
    d = fcl.distance(_obj(mesh_a), _obj(mesh_b), req, res)
    pa = np.asarray(res.nearest_points[0], dtype=float) if res.nearest_points is not None else None
    pb = np.asarray(res.nearest_points[1], dtype=float) if res.nearest_points is not None else None
    if d is None or d < 0:
        return 0.0, pa, pb
    return float(d), pa, pb


TOUCH_TOL_MM = 1e-4
"""Kontakte flacher als diese Schwelle sind Berührung, keine Durchdringung.
Tessellierte Flächen, die konstruktiv aufeinander liegen, liefern in fcl Tiefe 0.0;
echte Durchdringungen liegen um Größenordnungen darüber."""


def collide(mesh_a, mesh_b, max_contacts=64, tol=TOUCH_TOL_MM):
    """(anzahl_durchdringender_kontakte, max_eindringtiefe_mm, anzahl_beruehrungen)."""
    deep, depth, n, _ = collide_punkte(mesh_a, mesh_b, max_contacts, tol)
    return deep, depth, n


def collide_punkte(mesh_a, mesh_b, max_contacts=64, tol=TOUCH_TOL_MM):
    """Wie `collide`, zusätzlich die Kontaktorte in **Welt**koordinaten.

    „Kollidiert" ist eine Zahl, mit der niemand etwas anfangen kann; „kollidiert bei
    (111,3 / 128,5 / 233,8)" ist ein Ort, an dem man nachsehen kann. Die Punkte kosten
    nichts extra -- fcl liefert sie ohnehin mit, sie wurden bisher weggeworfen.
    """
    req = fcl.CollisionRequest(num_max_contacts=max_contacts, enable_contact=True)
    res = fcl.CollisionResult()
    n = fcl.collide(_obj(mesh_a), _obj(mesh_b), req, res)
    depth = 0.0
    deep = 0
    punkte = []
    for c in res.contacts:
        d = abs(float(c.penetration_depth))
        depth = max(depth, d)
        if d > tol:
            deep += 1
            punkte.append([round(float(x), 4) for x in np.asarray(c.pos, dtype=float)])
    return deep, depth, int(n), punkte


def watertight(mesh) -> bool:
    return bool(mesh.is_watertight)
