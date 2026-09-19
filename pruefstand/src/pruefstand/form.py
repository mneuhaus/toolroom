"""Form: Absätze, Kerben, fehlende Rundungen, Splitter -- vier Warnungen auf dem BRep.

Marc am 17.09.2026 zu `docs/bilder/t41-absaetze-marc-2026-09-17.png`: Die Stilregeln
(keine Kerben, saubere Übergänge, R4,2 an Außenkanten, 0,42 mm Bahnbreite) stehen in
den Designregeln, werden aber nicht durchgezogen, weil niemand jedes Teil danach
absucht. Die Pfeile im Bild zeigen auf **Absätze** in der Seitenplatte T41:
Konturversätze von 1--3 mm, entstanden, weil Blöcke zusammengefügt wurden, statt die
Kontur durchzuziehen. „Unnötige Shapes statt eines homogenen Bodies."

Das ist messbar, und zwar rein im BRep -- ohne Messfenster und damit ohne die
Fenster-Falle aus Etappe 3. Alles hier sind **Warnungen** (`@pytest.mark.warnung`),
keine Fehler: ob ein Absatz Absicht ist, weiß nur Marc. Der Prüfstand sagt, wo einer
ist und mit welchem Maß.

Grundlage ist `kanten(body)`: jede Kante mit Länge, Geometrietyp, Knickwinkel und --
der eigentliche Punkt -- **konvex oder konkav**. Konvex ist eine Außenecke (das
Material liegt im spitzen Keil), konkav eine Innenecke. Erst diese Unterscheidung
macht die vier Regeln formulierbar:

| Regel | sucht |
|---|---|
| `absatz` | konvex + konkav, parallel, 0,3--3 mm auseinander, schmale Stufe dazwischen |
| `kerbe` | konkave Kante mit eigener Gegenwand in 0,2--2,5 mm, ohne Anker |
| `unverrundet` | konvexe Außenkante, 80--100°, länger als 5 mm, ohne Rundung |
| `splitter` | Kanten < 0,42 mm, Flächen < 1 mm², unverschmolzene Nachbarn |

Mesh-Körper haben keine Kanten in diesem Sinn -- ein tesselliertes Dreiecksnetz hat
an *jeder* Facette einen Knick. Für einen Körper ohne Solid liefern alle vier Regeln
deshalb `unentschieden` mit dem Grund „kein BRep", nie eine Null.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .results import Result

__all__ = ['Kante', 'kanten', 'absatz', 'kerbe', 'unverrundet', 'splitter',
           'AbsatzResult', 'KerbeResult', 'UnverrundetResult', 'SplitterResult',
           'FormSpec', 'TeilForm', 'load_form', 'find_form']

KONVEX = 'konvex'
KONKAV = 'konkav'
TANGENTIAL = 'tangential'
UNENTSCHIEDEN = 'unentschieden'

#: Unter diesem Knick ist eine Kante keine Ecke, sondern ein tangentialer Übergang
#: (Fläche auf Rundung). Dort gibt es nichts zu entscheiden.
TANGENTEN_GRAD = 1.0

#: Bahnbreite der Standarddüse. Was kürzer ist, ist im Druck kein Merkmal mehr,
#: sondern eine Spur der Modellierung (Regel 5).
BAHNBREITE_MM = 0.42

#: Außenkanten sollen R4,2 bekommen (`cad-design-preferences`: 0,42 / R4,2).
RUNDUNG_MM = 4.2

#: Rasterweite, in der enge Stellen zu Zonen gebündelt werden. Feiner gemeldet wäre
#: eine Liste von hundert Kanten derselben Nut; gröber verschmölzen zwei Nuten.
ZONEN_RASTER_MM = 5.0

#: Mindestradius, in dem ein Fremdkörper oder eine Schraube an einer engen Stelle
#: liegen muss, damit sie als gewollt gilt. 2,5 mm ist der Wert, mit dem Fables
#: Mesh-Sonde an T41L die Nachbarschaft (T40L, R18, R59, T05) sauber getroffen hat.
ANKER_MM = 2.5

#: Zusätzlich wächst der Ankerradius mit der Spaltbreite: ein 1,45 mm breiter Sitz
#: nimmt ein Teil auf, das 3,7 mm weiter beginnt -- fest verschraubt, mit Fuge.
#: Gemessen an den fünf vertieften R6d-Teilen (18.09.2026):
#:
#: * Faktor 2 (Vorschlag aus dem Analysebericht) erklärt **keine** der 13 Rahmenfugen:
#:   2 x 1,45 = 2,90 mm, die Partner liegen bei 3,7--4,0 mm.
#: * Faktor 3 erklärt genau diese 13 (Grenze 4,35 mm) und **keine** Stelle mehr:
#:   der nächste Befund darüber ist die 95 mm lange Nut an T41R mit Partner HORN0 in
#:   5,53 mm, dann die echten Nuten von T02 ab 6,12 mm. Zwischen 4,0 und 5,5 mm
#:   liegt nichts -- die Trennung ist also nicht knapp, sondern deutlich.
#:
#: Der Faktor ist je Aufruf und je Teil (`form.yaml`) überschreibbar; der angewandte
#: Radius steht an jeder Zone (`anker_mm`), damit nichts davon unsichtbar wirkt.
ANKER_FAKTOR = 3.0

#: Spaltbreiten, die als Kerbe zählen. Unter 0,2 mm ist es eine Modellierungsnaht,
#: über 2,5 mm ein Durchgang.
KERBE_MM = (0.2, 2.5)

#: Kanten an der Bettseite werden im Druck ohnehin nicht gerundet -- die erste Lage
#: liegt plan auf. Diese Toleranz um `z_min` der Druckpose nimmt sie heraus.
BETT_MM = 0.5

SCHEMA = 'pruefstand.form/1'

_WURZEL_KEYS = {'schema', 'teile'}
_TEIL_KEYS = {'key', 'erklaert', 'anker_mm', 'anker_faktor'}
_ERKLAERT_KEYS = {'name', 'bereich', 'grund'}
_BEREICH_KEYS = {'frame', 'von', 'bis'}


# -- Kantenklassifikation ---------------------------------------------------

@dataclass(frozen=True)
class Kante:
    """Eine Kante mit ihrer Nachbarschaft. Längen in mm, Winkel in Grad."""

    index: int
    typ: str                          #: Line / Circle / Ellipse / BSplineCurve / ...
    laenge_mm: float
    mitte: np.ndarray                 #: Kantenmitte in Weltkoordinaten
    richtung: np.ndarray              #: Tangente in der Mitte, normiert
    knick_deg: float                  #: Winkel zwischen den beiden Flächennormalen
    art: str                          #: konvex | konkav | tangential | unentschieden
    normalen: tuple = ()              #: die beiden Normalen in der Kantenmitte
    flaechen: tuple = ()              #: Flächenindizes wie in `interface.py`: `<key>#i`
    flaechen_mm2: tuple = ()
    radius_mm: float | None = None    #: nur bei Circle: Krümmungsradius
    kreis_mitte: np.ndarray | None = None
    geschlossen: bool = False
    grund: str = ''                   #: warum `unentschieden`

    @property
    def halbierende(self) -> np.ndarray:
        """Winkelhalbierende der Normalen -- bei konvexen Kanten zeigt sie nach außen."""
        h = np.asarray(self.normalen[0], dtype=float) + np.asarray(self.normalen[1], dtype=float)
        n = float(np.linalg.norm(h))
        return h / n if n > 1e-9 else np.asarray(self.normalen[0], dtype=float)

    def __repr__(self):
        return (f'Kante({self.index}, {self.typ}, {self.laenge_mm:.2f} mm, {self.art}, '
                f'{self.knick_deg:.1f}°, {np.round(self.mitte, 1).tolist()})')


def _tangente(edge):
    """(Mittelpunkt, normierte Tangente) in der Parametermitte der Kante."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.gp import gp_Pnt, gp_Vec
    ad = BRepAdaptor_Curve(edge.wrapped)
    u = 0.5 * (ad.FirstParameter() + ad.LastParameter())
    p, v = gp_Pnt(), gp_Vec()
    ad.D1(u, p, v)
    t = np.array([v.X(), v.Y(), v.Z()], dtype=float)
    n = float(np.linalg.norm(t))
    return np.asarray(p.Coord(), dtype=float), (t / n if n > 1e-12 else t)


