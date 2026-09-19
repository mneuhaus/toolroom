"""gap(): kleinster Abstand zwischen zwei Körpermengen."""
from __future__ import annotations

import numpy as np

from ..results import GapResult, KernelFehler
from . import _fcl
from ._common import as_bodies, empty, fenster_flag, prepare

#: Ab dieser Eindringtiefe ist eine Netzberührung eine Durchdringung. Darunter ist es
#: Koinzidenz: zwei bündig aufeinander liegende Tessellierungen teilen sich dieselben
#: Stützpunkte, und fcl meldet dafür dieselbe Tiefe wie für echtes Material im
#: Material. 0,01 mm liegt zwei Größenordnungen unter jeder Fuge, die der Prüfstand
#: sonst misst (0,2 mm Montagefuge), und zwei über der Rauheit einer STEP-Tessellierung.
DURCHDRINGUNG_MM = 0.01


def _bbox_lower_bound(ma, mb) -> float:
    a0, a1 = ma.bounds
    b0, b1 = mb.bounds
    d = np.maximum(np.maximum(b0 - a1, a0 - b1), 0.0)
    return float(np.linalg.norm(d))


#: So viele Netzpunkte werden je Seite höchstens auf Eindringtiefe geprüft. Eine
#: Tessellierung der ganzen Maschine hat Hunderttausende; für die Frage „steckt hier
#: etwas ineinander" reicht ein gleichmäßiger Auszug aus der Überlappungszone.
NETZ_PUNKTE_MAX = 20000


def _geschlossen(mesh):
    """Geschlossene Fassung eines Netzes oder `None`, wenn es keine gibt.

    STL-Körper werden mit `process=False` geladen (jede Facette bringt ihre eigenen
    Stützpunkte mit) -- ungeprüft ist damit **jedes** Netz „offen", und die
    Innen/Außen-Frage wäre nie beantwortbar. Geprüft wird deshalb an einer Kopie mit
    zusammengelegten Stützpunkten; sie hängt am Netz, damit sie nur einmal entsteht.
    """
    hit = getattr(mesh, '_pruefstand_dicht', False)
    if hit is not False:
        return hit
    m = mesh
    if not m.is_watertight:
        m = mesh.copy()
        m.merge_vertices()
        if not m.is_watertight:
            m = None
    try:
        object.__setattr__(mesh, '_pruefstand_dicht', m)
    except Exception:                                      # pragma: no cover
        pass
    return m


