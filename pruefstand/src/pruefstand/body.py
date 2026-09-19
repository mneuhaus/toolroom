"""Body / Parts: ein Körper aus STEP (exakt) oder STL (Mesh)."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import numpy as np

from . import context
from .frame import Frame

_STL_TOL = 0.01
_STL_ANG = 0.1


def _safe(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', str(name))[:120] or 'body'


class Body:
    """Ein starrer Körper. Längen in mm."""

    def __init__(self, key, name=None, solid=None, mesh=None, moving=False, source=None, role=None):
        if solid is None and mesh is None:
            raise ValueError('Body braucht solid oder mesh')
        self.key = str(key)
        self.name = str(name) if name is not None else str(key)
        self.solid = solid
        self._mesh = mesh
        self.moving = bool(moving)
        self.source = Path(source) if source is not None else None
        self.role = role
        self.displaced = False

    # -- Geometrie -------------------------------------------------------
    @property
    def mesh(self):
        if self._mesh is None:
            import trimesh
            from build123d import export_stl
            rev = context.review_dir()
            if rev is not None:
                out = Path(rev) / f'{_safe(self.key)}.stl'
            else:
                out = Path(tempfile.gettempdir()) / f'pruefstand-{_safe(self.key)}-{id(self):x}.stl'
            out.parent.mkdir(parents=True, exist_ok=True)
            export_stl(self.solid, str(out), tolerance=_STL_TOL, angular_tolerance=_STL_ANG)
            self._mesh = trimesh.load_mesh(out, process=False)
        return self._mesh

    @property
    def has_mesh(self) -> bool:
        return self._mesh is not None

    @property
    def volume_mm3(self) -> float:
        if self.solid is not None:
            return float(self.solid.volume)
        return float(abs(self.mesh.volume))

    @property
    def watertight(self) -> bool:
        return bool(self.mesh.is_watertight)

    def vertices(self, frame: Frame | None = None) -> np.ndarray:
        v = np.asarray(self.mesh.vertices, dtype=float)
        return v if frame is None else frame.to_local(v)

    def bounds(self, frame: Frame | None = None):
        v = self.vertices(frame)
        return v.min(axis=0), v.max(axis=0)

    # -- Bewegen ---------------------------------------------------------
    def _copy_with(self, solid, mesh):
        b = Body(self.key, self.name, solid=solid, mesh=mesh, moving=self.moving, source=self.source, role=self.role)
        b.displaced = self.displaced
        return b

    def translated(self, delta_world) -> "Body":
        d = np.asarray(delta_world, dtype=float).reshape(3)
        if not np.any(d):
            return self._copy_with(self.solid, self._mesh)
        solid = None
        if self.solid is not None:
            from build123d import Location
            solid = self.solid.moved(Location((float(d[0]), float(d[1]), float(d[2]))))
        mesh = None
        if self._mesh is not None:
            mesh = self._mesh.copy()
            mesh.apply_translation(d)
        elif solid is None:
            mesh = self.mesh.copy()
            mesh.apply_translation(d)
        return self._copy_with(solid, mesh)

    def moved(self, frame: Frame, delta) -> "Body":
        """Kopie, um `delta` im Frame verschoben (Welt-Delta = R @ delta)."""
        return self.translated(frame.direction_to_world(delta))

    def transformed(self, matrix) -> "Body":
        m = np.asarray(matrix, dtype=float).reshape(4, 4)
        solid = None
        if self.solid is not None:
            from build123d import Matrix
            solid = self.solid.transform_geometry(Matrix([[float(m[i][j]) for j in range(4)] for i in range(4)]))
        mesh = None
        if self._mesh is not None:
            mesh = self._mesh.copy()
            mesh.apply_transform(m)
        elif solid is None:
            mesh = self.mesh.copy()
            mesh.apply_transform(m)
        return self._copy_with(solid, mesh)

    def __repr__(self):
        kind = 'solid' if self.solid is not None else 'mesh'
        return f'Body({self.key!r}, {kind}, moving={self.moving})'


class Parts:
    """Sammlung von Bodies aus einer Quelle."""

    def __init__(self, bodies, source=None):
        self._bodies = list(bodies)
        self.source = Path(source) if source is not None else None

    def all(self) -> list[Body]:
        return list(self._bodies)

    def keys(self) -> list[str]:
        return [b.key for b in self._bodies]

    def __len__(self):
        return len(self._bodies)

    def __iter__(self):
        return iter(self._bodies)

    def __getitem__(self, key):
        for b in self._bodies:
            if b.key == key:
                return b
        raise KeyError(f'{key!r} nicht in {self.keys()}')

    def one(self, key=None, moving=None) -> Body:
        if len(self._bodies) != 1:
            raise ValueError(f'erwartet genau einen Körper, gefunden {len(self._bodies)}: {self.keys()}')
        b = self._bodies[0]
        if key is not None:
            b.key = str(key)
        if moving is not None:
            b.moving = bool(moving)
        return b

    def find_all(self, substring) -> list[Body]:
        s = str(substring).lower()
        return [b for b in self._bodies if s in b.key.lower() or s in b.name.lower()]

    def find(self, substring) -> Body:
        hits = self.find_all(substring)
        if len(hits) != 1:
            raise ValueError(f'{substring!r} trifft {len(hits)} Körper: {[h.key for h in hits]} '
                             f'(vorhanden: {self.keys()})')
        return hits[0]

    def __repr__(self):
        return f'Parts({len(self._bodies)}: {self.keys()})'


def load_step(path, moving=False) -> Parts:
    """STEP laden; ein Body je Solid, key = STEP-Produktname."""
    from build123d import import_step
    path = Path(path)
    shape = import_step(str(path))
    bodies = []
    children = list(getattr(shape, 'children', []) or [])
    if children:
        for ch in children:
            for i, so in enumerate(ch.solids()):
                label = getattr(ch, 'label', '') or f'{path.stem}_{i}'
                key = label if len(ch.solids()) == 1 else f'{label}#{i}'
                bodies.append(Body(key, label, solid=so, moving=moving, source=path))
    else:
        solids = shape.solids()
        label = getattr(shape, 'label', '') or path.stem
        if len(solids) == 1:
            bodies.append(Body(label or path.stem, label, solid=solids[0], moving=moving, source=path))
        else:
            for i, so in enumerate(solids):
                bodies.append(Body(f'{label or path.stem}#{i}', label, solid=so, moving=moving, source=path))
    return Parts(bodies, source=path)


def load_mesh(path, key=None, moving=False) -> Body:
    import trimesh
    path = Path(path)
    m = trimesh.load_mesh(path, process=False)
    return Body(key or path.stem, key or path.stem, mesh=m, moving=moving, source=path)
