"""Druckprofil, Druckpose und der Lader für `spec/druck.yaml`.

`spec/druck.yaml` beschreibt je Druckteil die Druckpose und die Lastabschnitte::

    schema: pruefstand.druck/1
    teile:
      - key: T05
        pose: {rotate: [0, 0, 0]}
        profil: {waende: 3, infill: 0.25, duese: 0.42, schicht: 0.2}
        lastabschnitte:
          - name: Fuss
            ebene: {frame: local, punkt: [0, 0, 0], normale: [0, 0, 1]}
            richtung: [0, 1, 0]

Fehlerhafte Dateien werden laut und früh abgewiesen (`DruckSpecFehler`), nicht
stillschweigend auf Standardwerte zurückgefallen.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .frame import Frame

SCHEMA = 'pruefstand.druck/1'


class DruckSpecFehler(ValueError):
    """Die YAML-Pflegedatei ist kaputt. Immer mit Dateipfad und Schlüsselpfad melden."""


# ---------------------------------------------------------------- Profil ----
@dataclass(frozen=True)
class Profil:
    """Slicer-Profil, soweit der Prüfstand es braucht.

    waende  Anzahl der Wandlinien (Perimeter) je Seite
    infill  Füllgrad 0..1 im Kern
    duese   Extrusionsbreite einer Wandlinie in mm (Marcs Standard 0,42)
    schicht Schichthöhe in mm
    """

    waende: int = 3
    infill: float = 0.25
    duese: float = 0.42
    schicht: float = 0.2

    def __post_init__(self):
        if self.waende < 1:
            raise DruckSpecFehler(f'profil.waende muss >= 1 sein, ist {self.waende}')
        if not 0.0 <= self.infill <= 1.0:
            raise DruckSpecFehler(f'profil.infill muss zwischen 0 und 1 liegen, ist {self.infill}')
        if self.duese <= 0 or self.schicht <= 0:
            raise DruckSpecFehler(f'profil.duese/schicht müssen > 0 sein, sind {self.duese}/{self.schicht}')

    @property
    def wandstaerke_mm(self) -> float:
        """Gesamte Wanddicke einer Seite = Wandlinien × Düsenbreite."""
        return float(self.waende) * float(self.duese)

    @classmethod
    def from_dict(cls, d, wo='profil') -> "Profil":
        if d is None:
            return cls()
        if not isinstance(d, dict):
            raise DruckSpecFehler(f'{wo}: Abbildung erwartet, bekommen {type(d).__name__}')
        erlaubt = {'waende', 'infill', 'duese', 'schicht'}
        unbekannt = set(d) - erlaubt
        if unbekannt:
            raise DruckSpecFehler(f'{wo}: unbekannte Schlüssel {sorted(unbekannt)}, erlaubt {sorted(erlaubt)}')
        std = cls()
        try:
            return cls(waende=int(d.get('waende', std.waende)),
                       infill=float(d.get('infill', std.infill)),
                       duese=float(d.get('duese', std.duese)),
                       schicht=float(d.get('schicht', std.schicht)))
        except (TypeError, ValueError) as e:
            raise DruckSpecFehler(f'{wo}: Zahl erwartet ({e})') from None

    def as_dict(self) -> dict:
        return {'waende': self.waende, 'infill': self.infill, 'duese': self.duese, 'schicht': self.schicht}


STANDARD_PROFIL = Profil()


# ------------------------------------------------------------------ Pose ----
def pose_matrix(pose=None) -> np.ndarray:
    """Druckpose in eine 4x4-Matrix übersetzen.

    Akzeptiert None (wie modelliert), eine 4x4-Matrix, ein `Frame`, eine
    3x3-Rotation oder eine Abbildung ``{'rotate': [rx, ry, rz], 'translate': [...]}``
    mit Drehungen in Grad, nacheinander um X, dann Y, dann Z.
    """
    if pose is None:
        return np.eye(4)
    if isinstance(pose, Frame):
        return pose.matrix()
    if isinstance(pose, dict):
        erlaubt = {'rotate', 'translate'}
        unbekannt = set(pose) - erlaubt
        if unbekannt:
            raise DruckSpecFehler(f'pose: unbekannte Schlüssel {sorted(unbekannt)}, erlaubt {sorted(erlaubt)}')
        rot = _vec3(pose.get('rotate', (0, 0, 0)), 'pose.rotate')
        tra = _vec3(pose.get('translate', (0, 0, 0)), 'pose.translate')
        m = np.eye(4)
        for achse, winkel in zip('xyz', rot):
            if winkel:
                m = _rot4(achse, float(winkel)) @ m
        m[:3, 3] += tra
        return m
    a = np.asarray(pose, dtype=float)
    if a.shape == (4, 4):
        return a
    if a.shape == (3, 3):
        m = np.eye(4)
        m[:3, :3] = a
        return m
    raise DruckSpecFehler(f'pose: 4x4-Matrix, 3x3-Rotation, Frame oder dict erwartet, bekommen {a.shape}')


def _rot4(achse, grad) -> np.ndarray:
    a = math.radians(float(grad))
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4)
    if achse == 'x':
        m[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif achse == 'y':
        m[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    else:
        m[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    return m


def _vec3(v, wo) -> np.ndarray:
    a = np.asarray(v, dtype=float).ravel() if not isinstance(v, (str, bytes)) else None
    if a is None or a.size != 3 or not np.all(np.isfinite(a)):
        raise DruckSpecFehler(f'{wo}: drei endliche Zahlen erwartet, bekommen {v!r}')
    return a


# ---------------------------------------------------------- Lastabschnitt ----
@dataclass
class Lastabschnitt:
    """Ein Schnitt, an dem `stability()` rechnet."""

    name: str
    punkt: np.ndarray
    normale: np.ndarray
    richtung: np.ndarray
    frame: str = 'local'

    def als_ebene(self) -> tuple:
        return (self.punkt, self.normale)

    def as_dict(self) -> dict:
        return {'name': self.name, 'frame': self.frame,
                'punkt': self.punkt.tolist(), 'normale': self.normale.tolist(),
                'richtung': self.richtung.tolist()}


@dataclass
class Teilspec:
    key: str
    pose: object = None
    profil: Profil = STANDARD_PROFIL
    lastabschnitte: list = field(default_factory=list)

    def abschnitt(self, name) -> Lastabschnitt:
        for a in self.lastabschnitte:
            if a.name == name:
                return a
        raise KeyError(f'Lastabschnitt {name!r} nicht in {self.key}: '
                       f'{[a.name for a in self.lastabschnitte]}')

    def pose_matrix(self) -> np.ndarray:
        return pose_matrix(self.pose)


@dataclass
class DruckSpec:
    pfad: Path
    teile: dict

    def __getitem__(self, key) -> Teilspec:
        try:
            return self.teile[str(key)]
        except KeyError:
            raise KeyError(f'Teil {key!r} nicht in {self.pfad}: {sorted(self.teile)}') from None

    def __contains__(self, key):
        return str(key) in self.teile

    def __len__(self):
        return len(self.teile)

    def keys(self):
        return list(self.teile)


def lade_druck_spec(path) -> DruckSpec:
    """`spec/druck.yaml` laden und streng prüfen."""
    import yaml

    path = Path(path)
    if not path.exists():
        raise DruckSpecFehler(f'{path}: Datei fehlt')
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise DruckSpecFehler(f'{path}: kein gültiges YAML ({e})') from None
    if not isinstance(data, dict):
        raise DruckSpecFehler(f'{path}: Abbildung auf oberster Ebene erwartet, bekommen {type(data).__name__}')
    unbekannt = set(data) - {'schema', 'teile'}
    if unbekannt:
        raise DruckSpecFehler(f'{path}: unbekannte Schlüssel {sorted(unbekannt)}')
    if data.get('schema') != SCHEMA:
        raise DruckSpecFehler(f'{path}: schema muss {SCHEMA!r} sein, ist {data.get("schema")!r}')
    roh = data.get('teile')
    if not isinstance(roh, list) or not roh:
        raise DruckSpecFehler(f'{path}: teile muss eine nicht-leere Liste sein')

    teile = {}
    for i, t in enumerate(roh):
        wo = f'{path}: teile[{i}]'
        if not isinstance(t, dict):
            raise DruckSpecFehler(f'{wo}: Abbildung erwartet, bekommen {type(t).__name__}')
        unbekannt = set(t) - {'key', 'pose', 'profil', 'lastabschnitte'}
        if unbekannt:
            raise DruckSpecFehler(f'{wo}: unbekannte Schlüssel {sorted(unbekannt)}')
        key = t.get('key')
        if not isinstance(key, str) or not key.strip():
            raise DruckSpecFehler(f'{wo}: key fehlt oder ist leer')
        if key in teile:
            raise DruckSpecFehler(f'{wo}: key {key!r} doppelt')
        try:
            pose = t.get('pose')
            pose_matrix(pose)  # früh validieren
        except DruckSpecFehler as e:
            raise DruckSpecFehler(f'{wo}.{e}') from None
        profil = Profil.from_dict(t.get('profil'), wo=f'{wo}.profil')
        abschnitte = []
        for j, a in enumerate(t.get('lastabschnitte') or []):
            wa = f'{wo}.lastabschnitte[{j}]'
            if not isinstance(a, dict):
                raise DruckSpecFehler(f'{wa}: Abbildung erwartet')
            unbekannt = set(a) - {'name', 'ebene', 'richtung'}
            if unbekannt:
                raise DruckSpecFehler(f'{wa}: unbekannte Schlüssel {sorted(unbekannt)}')
            name = a.get('name')
            if not isinstance(name, str) or not name.strip():
                raise DruckSpecFehler(f'{wa}: name fehlt oder ist leer')
            ebene = a.get('ebene')
            if not isinstance(ebene, dict):
                raise DruckSpecFehler(f'{wa}.ebene: Abbildung mit punkt/normale erwartet')
            unbekannt = set(ebene) - {'frame', 'punkt', 'normale'}
            if unbekannt:
                raise DruckSpecFehler(f'{wa}.ebene: unbekannte Schlüssel {sorted(unbekannt)}')
            if 'punkt' not in ebene or 'normale' not in ebene:
                raise DruckSpecFehler(f'{wa}.ebene: punkt und normale sind Pflicht')
            normale = _vec3(ebene['normale'], f'{wa}.ebene.normale')
            if np.linalg.norm(normale) < 1e-9:
                raise DruckSpecFehler(f'{wa}.ebene.normale: Nullvektor')
            richtung = _vec3(a.get('richtung', (0, 0, 0)), f'{wa}.richtung')
            if np.linalg.norm(richtung) < 1e-9:
                raise DruckSpecFehler(f'{wa}.richtung: Nullvektor')
            abschnitte.append(Lastabschnitt(name=name,
                                            punkt=_vec3(ebene['punkt'], f'{wa}.ebene.punkt'),
                                            normale=normale, richtung=richtung,
                                            frame=str(ebene.get('frame', 'local'))))
        teile[key] = Teilspec(key=key, pose=pose, profil=profil, lastabschnitte=abschnitte)
    return DruckSpec(pfad=path, teile=teile)