def _abstand_punkt_flaeche(face, punkt) -> float:
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    v = BRepBuilderAPI_MakeVertex(gp_Pnt(*[float(x) for x in punkt])).Vertex()
    d = BRepExtrema_DistShapeShape(v, face.wrapped)
    d.Perform()
    return float(d.Value())


def _hinein(face, edge, mitte, tangente, normale) -> np.ndarray | None:
    """Richtung von der Kante **in die Fläche hinein**, senkrecht zur Kante.

    Beide Vorzeichen von ``n x t`` liegen in der Tangentialebene; welches in die
    Fläche zeigt, entscheidet ein Probepunkt -- nur auf der richtigen Seite liegt er
    noch auf der Fläche. Das ist der Unterschied zur naheliegenden Abkürzung über den
    Flächenschwerpunkt: die kippt an T05 an sechs Kanten (0,02 bis 0,57 mm lang, an
    einer 902 mm² großen Ebene), weil der Schwerpunkt einer großen Fläche nichts
    darüber sagt, auf welcher Seite einer winzigen Kante sie liegt.
    """
    q = np.cross(normale, tangente)
    n = float(np.linalg.norm(q))
    if n < 1e-9:
        return None
    q = q / n
    eps = float(np.clip(0.2 * float(edge.length), 1e-4, 0.05))
    da = _abstand_punkt_flaeche(face, mitte + q * eps)
    db = _abstand_punkt_flaeche(face, mitte - q * eps)
    if abs(da - db) < 1e-12:
        return None
    return q if da < db else -q


def _flaechen_karte(solid):
    """Indexkarte der Flächen, in derselben Reihenfolge, in der `interface.py` zählt."""
    from OCP.TopTools import TopTools_IndexedMapOfShape
    karte = TopTools_IndexedMapOfShape()
    for f in solid.faces():
        karte.Add(f.wrapped)
    return karte


def _kanten_roh(body) -> list[tuple]:
    """(Kante, build123d-Edge) je Kante -- die Rohform für die Regeln."""
    if getattr(body, 'solid', None) is None:
        return []
    import build123d as bd
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_CurveType
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape

    solid = body.solid
    fkarte = _flaechen_karte(solid)
    karte = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid.wrapped, TopAbs_EDGE, TopAbs_FACE, karte)
    out = []
    for i in range(1, karte.Extent() + 1):
        e = bd.Edge(karte.FindKey(i))
        fs = [bd.Face(f) for f in karte.FindFromIndex(i)]
        ad = BRepAdaptor_Curve(e.wrapped)
        mitte, t = _tangente(e)
        gemein = dict(index=i, typ=str(ad.GetType()).split('_')[-1], laenge_mm=float(e.length),
                      mitte=mitte, richtung=t, geschlossen=bool(e.wrapped.Closed()),
                      flaechen=tuple(f'{body.key}#{fkarte.FindIndex(f.wrapped) - 1}' for f in fs),
                      flaechen_mm2=tuple(round(float(f.area), 4) for f in fs))
        if ad.GetType() == GeomAbs_CurveType.GeomAbs_Circle:
            ci = ad.Circle()
            gemein['radius_mm'] = float(ci.Radius())
            gemein['kreis_mitte'] = np.asarray(ci.Location().Coord(), dtype=float)
        if len(fs) != 2:
            out.append((Kante(knick_deg=float('nan'), art=UNENTSCHIEDEN,
                              grund=f'{len(fs)} Nachbarflächen statt zwei', **gemein), e))
            continue
        pt = bd.Vector(*mitte)
        n1 = np.asarray(tuple(fs[0].normal_at(pt)), dtype=float)
        n2 = np.asarray(tuple(fs[1].normal_at(pt)), dtype=float)
        knick = float(np.degrees(np.arccos(np.clip(float(np.dot(n1, n2)), -1.0, 1.0))))
        gemein['normalen'] = (n1, n2)
        if knick < TANGENTEN_GRAD:
            out.append((Kante(knick_deg=knick, art=TANGENTIAL, **gemein), e))
            continue
        t2 = _hinein(fs[1], e, mitte, t, n2)
        if t2 is None:
            out.append((Kante(knick_deg=knick, art=UNENTSCHIEDEN,
                              grund='Richtung in die Nachbarfläche nicht bestimmbar',
                              **gemein), e))
            continue
        # Das Material liegt im Keil zwischen beiden Flächen. Führt die Nachbarfläche
        # unter die Außennormale der ersten (negative Projektion), ist der Keil spitz:
        # eine Außenecke.
        art = KONVEX if float(np.dot(n1, t2)) < 0 else KONKAV
        out.append((Kante(knick_deg=knick, art=art, **gemein), e))
    return out


def kanten(body) -> list[Kante]:
    """Alle Kanten eines Körpers klassifizieren. Leere Liste, wenn kein BRep da ist."""
    return [k for k, _ in _kanten_roh(body)]


# -- gemeinsame Werkzeuge ---------------------------------------------------