def _netz_tiefe(ma, mb) -> float | None:
    """Größte Eindringtiefe zweier Netze in mm -- `None`, wenn nicht entscheidbar.

    **Nicht** über `fcl.penetration_depth`: für koinzidente Flächen (Formschluss)
    liefert der Kern dort die volle Körpertiefe -- zwei bündige 10er-Würfel ergeben
    10,0 mm. Gemessen wird stattdessen, wie weit die Stützpunkte des einen Netzes
    **im** anderen liegen (vorzeichenbehafteter Abstand, positiv innen). Für zwei
    bündige Flächen ist das 0, für 0,05 mm Überschneidung 0,05.

    Das setzt geschlossene Netze voraus -- „innen" ist sonst nicht definiert. Bei
    einem offenen Netz gibt es keine Antwort, und eine erfundene wäre schlimmer als
    keine.
    """
    import trimesh
    ma, mb = _geschlossen(ma), _geschlossen(mb)
    if ma is None or mb is None:
        return None
    lo = np.maximum(ma.bounds[0], mb.bounds[0]) - 0.05
    hi = np.minimum(ma.bounds[1], mb.bounds[1]) + 0.05
    tiefe = 0.0
    for m, gegen in ((ma, mb), (mb, ma)):
        # Stützpunkte **und** Facettenmitten. Nur die Stützpunkte zu nehmen misst bei
        # zwei Quadern null: die einzigen eingedrungenen Punkte sind Ecken, und die
        # liegen auf den Seitenflächen des Gegenkörpers (Abstand 0). Die Mitte der
        # eingedrungenen Facette liegt dagegen frei im Material.
        v = np.vstack([np.asarray(m.vertices, dtype=float),
                       np.asarray(m.triangles_center, dtype=float)])
        v = v[np.all((v >= lo) & (v <= hi), axis=1)]
        if not len(v):
            continue
        if len(v) > NETZ_PUNKTE_MAX:
            v = v[:: len(v) // NETZ_PUNKTE_MAX + 1]
        d = trimesh.proximity.signed_distance(gegen, v)
        if len(d):
            tiefe = max(tiefe, float(np.max(d)))
    return max(tiefe, 0.0)


def _durchdringt(ba, bb, ma, mb, beschnitten: bool) -> tuple:
    """(durchdringt, worauf, tiefe_mm) für ein Paar mit Netzabstand 0.

    `distance() == 0` allein ist **kein** Beleg für eine Durchdringung: Formschluss
    liefert denselben Wert. T40 gegen T41 stand deshalb als `penetrating=True` im
    Bericht, während `overlap` daneben exakt 0,0 mm³ und `collides=False` sagte --
    jede gewollte Auflage sah aus wie eine Kollision.

    Deshalb wird nachgerechnet: Haben beide Körper ein BRep und wurde nichts
    zugeschnitten, entscheidet der **exakte Schnitt** (> 0 mm³ = Durchdringung).
    Sonst -- Netzkörper, oder ein Messfenster hat die Netze beschnitten und die
    Solids passen nicht mehr zu dem, was gemessen wurde -- bleibt nur das Netz, und
    dort zählt erst eine Eindringtiefe über `DURCHDRINGUNG_MM`.
    """
    if not beschnitten and ba.solid is not None and bb.solid is not None:
        from .overlap import _intersect_volume
        try:
            v, _ort = _intersect_volume(ba.solid, bb.solid)
            return bool(v > 1e-9), 'brep', 0.0
        except KernelFehler:
            pass                      # Kern hat verweigert -- unten über das Netz
    tiefe = _netz_tiefe(ma, mb)
    if tiefe is None:
        return False, 'unentschieden', 0.0
    return bool(tiefe > DURCHDRINGUNG_MM), 'mesh', float(tiefe)


#: Reihenfolge der Belege, vom stärksten zum schwächsten.
_BELEG = ('brep', 'mesh', 'unentschieden')


def _schwaecher(a: str, b: str) -> str:
    """Der schwächere der beiden Belege gewinnt -- eine Messung ist so gut wie ihr
    schlechtestes Paar."""
    return max((a, b), key=lambda x: _BELEG.index(x) if x in _BELEG else -1)


def gap(a, b, at=None, within=None, ignore=None, min_mm=None, max_mm=None) -> GapResult:
    A = as_bodies(a, at)
    B = as_bodies(b, at)
    beschnitten = within is not None or ignore is not None
    best = float('inf')
    pair = ()
    pa = pb = None
    per_body = {}
    penetrating = False
    penetration_auf = ''
    durchdringung_mm = 0.0
    kernel_aus = False
    offen: list = []
    single = len(A) == 1
    for ba in A:
        ma = prepare(ba, within, ignore)
        if empty(ma):
            continue
        for bb in B:
            mb = prepare(bb, within, ignore)
            if empty(mb):
                continue
            key = bb.key if single else f'{ba.key}|{bb.key}'
            lb = _bbox_lower_bound(ma, mb)
            if lb >= best and key in per_body:
                continue
            d, p1, p2 = _fcl.distance(ma, mb)
            per_body[key] = min(per_body.get(key, float('inf')), d)
            if d < best:
                best = d
                pair = (ba.key, bb.key)
                pa, pb = p1, p2
            if d <= 0.0:
                tief, woher, tiefe = _durchdringt(ba, bb, ma, mb, beschnitten)
                kernel_aus = kernel_aus or woher != 'brep'
                if tief:
                    penetrating = True
                    durchdringung_mm = max(durchdringung_mm, tiefe)
                if woher == 'unentschieden':
                    offen.append(f'{ba.key} gegen {bb.key}: offenes Netz')
                # Der schwächere Beleg gewinnt: sagt auch nur ein Paar „nur Netz",
                # steht das an der Aussage.
                penetration_auf = _schwaecher(penetration_auf, woher)
    leer = best == float('inf')
    ok = not leer
    if min_mm is not None:
        ok = ok and best >= min_mm
    if max_mm is not None:
        ok = ok and best <= max_mm
    r = GapResult(min_mm=best, point_a=pa, point_b=pb, pair=pair, per_body=per_body,
                  penetrating=penetrating, penetration_auf=penetration_auf,
                  durchdringung_mm=round(durchdringung_mm, 5), passed=ok)
    # Der Abstand kommt aus dem Kollisionskern, der auf Netzen rechnet -- das Urteil
    # ist ein Mesh-Urteil, auch wenn beide Körper aus einem STEP stammen. `penetrating`
    # kann trotzdem exakt sein; woher es kommt, steht in `penetration_auf`.
    r.urteil_auf = 'mesh'
    if penetration_auf:
        r.annahmen.append({'regel': 'gap.penetrating', 'auf': penetration_auf,
                           'durchdringung_mm': DURCHDRINGUNG_MM if penetration_auf == 'mesh'
                           else None})
    if kernel_aus and beschnitten:
        r.uebersprungen.append({'was': 'brep', 'grund': 'Durchdringung auf dem Netz entschieden: '
                                'ein Messfenster hat die Netze beschnitten, die Solids nicht'})
    if offen:
        # Kein Urteil über die Durchdringung -- `penetrating=False` heißt hier „nicht
        # geprüft", und das muss im Budget stehen, sonst liest es sich wie „geprüft".
        r.uebersprungen.append({'was': 'durchdringung', 'anzahl': len(offen),
                                'keys': offen[:12],
                                'grund': 'offenes Netz: „innen" ist daran nicht definiert'})
    r.fenster_schneidet_material = fenster_flag(within, ignore)
    if leer:
        r.nichts_gemessen = True
        r.leer_grund = 'min_mm=inf, kein Körperpaar im Ausschnitt'
    r._publish()
    return r
