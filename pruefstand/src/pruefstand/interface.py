"""Schnittstellen benennen statt Messfenster platzieren.

Eine Schnittstelle ist die Stelle, an der ein Teil die Maschine greift: ein Lagerzapfen
im 608, ein Hornsitz, ein Schraubenkreis, eine Anlagefläche. Bisher wurde sie von Hand
als Quader oder Zylinder nachgebaut -- und genau daran sind beide Referenzteile
gescheitert: ein Fenster, dessen Wand im Material liegt, misst sich selbst (Zylinder
r 4,5 über dem Bund Ø10,5 liefert 4,41 statt 3,95).

Hier steht stattdessen, **was** die Schnittstelle ist. Das Fenster fällt daraus ab, und
die tragende Fläche wird im BRep gesucht, nicht geraten.

Pflegedatei `spec/schnittstellen.yaml`, Schema `pruefstand.schnittstellen/1`:

```yaml
schema: pruefstand.schnittstellen/1
schnittstellen:
  - id: journal_pin          # Lagerzapfen im 608
    kind: pin                # pin | bore | seat | plane
    body: T60                # Suchbegriff wie bei Parts.find
    frame: world
    axis: [1, 0, 0]
    origin: [-104.3, 135, 236]
    radius: 3.95
    length: 7.4              # nur der freie Zapfen, nicht der Bund
    partner: H608            # Maschinenkörper, optional
    tolerance: {radius: 0.05, axis_deg: 0.1, offset: 0.05}
  - id: hub_bolt_circle
    kind: bore
    body: T61
    axis: [1, 0, 0]
    origin: [93.3, 135, 236]
    radius: 1.31
    pitch_radius: 9.5        # Teilkreis: die Bohrungen liegen neben der Achse
    count: 4                 # alle vier müssen da sein, sonst MISSING/AMBIGUOUS
    length: 12.0
```

`plane` braucht statt `radius` ein `size: [u, v]` (Kantenlängen des Fensters quer zur
Normale); `axis` ist dann die Flächennormale.

Drei Ausgänge beim Suchen, und keiner davon ist „nimm den besten Kandidaten":

| status | heißt |
|---|---|
| `UNIQUE` | genau `count` Flächen erfüllen alle Kriterien |
| `AMBIGUOUS` | mehr als `count` -- die Beschreibung trennt die Geometrie nicht |
| `MISSING` | weniger als `count` -- die beschriebene Fläche gibt es so nicht |

`AMBIGUOUS` und `MISSING` sind **unentschieden**, nicht „verletzt": eine nicht
gefundene Fläche beweist keinen Verstoß, sie beweist gar nichts. Grün werden sie nie.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .frame import Frame
from .region import Region
from .results import NICHT_GEBAUT, NICHT_GEBAUT_MELDUNG, Result, pruefe_bau_status

SCHEMA = 'pruefstand.schnittstellen/1'
ARTEN = ('pin', 'bore', 'seat', 'plane')
PFLICHT = ('id', 'kind', 'body', 'axis', 'origin')

UNIQUE = 'UNIQUE'
AMBIGUOUS = 'AMBIGUOUS'
MISSING = 'MISSING'

#: Vorgabetoleranzen, wenn die Pflegedatei schweigt. Bewusst eng: eine Schnittstelle,
#: die 0,5 mm Spiel im Radius hat, ist keine.
TOLERANZ = {'radius': 0.05, 'axis_deg': 0.1, 'offset': 0.05, 'gap': 0.02}

#: Die Suche greift mindestens so weit, auch wenn die Toleranz enger ist (mm bzw. Grad).
#: Ohne diesen Abstand zwischen Suchen und Urteilen könnte eine gefundene Fläche nie
#: durchfallen -- sie wäre ja mit genau der Urteilstoleranz gefunden worden. Eine knapp
#: verfehlte Fläche soll als **Fehler** auffallen, nicht als MISSING verschwinden; wer
#: weiter danebenliegt, beschreibt eine andere Fläche.
SUCHFENSTER = {'radius': 0.25, 'axis_deg': 1.0, 'offset': 0.25}

#: Das Messfenster steht um diesen Betrag weiter als die Schnittstelle selbst. Ein
#: Fenster exakt auf der Oberfläche ist eine Gussform, kein Fenster -- es berührt die
#: Fläche überall und der Randhinweis ginge bei jeder sauberen Schnittstelle an.
FENSTER_ZUSCHLAG_MM = 0.5


def _vec3(value, feld, sid) -> np.ndarray:
    try:
        v = np.asarray(value, dtype=float).reshape(3)
    except Exception as exc:
        raise ValueError(f'Schnittstelle {sid!r}: {feld} braucht drei Zahlen, bekommen {value!r}') from exc
    if not np.all(np.isfinite(v)):
        raise ValueError(f'Schnittstelle {sid!r}: {feld} enthält keine endlichen Zahlen: {value!r}')
    return v


@dataclass(frozen=True)
class Interface:
    """Eine benannte Schnittstelle. Längen in mm, Winkel in Grad."""

    id: str
    kind: str
    body: str
    axis: np.ndarray
    origin: np.ndarray
    frame: str = 'world'
    radius: float | None = None
    inner_radius: float = 0.0
    pitch_radius: float = 0.0
    length: float = 0.0
    size: tuple | None = None
    count: int = 1
    partner: str | None = None
    #: '' oder 'not_built_yet': beschrieben, aber noch nicht gebaut.
    status: str = ''
    tolerance: dict = field(default_factory=lambda: dict(TOLERANZ))
    quelle: Path | None = None
    extra: dict = field(default_factory=dict)

    @property
    def nicht_gebaut(self) -> bool:
        return self.status == NICHT_GEBAUT

    # -- Lage ------------------------------------------------------------
    def _frame(self, machine=None) -> Frame:
        if str(self.frame).lower() == 'world' or machine is None:
            return Frame.identity()
        return machine.frame(self.frame)

    def welt_achse(self, machine=None) -> tuple[np.ndarray, np.ndarray]:
        """(Ursprung, Richtung) der Schnittstellenachse in Weltkoordinaten."""
        f = self._frame(machine)
        o = np.asarray(f.to_world(self.origin), dtype=float).reshape(3)
        d = f.direction_to_world(self.axis)
        return o, d / float(np.linalg.norm(d))

    def tol(self, name: str) -> float:
        """Urteilstoleranz: so eng darf die Schnittstelle höchstens danebenliegen."""
        return float(self.tolerance.get(name, TOLERANZ[name]))

    def suchfenster(self, name: str) -> float:
        """Suchtoleranz: so weit schaut die Flächensuche -- nie enger als das Urteil."""
        return max(self.tol(name), SUCHFENSTER[name])

    # -- Fenster ---------------------------------------------------------
    def region(self, machine=None, zuschlag_mm: float = FENSTER_ZUSCHLAG_MM) -> Region:
        """Das Messfenster zur Schnittstelle -- rund für pin/bore/seat, Quader für plane."""
        o, d = self.welt_achse(machine)
        if self.kind == 'plane':
            if self.size is None:
                raise ValueError(f'Schnittstelle {self.id!r}: plane braucht `size: [u, v]`')
            u, v = (float(x) for x in self.size)
            # Das Fenster liegt **um** die Fläche herum, nicht auf einer Seite: eine
            # Anlagefläche hat ihren Partner auf der anderen Seite, und welche das ist,
            # sagt die Normale nicht verlässlich (STEP dreht sie, wie es mag).
            tiefe = float(self.length) or zuschlag_mm
            f = Frame.from_axis(d, o)
            return Region.box(f, (-u / 2, -v / 2, -tiefe / 2), (u / 2, v / 2, tiefe / 2))
        if self.radius is None:
            raise ValueError(f'Schnittstelle {self.id!r}: {self.kind} braucht `radius`')
        laenge = float(self.length) or (2 * zuschlag_mm)
        aussen = float(self.radius) + float(self.pitch_radius) + zuschlag_mm
        innen = float(self.inner_radius)
        return Region.cylinder(Frame.identity(), o, d, radius=aussen, length=laenge,
                               inner_radius=innen)

    # -- Suchen ----------------------------------------------------------
    def match(self, body, machine=None) -> "Match":
        """Die tragende Fläche im BRep suchen. Nie raten -- siehe Modulkopf."""
        if body.solid is None:
            return Match(self.id, MISSING, [],
                         grund=f'{body.key!r} hat keinen Solid (aus STL geladen), '
                               'im Netz gibt es keine Flächen zu erkennen')
        o, d = self.welt_achse(machine)
        kandidaten = (_ebenen(body, o, d, self) if self.kind == 'plane'
                      else _zylinder(body, o, d, self))
        n = max(1, int(self.count))
        if len(kandidaten) == n:
            status = UNIQUE
        elif len(kandidaten) > n:
            status = AMBIGUOUS
        else:
            status = MISSING
        return Match(self.id, status, kandidaten, erwartet=n)

    def __repr__(self):
        r = f', r={self.radius:g}' if self.radius is not None else ''
        c = f', count={self.count}' if self.count != 1 else ''
        return f'Interface({self.id!r}, {self.kind}, {self.body!r}{r}{c})'


@dataclass
class Match:
    """Was die Suche gefunden hat -- mit allen Kandidaten, nicht nur dem besten."""

    interface_id: str
    status: str
    candidates: list
    erwartet: int = 1
    grund: str = ''

    @property
    def unique(self) -> bool:
        return self.status == UNIQUE

    def best(self) -> dict | None:
        """Der erste Kandidat -- **nur** aufrufen, wenn der Status UNIQUE ist."""
        return self.candidates[0] if self.candidates else None

    def __repr__(self):
        return (f'Match({self.interface_id!r}, {self.status}, '
                f'{len(self.candidates)}/{self.erwartet} Flächen)')


@dataclass(repr=False)
class InterfaceResult(Result):
    interface_id: str = ''
    kind: str = ''
    status: str = MISSING
    radius_soll_mm: float | None = None
    radius_mm: float | None = None
    axis_deg: float | None = None
    offset_mm: float | None = None
    gap_mm: float | None = None
    partner: str = ''
    candidates: list = field(default_factory=list)
    #: Welche Kriterien die gefundene Fläche reißt -- im Klartext, mit dem Messwert.
    verletzt: list = field(default_factory=list)
    passed: bool = False
    primitive: str = 'interface'
    _fields: tuple = ('interface_id', 'kind', 'status', 'radius_soll_mm', 'radius_mm',
                      'axis_deg', 'offset_mm', 'gap_mm', 'partner', 'verletzt', 'candidates')


# -- Flächensuche -----------------------------------------------------------

def _flaechen(body):
    """(Index, Fläche, BRepAdaptor_Surface) je Fläche des Körpers."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    for i, f in enumerate(body.solid.faces()):
        yield i, f, BRepAdaptor_Surface(f.wrapped)


