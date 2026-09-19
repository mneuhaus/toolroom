"""Schraubenliste `spec/schrauben.yaml` laden und prüfen.

Schema `pruefstand.schrauben/1`:

```yaml
schema: pruefstand.schrauben/1
schrauben:
  - id: P03-1
    norm: M3x16          # M3/M5, Länge in mm
    kopf: zylinder       # zylinder | senkkopf
    frame: local         # Bezugssystem aus machine.json (oder `world`)
    punkt: [x, y, z]     # Mitte der Kopfauflage, im Frame
    richtung: [0, 1, 0]  # Einschraubrichtung, im Frame, wird normiert
    beisst: Klemmbacke   # optional: erwartetes beißendes Teil
    status: not_built_yet  # optional: beschrieben, aber noch nicht gebaut
```

`status: not_built_yet` ist der einzige erlaubte Wert. Er macht die zugehörige Prüfung
**unentschieden**: die Schraube ist beschrieben, das Teil dazu gibt es noch nicht.

Fehlerhafte Dateien werden laut und früh abgewiesen (unbekanntes Schema, fehlende
Pflichtfelder, Nullvektor, doppelte id, unbekannte Kopfform, unlesbare Norm).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .frame import Frame
from .results import NICHT_GEBAUT, pruefe_bau_status

SCHEMA = 'pruefstand.schrauben/1'
KOPFFORMEN = ('zylinder', 'senkkopf')
PFLICHT = ('id', 'norm', 'kopf', 'frame', 'punkt', 'richtung')
_NORM = re.compile(r'^M(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)$')


def _vec3(value, feld, sid) -> np.ndarray:
    try:
        v = np.asarray(value, dtype=float).reshape(3)
    except Exception as exc:
        raise ValueError(f'Schraube {sid!r}: {feld} braucht drei Zahlen, bekommen {value!r}') from exc
    if not np.all(np.isfinite(v)):
        raise ValueError(f'Schraube {sid!r}: {feld} enthält keine endlichen Zahlen: {value!r}')
    return v


@dataclass(frozen=True)
class Screw:
    """Eine Schraube aus der Pflegedatei. Längen in mm."""

    id: str
    norm: str
    kopf: str
    frame: str
    punkt: np.ndarray
    richtung: np.ndarray
    beisst: str | None = None
    #: '' oder 'not_built_yet' -- siehe `pruefe_bau_status`.
    status: str = ''
    quelle: Path | None = None
    extra: dict = field(default_factory=dict)

    # -- Norm ------------------------------------------------------------
    @property
    def nicht_gebaut(self) -> bool:
        """Die Pflegedatei sagt: beschrieben, aber noch nicht gebaut."""
        return self.status == NICHT_GEBAUT

    @property
    def nominal_mm(self) -> float:
        """Nenndurchmesser (M3 -> 3.0)."""
        return float(_NORM.match(self.norm).group(1).replace(',', '.'))

    @property
    def laenge_mm(self) -> float:
        """Schaftlänge unter dem Kopf (M3x16 -> 16.0)."""
        return float(_NORM.match(self.norm).group(2).replace(',', '.'))

    @property
    def groesse(self) -> str:
        n = self.nominal_mm
        return f'M{n:g}'

    # -- Lage ------------------------------------------------------------
    def axis_points(self, frame) -> tuple[np.ndarray, np.ndarray]:
        """(Kopfauflage, Einschraubrichtung) in **Welt**koordinaten.

        `frame` ist ein `Frame` oder etwas mit `.frame(name)` (z. B. `Machine`).
        """
        f = self._frame(frame)
        origin = np.asarray(f.to_world(self.punkt), dtype=float).reshape(3)
        d = f.direction_to_world(self.richtung)
        n = float(np.linalg.norm(d))
        if n == 0.0:
            raise ValueError(f'Schraube {self.id!r}: Richtung ist der Nullvektor')
        return origin, d / n

    def _frame(self, frame) -> Frame:
        if isinstance(frame, Frame):
            return frame
        if frame is None or str(self.frame).lower() == 'world':
            return Frame.identity()
        getter = getattr(frame, 'frame', None)
        if callable(getter):
            return getter(self.frame)
        raise TypeError(f'Frame oder Machine erwartet, bekommen {type(frame).__name__}')

    def __repr__(self):
        b = f', beisst={self.beisst!r}' if self.beisst else ''
        return (f'Screw({self.id!r}, {self.norm}, {self.kopf}, {self.frame}, '
                f'punkt={np.round(self.punkt, 3).tolist()}{b})')


def screw_from_dict(d: dict, quelle=None) -> Screw:
    if not isinstance(d, dict):
        raise ValueError(f'Schraubeneintrag muss eine Abbildung sein, bekommen {type(d).__name__}')
    sid = d.get('id')
    fehlt = [k for k in PFLICHT if d.get(k) is None]
    if fehlt:
        raise ValueError(f'Schraube {sid!r}: Pflichtfelder fehlen: {fehlt}')
    norm = str(d['norm']).strip()
    if not _NORM.match(norm):
        raise ValueError(f'Schraube {sid!r}: norm {norm!r} nicht lesbar (erwartet z. B. M3x16)')
    kopf = str(d['kopf']).strip().lower()
    if kopf not in KOPFFORMEN:
        raise ValueError(f'Schraube {sid!r}: kopf {kopf!r} unbekannt, erlaubt {list(KOPFFORMEN)}')
    punkt = _vec3(d['punkt'], 'punkt', sid)
    richtung = _vec3(d['richtung'], 'richtung', sid)
    n = float(np.linalg.norm(richtung))
    if n == 0.0:
        raise ValueError(f'Schraube {sid!r}: richtung ist der Nullvektor')
    status = pruefe_bau_status(d.get('status'), f'Schraube {sid!r}')
    bekannt = set(PFLICHT) | {'beisst', 'status'}
    return Screw(id=str(sid), norm=norm, kopf=kopf, frame=str(d['frame']),
                 punkt=punkt, richtung=richtung / n,
                 beisst=(str(d['beisst']) if d.get('beisst') else None),
                 status=status, quelle=Path(quelle) if quelle else None,
                 extra={k: v for k, v in d.items() if k not in bekannt})


def load_screws(path) -> list[Screw]:
    """`spec/schrauben.yaml` lesen. Wirft bei jedem Formfehler."""
    import yaml
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Schraubenliste {path} fehlt')
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f'{path}: Wurzel muss eine Abbildung sein')
    if data.get('schema') != SCHEMA:
        raise ValueError(f'{path}: unerwartetes Schema {data.get("schema")!r}, erwartet {SCHEMA!r}')
    rows = data.get('schrauben')
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'{path}: `schrauben` fehlt oder ist leer')
    out = [screw_from_dict(r, quelle=path) for r in rows]
    doppelt = sorted({s.id for s in out if [x.id for x in out].count(s.id) > 1})
    if doppelt:
        raise ValueError(f'{path}: doppelte Schrauben-ids: {doppelt}')
    return out


def screws_by_id(screws) -> dict[str, Screw]:
    return {s.id: s for s in screws}
