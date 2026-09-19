"""Punkt-zu-Oberfläche-Abstand für viele Punkte, exakt.

`trimesh.proximity` ist exakt, läuft aber je Punkt durch Python: bei den hier üblichen
100k+ Abtastpunkten sind das Minuten (gemessen 0,46 ms/Punkt). Ein KD-Baum über
Dreiecks-Schwerpunkte ist kein Ersatz -- die Maschinen-STLs haben Dreiecke bis 25 mm
Kantenlänge, und die k nächsten Schwerpunkte gehören dann oft zu einem dichten Splitter-
Nest nebenan statt zur wirklich nächsten großen Fläche (gemessen: Schranke 0,58 mm statt
0,0005 mm bei k=16 auf fein unterteilten Dreiecken).

Deshalb VTKs `vtkStaticCellLocator`: ein echter Zell-Baum in C++, 12 µs/Punkt. Der
gefundene Zellindex wird anschließend nochmal exakt in numpy nachgerechnet
(Punkt-Dreieck nach Ericson), damit der zurückgegebene Wert garantiert ein echter
Abstand zu einem existierenden Dreieck ist und nicht die toleranzbehaftete Zahl des
Lokalisierers (der Unterschied lag bei 1e-6 mm, aber nur die nachgerechnete Zahl kann
nicht zu klein sein).

Die Meshes dürfen offen (nicht wasserdicht) sein; gemessen wird nur die Oberfläche,
kein Vorzeichen.
"""
from __future__ import annotations

import numpy as np


def _closest_on_triangles(p, a, b, c):
    """p, a, b, c: (M,3) -> (M,3) nächster Punkt im Dreieck."""
    ab = b - a
    ac = c - a
    ap = p - a
    d1 = np.einsum('ij,ij->i', ab, ap)
    d2 = np.einsum('ij,ij->i', ac, ap)
    bp = p - b
    d3 = np.einsum('ij,ij->i', ab, bp)
    d4 = np.einsum('ij,ij->i', ac, bp)
    cp = p - c
    d5 = np.einsum('ij,ij->i', ab, cp)
    d6 = np.einsum('ij,ij->i', ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    with np.errstate(divide='ignore', invalid='ignore'):
        inv = np.where(np.abs(denom) > 1e-300, 1.0 / denom, 0.0)
        v = vb * inv
        w = vc * inv
        out = a + ab * v[:, None] + ac * w[:, None]
        # Kanten und Ecken (in umgekehrter Priorität überschreiben)
        t = np.where(np.abs(d4 - d3 + d5 - d6) > 1e-300, (d4 - d3) / (d4 - d3 + d5 - d6), 0.0)
        m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        out = np.where(m[:, None], b + (c - b) * np.clip(t, 0, 1)[:, None], out)
        t = np.where(np.abs(d2 - d6) > 1e-300, d2 / (d2 - d6), 0.0)
        m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        out = np.where(m[:, None], a + ac * np.clip(t, 0, 1)[:, None], out)
        t = np.where(np.abs(d1 - d3) > 1e-300, d1 / (d1 - d3), 0.0)
        m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        out = np.where(m[:, None], a + ab * np.clip(t, 0, 1)[:, None], out)
    out = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, out)
    out = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, out)
    out = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, out)
    return out


def _polydata(mesh, vtk, ns):
    pts = vtk.vtkPoints()
    pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(mesh.vertices, dtype=np.float64), deep=True))
    faces = np.asarray(mesh.faces, dtype=np.int64)
    flat = np.hstack([np.full((len(faces), 1), 3, dtype=np.int64), faces]).ravel()
    cells = vtk.vtkCellArray()
    cells.SetCells(len(faces), ns.numpy_to_vtkIdTypeArray(flat, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    return pd


def _locator(mesh):
    """(vtkStaticCellLocator, Dreiecke) für das Mesh, am Mesh gecacht. None ohne VTK."""
    cached = getattr(mesh, '_pruefstand_locator', None)
    if cached is not None:
        return cached
    try:
        import vtk
        from vtk.util import numpy_support as ns
    except Exception:  # pragma: no cover -- VTK kommt über build123d mit
        return None
    loc = vtk.vtkStaticCellLocator()
    loc.SetDataSet(_polydata(mesh, vtk, ns))
    loc.BuildLocator()
    entry = (loc, np.asarray(mesh.triangles, dtype=float))
    try:
        object.__setattr__(mesh, '_pruefstand_locator', entry)
    except Exception:  # pragma: no cover
        pass
    return entry


def distances(points, mesh) -> np.ndarray:
    """Kleinster Abstand jedes Punktes zur Mesh-Oberfläche in mm, exakt."""
    points = np.asarray(points, dtype=float)
    if len(points) == 0:
        return np.zeros(0)
    if mesh is None or len(mesh.faces) == 0:
        return np.full(len(points), np.inf)
    entry = _locator(mesh)
    if entry is None:  # pragma: no cover -- Notnagel ohne VTK: exakt, aber langsam
        import trimesh
        return np.asarray(trimesh.proximity.ProximityQuery(mesh).on_surface(points)[1], dtype=float)
    import vtk
    loc, tri = entry
    cell = vtk.vtkGenericCell()
    closest = [0.0, 0.0, 0.0]
    cid = vtk.reference(0)
    sub = vtk.reference(0)
    dist2 = vtk.reference(0.0)
    ids = np.empty(len(points), dtype=np.int64)
    for i in range(len(points)):
        loc.FindClosestPoint(points[i], closest, cell, cid, sub, dist2)
        ids[i] = int(cid)
    # Den gefundenen Treffer selbst nachrechnen: nur so ist der Wert garantiert der
    # Abstand zu einem echten Dreieck (und damit nie zu klein).
    ok = ids >= 0
    out = np.full(len(points), np.inf)
    t = tri[ids[ok]]
    p = points[ok]
    q = _closest_on_triangles(p, t[:, 0], t[:, 1], t[:, 2])
    out[ok] = np.linalg.norm(q - p, axis=1)
    if not ok.all():  # pragma: no cover -- Lokalisierer hat nichts gefunden
        import trimesh
        out[~ok] = np.asarray(trimesh.proximity.ProximityQuery(mesh).on_surface(points[~ok])[1], dtype=float)
    return out
