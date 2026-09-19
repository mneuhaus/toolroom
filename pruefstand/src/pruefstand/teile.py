"""Pflegedatei `spec/teile.yaml`: was ein Druckteil über sich selbst weiß.

Schema `pruefstand.teile/1`. Drei Angaben je Teil, und jede beantwortet eine Frage,
die die Formregeln sonst raten müssten::

    schema: pruefstand.teile/1
    teile:
      - key: T41L
        pose: {rotate: [0, 90, 0]}          # Druckpose (wie printing.pose_matrix)
        auflage: {normale: [0, 0, -1]}      # oder {region: {frame, von, bis}}
        griffkanten: nein                   # ja | nein
        radius_mm: 1.0                      # optional: Schwelle statt der Hausregel

* **Druckpose / Auflage** -- an der Bettseite wird nicht verrundet: die erste Lage
  liegt plan auf. Ohne diese Angabe zählt `unverrundet` die Bettkanten mit, und jede
  Zahl ist eine Obergrenze (`r7-analyse-bericht.md`, Werkzeuglücke 3: 2,3--5,4 m
  scharfe Kante je Rahmenplatte).
* **`griffkanten`** -- die Hausregel R4,2 gilt für frei anfassbare Außenkanten. Eine
  Rahmenplatte fasst niemand an; dort ist ein Kantenbruch R1,0 gemeint. `nein` setzt
  deshalb die Schwelle auf `KANTENBRUCH_MM`, `radius_mm` überschreibt beides.

Die Datei ersetzt `druck.yaml` nicht: dort stehen Profil und Lastabschnitte für
`print_pose` und `stability`, hier steht, was die **Formregeln** über das Teil wissen
müssen. Wer beides pflegt, schreibt die Pose zweimal -- das ist der Preis dafür, dass
ein Projekt die Formregeln ohne Druckprofil benutzen kann.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .printing import pose_matrix

SCHEMA = 'pruefstand.teile/1'

#: Kantenbruch an Teilen, die niemand anfasst (`griffkanten: nein`). Nicht die
#: Hausregel R4,2 -- die wäre an einer 3,15 mm breiten Randleiste geometrisch
#: unmöglich (zwei Rundungen bräuchten 8,4 mm), wie die Wanne R2 gezeigt hat.
KANTENBRUCH_MM = 1.0

_WURZEL_KEYS = {'schema', 'teile'}
_TEIL_KEYS = {'key', 'pose', 'auflage', 'griffkanten', 'radius_mm'}
_AUFLAGE_KEYS = {'normale', 'region', 'frame'}
_REGION_KEYS = {'frame', 'von', 'bis'}

_JA = {'ja', 'yes', 'true', True}
_NEIN = {'nein', 'no', 'false', False}


class TeileSpecFehler(ValueError):
    """Die Pflegedatei ist kaputt. Immer mit Dateipfad und Schlüsselpfad melden."""


def _vec3(value, wo) -> np.ndarray:
    try:
        v = np.asarray(value, dtype=float).reshape(3)
    except Exception:
        raise TeileSpecFehler(f'{wo}: drei Zahlen erwartet, bekommen {value!r}') from None
    if not np.all(np.isfinite(v)):
        raise TeileSpecFehler(f'{wo}: keine endlichen Zahlen: {value!r}')
    return v


def _fremde(d: dict, erlaubt: set, wo: str) -> None:
    unbekannt = sorted(set(d) - erlaubt)
    if unbekannt:
        raise TeileSpecFehler(f'{wo}: unbekannte Schlüssel {unbekannt}, erlaubt {sorted(erlaubt)}')


@dataclass(frozen=True)
class Auflage:
    """Wo das Teil auf dem Bett liegt -- als Richtung oder als Bereich.

    `normale` zeigt **zum Bett**: die Kanten am äußersten Ende dieser Richtung liegen
    auf. Das ist die billige Angabe, die für eine Platte reicht. `region` ist die
    genaue: ein Quader, in dem alle Kanten Bettkanten sind (für Teile, die auf einem
    Kragen oder mehreren Füßen stehen).
    """

    normale: np.ndarray | None = None
    region: dict | None = None
    frame: str = 'world'

    def _frame(self, machine):
        from .frame import Frame
        if machine is None or str(self.frame).lower() == 'world':
            return Frame.identity()
        return machine.frame(self.frame)

    def bettkanten(self, mitten, punkte=None, machine=None, toleranz=0.5) -> np.ndarray:
        """Maske über Kantenmitten: liegt diese Kante am Bett?

        `punkte` sind die Stützpunkte des **ganzen** Körpers -- an ihnen hängt die
        Bettebene. Ohne sie ergäbe eine Auswertung je Kante Unsinn: eine einzelne
        Kantenmitte ist immer ihr eigenes Extrem und läge damit stets am Bett.
        """
        p = np.atleast_2d(np.asarray(mitten, dtype=float))
        f = self._frame(machine)
        if self.region is not None:
            from .region import Region
            r = Region.box(f, tuple(self.region['von']), tuple(self.region['bis']))
            return np.asarray(r.contains(p), dtype=bool)
        n = f.direction_to_world(self.normale)
        n = n / float(np.linalg.norm(n))
        ref = p if punkte is None else np.atleast_2d(np.asarray(punkte, dtype=float))
        return (p @ n) >= float((ref @ n).max()) - float(toleranz)


@dataclass(frozen=True)
class Teil:
    """Ein Druckteil, so wie die Formregeln es brauchen."""

    key: str
    pose: object = None
    auflage: Auflage | None = None
    #: `True` = frei anfassbare Außenkanten (Hausregel R4,2), `False` = Rahmenteil
    #: (Kantenbruch), `None` = nicht gesagt; dann bleibt es bei der Hausregel.
    griffkanten: bool | None = None
    radius_mm: float | None = None
    quelle: Path | None = None

    def pose_matrix(self) -> np.ndarray:
        return pose_matrix(self.pose)

    def schwelle_mm(self, hausregel: float) -> float:
        """Welcher Radius an diesem Teil verlangt ist."""
        if self.radius_mm is not None:
            return float(self.radius_mm)
        if self.griffkanten is False:
            return KANTENBRUCH_MM
        return float(hausregel)

    def __repr__(self):
        return (f'Teil({self.key!r}, pose={self.pose is not None}, '
                f'auflage={self.auflage is not None}, griffkanten={self.griffkanten})')


@dataclass
class TeileSpec:
    """Alle Teile einer `teile.yaml`."""

    teile: dict
    quelle: Path | None = None

    def teil(self, key) -> Teil | None:
        return self.teile.get(str(key))

    def __getitem__(self, key) -> Teil:
        t = self.teil(key)
        if t is None:
            raise KeyError(f'Teil {key!r} nicht in {self.quelle}: {sorted(self.teile)}')
        return t

    def __contains__(self, key):
        return str(key) in self.teile

    def __len__(self):
        return len(self.teile)

    def keys(self) -> list[str]:
        return list(self.teile)

    def __repr__(self):
        return f'TeileSpec({self.keys()})'


def _griffkanten(value, wo) -> bool | None:
    if value is None:
        return None
    v = value if isinstance(value, bool) else str(value).strip().lower()
    if v in _JA:
        return True
    if v in _NEIN:
        return False
    raise TeileSpecFehler(f'{wo}: griffkanten muss ja oder nein sein, ist {value!r}')


def _auflage(d, wo) -> Auflage | None:
    if d is None:
        return None
    if not isinstance(d, dict):
        raise TeileSpecFehler(f'{wo}: auflage muss eine Abbildung sein')
    _fremde(d, _AUFLAGE_KEYS, wo)
    hat_n, hat_r = d.get('normale') is not None, d.get('region') is not None
    if hat_n == hat_r:
        raise TeileSpecFehler(f'{wo}: auflage braucht genau eines von normale oder region')
    frame = str(d.get('frame', 'world'))
    if hat_n:
        n = _vec3(d['normale'], f'{wo}.normale')
        if float(np.linalg.norm(n)) < 1e-9:
            raise TeileSpecFehler(f'{wo}.normale: Nullvektor')
        return Auflage(normale=n, frame=frame)
    r = d['region']
    if not isinstance(r, dict):
        raise TeileSpecFehler(f'{wo}.region: Abbildung mit von/bis erwartet')
    _fremde(r, _REGION_KEYS, f'{wo}.region')
    for feld in ('von', 'bis'):
        if r.get(feld) is None:
            raise TeileSpecFehler(f'{wo}.region: {feld} fehlt')
    return Auflage(region={'von': _vec3(r['von'], f'{wo}.region.von'),
                           'bis': _vec3(r['bis'], f'{wo}.region.bis')},
                   frame=str(r.get('frame', frame)))


def load_teile(path) -> TeileSpec:
    """`spec/teile.yaml` lesen. Jeder Formfehler fliegt beim Laden, nicht beim Messen."""
    import yaml
    path = Path(path)
    if not path.exists():
        raise TeileSpecFehler(f'{path}: Datei fehlt')
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise TeileSpecFehler(f'{path}: kein gültiges YAML ({e})') from None
    if not isinstance(data, dict):
        raise TeileSpecFehler(f'{path}: Abbildung auf oberster Ebene erwartet')
    _fremde(data, _WURZEL_KEYS, str(path))
    if data.get('schema') != SCHEMA:
        raise TeileSpecFehler(f'{path}: schema muss {SCHEMA!r} sein, ist {data.get("schema")!r}')
    rows = data.get('teile')
    if not isinstance(rows, list) or not rows:
        raise TeileSpecFehler(f'{path}: teile fehlt oder ist leer')
    teile = {}
    for i, d in enumerate(rows):
        wo = f'{path}: teile[{i}]'
        if not isinstance(d, dict):
            raise TeileSpecFehler(f'{wo}: Abbildung erwartet')
        _fremde(d, _TEIL_KEYS, wo)
        key = d.get('key')
        if not isinstance(key, str) or not key.strip():
            raise TeileSpecFehler(f'{wo}: key fehlt oder ist leer')
        if key in teile:
            raise TeileSpecFehler(f'{wo}: key {key!r} doppelt')
        try:
            pose_matrix(d.get('pose'))                    # früh validieren
        except Exception as e:
            raise TeileSpecFehler(f'{wo}.{e}') from None
        radius = d.get('radius_mm')
        if radius is not None:
            try:
                radius = float(radius)
            except (TypeError, ValueError):
                raise TeileSpecFehler(f'{wo}: radius_mm braucht eine Zahl, ist {radius!r}') from None
            if not radius > 0:
                raise TeileSpecFehler(f'{wo}: radius_mm muss größer als null sein, ist {radius!r}')
        teile[key] = Teil(key=key, pose=d.get('pose'),
                          auflage=_auflage(d.get('auflage'), f'{wo}.auflage'),
                          griffkanten=_griffkanten(d.get('griffkanten'), wo),
                          radius_mm=radius, quelle=path)
    return TeileSpec(teile=teile, quelle=path)


def find_teile(spec_dir=None) -> TeileSpec | None:
    """`teile.yaml` im Spec-Verzeichnis des laufenden Projekts. None, wenn es keine gibt."""
    from . import context as _ctx
    if spec_dir is None:
        p = _ctx.project()
        if p is None:
            return None
        spec_dir = p.spec
    f = Path(spec_dir) / 'teile.yaml'
    return load_teile(f) if f.exists() else None
