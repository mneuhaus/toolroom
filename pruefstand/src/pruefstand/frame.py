"""Frame: starre Lage (world = R @ local + t)."""
from __future__ import annotations

import math

import numpy as np


class Frame:
    __slots__ = ('rotation', 'translation')

    def __init__(self, rotation, translation=(0.0, 0.0, 0.0)):
        self.rotation = np.asarray(rotation, dtype=float).reshape(3, 3)
        self.translation = np.asarray(translation, dtype=float).reshape(3)

    # -- Konstruktoren ---------------------------------------------------
    @classmethod
    def identity(cls) -> "Frame":
        return cls(np.eye(3), (0.0, 0.0, 0.0))

    @classmethod
    def _rot(cls, axis, deg, translation):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        if axis == 'x':
            r = [[1, 0, 0], [0, c, -s], [0, s, c]]
        elif axis == 'y':
            r = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
        else:
            r = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        return cls(r, translation)

    @classmethod
    def rot_x(cls, deg, translation=(0, 0, 0)) -> "Frame":
        return cls._rot('x', deg, translation)

    @classmethod
    def rot_y(cls, deg, translation=(0, 0, 0)) -> "Frame":
        return cls._rot('y', deg, translation)

    @classmethod
    def rot_z(cls, deg, translation=(0, 0, 0)) -> "Frame":
        return cls._rot('z', deg, translation)

    @classmethod
    def from_axis(cls, axis, origin=(0, 0, 0)) -> "Frame":
        """Frame mit `axis` als lokaler Z-Richtung; X/Y beliebig, aber rechtshändig.

        Für Fenster an einer Fläche: die Normale ist vorgegeben, wie das Fenster in der
        Ebene gedreht liegt, ist gleichgültig. Der Hilfsvektor wird nach der kleinsten
        Komponente von `axis` gewählt, damit das Kreuzprodukt nie entartet.
        """
        z = np.asarray(axis, dtype=float).reshape(3)
        n = float(np.linalg.norm(z))
        if n < 1e-12:
            raise ValueError('Frame.from_axis: Achse hat Länge 0')
        z = z / n
        hilfe = np.zeros(3)
        hilfe[int(np.argmin(np.abs(z)))] = 1.0
        x = np.cross(hilfe, z)
        x = x / float(np.linalg.norm(x))
        y = np.cross(z, x)
        return cls(np.column_stack([x, y, z]), origin)

    # -- Abbildung -------------------------------------------------------
    def to_world(self, pts):
        p = np.asarray(pts, dtype=float)
        single = p.ndim == 1
        p = np.atleast_2d(p)
        out = p @ self.rotation.T + self.translation
        return out[0] if single else out

    def to_local(self, pts):
        p = np.asarray(pts, dtype=float)
        single = p.ndim == 1
        p = np.atleast_2d(p)
        out = (p - self.translation) @ self.rotation
        return out[0] if single else out

    def direction_to_world(self, vec):
        return self.rotation @ np.asarray(vec, dtype=float).reshape(3)

    def direction_to_local(self, vec):
        """Richtung von Welt nach lokal -- die Umkehrung von `direction_to_world`.

        Eine Richtung wird ohne die Verschiebung gedreht; `to_local` zöge sie ab und
        machte aus einer Normalen einen Punkt. Bisher musste jeder Aufrufer selbst
        `rotation.T @ v` schreiben (so in `t41_details.py`), und wer es vergisst,
        bekommt für eine Normale einen Ortsvektor zurück, ohne dass etwas auffällt.
        """
        return self.rotation.T @ np.asarray(vec, dtype=float).reshape(3)

    def matrix(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = self.rotation
        m[:3, 3] = self.translation
        return m

    def inverse_matrix(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = self.rotation.T
        m[:3, 3] = -self.rotation.T @ self.translation
        return m

    def as_dict(self) -> dict:
        return {'rotation': self.rotation.tolist(), 'translation': self.translation.tolist()}

    @classmethod
    def from_dict(cls, d) -> "Frame":
        return cls(d['rotation'], d.get('translation', (0, 0, 0)))

    def __repr__(self):
        return f'Frame(t={np.round(self.translation, 3).tolist()})'