def _winkel_deg(a, b) -> float:
    """Winkel zwischen zwei Achsen, Vorzeichen egal (0…90°)."""
    c = float(np.clip(abs(np.dot(a, b)), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def _abstand_zur_achse(punkt, o, d) -> float:
    v = np.asarray(punkt, dtype=float) - o
    return float(np.linalg.norm(v - np.dot(v, d) * d))


def _zylinder(body, o, d, iface) -> list[dict]:
    from OCP.GeomAbs import GeomAbs_SurfaceType
    soll_r = float(iface.radius)
    tol_r = iface.suchfenster('radius')
    tol_w = iface.suchfenster('axis_deg')
    tol_o = iface.suchfenster('offset')
    teil = float(iface.pitch_radius)
    out = []
    for i, f, ad in _flaechen(body):
        if ad.GetType() != GeomAbs_SurfaceType.GeomAbs_Cylinder:
            continue
        cy = ad.Cylinder()
        r = float(cy.Radius())
        if abs(r - soll_r) > tol_r:
            continue
        richtung = np.asarray(cy.Axis().Direction().Coord(), dtype=float)
        winkel = _winkel_deg(richtung, d)
        if winkel > tol_w:
            continue
        # Abstand der Flächenachse zur Schnittstellenachse. Beim Schraubenkreis ist das
        # nicht null, sondern der Teilkreisradius -- deshalb wird gegen `pitch_radius`
        # gemessen und nicht gegen die Mitte.
        versatz = _abstand_zur_achse(np.asarray(cy.Axis().Location().Coord(), dtype=float), o, d)
        if abs(versatz - teil) > tol_o:
            continue
        mitte = np.asarray(tuple(f.center()), dtype=float)
        out.append({'face': f'{body.key}#{i}', 'radius_mm': round(r, 4),
                    'axis_deg': round(winkel, 4), 'offset_mm': round(versatz, 4),
                    'axial_mm': round(float(np.dot(mitte - o, d)), 3),
                    'area_mm2': round(float(f.area), 3)})
    return out


def _ebenen(body, o, d, iface) -> list[dict]:
    from OCP.GeomAbs import GeomAbs_SurfaceType
    tol_w, tol_o = iface.suchfenster('axis_deg'), iface.suchfenster('offset')
    out = []
    for i, f, ad in _flaechen(body):
        if ad.GetType() != GeomAbs_SurfaceType.GeomAbs_Plane:
            continue
        normale = np.asarray(ad.Plane().Axis().Direction().Coord(), dtype=float)
        winkel = _winkel_deg(normale, d)
        if winkel > tol_w:
            continue
        punkt = np.asarray(ad.Plane().Axis().Location().Coord(), dtype=float)
        versatz = abs(float(np.dot(punkt - o, d)))
        if versatz > tol_o:
            continue
        mitte = np.asarray(tuple(f.center()), dtype=float)
        out.append({'face': f'{body.key}#{i}', 'radius_mm': None,
                    'axis_deg': round(winkel, 4), 'offset_mm': round(versatz, 4),
                    'quer_mm': round(_abstand_zur_achse(mitte, o, d), 3),
                    'area_mm2': round(float(f.area), 3)})
    return out


# -- Prüfung ----------------------------------------------------------------

def _finde_body(iface, parts):
    """`iface.body` in `parts` auflösen -- Parts, Liste oder einzelner Body."""
    from .body import Body, Parts
    if isinstance(parts, Body):
        return parts if iface.body.lower() in (parts.key.lower(), parts.name.lower()) else None
    if isinstance(parts, Parts):
        try:
            return parts.find(iface.body)
        except Exception:
            return None
    treffer = [b for b in parts if iface.body.lower() in f'{b.key} {b.name}'.lower()]
    return treffer[0] if len(treffer) == 1 else None


def interface_ok(iface: Interface, parts, at=None, machine=None, partner_body=None) -> InterfaceResult:
    """Schnittstelle gegen die Geometrie prüfen: Fläche finden, Maße vergleichen.

    Urteil auf `brep` -- Radius, Achswinkel und Versatz kommen aus den exakten Flächen,
    nicht aus einer Abtastung. Der Partnerabstand (`gap_mm`) ist daneben ein
    Mesh-Messwert und steht als eigener `gap`-Eintrag im Bericht.
    """
    from .machine import Scene
    if machine is None:
        if isinstance(at, Scene):
            machine = at.machine
        elif hasattr(parts, 'machine'):
            machine = parts.machine
    r = InterfaceResult(interface_id=iface.id, kind=iface.kind,
                        radius_soll_mm=iface.radius, partner=iface.partner or '')
    r.urteil_auf = 'brep'
    if iface.nicht_gebaut:
        # Beschrieben, aber noch nicht gebaut: es gibt nichts zu suchen. Grün wäre
        # eine Aussage über Geometrie, die es nicht gibt.
        r.unentschieden = True
        r.offen_grund = f'{iface.id}: {NICHT_GEBAUT_MELDUNG}'
        r._publish()
        return r

    body = _finde_body(iface, parts)
    if body is None:
        r.unentschieden = True
        r.offen_grund = f'kein eindeutiger Körper zu body={iface.body!r}'
        r._publish()
        return r

    m = iface.match(body, machine)
    r.status = m.status
    r.candidates = m.candidates
    if m.status != UNIQUE:
        # Weder bestanden noch verletzt: die Beschreibung passt nicht eindeutig auf die
        # Geometrie. Den „besten" Kandidaten zu nehmen hieße, sich das Ergebnis zu
        # wünschen -- genau der Fehler, gegen den diese Etappe gebaut ist.
        r.unentschieden = True
        r.offen_grund = (m.grund or
                         f'{m.status}: {len(m.candidates)} Flächen passen auf {iface.id!r}, '
                         f'erwartet {m.erwartet}')
        r._publish()
        return r

    treffer = m.candidates
    r.radius_mm = treffer[0]['radius_mm']
    r.axis_deg = max(c['axis_deg'] for c in treffer)
    r.offset_mm = max(c['offset_mm'] for c in treffer)
    ok = True
    if iface.radius is not None and r.radius_mm is not None:
        schlimmster = max(treffer, key=lambda c: abs(c['radius_mm'] - iface.radius))
        d = abs(schlimmster['radius_mm'] - iface.radius)
        if d > iface.tol('radius'):
            ok = False
            r.verletzt.append(f"radius {schlimmster['radius_mm']} statt {iface.radius} "
                              f"({d:.3f} > {iface.tol('radius')})")
    if r.axis_deg > iface.tol('axis_deg'):
        ok = False
        r.verletzt.append(f"axis_deg {r.axis_deg} > {iface.tol('axis_deg')}")
    d = abs(r.offset_mm - float(iface.pitch_radius))
    if d > iface.tol('offset'):
        ok = False
        r.verletzt.append(f"offset {r.offset_mm} statt {iface.pitch_radius} "
                          f"({d:.3f} > {iface.tol('offset')})")

    if iface.partner:
        gegen = partner_body
        if gegen is None and machine is not None:
            try:
                gegen = machine.body(iface.partner)
            except KeyError:
                gegen = None
        if gegen is None:
            r.unentschieden = True
            r.offen_grund = f'Partner {iface.partner!r} nicht zugeordnet (Maschine fehlt?)'
            r._publish()
            return r
        from .primitives.gap import gap
        g = gap(body, [gegen], at=at, within=iface.region(machine))
        if g.nichts_gemessen:
            r.nichts_gemessen = True
            r.leer_grund = f'Partner {iface.partner!r} liegt nicht im Schnittstellenfenster'
            r._publish()
            return r
        r.gap_mm = g.min_mm
        # Formschluss heißt: aufliegen, nicht schweben. Toleranz aus der Pflegedatei.
        if abs(g.min_mm) > iface.tol('gap'):
            ok = False
            r.verletzt.append(f"gap {g.min_mm:.4f} zu {iface.partner} > {iface.tol('gap')}")
        r.fenster_schneidet_material = g.fenster_schneidet_material

    r.passed = ok
    r._publish()
    return r


# -- Pflegedatei ------------------------------------------------------------

def interface_from_dict(d: dict, quelle=None) -> Interface:
    if not isinstance(d, dict):
        raise ValueError(f'Schnittstelleneintrag muss eine Abbildung sein, bekommen {type(d).__name__}')
    sid = d.get('id')
    fehlt = [k for k in PFLICHT if d.get(k) is None]
    if fehlt:
        raise ValueError(f'Schnittstelle {sid!r}: Pflichtfelder fehlen: {fehlt}')
    kind = str(d['kind']).strip().lower()
    if kind not in ARTEN:
        raise ValueError(f'Schnittstelle {sid!r}: kind {kind!r} unbekannt, erlaubt {list(ARTEN)}')
    axis = _vec3(d['axis'], 'axis', sid)
    if not np.any(axis):
        raise ValueError(f'Schnittstelle {sid!r}: axis ist der Nullvektor')
    origin = _vec3(d['origin'], 'origin', sid)
    radius = d.get('radius')
    if kind == 'plane':
        if d.get('size') is None:
            raise ValueError(f'Schnittstelle {sid!r}: plane braucht `size: [u, v]`')
    elif radius is None:
        raise ValueError(f'Schnittstelle {sid!r}: {kind} braucht `radius`')
    if radius is not None and float(radius) <= 0:
        raise ValueError(f'Schnittstelle {sid!r}: radius muss positiv sein')
    count = int(d.get('count', 1))
    if count < 1:
        raise ValueError(f'Schnittstelle {sid!r}: count muss mindestens 1 sein')
    tol = dict(TOLERANZ)
    roh = d.get('tolerance') or {}
    if not isinstance(roh, dict):
        raise ValueError(f'Schnittstelle {sid!r}: tolerance muss eine Abbildung sein')
    unbekannt = set(roh) - set(TOLERANZ)
    if unbekannt:
        raise ValueError(f'Schnittstelle {sid!r}: unbekannte Toleranzen {sorted(unbekannt)}, '
                         f'erlaubt {sorted(TOLERANZ)}')
    tol.update({k: float(v) for k, v in roh.items()})
    status = pruefe_bau_status(d.get('status'), f'Schnittstelle {sid!r}')
    bekannt = set(PFLICHT) | {'frame', 'radius', 'inner_radius', 'pitch_radius', 'length',
                              'size', 'count', 'partner', 'tolerance', 'status'}
    return Interface(
        id=str(sid), kind=kind, body=str(d['body']),
        axis=axis / float(np.linalg.norm(axis)), origin=origin,
        frame=str(d.get('frame', 'world')),
        radius=None if radius is None else float(radius),
        inner_radius=float(d.get('inner_radius', 0.0)),
        pitch_radius=float(d.get('pitch_radius', 0.0)),
        length=float(d.get('length', 0.0)),
        size=tuple(float(x) for x in d['size']) if d.get('size') else None,
        count=count, partner=(str(d['partner']) if d.get('partner') else None),
        status=status, tolerance=tol, quelle=Path(quelle) if quelle else None,
        extra={k: v for k, v in d.items() if k not in bekannt})


def load_interfaces(path) -> list[Interface]:
    """`spec/schnittstellen.yaml` lesen. Wirft bei jedem Formfehler."""
    import yaml
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Schnittstellenliste {path} fehlt')
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f'{path}: Wurzel muss eine Abbildung sein')
    if data.get('schema') != SCHEMA:
        raise ValueError(f'{path}: unerwartetes Schema {data.get("schema")!r}, erwartet {SCHEMA!r}')
    rows = data.get('schnittstellen')
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'{path}: `schnittstellen` fehlt oder ist leer')
    out = [interface_from_dict(r, quelle=path) for r in rows]
    ids = [i.id for i in out]
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    if doppelt:
        raise ValueError(f'{path}: doppelte Schnittstellen-ids: {doppelt}')
    return out


def interfaces_by_id(interfaces) -> dict[str, Interface]:
    return {i.id: i for i in interfaces}
