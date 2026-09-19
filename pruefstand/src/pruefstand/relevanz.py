"""Pflegedatei `spec/relevanz.yaml` laden und prüfen.

Schema `pruefstand.relevanz/1`:

```yaml
schema: pruefstand.relevanz/1
teile:
  - key: T05
    erklaert:                    # bewusst vorhandenes Material ohne Kontaktpartner
      - name: Grifflippe
        bereich: {frame: local, von: [-120, -10, -5], bis: [120, 0, 5]}
        grund: Anfassen beim Einsetzen
    ignorieren: [Beschriftung]   # Namen aus `erklaert`, die NICHT als Anker zählen,
                                 # sondern ganz aus der Messung fallen
```

Ein Eintrag unter `erklaert` ist ein **Anker**: Material in diesem Quader gilt als
funktional, auch wenn die Automatik dort weder Kontakt noch Bohrung findet. Steht sein
Name zusätzlich unter `ignorieren`, wird der Bereich stattdessen **ausgeschlossen**:
das Material darin wird weder als funktional noch als fraglich gezählt (z. B. eine
Beschriftung, deren Relevanz das Verfahren gar nicht beurteilen kann).

Fehlerhafte Dateien werden laut und früh abgewiesen: unbekanntes Schema, unbekannte
Schlüssel, fehlende Pflichtfelder, doppelte Namen, `ignorieren` ohne passenden
`erklaert`-Eintrag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .frame import Frame
from .region import Region

SCHEMA = 'pruefstand.relevanz/1'

_WURZEL_KEYS = {'schema', 'teile'}
_TEIL_KEYS = {'key', 'erklaert', 'ignorieren'}
_ERKLAERT_KEYS = {'name', 'bereich', 'grund'}
_BEREICH_KEYS = {'frame', 'von', 'bis'}


def _vec3(value, feld, wo) -> np.ndarray:
    try:
        v = np.asarray(value, dtype=float).reshape(3)
    except Exception as exc:
        raise ValueError(f'{wo}: {feld} braucht drei Zahlen, bekommen {value!r}') from exc
    if not np.all(np.isfinite(v)):
        raise ValueError(f'{wo}: {feld} enthält keine endlichen Zahlen: {value!r}')
    return v


def _fremde(d: dict, erlaubt: set, wo: str) -> None:
    unbekannt = sorted(set(d) - erlaubt)
    if unbekannt:
        raise ValueError(f'{wo}: unbekannte Schlüssel {unbekannt}, erlaubt {sorted(erlaubt)}')


@dataclass(frozen=True)
class Erklaert:
    """Ein benannter Quader mit Begründung. Längen in mm."""

    name: str
    frame: str
    von: np.ndarray
    bis: np.ndarray
    grund: str = ''

    def region(self, frames=None) -> Region:
        """Region.box in Weltkoordinaten. `frames` ist ein Frame oder etwas mit `.frame(name)`."""
        return Region.box(self._frame(frames), self.von, self.bis)

    def _frame(self, frames) -> Frame:
        if isinstance(frames, Frame):
            return frames
        if frames is None or str(self.frame).lower() == 'world':
            return Frame.identity()
        getter = getattr(frames, 'frame', None)
        if callable(getter):
            return getter(self.frame)
        raise TypeError(f'Frame oder Machine erwartet, bekommen {type(frames).__name__}')

    def __repr__(self):
        return (f'Erklaert({self.name!r}, {self.frame}, von={np.round(self.von, 2).tolist()}, '
                f'bis={np.round(self.bis, 2).tolist()})')


@dataclass(frozen=True)
class TeilRelevanz:
    """Was für ein Teil von Hand erklärt wurde."""

    key: str
    erklaert: tuple = ()
    ignorieren: tuple = ()
    quelle: Path | None = None

    def anker(self) -> list[Erklaert]:
        """Erklärte Bereiche, die als Anker zählen."""
        return [e for e in self.erklaert if e.name not in self.ignorieren]

    def ausgeschlossen(self) -> list[Erklaert]:
        """Erklärte Bereiche, die ganz aus der Messung fallen."""
        return [e for e in self.erklaert if e.name in self.ignorieren]

    def __repr__(self):
        return (f'TeilRelevanz({self.key!r}, anker={[e.name for e in self.anker()]}, '
                f'ignoriert={list(self.ignorieren)})')


@dataclass
class Relevanz:
    """Alle Teile einer Pflegedatei."""

    teile: dict = field(default_factory=dict)
    quelle: Path | None = None

    def teil(self, key) -> TeilRelevanz | None:
        return self.teile.get(str(key))

    def keys(self) -> list[str]:
        return list(self.teile)

    def __len__(self):
        return len(self.teile)

    def __repr__(self):
        return f'Relevanz({self.keys()})'


def erklaert_from_dict(d: dict, wo: str) -> Erklaert:
    if not isinstance(d, dict):
        raise ValueError(f'{wo}: `erklaert`-Eintrag muss eine Abbildung sein, bekommen {type(d).__name__}')
    _fremde(d, _ERKLAERT_KEYS, wo)
    name = d.get('name')
    if not name:
        raise ValueError(f'{wo}: `name` fehlt')
    wo = f'{wo} / {name}'
    bereich = d.get('bereich')
    if not isinstance(bereich, dict):
        raise ValueError(f'{wo}: `bereich` fehlt oder ist keine Abbildung')
    _fremde(bereich, _BEREICH_KEYS, f'{wo} / bereich')
    for feld in ('von', 'bis'):
        if bereich.get(feld) is None:
            raise ValueError(f'{wo}: `bereich.{feld}` fehlt')
    von = _vec3(bereich['von'], 'bereich.von', wo)
    bis = _vec3(bereich['bis'], 'bereich.bis', wo)
    if np.any(von == bis):
        raise ValueError(f'{wo}: `von` und `bis` fallen in einer Achse zusammen — leerer Quader')
    return Erklaert(name=str(name), frame=str(bereich.get('frame', 'local')),
                    von=von, bis=bis, grund=str(d.get('grund', '')))


def teil_from_dict(d: dict, quelle=None) -> TeilRelevanz:
    if not isinstance(d, dict):
        raise ValueError(f'`teile`-Eintrag muss eine Abbildung sein, bekommen {type(d).__name__}')
    _fremde(d, _TEIL_KEYS, 'teile-Eintrag')
    key = d.get('key')
    if not key:
        raise ValueError('teile-Eintrag: `key` fehlt')
    wo = f'Teil {key!r}'
    rows = d.get('erklaert') or []
    if not isinstance(rows, list):
        raise ValueError(f'{wo}: `erklaert` muss eine Liste sein')
    erklaert = [erklaert_from_dict(r, wo) for r in rows]
    namen = [e.name for e in erklaert]
    doppelt = sorted({n for n in namen if namen.count(n) > 1})
    if doppelt:
        raise ValueError(f'{wo}: doppelte Namen unter `erklaert`: {doppelt}')
    ign = d.get('ignorieren') or []
    if not isinstance(ign, list):
        raise ValueError(f'{wo}: `ignorieren` muss eine Liste von Namen sein')
    ign = [str(x) for x in ign]
    fremd = sorted(set(ign) - set(namen))
    if fremd:
        raise ValueError(f'{wo}: `ignorieren` nennt {fremd}, dazu gibt es keinen `erklaert`-Eintrag')
    return TeilRelevanz(key=str(key), erklaert=tuple(erklaert), ignorieren=tuple(ign),
                        quelle=Path(quelle) if quelle else None)


def load_relevanz(path) -> Relevanz:
    """`spec/relevanz.yaml` lesen. Wirft bei jedem Formfehler."""
    import yaml
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Pflegedatei {path} fehlt')
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f'{path}: Wurzel muss eine Abbildung sein')
    _fremde(data, _WURZEL_KEYS, str(path))
    if data.get('schema') != SCHEMA:
        raise ValueError(f'{path}: unerwartetes Schema {data.get("schema")!r}, erwartet {SCHEMA!r}')
    rows = data.get('teile')
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'{path}: `teile` fehlt oder ist leer')
    teile = {}
    for r in rows:
        t = teil_from_dict(r, quelle=path)
        if t.key in teile:
            raise ValueError(f'{path}: doppelter Teil-key {t.key!r}')
        teile[t.key] = t
    return Relevanz(teile=teile, quelle=path)


def find_relevanz(spec_dir=None) -> Relevanz | None:
    """`relevanz.yaml` im Spec-Verzeichnis des laufenden Projekts. None, wenn es keine gibt."""
    from . import context as _ctx
    if spec_dir is None:
        p = _ctx.project()
        if p is None:
            return None
        spec_dir = p.spec
    f = Path(spec_dir) / 'relevanz.yaml'
    return load_relevanz(f) if f.exists() else None