def _strahl(solid, start, richtung, tol=1e-6) -> list[float]:
    """Abstände aller Flächentreffer entlang des Strahls, vorwärts, aufsteigend."""
    from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    inter = BRepIntCurveSurface_Inter()
    lin = gp_Lin(gp_Pnt(*[float(x) for x in start]), gp_Dir(*[float(x) for x in richtung]))
    inter.Init(solid.wrapped, lin, tol)
    out = []
    while inter.More():
        out.append(float(inter.W()))
        inter.Next()
    return sorted(w for w in out if w > tol)


def _im_material(solid, punkt, tol=1e-7) -> bool:
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_State
    c = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(*[float(x) for x in punkt]), tol)
    return c.State() == TopAbs_State.TopAbs_IN


def _winkel(a, b) -> float:
    """Winkel zwischen zwei Richtungen ohne Vorzeichen (0…90°)."""
    c = float(np.clip(abs(float(np.dot(a, b))), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def _kein_brep(r: Result, body) -> bool:
    """Mesh-only: unentschieden statt einer erfundenen Null. Meldet den Körper ans Budget."""
    from . import results as _res
    _res.merke_koerper(body.key, getattr(body, 'solid', None) is not None)
    if getattr(body, 'solid', None) is not None:
        return False
    r.unentschieden = True
    r.offen_grund = (f'kein BRep: {body.key!r} ist nur als Netz geladen. Ein Dreiecksnetz '
                     'hat an jeder Facette einen Knick -- Kanten sind daran nicht messbar')
    r.uebersprungen.append({'was': 'koerper', 'key': body.key, 'grund': 'kein BRep (nur Netz)'})
    r._publish()
    return True


def _ort(p) -> list:
    return [round(float(x), 3) for x in np.asarray(p, dtype=float).reshape(3)]


#: Flächen, an denen ein tangentialer Übergang gewollt ist: dort läuft eine Ebene in
#: eine Rundung. Alles andere (Ebene auf Ebene mit Knick 0) ist eine Boolesche Spur.
GEKRUEMMT = ('CYLINDER', 'TORUS', 'SPHERE', 'CONE', 'BEZIER', 'BSPLINE', 'REVOLUTION',
             'EXTRUSION', 'OFFSET', 'OTHER')


def _flaechentyp(flaechen, bezeichner) -> str:
    """Geometrietyp einer Fläche zu einem `<key>#i`-Bezeichner, als blanker Name."""
    try:
        f = flaechen[int(str(bezeichner).split('#')[-1])]
    except (IndexError, ValueError):                       # pragma: no cover
        return 'UNBEKANNT'
    return str(f.geom_type).split('.')[-1].upper()


def _normale_an(flaechen, bezeichner, ort) -> np.ndarray:
    """Normale einer Fläche am Ort `ort` -- notfalls in ihrer Mitte.

    Der Ort eines Absatzes ist die Mitte **zwischen** beiden Kanten und liegt damit
    nicht immer auf der Fläche; `normal_at` wirft dann. Für eine Ebene ist die
    Flächenmitte gleichwertig, für eine gekrümmte Fläche ist sie die beste Näherung,
    die ohne Projektion zu haben ist.
    """
    import build123d as bd
    f = flaechen[int(str(bezeichner).split('#')[-1])]
    try:
        return np.asarray(tuple(f.normal_at(bd.Vector(*[float(x) for x in ort]))), dtype=float)
    except Exception:
        return np.asarray(tuple(f.normal_at()), dtype=float)


#: Die drei Sorten eines Absatzes, nach dem Verfahren aus
#: `rocking-photo-tray-r7/src/t41_details.py` (18.09.2026, Marcs vier Pfeile):
#:
#: * `umriss`    -- alle drei Flächen stehen quer zur Platte: die **Silhouette**
#:                  springt. Das ist der Pfeil unten links im Foto.
#: * `banddicke` -- die Wände stehen quer, die Stufe liegt in einer Ebene der
#:                  Plattenachse: die **Stirnfläche des Randbandes** wird stufig
#:                  schmaler. Das sind die zwei Pfeile rechts am Servo.
#: * `pad`       -- die Wände sind die großen Plattenflächen: ein **aufgesetzter
#:                  Block** mitten auf der Fläche. Im Foto nicht zu sehen und meist
#:                  harmlos -- aber genau deshalb muss man ihn trennen können, sonst
#:                  ertrinken die zwei sichtbaren Sorten in 24 bzw. 31 unsichtbaren.
SORTEN = ('umriss', 'banddicke', 'pad')

#: Ab dieser Projektion auf die Plattenachse gilt eine Normale als „längs zur Achse".
#: 0,3 entspricht 17° Abweichung -- weit genug von 45°, dass eine schräge Fläche nicht
#: zufällig kippt, und derselbe Wert wie in der Handrechnung an T41.
_LAENGS = 0.3


def _sorte(na, nb, n_stufe, achse) -> str:
    """Die Sorte eines Absatzes aus den drei Flächennormalen und der Plattenachse."""
    quer = [abs(float(np.dot(n / max(float(np.linalg.norm(n)), 1e-12), achse))) < _LAENGS
            for n in (na, nb)]
    if not all(quer):
        return 'pad'
    n = n_stufe / max(float(np.linalg.norm(n_stufe)), 1e-12)
    return 'umriss' if abs(float(np.dot(n, achse))) < _LAENGS else 'banddicke'


def plattenachse(body) -> np.ndarray:
    """Richtung der kleinsten Ausdehnung eines Körpers -- die „Dicke" einer Platte.

    `absatz` braucht sie, um die drei Sorten zu trennen: ohne eine Bezugsachse lassen
    sich ein Pad auf der großen Fläche und ein Sprung im Umriss nicht unterscheiden --
    beide sind eine Stufe zwischen zwei parallelen Wänden, nur eben quer zu
    verschiedenen Richtungen. Für ein plattenartiges Teil (Seitenplatte, Boden,
    Wange) ist die dünnste Hüllrichtung genau die Plattennormale.
    """
    lo, hi = body.bounds()
    mass = np.asarray(hi, dtype=float) - np.asarray(lo, dtype=float)
    a = np.zeros(3)
    a[int(np.argmin(mass))] = 1.0
    return a


# -- Regel 2: Absatz --------------------------------------------------------

@dataclass(repr=False)
class AbsatzResult(Result):
    """Konturversätze: zwei parallele Wände, dazwischen eine schmale Stufe."""

    anzahl: int = 0
    max_versatz_mm: float = 0.0
    #: Wie viele Absätze je Sorte -- {'umriss': n, 'banddicke': n, 'pad': n}.
    sorten: dict = field(default_factory=dict)
    #: Bezugsachse, nach der sortiert wurde (die „Dicke" der Platte).
    achse: list = field(default_factory=list)
    absaetze: list = field(default_factory=list)
    passed: bool = True
    primitive: str = 'absatz'
    _fields: tuple = ('anzahl', 'max_versatz_mm', 'sorten', 'achse', 'absaetze')


def absatz(body, *, versatz_mm=(0.3, 3.0), parallel_deg=2.0, achse=None) -> AbsatzResult:
    """Konturversätze suchen -- Marcs Pfeile im T41-Bild.

    Ein Absatz ist ein Kantenpaar konvex + konkav, das

    1. an **derselben** Fläche liegt -- das ist die Stufe,
    2. parallel läuft (< `parallel_deg`),
    3. `versatz_mm` auseinanderliegt (0,3--3 mm: darunter eine Naht, darüber eine
       gewollte Stufe),
    4. dessen Stufe schmaler als lang ist, und
    5. dessen beide Nachbarwände (fast) parallel stehen -- dann läuft dieselbe Kontur
       zweimal, nur um den Versatz verschoben.

    Urteil auf `brep`.
    """
    import build123d as bd
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    r = AbsatzResult()
    r.urteil_auf = 'brep'
    if _kein_brep(r, body):
        return r
    achse_gesetzt = achse is not None
    achse = plattenachse(body) if achse is None else (
        np.asarray(achse, dtype=float).reshape(3)
        / float(np.linalg.norm(np.asarray(achse, dtype=float).reshape(3))))
    roh = _kanten_roh(body)
    edges = {k.index: e for k, e in roh}
    ks = [k for k, _ in roh]
    flaechen = list(body.solid.faces())
    lo, hi = float(versatz_mm[0]), float(versatz_mm[1])

    gefunden = []
    for a in (k for k in ks if k.art == KONVEX):
        for b in (k for k in ks if k.art == KONKAV):
            gemeinsam = set(a.flaechen) & set(b.flaechen)
            if not gemeinsam:
                continue
            if _winkel(a.richtung, b.richtung) > float(parallel_deg):
                continue
            d = BRepExtrema_DistShapeShape(edges[a.index].wrapped, edges[b.index].wrapped)
            d.Perform()
            versatz = float(d.Value())
            if not lo <= versatz <= hi:
                continue
            laenge = min(a.laenge_mm, b.laenge_mm)
            # Eine Stufe ist schmal: ihre Breite (der Versatz) bleibt unter ihrer Länge.
            if versatz >= laenge:
                continue
            stufe = sorted(gemeinsam)[0]
            wand_a = [x for x in a.flaechen if x != stufe]
            wand_b = [x for x in b.flaechen if x != stufe]
            if not wand_a or not wand_b:
                continue
            fa = flaechen[int(wand_a[0].split('#')[-1])]
            fb = flaechen[int(wand_b[0].split('#')[-1])]
            na = np.asarray(tuple(fa.normal_at(bd.Vector(*a.mitte))), dtype=float)
            nb = np.asarray(tuple(fb.normal_at(bd.Vector(*b.mitte))), dtype=float)
            if _winkel(na, nb) > float(parallel_deg):
                continue
            ort = _ort(0.5 * (a.mitte + b.mitte))
            n_stufe = _normale_an(flaechen, stufe, ort)
            gefunden.append({'ort': ort,
                             'versatz_mm': round(versatz, 4),
                             'laenge_mm': round(laenge, 3),
                             'sorte': _sorte(na, nb, n_stufe, achse),
                             'flaechen': [wand_a[0], stufe, wand_b[0]],
                             'stufe_mm2': round(float(flaechen[int(stufe.split('#')[-1])].area), 3),
                             'kanten': [a.index, b.index]})
    gefunden.sort(key=lambda g: -g['laenge_mm'])
    r.absaetze = gefunden
    r.anzahl = len(gefunden)
    r.max_versatz_mm = round(max((g['versatz_mm'] for g in gefunden), default=0.0), 4)
    r.sorten = {s: sum(1 for g in gefunden if g['sorte'] == s) for s in SORTEN}
    r.achse = _ort(achse)
    r.passed = not gefunden
    r.annahmen.append({'regel': 'absatz', 'versatz_mm': [lo, hi],
                       'parallel_deg': float(parallel_deg), 'kanten': len(ks),
                       'plattenachse': r.achse,
                       'plattenachse_gesetzt': achse_gesetzt})
    r._publish()
    return r


# -- Regel 3: Kerbe ---------------------------------------------------------

@dataclass(repr=False)
class KerbeResult(Result):
    """Enge Spalte im eigenen Körper, für die kein Partner spricht."""

    anzahl: int = 0
    unerklaert: int = 0
    enge_kanten_mm: float = 0.0
    min_spalt_mm: float | None = None
    zonen: list = field(default_factory=list)
    passed: bool = True
    primitive: str = 'kerbe'
    _fields: tuple = ('anzahl', 'unerklaert', 'enge_kanten_mm', 'min_spalt_mm', 'zonen')


def _segment_abstand(p, a, b) -> float:
    """Abstand eines Punktes zur Strecke a--b."""
    ab = b - a
    n = float(np.dot(ab, ab))
    t = 0.0 if n < 1e-12 else float(np.clip(np.dot(p - a, ab) / n, 0.0, 1.0))
    return float(np.linalg.norm(p - (a + ab * t)))


def _naechster_koerper(punkte, koerper) -> tuple:
    """(key, Abstand) des nächsten Fremdkörpers zu einer Punktwolke -- exakt auf dem Netz."""
    from .primitives import _nearest
    beste = ('', float('inf'))
    pts = np.atleast_2d(np.asarray(punkte, dtype=float))
    for b in koerper:
        try:
            m = b.mesh
        except Exception:                                  # pragma: no cover
            continue
        if m is None or len(m.faces) == 0:
            continue
        lo, hi = m.bounds
        # Grobfilter: liegt die Wolke weit außerhalb der Hülle, lohnt der Zellbaum nicht.
        schranke = float(np.linalg.norm(np.maximum(np.maximum(lo - pts.max(axis=0), 0),
                                                   np.maximum(pts.min(axis=0) - hi, 0))))
        if schranke > beste[1]:
            continue
        d = float(np.min(_nearest.distances(pts, m)))
        if d < beste[1]:
            beste = (b.key, d)
    return beste


def _kontext_koerper(kontext, body) -> list:
    """Fremdkörper aus `kontext` sammeln -- Scene, Liste von Szenen oder Bodies.

    Mehrere Szenen heißen „über alle Posen". Der Körper selbst fliegt heraus: er ist
    sein eigener Nachbar in jeder Fuge und würde jede Frage mit „0 mm" beantworten.
    """
    from .machine import Scene
    from .primitives._common import as_bodies
    fremd = []
    for q in (kontext if isinstance(kontext, (list, tuple)) else [kontext]):
        if q is None:
            continue
        if isinstance(q, Scene):
            fremd.extend(b for b in q.bodies if b.key != body.key)
        else:
            fremd.extend(b for b in as_bodies(q) if b.key != body.key)
    return fremd


def kerbe(body, kontext=None, at=None, *, schrauben=(), erklaert=None, machine=None,
          spalt_mm=KERBE_MM, knick_deg=60.0, raster_mm=ZONEN_RASTER_MM,
          anker_mm=None, anker_faktor=None) -> KerbeResult:
    """Enge Spalte ohne Anker finden -- „Lücke, die niemand bestellt hat".

    Gesucht werden konkave Kanten mit mehr als `knick_deg` Knick, von deren Mitte aus
    entlang **beider** Flächennormalen eine Gegenwand des *eigenen* Körpers in
    `spalt_mm` steht. Solche Kanten werden im `raster_mm`-Raster zu Zonen gebündelt.

    Eine Zone ist **erklärt**, wenn in ihrem Ankerradius ein Kontextkörper oder eine
    Schraube liegt (dann ist der Spalt eine Passung), oder wenn sie in
    `spec/form.yaml` unter `erklaert:` steht. Der Rest wird gemeldet -- mit
    Spaltbreite, Länge, nächstem Fremdkörper und dessen Abstand, damit man sieht, wie
    knapp die Erklärung fehlt.

    Der Ankerradius ist **nicht** fest, sondern wächst mit der Spaltbreite:
    ``max(anker_mm, anker_faktor * spalt)``. Ein fester Radius von 2,5 mm meldete an
    den R6d-Rahmenplatten 13 Sitze als Kerben, deren Partner 3,7--4,0 mm entfernt
    beginnt -- ein breiter Sitz nimmt nun einmal ein Teil auf, das weiter weg anfängt.
    Vorgaben: `anker_mm` = 2,5 mm, `anker_faktor` = 3,0; beide je Teil in
    `spec/form.yaml` überschreibbar (`anker_mm:`, `anker_faktor:`). Der tatsächlich
    angewandte Radius steht an jeder Zone.

    `kontext` ist eine `Scene`, eine Liste von Szenen oder eine Liste von Körpern;
    mehrere Szenen heißen „über alle Posen". Urteil auf `brep`.
    """
    from .primitives._common import as_bodies
    r = KerbeResult()
    r.urteil_auf = 'brep'
    if _kein_brep(r, body):
        return r
    if at is not None:
        body = as_bodies(body, at)[0]
    # Reihenfolge: Aufrufargument schlägt Pflegedatei schlägt Hausregel. Umgekehrt
    # könnte ein Eintrag in form.yaml einen bewusst gesetzten Wert im Test still
    # überschreiben.
    basis = float(anker_mm if anker_mm is not None
                  else (getattr(erklaert, 'anker_mm', None) or ANKER_MM))
    faktor = float(anker_faktor if anker_faktor is not None
                   else (getattr(erklaert, 'anker_faktor', None) or ANKER_FAKTOR))

    fremd = _kontext_koerper(kontext, body)

    lo, hi = float(spalt_mm[0]), float(spalt_mm[1])
    treffer = []
    for k in kanten(body):
        if k.art != KONKAV or k.knick_deg <= float(knick_deg):
            continue
        spalt = None
        for n in k.normalen:
            n = np.asarray(n, dtype=float)
            # Start minimal vor der Wand, sonst zählt die Fläche, auf der man steht.
            ws = _strahl(body.solid, k.mitte + n * 1e-4, n)
            if ws and lo <= ws[0] + 1e-4 <= hi:
                d = ws[0] + 1e-4
                spalt = d if spalt is None else min(spalt, d)
        if spalt is not None:
            treffer.append((k, spalt))

    zellen: dict = {}
    for k, spalt in treffer:
        schluessel = tuple(int(np.floor(x / float(raster_mm))) for x in k.mitte)
        z = zellen.setdefault(schluessel, {'kanten': 0, 'laenge_mm': 0.0,
                                           'spalt_mm': float('inf'), 'punkte': []})
        z['kanten'] += 1
        z['laenge_mm'] += k.laenge_mm
        z['spalt_mm'] = min(z['spalt_mm'], spalt)
        z['punkte'].append(k.mitte)

    gebiete = []
    for z in zellen.values():
        ort = np.mean(np.asarray(z['punkte'], dtype=float), axis=0)
        key, dist = _naechster_koerper(z['punkte'], fremd)
        for s in schrauben or ():
            p0, d0 = s.axis_points(machine)
            ds = min(_segment_abstand(np.asarray(p, dtype=float), p0, p0 + d0 * s.laenge_mm)
                     for p in z['punkte'])
            if ds < dist:
                key, dist = f'schraube {s.id}', ds
        # Der Ankerradius gehört zur Zone, nicht zur Regel: ein 0,34 mm schmaler
        # Schlitz bleibt bei 2,5 mm, ein 1,45 mm breiter Sitz darf bis 4,35 mm suchen.
        anker = max(basis, faktor * float(z['spalt_mm']))
        grund = ''
        if dist <= anker:
            grund = f'Partner {key} in {dist:.2f} mm (Anker {anker:.2f} mm)'
        elif erklaert is not None:
            name = erklaert.trifft(ort, machine)
            if name:
                grund = f'erklärt: {name}'
        gebiete.append({'ort': _ort(ort), 'spalt_mm': round(float(z['spalt_mm']), 4),
                        'laenge_mm': round(float(z['laenge_mm']), 3), 'kanten': z['kanten'],
                        'partner': key, 'partner_mm': (None if dist == float('inf')
                                                       else round(float(dist), 3)),
                        'anker_mm': round(float(anker), 3),
                        'erklaert': bool(grund), 'grund': grund})
    gebiete.sort(key=lambda g: (g['erklaert'], -g['laenge_mm']))
    offen = [g for g in gebiete if not g['erklaert']]
    r.zonen = gebiete
    r.anzahl = len(gebiete)
    r.unerklaert = len(offen)
    r.enge_kanten_mm = round(sum(k.laenge_mm for k, _ in treffer), 2)
    r.min_spalt_mm = round(min((g['spalt_mm'] for g in gebiete), default=float('nan')), 4) \
        if gebiete else None
    r.passed = not offen
    r.annahmen.append({'regel': 'kerbe', 'spalt_mm': [lo, hi], 'raster_mm': float(raster_mm),
                       'anker_mm': basis, 'anker_faktor': faktor,
                       'anker_max_mm': round(max((g['anker_mm'] for g in gebiete), default=basis), 3),
                       'kontext_koerper': len(fremd), 'schrauben': len(schrauben or ())})
    if not fremd:
        r.uebersprungen.append({'was': 'kontext', 'grund': 'kein Kontextkörper übergeben -- '
                                'jede enge Stelle kann nur über form.yaml erklärt werden'})
    r._publish()
    return r


# -- Regel 4: unverrundet ---------------------------------------------------

@dataclass(repr=False)
class UnverrundetResult(Result):
    """Scharfe Außenkanten, an denen nach Hausregel R4,2 sitzen sollte."""

    anzahl: int = 0
    gesamt_mm: float = 0.0
    radius_mm: float = RUNDUNG_MM
    kanten: list = field(default_factory=list)
    #: Welche Ausnahmen tatsächlich angewandt wurden. Fehlt eine, ist `anzahl` eine
    #: Obergrenze -- und das steht dann auch in `Result.obergrenze`.
    ausnahmen: dict = field(default_factory=dict)
    passed: bool = True
    primitive: str = 'unverrundet'
    _fields: tuple = ('anzahl', 'gesamt_mm', 'radius_mm', 'ausnahmen', 'kanten')
    _obergrenze_felder: tuple = ('anzahl', 'gesamt_mm')


#: Näher als das an einem Nachbarkörper ist eine Kante eine **Fugenkante**: dort stößt
#: ein anderes Teil an, sie ist nicht frei anfassbar und wird nicht verrundet. 1,0 mm
#: ist das Nahfeld aus dem HANDOFF (Anker = Kontakt/Nahfeld über alle Posen).
FUGE_MM = 1.0


def unverrundet(body, pose=None, *, teil=None, kontext=None, at=None, machine=None,
                knick_deg=(80.0, 100.0), min_mm=5.0, radius_mm=None,
                fuge_mm=FUGE_MM) -> UnverrundetResult:
    """Konvexe Außenkanten ohne Rundung -- die R4,2-Regel.

    Kandidat ist eine konvexe Kante mit `knick_deg` Knick und mehr als `min_mm` Länge.
    **Außenkante** heißt: ein Strahl von der Kantenmitte entlang der Winkelhalbierenden
    nach außen trifft den eigenen Körper nicht mehr -- die Kante steht frei und ließe
    sich anfassen.

    Zwei Dinge fallen bewusst heraus:

    * **Bohrungsmündungen.** Ein Kreis, dessen Krümmungsmittelpunkt nicht im Material
      liegt, ist der Rand eines Lochs, keine Außenecke des Teils. An der Wanne sind
      das sieben Kreise (r 1,70 x 4, r 3,10, r 6,10 x 2); ohne diese Unterscheidung
      stünden 23 statt 16 Kandidaten im Bericht, und kein R4,2 passte in ein Ø3,4-Loch.
    * **Die Bettseite.** Gibt `pose` oder `teil.auflage` die Lage im Druck her, sind
      die Kanten am Bett ausgenommen: dort wird ohnehin nicht gerundet.
    * **Fugenkanten.** Liegt mit `kontext` ein Nachbarkörper näher als `fuge_mm`,
      stößt dort ein anderes Teil an -- die Kante ist nicht frei anfassbar.

    **Ohne diese beiden Ausnahmen ist die Zahl eine Obergrenze**, und das Ergebnis
    sagt es: `result.obergrenze = True`, im Terminalbericht steht ein `≤` vor den
    Werten. Die 2,3--5,4 m scharfe Kante je R6d-Rahmenplatte sind genau so entstanden
    (`r7-analyse-bericht.md`, Werkzeuglücke 3).

    `teil` ist ein Eintrag aus `spec/teile.yaml` (`pruefstand.teile/1`): Druckpose,
    Auflagefläche und `griffkanten: ja/nein`. Daraus kommt auch die Schwelle --
    R4,2 gilt für frei anfassbare Außenkanten, ein Rahmenteil bekommt den Kantenbruch
    R1,0. Sie ist je Teil über `radius_mm` überschreibbar. Die **Zählung** ändert das
    nicht: eine scharfe Kante ist scharf, gleich welcher Radius verlangt ist; die
    Schwelle steht am Ergebnis und im Klartext der Meldung.

    Urteil auf `brep`.
    """
    from .printing import pose_matrix
    if pose is None and teil is not None:
        pose = getattr(teil, 'pose', None)
    schwelle = float(radius_mm) if radius_mm is not None else (
        teil.schwelle_mm(RUNDUNG_MM) if teil is not None else RUNDUNG_MM)
    r = UnverrundetResult(radius_mm=schwelle)
    r.urteil_auf = 'brep'
    if _kein_brep(r, body):
        return r
    if at is not None:
        from .primitives._common import as_bodies
        body = as_bodies(body, at)[0]
    ks = kanten(body)
    lo, hi = float(knick_deg[0]), float(knick_deg[1])

    m = pose_matrix(getattr(pose, 'pose', pose) if pose is not None else None)
    z_min = None
    if pose is not None:
        v = body.vertices()
        z_min = float((v @ m[:3, :3].T + m[:3, 3])[:, 2].min())
    auflage = getattr(teil, 'auflage', None) if teil is not None else None
    # Die Bettebene hängt am ganzen Körper, nicht an der einzelnen Kante -- deshalb
    # einmal für alle Kantenmitten zusammen, mit den Stützpunkten als Bezug.
    bett_maske = None
    if auflage is not None and ks:
        bett_maske = auflage.bettkanten([k.mitte for k in ks], body.vertices(), machine, BETT_MM)
    fremd = _kontext_koerper(kontext, body)

    gefunden = []
    for i, k in enumerate(ks):
        if k.art != KONVEX or not lo <= k.knick_deg <= hi or k.laenge_mm <= float(min_mm):
            continue
        h = k.halbierende
        if _strahl(body.solid, k.mitte + h * 0.02, h):
            continue                              # die Kante schaut in eine Tasche
        if k.radius_mm is not None and k.kreis_mitte is not None \
                and not _im_material(body.solid, k.kreis_mitte):
            continue                              # Bohrungsmündung, keine Außenecke
        if z_min is not None:
            z = float((m[:3, :3] @ k.mitte + m[:3, 3])[2])
            if z <= z_min + BETT_MM:
                continue                          # Bettseite: wird nicht gerundet
        if bett_maske is not None and bool(bett_maske[i]):
            continue                              # Auflage aus teile.yaml
        if fremd:
            key, dist = _naechster_koerper([k.mitte], fremd)
            if dist <= float(fuge_mm):
                continue                          # Fugenkante: da stößt key an
        gefunden.append({'ort': _ort(k.mitte), 'laenge_mm': round(k.laenge_mm, 3),
                         'typ': k.typ, 'knick_deg': round(k.knick_deg, 2),
                         'richtung': _ort(k.richtung), 'nach_aussen': _ort(h),
                         'flaechen': list(k.flaechen), 'kante': k.index})
    gefunden.sort(key=lambda g: -g['laenge_mm'])
    bett = z_min is not None or auflage is not None
    r.kanten = gefunden
    r.anzahl = len(gefunden)
    r.gesamt_mm = round(sum(g['laenge_mm'] for g in gefunden), 2)
    r.ausnahmen = {'bettseite': bool(bett), 'fugenkanten': bool(fremd),
                   'griffkanten': (None if teil is None else teil.griffkanten)}
    # Ehrlich bleiben: solange eine der beiden Ausnahmen fehlt, ist jede Zahl hier zu
    # groß -- Bettkanten und Fugenkanten werden nie verrundet, stehen aber mit drin.
    r.obergrenze = not (bett and bool(fremd))
    r.passed = not gefunden
    r.annahmen.append({'regel': 'unverrundet', 'knick_deg': [lo, hi], 'min_mm': float(min_mm),
                       'radius_mm': schwelle, 'bettseite_ausgenommen': bool(bett),
                       'fugenkanten_ausgenommen': bool(fremd),
                       'fuge_mm': float(fuge_mm) if fremd else None,
                       'obergrenze': bool(r.obergrenze)})
    if r.obergrenze:
        fehlt = [n for n, da in (('Druckpose/Auflage', bett), ('Kontext für Fugenkanten', bool(fremd)))
                 if not da]
        r.uebersprungen.append({'was': 'ausnahme', 'grund': 'Obergrenze: ' + ' und '.join(fehlt)
                                + ' fehlt -- Bettkanten und Fugenkanten zählen mit'})
    r._publish()
    return r


# -- Regel 5: Splitter ------------------------------------------------------

@dataclass(repr=False)
class SplitterResult(Result):
    """Spuren von Block-auf-Block: Reste, die kein Drucker mehr auflöst."""

    anzahl: int = 0
    kurze_kanten: list = field(default_factory=list)
    winzige_flaechen: list = field(default_factory=list)
    unverschmolzen: list = field(default_factory=list)
    #: Tangentiale Übergänge auf eine Rundung -- **kein** Befund, aber gezählt: wer
    #: eine Verrundung entfernt, sieht die Zahl fallen, ohne dass ein Test kippt.
    rundungsuebergaenge: list = field(default_factory=list)
    passed: bool = True
    primitive: str = 'splitter'
    _fields: tuple = ('anzahl', 'kurze_kanten', 'winzige_flaechen', 'unverschmolzen',
                      'rundungsuebergaenge')


def splitter(body, *, kante_mm=BAHNBREITE_MM, flaeche_mm2=1.0, nachbar_mm2=100.0,
             knick_deg=0.5) -> SplitterResult:
    """Splitter suchen: zu kurze Kanten, zu kleine Flächen, unverschmolzene Nachbarn.

    Drei Spuren derselben Ursache -- ein Block wurde an einen anderen gesetzt, statt
    die Kontur durchzuziehen:

    1. **Kanten unter der Bahnbreite** (0,42 mm). Der Drucker kann sie nicht drucken,
       das Modell führt sie trotzdem mit.
    2. **Flächen unter `flaeche_mm2`**, die zwischen Nachbarn über `nachbar_mm2`
       sitzen: ein Schnipsel zwischen zwei großen Wänden.
    3. **Unverschmolzene Nachbarn**: zwei Flächen mit weniger als `knick_deg` Knick,
       die trotzdem durch eine Kante getrennt sind. Geometrisch ist das eine Fläche,
       im Modell sind es zwei.

    Nur BRep -- auf dem Netz wäre die Frage sinnlos: über die Hälfte aller Dreiecke
    einer Tessellierung sind Winzlinge, ganz ohne Modellierfehler.
    """
    r = SplitterResult()
    r.urteil_auf = 'brep'
    if _kein_brep(r, body):
        return r
    ks = kanten(body)
    flaechen = list(body.solid.faces())

    kurz = [{'ort': _ort(k.mitte), 'laenge_mm': round(k.laenge_mm, 4), 'typ': k.typ,
             'kante': k.index} for k in ks if k.laenge_mm < float(kante_mm)]

    winzig = []
    for i, f in enumerate(flaechen):
        a = float(f.area)
        if a >= float(flaeche_mm2):
            continue
        nachbarn = [max(k.flaechen_mm2) for k in ks if f'{body.key}#{i}' in k.flaechen]
        if nachbarn and max(nachbarn) > float(nachbar_mm2):
            winzig.append({'flaeche': f'{body.key}#{i}', 'ort': _ort(tuple(f.center())),
                           'mm2': round(a, 4), 'groesster_nachbar_mm2': round(max(nachbarn), 2)})

    # Nahtkanten zählen nicht: bei einem Zylinder schließt sich die Parameterfläche an
    # einer Kante mit sich selbst. Beide Nachbarn sind dieselbe Fläche, der Knick ist
    # null -- „unverschmolzen" wäre dazu die falsche Behauptung. An der Wanne sind das
    # 14 von 14 Treffern; ohne diese Unterscheidung meldete jeder Rundzapfen Splitter.
    #
    # Und der zweite, größere Irrtum (Etappe 4, alle 20/16 Treffer an T41): ein sauber
    # tangentialer Fillet **ist** eine Fläche, die glatt in eine Rundung übergeht. Der
    # Übergang ist das Merkmal, nicht der Rest. Unverschmolzen bleibt nur, was zwischen
    # zwei *ungekrümmten* Flächen glatt durchläuft -- zwei Ebenen mit Knick 0, die
    # trotzdem eine Kante trennt, sind wirklich eine Boolesche Spur.
    glatt, rundung = [], []
    for k in ks:
        if k.art != TANGENTIAL or k.knick_deg >= float(knick_deg) or len(set(k.flaechen)) != 2:
            continue
        typen = sorted(_flaechentyp(flaechen, f) for f in k.flaechen)
        eintrag = {'ort': _ort(k.mitte), 'knick_deg': round(k.knick_deg, 4),
                   'laenge_mm': round(k.laenge_mm, 3), 'flaechen': list(k.flaechen),
                   'flaechentypen': typen, 'kante': k.index}
        (rundung if any(t in GEKRUEMMT for t in typen) else glatt).append(eintrag)

    r.kurze_kanten = sorted(kurz, key=lambda x: x['laenge_mm'])
    r.winzige_flaechen = sorted(winzig, key=lambda x: x['mm2'])
    r.unverschmolzen = sorted(glatt, key=lambda x: -x['laenge_mm'])
    r.rundungsuebergaenge = sorted(rundung, key=lambda x: -x['laenge_mm'])
    r.anzahl = len(kurz) + len(winzig) + len(glatt)
    r.passed = r.anzahl == 0
    r.annahmen.append({'regel': 'splitter', 'kante_mm': float(kante_mm),
                       'flaeche_mm2': float(flaeche_mm2), 'nachbar_mm2': float(nachbar_mm2),
                       'knick_deg': float(knick_deg), 'kanten': len(ks),
                       'flaechen': len(flaechen),
                       'rundungsuebergaenge': len(rundung)})
    r._publish()
    return r


# -- Pflegedatei `spec/form.yaml` -------------------------------------------

def _vec3(value, feld, wo) -> np.ndarray:
    try:
        v = np.asarray(value, dtype=float).reshape(3)
    except Exception as exc:
        raise ValueError(f'{wo}: {feld} braucht drei Zahlen, bekommen {value!r}') from exc
    if not np.all(np.isfinite(v)):
        raise ValueError(f'{wo}: {feld} enthält keine endlichen Zahlen: {value!r}')
    return v


def _zahl(value, feld, wo) -> float | None:
    """Eine positive Zahl aus der Pflegedatei -- oder `None`, wenn der Schlüssel fehlt."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{wo}: {feld} braucht eine Zahl, bekommen {value!r}') from None
    if not (v > 0) or not np.isfinite(v):
        raise ValueError(f'{wo}: {feld} muss größer als null sein, ist {value!r}')
    return v


def _fremde(d: dict, erlaubt: set, wo: str) -> None:
    unbekannt = sorted(set(d) - erlaubt)
    if unbekannt:
        raise ValueError(f'{wo}: unbekannte Schlüssel {unbekannt}, erlaubt {sorted(erlaubt)}')


@dataclass(frozen=True)
class ErklaerteZone:
    """Ein benannter Quader, in dem enge Stellen gewollt sind."""

    name: str
    frame: str
    von: np.ndarray
    bis: np.ndarray
    grund: str = ''

    def enthaelt(self, punkt, machine=None) -> bool:
        from .frame import Frame
        f = Frame.identity() if (machine is None or str(self.frame).lower() == 'world') \
            else machine.frame(self.frame)
        p = np.asarray(f.to_local(np.atleast_2d(np.asarray(punkt, dtype=float))))[0]
        lo = np.minimum(self.von, self.bis)
        hi = np.maximum(self.von, self.bis)
        return bool(np.all(p >= lo) and np.all(p <= hi))

    def __repr__(self):
        return f'ErklaerteZone({self.name!r}, {self.frame})'


@dataclass(frozen=True)
class TeilForm:
    """Was für ein Teil an engen Stellen von Hand erklärt wurde."""

    key: str
    erklaert: tuple = ()
    #: Ankerradius dieses Teils; `None` = Hausregel (`ANKER_MM` / `ANKER_FAKTOR`).
    #: Gebraucht für Teile, deren Nachbarschaft grundsätzlich weiter weg beginnt --
    #: eine Rahmenplatte mit 4 mm Fuge zum nächsten Teil meldet sonst jeden Sitz.
    anker_mm: float | None = None
    anker_faktor: float | None = None
    quelle: Path | None = None

    def trifft(self, punkt, machine=None) -> str:
        """Name der erklärten Zone, in der der Punkt liegt -- sonst ''."""
        for z in self.erklaert:
            if z.enthaelt(punkt, machine):
                return z.name
        return ''

    def __repr__(self):
        return f'TeilForm({self.key!r}, {[z.name for z in self.erklaert]})'


@dataclass
class FormSpec:
    """Alle Teile einer `form.yaml`."""

    teile: dict = field(default_factory=dict)
    quelle: Path | None = None

    def teil(self, key) -> TeilForm | None:
        return self.teile.get(str(key))

    def keys(self) -> list[str]:
        return list(self.teile)

    def __len__(self):
        return len(self.teile)

    def __repr__(self):
        return f'FormSpec({self.keys()})'


def load_form(path) -> FormSpec:
    """`spec/form.yaml` lesen (Schema `pruefstand.form/1`). Wirft bei jedem Formfehler."""
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
    for d in rows:
        if not isinstance(d, dict):
            raise ValueError(f'{path}: `teile`-Eintrag muss eine Abbildung sein')
        _fremde(d, _TEIL_KEYS, f'{path}: teile-Eintrag')
        key = d.get('key')
        if not key:
            raise ValueError(f'{path}: teile-Eintrag ohne `key`')
        if str(key) in teile:
            raise ValueError(f'{path}: doppelter Teil-key {key!r}')
        wo = f'{path}: Teil {key!r}'
        zonen = []
        for e in d.get('erklaert') or []:
            if not isinstance(e, dict):
                raise ValueError(f'{wo}: `erklaert`-Eintrag muss eine Abbildung sein')
            _fremde(e, _ERKLAERT_KEYS, wo)
            name = e.get('name')
            if not name:
                raise ValueError(f'{wo}: `name` fehlt')
            bereich = e.get('bereich')
            if not isinstance(bereich, dict):
                raise ValueError(f'{wo} / {name}: `bereich` fehlt oder ist keine Abbildung')
            _fremde(bereich, _BEREICH_KEYS, f'{wo} / {name} / bereich')
            for feld in ('von', 'bis'):
                if bereich.get(feld) is None:
                    raise ValueError(f'{wo} / {name}: `bereich.{feld}` fehlt')
            zonen.append(ErklaerteZone(
                name=str(name), frame=str(bereich.get('frame', 'world')),
                von=_vec3(bereich['von'], 'bereich.von', f'{wo} / {name}'),
                bis=_vec3(bereich['bis'], 'bereich.bis', f'{wo} / {name}'),
                grund=str(e.get('grund', ''))))
        namen = [z.name for z in zonen]
        doppelt = sorted({n for n in namen if namen.count(n) > 1})
        if doppelt:
            raise ValueError(f'{wo}: doppelte Namen unter `erklaert`: {doppelt}')
        teile[str(key)] = TeilForm(key=str(key), erklaert=tuple(zonen), quelle=path,
                                   anker_mm=_zahl(d.get('anker_mm'), 'anker_mm', wo),
                                   anker_faktor=_zahl(d.get('anker_faktor'), 'anker_faktor', wo))
    return FormSpec(teile=teile, quelle=path)


def find_form(spec_dir=None) -> FormSpec | None:
    """`form.yaml` im Spec-Verzeichnis des laufenden Projekts. None, wenn es keine gibt."""
    from . import context as _ctx
    if spec_dir is None:
        p = _ctx.project()
        if p is None:
            return None
        spec_dir = p.spec
    f = Path(spec_dir) / 'form.yaml'
    return load_form(f) if f.exists() else None
