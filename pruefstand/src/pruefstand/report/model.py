"""Bericht-JSON einlesen und in Klartext übersetzen.

Der Bericht des pytest-Plugins enthält je Test `nodeid`, `outcome`, `dauer_s`
und die rohen Messwerte der Primitive. Hier wird daraus eine Struktur, die die
HTML-Seite direkt anzeigen kann: deutsche Beschriftungen, Einheiten, und die
Körperschlüssel, auf die sich ein Befund bezieht.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

OUTCOME_LABEL = {
    'passed': 'bestanden',
    'failed': 'fehlgeschlagen',
    'warnung': 'Warnung',
    'xfailed': 'erwartet rot',
    'xpassed': 'unerwartet grün',
    'skipped': 'übersprungen',
    'error': 'Fehler',
}
#: Reihenfolge der Ampel im Kopf
OUTCOME_ORDER = ('failed', 'warnung', 'xfailed', 'xpassed', 'skipped', 'error', 'passed')


def mm(v, digits=3) -> str:
    if v is None:
        return '–'
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:
        return 'nicht bestimmbar'
    if f == float('inf'):
        return 'unendlich'
    return f'{f:.{digits}f} mm'.replace('.', ',')


def mm3(v) -> str:
    if v is None:
        return 'nicht bestimmt'
    return f'{float(v):.2f} mm³'.replace('.', ',')


def num(v, digits=0) -> str:
    return f'{float(v):.{digits}f}'.replace('.', ',') if digits else str(int(v))


def prozent(v) -> str:
    return f'{float(v) * 100:.1f} %'.replace('.', ',')


def ja_nein(v) -> str:
    return 'ja' if v else 'nein'


def safe_key(name: str) -> str:
    """Wie `pruefstand.body._safe`: Dateiname, unter dem ein Solid als STL landet."""
    return re.sub(r'[^A-Za-z0-9._-]+', '_', str(name))[:120] or 'body'


def _split_keys(k: str) -> list[str]:
    return [p for p in str(k).split('|') if p]


@dataclass
class Messwert:
    """Ein Primitiv-Ergebnis eines Tests."""
    primitive: str
    raw: dict
    index: int
    titel: str = ''
    zeilen: list[tuple[str, str]] = field(default_factory=list)
    koerper: list[str] = field(default_factory=list)
    marker: dict | None = None
    hinweis: str = ''
    schwere: str = 'info'          # info | warnung | fehler
    png: str | None = None

    @property
    def mid(self) -> str:
        return f'm{self.index}'


@dataclass
class Test:
    nodeid: str
    outcome: str
    dauer_s: float
    messwerte: list[Messwert]
    index: int

    @property
    def datei(self) -> str:
        return self.nodeid.split('::')[0]

    @property
    def name(self) -> str:
        return self.nodeid.split('::')[-1]

    @property
    def tid(self) -> str:
        return f't{self.index}'

    @property
    def koerper(self) -> list[str]:
        out = []
        for m in self.messwerte:
            for k in m.koerper:
                if k not in out:
                    out.append(k)
        return out


@dataclass
class Bericht:
    pfad: Path
    erzeugt: str
    tests: list[Test]
    projekt: str = ''
    revision: str = ''
    maschine: str = ''

    def zaehlung(self) -> dict[str, int]:
        z = {}
        for t in self.tests:
            z[t.outcome] = z.get(t.outcome, 0) + 1
        return z

    def alle_koerper(self) -> list[str]:
        out = []
        for t in self.tests:
            for k in t.koerper:
                if k not in out:
                    out.append(k)
        return out


# -- Übersetzung der Primitive ------------------------------------------------

def _gap(m: dict, w: Messwert) -> None:
    pair = m.get('pair') or []
    a = pair[0] if len(pair) > 0 else '?'
    b = pair[1] if len(pair) > 1 else '?'
    w.titel = f'Spalt {mm(m.get("min_mm"))}'
    w.zeilen = [
        ('Kleinster Abstand', mm(m.get('min_mm'))),
        ('Zwischen', f'{a} und {b}'),
        ('Durchdringung', ja_nein(m.get('penetrating'))),
    ]
    per = m.get('per_body') or {}
    for k, v in sorted(per.items(), key=lambda kv: (kv[1] is None, kv[1])):
        w.zeilen.append((f'Abstand zu {k}', mm(v)))
    w.koerper = [k for k in (a, b) if k and k != '?']
    for k in per:
        for part in _split_keys(k):
            if part not in w.koerper:
                w.koerper.append(part)
    pa, pb = m.get('point_a'), m.get('point_b')
    if pa and pb:
        w.marker = {'art': 'strecke', 'a': pa, 'b': pb,
                    'label': mm(m.get('min_mm')),
                    'rot': bool(m.get('penetrating'))}
    if m.get('penetrating'):
        w.schwere = 'fehler'


def _overlap(m: dict, w: Messwert) -> None:
    vol = m.get('volume_mm3')
    exakt = bool(m.get('exact'))
    if vol is not None:
        w.titel = f'Überschneidung {mm3(vol)}'
    elif m.get('collides'):
        w.titel = f'Durchdringung, {int(m.get("contacts") or 0)} Kontakte'
    else:
        w.titel = 'keine Überschneidung'
    w.zeilen = [
        ('Volumen', mm3(vol) if exakt else 'nicht bestimmt (Mesh-Prüfung)'),
        ('Kollidiert', ja_nein(m.get('collides'))),
        ('Verfahren', 'exakt (Solid)' if exakt else 'Mesh (fcl)'),
        ('Kontaktpunkte', num(m.get('contacts') or 0)),
        ('Größte Eindringtiefe', mm(m.get('max_penetration_mm'))),
        ('Berührung', ja_nein(m.get('touching'))),
    ]
    paare = []
    for p in (m.get('pairs') or []):
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        ka, kb = str(p[0]), str(p[1])
        v = p[2] if len(p) > 2 else None
        treffer = bool(p[3]) if len(p) > 3 else v not in (None, 0)
        txt = mm3(v) if v is not None else 'Mesh-Kontakt'
        paare.append((ka, kb, treffer))
        w.zeilen.append((f'{ka} ↔ {kb}', txt + (' – Treffer' if treffer else '')))
    for p in (m.get('touch_pairs') or []):
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            paare.append((str(p[0]), str(p[1]), False))
            w.zeilen.append((f'{p[0]} ↔ {p[1]}', 'berührt sich'))
    for ka, kb, _t in paare:
        for k in (ka, kb):
            if k not in w.koerper:
                w.koerper.append(k)
    treffer = [(a, b) for a, b, t in paare if t]
    if treffer:
        w.marker = {'art': 'ueberschneidung', 'paare': [list(t) for t in treffer],
                    'label': mm3(vol) if vol else f'{int(m.get("contacts") or 0)} Kontakte'}
        w.hinweis = ('Der markierte Quader ist die Überschneidung der Hüllquader beider Körper, '
                     'nicht das exakte Durchdringungsvolumen: Kontaktpunkte stehen im Bericht-JSON nicht.')
    if m.get('collides'):
        w.schwere = 'fehler'


def _coverage(m: dict, w: Messwert) -> None:
    w.titel = f'Abdeckung {prozent(m.get("fraction") or 0)}, {num(m.get("open") or 0)} offen'
    w.zeilen = [
        ('Abtastpunkte gesamt', num(m.get('total') or 0)),
        ('Abgedeckt', num(m.get('covered') or 0)),
        ('Offen', num(m.get('open') or 0)),
        ('Anteil abgedeckt', prozent(m.get('fraction') or 0)),
    ]
    w.png = m.get('map_png')
    if m.get('open'):
        w.schwere = 'fehler'
    w.hinweis = ('Die offenen Abtastpunkte liegen nur als Karte (PNG) vor; ihre Koordinaten '
                 'stehen nicht im Bericht-JSON und können daher nicht im 3D-Modell markiert werden.')


def _protrusion(m: dict, w: Messwert) -> None:
    w.titel = f'Vorstehen {mm3(m.get("volume_mm3"))}'
    w.zeilen = [
        ('Herausragendes Volumen', mm3(m.get('volume_mm3'))),
        ('Treffer', num(m.get('hits') or 0)),
        ('Verfahren', 'exakt (Solid)' if m.get('exact') else 'Mesh'),
    ]
    if m.get('hits'):
        w.schwere = 'fehler'


def _same_as(m: dict, w: Messwert) -> None:
    w.titel = f'Abweichung {mm(m.get("max_deviation_mm"), 4)}'
    w.zeilen = [
        ('Größte Abweichung', mm(m.get('max_deviation_mm'), 4)),
        ('Volumendifferenz', mm3(m.get('diff_mm3'))),
        ('Stichproben', num(m.get('samples') or 0)),
        ('Verfahren', 'exakt (Solid)' if m.get('exact') else 'Stichprobe'),
    ]


_UEBERSETZER = {'gap': _gap, 'overlap': _overlap, 'coverage': _coverage,
                'protrusion': _protrusion, 'same_as': _same_as}


def _messwert(raw: dict, index: int) -> Messwert:
    prim = str(raw.get('primitive', 'unbekannt'))
    w = Messwert(primitive=prim, raw=raw, index=index)
    fn = _UEBERSETZER.get(prim)
    if fn is None:
        w.titel = prim
        w.zeilen = [(k, str(v)) for k, v in raw.items() if k != 'primitive']
    else:
        fn(raw, w)
    if raw.get('nichts_gemessen'):
        w.schwere = 'fehler'
        w.hinweis = ('Nichts gemessen: die Region enthielt keine Geometrie. '
                     + w.hinweis).strip()
    return w


def lade(pfad) -> Bericht:
    """Bericht-JSON lesen und um Projekt-/Maschinenangaben aus dem Umfeld ergänzen."""
    pfad = Path(pfad).resolve()
    data = json.loads(pfad.read_text())
    tests = []
    n = 0
    for i, t in enumerate(data.get('tests', [])):
        ms = []
        for raw in (t.get('messwerte') or []):
            ms.append(_messwert(raw, n))
            n += 1
        tests.append(Test(nodeid=str(t.get('nodeid', f'test {i}')),
                          outcome=str(t.get('outcome', 'unbekannt')),
                          dauer_s=float(t.get('dauer_s') or 0.0),
                          messwerte=ms, index=i))
    b = Bericht(pfad=pfad, erzeugt=str(data.get('erzeugt', '')), tests=tests)
    b.projekt = _projekt_name(pfad)
    return b


def projekt_wurzel(bericht_pfad: Path) -> Path:
    """Projektwurzel raten: <projekt>/var/review/pruefstand.json."""
    p = Path(bericht_pfad).resolve().parent
    if p.name == 'review' and p.parent.name == 'var':
        return p.parent.parent
    return p


def _projekt_name(pfad: Path) -> str:
    return projekt_wurzel(pfad).name
